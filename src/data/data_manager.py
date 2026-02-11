"""데이터 수집 오케스트레이션 모듈 - MarketSense-AI DB 통합"""
import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from pathlib import Path

# MarketSense-AI 경로 추가
MARKETSENSE_PATH = Path(__file__).parent.parent.parent.parent / "marketsense-ai"
if str(MARKETSENSE_PATH) not in sys.path:
    sys.path.insert(0, str(MARKETSENSE_PATH))

# MarketSense-AI 데이터 로더 import
from .data_loader import MarketSenseDataLoader

logger = logging.getLogger("3s_trader")


class DataManager:
    """MarketSense-AI 데이터베이스에서 데이터를 조회하는 매니저"""

    def __init__(self, config: Dict):
        self.config = config
        self.universe = config.get("stocks", {}).get("universe", {})
        self.lookback_weeks = config.get("trading", {}).get("technical_lookback_weeks", 4)
        
        # MarketSense-AI 데이터 로더
        db_url = config.get("data", {}).get("db_url")
        self.data_loader = MarketSenseDataLoader(db_url)
        
        logger.info(f"DataManager 초기화 완료 (MarketSense-AI DB, {len(self.universe)}개 종목)")

    def collect_all_data(self, end_date: str) -> Dict[str, Dict]:
        """모든 종목의 데이터 수집
        
        Args:
            end_date: YYYYMMDD 형식 (예: "20250106")
            
        Returns:
            {ticker: {name, technical, news_text, fundamental_text}, ...}
        """
        logger.info(f"=== 데이터 수집 시작: {end_date} 기준 ===")
        
        # YYYYMMDD -> datetime 변환
        end_dt = datetime.strptime(end_date, "%Y%m%d")
        start_dt = end_dt - timedelta(weeks=self.lookback_weeks)
        
        all_data = {}
        tickers = list(self.universe.keys())
        
        # 전체 데이터 한 번에 로드 (효율적)
        logger.info(f"MarketSense-AI DB에서 {len(tickers)}개 종목 데이터 로딩...")
        universe_data = self.data_loader.get_all_universe_data(tickers, lookback_weeks=self.lookback_weeks)
        
        for ticker, name in self.universe.items():
            logger.info(f"[{name}({ticker})] 데이터 처리 중...")
            
            stock_data = universe_data.get(ticker, {})
            
            # 1. 기술적 데이터 (가격 + 지표)
            tech_data = self._format_technical_data(stock_data.get('prices', []))
            
            # 2. 뉴스 데이터
            news_text = self._format_news_text(ticker, name, stock_data.get('news', []))
            
            # 3. 재무 데이터
            fundamental_text = self._format_fundamental_text(ticker, name, stock_data.get('financials', []))
            
            all_data[ticker] = {
                "name": name,
                "technical": tech_data,
                "news_text": news_text,
                "fundamental_text": fundamental_text,
            }

        logger.info(f"=== 데이터 수집 완료: {len(all_data)}종목 ===")
        return all_data

    def _format_technical_data(self, prices: List[Dict]) -> Dict:
        """가격 데이터를 기술적 지표 포맷으로 변환
        
        Args:
            prices: [{date, open, high, low, close, volume}, ...]
            
        Returns:
            {prices: {...}, indicators: {...}}
        """
        if not prices:
            logger.warning("가격 데이터 없음")
            return {"prices": {}, "indicators": {}}
        
        # 간단한 기술적 지표 계산
        closes = [p.get('close') for p in prices if isinstance(p, dict) and p.get('close')]
        volumes = [p.get('volume') for p in prices if isinstance(p, dict) and p.get('volume')]
        highs = [p.get('high') for p in prices if isinstance(p, dict) and p.get('high')]
        lows = [p.get('low') for p in prices if isinstance(p, dict) and p.get('low')]
        
        if not closes:
            logger.warning("종가 데이터 없음")
            return {"prices": {}, "indicators": {}}
        
        # 최신 가격 정보
        latest = prices[-1] if prices and isinstance(prices[-1], dict) else {}
        
        # SMA 계산
        sma_5 = sum(closes[-5:]) / min(len(closes), 5) if len(closes) >= 5 else closes[-1]
        sma_20 = sum(closes[-20:]) / min(len(closes), 20) if len(closes) >= 20 else closes[-1]
        
        # 변동성 (표준편차)
        avg_price = sum(closes) / len(closes)
        variance = sum((p - avg_price) ** 2 for p in closes) / len(closes)
        volatility = variance ** 0.5
        
        # RSI (간단 버전)
        gains = []
        losses = []
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
            else:
                losses.append(abs(change))
        
        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 1
        rs = avg_gain / avg_loss if avg_loss > 0 else 0
        rsi = 100 - (100 / (1 + rs))
        
        return {
            "prices": {
                "latest_close": latest.get('close', 0) if latest else 0,
                "latest_volume": latest.get('volume', 0) if latest else 0,
                "high": max(highs) if highs else 0,
                "low": min(lows) if lows else 0,
            },
            "indicators": {
                "sma_5": sma_5,
                "sma_20": sma_20,
                "rsi": rsi,
                "volatility": volatility,
                "avg_volume": sum(volumes) / len(volumes) if volumes else 0
            }
        }

    def _format_news_text(self, ticker: str, name: str, news: List[Dict]) -> str:
        """뉴스 리스트를 텍스트로 포맷팅
        
        Args:
            ticker: 종목 코드
            name: 종목명
            news: [{published_at, title, content, url}, ...]
            
        Returns:
            포맷팅된 뉴스 텍스트
        """
        if not news:
            return f"{name}({ticker}) 최근 뉴스 없음"
        
        lines = [f"=== {name}({ticker}) 최근 뉴스 ({len(news)}건) ===\n"]
        
        for i, item in enumerate(news[:10], 1):  # 최대 10개
            pub_date = item['published_at'].strftime("%Y-%m-%d") if isinstance(item['published_at'], datetime) else str(item['published_at'])
            title = item['title']
            content = item.get('content', '')[:200]  # 최대 200자
            
            lines.append(f"{i}. [{pub_date}] {title}")
            if content:
                lines.append(f"   {content}...")
            lines.append("")
        
        return "\n".join(lines)

    def _format_fundamental_text(self, ticker: str, name: str, financials: List[Dict]) -> str:
        """재무제표를 텍스트로 포맷팅
        
        Args:
            ticker: 종목 코드
            name: 종목명
            financials: [{period_end, revenue, operating_income, ...}, ...]
            
        Returns:
            포맷팅된 재무 텍스트
        """
        if not financials:
            return f"{name}({ticker}) 재무 데이터 없음"
        
        lines = [f"=== {name}({ticker}) 재무제표 (최근 {len(financials)}분기) ===\n"]
        
        for i, stmt in enumerate(financials[:4], 1):  # 최대 4분기
            period = stmt.get('period_end', 'N/A')
            if isinstance(period, datetime):
                period = period.strftime("%Y-%m-%d")
            
            revenue = stmt.get('revenue', 0) / 100000000  # 억원 단위
            op_income = stmt.get('operating_income', 0) / 100000000
            net_income = stmt.get('net_income', 0) / 100000000
            
            lines.append(f"{i}. {period}")
            lines.append(f"   매출액: {revenue:,.0f}억원")
            lines.append(f"   영업이익: {op_income:,.0f}억원")
            lines.append(f"   당기순이익: {net_income:,.0f}억원")
            lines.append("")
        
        return "\n".join(lines)

    def get_weekly_returns(self, monday: str, friday: str) -> Dict[str, float]:
        """모든 종목의 주간 수익률 계산
        
        Args:
            monday: YYYYMMDD 형식
            friday: YYYYMMDD 형식
            
        Returns:
            {ticker: return_pct, ...}
        """
        monday_dt = datetime.strptime(monday, "%Y%m%d")
        friday_dt = datetime.strptime(friday, "%Y%m%d")
        
        returns = {}
        
        for ticker in self.universe.keys():
            # 해당 주의 가격 데이터 조회
            prices = self.data_loader.get_price_data(ticker, monday_dt, friday_dt)
            
            if len(prices) < 2:
                continue
            
            # 주초, 주말 종가
            monday_close = prices[0]['close']
            friday_close = prices[-1]['close']
            
            if monday_close and friday_close:
                ret = (friday_close - monday_close) / monday_close
                returns[ticker] = ret
        
        return returns

    def get_market_avg_return(self, returns: Dict[str, float]) -> float:
        """시장 평균 수익률 (유니버스 평균)"""
        if not returns:
            return 0.0
        return sum(returns.values()) / len(returns)
