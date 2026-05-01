import asyncio
import logging
import uuid
from contextlib import asynccontextmanager, suppress
from collections import deque
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.engine import make_url
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.core.rate_limit import limiter
from app.core.request_context import RequestIdFilter, request_id_ctx
from app.db.session import async_session
from app.crud import settings as crud_settings
from app.schemas import settings as schema_settings
from app.services import backup_scheduler
from app.services import pdf_template_service

# in-memory log buffer for errors (used by admin UI)
# storing here so endpoints can import easily
log_history: deque[str] = deque(maxlen=2000)

class MemoryHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        log_history.append(msg)

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s [req=%(request_id)s] %(message)s"


def _attach_handler(root_logger: logging.Logger, handler: logging.Handler, marker: str) -> None:
    if any(getattr(h, "_pmm_marker", None) == marker for h in root_logger.handlers):
        return
    handler.addFilter(RequestIdFilter())
    setattr(handler, "_pmm_marker", marker)
    root_logger.addHandler(handler)


root = logging.getLogger()
root.setLevel(logging.INFO)

mem_handler = MemoryHandler()
mem_handler.setLevel(logging.ERROR)
mem_handler.setFormatter(logging.Formatter(LOG_FORMAT))
_attach_handler(root, mem_handler, "memory_handler")

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
_attach_handler(root, stream_handler, "stdout_handler")

log_file_path = Path(settings.posting_error_log_path).parent / "app.log"
try:
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file_path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    _attach_handler(root, file_handler, "file_handler")
except OSError as exc:
    root.warning("File logging disabled for %s: %s", log_file_path, exc)

logger = logging.getLogger(__name__)

# dedicated posting/adjustment error logger
posting_logger = logging.getLogger("app.posting")
posting_logger.setLevel(logging.INFO)
if not any(isinstance(h, logging.FileHandler) for h in posting_logger.handlers):
    posting_log_path = Path(settings.posting_error_log_path)
    try:
        posting_log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(posting_log_path, encoding="utf-8")
        fh.setLevel(logging.ERROR)
        fh.setFormatter(logging.Formatter(LOG_FORMAT))
        fh.addFilter(RequestIdFilter())
        posting_logger.addHandler(fh)
    except OSError as exc:
        root.warning("Posting file logging disabled for %s: %s", posting_log_path, exc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # schema is managed by Alembic migrations; startup only seeds default data
    try:
        db_url = make_url(settings.database_url)
        logger.info(
            "Database target: dialect=%s host=%s port=%s db=%s",
            db_url.drivername,
            db_url.host or "localhost",
            db_url.port or "-",
            db_url.database or "-",
        )
    except Exception:
        logger.warning("Unable to parse DATABASE_URL for startup diagnostics")
    async with async_session() as session:
        dens = await crud_settings.get_settings(session)
        if not dens:
            await crud_settings.create_or_update_settings(
                session,
                schema_settings.DensitySettingsBase(density_factor_ab=0.74, density_factor_dp=0.84),
            )
        await pdf_template_service.ensure_default_template(session)
        await session.commit()
    backup_scheduler_task = asyncio.create_task(backup_scheduler.auto_backup_loop())
    try:
        yield
    finally:
        backup_scheduler_task.cancel()
        with suppress(asyncio.CancelledError):
            await backup_scheduler_task


app = FastAPI(title="Облік ПММ API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _normalize_host(value: str) -> str:
    token = (value or "").strip().lower()
    if not token:
        return ""
    if token == "*":
        return token
    if "://" in token:
        parsed = urlparse(token)
        token = (parsed.netloc or parsed.path or "").strip().lower()
    token = token.split("/", 1)[0].strip()
    return token


def _trusted_hosts_with_internal_defaults(values: list[str]) -> list[str]:
    cleaned: list[str] = []
    for raw in values or []:
        host = _normalize_host(str(raw))
        if host and host not in cleaned:
            cleaned.append(host)
    if "*" in cleaned:
        return ["*"]
    for public_url in (
        settings.frontend_base_url,
        settings.print_qr_target_url,
    ):
        raw_public = str(public_url or "").strip()
        host = _normalize_host(raw_public)
        if host and host not in cleaned:
            cleaned.append(host)
        if ":" in host:
            hostname = host.split(":", 1)[0].strip()
            if hostname and hostname not in cleaned:
                cleaned.append(hostname)
        elif "://" in raw_public:
            parsed = urlparse(raw_public)
            scheme = (parsed.scheme or "").strip().lower()
            if scheme == "https":
                https_host = f"{host}:443"
                if host and https_host not in cleaned:
                    cleaned.append(https_host)
            elif scheme == "http":
                http_host = f"{host}:80"
                if host and http_host not in cleaned:
                    cleaned.append(http_host)
    for internal in (
        "127.0.0.1",
        "127.0.0.1:8000",
        "localhost",
        "localhost:8000",
        "backend",
        "backend:8000",
        "pmm-api-internal",
        "pmm-api-internal:8000",
        "frontend",
        "frontend:80",
    ):
        if internal not in cleaned:
            cleaned.append(internal)
    return cleaned


trusted_hosts = _trusted_hosts_with_internal_defaults(settings.allowed_hosts)
logger.info("Trusted host validation disabled; configured hosts=%s", ",".join(trusted_hosts))


@app.middleware("http")
async def add_request_context_and_security_headers(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    token = request_id_ctx.set(request_id)
    try:
        response = await call_next(request)
    finally:
        request_id_ctx.reset(token)

    response.headers["X-Request-ID"] = request_id
    if settings.enable_security_headers:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.url.scheme == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


def _request_id_of(request: Request) -> str:
    return str(getattr(request.state, "request_id", "-"))


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = _request_id_of(request)
    token = request_id_ctx.set(request_id)
    detail = exc.detail if exc.status_code < 500 else "Internal server error"
    headers = dict(exc.headers or {})
    headers["X-Request-ID"] = request_id
    try:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": detail, "request_id": request_id},
            headers=headers,
        )
    finally:
        request_id_ctx.reset(token)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = _request_id_of(request)
    token = request_id_ctx.set(request_id)
    try:
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "request_id": request_id},
            headers={"X-Request-ID": request_id},
        )
    finally:
        request_id_ctx.reset(token)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = _request_id_of(request)
    token = request_id_ctx.set(request_id)
    try:
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
            headers={"X-Request-ID": request_id},
        )
    finally:
        request_id_ctx.reset(token)

from app.api.v1.endpoints import auth, departments, users, stock, requests, vehicles, vehicle_change_requests, routes, jobs, incidents, updates, pdf_templates
# avoid name collision with config settings
from app.api.v1.endpoints import settings as settings_router

app.include_router(auth.router, prefix="/api/v1")
app.include_router(departments.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(settings_router.router, prefix="/api/v1")
app.include_router(stock.router, prefix="/api/v1")
app.include_router(requests.router, prefix="/api/v1")
app.include_router(vehicles.router, prefix="/api/v1")
app.include_router(vehicle_change_requests.router, prefix="/api/v1")
app.include_router(routes.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1")
app.include_router(updates.router, prefix="/api/v1")
app.include_router(pdf_templates.router, prefix="/api/v1")
# include logs router last so that it is easy to find (also `/settings/logs` path)
from app.api.v1.endpoints import logs as logs_router
app.include_router(logs_router.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/ready")
async def ready():
    return await readyz()


@app.get("/readyz")
async def readyz():
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"ok": False, "db": "down"})
    return {"ok": True, "db": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
