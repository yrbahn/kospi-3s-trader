"""한국 뉴스 수집 모듈 (네이버 금융 뉴스)"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, List
import logging
import time

logger = logging.getLogger("3s_trader")


class NewsCollector:
    """네이버 금융에서 종목 뉴스를 수집"""

    NAVER_NEWS_URL = "https://finance.naver.com/item/news_news.naver"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

    def get_news(self, ticker: str, end_date: str, days: int = 7) -> List[Dict]:
        """네이버 금융에서 종목 뉴스 수집"""
        end_dt = datetime.strptime(end_date, "%Y%m%d")
        start_dt = end_dt - timedelta(days=days)
        news_list = []

        try:
            for page in range(1, 4):  # 최대 3페이지
                params = {
                    "code": ticker,
                    "page": page,
                    "sm": "title_entity_id.basic",
                    "clusterId": "",
                }
                resp = self.session.get(self.NAVER_NEWS_URL, params=params, timeout=10)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                rows = soup.select("table.type5 tbody tr")
                for row in rows:
                    title_tag = row.select_one("td.title a")
                    date_tag = row.select_one("td.date")
                    if not title_tag or not date_tag:
                        continue

                    title = title_tag.get_text(strip=True)
                    date_str = date_tag.get_text(strip=True)

                    try:
                        news_date = datetime.strptime(date_str, "%Y.%m.%d %H:%M")
                    except ValueError:
                        continue

                    if news_date < start_dt:
                        continue
                    if news_date > end_dt:
                        continue

                    news_list.append({
                        "title": title,
                        "date": date_str,
                        "source": "네이버금융",
                    })

                time.sleep(0.5)  # 요청 간격

        except Exception as e:
            logger.error(f"[{ticker}] 뉴스 수집 실패: {e}")

        logger.info(f"[{ticker}] 뉴스 {len(news_list)}건 수집")
        return news_list

    def format_news_text(self, ticker: str, stock_name: str, news_list: List[Dict]) -> str:
        """뉴스 목록을 텍스트로 포맷"""
        if not news_list:
            return f"[{stock_name}({ticker})] 최근 뉴스 없음"

        lines = [f"[{stock_name}({ticker})] 최근 뉴스 ({len(news_list)}건):\n"]
        for i, news in enumerate(news_list[:20], 1):  # 최대 20건
            lines.append(f"{i}. [{news['date']}] {news['title']}")

        return "\n".join(lines)
