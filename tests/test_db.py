"""SQLite connection and schema tests."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import BUSY_TIMEOUT_MS, connect, init_db, resolve_database_path
from app.main import create_app


EXPECTED_COLUMNS = {
    "id",
    "title",
    "question",
    "conclusion",
    "reason",
    "tradeoffs",
    "conditions",
    "category",
    "confidence",
    "created_at",
    "updated_at",
}
VALID_CONCLUSION = {
    "title": "Buy a standing desk",
    "question": "Should I replace my current desk?",
    "conclusion": "Wait until the current desk becomes limiting.",
    "reason": "The current setup is still adequate.",
    "tradeoffs": "Accept less flexibility for now.",
    "conditions": "Reconsider if the desk becomes unstable.",
    "category": "Shopping",
    "confidence": "Medium",
    "created_at": "2026-07-14T12:00:00+00:00",
    "updated_at": "2026-07-14T12:00:00+00:00",
}
INSERT_CONCLUSION_SQL = """
    INSERT INTO conclusions (
        title, question, conclusion, reason, tradeoffs, conditions,
        category, confidence, created_at, updated_at
    )
    VALUES (
        :title, :question, :conclusion, :reason, :tradeoffs, :conditions,
        :category, :confidence, :created_at, :updated_at
    )
"""


def test_connect_creates_parent_and_configures_sqlite(tmp_path: Path) -> None:
    database_path = tmp_path / "nested" / "conclusion.sqlite3"

    with connect(database_path) as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == BUSY_TIMEOUT_MS
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"

    assert database_path.exists()


def test_resolve_database_path_uses_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured_path = tmp_path / "configured.sqlite3"
    monkeypatch.setenv("CONCLUSION_DATABASE_PATH", str(configured_path))

    assert resolve_database_path() == configured_path


def test_init_db_creates_idempotent_schema(tmp_path: Path) -> None:
    with connect(tmp_path / "conclusion.sqlite3") as connection:
        init_db(connection)
        init_db(connection)

        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(conclusions)").fetchall()
        }
        indexes = {
            row["name"] for row in connection.execute("PRAGMA index_list(conclusions)").fetchall()
        }
        tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert columns == EXPECTED_COLUMNS
    assert {"idx_conclusions_category", "idx_conclusions_updated_at"} <= indexes
    assert {
        "conclusions",
        "tags",
        "conclusion_tags",
        "decision_analyses",
        "decision_models",
    } <= tables


def test_init_db_migrates_existing_conclusions_with_default_conditions(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.sqlite3"
    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(
            """
            CREATE TABLE conclusions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                question TEXT NOT NULL,
                conclusion TEXT NOT NULL,
                reason TEXT NOT NULL,
                tradeoffs TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL,
                confidence TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        legacy_values = {
            key: value for key, value in VALID_CONCLUSION.items() if key != "conditions"
        }
        connection.execute(
            """
            INSERT INTO conclusions (
                title, question, conclusion, reason, tradeoffs,
                category, confidence, created_at, updated_at
            ) VALUES (
                :title, :question, :conclusion, :reason, :tradeoffs,
                :category, :confidence, :created_at, :updated_at
            )
            """,
            legacy_values,
        )
        connection.commit()

    with connect(database_path) as connection:
        init_db(connection)
        migrated = connection.execute(
            "SELECT conditions FROM conclusions WHERE id = 1"
        ).fetchone()

    assert migrated["conditions"] == ""


def test_init_db_migrates_legacy_decision_models_to_versioned_primary_key(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "legacy-models.sqlite3"
    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute(
            """
            CREATE TABLE decision_models (
                id TEXT PRIMARY KEY,
                version INTEGER NOT NULL CHECK (version = 1),
                name TEXT NOT NULL,
                short_name TEXT NOT NULL,
                description TEXT NOT NULL,
                prompts_json TEXT NOT NULL,
                source_name TEXT NOT NULL DEFAULT '',
                source_url TEXT NOT NULL DEFAULT '',
                is_builtin INTEGER NOT NULL CHECK (is_builtin IN (0, 1)),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO decision_models VALUES (
                'legacy-model', 1, '旧模型', '旧模型', '保留这段说明。', '[]',
                '', '', 0, '2026-07-01T00:00:00Z', '2026-07-01T00:00:00Z'
            )
            """
        )
        connection.commit()

    with connect(database_path) as connection:
        init_db(connection)
        primary_key = {
            row["name"]: row["pk"]
            for row in connection.execute("PRAGMA table_info(decision_models)").fetchall()
            if row["pk"]
        }
        legacy = connection.execute(
            "SELECT name, description FROM decision_models WHERE id = 'legacy-model'"
        ).fetchone()

    assert primary_key == {"id": 1, "version": 2}
    assert dict(legacy) == {"name": "旧模型", "description": "保留这段说明。"}


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("title", "   "),
        ("question", ""),
        ("conclusion", "\t"),
        ("reason", "\n"),
        ("category", " "),
        ("confidence", "Certain"),
    ],
)
def test_schema_rejects_invalid_required_values(
    tmp_path: Path,
    field: str,
    invalid_value: str,
) -> None:
    values = dict(VALID_CONCLUSION)
    values[field] = invalid_value

    with connect(tmp_path / "conclusion.sqlite3") as connection:
        init_db(connection)
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(INSERT_CONCLUSION_SQL, values)


def test_connect_rolls_back_and_closes_on_error(tmp_path: Path) -> None:
    database_path = tmp_path / "conclusion.sqlite3"

    with pytest.raises(RuntimeError, match="stop write"):
        with connect(database_path) as connection:
            init_db(connection)
            connection.execute(INSERT_CONCLUSION_SQL, VALID_CONCLUSION)
            opened_connection = connection
            raise RuntimeError("stop write")

    with pytest.raises(sqlite3.ProgrammingError):
        opened_connection.execute("SELECT 1")

    with connect(database_path, read_only=True) as connection:
        count = connection.execute("SELECT count(*) FROM conclusions").fetchone()[0]

    assert count == 0


def test_app_lifespan_initializes_database(tmp_path: Path) -> None:
    database_path = tmp_path / "conclusion.sqlite3"

    with TestClient(create_app(database_path)):
        pass

    with connect(database_path, read_only=True) as connection:
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'conclusions'"
        ).fetchone()

    assert table["name"] == "conclusions"
