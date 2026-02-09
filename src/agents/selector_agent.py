"""포트폴리오 선택 에이전트"""
from typing import Dict, List, Optional
from .base_agent import BaseAgent
import logging

logger = logging.getLogger("3s_trader")


class SelectorAgent(BaseAgent):
    """점수 + 전략을 기반으로 포트폴리오 구성"""

    def __init__(self, config: Dict, prompts: Dict):
        super().__init__(config, prompts, "selector_agent")
        self.max_stocks = config.get("trading", {}).get("max_portfolio_stocks", 5)

    def select(self, all_scores_text: str, strategy: str) -> Dict:
        """포트폴리오 선택 수행"""
        prompt = self._get_prompt("user")
        system = prompt["system"]
        user = prompt["user"].format(
            strategy=strategy,
            all_scores=all_scores_text,
        )

        response = self.call_llm(system, user)
        result = self.parse_json_response(response)

        if result is None:
            logger.warning("포트폴리오 선택 파싱 실패, 빈 포트폴리오 반환")
            return {"portfolio": [], "cash_weight": 1.0, "rationale": "파싱 실패"}

        # 비중 검증
        portfolio = result.get("portfolio", [])
        total_weight = sum(p.get("weight", 0) for p in portfolio)

        if total_weight > 1.0:
            # 비중 정규화
            for p in portfolio:
                p["weight"] = p["weight"] / total_weight
            total_weight = 1.0

        result["portfolio"] = portfolio[:self.max_stocks]
        result["cash_weight"] = max(0, 1.0 - total_weight)

        return result
