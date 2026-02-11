#!/usr/bin/env python3
"""
포트폴리오 분석만 수행 (주문 없음)
전날 밤 실행하여 포트폴리오를 미리 구성
"""
import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from src.agents.news_agent import NewsAgent
from src.agents.technical_agent import TechnicalAgent
from src.agents.fundamental_agent import FundamentalAgent
from src.agents.score_agent import ScoreAgent
from src.agents.selector_agent import SelectorAgent
from src.agents.strategy_agent import StrategyAgent
from src.data.data_manager import DataManager
from src.utils.helpers import load_config

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/analyze_only.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# .env 로드
load_dotenv()

PORTFOLIO_FILE = Path(__file__).parent / "portfolio_scheduled.json"


class PortfolioAnalyzer:
    """포트폴리오 분석 전용"""
    
    def __init__(self):
        self.config = load_config()
        self.prompts = self.config.get("prompts", {})
        
        # 에이전트 초기화
        self.news_agent = NewsAgent(self.config, self.prompts)
        self.technical_agent = TechnicalAgent(self.config, self.prompts)
        self.fundamental_agent = FundamentalAgent(self.config, self.prompts)
        self.score_agent = ScoreAgent(self.config, self.prompts)
        self.selector_agent = SelectorAgent(self.config, self.prompts)
        self.strategy_agent = StrategyAgent(self.config, self.prompts)
        
        self.data_manager = DataManager(self.config)
        self.current_strategy = self.prompts.get("initial_strategy", "균형 잡힌 투자")
    
    def _analyze_single_stock(self, ticker: str, data: dict) -> dict:
        """단일 종목 분석 (병렬 처리용)"""
        name = data["name"]
        
        try:
            # 3개 에이전트 분석
            news_analysis = self.news_agent.analyze(ticker, name, data["news_text"])
            tech_summary = data["technical"].get("summary", "데이터 없음")
            tech_analysis = self.technical_agent.analyze(ticker, name, tech_summary)
            fund_analysis = self.fundamental_agent.analyze(ticker, name, data["fundamental_text"])
            
            # 점수 평가
            scores = self.score_agent.score(
                ticker, name,
                news_analysis, tech_analysis, fund_analysis
            )
            
            logger.info(
                f"  [{name}] 재무:{scores['financial_health']} "
                f"성장:{scores['growth_potential']} "
                f"뉴스감성:{scores['news_sentiment']}"
            )
            return scores
        except Exception as e:
            logger.error(f"[{name}] 분석 실패: {e}")
            return None
    
    def analyze_portfolio(self) -> dict:
        """포트폴리오 분석"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        logger.info("🚀 포트폴리오 분석 시작")
        
        today = datetime.now().strftime("%Y%m%d")
        
        # Stage 1: 데이터 수집
        logger.info("📊 Stage 1: 시장 데이터 분석...")
        all_data = self.data_manager.collect_all_data(today)
        
        # Stage 2: 종목 점수 평가 (병렬 처리)
        logger.info("🎯 Stage 2: 종목 점수 평가... (병렬 처리 10개 동시)")
        all_scores = []
        
        # 병렬 처리: 10개 종목을 동시에 분석
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {
                executor.submit(self._analyze_single_stock, ticker, data): ticker
                for ticker, data in all_data.items()
            }
            
            for future in as_completed(future_to_ticker):
                try:
                    result = future.result()
                    if result is not None:
                        all_scores.append(result)
                except Exception as e:
                    ticker = future_to_ticker[future]
                    logger.error(f"[{ticker}] 병렬 처리 실패: {e}")
        
        # Stage 3: 포트폴리오 구성
        logger.info("📋 Stage 3: 포트폴리오 구성...")
        
        # 점수 높은 상위 50종목만 선택
        for score in all_scores:
            total = (
                score.get('financial_health', 0) +
                score.get('growth_potential', 0) +
                score.get('news_sentiment', 0) +
                score.get('news_impact', 0) +
                score.get('price_momentum', 0) +
                (10 - score.get('volatility_risk', 5))
            )
            score['total_score'] = total
        
        top_scores = sorted(all_scores, key=lambda x: x['total_score'], reverse=True)[:50]
        logger.info(f"상위 50종목 선택 (전체 {len(all_scores)}개 중)")
        
        scores_text = ScoreAgent.format_scores_text(top_scores)
        new_portfolio = self.selector_agent.select(
            scores_text, self.current_strategy
        )
        
        # 타임스탬프 추가
        new_portfolio['analyzed_at'] = datetime.now().isoformat()
        new_portfolio['execute_date'] = datetime.now().strftime("%Y-%m-%d")
        
        return new_portfolio
    
    def save_portfolio(self, portfolio: dict):
        """포트폴리오 저장"""
        with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
            json.dump(portfolio, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ 포트폴리오 저장: {PORTFOLIO_FILE}")


def main():
    analyzer = PortfolioAnalyzer()
    
    # 포트폴리오 분석
    portfolio = analyzer.analyze_portfolio()
    
    # 저장
    analyzer.save_portfolio(portfolio)
    
    # 결과 출력
    logger.info("\n" + "=" * 60)
    logger.info("📊 **분석 완료된 포트폴리오**")
    logger.info("=" * 60)
    
    for stock in portfolio.get('portfolio', []):
        logger.info(f"  • {stock['name']}({stock['code']}): {stock['weight']*100:.1f}%")
    
    logger.info(f"  • 현금: {portfolio.get('cash_weight', 0)*100:.1f}%")
    logger.info("")
    logger.info(f"근거: {portfolio.get('rationale', '')}")
    logger.info("=" * 60)
    logger.info("✅ 다음 장 시작 시 execute_portfolio.py 실행")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
