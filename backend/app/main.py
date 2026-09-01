import uuid
from pathlib import Path

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func, select

from app.api import auth, dictionary, grammar, learning
from app.config import get_settings
from app.database import SessionFactory, database_is_ready
from app.logging import configure_logging
from app.models import DictionaryEntry

settings = get_settings()
configure_logging(settings.is_production)
logger = structlog.get_logger()

app = FastAPI(
    title="Ӟечбур API",
    summary="API для изучения удмуртской лексики и грамматики",
    version="2.0.0-rc.1",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Bot-Secret", "X-Request-ID"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))[:80]
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", method=request.method, error=str(exc))
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(dictionary.router, prefix=settings.api_prefix)
app.include_router(learning.router, prefix=settings.api_prefix)
app.include_router(grammar.router, prefix=settings.api_prefix)


@app.get("/health/live", tags=["health"])
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def readiness() -> JSONResponse:
    if not await database_is_ready():
        return JSONResponse(status_code=503, content={"status": "not-ready", "database": False})
    async with SessionFactory() as session:
        entries = await session.scalar(select(func.count()).select_from(DictionaryEntry)) or 0
    if entries == 0:
        return JSONResponse(
            status_code=503,
            content={"status": "not-ready", "database": True, "dictionary_entries": 0},
        )
    return JSONResponse(content={"status": "ok", "database": True, "dictionary_entries": entries})


Instrumentator(excluded_handlers=["/health/live", "/metrics"]).instrument(app).expose(
    app, include_in_schema=False
)

web_dir = Path(__file__).resolve().parents[2] / "web"
if web_dir.exists():
    app.mount("/assets", StaticFiles(directory=web_dir), name="assets")


@app.get("/{path:path}", include_in_schema=False)
async def single_page_app(path: str):
    index = web_dir / "index.html"
    if not index.exists():
        return JSONResponse({"name": settings.app_name, "docs": "/api/docs"})
    return FileResponse(index)
