#!/usr/bin/env python3
"""
저장된 포트폴리오로 즉시 주문 실행
장 시작 시 실행 (10초 이내 완료)
"""
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from src.kis.kis_client import KISClient
import psycopg2
from psycopg2.extras import RealDictCursor

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/execute_portfolio.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# .env 로드
load_dotenv()

PORTFOLIO_FILE = Path(__file__).parent / "portfolio_scheduled.json"


class PortfolioExecutor:
    """포트폴리오 주문 실행 전용"""
    
    def __init__(self):
        # KIS API 설정
        app_key = os.getenv("KIS_APP_KEY")
        app_secret = os.getenv("KIS_APP_SECRET")
        account_no = os.getenv("KIS_ACCOUNT_NO")
        
        if not all([app_key, app_secret, account_no]):
            raise ValueError("KIS API 인증 정보가 없습니다!")
        
        self.kis = KISClient(app_key, app_secret, account_no, mock=False)
        self.portfolio_id = None
    
    def load_portfolio(self) -> dict:
        """DB에서 실행 대기 중인 포트폴리오 로드"""
        conn = psycopg2.connect("postgresql://yrbahn@localhost:5432/marketsense")
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # 오늘 날짜의 미실행 포트폴리오 조회
            today = datetime.now().date()
            
            cur.execute("""
                SELECT id, portfolio_json, analyzed_at, execute_date, cash_weight, rationale
                FROM portfolio_history
                WHERE execute_date = %s AND executed = FALSE
                ORDER BY analyzed_at DESC
                LIMIT 1
            """, (today,))
            
            row = cur.fetchone()
            
            if not row:
                # JSON 파일 백업에서 로드
                logger.warning("⚠️ DB에 포트폴리오 없음, JSON 파일 사용")
                if not PORTFOLIO_FILE.exists():
                    raise FileNotFoundError("포트폴리오가 없습니다!")
                
                with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            self.portfolio_id = row['id']
            portfolio = row['portfolio_json']
            
            logger.info(f"✅ 포트폴리오 DB 로드 (ID: {self.portfolio_id})")
            logger.info(f"   분석 시간: {row['analyzed_at']}")
            logger.info(f"   실행 예정일: {row['execute_date']}")
            
            return portfolio
            
        finally:
            cur.close()
            conn.close()
    
    def execute(self):
        """포트폴리오 실행"""
        logger.info("🚀 포트폴리오 주문 실행 시작")
        logger.info(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 포트폴리오 로드
        portfolio = self.load_portfolio()
        
        # 현재 잔고 조회
        balance = self.kis.get_balance()
        current_cash = balance["cash"]
        current_holdings = balance["holdings"]
        
        logger.info(f"현재 현금: {current_cash:,.0f}원")
        logger.info(f"현재 보유 종목: {len(current_holdings)}개")
        
        # 현재 포트폴리오 가치 계산
        current_value = current_cash
        for ticker, holding in current_holdings.items():
            price = self.kis.get_current_price(ticker)
            if price:
                current_value += holding["shares"] * price
        
        logger.info(f"현재 총 자산: {current_value:,.0f}원")
        
        # 1. 매도 (기존 종목 정리)
        logger.info("\n📉 매도 주문...")
        new_tickers = {stock['code'] for stock in portfolio.get('portfolio', [])}
        
        for ticker, holding in current_holdings.items():
            if ticker not in new_tickers:
                name = holding["name"]
                shares = holding["shares"]
                logger.info(f"📉 매도: {name}({ticker}) {shares}주")
                
                success = self.kis.order_sell(ticker, shares, price=None)
                if success:
                    logger.info(f"✅ 매도 주문 성공!")
                    # 매도 예상 금액 추가
                    current_price = self.kis.get_current_price(ticker)
                    if current_price:
                        current_cash += shares * current_price
                else:
                    logger.error(f"❌ 매도 주문 실패")
        
        # 2. 매수 (새 포트폴리오 구성)
        logger.info("\n📈 매수 주문...")
        
        target_stocks = portfolio.get('portfolio', [])
        if not target_stocks:
            logger.warning("⚠️ 매수할 종목 없음 (현금 100% 유지)")
            return
        
        # 가격 정보 수집 및 정렬 (저가 우선)
        stock_prices = []
        for stock in target_stocks:
            ticker = stock['code']
            name = stock.get('name', 'Unknown')
            weight = stock['weight']
            
            current_price = self.kis.get_current_price(ticker)
            if not current_price:
                logger.warning(f"⚠️ {name}({ticker}) 현재가 조회 실패")
                continue
            
            target_amount = current_value * weight
            shares = int(target_amount / current_price)
            
            if shares < 1:
                continue
            
            stock_prices.append({
                'ticker': ticker,
                'name': name,
                'price': current_price,
                'shares': shares,
                'amount': shares * current_price
            })
        
        # 가격 낮은 순 정렬
        stock_prices.sort(key=lambda x: x['price'])
        
        logger.info(f"💰 매수 가능한 종목: {len(stock_prices)}개 (현금: {current_cash:,.0f}원)")
        
        # 최대 5개 종목, 현금 80% 사용
        max_cash = current_cash * 0.8
        used_cash = 0
        buy_count = 0
        
        for stock_info in stock_prices:
            if buy_count >= 5:
                break
            
            if used_cash + stock_info['amount'] > max_cash:
                continue
            
            ticker = stock_info['ticker']
            name = stock_info['name']
            shares = stock_info['shares']
            price = stock_info['price']
            amount = stock_info['amount']
            
            logger.info(f"📈 매수: {name}({ticker}) {shares}주 @ {price:,.0f}원 = {amount:,.0f}원")
            
            success = self.kis.order_buy(ticker, shares, price=None)
            if success:
                logger.info(f"✅ 매수 주문 성공!")
                used_cash += amount
                buy_count += 1
            else:
                logger.error(f"❌ 매수 주문 실패")
        
        # 결과
        logger.info("\n" + "=" * 60)
        logger.info(f"✅ 주문 실행 완료")
        logger.info(f"매수: {buy_count}개 종목")
        logger.info(f"사용: {used_cash:,.0f}원")
        logger.info(f"잔액: {current_cash - used_cash:,.0f}원 (예상)")
        logger.info("=" * 60)
        
        # DB에 실행 완료 표시
        if self.portfolio_id:
            conn = psycopg2.connect("postgresql://yrbahn@localhost:5432/marketsense")
            cur = conn.cursor()
            try:
                cur.execute("""
                    UPDATE portfolio_history
                    SET executed = TRUE, executed_at = NOW()
                    WHERE id = %s
                """, (self.portfolio_id,))
                conn.commit()
                logger.info(f"✅ DB 실행 기록 업데이트 (ID: {self.portfolio_id})")
            finally:
                cur.close()
                conn.close()


def main():
    try:
        executor = PortfolioExecutor()
        executor.execute()
    except Exception as e:
        logger.error(f"❌ 실행 실패: {e}")
        raise


if __name__ == "__main__":
    main()
