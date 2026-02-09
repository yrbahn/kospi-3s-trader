"""주가 및 기술적 지표 수집 모듈"""
import pandas as pd
import numpy as np
from pykrx import stock
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

logger = logging.getLogger("3s_trader")


class PriceCollector:
    """KRX에서 주가 데이터를 수집하고 기술적 지표를 계산"""

    def __init__(self, cache_dir: str = "./cache"):
        self.cache_dir = cache_dir

    def get_price_data(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """주가 데이터 조회 (pykrx)"""
        try:
            df = stock.get_market_ohlcv_by_date(start_date, end_date, ticker)
            if df.empty:
                logger.warning(f"[{ticker}] 가격 데이터 없음: {start_date}~{end_date}")
                return pd.DataFrame()
            df.columns = ["open", "high", "low", "close", "volume"]
            return df
        except Exception as e:
            logger.error(f"[{ticker}] 가격 데이터 수집 실패: {e}")
            return pd.DataFrame()

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        if df.empty or len(df) < 20:
            return df

        # SMA
        df["sma_5"] = df["close"].rolling(window=5).mean()
        df["sma_20"] = df["close"].rolling(window=20).mean()

        # RSI (14)
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, np.nan)
        df["rsi_14"] = 100 - (100 / (1 + rs))

        # MACD (12, 26, 9)
        ema_12 = df["close"].ewm(span=12, adjust=False).mean()
        ema_26 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd"] = ema_12 - ema_26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # Bollinger Bands (20, 2)
        df["bb_middle"] = df["close"].rolling(window=20).mean()
        bb_std = df["close"].rolling(window=20).std()
        df["bb_upper"] = df["bb_middle"] + 2 * bb_std
        df["bb_lower"] = df["bb_middle"] - 2 * bb_std

        # ATR (14)
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr_14"] = true_range.rolling(window=14).mean()

        return df

    def get_technical_data(self, ticker: str, end_date: str, lookback_weeks: int = 4) -> Dict:
        """기술적 지표 포함 데이터 조회 (4주 룩백 + 지표 계산용 추가 기간)"""
        end_dt = datetime.strptime(end_date, "%Y%m%d")
        # 지표 계산을 위해 추가 60일 가져옴
        start_dt = end_dt - timedelta(days=lookback_weeks * 7 + 60)
        start_str = start_dt.strftime("%Y%m%d")

        df = self.get_price_data(ticker, start_str, end_date)
        if df.empty:
            return {"ticker": ticker, "data": None, "summary": "데이터 없음"}

        df = self.calculate_indicators(df)

        # 최근 4주 데이터만 추출
        cutoff = end_dt - timedelta(days=lookback_weeks * 7)
        recent = df[df.index >= cutoff.strftime("%Y-%m-%d")]

        if recent.empty:
            return {"ticker": ticker, "data": None, "summary": "데이터 없음"}

        # 텍스트 요약 생성
        latest = recent.iloc[-1]
        first = recent.iloc[0]
        price_change = (latest["close"] - first["close"]) / first["close"] * 100

        summary_lines = [
            f"기간: {recent.index[0].strftime('%Y-%m-%d')} ~ {recent.index[-1].strftime('%Y-%m-%d')}",
            f"시가: {first['open']:,.0f}원 → 종가: {latest['close']:,.0f}원 (변동: {price_change:+.2f}%)",
            f"최고가: {recent['high'].max():,.0f}원 / 최저가: {recent['low'].min():,.0f}원",
            f"평균거래량: {recent['volume'].mean():,.0f}주",
            f"SMA(5): {latest.get('sma_5', 'N/A'):,.0f}원 / SMA(20): {latest.get('sma_20', 'N/A'):,.0f}원",
            f"RSI(14): {latest.get('rsi_14', 'N/A'):.1f}",
            f"MACD: {latest.get('macd', 'N/A'):.2f} / Signal: {latest.get('macd_signal', 'N/A'):.2f}",
            f"볼린저밴드: 상단 {latest.get('bb_upper', 'N/A'):,.0f} / 중간 {latest.get('bb_middle', 'N/A'):,.0f} / 하단 {latest.get('bb_lower', 'N/A'):,.0f}",
            f"ATR(14): {latest.get('atr_14', 'N/A'):,.0f}",
        ]

        # 일별 데이터 요약
        daily_lines = []
        for idx, row in recent.tail(10).iterrows():
            daily_lines.append(
                f"  {idx.strftime('%Y-%m-%d')}: 종가 {row['close']:,.0f}원 (거래량 {row['volume']:,.0f})"
            )

        summary = "\n".join(summary_lines) + "\n\n최근 일별 데이터:\n" + "\n".join(daily_lines)

        return {
            "ticker": ticker,
            "data": recent,
            "summary": summary,
            "latest_close": latest["close"],
        }

    def get_weekly_return(self, ticker: str, monday: str, friday: str) -> Optional[float]:
        """주간 수익률 계산 (월요일 시가 → 금요일 종가)"""
        df = self.get_price_data(ticker, monday, friday)
        if df.empty or len(df) < 2:
            return None
        buy_price = df.iloc[0]["open"]
        sell_price = df.iloc[-1]["close"]
        if buy_price == 0:
            return None
        return (sell_price - buy_price) / buy_price
