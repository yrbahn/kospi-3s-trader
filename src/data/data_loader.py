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
            
            # 재무제표 조회
            results = session.execute(
                text("""
                SELECT period_end, fiscal_quarter, raw_data
                FROM financial_statements
                WHERE stock_id = :stock_id
                  AND statement_type = 'income'
                  AND period_type = 'quarterly'
                ORDER BY period_end DESC
                LIMIT :limit
                """),
                {"stock_id": stock_id, "limit": lookback_quarters}
            ).fetchall()

            statements = []
            for row in results:
                data = row[2] or {}  # raw_data (JSON)

                # DB에서 직접 가져오는 값
                revenue = data.get('revenue', 0) or 0
                cost_of_sales = data.get('cost_of_revenue', 0) or 0
                gross_profit = data.get('gross_profit', 0) or 0
                sga = data.get('sga_expenses', 0) or 0
                operating_income = data.get('operating_income', 0) or 0
                net_income = data.get('net_income', 0) or 0
                total_assets = data.get('total_assets', 0) or 0
                current_assets = data.get('current_assets', 0) or 0
                total_liabilities = data.get('total_liabilities', 0) or 0
                current_liabilities = data.get('current_liabilities', 0) or 0
                total_equity = data.get('total_equity', 0) or 0
                op_cf = data.get('operating_cash_flow', 0) or 0
                inv_cf = data.get('investing_cash_flow', 0) or 0
                fin_cf = data.get('financing_cash_flow', 0) or 0
                depreciation = data.get('depreciation_amortization', 0) or 0

                # DB에 없는 항목 계산
                non_current_assets = total_assets - current_assets
                non_current_liabilities = total_liabilities - current_liabilities
                income_before_tax = net_income + (data.get('income_tax', 0) or 0) if data.get('income_tax') else 0
                cash_increase = op_cf + inv_cf + fin_cf
                free_cash_flow = op_cf + inv_cf  # FCF = 영업CF + 투자CF (capex 포함)

                statements.append({
                    'period_end': row[0],
                    'fiscal_quarter': row[1],
                    # 손익계산서 (Income Statement)
                    'revenue': revenue,
                    'cost_of_sales': cost_of_sales,
                    'gross_profit': gross_profit,
                    'selling_general_admin': sga,
                    'operating_income': operating_income,
                    'income_before_tax': income_before_tax,
                    'net_income': net_income,
                    # 재무상태표 (Balance Sheet)
                    'assets': total_assets,
                    'current_assets': current_assets,
                    'non_current_assets': non_current_assets,
                    'liabilities': total_liabilities,
                    'current_liabilities': current_liabilities,
                    'non_current_liabilities': non_current_liabilities,
                    'equity': total_equity,
                    # 현금흐름표 (Cash Flow Statement)
                    'operating_cash_flow': op_cf,
                    'investing_cash_flow': inv_cf,
                    'financing_cash_flow': fin_cf,
                    'cash_increase': cash_increase,
                    'free_cash_flow': free_cash_flow,
                    'depreciation_amortization': depreciation,
                    # 파생 지표
                    'ebitda': data.get('ebitda', 0) or 0,
                    'eps': data.get('eps_basic', 0) or 0,
                    'eps_diluted': data.get('eps_diluted', 0) or 0,
                    'bps': data.get('bps', 0) or 0,
                    'shares_outstanding': data.get('shares_outstanding', 0) or 0,
                    'roa': data.get('roa', 0) or 0,
                    'roe': data.get('roe', 0) or 0,
                    'gross_margin': data.get('gross_margin', 0) or 0,
                    'operating_margin': data.get('operating_margin', 0) or 0,
                    'net_margin': data.get('net_margin', 0) or 0,
                    'debt_ratio': data.get('debt_ratio', 0) or 0,
                    'current_ratio': data.get('current_ratio', 0) or 0,
                    'equity_ratio': data.get('equity_ratio', 0) or 0,
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
    
    def get_blog_posts(self, ticker: str, lookback_days: int = 30) -> List[Dict]:
        """블로그 데이터 조회

        Args:
            ticker: 종목 코드
            lookback_days: 몇 일 전까지 조회할지

        Returns:
            [{post_date, title, description, blogger_name, quality_score}, ...]
        """
        start_date = datetime.now() - timedelta(days=lookback_days)

        with self.get_session() as session:
            stock_id_result = session.execute(
                text("SELECT id FROM stocks WHERE ticker = :ticker"),
                {"ticker": ticker}
            ).fetchone()

            if not stock_id_result:
                return []

            stock_id = stock_id_result[0]

            results = session.execute(
                text("""
                SELECT post_date, title, description, blogger_name, quality_score
                FROM blog_posts
                WHERE stock_id = :stock_id
                  AND post_date >= :start_date
                ORDER BY post_date DESC
                """),
                {"stock_id": stock_id, "start_date": start_date}
            ).fetchall()

            return [
                {
                    'post_date': row[0],
                    'title': row[1],
                    'description': row[2],
                    'blogger_name': row[3],
                    'quality_score': row[4]
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
                    'news': [...],
                    'blogs': [...]
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
                    'news': self.get_news(ticker, lookback_days=lookback_weeks*7),
                    'blogs': self.get_blog_posts(ticker, lookback_days=lookback_weeks*7)
                }
            except Exception as e:
                logger.error(f"{ticker} 데이터 로딩 실패: {e}")
                result[ticker] = {
                    'info': None,
                    'prices': [],
                    'financials': [],
                    'news': [],
                    'blogs': []
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
