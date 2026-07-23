import asyncpg
from fastapi import Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.runtime import services


def register_http_endpoints(app: object) -> None:
    @app.get("/healthz", include_in_schema=False)  # type: ignore[attr-defined]
    async def health() -> Response:
        try:
            await services.start()
            database = await services.database.health_check()
            ollama = await services.ollama.health_check()
        except (asyncpg.PostgresError, OSError, RuntimeError):
            database = False
            ollama = False
        healthy = database and ollama
        return Response(
            content='{"healthy":true}' if healthy else '{"healthy":false}',
            media_type="application/json",
            status_code=status.HTTP_200_OK
            if healthy
            else status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @app.get("/metrics", include_in_schema=False)  # type: ignore[attr-defined]
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
