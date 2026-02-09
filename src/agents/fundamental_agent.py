"""재무 분석 에이전트"""
from typing import Dict
from .base_agent import BaseAgent


class FundamentalAgent(BaseAgent):
    """재무제표를 분석하여 리포트 생성"""

    def __init__(self, config: Dict, prompts: Dict):
        super().__init__(config, prompts, "fundamental_agent")

    def analyze(self, stock_code: str, stock_name: str, fundamental_text: str) -> str:
        """재무 분석 리포트 생성"""
        prompt = self._get_prompt("user")
        system = prompt["system"]
        user = prompt["user"].format(
            stock_name=stock_name,
            stock_code=stock_code,
            fundamental_data=fundamental_text,
        )
        return self.call_llm(system, user)
