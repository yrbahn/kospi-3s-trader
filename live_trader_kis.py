#!/usr/bin/env python3
"""
실시간 모의 투자 시스템 (KIS API 연동)
한국투자증권 모의투자 계좌를 통한 실제 주문 처리
"""
import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
import yaml
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from src.data.data_manager import DataManager
from src.agents.news_agent import NewsAgent
from src.agents.technical_agent import TechnicalAgent
from src.agents.fundamental_agent import FundamentalAgent
from src.agents.score_agent import ScoreAgent
from src.agents.selector_agent import SelectorAgent
from src.agents.strategy_agent import StrategyAgent
from src.kis.kis_client import KISClient

# .env 로드
load_dotenv()

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger("live_trader_kis")

HISTORY_FILE = Path(__file__).parent / "trading_history.json"


class LiveTraderKIS:
    """실시간 모의 투자 시스템 (KIS API)"""

    def __init__(self, config: dict, prompts: dict):
        self.config = config
        self.prompts = prompts
        
        # KIS 클라이언트
        self.kis = self._init_kis_client()
        
        # 데이터 매니저
        self.data_manager = DataManager(config)
        
        # 에이전트
        self.news_agent = NewsAgent(config, prompts)
        self.technical_agent = TechnicalAgent(config, prompts)
        self.fundamental_agent = FundamentalAgent(config, prompts)
        self.score_agent = ScoreAgent(config, prompts)
        self.selector_agent = SelectorAgent(config, prompts)
        self.strategy_agent = StrategyAgent(config, prompts)
        
        # 현재 전략
        self.current_strategy = prompts.get("initial_strategy", "균형 잡힌 접근법")
        
        # 거래 이력 로드
        self.history = self._load_history()

    def _init_kis_client(self) -> KISClient:
        """KIS 클라이언트 초기화"""
        app_key = os.getenv("KIS_APP_KEY")
        app_secret = os.getenv("KIS_APP_SECRET")
        account_no = os.getenv("KIS_ACCOUNT_NO")
        
        if not all([app_key, app_secret, account_no]):
            raise ValueError(
                "KIS API 인증 정보 없음!\n"
                ".env 파일에 설정하세요:\n"
                "KIS_APP_KEY=...\n"
                "KIS_APP_SECRET=...\n"
                "KIS_ACCOUNT_NO=12345678-01"
            )
        
        # 실전투자 모드
        return KISClient(app_key, app_secret, account_no, mock=False)

    def _load_history(self) -> list:
        """거래 이력 로드"""
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def _save_history(self):
        """거래 이력 저장"""
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def run_weekly_analysis(self) -> dict:
        """주간 3S-Trader 분석 실행"""
        logger.info("🚀 주간 3S-Trader 분석 시작")
        
        today = datetime.now().strftime("%Y%m%d")
        
        # Stage 1: 데이터 수집
        logger.info("📊 Stage 1: 시장 데이터 분석...")
        all_data = self.data_manager.collect_all_data(today)
        
        # Stage 2: 종목 점수 평가
        logger.info("🎯 Stage 2: 종목 점수 평가...")
        all_scores = []
        
        for ticker, data in all_data.items():
            name = data["name"]
            
            try:
                # 3개 에이전트 분석
                news_analysis = self.news_agent.analyze(ticker, name, data["news_text"])
                tech_summary = data["technical"].get("summary", "데이터 없음")
                tech_analysis = self.technical_agent.analyze(ticker, name, tech_summary)
                fund_analysis = self.fundamental_agent.analyze(ticker, name, data["fundamental_text"])
                
                # 점수 평가
                scores = self.score_agent.score(
                    ticker, name,
                    news_analysis, tech_analysis, fund_analysis
                )
                all_scores.append(scores)
                
                logger.info(
                    f"  [{name}] 재무:{scores['financial_health']} "
                    f"성장:{scores['growth_potential']} "
                    f"뉴스감성:{scores['news_sentiment']}"
                )
            except Exception as e:
                logger.error(f"[{name}] 분석 실패: {e}")
                continue
        
        # Stage 3: 포트폴리오 구성
        logger.info("📋 Stage 3: 포트폴리오 구성...")
        scores_text = ScoreAgent.format_scores_text(all_scores)
        new_portfolio = self.selector_agent.select(
            scores_text, self.current_strategy
        )
        
        return new_portfolio

    def rebalance(self, new_portfolio: dict) -> dict:
        """포트폴리오 리밸런싱 (KIS API 사용)"""
        logger.info("🔄 포트폴리오 리밸런싱...")
        
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
        
        # 매도 (새 포트폴리오에 없는 종목)
        new_codes = {item["code"] for item in new_portfolio.get("portfolio", [])}
        sells = []
        
        for ticker in current_holdings.keys():
            if ticker not in new_codes:
                holding = current_holdings[ticker]
                shares = holding["shares"]
                
                # 매도 주문
                logger.info(f"📉 매도: {holding['name']}({ticker}) {shares}주")
                success = self.kis.order_sell(ticker, shares)
                
                if success:
                    price = self.kis.get_current_price(ticker)
                    sells.append({
                        "ticker": ticker,
                        "name": holding["name"],
                        "shares": shares,
                        "price": price or 0,
                    })
        
        # 잔고 재조회 (매도 후)
        balance = self.kis.get_balance()
        available_cash = balance["cash"]
        
        # 매수 (새 포트폴리오 종목)
        # ⚠️ 소액 투자 모드: 저가 종목 우선, 최소 1주 매수 가능한 것만
        buys = []
        
        # 매수 가능한 종목 필터링 (가격 순 정렬)
        affordable_items = []
        for item in new_portfolio.get("portfolio", []):
            ticker = item["code"]
            name = item["name"]
            price = self.kis.get_current_price(ticker)
            
            if not price or price == 0:
                logger.warning(f"⚠️ {name}({ticker}) 현재가 조회 실패")
                continue
            
            # 최소 1주 매수 가능한지 확인
            if price <= available_cash * 0.8:  # 현금의 80%까지만 사용 (여유 20%)
                affordable_items.append({
                    **item,
                    "price": price,
                })
        
        # 저가 종목부터 매수 (가격 오름차순)
        affordable_items.sort(key=lambda x: x["price"])
        
        logger.info(f"💰 매수 가능한 종목: {len(affordable_items)}개 (현금: {available_cash:,.0f}원)")
        
        for item in affordable_items[:5]:  # 최대 5종목
            ticker = item["code"]
            name = item["name"]
            price = item["price"]
            target_weight = item["weight"]
            
            # 비중에 맞춰 주수 계산 (단, 최소 1주)
            target_value = current_value * target_weight
            shares = max(1, int(target_value / price))
            cost = shares * price
            
            # 현금 부족하면 1주만 매수
            if cost > available_cash:
                shares = 1
                cost = price
            
            if available_cash >= cost:
                # 매수 주문
                logger.info(f"📈 매수: {name}({ticker}) {shares}주 @ {price:,.0f}원 = {cost:,.0f}원")
                success = self.kis.order_buy(ticker, shares)
                
                if success:
                    buys.append({
                        "ticker": ticker,
                        "name": name,
                        "shares": shares,
                        "price": price,
                        "cost": cost,
                    })
                    available_cash -= cost
            else:
                logger.info(f"⏭️ 건너뜀: {name}({ticker}) - 현금 부족")
        
        # 거래 이력 기록
        self.history.append({
            "date": datetime.now().isoformat(),
            "total_value": current_value,
            "cash": available_cash,
            "sells": sells,
            "buys": buys,
        })
        self._save_history()
        
        return {
            "sells": sells,
            "buys": buys,
            "current_value": current_value,
            "cash": available_cash,
        }

    def generate_report(self, rebalance_result: dict) -> str:
        """Telegram 리포트 생성"""
        lines = []
        lines.append("📊 **3S-Trader 주간 리포트** (KIS 모의투자)")
        lines.append(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")
        
        # 포트폴리오 가치
        current = rebalance_result["current_value"]
        
        # 첫 거래인지 확인
        if len(self.history) > 1:
            initial = self.history[0]["total_value"]
        else:
            initial = current
        
        change = current - initial
        change_pct = (change / initial) * 100 if initial > 0 else 0
        
        lines.append("💰 **포트폴리오 가치**")
        lines.append(f"현재: {current:,.0f}원")
        lines.append(f"누적 수익: {change:+,.0f}원 ({change_pct:+.2f}%)")
        lines.append(f"현금: {rebalance_result['cash']:,.0f}원")
        lines.append("")
        
        # 매도
        if rebalance_result["sells"]:
            lines.append("📉 **매도**")
            for sell in rebalance_result["sells"]:
                lines.append(
                    f"- {sell['name']}({sell['ticker']}): "
                    f"{sell['shares']:,}주 @ {sell['price']:,.0f}원"
                )
            lines.append("")
        
        # 매수
        if rebalance_result["buys"]:
            lines.append("📈 **매수**")
            for buy in rebalance_result["buys"]:
                lines.append(
                    f"- {buy['name']}({buy['ticker']}): "
                    f"{buy['shares']:,}주 @ {buy['price']:,.0f}원"
                )
            lines.append("")
        
        # 현재 보유
        balance = self.kis.get_balance()
        lines.append("📋 **현재 보유**")
        if balance["holdings"]:
            for ticker, holding in balance["holdings"].items():
                lines.append(f"- {holding['name']}({ticker}): {holding['shares']:,}주")
        else:
            lines.append("- 현금 100%")
        
        return "\n".join(lines)

    def run(self):
        """메인 실행"""
        try:
            # 주간 분석
            new_portfolio = self.run_weekly_analysis()
            
            # 리밸런싱
            result = self.rebalance(new_portfolio)
            
            # 리포트 생성
            report = self.generate_report(result)
            
            logger.info("✅ 주간 실행 완료")
            print("\n" + report)
            
            return report
            
        except Exception as e:
            logger.error(f"❌ 실행 실패: {e}")
            import traceback
            traceback.print_exc()
            raise


def main():
    """메인 함수"""
    # 설정 로드
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    with open('config/prompts.yaml', 'r', encoding='utf-8') as f:
        prompts = yaml.safe_load(f)
    
    # LiveTraderKIS 실행
    trader = LiveTraderKIS(config, prompts)
    report = trader.run()
    
    # TODO: Telegram 메시지 전송


if __name__ == "__main__":
    main()
