"""백테스팅 엔진"""
import logging
from typing import Dict, List
from datetime import datetime

from src.data.data_manager import DataManager
from src.agents.news_agent import NewsAgent
from src.agents.technical_agent import TechnicalAgent
from src.agents.fundamental_agent import FundamentalAgent
from src.agents.score_agent import ScoreAgent
from src.agents.selector_agent import SelectorAgent
from src.agents.strategy_agent import StrategyAgent
from src.portfolio.portfolio_manager import PortfolioManager
from src.portfolio.evaluator import Evaluator
from src.utils.helpers import get_trading_weeks

logger = logging.getLogger("3s_trader")


class Backtester:
    """3S-Trader 백테스팅 엔진

    논문의 4단계 파이프라인을 주간 단위로 실행:
    1. 데이터 분석 (Market Analysis)
    2. 종목 점수 평가 (Stock Scoring)
    3. 종목 선택 (Stock Selection)
    4. 전략 반복 개선 (Strategy Iteration)
    """

    def __init__(self, config: Dict, prompts: Dict):
        self.config = config
        self.prompts = prompts

        # 데이터 매니저
        self.data_manager = DataManager(config)

        # 에이전트 초기화
        self.news_agent = NewsAgent(config, prompts)
        self.technical_agent = TechnicalAgent(config, prompts)
        self.fundamental_agent = FundamentalAgent(config, prompts)
        self.score_agent = ScoreAgent(config, prompts)
        self.selector_agent = SelectorAgent(config, prompts)
        self.strategy_agent = StrategyAgent(config, prompts)

        # 포트폴리오 매니저
        self.portfolio_manager = PortfolioManager(config)

        # 초기 전략
        initial_strategy = prompts.get("initial_strategy", "균형 잡힌 접근법")
        self.portfolio_manager.set_initial_strategy(initial_strategy)

    def run(self, start_date: str = None, end_date: str = None) -> Dict:
        """백테스트 실행"""
        start = start_date or self.config["backtest"]["start_date"]
        end = end_date or self.config["backtest"]["end_date"]

        weeks = get_trading_weeks(start, end)
        logger.info(f"백테스트 시작: {start} ~ {end} ({len(weeks)}주)")

        for i, (monday, friday) in enumerate(weeks):
            week_label = f"W{i+1}({monday[:4]}-{monday[4:6]}-{monday[6:]})"
            logger.info(f"\n{'='*60}")
            logger.info(f"📅 {week_label} 처리 중...")
            logger.info(f"{'='*60}")

            try:
                self._process_week(week_label, monday, friday)
            except Exception as e:
                logger.error(f"[{week_label}] 처리 실패: {e}")
                continue

        # 최종 평가
        weekly_returns = self.portfolio_manager.get_weekly_returns()
        metrics = Evaluator.evaluate_all(weekly_returns)
        Evaluator.print_report(metrics)

        # 차트 생성
        if self.portfolio_manager.history:
            Evaluator.plot_cumulative_returns(self.portfolio_manager.history)
            Evaluator.plot_weekly_returns(self.portfolio_manager.history)

        # 결과 저장
        self.portfolio_manager.save_results()

        return metrics

    def _process_week(self, week_label: str, monday: str, friday: str):
        """한 주 처리 (4단계 파이프라인)"""
        # 월요일 전 금요일을 데이터 기준일로 사용
        from datetime import timedelta
        end_dt = datetime.strptime(monday, "%Y%m%d") - timedelta(days=2)
        data_end = end_dt.strftime("%Y%m%d")

        # ═══════════════════════════════════════
        # Stage 1: Market Analysis (데이터 분석)
        # ═══════════════════════════════════════
        logger.info("📊 Stage 1: 시장 데이터 분석...")
        all_data = self.data_manager.collect_all_data(data_end)

        # ═══════════════════════════════════════
        # Stage 2: Stock Scoring (종목 점수 평가)
        # ═══════════════════════════════════════
        logger.info("🎯 Stage 2: 종목 점수 평가...")
        all_scores = []

        for ticker, data in all_data.items():
            name = data["name"]

            # 3개 에이전트 분석
            news_analysis = self.news_agent.analyze(
                ticker, name, data["news_text"]
            )
            tech_summary = data["technical"].get("summary", "데이터 없음")
            tech_analysis = self.technical_agent.analyze(
                ticker, name, tech_summary
            )
            fund_analysis = self.fundamental_agent.analyze(
                ticker, name, data["fundamental_text"]
            )

            # 점수 평가
            scores = self.score_agent.score(
                ticker, name,
                news_analysis, tech_analysis, fund_analysis
            )
            all_scores.append(scores)
            logger.info(
                f"  [{name}] 재무:{scores['financial_health']} 성장:{scores['growth_potential']} "
                f"뉴스:{scores['news_sentiment']} 모멘텀:{scores['price_momentum']}"
            )

        # ═══════════════════════════════════════
        # Stage 3: Stock Selection (종목 선택)
        # ═══════════════════════════════════════
        logger.info("📋 Stage 3: 포트폴리오 구성...")
        scores_text = ScoreAgent.format_scores_text(all_scores)
        portfolio = self.selector_agent.select(
            scores_text, self.portfolio_manager.current_strategy
        )

        selected = portfolio.get("portfolio", [])
        selected_str = [f"{p['name']}({p['weight']:.0%})" for p in selected]
        logger.info(f"  선택 종목: {selected_str}")
        logger.info(f"  현금 비중: {portfolio.get('cash_weight', 0):.0%}")

        # 주간 수익률 계산
        returns = self.data_manager.get_weekly_returns(monday, friday)
        market_avg = self.data_manager.get_market_avg_return(returns)

        # 결과 기록
        portfolio_return = self.portfolio_manager.record_week(
            week_label, portfolio, all_scores, returns, market_avg
        )

        # ═══════════════════════════════════════
        # Stage 4: Strategy Iteration (전략 개선)
        # ═══════════════════════════════════════
        logger.info("🔄 Stage 4: 전략 반복 개선...")
        scores_returns_text = StrategyAgent.format_scores_returns(all_scores, returns)
        history_text = StrategyAgent.format_strategy_history(
            self.portfolio_manager.get_recent_strategy_history()
        )

        new_strategy = self.strategy_agent.refine_strategy(
            current_strategy=self.portfolio_manager.current_strategy,
            portfolio_return=portfolio_return,
            market_avg_return=market_avg,
            scores_and_returns=scores_returns_text,
            strategy_history=history_text,
        )

        self.portfolio_manager.update_strategy(
            new_strategy.get("strategy", self.portfolio_manager.current_strategy)
        )
        logger.info(f"  새 전략: {new_strategy.get('strategy', 'N/A')[:100]}...")
