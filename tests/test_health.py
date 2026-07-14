"""Health endpoint tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
