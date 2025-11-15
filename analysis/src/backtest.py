"""策略回测模块：提供简单趋势策略评估结果。"""
from __future__ import annotations

from collections import deque
import json
from statistics import mean
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection


def load_backtest_draws(conn: Connection, limit: int) -> list[dict[str, Any]]:
    """按照 draw_time 升序获取回测需要的开奖数据。"""

    rows = conn.execute(
        text(
            """
            SELECT period, draw_time, sum, numbers, big_small
            FROM lottery_draws
            ORDER BY draw_time ASC
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


def run_momentum_backtest(
    conn: Connection,
    window: int,
    short_window: int,
    long_window: int,
    stake: float,
    payout_multiplier: float,
) -> dict[str, Any]:
    """使用和值均线策略执行回测，输出收益指标。"""

    draws = load_backtest_draws(conn, limit=window)
    if len(draws) < long_window:
        raise ValueError("insufficient draws for backtest")

    sums = [draw["sum"] for draw in draws]
    queue_short: deque[int] = deque(maxlen=short_window)
    queue_long: deque[int] = deque(maxlen=long_window)
    equity = 0.0
    wins = 0
    losses = 0
    trades = 0
    equity_curve: list[dict[str, Any]] = []

    for idx, value in enumerate(sums):
        queue_short.append(value)
        queue_long.append(value)
        if len(queue_long) < long_window or len(queue_short) < short_window:
            continue
        short_ma = mean(queue_short)
        long_ma = mean(queue_long)
        signal = "big" if short_ma >= long_ma else "small"
        actual_result = draws[idx]["big_small"] if draws[idx].get("big_small") else ("big" if value >= 23 else "small")
        if signal == actual_result:
            pnl = stake * payout_multiplier
            wins += 1
        else:
            pnl = -stake
            losses += 1
        equity += pnl
        trades += 1
        equity_curve.append(
            {
                "period": draws[idx]["period"],
                "draw_time": draws[idx]["draw_time"],
                "signal": signal,
                "actual": actual_result,
                "pnl": pnl,
                "equity": equity,
            }
        )

    if trades == 0:
        raise ValueError("backtest produced no trades")

    win_rate = wins / trades
    avg_return = equity / (trades * stake)
    return {
        "period": draws[-1]["period"],
        "window": window,
        "short_window": short_window,
        "long_window": long_window,
        "stake": stake,
        "payout_multiplier": payout_multiplier,
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "avg_return": avg_return,
        "pnl": equity,
        "equity_curve": equity_curve[-50:],  # 保留最近 50 条用于前端展示
    }
