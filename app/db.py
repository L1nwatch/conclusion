"""SQLite connection and schema management for Conclusion."""

from __future__ import annotations

import json
import os
import sqlite3
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping
from uuid import uuid4


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE_PATH = ROOT_DIR / "data" / "conclusion.sqlite3"
DATABASE_PATH_ENV = "CONCLUSION_DATABASE_PATH"
BUSY_TIMEOUT_MS = 5_000
BUILTIN_DECISION_MODELS = (
    {
        "id": "precedent-review",
        "name": "经验之谈",
        "explanation": "先查找相似的既有 Conclusion，复用已经验证过的经验，同时指出这次有什么关键差异。没有先例时直接说明，不要编造。",
    },
    {
        "id": "munger-checklist",
        "name": "穷查理原则检查",
        "explanation": "用芒格式检查表快速扫一遍能力圈、激励、风险、机会成本、事实依据和心理偏差，找出最容易忽略的一项。例如促销带来的紧迫感，可能不是购买理由。",
    },
    {
        "id": "scenario-range",
        "name": "极端思考",
        "explanation": "分别看合理的最好、最可能和最坏结果，重点确认最坏结果能否承受，以及能否预留退路。不要把极小概率的幻想当成主要情景。",
    },
    {
        "id": "time-horizons",
        "name": "时间尺度",
        "explanation": "分别从 10 小时、10 天、10 个月和 10 年后回看这个决定，区分短期情绪与长期影响。例如今天的不舍，十个月后可能已经无关紧要。",
    },
    {
        "id": "inversion",
        "name": "逆向思考",
        "explanation": "先问怎样做一定会把事情搞砸，再检查当前方案是否已经踩中这些失败条件。优先切断最可能、代价最大的失败路径。",
    },
    {
        "id": "inaction-value",
        "name": "不行动分析",
        "explanation": "把“不做”也当作一个真实选项，比较它能避免的成本、会错失的价值，以及继续等待的代价。必要时给出明确的行动触发条件。",
    },
    {
        "id": "reversibility",
        "name": "可逆性判断",
        "explanation": "判断这是难以撤回的单向门，还是可以低成本试错的双向门。可逆决定优先做小实验，不可逆决定才投入更多调查和审慎。",
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


class DecisionModelUpdateConflictError(Exception):
    """Raised when an update uses a stale model updated_at value."""

    def __init__(self, current_updated_at: str) -> None:
        super().__init__("Decision model was modified by another writer")
        self.current_updated_at = current_updated_at


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
            name TEXT NOT NULL,
            short_name TEXT NOT NULL,
            description TEXT NOT NULL,
            prompts_json TEXT NOT NULL,
            source_name TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '',
            is_builtin INTEGER NOT NULL CHECK (is_builtin IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT
        );

        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL CHECK(length(trim(title)) > 0),
            description TEXT,
            status TEXT NOT NULL CHECK(status IN ('Draft', 'Thinking', 'Decided')),
            version INTEGER NOT NULL DEFAULT 1 CHECK(version >= 1),
            root_id TEXT NOT NULL,
            nodes_json TEXT NOT NULL CHECK(json_valid(nodes_json)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_decisions_updated_at
        ON decisions(updated_at DESC, id DESC);
        """
    )

    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(conclusions)").fetchall()
    }
    if "conditions" not in columns:
        connection.execute(
            "ALTER TABLE conclusions ADD COLUMN conditions TEXT NOT NULL DEFAULT ''"
        )
    _migrate_decision_model_soft_delete(connection)
    _migrate_decision_models_to_single_row(connection)
    _migrate_decision_analysis_model_versions(connection)
    _seed_builtin_decision_models(connection)
    connection.commit()


class DecisionNotFoundError(Exception):
    """The requested Decision does not exist."""


class InvalidDecisionTreeError(ValueError):
    """A node operation would violate the tree's structure."""


class DecisionVersionConflictError(Exception):
    def __init__(self, current_version: int) -> None:
        super().__init__("Decision was modified by another writer")
        self.current_version = current_version


DECISION_COLUMNS = "id, title, description, status, version, created_at, updated_at"


def list_decisions(
    connection: sqlite3.Connection,
    *,
    query: str | None,
    status: str | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    connection.create_function("casefold_title", 1, str.casefold, deterministic=True)
    filters = "WHERE (? IS NULL OR instr(casefold_title(title), ?) > 0) AND (? IS NULL OR status = ?)"
    search = query.strip().casefold() if query else None
    params = (search, search, status, status)
    with connection:
        connection.execute("BEGIN")
        count = connection.execute(f"SELECT count(*) FROM decisions {filters}", params).fetchone()[0]
        rows = connection.execute(
            f"""SELECT {DECISION_COLUMNS} FROM decisions {filters}
            ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?""",
            (*params, limit, offset),
        )
        return {"count": count, "offset": offset, "items": [dict(row) for row in rows]}


def get_decision(connection: sqlite3.Connection, decision_id: int) -> dict[str, Any]:
    row = connection.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,)).fetchone()
    if row is None:
        raise DecisionNotFoundError(f"Decision {decision_id} was not found")
    record = dict(row)
    record["nodes"] = [
        {**node, "decision_id": decision_id} for node in json.loads(record.pop("nodes_json"))
    ]
    return record


def _tree_index(
    nodes: list[dict[str, Any]],
) -> tuple[str, dict[str, dict[str, Any]], dict[str | None, list[str]]]:
    by_id = {node["id"]: node for node in nodes}
    if len(by_id) != len(nodes):
        raise InvalidDecisionTreeError("Node IDs must be unique within the Decision")
    children: dict[str | None, list[str]] = defaultdict(list)
    for node in nodes:
        parent_id = node["parent_id"]
        if parent_id is not None and parent_id not in by_id:
            raise InvalidDecisionTreeError(f"Parent node {parent_id} was not found in this Decision")
        children[parent_id].append(node["id"])
    if len(children[None]) != 1:
        raise InvalidDecisionTreeError("A Decision must have exactly one root node")
    for siblings in children.values():
        siblings.sort(key=lambda node_id: by_id[node_id]["order"])
        if any(by_id[node_id]["order"] != index for index, node_id in enumerate(siblings)):
            raise InvalidDecisionTreeError("Sibling order must be consecutive and start at 0")
    root_id = children[None][0]
    pending = [root_id]
    visited = 0
    while pending:
        visited += 1
        pending.extend(children.get(pending.pop(), ()))
    if visited != len(nodes):
        raise InvalidDecisionTreeError("The tree contains a cycle disconnected from its root")
    return root_id, by_id, children


def _encode_decision_nodes(
    nodes: list[dict[str, Any]], previous: list[dict[str, Any]], now: str
) -> str:
    old_nodes = {node["id"]: node for node in previous}
    encoded = []
    for node in nodes:
        old = old_nodes.get(node["id"])
        unchanged = old and all(old[key] == value for key, value in node.items())
        encoded.append({
            **node,
            "created_at": old["created_at"] if old else now,
            "updated_at": old["updated_at"] if unchanged else now,
        })
    return json.dumps(encoded, ensure_ascii=False, allow_nan=False)


def create_decision(connection: sqlite3.Connection, values: dict[str, Any]) -> dict[str, Any]:
    nodes = values["nodes"]
    if nodes is None:
        nodes = [{
            "id": uuid4().hex, "parent_id": None, "text": values["title"],
            "description": None, "type": "Topic", "order": 0,
            "position_x": None, "position_y": None, "collapsed": False,
        }]
    root_id, _, _ = _tree_index(nodes)
    now = utc_timestamp()
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            """INSERT INTO decisions (title, description, status, root_id, nodes_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (values["title"], values["description"], values["status"], root_id,
             _encode_decision_nodes(nodes, [], now), now, now),
        )
        return get_decision(connection, cursor.lastrowid)


def _check_decision_version(current_version: int, expected_version: int) -> None:
    if current_version != expected_version:
        raise DecisionVersionConflictError(current_version)


def update_decision(
    connection: sqlite3.Connection, decision_id: int, expected_version: int, changes: dict[str, Any]
) -> dict[str, Any]:
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        record = connection.execute(
            f"SELECT {DECISION_COLUMNS} FROM decisions WHERE id = ?", (decision_id,)
        ).fetchone()
        if record is None:
            raise DecisionNotFoundError(f"Decision {decision_id} was not found")
        _check_decision_version(record["version"], expected_version)
        merged = dict(record) | changes
        connection.execute(
            """UPDATE decisions SET title = ?, description = ?, status = ?,
            version = version + 1, updated_at = ? WHERE id = ?""",
            (merged["title"], merged["description"], merged["status"], utc_timestamp(), decision_id),
        )
        return get_decision(connection, decision_id)


def _apply_tree_operations(
    nodes: list[dict[str, Any]], operations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    root_id, by_id, children = _tree_index(nodes)

    def renumber(siblings: list[str]) -> None:
        for order, node_id in enumerate(siblings):
            by_id[node_id]["order"] = order

    for operation in operations:
        action, node_id = operation["op"], operation["id"]
        node = by_id.get(node_id)
        if action == "add":
            if node is not None:
                raise InvalidDecisionTreeError(f"Node {node_id} already exists")
        elif node is None:
            raise InvalidDecisionTreeError(f"Node {node_id} was not found in this Decision")
        elif action == "update":
            node.update(operation["changes"])
            continue
        elif node_id == root_id:
            raise InvalidDecisionTreeError("The root node cannot be moved or deleted")

        if node is not None:
            siblings = children[node["parent_id"]]
            siblings.remove(node_id)
            renumber(siblings)
        if action == "delete":
            pending = [node_id]
            while pending:
                removed = pending.pop()
                pending.extend(children.pop(removed, ()))
                del by_id[removed]
            continue

        parent_id = operation["parent_id"]
        if parent_id not in by_id:
            raise InvalidDecisionTreeError(f"Parent node {parent_id} was not found in this Decision")
        if action == "move":
            ancestor = parent_id
            while ancestor is not None:
                if ancestor == node_id:
                    raise InvalidDecisionTreeError(f"Moving node {node_id} here would create a cycle")
                ancestor = by_id[ancestor]["parent_id"]
            node["parent_id"] = parent_id
        else:
            by_id[node_id] = {
                "id": node_id, "parent_id": parent_id, "text": operation["text"],
                "description": operation.get("description"), "type": operation.get("type"),
                "order": 0, "position_x": None, "position_y": None, "collapsed": False,
            }
        destination = children[parent_id]
        order = operation.get("order")
        if order is None:
            order = len(destination)
        if order > len(destination):
            raise InvalidDecisionTreeError(f"Order {order} is out of range under parent {parent_id}")
        destination.insert(order, node_id)
        renumber(destination)
    return list(by_id.values())


def update_decision_tree(
    connection: sqlite3.Connection, decision_id: int, values: dict[str, Any]
) -> dict[str, Any]:
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        stored = connection.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,)).fetchone()
        if stored is None:
            raise DecisionNotFoundError(f"Decision {decision_id} was not found")
        _check_decision_version(stored["version"], values["expected_version"])
        previous = json.loads(stored["nodes_json"])
        nodes = values["nodes"]
        if nodes is None:
            nodes = [
                {key: value for key, value in node.items() if key not in ("created_at", "updated_at")}
                for node in previous
            ]
            nodes = _apply_tree_operations(nodes, values["operations"])
        root_id, _, _ = _tree_index(nodes)
        if root_id != stored["root_id"]:
            raise InvalidDecisionTreeError("The root node ID must be preserved")
        now = utc_timestamp()
        connection.execute(
            """UPDATE decisions SET nodes_json = ?, version = version + 1, updated_at = ?
            WHERE id = ?""",
            (_encode_decision_nodes(nodes, previous, now), now, decision_id),
        )
        return get_decision(connection, decision_id)


def delete_decision(
    connection: sqlite3.Connection, decision_id: int, expected_version: int
) -> None:
    with connection:
        connection.execute("BEGIN IMMEDIATE")
        record = connection.execute("SELECT version FROM decisions WHERE id = ?", (decision_id,)).fetchone()
        if record is None:
            raise DecisionNotFoundError(f"Decision {decision_id} was not found")
        _check_decision_version(record["version"], expected_version)
        connection.execute("DELETE FROM decisions WHERE id = ?", (decision_id,))


def _migrate_decision_models_to_single_row(connection: sqlite3.Connection) -> None:
    """Collapse a versioned registry to the latest definition for each stable ID."""
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(decision_models)").fetchall()
    }
    primary_key = {
        row["name"]: int(row["pk"])
        for row in connection.execute("PRAGMA table_info(decision_models)").fetchall()
        if int(row["pk"]) > 0
    }
    if "version" not in columns and primary_key == {"id": 1}:
        return

    connection.executescript(
        """
        ALTER TABLE decision_models RENAME TO decision_models_legacy;

        CREATE TABLE decision_models (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            short_name TEXT NOT NULL,
            description TEXT NOT NULL,
            prompts_json TEXT NOT NULL,
            source_name TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '',
            is_builtin INTEGER NOT NULL CHECK (is_builtin IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            deleted_at TEXT
        );

        INSERT INTO decision_models (
            id, name, short_name, description, prompts_json,
            source_name, source_url, is_builtin, created_at, updated_at, deleted_at
        )
        SELECT
            model.id, model.name, model.short_name, model.description, model.prompts_json,
            model.source_name, model.source_url, model.is_builtin,
            model.created_at, model.updated_at, model.deleted_at
        FROM decision_models_legacy AS model
        JOIN (
            SELECT id, max(version) AS latest_version
            FROM decision_models_legacy
            GROUP BY id
        ) AS latest
          ON latest.id = model.id AND latest.latest_version = model.version;

        DROP TABLE decision_models_legacy;
        """
    )


def _migrate_decision_model_soft_delete(connection: sqlite3.Connection) -> None:
    """Add the tombstone used by website-only model deletion."""
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(decision_models)").fetchall()
    }
    if "deleted_at" not in columns:
        connection.execute("ALTER TABLE decision_models ADD COLUMN deleted_at TEXT")


def _migrate_decision_analysis_model_versions(connection: sqlite3.Connection) -> None:
    """Remove obsolete per-model version keys from saved analysis JSON."""
    rows = connection.execute(
        "SELECT conclusion_id, analysis_json FROM decision_analyses"
    ).fetchall()
    for row in rows:
        analysis = json.loads(row["analysis_json"])
        changed = False
        for run in analysis.get("models", []):
            for key in ("model_version", "modelVersion"):
                if key in run:
                    run.pop(key)
                    changed = True
        if changed:
            connection.execute(
                "UPDATE decision_analyses SET analysis_json = ? WHERE conclusion_id = ?",
                (
                    json.dumps(analysis, ensure_ascii=False, separators=(",", ":")),
                    row["conclusion_id"],
                ),
            )


def _seed_builtin_decision_models(connection: sqlite3.Connection) -> None:
    """Register built-ins when their IDs have never existed."""
    timestamp = utc_timestamp()
    for model in BUILTIN_DECISION_MODELS:
        connection.execute(
            """
            INSERT INTO decision_models (
                id, name, short_name, description, prompts_json,
                source_name, source_url, is_builtin, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(id) DO NOTHING
            """,
            (
                model["id"],
                model["name"],
                model["name"],
                model["explanation"],
                "[]",
                "",
                "",
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
    """Replace one Conclusion's structured decision analysis."""
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
    """Ensure every analysis answer matches a registered model."""
    for run in analysis.get("models", []):
        model_id = run["model_id"]
        row = connection.execute(
            """
            SELECT prompts_json
            FROM decision_models
            WHERE id = ?
            """,
            (model_id,),
        ).fetchone()
        if row is None:
            raise UnknownDecisionModelError(f"Unknown decision model: {model_id}")
        # ``analysis`` is the single current answer field. Stored prompt keys
        # remain accepted so old Conclusions can still be edited and saved.
        prompt_keys = {"analysis"} | {
            prompt["key"] for prompt in json.loads(row["prompts_json"])
        }
        unknown_keys = set(run["answers"]) - prompt_keys
        if unknown_keys:
            raise UnknownDecisionModelError(
                f"Unknown prompts for {model_id}: {', '.join(sorted(unknown_keys))}"
            )


def _serialize_decision_model(row: sqlite3.Row) -> dict[str, Any]:
    record = dict(row)
    record.pop("deleted_at")
    record["explanation"] = record.pop("description")
    record.pop("short_name")
    record.pop("prompts_json")
    record.pop("source_name")
    record.pop("source_url")
    record["is_builtin"] = bool(record["is_builtin"])
    return record


def list_decision_models(
    connection: sqlite3.Connection,
    *,
    include_deleted: bool = False,
) -> dict[str, Any]:
    """Return the single latest definition for each model."""
    where_sql = "" if include_deleted else "WHERE model.deleted_at IS NULL"
    rows = connection.execute(
        f"""
        SELECT model.*
        FROM decision_models AS model
        {where_sql}
        ORDER BY CASE model.id
            WHEN 'precedent-review' THEN 0
            WHEN 'munger-checklist' THEN 1
            WHEN 'scenario-range' THEN 2
            WHEN 'time-horizons' THEN 3
            WHEN 'inversion' THEN 4
            WHEN 'inaction-value' THEN 5
            WHEN 'reversibility' THEN 6
            ELSE 100
        END, model.created_at, model.id
        """
    ).fetchall()
    return {"count": len(rows), "items": [_serialize_decision_model(row) for row in rows]}


def get_decision_model(
    connection: sqlite3.Connection,
    model_id: str,
) -> dict[str, Any] | None:
    """Return the active definition for one model."""
    row = connection.execute(
        "SELECT * FROM decision_models WHERE id = ? AND deleted_at IS NULL",
        (model_id,),
    ).fetchone()
    return _serialize_decision_model(row) if row is not None else None


def create_decision_model(
    connection: sqlite3.Connection,
    values: Mapping[str, Any],
) -> dict[str, Any]:
    """Register one custom decision model."""
    timestamp = utc_timestamp()
    try:
        connection.execute(
            """
            INSERT INTO decision_models (
                id, name, short_name, description, prompts_json,
                source_name, source_url, is_builtin, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                values["id"],
                values["name"],
                values["name"],
                values["explanation"],
                "[]",
                "",
                "",
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


def update_decision_model(
    connection: sqlite3.Connection,
    model_id: str,
    values: Mapping[str, Any],
    *,
    expected_updated_at: str,
) -> dict[str, Any] | None:
    """Edit the active model definition in place with optimistic concurrency."""
    current = get_decision_model(connection, model_id)
    if current is None:
        return None
    cursor = connection.execute(
        """
        UPDATE decision_models
        SET name = ?, short_name = ?, description = ?, updated_at = ?
        WHERE id = ? AND updated_at = ? AND deleted_at IS NULL
        """,
        (
            values["name"],
            values["name"],
            values["explanation"],
            utc_timestamp(),
            model_id,
            expected_updated_at,
        ),
    )
    if cursor.rowcount == 0:
        latest = get_decision_model(connection, model_id)
        if latest is None:
            return None
        raise DecisionModelUpdateConflictError(latest["updated_at"])
    return get_decision_model(connection, model_id)


def delete_decision_model(
    connection: sqlite3.Connection,
    model_id: str,
) -> bool:
    """Soft-delete one model while keeping its latest definition readable internally."""
    timestamp = utc_timestamp()
    cursor = connection.execute(
        """
        UPDATE decision_models
        SET deleted_at = ?
        WHERE id = ? AND deleted_at IS NULL
        """,
        (timestamp, model_id),
    )
    return cursor.rowcount > 0


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
    return search_conclusions(connection, limit=limit)


def search_conclusions(
    connection: sqlite3.Connection,
    *,
    query: str | None = None,
    category: str | None = None,
    tag: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Search Conclusions by text, category, and tag, newest first."""
    clauses: list[str] = []
    parameters: list[Any] = []
    if query:
        clauses.append(
            "(title LIKE ? OR question LIKE ? OR conclusion LIKE ? OR reason LIKE ?)"
        )
        pattern = f"%{query}%"
        parameters.extend([pattern, pattern, pattern, pattern])
    if category:
        clauses.append("category = ? COLLATE NOCASE")
        parameters.append(category)
    if tag:
        clauses.append(
            """
            EXISTS (
                SELECT 1
                FROM conclusion_tags AS search_ct
                JOIN tags AS search_t ON search_t.id = search_ct.tag_id
                WHERE search_ct.conclusion_id = conclusions.id
                  AND search_t.normalized_name = ?
            )
            """
        )
        parameters.append(tag.casefold())

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    total = connection.execute(
        f"SELECT count(*) FROM conclusions {where_sql}",
        parameters,
    ).fetchone()[0]
    rows = connection.execute(
        f"""
        SELECT *
        FROM conclusions
        {where_sql}
        ORDER BY updated_at DESC, id DESC
        LIMIT ?
        """,
        (*parameters, limit),
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


def delete_conclusion(
    connection: sqlite3.Connection,
    conclusion_id: int,
) -> bool:
    """Delete one Conclusion and its cascading relations."""
    cursor = connection.execute(
        "DELETE FROM conclusions WHERE id = ?",
        (conclusion_id,),
    )
    return cursor.rowcount > 0


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
