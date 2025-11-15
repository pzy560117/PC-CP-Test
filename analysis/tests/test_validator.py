"""validator 模块测试。"""
from __future__ import annotations

from typing import Any

import pytest

from analysis.src import validator


class FakeConn:
    def __init__(self):
        self.executed: list[tuple[str, dict[str, Any] | None]] = []

    def execute(self, stmt, params=None):
        self.executed.append((str(stmt), params))
        return []


class DummyContext:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, exc_type, exc, tb):
        return False


def test_run_validation_processes_valid_and_invalid(monkeypatch):
    pending = [
        {"id": 1, "payload": {"period": "001", "openTime": "2025-01-01 00:00:00", "openCode": "1,2,3,4,5"}},
        {"id": 2, "payload": {"period": "002", "openTime": "2025-01-01 00:01:00"}},  # invalid
    ]
    inserted: list[dict[str, Any]] = []
    fake_conn = FakeConn()

    monkeypatch.setattr(validator, "load_pending_raw", lambda limit=200: pending)
    monkeypatch.setattr(validator, "insert_validated_draw", lambda conn, record: inserted.append(record))
    monkeypatch.setattr(validator, "session_scope", lambda: DummyContext(fake_conn))

    validator.run_validation()

    assert inserted[0]["period"] == "001"
    update_statements = [sql for sql, _ in fake_conn.executed]
    # 应该对两条记录分别更新状态
    assert any("status='failed'" in sql for sql in update_statements)
    assert any("status='passed'" in sql for sql in update_statements)
