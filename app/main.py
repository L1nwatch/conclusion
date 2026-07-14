"""FastAPI application entry point for Conclusion."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, status

from app.db import connect, create_conclusion, init_db
from app.schemas import ConclusionCreate, ConclusionRecord


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

    return app


app = create_app()
