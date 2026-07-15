"""List and detail Conclusion API tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def payload(title: str, category: str = "Life") -> dict[str, object]:
    return {
        "title": title,
        "question": f"Question for {title}",
        "conclusion": f"Conclusion for {title}",
        "reason": f"Reason for {title}",
        "tradeoffs": f"Tradeoffs for {title}",
        "conditions": f"Conditions for {title}",
        "category": category,
        "tags": [category, "Decision"],
        "confidence": "High",
    }


def test_list_conclusions_returns_newest_first_and_bounded_metadata(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        first = client.post("/api/conclusions", json=payload("First")).json()
        second = client.post("/api/conclusions", json=payload("Second")).json()

        response = client.get("/api/conclusions", params={"limit": 1})

    assert response.status_code == 200
    assert response.json() == {
        "count": 2,
        "returned": 1,
        "items": [second],
    }
    assert first["id"] < second["id"]


def test_list_conclusions_returns_empty_page(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        response = client.get("/api/conclusions")

    assert response.status_code == 200
    assert response.json() == {"count": 0, "returned": 0, "items": []}


def test_list_conclusions_validates_limit(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        too_small = client.get("/api/conclusions", params={"limit": 0})
        too_large = client.get("/api/conclusions", params={"limit": 201})

    assert too_small.status_code == 422
    assert too_large.status_code == 422


def test_search_conclusions_combines_text_category_and_tag_filters(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        client.post(
            "/api/conclusions",
            json={**payload("Keep the emergency reserve", "Finance"), "tags": ["Safety"]},
        )
        match = client.post(
            "/api/conclusions",
            json={
                **payload("Keep emergency cash available", "Finance"),
                "reason": "Liquidity matters more than return for this money.",
                "tags": ["Emergency Fund", "Safety"],
            },
        ).json()
        client.post(
            "/api/conclusions",
            json={**payload("Buy a winter coat", "Shopping"), "tags": ["Clothing"]},
        )

        response = client.get(
            "/api/conclusions",
            params={"query": "liquidity", "category": "finance", "tag": "emergency fund"},
        )

    assert response.status_code == 200
    assert response.json() == {"count": 1, "returned": 1, "items": [match]}


def test_search_conclusions_returns_all_when_filters_are_omitted(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        created = client.post("/api/conclusions", json=payload("Keep it simple")).json()
        response = client.get("/api/conclusions")

    assert response.json() == {"count": 1, "returned": 1, "items": [created]}


def test_get_conclusion_returns_record(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        created = client.post(
            "/api/conclusions",
            json=payload("Keep an emergency fund", "Finance"),
        ).json()

        response = client.get(f"/api/conclusions/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_conclusion_returns_404_for_missing_record(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3")) as client:
        response = client.get("/api/conclusions/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Conclusion not found"}
