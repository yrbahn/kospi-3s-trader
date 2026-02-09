"""종목 점수 평가 에이전트"""
from typing import Dict, Optional
from .base_agent import BaseAgent
import logging

logger = logging.getLogger("3s_trader")

# 기본 점수 (LLM 실패 시)
DEFAULT_SCORES = {
    "financial_health": 5,
    "growth_potential": 5,
    "news_sentiment": 5,
    "news_impact": 5,
    "price_momentum": 5,
    "volatility_risk": 5,
    "rationale": "LLM 응답 파싱 실패로 기본값 사용",
}

SCORE_DIMENSIONS = [
    "financial_health",
    "growth_potential",
    "news_sentiment",
    "news_impact",
    "price_momentum",
    "volatility_risk",
]


class ScoreAgent(BaseAgent):
    """종목별 6차원 점수 평가"""

    def __init__(self, config: Dict, prompts: Dict):
        super().__init__(config, prompts, "score_agent")

    def score(
        self,
        stock_code: str,
        stock_name: str,
        news_analysis: str,
        technical_analysis: str,
        fundamental_analysis: str,
    ) -> Dict:
        """6차원 점수 평가 수행"""
        prompt = self._get_prompt("user")
        system = prompt["system"]
        user = prompt["user"].format(
            stock_name=stock_name,
            stock_code=stock_code,
            news_analysis=news_analysis,
            technical_analysis=technical_analysis,
            fundamental_analysis=fundamental_analysis,
        )

        response = self.call_llm(system, user)
        scores = self.parse_json_response(response)

        if scores is None:
            logger.warning(f"[{stock_name}] 점수 파싱 실패, 기본값 사용")
            return {**DEFAULT_SCORES, "code": stock_code, "name": stock_name}

        # 점수 범위 검증 (1~10)
        for dim in SCORE_DIMENSIONS:
            if dim in scores:
                scores[dim] = max(1, min(10, int(scores[dim])))
            else:
                scores[dim] = 5

        scores["code"] = stock_code
        scores["name"] = stock_name
        return scores

    @staticmethod
    def format_scores_text(all_scores: list) -> str:
        """모든 종목 점수를 텍스트로 포맷"""
        lines = []
        for s in all_scores:
            lines.append(
                f"[{s['name']}({s['code']})] "
                f"재무건전성:{s['financial_health']} "
                f"성장잠재력:{s['growth_potential']} "
                f"뉴스감성:{s['news_sentiment']} "
                f"뉴스영향력:{s['news_impact']} "
                f"가격모멘텀:{s['price_momentum']} "
                f"변동성리스크:{s['volatility_risk']}"
            )
        return "\n".join(lines)
