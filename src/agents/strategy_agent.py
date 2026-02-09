"""전략 반복 개선 에이전트"""
from typing import Dict, List
from .base_agent import BaseAgent
import logging

logger = logging.getLogger("3s_trader")


class StrategyAgent(BaseAgent):
    """과거 성과를 분석하여 전략을 반복적으로 개선"""

    def __init__(self, config: Dict, prompts: Dict):
        super().__init__(config, prompts, "strategy_agent")
        self.history_length = config.get("trading", {}).get("strategy_history_length", 10)

    def refine_strategy(
        self,
        current_strategy: str,
        portfolio_return: float,
        market_avg_return: float,
        scores_and_returns: str,
        strategy_history: str,
    ) -> Dict:
        """전략 개선 수행"""
        prompt = self._get_prompt("user")
        system = prompt["system"]
        user = prompt["user"].format(
            current_strategy=current_strategy,
            portfolio_return=f"{portfolio_return * 100:.2f}",
            market_avg_return=f"{market_avg_return * 100:.2f}",
            scores_and_returns=scores_and_returns,
            strategy_history=strategy_history,
        )

        response = self.call_llm(system, user)
        result = self.parse_json_response(response)

        if result is None:
            logger.warning("전략 개선 파싱 실패, 기존 전략 유지")
            return {
                "strategy": current_strategy,
                "preferred_dimensions": [],
                "avoid_dimensions": [],
                "analysis": "전략 분석 실패",
            }

        return result

    @staticmethod
    def format_scores_returns(scores: list, returns: Dict[str, float]) -> str:
        """점수와 수익률을 매칭하여 텍스트 생성"""
        lines = []
        for s in scores:
            code = s["code"]
            ret = returns.get(code, 0)
            lines.append(
                f"[{s['name']}({code})] "
                f"수익률: {ret*100:+.2f}% | "
                f"재무:{s['financial_health']} 성장:{s['growth_potential']} "
                f"뉴스감성:{s['news_sentiment']} 뉴스영향:{s['news_impact']} "
                f"모멘텀:{s['price_momentum']} 변동성:{s['volatility_risk']}"
            )
        return "\n".join(lines)

    @staticmethod
    def format_strategy_history(history: list) -> str:
        """전략 이력 포맷"""
        if not history:
            return "전략 이력 없음 (첫 주)"
        lines = []
        for i, h in enumerate(history[-10:], 1):
            lines.append(
                f"[{h['week']}] 전략: {h['strategy']}\n"
                f"  포트폴리오 수익률: {h['portfolio_return']*100:+.2f}% / "
                f"시장 평균: {h['market_avg_return']*100:+.2f}%"
            )
        return "\n".join(lines)
