from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.config import settings
from app.db.session import get_db
from app.models.pdf_template import PdfTemplateVersion, PrintArtifact
from app.models.request import Request
from app.schemas import pdf_template as schema_pdf
from app.services import pdf_template_service

router = APIRouter()


def _version_out(v: PdfTemplateVersion) -> dict:
    return {
        "id": v.id,
        "template_id": v.template_id,
        "version": v.version,
        "name": v.name,
        "status": v.status.value if v.status else None,
        "layout_json": v.layout_json,
        "table_columns_json": v.table_columns_json,
        "mapping_json": v.mapping_json,
        "rules_json": v.rules_json,
        "service_block_json": v.service_block_json,
        "created_at": v.created_at,
        "created_by": v.created_by,
        "published_at": v.published_at,
        "published_by": v.published_by,
    }


async def _assert_request_access(db: AsyncSession, request_id: int, current_user) -> Request:
    req = (await db.execute(select(Request).where(Request.id == request_id))).scalars().first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if current_user.role.value == "DEPT_USER" and req.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Request belongs to another department")
    return req


@router.get("/admin/pdf-templates")
async def list_pdf_templates(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    await pdf_template_service.ensure_default_template(db)
    rows = await pdf_template_service.list_templates(db)
    await db.commit()
    return rows


@router.post("/admin/pdf-templates")
async def create_pdf_template(
    data: schema_pdf.PdfTemplateCreateIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    row = await pdf_template_service.create_template(
        db,
        name=data.name,
        scope=data.scope,
        is_active=data.is_active,
        created_by=current_user.id,
    )
    await db.commit()
    detail = await pdf_template_service.get_template_detail(db, row.id)
    return detail


@router.get("/admin/pdf-templates/{template_id}")
async def get_pdf_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    return await pdf_template_service.get_template_detail(db, template_id)


@router.delete("/admin/pdf-templates/{template_id}")
async def delete_pdf_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    result = await pdf_template_service.delete_template(db, template_id=template_id)
    await db.commit()
    return result


@router.post("/admin/pdf-templates/{template_id}/versions")
async def create_pdf_template_version(
    template_id: str,
    data: schema_pdf.PdfTemplateVersionCreateIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    row = await pdf_template_service.create_template_version(
        db,
        template_id=template_id,
        from_version_id=data.from_version_id,
        name=data.name,
        created_by=current_user.id,
    )
    await db.commit()
    return _version_out(row)


@router.patch("/admin/pdf-template-versions/{version_id}")
async def patch_pdf_template_version(
    version_id: str,
    data: schema_pdf.PdfTemplateVersionPatchIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    row = await pdf_template_service.patch_template_version(
        db,
        version_id=version_id,
        name=data.name,
        layout_json=data.layout_json,
        table_columns_json=data.table_columns_json,
        mapping_json=data.mapping_json,
        rules_json=data.rules_json,
        service_block_json=data.service_block_json,
    )
    await db.commit()
    return _version_out(row)


@router.post("/admin/pdf-template-versions/{version_id}/publish")
async def publish_pdf_template_version(
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    row = await pdf_template_service.publish_template_version(
        db,
        version_id=version_id,
        published_by=current_user.id,
    )
    await db.commit()
    return _version_out(row)


@router.delete("/admin/pdf-template-versions/{version_id}")
async def delete_pdf_template_version(
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    result = await pdf_template_service.delete_template_version(db, version_id=version_id)
    await db.commit()
    return result


@router.post("/admin/pdf-template-versions/{version_id}/preview")
async def preview_pdf_template_version(
    version_id: str,
    data: schema_pdf.PdfTemplatePreviewIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    await _assert_request_access(db, data.request_id, current_user)
    pdf_bytes = await pdf_template_service.build_preview_pdf(
        db,
        version_id=version_id,
        request_id=data.request_id,
        base_url=settings.frontend_base_url,
        layout_json=data.layout_json,
        table_columns_json=data.table_columns_json,
        mapping_json=data.mapping_json,
        rules_json=data.rules_json,
        service_block_json=data.service_block_json,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=request_{data.request_id}_preview.pdf"},
    )


@router.post("/requests/{request_id}/print/pdf", response_model=schema_pdf.RequestPrintPdfOut)
async def print_request_pdf(
    request_id: int,
    data: schema_pdf.RequestPrintPdfIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER", "OPERATOR"])),
):
    await _assert_request_access(db, request_id, current_user)
    result = await pdf_template_service.generate_request_pdf_artifact(
        db,
        request_id=request_id,
        actor_user_id=current_user.id,
        template_id=data.template_id,
        force_regenerate=bool(data.force_regenerate),
        base_url=settings.frontend_base_url,
    )
    await db.commit()
    artifact: PrintArtifact = result["artifact"]
    return {
        "artifact_id": artifact.id,
        "request_id": request_id,
        "template_version_id": artifact.template_version_id,
        "download_url": f"/api/v1/print-artifacts/{artifact.id}/download",
        "from_cache": bool(result.get("from_cache")),
    }


@router.get("/print-artifacts/{artifact_id}/download")
async def download_print_artifact(
    artifact_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER", "OPERATOR"])),
):
    artifact = (
        await db.execute(
            select(PrintArtifact).where(PrintArtifact.id == artifact_id)
        )
    ).scalars().first()
    if not artifact:
        raise HTTPException(status_code=404, detail="Print artifact not found")

    await _assert_request_access(db, artifact.request_id, current_user)

    path = Path(artifact.file_path).expanduser().resolve()
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact file not found")
    return FileResponse(path=str(path), filename=path.name, media_type="application/pdf")
