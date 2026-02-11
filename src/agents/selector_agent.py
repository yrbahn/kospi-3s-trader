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
        
        # 디버깅: 응답 저장
        from datetime import datetime
        from pathlib import Path
        debug_dir = Path(__file__).parent.parent.parent / "debug"
        debug_dir.mkdir(exist_ok=True)
        debug_file = debug_dir / f"selector_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(f"=== SYSTEM ===\n{system}\n\n")
            f.write(f"=== USER ===\n{user[:500]}...\n\n")
            f.write(f"=== RESPONSE ===\n{response}\n")
        logger.info(f"디버그 응답 저장: {debug_file}")
        
        result = self.parse_json_response(response)

        if result is None:
            logger.warning("포트폴리오 선택 파싱 실패, 빈 포트폴리오 반환")
            logger.warning(f"응답 확인: {debug_file}")
            return {"portfolio": [], "cash_weight": 1.0, "rationale": "파싱 실패"}

        # 비중 검증 (selected_stocks를 portfolio로 변환)
        portfolio = result.get("selected_stocks", result.get("portfolio", []))
        
        # 키 이름 정규화 + DB에서 종목명 조회
        import psycopg2
        normalized_portfolio = []
        
        # DB 연결
        try:
            conn = psycopg2.connect("postgresql://yrbahn@localhost:5432/marketsense")
            cur = conn.cursor()
            
            for stock in portfolio:
                stock_code = stock.get("stock_code", stock.get("code"))
                
                # DB에서 종목명 조회
                cur.execute("SELECT name FROM stocks WHERE ticker = %s", (stock_code,))
                row = cur.fetchone()
                stock_name = row[0] if row else "Unknown"
                
                normalized = {
                    "code": stock_code,
                    "weight": stock.get("weight", 0) / 100.0,  # 백분율 → 비율
                    "name": stock_name
                }
                normalized_portfolio.append(normalized)
            
            cur.close()
            conn.close()
        except Exception as e:
            logger.error(f"종목명 조회 실패: {e}")
            # 실패 시 기본값 사용
            for stock in portfolio:
                normalized = {
                    "code": stock.get("stock_code", stock.get("code")),
                    "weight": stock.get("weight", 0) / 100.0,
                    "name": stock.get("stock_name", stock.get("name", "Unknown"))
                }
                normalized_portfolio.append(normalized)
        
        total_weight = sum(p["weight"] for p in normalized_portfolio)

        if total_weight > 1.0:
            # 비중 정규화
            for p in normalized_portfolio:
                p["weight"] = p["weight"] / total_weight
            total_weight = 1.0

        result["portfolio"] = normalized_portfolio[:self.max_stocks]
        result["cash_weight"] = max(0, 1.0 - total_weight)

        return result
