"""FastAPI application entry point for Conclusion."""

from __future__ import annotations

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create the Conclusion HTTP application."""
    app = FastAPI(title="Conclusion")

    @app.get("/api/health", tags=["health"])
    def health() -> dict[str, bool]:
        return {"ok": True}

    return app


app = create_app()

