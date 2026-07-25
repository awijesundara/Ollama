import secrets

import asyncpg
from fastapi import Request, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.runtime import services


def register_http_endpoints(app: object) -> None:
    @app.get(  # type: ignore[attr-defined,untyped-decorator]
        "/healthz", include_in_schema=False
    )
    async def health() -> Response:
        try:
            await services.start()
            storage = await services.storage_health_check()
            ollama = await services.ollama.health_check()
        except (asyncpg.PostgresError, OSError, RuntimeError):
            storage = False
            ollama = False
        healthy = storage and ollama
        return Response(
            content='{"healthy":true}' if healthy else '{"healthy":false}',
            media_type="application/json",
            status_code=status.HTTP_200_OK
            if healthy
            else status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @app.get(  # type: ignore[attr-defined,untyped-decorator]
        "/metrics", include_in_schema=False
    )
    async def metrics(request: Request) -> Response:
        if not services.settings.METRICS_ENABLED:
            return Response(status_code=status.HTTP_404_NOT_FOUND)
        expected = services.settings.METRICS_AUTH_TOKEN
        authorization = request.headers.get("authorization", "")
        supplied = (
            authorization.removeprefix("Bearer ").strip()
            if authorization.startswith("Bearer ")
            else ""
        )
        if expected is None or not secrets.compare_digest(
            supplied, expected.get_secret_value()
        ):
            return Response(status_code=status.HTTP_401_UNAUTHORIZED)
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
