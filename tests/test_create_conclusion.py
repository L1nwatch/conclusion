"""Create Conclusion API tests."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import connect
from app.main import create_app


VALID_PAYLOAD = {
    "title": "  Buy a standing desk  ",
    "question": " Should I replace my current desk? ",
    "conclusion": " Wait until the current desk becomes limiting. ",
    "reason": " The current setup is still adequate. ",
    "tradeoffs": " Accept less flexibility for now. ",
    "category": " Shopping ",
    "confidence": "Medium",
}


def test_create_conclusion_returns_and_persists_record(tmp_path: Path) -> None:
    database_path = tmp_path / "conclusion.sqlite3"

    with TestClient(create_app(database_path)) as client:
        response = client.post("/api/conclusions", json=VALID_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["title"] == "Buy a standing desk"
    assert body["question"] == "Should I replace my current desk?"
    assert body["conclusion"] == "Wait until the current desk becomes limiting."
    assert body["reason"] == "The current setup is still adequate."
    assert body["tradeoffs"] == "Accept less flexibility for now."
    assert body["category"] == "Shopping"
    assert body["confidence"] == "Medium"
    assert body["createdAt"] == body["updatedAt"]
    assert datetime.fromisoformat(body["createdAt"]).utcoffset().total_seconds() == 0

    with connect(database_path, read_only=True) as connection:
        stored = connection.execute("SELECT * FROM conclusions WHERE id = 1").fetchone()

    assert dict(stored) == {
        "id": 1,
        "title": body["title"],
        "question": body["question"],
        "conclusion": body["conclusion"],
        "reason": body["reason"],
        "tradeoffs": body["tradeoffs"],
        "category": body["category"],
        "confidence": body["confidence"],
        "created_at": body["createdAt"],
        "updated_at": body["updatedAt"],
    }


def test_create_conclusion_defaults_tradeoffs_to_empty_text(tmp_path: Path) -> None:
    payload = dict(VALID_PAYLOAD)
    payload.pop("tradeoffs")

    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        response = client.post("/api/conclusions", json=payload)

    assert response.status_code == 201
    assert response.json()["tradeoffs"] == ""


@pytest.mark.parametrize(
    "field",
    ["title", "question", "conclusion", "reason", "category"],
)
def test_create_conclusion_rejects_blank_required_text(tmp_path: Path, field: str) -> None:
    payload = dict(VALID_PAYLOAD)
    payload[field] = " \t\n "

    with TestClient(create_app(tmp_path / f"{field}.sqlite3")) as client:
        response = client.post("/api/conclusions", json=payload)

    assert response.status_code == 422


def test_create_conclusion_rejects_unknown_confidence(tmp_path: Path) -> None:
    payload = dict(VALID_PAYLOAD)
    payload["confidence"] = "Certain"

    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        response = client.post("/api/conclusions", json=payload)

    assert response.status_code == 422

