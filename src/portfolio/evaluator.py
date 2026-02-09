"""성과 평가 모듈"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from typing import List, Dict, Optional
import os
import logging

# 한글 폰트 설정
matplotlib.rcParams["font.family"] = "AppleGothic"
matplotlib.rcParams["axes.unicode_minus"] = False

logger = logging.getLogger("3s_trader")


class Evaluator:
    """포트폴리오 성과 평가 (AR, SR, CR, MDD)"""

    @staticmethod
    def accumulated_return(weekly_returns: List[float]) -> float:
        """누적 수익률 (AR)"""
        if not weekly_returns:
            return 0.0
        ar = 1.0
        for r in weekly_returns:
            ar *= (1 + r)
        return ar - 1

    @staticmethod
    def sharpe_ratio(weekly_returns: List[float]) -> float:
        """샤프 비율 (SR) - 무위험이자율 0 가정"""
        if not weekly_returns or len(weekly_returns) < 2:
            return 0.0
        returns = np.array(weekly_returns)
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)
        if std_return == 0:
            return 0.0
        return mean_return / std_return

    @staticmethod
    def max_drawdown(weekly_returns: List[float]) -> float:
        """최대 낙폭 (MDD)"""
        if not weekly_returns:
            return 0.0
        cumulative = [1.0]
        for r in weekly_returns:
            cumulative.append(cumulative[-1] * (1 + r))

        peak = cumulative[0]
        mdd = 0.0
        for c in cumulative:
            if c > peak:
                peak = c
            drawdown = (c - peak) / peak
            if drawdown < mdd:
                mdd = drawdown
        return mdd

    @staticmethod
    def calmar_ratio(weekly_returns: List[float]) -> float:
        """칼마 비율 (CR) = AR / |MDD|"""
        ar = Evaluator.accumulated_return(weekly_returns)
        mdd = Evaluator.max_drawdown(weekly_returns)
        if mdd == 0:
            return 0.0
        return ar / abs(mdd)

    @staticmethod
    def evaluate_all(weekly_returns: List[float]) -> Dict[str, float]:
        """모든 성과 지표 계산"""
        return {
            "accumulated_return": Evaluator.accumulated_return(weekly_returns),
            "sharpe_ratio": Evaluator.sharpe_ratio(weekly_returns),
            "max_drawdown": Evaluator.max_drawdown(weekly_returns),
            "calmar_ratio": Evaluator.calmar_ratio(weekly_returns),
        }

    @staticmethod
    def print_report(metrics: Dict[str, float]):
        """성과 리포트 출력"""
        print("\n" + "=" * 50)
        print("📊 3S-Trader 성과 리포트")
        print("=" * 50)
        print(f"  누적 수익률 (AR):  {metrics['accumulated_return']*100:+.2f}%")
        print(f"  샤프 비율 (SR):    {metrics['sharpe_ratio']:.4f}")
        print(f"  최대 낙폭 (MDD):   {metrics['max_drawdown']*100:.2f}%")
        print(f"  칼마 비율 (CR):    {metrics['calmar_ratio']:.4f}")
        print("=" * 50)

    @staticmethod
    def plot_cumulative_returns(
        history: List[Dict],
        output_path: str = "./results/cumulative_returns.png",
        title: str = "3S-Trader 누적 수익률",
    ):
        """누적 수익률 차트 생성"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        weeks = [h["week"] for h in history]
        cum_returns = [h["cumulative_return"] * 100 for h in history]
        market_cum = []

        # 시장 평균 누적 수익률
        market_c = 1.0
        for h in history:
            market_c *= (1 + h["market_avg_return"])
            market_cum.append((market_c - 1) * 100)

        fig, ax = plt.subplots(figsize=(14, 6))
        ax.plot(range(len(weeks)), cum_returns, "b-", linewidth=2, label="3S-Trader")
        ax.plot(range(len(weeks)), market_cum, "r--", linewidth=1.5, label="시장 평균 (1/N)")
        ax.fill_between(range(len(weeks)), cum_returns, alpha=0.1, color="blue")

        # x축 레이블 간소화
        step = max(1, len(weeks) // 10)
        ax.set_xticks(range(0, len(weeks), step))
        ax.set_xticklabels([weeks[i] for i in range(0, len(weeks), step)], rotation=45)

        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_xlabel("주차")
        ax.set_ylabel("누적 수익률 (%)")
        ax.legend(fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color="gray", linestyle="-", alpha=0.5)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
        logger.info(f"차트 저장: {output_path}")

    @staticmethod
    def plot_weekly_returns(
        history: List[Dict],
        output_path: str = "./results/weekly_returns.png",
    ):
        """주간 수익률 바 차트"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        weeks = [h["week"] for h in history]
        returns = [h["portfolio_return"] * 100 for h in history]
        colors = ["green" if r >= 0 else "red" for r in returns]

        fig, ax = plt.subplots(figsize=(14, 5))
        ax.bar(range(len(weeks)), returns, color=colors, alpha=0.7)

        step = max(1, len(weeks) // 10)
        ax.set_xticks(range(0, len(weeks), step))
        ax.set_xticklabels([weeks[i] for i in range(0, len(weeks), step)], rotation=45)

        ax.set_title("3S-Trader 주간 수익률", fontsize=14, fontweight="bold")
        ax.set_xlabel("주차")
        ax.set_ylabel("수익률 (%)")
        ax.axhline(y=0, color="gray", linestyle="-", alpha=0.5)
        ax.grid(True, alpha=0.3, axis="y")

        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
        logger.info(f"차트 저장: {output_path}")
