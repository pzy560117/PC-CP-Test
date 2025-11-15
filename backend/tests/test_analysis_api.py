"""API 导出能力测试。"""
from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from backend.app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    """每个测试默认提供样例数据。"""

    sample_results = [
        {
            "id": 1,
            "analysis_type": "statistical_analysis",
            "schema_version": 1,
            "result_summary": "demo",
            "result_data": {"randomness": {"runs": 10}},
            "metadata": {"window": 10},
            "created_at": "2025-01-01T00:00:00",
        }
    ]
    monkeypatch.setattr("backend.app.api.analysis.fetch_analysis_results", lambda limit=1, offset=0, analysis_type=None: sample_results)
    monkeypatch.setattr(
        "backend.app.api.analysis.fetch_features_batch",
        lambda periods: {
            period: {
                "period": period,
                "features": {
                    "basic_stats": {"schema_version": 1, "value": {"sum": 10}, "updated_at": "2025-01-01"},
                },
            }
            for period in periods
        },
    )


def test_export_analysis_json() -> None:
    """JSON 导出应返回格式字段。"""

    response = client.get("/api/v1/analysis/results/export?export_format=json")
    assert response.status_code == 200
    payload = response.json()
    assert payload["format"] == "json"
    assert payload["count"] == 1


def test_export_analysis_csv() -> None:
    """CSV 导出应返回附件。"""

    response = client.get("/api/v1/analysis/results/export?export_format=csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]


def test_export_features_json() -> None:
    """特征 JSON 导出。"""

    response = client.post("/api/v1/features/export", json={"periods": ["1"], "export_format": "json"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["format"] == "json"
    assert payload["count"] == 1


def test_export_features_csv() -> None:
    """特征 CSV 导出。"""

    response = client.post("/api/v1/features/export", json={"periods": ["1"], "export_format": "csv"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
