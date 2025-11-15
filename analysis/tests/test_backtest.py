"""backtest 模块测试。"""
from __future__ import annotations

from typing import Any

import pytest

from analysis.src import backtest


class DummyConn:
    """占位连接，供 monkeypatch 使用。"""

    def __init__(self) -> None:
        self.executed: list[Any] = []


def test_run_momentum_backtest(monkeypatch: pytest.MonkeyPatch) -> None:
    """确保回测返回合理指标。"""

    draws = [
        {"period": "1", "draw_time": "2025-01-01 00:00:00", "sum": 25, "numbers": [5, 5, 5, 5, 5], "big_small": "big"},
        {"period": "2", "draw_time": "2025-01-01 00:01:00", "sum": 18, "numbers": [3, 3, 3, 3, 6], "big_small": "small"},
        {"period": "3", "draw_time": "2025-01-01 00:02:00", "sum": 30, "numbers": [6, 6, 6, 6, 6], "big_small": "big"},
        {"period": "4", "draw_time": "2025-01-01 00:03:00", "sum": 20, "numbers": [4, 4, 4, 4, 4], "big_small": "small"},
        {"period": "5", "draw_time": "2025-01-01 00:04:00", "sum": 28, "numbers": [5, 5, 5, 6, 7], "big_small": "big"},
        {"period": "6", "draw_time": "2025-01-01 00:05:00", "sum": 15, "numbers": [1, 3, 4, 3, 4], "big_small": "small"},
    ]

    monkeypatch.setattr(backtest, "load_backtest_draws", lambda conn, limit: draws)
    result = backtest.run_momentum_backtest(
        DummyConn(), window=6, short_window=2, long_window=3, stake=1.0, payout_multiplier=0.9
    )
    assert result["trades"] > 0
    assert "equity_curve" in result
