"""Public-safe screenshot demo data tests."""

from pathlib import Path

import pytest

from app.db import connect
from scripts.seed_demo_data import DEMO_CONCLUSIONS, seed


def test_seed_creates_deterministic_public_safe_records(tmp_path: Path) -> None:
    database_path = tmp_path / "demo.sqlite3"

    seed(database_path)

    with connect(database_path, read_only=True) as connection:
        rows = connection.execute(
            "SELECT title, category, created_at, updated_at FROM conclusions ORDER BY id"
        ).fetchall()

    assert len(rows) == len(DEMO_CONCLUSIONS)
    assert [row["title"] for row in rows] == [item["title"] for item in DEMO_CONCLUSIONS]
    assert [row["category"] for row in rows] == [item["category"] for item in DEMO_CONCLUSIONS]
    assert [row["created_at"] for row in rows] == [item["timestamp"] for item in DEMO_CONCLUSIONS]
    assert all(row["updated_at"] == row["created_at"] for row in rows)


def test_seed_refuses_to_replace_database_without_clean(tmp_path: Path) -> None:
    database_path = tmp_path / "demo.sqlite3"
    seed(database_path)

    with pytest.raises(FileExistsError, match="Demo database already exists"):
        seed(database_path)


def test_seed_clean_replaces_existing_database(tmp_path: Path) -> None:
    database_path = tmp_path / "demo.sqlite3"
    seed(database_path)

    with connect(database_path) as connection:
        connection.execute("DELETE FROM conclusions")

    seed(database_path, clean=True)

    with connect(database_path, read_only=True) as connection:
        count = connection.execute("SELECT count(*) FROM conclusions").fetchone()[0]

    assert count == len(DEMO_CONCLUSIONS)

