"""LLM 에이전트 기본 클래스"""
import json
import logging
from typing import Dict, Any, Optional
from openai import OpenAI

logger = logging.getLogger("3s_trader")


class BaseAgent:
    """모든 LLM 에이전트의 기본 클래스"""

    def __init__(self, config: Dict, prompts: Dict, agent_name: str):
        self.config = config
        self.prompts = prompts
        self.agent_name = agent_name
        self.llm_config = config.get("llm", {})
        self.client = OpenAI()
        self.model = self.llm_config.get("model", "gpt-4o")
        self.temperature = self.llm_config.get("temperature", 0.3)
        self.max_tokens = self.llm_config.get("max_tokens", 4096)

    def _get_prompt(self, key: str) -> Dict[str, str]:
        """에이전트별 프롬프트 조회"""
        agent_prompts = self.prompts.get(self.agent_name, {})
        return {
            "system": agent_prompts.get("system", ""),
            "user": agent_prompts.get("user", ""),
        }

    def call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """LLM API 호출"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.choices[0].message.content
            logger.debug(f"[{self.agent_name}] LLM 응답 길이: {len(content)}")
            return content
        except Exception as e:
            logger.error(f"[{self.agent_name}] LLM 호출 실패: {e}")
            return f"LLM 호출 실패: {e}"

    def parse_json_response(self, response: str) -> Optional[Dict]:
        """LLM 응답에서 JSON 파싱"""
        try:
            # ```json ... ``` 블록 추출
            if "```json" in response:
                start = response.index("```json") + 7
                end = response.index("```", start)
                json_str = response[start:end].strip()
            elif "```" in response:
                start = response.index("```") + 3
                end = response.index("```", start)
                json_str = response[start:end].strip()
            else:
                # JSON 객체 직접 찾기
                start = response.index("{")
                end = response.rindex("}") + 1
                json_str = response[start:end]

            return json.loads(json_str)
        except (ValueError, json.JSONDecodeError) as e:
            logger.error(f"[{self.agent_name}] JSON 파싱 실패: {e}\n응답: {response[:200]}")
            return None
