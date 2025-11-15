"""collector 模块测试。"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from analysis.src import collector


class DummyContext:
    """用于替代 session_scope 的上下文。"""

    def __enter__(self):  # noqa: D401 - 简单实现
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_run_collection_inserts_history(monkeypatch):
    payloads = [
        {"period": "001", "openTime": "2024-01-01 00:00:00", "openCode": "1,2,3,4,5", "timestamp": 1},
        {"period": "002", "openTime": "2024-01-01 00:01:00", "openCode": "1,2,3,4,6", "timestamp": 2},
        {"period": "003", "openTime": "2024-01-01 00:02:00", "openCode": "1,2,3,4,7", "timestamp": 3},
    ]
    inserted: list[tuple[str, str]] = []

    def fake_history(config):
        return payloads

    def fake_insert(conn, payload, source):
        inserted.append((payload["period"], source))

    monkeypatch.setattr(collector, "fetch_history", fake_history)
    monkeypatch.setattr(collector, "insert_raw_draw", fake_insert)
    monkeypatch.setattr(collector, "session_scope", lambda: DummyContext())

    config = SimpleNamespace(api=SimpleNamespace(user_agent="ua"), batch_size=2, retry=1)
    monkeypatch.setattr(collector, "load_config", lambda: config)

    collector.run_collection()

    assert inserted == [
        ("001", "history_api"),
        ("002", "history_api"),  # 仅插入 batch_size 数量
    ]
