from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, Boolean

from app.core.time import utcnow
from app.models.base import Base


class SystemMeta(Base):
    __tablename__ = "system_meta"

    id = Column(Integer, primary_key=True, index=True)
    backend_version = Column(String(64), nullable=False, default="dev")
    frontend_version = Column(String(64), nullable=False, default="dev")
    db_schema_version = Column(String(128), nullable=True)
    last_update_at = Column(DateTime, nullable=False, default=utcnow)
    last_update_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    update_lock = Column(Boolean, nullable=False, default=False)
    update_lock_job_id = Column(String(36), nullable=True)
    update_lock_acquired_at = Column(DateTime, nullable=True)
    updater_mode = Column(String(32), nullable=False, default="server_build")
    update_repo = Column(String(256), nullable=True)
