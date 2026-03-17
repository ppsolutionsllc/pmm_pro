import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.core.time import utcnow
from app.models.base import Base


class PdfTemplateScope(str, enum.Enum):
    REQUEST_FUEL = "REQUEST_FUEL"


class PdfTemplateVersionStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class PrintArtifactType(str, enum.Enum):
    PDF_REQUEST_FORM = "PDF_REQUEST_FORM"


class PdfTemplate(Base):
    __tablename__ = "pdf_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    scope = Column(
        Enum(PdfTemplateScope, name="pdf_template_scope_enum", create_type=False),
        nullable=False,
        default=PdfTemplateScope.REQUEST_FUEL,
    )
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    versions = relationship("PdfTemplateVersion", back_populates="template", cascade="all, delete-orphan")


class PdfTemplateVersion(Base):
    __tablename__ = "pdf_template_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    template_id = Column(String(36), ForeignKey("pdf_templates.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    name = Column(String(200), nullable=False, default="")
    status = Column(
        Enum(PdfTemplateVersionStatus, name="pdf_template_version_status_enum", create_type=False),
        nullable=False,
        default=PdfTemplateVersionStatus.DRAFT,
    )
    layout_json = Column(JSON, nullable=False)
    table_columns_json = Column(JSON, nullable=False)
    mapping_json = Column(JSON, nullable=False)
    rules_json = Column(JSON, nullable=False)
    service_block_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    published_at = Column(DateTime, nullable=True)
    published_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    template = relationship("PdfTemplate", back_populates="versions")


class RequestPrintSnapshot(Base):
    __tablename__ = "request_print_snapshots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False, index=True)
    template_id = Column(String(36), ForeignKey("pdf_templates.id"), nullable=False, index=True)
    template_version_id = Column(String(36), ForeignKey("pdf_template_versions.id"), nullable=False, index=True)
    snapshot_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    request = relationship("Request", back_populates="print_snapshots")
    template = relationship("PdfTemplate")
    template_version = relationship("PdfTemplateVersion")


class PrintArtifact(Base):
    __tablename__ = "print_artifacts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False, index=True)
    artifact_type = Column(
        Enum(PrintArtifactType, name="print_artifact_type_enum", create_type=False),
        nullable=False,
        default=PrintArtifactType.PDF_REQUEST_FORM,
    )
    template_version_id = Column(String(36), ForeignKey("pdf_template_versions.id"), nullable=False, index=True)
    file_path = Column(Text, nullable=False)
    sha256 = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    request = relationship("Request", back_populates="print_artifacts")
    template_version = relationship("PdfTemplateVersion")
