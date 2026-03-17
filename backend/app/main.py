import uvicorn
import asyncio
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from logging.handlers import RotatingFileHandler
from collections import deque
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.engine import make_url
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
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

# configure root logger to use memory handler
mem_handler = MemoryHandler()
mem_handler.setLevel(logging.ERROR)
mem_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logging.getLogger().addHandler(mem_handler)
log_file_path = Path(settings.posting_error_log_path).parent / "app.log"
log_file_path.parent.mkdir(parents=True, exist_ok=True)
file_handler = RotatingFileHandler(
    log_file_path, maxBytes=10*1024*1024, backupCount=5, encoding="utf-8"
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
logging.getLogger().addHandler(file_handler)
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

# dedicated posting/adjustment error logger
posting_logger = logging.getLogger("app.posting")
posting_logger.setLevel(logging.INFO)
if not any(isinstance(h, logging.FileHandler) for h in posting_logger.handlers):
    posting_log_path = Path(settings.posting_error_log_path)
    posting_log_path.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(posting_log_path, encoding="utf-8")
    fh.setLevel(logging.ERROR)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    posting_logger.addHandler(fh)


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


@app.get("/healthz")
async def healthz():
    return {"ok": True}


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
