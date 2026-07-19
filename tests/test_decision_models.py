"""Decision model registry API tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import connect
from app.main import create_app


CUSTOM_MODEL = {
    "id": "constraint-check",
    "name": "约束检查",
    "explanation": "找出决定必须满足的硬约束，以及最先限制结果的瓶颈。",
}


CONCLUSION_PAYLOAD = {
    "title": "Choose a reversible experiment",
    "question": "Should I commit to the full plan now?",
    "conclusion": "Run a small reversible experiment first.",
    "reason": "The exit cost is low and the evidence is incomplete.",
    "category": "Learning",
    "tags": [],
    "confidence": "Medium",
}


def test_list_and_get_builtin_decision_models(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        listed = client.get("/api/decision-models")
        fetched = client.get("/api/decision-models/time-horizons")
        munger = client.get("/api/decision-models/munger-checklist")

    assert listed.status_code == 200
    body = listed.json()
    assert body["count"] == 7
    assert [item["id"] for item in body["items"]] == [
        "precedent-review",
        "munger-checklist",
        "scenario-range",
        "time-horizons",
        "inversion",
        "inaction-value",
        "reversibility",
    ]
    assert all(item["version"] == 1 and item["isBuiltin"] for item in body["items"])
    assert all(
        set(item) == {
            "id", "version", "name", "explanation", "isBuiltin", "createdAt", "updatedAt"
        }
        for item in body["items"]
    )
    assert fetched.status_code == 200
    assert "10 小时、10 天、10 个月和 10 年" in fetched.json()["explanation"]
    assert "能力圈、激励、风险、机会成本" in munger.json()["explanation"]


def test_create_custom_model_and_use_it_in_conclusion(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        created = client.post("/api/decision-models", json=CUSTOM_MODEL)
        payload = {
            **CONCLUSION_PAYLOAD,
            "decisionAnalysis": {
                "version": 1,
                "models": [
                    {
                        "modelId": "constraint-check",
                        "modelVersion": 1,
                        "answers": {"analysis": "Stay within the weekly time budget."},
                    }
                ],
            },
        }
        conclusion = client.post("/api/conclusions", json=payload)
        listed = client.get("/api/decision-models")

    assert created.status_code == 201
    assert created.json() == {
        **CUSTOM_MODEL,
        "version": 1,
        "isBuiltin": False,
        "createdAt": created.json()["createdAt"],
        "updatedAt": created.json()["updatedAt"],
    }
    assert conclusion.status_code == 201
    assert conclusion.json()["decisionAnalysis"] == payload["decisionAnalysis"]
    assert listed.json()["count"] == 8


def test_create_decision_model_rejects_duplicate_id(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        first = client.post("/api/decision-models", json=CUSTOM_MODEL)
        duplicate = client.post("/api/decision-models", json=CUSTOM_MODEL)

    assert first.status_code == 201
    assert duplicate.status_code == 409


@pytest.mark.parametrize(
    "change",
    [
        {"id": "Bad ID"},
        {"name": " "},
        {"explanation": " "},
    ],
)
def test_create_decision_model_validates_definition(
    tmp_path: Path,
    change: dict[str, object],
) -> None:
    payload = {**CUSTOM_MODEL, **change}
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        response = client.post("/api/decision-models", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "run",
    [
        {
            "modelId": "missing-model",
            "modelVersion": 1,
            "answers": {"question": "Answer"},
        },
        {
            "modelId": "time-horizons",
            "modelVersion": 2,
            "answers": {"analysis": "Answer"},
        },
        {
            "modelId": "time-horizons",
            "modelVersion": 1,
            "answers": {"unknownPrompt": "Answer"},
        },
    ],
)
def test_create_conclusion_rejects_unregistered_model_reference(
    tmp_path: Path,
    run: dict[str, object],
) -> None:
    payload = {
        **CONCLUSION_PAYLOAD,
        "decisionAnalysis": {"version": 1, "models": [run]},
    }
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        response = client.post("/api/conclusions", json=payload)
        conclusions = client.get("/api/conclusions").json()

    assert response.status_code == 422
    assert conclusions["count"] == 0


def test_get_missing_decision_model_returns_404(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        response = client.get("/api/decision-models/missing-model")

    assert response.status_code == 404


def test_builtin_refresh_keeps_legacy_prompt_keys_readable(tmp_path: Path) -> None:
    database_path = tmp_path / "conclusion.sqlite3"
    with TestClient(create_app(database_path)):
        pass

    legacy_prompts = (
        '[{"key":"tenHours","label":"10 小时后","placeholder":""}]'
    )
    with connect(database_path) as connection:
        connection.execute(
            """
            UPDATE decision_models
            SET description = ?, prompts_json = ?
            WHERE id = 'time-horizons'
            """,
            ("旧版多问题说明", legacy_prompts),
        )

    payload = {
        **CONCLUSION_PAYLOAD,
        "decisionAnalysis": {
            "version": 1,
            "models": [
                {
                    "modelId": "time-horizons",
                    "modelVersion": 1,
                    "answers": {"tenHours": "Legacy answer remains valid."},
                }
            ],
        },
    }
    with TestClient(create_app(database_path)) as client:
        refreshed = client.get("/api/decision-models/time-horizons")
        conclusion = client.post("/api/conclusions", json=payload)

    assert refreshed.status_code == 200
    assert refreshed.json()["explanation"] != "旧版多问题说明"
    assert conclusion.status_code == 201

    with connect(database_path, read_only=True) as connection:
        stored = connection.execute(
            "SELECT prompts_json FROM decision_models WHERE id = 'time-horizons'"
        ).fetchone()
    assert stored["prompts_json"] == legacy_prompts
