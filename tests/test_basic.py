"""기본 테스트"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.portfolio.evaluator import Evaluator
from src.utils.helpers import load_config, get_trading_weeks


class TestEvaluator:
    """성과 평가 모듈 테스트"""

    def test_accumulated_return(self):
        returns = [0.01, 0.02, -0.01, 0.03]
        ar = Evaluator.accumulated_return(returns)
        expected = (1.01 * 1.02 * 0.99 * 1.03) - 1
        assert abs(ar - expected) < 1e-10

    def test_accumulated_return_empty(self):
        assert Evaluator.accumulated_return([]) == 0.0

    def test_sharpe_ratio(self):
        returns = [0.01, 0.02, 0.01, 0.03, 0.02]
        sr = Evaluator.sharpe_ratio(returns)
        assert sr > 0

    def test_max_drawdown(self):
        returns = [0.1, -0.2, 0.05, -0.1]
        mdd = Evaluator.max_drawdown(returns)
        assert mdd < 0

    def test_calmar_ratio(self):
        returns = [0.05, 0.03, -0.02, 0.04]
        cr = Evaluator.calmar_ratio(returns)
        assert cr != 0

    def test_evaluate_all(self):
        returns = [0.01, 0.02, -0.01, 0.03]
        metrics = Evaluator.evaluate_all(returns)
        assert "accumulated_return" in metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics
        assert "calmar_ratio" in metrics


class TestHelpers:
    """헬퍼 함수 테스트"""

    def test_trading_weeks(self):
        weeks = get_trading_weeks("2024-01-01", "2024-01-31")
        assert len(weeks) > 0
        for monday, friday in weeks:
            assert len(monday) == 8
            assert len(friday) == 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
