"""SQLite connection and schema management for Conclusion."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_PATH = ROOT_DIR / "data" / "conclusion.sqlite3"
DATABASE_PATH_ENV = "CONCLUSION_DATABASE_PATH"
BUSY_TIMEOUT_MS = 5_000


def resolve_database_path(database_path: str | Path | None = None) -> Path:
    """Resolve an explicit, configured, or default SQLite database path."""
    configured_path = database_path or os.getenv(DATABASE_PATH_ENV) or DEFAULT_DATABASE_PATH
    return Path(configured_path).expanduser()


@contextmanager
def connect(
    database_path: str | Path | None = None,
    *,
    read_only: bool = False,
) -> Iterator[sqlite3.Connection]:
    """Yield a transactional SQLite connection and always close it."""
    path = resolve_database_path(database_path)

    if read_only:
        connection = sqlite3.connect(
            f"{path.resolve().as_uri()}?mode=ro",
            uri=True,
            timeout=BUSY_TIMEOUT_MS / 1_000,
        )
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(path, timeout=BUSY_TIMEOUT_MS / 1_000)

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    if not read_only:
        connection.execute("PRAGMA journal_mode = WAL")

    try:
        yield connection
        if not read_only:
            connection.commit()
    except Exception:
        if not read_only:
            connection.rollback()
        raise
    finally:
        connection.close()


def init_db(connection: sqlite3.Connection) -> None:
    """Create the initial Conclusion schema if it does not exist."""
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS conclusions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL CHECK (
                length(trim(title, ' ' || char(9) || char(10) || char(13))) > 0
            ),
            question TEXT NOT NULL CHECK (
                length(trim(question, ' ' || char(9) || char(10) || char(13))) > 0
            ),
            conclusion TEXT NOT NULL CHECK (
                length(trim(conclusion, ' ' || char(9) || char(10) || char(13))) > 0
            ),
            reason TEXT NOT NULL CHECK (
                length(trim(reason, ' ' || char(9) || char(10) || char(13))) > 0
            ),
            tradeoffs TEXT NOT NULL DEFAULT '',
            conditions TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL CHECK (
                length(trim(category, ' ' || char(9) || char(10) || char(13))) > 0
            ),
            confidence TEXT NOT NULL CHECK (confidence IN ('High', 'Medium', 'Low')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_conclusions_category
        ON conclusions(category);

        CREATE INDEX IF NOT EXISTS idx_conclusions_updated_at
        ON conclusions(updated_at DESC);

        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL CHECK (
                length(trim(name, ' ' || char(9) || char(10) || char(13))) > 0
            ),
            normalized_name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS conclusion_tags (
            conclusion_id INTEGER NOT NULL REFERENCES conclusions(id) ON DELETE CASCADE,
            tag_id INTEGER NOT NULL REFERENCES tags(id),
            position INTEGER NOT NULL CHECK (position >= 0),
            PRIMARY KEY (conclusion_id, tag_id),
            UNIQUE (conclusion_id, position)
        );

        CREATE INDEX IF NOT EXISTS idx_conclusion_tags_tag_id
        ON conclusion_tags(tag_id);
        """
    )

    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(conclusions)").fetchall()
    }
    if "conditions" not in columns:
        connection.execute(
            "ALTER TABLE conclusions ADD COLUMN conditions TEXT NOT NULL DEFAULT ''"
        )
    connection.commit()


def create_conclusion(
    connection: sqlite3.Connection,
    values: Mapping[str, Any],
) -> dict[str, Any]:
    """Insert and return one Conclusion inside the caller's transaction."""
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    parameters = {
        "title": values["title"],
        "question": values["question"],
        "conclusion": values["conclusion"],
        "reason": values["reason"],
        "tradeoffs": values.get("tradeoffs", ""),
        "conditions": values.get("conditions", ""),
        "category": values["category"],
        "confidence": values["confidence"],
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    cursor = connection.execute(
        """
        INSERT INTO conclusions (
            title, question, conclusion, reason, tradeoffs, conditions,
            category, confidence, created_at, updated_at
        )
        VALUES (
            :title, :question, :conclusion, :reason, :tradeoffs, :conditions,
            :category, :confidence, :created_at, :updated_at
        )
        """,
        parameters,
    )
    row = connection.execute(
        "SELECT * FROM conclusions WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    if row is None:  # pragma: no cover - SQLite guarantees lastrowid for this insert
        raise RuntimeError("Created Conclusion could not be loaded")
    conclusion_id = int(row["id"])
    _replace_conclusion_tags(connection, conclusion_id, values.get("tags", []))
    return _records_with_tags(connection, [row])[0]


def _replace_conclusion_tags(
    connection: sqlite3.Connection,
    conclusion_id: int,
    tags: list[str],
) -> None:
    """Replace one Conclusion's ordered tags inside the caller's transaction."""
    connection.execute("DELETE FROM conclusion_tags WHERE conclusion_id = ?", (conclusion_id,))
    for position, name in enumerate(tags):
        normalized_name = name.casefold()
        connection.execute(
            """
            INSERT INTO tags (name, normalized_name)
            VALUES (?, ?)
            ON CONFLICT(normalized_name) DO NOTHING
            """,
            (name, normalized_name),
        )
        tag = connection.execute(
            "SELECT id FROM tags WHERE normalized_name = ?",
            (normalized_name,),
        ).fetchone()
        if tag is None:  # pragma: no cover - insert/select invariant
            raise RuntimeError("Tag could not be loaded")
        connection.execute(
            """
            INSERT INTO conclusion_tags (conclusion_id, tag_id, position)
            VALUES (?, ?, ?)
            """,
            (conclusion_id, tag["id"], position),
        )


def _records_with_tags(
    connection: sqlite3.Connection,
    rows: list[sqlite3.Row],
) -> list[dict[str, Any]]:
    """Serialize Conclusion rows with their ordered tag names in one extra query."""
    records = [dict(row) for row in rows]
    if not records:
        return records

    by_id = {int(record["id"]): record for record in records}
    for record in records:
        record["tags"] = []

    placeholders = ", ".join("?" for _ in by_id)
    tag_rows = connection.execute(
        f"""
        SELECT ct.conclusion_id, t.name
        FROM conclusion_tags AS ct
        JOIN tags AS t ON t.id = ct.tag_id
        WHERE ct.conclusion_id IN ({placeholders})
        ORDER BY ct.conclusion_id, ct.position
        """,
        tuple(by_id),
    ).fetchall()
    for tag_row in tag_rows:
        by_id[int(tag_row["conclusion_id"])]["tags"].append(tag_row["name"])
    return records


def list_conclusions(
    connection: sqlite3.Connection,
    *,
    limit: int = 50,
) -> dict[str, Any]:
    """Return a bounded page of Conclusions, newest first."""
    total = connection.execute("SELECT count(*) FROM conclusions").fetchone()[0]
    rows = connection.execute(
        """
        SELECT *
        FROM conclusions
        ORDER BY updated_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return {
        "count": total,
        "returned": len(rows),
        "items": _records_with_tags(connection, rows),
    }


def get_conclusion(
    connection: sqlite3.Connection,
    conclusion_id: int,
) -> dict[str, Any] | None:
    """Return one Conclusion by ID, or None when it does not exist."""
    row = connection.execute(
        "SELECT * FROM conclusions WHERE id = ?",
        (conclusion_id,),
    ).fetchone()
    return _records_with_tags(connection, [row])[0] if row is not None else None
