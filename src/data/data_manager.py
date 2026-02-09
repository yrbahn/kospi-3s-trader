"""데이터 수집 오케스트레이션 모듈"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

from .price_collector import PriceCollector
from .news_collector import NewsCollector
from .fundamental_collector import FundamentalCollector

logger = logging.getLogger("3s_trader")


class DataManager:
    """모든 데이터 수집을 조율하는 매니저"""

    def __init__(self, config: Dict):
        self.config = config
        self.price_collector = PriceCollector(config.get("data", {}).get("cache_dir", "./cache"))
        self.news_collector = NewsCollector()
        self.fundamental_collector = FundamentalCollector()
        self.universe = config.get("stocks", {}).get("universe", {})
        self.lookback_weeks = config.get("trading", {}).get("technical_lookback_weeks", 4)

    def collect_all_data(self, end_date: str) -> Dict[str, Dict]:
        """모든 종목의 데이터 수집"""
        logger.info(f"=== 데이터 수집 시작: {end_date} 기준 ===")
        all_data = {}

        for ticker, name in self.universe.items():
            logger.info(f"[{name}({ticker})] 데이터 수집 중...")

            # 기술적 데이터
            tech_data = self.price_collector.get_technical_data(
                ticker, end_date, self.lookback_weeks
            )

            # 뉴스 데이터
            news_list = self.news_collector.get_news(ticker, end_date, days=7)
            news_text = self.news_collector.format_news_text(ticker, name, news_list)

            # 재무 데이터
            fund_text = self.fundamental_collector.get_financial_statements(ticker, name)

            all_data[ticker] = {
                "name": name,
                "technical": tech_data,
                "news_text": news_text,
                "fundamental_text": fund_text,
            }

        logger.info(f"=== 데이터 수집 완료: {len(all_data)}종목 ===")
        return all_data

    def get_weekly_returns(self, monday: str, friday: str) -> Dict[str, float]:
        """모든 종목의 주간 수익률 계산"""
        returns = {}
        for ticker, name in self.universe.items():
            ret = self.price_collector.get_weekly_return(ticker, monday, friday)
            if ret is not None:
                returns[ticker] = ret
        return returns

    def get_market_avg_return(self, returns: Dict[str, float]) -> float:
        """시장 평균 수익률 (유니버스 평균)"""
        if not returns:
            return 0.0
        return sum(returns.values()) / len(returns)
