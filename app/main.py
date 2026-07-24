"""FastAPI application entry point for Conclusion."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.db import (
    ConclusionUpdateConflictError,
    DecisionModelAlreadyExistsError,
    DecisionModelUpdateConflictError,
    UnknownDecisionModelError,
    connect,
    create_conclusion,
    create_decision_model,
    delete_conclusion,
    get_conclusion,
    get_decision_model,
    init_db,
    list_decision_models,
    search_conclusions,
    update_conclusion,
    update_decision_model,
)
from app.schemas import (
    ConclusionCreate,
    ConclusionList,
    ConclusionRecord,
    ConclusionUpdate,
    DecisionModelCreate,
    DecisionModelList,
    DecisionModelRecord,
    DecisionModelUpdate,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"


def create_app(
    database_path: str | Path | None = None,
    frontend_dist: str | Path | None = FRONTEND_DIST,
) -> FastAPI:
    """Create the Conclusion HTTP application."""

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        with connect(database_path) as connection:
            init_db(connection)
        yield

    app = FastAPI(title="Conclusion", lifespan=lifespan)
    frontend_path = Path(frontend_dist) if frontend_dist is not None else None
    assets_path = frontend_path / "assets" if frontend_path is not None else None
    if assets_path is not None and assets_path.exists():
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

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
        try:
            with connect(database_path) as connection:
                return create_conclusion(connection, payload.model_dump())
        except UnknownDecisionModelError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post(
        "/api/decision-models",
        response_model=DecisionModelRecord,
        status_code=status.HTTP_201_CREATED,
        tags=["decision-models"],
    )
    def post_decision_model(payload: DecisionModelCreate) -> dict[str, object]:
        try:
            with connect(database_path) as connection:
                return create_decision_model(connection, payload.model_dump())
        except DecisionModelAlreadyExistsError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Decision model ID already exists",
            ) from error

    @app.get(
        "/api/decision-models",
        response_model=DecisionModelList,
        tags=["decision-models"],
    )
    def get_decision_models(
        include_history: bool = Query(default=False, alias="includeHistory"),
    ) -> dict[str, object]:
        with connect(database_path, read_only=True) as connection:
            return list_decision_models(connection, include_history=include_history)

    @app.get(
        "/api/decision-models/{model_id}",
        response_model=DecisionModelRecord,
        tags=["decision-models"],
    )
    def get_decision_model_by_id(
        model_id: str,
        version: int | None = Query(default=None, ge=1),
    ) -> dict[str, object]:
        with connect(database_path, read_only=True) as connection:
            record = get_decision_model(connection, model_id, version)
        if record is None:
            raise HTTPException(status_code=404, detail="Decision model not found")
        return record

    @app.patch(
        "/api/decision-models/{model_id}",
        response_model=DecisionModelRecord,
        tags=["decision-models"],
    )
    def patch_decision_model(
        model_id: str,
        payload: DecisionModelUpdate,
    ) -> dict[str, object]:
        try:
            with connect(database_path) as connection:
                record = update_decision_model(
                    connection,
                    model_id,
                    payload.model_dump(exclude={"expected_version"}),
                    expected_version=payload.expected_version,
                )
        except DecisionModelUpdateConflictError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": str(error),
                    "currentVersion": error.current_version,
                },
            ) from error
        if record is None:
            raise HTTPException(status_code=404, detail="Decision model not found")
        return record

    @app.get(
        "/api/conclusions",
        response_model=ConclusionList,
        tags=["conclusions"],
    )
    def get_conclusions(
        query: str | None = Query(default=None, min_length=1, max_length=200),
        category: str | None = Query(default=None, min_length=1, max_length=100),
        tag: str | None = Query(default=None, min_length=1, max_length=50),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> dict[str, object]:
        with connect(database_path, read_only=True) as connection:
            return search_conclusions(
                connection,
                query=query,
                category=category,
                tag=tag,
                limit=limit,
            )

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

    @app.patch(
        "/api/conclusions/{conclusion_id}",
        response_model=ConclusionRecord,
        tags=["conclusions"],
    )
    def patch_conclusion(
        conclusion_id: int,
        payload: ConclusionUpdate,
    ) -> dict[str, object]:
        values = payload.model_dump(
            exclude_unset=True,
            exclude={"expected_updated_at"},
        )
        try:
            with connect(database_path) as connection:
                record = update_conclusion(
                    connection,
                    conclusion_id,
                    values,
                    expected_updated_at=payload.expected_updated_at,
                )
        except UnknownDecisionModelError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except ConclusionUpdateConflictError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": str(error),
                    "currentUpdatedAt": error.current_updated_at,
                },
            ) from error
        if record is None:
            raise HTTPException(status_code=404, detail="Conclusion not found")
        return record

    @app.delete(
        "/api/conclusions/{conclusion_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        response_class=Response,
        tags=["conclusions"],
    )
    def delete_conclusion_by_id(conclusion_id: int) -> Response:
        with connect(database_path) as connection:
            deleted = delete_conclusion(connection, conclusion_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Conclusion not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        index_html = frontend_path / "index.html" if frontend_path is not None else None
        if index_html is not None and index_html.exists():
            return FileResponse(index_html)
        return JSONResponse(
            status_code=503,
            content={"detail": "Frontend build not found. Run the frontend build first."},
        )

    return app


app = create_app()
