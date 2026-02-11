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
        
        # 일일 데이터 포맷팅 (최근 20 거래일, 4주)
        daily_lines = ["=== 일일 가격 및 기술적 지표 (최근 4주) ===\n"]
        
        # 전체 평균 거래량 계산
        avg_volume = sum(volumes) / len(volumes) if volumes else 1
        
        for i, price_data in enumerate(prices[-20:]):  # 최근 20일
            date = price_data.get('date', 'N/A')
            if isinstance(date, datetime):
                date = date.strftime("%Y-%m-%d")
            
            open_price = price_data.get('open', 0)
            high_price = price_data.get('high', 0)
            low_price = price_data.get('low', 0)
            close_price = price_data.get('close', 0)
            volume = price_data.get('volume', 0)
            
            # 해당 시점까지의 종가 데이터
            idx = len(prices) - 20 + i
            day_closes = closes[:idx+1]
            
            # 일일 SMA5, SMA20 계산
            day_sma_5 = sum(day_closes[-5:]) / min(len(day_closes), 5) if len(day_closes) >= 1 else close_price
            day_sma_20 = sum(day_closes[-20:]) / min(len(day_closes), 20) if len(day_closes) >= 1 else close_price
            
            # 볼린저밴드 (20일 기준)
            if len(day_closes) >= 20:
                bb_middle = sum(day_closes[-20:]) / 20
                bb_std = (sum((p - bb_middle) ** 2 for p in day_closes[-20:]) / 20) ** 0.5
                bb_upper = bb_middle + (2 * bb_std)
                bb_lower = bb_middle - (2 * bb_std)
            else:
                bb_middle = close_price
                bb_upper = close_price * 1.1
                bb_lower = close_price * 0.9
            
            # 거래량 비율 (평균 대비)
            volume_ratio = (volume / avg_volume * 100) if avg_volume > 0 else 100
            
            # 일일 RSI 계산
            if len(day_closes) > 1:
                day_gains = []
                day_losses = []
                for j in range(1, len(day_closes)):
                    change = day_closes[j] - day_closes[j-1]
                    if change > 0:
                        day_gains.append(change)
                    else:
                        day_losses.append(abs(change))
                
                day_avg_gain = sum(day_gains) / len(day_gains) if day_gains else 0
                day_avg_loss = sum(day_losses) / len(day_losses) if day_losses else 1
                day_rs = day_avg_gain / day_avg_loss if day_avg_loss > 0 else 0
                day_rsi = 100 - (100 / (1 + day_rs))
            else:
                day_rsi = 50.0
            
            daily_lines.append(
                f"{date}: 시가 {open_price:,.0f} 고가 {high_price:,.0f} "
                f"저가 {low_price:,.0f} 종가 {close_price:,.0f}"
            )
            daily_lines.append(
                f"        거래량 {volume:,.0f}주 (평균의 {volume_ratio:.1f}%), RSI {day_rsi:.1f}"
            )
            daily_lines.append(
                f"        SMA5 {day_sma_5:,.0f} SMA20 {day_sma_20:,.0f} "
                f"볼린저 {bb_lower:,.0f}/{bb_middle:,.0f}/{bb_upper:,.0f}"
            )
        
        daily_data = "\n".join(daily_lines)
        
        # 요약 정보
        summary = f"""
{daily_data}

=== 요약 지표 ===
현재가: {latest_close:,.0f}원
최고가: {high:,.0f}원 (4주)
최저가: {low:,.0f}원 (4주)
5일 이동평균: {sma_5:,.0f}원
20일 이동평균: {sma_20:,.0f}원
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
            
            # 손익계산서 (Income Statement)
            revenue = stmt.get('revenue', 0) / 100000000  # 억원 단위
            cost_of_sales = stmt.get('cost_of_sales', 0) / 100000000
            gross_profit = stmt.get('gross_profit', 0) / 100000000
            sg_and_a = stmt.get('selling_general_admin', 0) / 100000000
            op_income = stmt.get('operating_income', 0) / 100000000
            income_before_tax = stmt.get('income_before_tax', 0) / 100000000
            net_income = stmt.get('net_income', 0) / 100000000
            
            # 재무상태표 (Balance Sheet)
            assets = stmt.get('assets', 0) / 100000000
            current_assets = stmt.get('current_assets', 0) / 100000000
            non_current_assets = stmt.get('non_current_assets', 0) / 100000000
            cash = stmt.get('cash_and_equivalents', 0) / 100000000
            inventory = stmt.get('inventory', 0) / 100000000
            ar = stmt.get('accounts_receivable', 0) / 100000000
            liabilities = stmt.get('liabilities', 0) / 100000000
            current_liabilities = stmt.get('current_liabilities', 0) / 100000000
            non_current_liabilities = stmt.get('non_current_liabilities', 0) / 100000000
            equity = stmt.get('equity', 0) / 100000000
            retained_earnings = stmt.get('retained_earnings', 0) / 100000000
            
            # 현금흐름표 (Cash Flow Statement)
            op_cash_flow = stmt.get('operating_cash_flow', 0) / 100000000
            invest_cash_flow = stmt.get('investing_cash_flow', 0) / 100000000
            finance_cash_flow = stmt.get('financing_cash_flow', 0) / 100000000
            cash_increase = stmt.get('cash_increase', 0) / 100000000
            
            lines.append(f"{i}. {period}")
            lines.append(f"   [손익계산서]")
            lines.append(f"   - 매출액: {revenue:,.0f}억원")
            if cost_of_sales != 0:
                lines.append(f"   - 매출원가: {cost_of_sales:,.0f}억원")
            if gross_profit != 0:
                lines.append(f"   - 매출총이익: {gross_profit:,.0f}억원")
            if sg_and_a != 0:
                lines.append(f"   - 판매관리비: {sg_and_a:,.0f}억원")
            lines.append(f"   - 영업이익: {op_income:,.0f}억원")
            if income_before_tax != 0:
                lines.append(f"   - 세전순이익: {income_before_tax:,.0f}억원")
            lines.append(f"   - 당기순이익: {net_income:,.0f}억원")
            
            if assets > 0 or equity > 0 or liabilities > 0:
                lines.append(f"   [재무상태표]")
                lines.append(f"   - 자산총계: {assets:,.0f}억원")
                if current_assets > 0:
                    lines.append(f"     (유동: {current_assets:,.0f}, 비유동: {non_current_assets:,.0f})")
                if cash > 0:
                    lines.append(f"   - 현금: {cash:,.0f}억원")
                if inventory > 0:
                    lines.append(f"   - 재고: {inventory:,.0f}억원")
                if ar > 0:
                    lines.append(f"   - 매출채권: {ar:,.0f}억원")
                lines.append(f"   - 부채총계: {liabilities:,.0f}억원")
                if current_liabilities > 0:
                    lines.append(f"     (유동: {current_liabilities:,.0f}, 비유동: {non_current_liabilities:,.0f})")
                lines.append(f"   - 자본총계: {equity:,.0f}억원")
                if retained_earnings > 0:
                    lines.append(f"   - 이익잉여금: {retained_earnings:,.0f}억원")
            
            if op_cash_flow != 0 or invest_cash_flow != 0 or finance_cash_flow != 0:
                lines.append(f"   [현금흐름표]")
                lines.append(f"   - 영업활동: {op_cash_flow:,.0f}억원")
                lines.append(f"   - 투자활동: {invest_cash_flow:,.0f}억원")
                lines.append(f"   - 재무활동: {finance_cash_flow:,.0f}억원")
                if cash_increase != 0:
                    lines.append(f"   - 현금증감: {cash_increase:,.0f}억원")
            
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
