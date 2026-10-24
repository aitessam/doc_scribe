from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, List

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.utils.logger import get_logger
from config.settings import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance.

    Returns:
        FastAPI: Configured FastAPI application.
    """

    settings = get_settings()
    logger = get_logger(__name__)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        """Log a startup message with the server URL."""

        url = f"http://{settings.API_HOST}:{settings.API_PORT}"
        logger.info("DocScribe API starting at %s", url)
        yield

    app = FastAPI(title="DocScribe API", version="1.0.0", lifespan=lifespan)

    # Allow common localhost origins for local development.
    allowed_origins: List[str] = [
        "http://localhost",
        "http://localhost:8000",
        "http://localhost:8501",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8501",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    return app


app = create_app()


if __name__ == "__main__":
    _settings = get_settings()
    uvicorn.run(
        "server:app",
        host=_settings.API_HOST,
        port=_settings.API_PORT,
        reload=False,
    )
