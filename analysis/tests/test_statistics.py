"""statistics 模块测试。"""
from __future__ import annotations

from analysis.src import statistics


def test_build_digit_frequency_and_randomness() -> None:
    """验证数字频率与随机性统计。"""

    draws = [
        {"numbers": [1, 2, 3, 4, 5], "odd_even": "odd", "big_small": "big", "sum": 15},
        {"numbers": [5, 4, 3, 2, 1], "odd_even": "even", "big_small": "small", "sum": 15},
    ]
    freq = statistics.build_digit_frequency(draws)
    assert freq["digits"]["1"]["count"] == 2
    randomness = statistics.build_randomness_metrics(draws)
    assert randomness["runs"] >= 1


def test_build_markov_transitions() -> None:
    """验证 Markov 转移矩阵。"""

    draws = [
        {"numbers": [1], "odd_even": "odd", "big_small": "small", "sum": 1},
        {"numbers": [2], "odd_even": "even", "big_small": "small", "sum": 2},
        {"numbers": [3], "odd_even": "odd", "big_small": "big", "sum": 3},
    ]
    markov = statistics.build_markov_transitions(draws)
    assert "odd" in markov["parity"]
    assert sum(markov["parity"]["odd"].values()) == 1.0
