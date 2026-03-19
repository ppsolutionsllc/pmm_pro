from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.background_job import BackgroundJob, BackgroundJobType
from app.schemas import job as schema_job
from app.schemas import stock as schema_stock
from app.services import job_service, reporting_service

router = APIRouter()


def _job_out(job: BackgroundJob) -> dict:
    return {
        "id": job.id,
        "type": job.type.value if job.type else None,
        "status": job.status.value if job.status else None,
        "params_json": job.params_json,
        "result_json": job.result_json,
        "created_at": job.created_at,
        "created_by": job.created_by,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "error_message": job.error_message,
    }


def _apply_dept_scope(current_user, filters: dict | None) -> dict:
    f = dict(filters or {})
    if current_user.role.value == "DEPT_USER":
        f["department_id"] = current_user.department_id
    return f


@router.get("/reports/vehicle-consumption")
async def get_vehicle_consumption_report(
    date_from: str | None = None,
    date_to: str | None = None,
    department_id: int | None = None,
    vehicle_id: int | None = None,
    fuel_type: str | None = None,
    route_contains: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER"])),
):
    if current_user.role.value == "DEPT_USER":
        department_id = current_user.department_id
    try:
        parsed_from = datetime.fromisoformat(date_from) if date_from else None
        parsed_to = datetime.fromisoformat(date_to) if date_to else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO datetime")
    rows = await reporting_service.build_vehicle_consumption_rows(
        db,
        date_from=parsed_from,
        date_to=parsed_to,
        department_id=department_id,
        vehicle_id=vehicle_id,
        fuel_type=fuel_type,
        route_contains=route_contains,
    )
    return {"rows": rows, "count": len(rows)}


@router.get("/reports/departments")
async def get_departments_report(
    date_from: str | None = None,
    date_to: str | None = None,
    department_id: int | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER"])),
):
    if current_user.role.value == "DEPT_USER":
        department_id = current_user.department_id
    try:
        parsed_from = datetime.fromisoformat(date_from) if date_from else None
        parsed_to = datetime.fromisoformat(date_to) if date_to else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO datetime")
    rows = await reporting_service.build_department_consumption_rows(
        db,
        date_from=parsed_from,
        date_to=parsed_to,
        department_id=department_id,
        status=status,
    )
    return {"rows": rows, "count": len(rows)}


@router.post("/jobs/reconcile", response_model=schema_job.JobCreateOut)
async def create_reconcile_job(
    data: schema_job.ReconcileJobIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    job = await job_service.enqueue_job(
        db,
        job_type=BackgroundJobType.RECONCILE,
        params_json={"filters": data.filters or {}},
        created_by=current_user.id,
    )
    await db.commit()
    job_service.schedule_background_job(job.id)
    return {"job_id": job.id, "status": job.status.value}


@router.post("/jobs/exports/requests", response_model=schema_job.JobCreateOut)
async def create_requests_export_job(
    data: schema_job.ExportJobIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER"])),
):
    filters = _apply_dept_scope(current_user, data.filters)
    job = await job_service.enqueue_job(
        db,
        job_type=BackgroundJobType.REQUESTS_EXPORT,
        params_json={"format": data.format, "filters": filters},
        created_by=current_user.id,
    )
    await db.commit()
    job_service.schedule_background_job(job.id)
    return {"job_id": job.id, "status": job.status.value}


@router.post("/jobs/exports/debts", response_model=schema_job.JobCreateOut)
async def create_debts_export_job(
    data: schema_job.ExportJobIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER"])),
):
    filters = _apply_dept_scope(current_user, data.filters)
    job = await job_service.enqueue_job(
        db,
        job_type=BackgroundJobType.DEBTS_EXPORT,
        params_json={"format": data.format, "filters": filters},
        created_by=current_user.id,
    )
    await db.commit()
    job_service.schedule_background_job(job.id)
    return {"job_id": job.id, "status": job.status.value}


@router.post("/jobs/exports/vehicle-report", response_model=schema_job.JobCreateOut)
async def create_vehicle_report_export_job(
    data: schema_job.ExportJobIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER"])),
):
    filters = _apply_dept_scope(current_user, data.filters)
    job = await job_service.enqueue_job(
        db,
        job_type=BackgroundJobType.VEHICLE_REPORT_EXPORT,
        params_json={"format": data.format, "filters": filters},
        created_by=current_user.id,
    )
    await db.commit()
    job_service.schedule_background_job(job.id)
    return {"job_id": job.id, "status": job.status.value}


@router.get("/jobs/{job_id}", response_model=schema_job.JobOut)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER"])),
):
    job = (await db.execute(select(BackgroundJob).where(BackgroundJob.id == job_id))).scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if current_user.role.value == "DEPT_USER":
        if job.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Operation not permitted")
    return _job_out(job)


@router.get("/jobs/{job_id}/download")
async def download_job_result(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "DEPT_USER"])),
):
    job = (await db.execute(select(BackgroundJob).where(BackgroundJob.id == job_id))).scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if current_user.role.value == "DEPT_USER" and job.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Operation not permitted")
    if not job.result_json or not job.result_json.get("file_path"):
        raise HTTPException(status_code=404, detail="Job has no downloadable artifact")
    path = Path(job.result_json["file_path"]).expanduser().resolve()
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(path=str(path), filename=path.name)


@router.get("/stock/reconcile", response_model=list[schema_stock.StockReconcileRowOut])
async def get_stock_reconcile_now(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    return await reporting_service.build_stock_reconcile_rows(db)
