"""统计与状态转移分析模块。"""
from __future__ import annotations

from collections import Counter, deque
import json
import math
from statistics import mean
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection


def load_recent_draws(conn: Connection, limit: int) -> list[dict[str, Any]]:
    """查询最近开奖数据，按 draw_time DESC 排序。"""

    rows = conn.execute(
        text(
            """
            SELECT period, numbers, sum, odd_even, big_small, draw_time
            FROM lottery_draws
            ORDER BY draw_time DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    ).mappings().all()
    result: list[dict[str, Any]] = []
    for row in rows:
        numbers = row["numbers"]
        if isinstance(numbers, str):
            numbers = json.loads(numbers)
        result.append({**row, "numbers": [int(x) for x in numbers]})
    return result


def build_digit_frequency(draws: list[dict[str, Any]]) -> dict[str, Any]:
    """计算数字与位置频率并返回比例。"""

    digit_counter: Counter[int] = Counter()
    position_counters: list[Counter[int]] = []
    for draw in draws:
        numbers = draw["numbers"]
        for idx, number in enumerate(numbers):
            digit_counter[number] += 1
            if idx >= len(position_counters):
                position_counters.append(Counter())
            position_counters[idx][number] += 1
    total = sum(digit_counter.values()) or 1
    digit_distribution = {
        str(key): {"count": value, "ratio": value / total} for key, value in sorted(digit_counter.items())
    }
    position_distribution: dict[str, Any] = {}
    for idx, counter in enumerate(position_counters):
        pos_total = sum(counter.values()) or 1
        position_distribution[f"position_{idx + 1}"] = {
            str(key): {"count": value, "ratio": value / pos_total} for key, value in sorted(counter.items())
        }
    return {
        "total_digits": total,
        "digits": digit_distribution,
        "positions": position_distribution,
    }


def build_randomness_metrics(draws: list[dict[str, Any]]) -> dict[str, Any]:
    """执行基础随机性指标（卡方、奇偶游程、和值波动）。"""

    if not draws:
        return {"chi_square": 0.0, "runs": 0, "mean_sum": 0.0, "std_sum": 0.0}
    all_numbers = [num for draw in draws for num in draw["numbers"]]
    total_digits = len(all_numbers)
    digit_counter = Counter(all_numbers)
    expected = total_digits / 10 if total_digits else 1
    chi_square = sum(((count - expected) ** 2) / expected for count in digit_counter.values())

    # 奇偶游程统计
    runs = 1
    parity_sequence = [draw["odd_even"] for draw in reversed(draws)]
    for prev, curr in zip(parity_sequence, parity_sequence[1:]):
        if prev != curr:
            runs += 1

    sums = [draw["sum"] for draw in draws]
    avg_sum = mean(sums)
    variance = mean([(value - avg_sum) ** 2 for value in sums]) if len(sums) > 1 else 0.0
    std_sum = math.sqrt(variance)
    return {
        "chi_square": chi_square,
        "runs": runs,
        "mean_sum": avg_sum,
        "std_sum": std_sum,
    }


def build_markov_transitions(draws: list[dict[str, Any]]) -> dict[str, Any]:
    """构建奇偶/大小状态的 Markov 转移矩阵。"""

    if len(draws) < 2:
        return {"parity": {}, "size": {}}
    parity_matrix = _build_transition_matrix([draw["odd_even"] for draw in reversed(draws)])
    size_matrix = _build_transition_matrix([draw["big_small"] for draw in reversed(draws)])
    return {"parity": parity_matrix, "size": size_matrix}


def _build_transition_matrix(sequence: list[str]) -> dict[str, dict[str, float]]:
    """根据状态序列生成带概率的矩阵。"""

    transitions: dict[str, Counter[str]] = {}
    for prev, curr in zip(sequence, sequence[1:]):
        if prev not in transitions:
            transitions[prev] = Counter()
        transitions[prev][curr] += 1
    matrix: dict[str, dict[str, float]] = {}
    for state, counter in transitions.items():
        total = sum(counter.values()) or 1
        matrix[state] = {target: count / total for target, count in counter.items()}
    return matrix


def build_statistical_report(conn: Connection, window: int) -> dict[str, Any]:
    """生成统计+状态转移报告。"""

    draws = load_recent_draws(conn, limit=window)
    frequency = build_digit_frequency(draws)
    randomness = build_randomness_metrics(draws)
    markov = build_markov_transitions(draws)
    latest_period = draws[0]["period"] if draws else ""
    return {
        "period": latest_period,
        "window": len(draws),
        "frequency": frequency,
        "randomness": randomness,
        "markov": markov,
        "sequence": build_sequence_snapshot(draws, window=window),
    }


def build_sequence_snapshot(draws: list[dict[str, Any]], window: int) -> list[dict[str, Any]]:
    """返回最近 window 条开奖快照，供前端展示。"""

    queue: deque[dict[str, Any]] = deque(maxlen=window)
    for draw in reversed(draws):
        queue.append(
            {
                "period": draw["period"],
                "sum": draw["sum"],
                "odd_even": draw["odd_even"],
                "big_small": draw["big_small"],
                "numbers": draw["numbers"],
            }
        )
    return list(queue)
