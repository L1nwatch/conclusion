"""Update Conclusion API tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

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
}


def test_patch_conclusion_updates_only_supplied_fields(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        created = client.post("/api/conclusions", json=CREATE_PAYLOAD).json()

        response = client.patch(
            f"/api/conclusions/{created['id']}",
            json={
                "reason": " Avoid because of **static** and poor breathability. ",
                "conditions": " Reconsider when a tested garment performs well. ",
                "tags": [" Clothing ", "Avoid", "clothing"],
                "expectedUpdatedAt": created["updatedAt"],
            },
        )

    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == created["title"]
    assert updated["conclusion"] == created["conclusion"]
    assert updated["reason"] == "Avoid because of **static** and poor breathability."
    assert updated["conditions"] == "Reconsider when a tested garment performs well."
    assert updated["tags"] == ["Clothing", "Avoid"]
    assert updated["createdAt"] == created["createdAt"]
    assert updated["updatedAt"] != created["updatedAt"]


def test_patch_conclusion_can_clear_tags(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        created = client.post("/api/conclusions", json=CREATE_PAYLOAD).json()

        response = client.patch(
            f"/api/conclusions/{created['id']}",
            json={"tags": [], "expectedUpdatedAt": created["updatedAt"]},
        )

    assert response.status_code == 200
    assert response.json()["tags"] == []


def test_patch_conclusion_updates_decision_analysis(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        created = client.post("/api/conclusions", json=CREATE_PAYLOAD).json()
        analysis = {
            "version": 1,
            "models": [
                {
                    "modelId": "scenario-range",
                    "answers": {
                        "bestCase": "The replacement materially improves comfort.",
                        "likelyCase": "The improvement is modest.",
                        "worstCase": "It wastes money and space.",
                        "safeguards": "Wait until the need is measurable.",
                    },
                }
            ],
        }
        response = client.patch(
            f"/api/conclusions/{created['id']}",
            json={
                "decisionAnalysis": analysis,
                "expectedUpdatedAt": created["updatedAt"],
            },
        )

    assert response.status_code == 200
    assert response.json()["decisionAnalysis"] == analysis


def test_patch_conclusion_rejects_stale_update_without_mutating_record(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        created = client.post("/api/conclusions", json=CREATE_PAYLOAD).json()
        first = client.patch(
            f"/api/conclusions/{created['id']}",
            json={
                "title": "First writer won",
                "expectedUpdatedAt": created["updatedAt"],
            },
        ).json()

        stale = client.patch(
            f"/api/conclusions/{created['id']}",
            json={
                "title": "Stale writer",
                "expectedUpdatedAt": created["updatedAt"],
            },
        )
        current = client.get(f"/api/conclusions/{created['id']}").json()

    assert stale.status_code == 409
    assert stale.json() == {
        "detail": {
            "message": "Conclusion was modified by another writer",
            "currentUpdatedAt": first["updatedAt"],
        }
    }
    assert current == first


def test_patch_conclusion_returns_404_for_missing_record(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        response = client.patch(
            "/api/conclusions/999",
            json={
                "title": "Missing",
                "expectedUpdatedAt": "2026-07-14T12:00:00Z",
            },
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Conclusion not found"}


@pytest.mark.parametrize(
    "payload",
    [
        {"expectedUpdatedAt": "2026-07-14T12:00:00Z"},
        {"title": "   ", "expectedUpdatedAt": "2026-07-14T12:00:00Z"},
        {"title": None, "expectedUpdatedAt": "2026-07-14T12:00:00Z"},
        {"conclusion": "x" * 281, "expectedUpdatedAt": "2026-07-14T12:00:00Z"},
        {"title": "Updated", "expectedUpdatedAt": "2026-07-14T12:00:00"},
    ],
)
def test_patch_conclusion_rejects_invalid_payload(
    tmp_path: Path,
    payload: dict[str, object],
) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        response = client.patch("/api/conclusions/1", json=payload)

    assert response.status_code == 422
