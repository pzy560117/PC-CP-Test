"""collector 模块测试。"""
from __future__ import annotations

from types import SimpleNamespace

from analysis.src import collector


class DummyContext:
    """用于替代 session_scope 的上下文。"""

    def __init__(self) -> None:
        self.executed: list[tuple[str, dict | None]] = []

    def __enter__(self):  # noqa: D401
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, stmt, params=None):  # noqa: D401
        self.executed.append((str(stmt), params))
        return None


def test_run_collection_inserts_history(monkeypatch):
    """确保 run_collection 能触发插入。"""

    payloads = [
        {"period": "001", "openTime": "2024-01-01 00:00:00", "openCode": "1,2,3,4,5", "timestamp": 1},
        {"period": "002", "openTime": "2024-01-01 00:01:00", "openCode": "1,2,3,4,6", "timestamp": 2},
        {"period": "003", "openTime": "2024-01-01 00:02:00", "openCode": "1,2,3,4,7", "timestamp": 3},
    ]
    inserted: list[tuple[str, str]] = []

    def fake_fetch(config, source_cfg):  # noqa: D401
        yield from payloads

    def fake_insert(conn, payload, source):
        inserted.append((payload["period"], source))

    monkeypatch.setattr(collector, "_fetch_source_payloads", fake_fetch)
    monkeypatch.setattr(collector, "insert_raw_draw", fake_insert)
    monkeypatch.setattr(collector, "session_scope", lambda: DummyContext())

    config = SimpleNamespace(
        sources=[SimpleNamespace(name="history", parser="history_html", endpoint="demo")],
        monitoring_enabled=False,
        batch_size=2,
    )
    monkeypatch.setattr(collector, "load_config", lambda: config)

    collector.run_collection()

    assert inserted == [
        ("001", "history"),
        ("002", "history"),
    ]
