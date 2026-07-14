"""FastAPI application entry point for Conclusion."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, status

from app.db import connect, create_conclusion, get_conclusion, init_db, list_conclusions
from app.schemas import ConclusionCreate, ConclusionList, ConclusionRecord


def create_app(database_path: str | Path | None = None) -> FastAPI:
    """Create the Conclusion HTTP application."""

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        with connect(database_path) as connection:
            init_db(connection)
        yield

    app = FastAPI(title="Conclusion", lifespan=lifespan)

    @app.get("/api/health", tags=["health"])
    def health() -> dict[str, bool]:
        return {"ok": True}

    @app.post(
        "/api/conclusions",
        response_model=ConclusionRecord,
        status_code=status.HTTP_201_CREATED,
        tags=["conclusions"],
    )
    def post_conclusion(payload: ConclusionCreate) -> dict[str, object]:
        with connect(database_path) as connection:
            return create_conclusion(connection, payload.model_dump())

    @app.get(
        "/api/conclusions",
        response_model=ConclusionList,
        tags=["conclusions"],
    )
    def get_conclusions(
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, object]:
        with connect(database_path, read_only=True) as connection:
            return list_conclusions(connection, limit=limit)

    @app.get(
        "/api/conclusions/{conclusion_id}",
        response_model=ConclusionRecord,
        tags=["conclusions"],
    )
    def get_conclusion_by_id(conclusion_id: int) -> dict[str, object]:
        with connect(database_path, read_only=True) as connection:
            record = get_conclusion(connection, conclusion_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Conclusion not found")
        return record

    return app


app = create_app()
