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
        
        # universe 로드 (딕셔너리 또는 파일)
        stocks_config = config.get("stocks", {})
        universe_file = stocks_config.get("universe_file")
        
        if universe_file:
            # JSON 파일에서 종목 리스트 로드
            file_path = Path(__file__).parent.parent.parent / universe_file
            with open(file_path, 'r') as f:
                tickers = json.load(f)
            # 리스트 → 딕셔너리 변환 (ticker: name은 나중에 DB에서 조회)
            self.universe = {ticker: None for ticker in tickers}
            logger.info(f"universe 파일 로드: {universe_file} ({len(tickers)}개 종목)")
        else:
            self.universe = stocks_config.get("universe", {})
        
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
        
        result = {
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
        
        # summary 텍스트 생성 (TechnicalAgent용)
        latest_close = result["prices"]["latest_close"]
        latest_volume = result["prices"]["latest_volume"]
        high = result["prices"]["high"]
        low = result["prices"]["low"]
        sma_5 = result["indicators"]["sma_5"]
        sma_20 = result["indicators"]["sma_20"]
        rsi = result["indicators"]["rsi"]
        volatility = result["indicators"]["volatility"]
        avg_volume = result["indicators"]["avg_volume"]
        
        summary = f"""
=== 가격 정보 ===
현재가: {latest_close:,.0f}원
거래량: {latest_volume:,.0f}주
최고가: {high:,.0f}원
최저가: {low:,.0f}원

=== 이동평균 ===
5일 평균: {sma_5:,.0f}원
20일 평균: {sma_20:,.0f}원
SMA5/SMA20: {(sma_5/sma_20*100):.2f}%

=== 모멘텀 지표 ===
RSI(14): {rsi:.2f}
변동성: {volatility:,.0f}원
평균 거래량: {avg_volume:,.0f}주
        """.strip()
        
        result["summary"] = summary
        return result

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
            pub_date = item.get('published_at', 'N/A')
            if isinstance(pub_date, datetime):
                pub_date = pub_date.strftime("%Y-%m-%d")
            else:
                pub_date = str(pub_date)
            
            title = item.get('title', '제목 없음')
            content = item.get('content') or ''  # None 처리
            content = content[:200] if content else ''  # 최대 200자
            
            lines.append(f"{i}. [{pub_date}] {title}")
            if content:
                lines.append(f"   {content}...")
            lines.append("")
        
        return "\n".join(lines)

    def _get_common_stock_ticker(self, ticker: str) -> str:
        """우선주인 경우 보통주 코드로 변환
        
        Args:
            ticker: 종목 코드
            
        Returns:
            보통주 코드 (우선주가 아니면 원본 반환)
        """
        # 우선주 판단: 마지막 자리가 5인 경우
        if ticker.endswith('5') and len(ticker) == 6:
            # 5 -> 0으로 변환 (예: 005385 -> 005380)
            return ticker[:-1] + '0'
        return ticker
    
    def _format_fundamental_text(self, ticker: str, name: str, financials: List[Dict]) -> str:
        """재무제표를 텍스트로 포맷팅
        
        Args:
            ticker: 종목 코드
            name: 종목명
            financials: [{period_end, revenue, operating_income, ...}, ...]
            
        Returns:
            포맷팅된 재무 텍스트
        """
        # 우선주인 경우 보통주 데이터 조회
        original_ticker = ticker
        if ticker.endswith('5') and len(ticker) == 6 and not financials:
            common_ticker = self._get_common_stock_ticker(ticker)
            logger.info(f"우선주 {ticker} → 보통주 {common_ticker} 재무 데이터 조회")
            # MarketSense-AI DB에서 보통주 재무 데이터 가져오기
            common_financials = self.data_loader.get_financial_statements(common_ticker, lookback_quarters=4)
            if common_financials:
                financials = common_financials
                name = f"{name} (보통주 재무)"
        
        if not financials:
            return f"{name}({original_ticker}) 재무 데이터 없음"
        
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
