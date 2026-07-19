"""Delete Conclusion API tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.db import connect
from app.main import create_app


CREATE_PAYLOAD = {
    "title": "Avoid high-acrylic base layers",
    "question": "Which clothing materials should I stop buying?",
    "conclusion": "Avoid base layers with a high acrylic percentage.",
    "reason": "They feel clammy and build up static.",
    "tradeoffs": "Some inexpensive styles will be excluded.",
    "conditions": "Reconsider if the fabric construction changes.",
    "category": "Shopping",
    "tags": ["Clothing", "Materials"],
    "confidence": "High",
    "decisionAnalysis": {
        "version": 1,
        "models": [
            {
                "modelId": "inversion",
                "modelVersion": 1,
                "answers": {"analysis": "Keep buying fabrics that already failed."},
            }
        ],
    },
}


def test_delete_conclusion_removes_record_and_cascading_relations(tmp_path: Path) -> None:
    database_path = tmp_path / "conclusion.sqlite3"
    with TestClient(create_app(database_path)) as client:
        created = client.post("/api/conclusions", json=CREATE_PAYLOAD).json()

        response = client.delete(f"/api/conclusions/{created['id']}")
        missing = client.get(f"/api/conclusions/{created['id']}")
        listed = client.get("/api/conclusions")

    assert response.status_code == 204
    assert response.content == b""
    assert missing.status_code == 404
    assert listed.json()["count"] == 0

    with connect(database_path, read_only=True) as connection:
        assert connection.execute("SELECT count(*) FROM conclusion_tags").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM decision_analyses").fetchone()[0] == 0
        # Tags remain reusable; orphan cleanup is intentionally a separate concern.
        assert connection.execute("SELECT count(*) FROM tags").fetchone()[0] == 2


def test_delete_conclusion_returns_404_for_missing_record(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        response = client.delete("/api/conclusions/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Conclusion not found"}
