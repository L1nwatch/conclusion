"""SQLite connection and schema management for Conclusion."""

from __future__ import annotations

import json
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
BUILTIN_DECISION_MODELS = (
    {
        "id": "time-horizons",
        "name": "时间尺度",
        "short_name": "10H · 10D · 10M · 10Y",
        "description": "把眼前情绪拉远，观察这个决定在不同时间尺度上的影响。",
        "prompts": [
            {"key": "tenHours", "label": "10 小时后", "placeholder": "今天晚些时候，我会怎么看？"},
            {"key": "tenDays", "label": "10 天后", "placeholder": "短期影响会是什么？"},
            {"key": "tenMonths", "label": "10 个月后", "placeholder": "它会带来什么持续变化？"},
            {"key": "tenYears", "label": "10 年后", "placeholder": "长期回看，什么真正重要？"},
        ],
        "source_name": "Suzy Welch 10-10-10",
        "source_url": "https://suzywelch.com/books/",
    },
    {
        "id": "scenario-range",
        "name": "情景边界",
        "short_name": "BEST · LIKELY · WORST",
        "description": "同时看到上行空间、最可能结果和可以承受的下行风险。",
        "prompts": [
            {"key": "bestCase", "label": "最好情况", "placeholder": "合理范围内，最好会发生什么？"},
            {"key": "likelyCase", "label": "最可能情况", "placeholder": "不乐观也不悲观，最可能怎样？"},
            {"key": "worstCase", "label": "最坏情况", "placeholder": "合理的最坏结果是什么？"},
            {"key": "safeguards", "label": "保护措施", "placeholder": "如何降低损失，或者保留退路？"},
        ],
        "source_name": "",
        "source_url": "",
    },
    {
        "id": "munger-checklist",
        "name": "芒格式多模型检查",
        "short_name": "LATTICEWORK CHECK",
        "description": "受多模型思维启发，从激励、反演和认知盲点检查遗漏。",
        "prompts": [
            {"key": "incentives", "label": "激励", "placeholder": "谁希望我做什么？各方真实激励是什么？"},
            {"key": "opportunityCost", "label": "机会成本", "placeholder": "选择它，就放弃了什么更好的用途？"},
            {"key": "inversion", "label": "反演", "placeholder": "怎样做几乎一定会失败？现在是否正在这样做？"},
            {"key": "secondOrderEffects", "label": "二阶效应", "placeholder": "然后呢？这个结果还会继续导致什么？"},
            {"key": "circleOfCompetence", "label": "能力圈", "placeholder": "我真正知道什么？哪些只是在猜？"},
            {"key": "disconfirmingEvidence", "label": "反方证据", "placeholder": "什么事实会证明我错了？我是否主动找过？"},
        ],
        "source_name": "Charlie Munger — Elementary Worldly Wisdom",
        "source_url": "https://www.ivey.uwo.ca/media/2975916/the-best-of-charlie-munger-1994-2011.pdf",
    },
)
UPDATE_FIELDS = (
    "title",
    "question",
    "conclusion",
    "reason",
    "tradeoffs",
    "conditions",
    "category",
    "confidence",
)


class ConclusionUpdateConflictError(Exception):
    """Raised when an update uses a stale updated_at value."""

    def __init__(self, current_updated_at: str) -> None:
        super().__init__("Conclusion was modified by another writer")
        self.current_updated_at = current_updated_at


class DecisionModelAlreadyExistsError(Exception):
    """Raised when a new decision model reuses an existing stable ID."""


class UnknownDecisionModelError(Exception):
    """Raised when analysis references a model or prompt that is not registered."""


def utc_timestamp() -> str:
    """Return a UTC timestamp precise enough for optimistic concurrency checks."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


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

        CREATE TABLE IF NOT EXISTS decision_analyses (
            conclusion_id INTEGER PRIMARY KEY
                REFERENCES conclusions(id) ON DELETE CASCADE,
            schema_version INTEGER NOT NULL CHECK (schema_version = 1),
            analysis_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS decision_models (
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
        );
        """
    )

    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(conclusions)").fetchall()
    }
    if "conditions" not in columns:
        connection.execute(
            "ALTER TABLE conclusions ADD COLUMN conditions TEXT NOT NULL DEFAULT ''"
        )
    _seed_builtin_decision_models(connection)
    connection.commit()


def _seed_builtin_decision_models(connection: sqlite3.Connection) -> None:
    """Register built-in models once without overwriting future stored records."""
    timestamp = utc_timestamp()
    for model in BUILTIN_DECISION_MODELS:
        connection.execute(
            """
            INSERT INTO decision_models (
                id, version, name, short_name, description, prompts_json,
                source_name, source_url, is_builtin, created_at, updated_at
            ) VALUES (?, 1, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(id) DO NOTHING
            """,
            (
                model["id"],
                model["name"],
                model["short_name"],
                model["description"],
                json.dumps(model["prompts"], ensure_ascii=False, separators=(",", ":")),
                model["source_name"],
                model["source_url"],
                timestamp,
                timestamp,
            ),
        )


def create_conclusion(
    connection: sqlite3.Connection,
    values: Mapping[str, Any],
) -> dict[str, Any]:
    """Insert and return one Conclusion inside the caller's transaction."""
    timestamp = utc_timestamp()
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
    _replace_decision_analysis(
        connection,
        conclusion_id,
        values.get("decision_analysis", {"version": 1, "models": []}),
    )
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


def _replace_decision_analysis(
    connection: sqlite3.Connection,
    conclusion_id: int,
    analysis: Mapping[str, Any],
) -> None:
    """Replace one Conclusion's versioned decision analysis."""
    _validate_decision_analysis(connection, analysis)
    connection.execute(
        "DELETE FROM decision_analyses WHERE conclusion_id = ?",
        (conclusion_id,),
    )
    if not analysis.get("models"):
        return
    connection.execute(
        """
        INSERT INTO decision_analyses (conclusion_id, schema_version, analysis_json)
        VALUES (?, ?, ?)
        """,
        (
            conclusion_id,
            analysis["version"],
            json.dumps(analysis, ensure_ascii=False, separators=(",", ":")),
        ),
    )


def _validate_decision_analysis(
    connection: sqlite3.Connection,
    analysis: Mapping[str, Any],
) -> None:
    """Ensure every analysis answer matches a registered immutable model version."""
    for run in analysis.get("models", []):
        model_id = run["model_id"]
        model_version = run.get("model_version", 1)
        row = connection.execute(
            "SELECT version, prompts_json FROM decision_models WHERE id = ?",
            (model_id,),
        ).fetchone()
        if row is None or int(row["version"]) != model_version:
            raise UnknownDecisionModelError(
                f"Unknown decision model version: {model_id}@{model_version}"
            )
        prompt_keys = {prompt["key"] for prompt in json.loads(row["prompts_json"])}
        unknown_keys = set(run["answers"]) - prompt_keys
        if unknown_keys:
            raise UnknownDecisionModelError(
                f"Unknown prompts for {model_id}: {', '.join(sorted(unknown_keys))}"
            )


def _serialize_decision_model(row: sqlite3.Row) -> dict[str, Any]:
    record = dict(row)
    record["prompts"] = json.loads(record.pop("prompts_json"))
    record["is_builtin"] = bool(record["is_builtin"])
    return record


def list_decision_models(connection: sqlite3.Connection) -> dict[str, Any]:
    """Return all registered decision models in stable creation order."""
    rows = connection.execute(
        """
        SELECT *
        FROM decision_models
        ORDER BY CASE id
            WHEN 'time-horizons' THEN 0
            WHEN 'scenario-range' THEN 1
            WHEN 'munger-checklist' THEN 2
            ELSE 100
        END, created_at, id
        """
    ).fetchall()
    return {"count": len(rows), "items": [_serialize_decision_model(row) for row in rows]}


def get_decision_model(
    connection: sqlite3.Connection,
    model_id: str,
) -> dict[str, Any] | None:
    """Return one registered decision model by stable ID."""
    row = connection.execute(
        "SELECT * FROM decision_models WHERE id = ?",
        (model_id,),
    ).fetchone()
    return _serialize_decision_model(row) if row is not None else None


def create_decision_model(
    connection: sqlite3.Connection,
    values: Mapping[str, Any],
) -> dict[str, Any]:
    """Register one immutable version-one custom decision model."""
    timestamp = utc_timestamp()
    try:
        connection.execute(
            """
            INSERT INTO decision_models (
                id, version, name, short_name, description, prompts_json,
                source_name, source_url, is_builtin, created_at, updated_at
            ) VALUES (?, 1, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                values["id"],
                values["name"],
                values["short_name"],
                values["description"],
                json.dumps(values["prompts"], ensure_ascii=False, separators=(",", ":")),
                values.get("source_name", ""),
                values.get("source_url", ""),
                timestamp,
                timestamp,
            ),
        )
    except sqlite3.IntegrityError as error:
        if connection.execute(
            "SELECT 1 FROM decision_models WHERE id = ?", (values["id"],)
        ).fetchone():
            raise DecisionModelAlreadyExistsError(values["id"]) from error
        raise
    record = get_decision_model(connection, values["id"])
    if record is None:  # pragma: no cover - successful insert guarantees the row
        raise RuntimeError("Created decision model could not be loaded")
    return record


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
        record["decision_analysis"] = {"version": 1, "models": []}

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

    analysis_rows = connection.execute(
        f"""
        SELECT conclusion_id, analysis_json
        FROM decision_analyses
        WHERE conclusion_id IN ({placeholders})
        """,
        tuple(by_id),
    ).fetchall()
    for analysis_row in analysis_rows:
        by_id[int(analysis_row["conclusion_id"])]["decision_analysis"] = json.loads(
            analysis_row["analysis_json"]
        )
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


def update_conclusion(
    connection: sqlite3.Connection,
    conclusion_id: int,
    values: Mapping[str, Any],
    *,
    expected_updated_at: str,
) -> dict[str, Any] | None:
    """Partially update and return a Conclusion with optimistic concurrency."""
    parameters = {field: values[field] for field in UPDATE_FIELDS if field in values}
    parameters.update(
        {
            "id": conclusion_id,
            "expected_updated_at": expected_updated_at,
            "updated_at": utc_timestamp(),
        }
    )
    assignments = [f"{field} = :{field}" for field in parameters if field in UPDATE_FIELDS]
    assignments.append("updated_at = :updated_at")
    cursor = connection.execute(
        f"""
        UPDATE conclusions
        SET {", ".join(assignments)}
        WHERE id = :id AND updated_at = :expected_updated_at
        """,
        parameters,
    )
    if cursor.rowcount == 0:
        current = connection.execute(
            "SELECT updated_at FROM conclusions WHERE id = ?",
            (conclusion_id,),
        ).fetchone()
        if current is None:
            return None
        raise ConclusionUpdateConflictError(current["updated_at"])

    if "tags" in values:
        _replace_conclusion_tags(connection, conclusion_id, values["tags"])
    if "decision_analysis" in values:
        _replace_decision_analysis(
            connection,
            conclusion_id,
            values["decision_analysis"],
        )

    row = connection.execute(
        "SELECT * FROM conclusions WHERE id = ?",
        (conclusion_id,),
    ).fetchone()
    if row is None:  # pragma: no cover - the successful update guarantees the row
        raise RuntimeError("Updated Conclusion could not be loaded")
    return _records_with_tags(connection, [row])[0]
