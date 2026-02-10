"""MarketSense-AI 데이터베이스 통합 로더

kospi-3s-trader가 marketsense-ai의 PostgreSQL 데이터베이스를 사용하도록 통합
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

# MarketSense-AI 모듈 import
MARKETSENSE_PATH = Path(__file__).parent.parent.parent.parent / "marketsense-ai"
sys.path.insert(0, str(MARKETSENSE_PATH))

from src.storage.database import Database
from src.storage.models import Stock, PriceData, FinancialStatement, NewsData
from sqlalchemy import and_

logger = logging.getLogger(__name__)


class MarketSenseDataLoader:
    """MarketSense-AI 데이터베이스에서 데이터 로드"""
    
    def __init__(self, db_url: str = None):
        """
        Args:
            db_url: PostgreSQL 연결 URL (None이면 환경변수 사용)
        """
        if db_url is None:
            db_url = os.getenv("DATABASE_URL", "postgresql://yrbahn@localhost:5432/marketsense")
        
        self.db = Database(db_url)
        logger.info(f"MarketSense-AI DB 연결: {db_url}")
    
    def get_stock_info(self, ticker: str) -> Optional[Dict]:
        """종목 기본 정보 조회
        
        Args:
            ticker: 종목 코드
            
        Returns:
            {name, market_cap, sector, ...}
        """
        with self.db.get_session() as session:
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                logger.warning(f"{ticker} 종목 정보 없음")
                return None
            
            return {
                'ticker': stock.ticker,
                'name': stock.name,
                'market_cap': stock.market_cap,
                'sector': stock.sector,
                'industry': stock.industry
            }
    
    def get_price_data(self, ticker: str, start_date: datetime, end_date: datetime = None) -> List[Dict]:
        """가격 데이터 조회
        
        Args:
            ticker: 종목 코드
            start_date: 시작일
            end_date: 종료일 (None이면 오늘)
            
        Returns:
            [{date, open, high, low, close, volume}, ...]
        """
        if end_date is None:
            end_date = datetime.now()
        
        with self.db.get_session() as session:
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                logger.warning(f"{ticker} 종목 없음")
                return []
            
            prices = session.query(PriceData).filter(
                and_(
                    PriceData.stock_id == stock.id,
                    PriceData.date >= start_date,
                    PriceData.date <= end_date
                )
            ).order_by(PriceData.date).all()
            
            return [
                {
                    'date': p.date,
                    'open': p.open,
                    'high': p.high,
                    'low': p.low,
                    'close': p.close,
                    'volume': p.volume
                }
                for p in prices
            ]
    
    def get_financial_statements(self, ticker: str, lookback_quarters: int = 8) -> List[Dict]:
        """재무제표 데이터 조회
        
        Args:
            ticker: 종목 코드
            lookback_quarters: 몇 분기 조회할지
            
        Returns:
            [{period_end, revenue, operating_income, net_income, ...}, ...]
        """
        with self.db.get_session() as session:
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                logger.warning(f"{ticker} 종목 없음")
                return []
            
            statements = session.query(FinancialStatement).filter(
                and_(
                    FinancialStatement.stock_id == stock.id,
                    FinancialStatement.statement_type == 'income',
                    FinancialStatement.period_type == 'quarterly'
                )
            ).order_by(FinancialStatement.period_end.desc()).limit(lookback_quarters).all()
            
            results = []
            for stmt in statements:
                data = stmt.raw_data
                results.append({
                    'period_end': stmt.period_end,
                    'fiscal_quarter': stmt.fiscal_quarter,
                    'revenue': data.get('매출액', 0),
                    'operating_income': data.get('영업이익', 0),
                    'net_income': data.get('당기순이익', 0),
                    'assets': data.get('자산총계', 0),
                    'equity': data.get('자본총계', 0),
                    'liabilities': data.get('부채총계', 0)
                })
            
            return results
    
    def get_news(self, ticker: str, lookback_days: int = 30) -> List[Dict]:
        """뉴스 데이터 조회
        
        Args:
            ticker: 종목 코드
            lookback_days: 몇 일 전까지 조회할지
            
        Returns:
            [{published_at, title, content, url}, ...]
        """
        start_date = datetime.now() - timedelta(days=lookback_days)
        
        with self.db.get_session() as session:
            stock = session.query(Stock).filter_by(ticker=ticker).first()
            if not stock:
                logger.warning(f"{ticker} 종목 없음")
                return []
            
            news = session.query(NewsData).filter(
                and_(
                    NewsData.stock_id == stock.id,
                    NewsData.published_at >= start_date
                )
            ).order_by(NewsData.published_at.desc()).all()
            
            return [
                {
                    'published_at': n.published_at,
                    'title': n.title,
                    'content': n.content,
                    'url': n.url
                }
                for n in news
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
            logger.info(f"{ticker} 데이터 로딩...")
            
            try:
                result[ticker] = {
                    'info': self.get_stock_info(ticker),
                    'prices': self.get_price_data(ticker, start_date),
                    'financials': self.get_financial_statements(ticker),
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
