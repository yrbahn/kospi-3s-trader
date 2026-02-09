"""포트폴리오 관리 모듈"""
import json
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("3s_trader")


class PortfolioManager:
    """포트폴리오 구성, 추적, 기록 관리"""

    def __init__(self, config: Dict):
        self.config = config
        self.initial_capital = config.get("backtest", {}).get("initial_capital", 100_000_000)
        self.current_capital = self.initial_capital
        self.history: List[Dict] = []  # 주간 포트폴리오 이력
        self.strategy_history: List[Dict] = []  # 전략 이력
        self.current_strategy: str = ""
        self.cumulative_returns: List[float] = []  # 누적 수익률

    def set_initial_strategy(self, strategy: str):
        """초기 전략 설정"""
        self.current_strategy = strategy

    def record_week(
        self,
        week_label: str,
        portfolio: Dict,
        scores: List[Dict],
        returns: Dict[str, float],
        market_avg_return: float,
    ) -> float:
        """주간 결과 기록 및 포트폴리오 수익률 계산"""
        # 포트폴리오 수익률 계산
        portfolio_return = 0.0
        positions = portfolio.get("portfolio", [])
        for pos in positions:
            code = pos.get("code", "")
            weight = pos.get("weight", 0)
            stock_return = returns.get(code, 0)
            portfolio_return += weight * stock_return

        # 자본 업데이트
        self.current_capital *= (1 + portfolio_return)

        # 누적 수익률
        if not self.cumulative_returns:
            cum_return = portfolio_return
        else:
            cum_return = (1 + self.cumulative_returns[-1]) * (1 + portfolio_return) - 1
        self.cumulative_returns.append(cum_return)

        # 이력 저장
        record = {
            "week": week_label,
            "portfolio": portfolio,
            "portfolio_return": portfolio_return,
            "market_avg_return": market_avg_return,
            "cumulative_return": cum_return,
            "capital": self.current_capital,
            "strategy": self.current_strategy,
            "scores": scores,
        }
        self.history.append(record)

        # 전략 이력 저장
        self.strategy_history.append({
            "week": week_label,
            "strategy": self.current_strategy,
            "portfolio_return": portfolio_return,
            "market_avg_return": market_avg_return,
        })

        logger.info(
            f"[{week_label}] 포트폴리오 수익률: {portfolio_return*100:+.2f}% | "
            f"시장 평균: {market_avg_return*100:+.2f}% | "
            f"누적: {cum_return*100:+.2f}% | "
            f"자본: {self.current_capital:,.0f}원"
        )

        return portfolio_return

    def update_strategy(self, new_strategy: str):
        """전략 업데이트"""
        self.current_strategy = new_strategy

    def get_recent_strategy_history(self, n: int = 10) -> List[Dict]:
        """최근 N주간 전략 이력"""
        return self.strategy_history[-n:]

    def get_weekly_returns(self) -> List[float]:
        """주간 수익률 리스트"""
        return [h["portfolio_return"] for h in self.history]

    def save_results(self, output_dir: str = "./results"):
        """결과 저장"""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 이력 저장 (scores의 DataFrame 제거)
        clean_history = []
        for h in self.history:
            clean = {k: v for k, v in h.items() if k != "scores"}
            clean["scores_summary"] = [
                {k: v for k, v in s.items() if k != "data"}
                for s in h.get("scores", [])
            ]
            clean_history.append(clean)

        with open(os.path.join(output_dir, f"history_{timestamp}.json"), "w", encoding="utf-8") as f:
            json.dump(clean_history, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"결과 저장: {output_dir}/history_{timestamp}.json")
