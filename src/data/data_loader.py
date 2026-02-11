"""MarketSense-AI 데이터베이스 통합 로더 (독립적 구현)

kospi-3s-trader가 marketsense-ai의 PostgreSQL 데이터베이스를 사용하도록 통합
marketsense-ai 모듈에 의존하지 않고 직접 DB 쿼리
"""
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import create_engine, and_, text
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class MarketSenseDataLoader:
    """MarketSense-AI 데이터베이스에서 데이터 로드 (독립적 구현)"""
    
    def __init__(self, db_url: str = None):
        """
        Args:
            db_url: PostgreSQL 연결 URL (None이면 환경변수 사용)
        """
        if db_url is None:
            db_url = os.getenv("DATABASE_URL", "postgresql://yrbahn@localhost:5432/marketsense")
        
        self.engine = create_engine(db_url, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        logger.info(f"MarketSense-AI DB 연결: {db_url}")
    
    @contextmanager
    def get_session(self):
        """세션 컨텍스트 매니저"""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()
    
    def get_stock_info(self, ticker: str) -> Optional[Dict]:
        """종목 기본 정보 조회 (SQL 직접 쿼리)
        
        Args:
            ticker: 종목 코드
            
        Returns:
            {name, market_cap, sector, ...}
        """
        with self.get_session() as session:
            result = session.execute(
                text("SELECT ticker, name, market_cap, sector, industry FROM stocks WHERE ticker = :ticker"),
                {"ticker": ticker}
            ).fetchone()
            
            if not result:
                logger.warning(f"{ticker} 종목 정보 없음")
                return None
            
            return {
                'ticker': result[0],
                'name': result[1],
                'market_cap': result[2],
                'sector': result[3],
                'industry': result[4]
            }
    
    def get_price_data(self, ticker: str, start_date: datetime, end_date: datetime = None) -> List[Dict]:
        """가격 데이터 조회 (SQL 직접 쿼리)
        
        Args:
            ticker: 종목 코드
            start_date: 시작일
            end_date: 종료일 (None이면 오늘)
            
        Returns:
            [{date, open, high, low, close, volume}, ...]
        """
        if end_date is None:
            end_date = datetime.now()
        
        with self.get_session() as session:
            # 종목 ID 조회
            stock_id_result = session.execute(
                text("SELECT id FROM stocks WHERE ticker = :ticker"),
                {"ticker": ticker}
            ).fetchone()
            
            if not stock_id_result:
                logger.warning(f"{ticker} 종목 없음")
                return []
            
            stock_id = stock_id_result[0]
            
            # 가격 데이터 조회
            results = session.execute(
                text("""
                SELECT date, open, high, low, close, volume
                FROM price_data
                WHERE stock_id = :stock_id
                  AND date >= :start_date
                  AND date <= :end_date
                ORDER BY date
                """),
                {"stock_id": stock_id, "start_date": start_date, "end_date": end_date}
            ).fetchall()
            
            return [
                {
                    'date': row[0],
                    'open': row[1],
                    'high': row[2],
                    'low': row[3],
                    'close': row[4],
                    'volume': row[5]
                }
                for row in results
            ]
    
    def get_financial_statements(self, ticker: str, lookback_quarters: int = 8) -> List[Dict]:
        """재무제표 데이터 조회 (SQL 직접 쿼리)
        
        Args:
            ticker: 종목 코드
            lookback_quarters: 몇 분기 조회할지
            
        Returns:
            [{period_end, revenue, operating_income, net_income, ...}, ...]
        """
        with self.get_session() as session:
            # 종목 ID 조회
            stock_id_result = session.execute(
                text("SELECT id FROM stocks WHERE ticker = :ticker"),
                {"ticker": ticker}
            ).fetchone()
            
            if not stock_id_result:
                logger.warning(f"{ticker} 종목 없음")
                return []
            
            stock_id = stock_id_result[0]
            
            # 재무제표 조회 (consolidated 우선, 없으면 dart_comprehensive)
            results = session.execute(
                text("""
                SELECT period_end, fiscal_quarter, raw_data
                FROM financial_statements
                WHERE stock_id = :stock_id
                  AND statement_type IN ('consolidated', 'dart_comprehensive')
                  AND period_type = 'quarterly'
                ORDER BY period_end DESC
                LIMIT :limit
                """),
                {"stock_id": stock_id, "limit": lookback_quarters}
            ).fetchall()
            
            statements = []
            for row in results:
                data = row[2] or {}  # raw_data (JSON)
                statements.append({
                    'period_end': row[0],
                    'fiscal_quarter': row[1],
                    # 손익계산서
                    'revenue': data.get('매출액', 0),
                    'operating_income': data.get('영업이익', 0),
                    'net_income': data.get('당기순이익', 0),
                    # 재무상태표
                    'assets': data.get('자산총계', 0),
                    'equity': data.get('자본총계', 0),
                    'liabilities': data.get('부채총계', 0),
                    # 현금흐름표
                    'operating_cash_flow': data.get('영업활동현금흐름', 0),
                    'investing_cash_flow': data.get('투자활동현금흐름', 0),
                    'financing_cash_flow': data.get('재무활동현금흐름', 0)
                })
            
            return statements
    
    def get_news(self, ticker: str, lookback_days: int = 30) -> List[Dict]:
        """뉴스 데이터 조회 (SQL 직접 쿼리)
        
        Args:
            ticker: 종목 코드
            lookback_days: 몇 일 전까지 조회할지
            
        Returns:
            [{published_at, title, content, url}, ...]
        """
        start_date = datetime.now() - timedelta(days=lookback_days)
        
        with self.get_session() as session:
            # 종목 ID 조회
            stock_id_result = session.execute(
                text("SELECT id FROM stocks WHERE ticker = :ticker"),
                {"ticker": ticker}
            ).fetchone()
            
            if not stock_id_result:
                logger.warning(f"{ticker} 종목 없음")
                return []
            
            stock_id = stock_id_result[0]
            
            # 뉴스 조회
            results = session.execute(
                text("""
                SELECT published_at, title, content, url
                FROM news_articles
                WHERE stock_id = :stock_id
                  AND published_at >= :start_date
                ORDER BY published_at DESC
                """),
                {"stock_id": stock_id, "start_date": start_date}
            ).fetchall()
            
            return [
                {
                    'published_at': row[0],
                    'title': row[1],
                    'content': row[2],
                    'url': row[3]
                }
                for row in results
            ]
    
    def get_all_universe_data(self, tickers: List[str], lookback_weeks: int = 4) -> Dict:
        """전체 universe의 데이터를 한 번에 조회
        
        Args:
            tickers: 종목 코드 리스트
            lookback_weeks: 몇 주 전까지 조회할지
            
        Returns:
            {
                ticker: {
                    'info': {...},
                    'prices': [...],
                    'financials': [...],
                    'news': [...]
                },
                ...
            }
        """
        start_date = datetime.now() - timedelta(weeks=lookback_weeks)
        
        result = {}
        
        for ticker in tickers:
            logger.debug(f"{ticker} 데이터 로딩...")
            
            try:
                result[ticker] = {
                    'info': self.get_stock_info(ticker),
                    'prices': self.get_price_data(ticker, start_date),
                    'financials': self.get_financial_statements(ticker, lookback_quarters=4),  # 논문: 4분기
                    'news': self.get_news(ticker, lookback_days=lookback_weeks*7)
                }
            except Exception as e:
                logger.error(f"{ticker} 데이터 로딩 실패: {e}")
                result[ticker] = {
                    'info': None,
                    'prices': [],
                    'financials': [],
                    'news': []
                }
        
        return result


def load_market_data(config: Dict) -> MarketSenseDataLoader:
    """설정에서 데이터 로더 초기화
    
    Args:
        config: config.yaml의 data 섹션
        
    Returns:
        MarketSenseDataLoader 인스턴스
    """
    db_url = config.get('db_url')
    return MarketSenseDataLoader(db_url)
