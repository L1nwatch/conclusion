"""Frontend static serving tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app


def test_spa_fallback_serves_built_index(tmp_path: Path) -> None:
    frontend_dist = tmp_path / "dist"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text("<h1>Conclusion UI</h1>", encoding="utf-8")
    assets = frontend_dist / "assets"
    assets.mkdir()
    (assets / "app.js").write_text("console.log('Conclusion')", encoding="utf-8")

    with TestClient(create_app(tmp_path / "conclusion.sqlite3", frontend_dist)) as client:
        root = client.get("/")
        nested = client.get("/conclusions/1")
        asset = client.get("/assets/app.js")

    assert root.status_code == 200
    assert nested.status_code == 200
    assert root.text == "<h1>Conclusion UI</h1>"
    assert nested.text == root.text
    assert asset.status_code == 200
    assert asset.text == "console.log('Conclusion')"


def test_spa_fallback_reports_missing_build(tmp_path: Path) -> None:
    with TestClient(
        create_app(tmp_path / "conclusion.sqlite3", tmp_path / "missing")
    ) as client:
        response = client.get("/")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Frontend build not found. Run the frontend build first."
    }


def test_spa_fallback_preserves_api_404(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "conclusion.sqlite3", None)) as client:
        response = client.get("/api/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
