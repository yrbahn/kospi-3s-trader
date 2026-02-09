"""재무제표 수집 모듈"""
import pandas as pd
from pykrx import stock
from typing import Dict, Optional
import logging

logger = logging.getLogger("3s_trader")


class FundamentalCollector:
    """KRX/DART에서 재무제표 데이터를 수집"""

    def __init__(self):
        pass

    def get_fundamentals(self, ticker: str, date: str) -> Dict:
        """종목의 기본 재무지표 수집"""
        try:
            # pykrx로 PER, PBR, 배당수익률 조회
            year = date[:4]
            fund = stock.get_market_fundamental_by_date(
                f"{year}0101", date, ticker, freq="m"
            )
            if fund.empty:
                return {"ticker": ticker, "data": None, "summary": "재무 데이터 없음"}

            latest = fund.iloc[-1]
            return {
                "ticker": ticker,
                "data": fund,
                "per": latest.get("PER", None),
                "pbr": latest.get("PBR", None),
                "div_yield": latest.get("DIV", None),
            }
        except Exception as e:
            logger.error(f"[{ticker}] 재무지표 수집 실패: {e}")
            return {"ticker": ticker, "data": None, "summary": "재무 데이터 수집 실패"}

    def get_financial_statements(self, ticker: str, stock_name: str) -> str:
        """재무제표 텍스트 요약 생성 (간이 버전 - pykrx 기반)"""
        try:
            # 최근 연도 PER/PBR/배당수익률
            from datetime import datetime
            today = datetime.now().strftime("%Y%m%d")
            year = today[:4]

            fund = stock.get_market_fundamental_by_date(
                f"{int(year)-1}0101", today, ticker, freq="m"
            )

            if fund.empty:
                return f"[{stock_name}({ticker})] 재무 데이터 없음"

            # 최근 12개월 데이터
            recent = fund.tail(12)
            latest = recent.iloc[-1]

            lines = [
                f"[{stock_name}({ticker})] 재무 지표 요약",
                f"",
                f"최근 PER: {latest.get('PER', 'N/A'):.2f}배" if pd.notna(latest.get('PER')) else "최근 PER: N/A",
                f"최근 PBR: {latest.get('PBR', 'N/A'):.2f}배" if pd.notna(latest.get('PBR')) else "최근 PBR: N/A",
                f"배당수익률: {latest.get('DIV', 'N/A'):.2f}%" if pd.notna(latest.get('DIV')) else "배당수익률: N/A",
            ]

            # PER 추세
            if len(recent) >= 3:
                per_vals = recent["PER"].dropna()
                if len(per_vals) >= 3:
                    lines.append(f"\nPER 추세 (최근 3개월): {per_vals.iloc[-3]:.1f} → {per_vals.iloc[-2]:.1f} → {per_vals.iloc[-1]:.1f}")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"[{ticker}] 재무제표 조회 실패: {e}")
            return f"[{stock_name}({ticker})] 재무 데이터 조회 실패: {e}"
