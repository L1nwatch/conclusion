"""FastAPI application entry point for Conclusion."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.db import connect, init_db


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

    return app


app = create_app()
