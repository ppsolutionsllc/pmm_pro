from typing import Optional
from typing import List
import base64
import io
import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from PIL import Image, ImageDraw

from app.db.session import get_db
from app.schemas import settings as schema_settings
from app.schemas import planned_activity as schema_planned
from app.crud import settings as crud_settings
from app.crud import app_settings as crud_app
from app.crud import planned_activity as crud_planned
from app.api import deps

router = APIRouter()

_PWA_ICON_SIZES = (192, 512)


def _normalize_color(value: str | None, fallback: str) -> str:
    v = (value or "").strip()
    if len(v) == 7 and v.startswith("#"):
        return v
    return fallback


def _render_png_variants(raw_bytes: bytes) -> dict[int, str]:
    try:
        src = Image.open(io.BytesIO(raw_bytes)).convert("RGBA")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Unsupported image file") from exc
    out: dict[int, str] = {}
    for size in _PWA_ICON_SIZES:
        resized = src.resize((size, size), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        resized.save(buf, format="PNG")
        out[size] = base64.b64encode(buf.getvalue()).decode("ascii")
    return out


def _default_icon_bytes(size: int) -> bytes:
    canvas = Image.new("RGBA", (size, size), "#0f172a")
    draw = ImageDraw.Draw(canvas)

    pad = int(size * 0.14)
    radius = int(size * 0.12)
    stroke = max(2, size // 42)
    draw.rounded_rectangle(
        (pad, pad, size - pad, size - pad),
        radius=radius,
        fill="#162338",
        outline="#3dde95",
        width=stroke,
    )

    # Minimal fuel-pump glyph without external font dependency.
    body_left = int(size * 0.38)
    body_top = int(size * 0.30)
    body_right = int(size * 0.57)
    body_bottom = int(size * 0.69)
    inner_radius = max(2, int(size * 0.03))
    draw.rounded_rectangle(
        (body_left, body_top, body_right, body_bottom),
        radius=inner_radius,
        outline="#52f2a0",
        width=stroke,
    )
    draw.line(
        (
            body_right,
            int(size * 0.37),
            int(size * 0.66),
            int(size * 0.37),
            int(size * 0.69),
            int(size * 0.43),
            int(size * 0.65),
            int(size * 0.52),
        ),
        fill="#52f2a0",
        width=stroke,
        joint="curve",
    )
    draw.line(
        (
            body_left + stroke,
            int(size * 0.45),
            body_right - stroke,
            int(size * 0.45),
        ),
        fill="#52f2a0",
        width=max(1, stroke - 1),
    )

    buff = io.BytesIO()
    canvas.save(buff, format="PNG")
    return buff.getvalue()


async def _get_pwa_icons_info(db: AsyncSession) -> dict:
    b192 = await crud_app.get_setting(db, "pwa.icon_192_b64")
    b512 = await crud_app.get_setting(db, "pwa.icon_512_b64")
    has_icons = bool(b192 and b512)
    return {
        "has_icons": has_icons,
        "icon_192_url": "/api/v1/settings/pwa/icon/192.png",
        "icon_512_url": "/api/v1/settings/pwa/icon/512.png",
    }

@router.get("/settings/density", response_model=schema_settings.DensitySettingsOut)
async def get_density_settings(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    s = await crud_settings.get_settings(db)
    if not s:
        raise HTTPException(status_code=404, detail="Settings not set")
    return s

@router.post("/settings/density", response_model=schema_settings.DensitySettingsOut)
async def set_density_settings(
    data: schema_settings.DensitySettingsUpdateIn,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    return await crud_settings.create_or_update_settings(
        db,
        data,
        changed_by=current_user.id,
        comment=data.comment,
    )


@router.get("/settings/density/history")
async def get_density_history(
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    rows = await crud_settings.list_coeff_history(db, limit=limit)
    out = []
    for r in rows:
        out.append(
            {
                "id": r.id,
                "fuel_type": r.fuel_type.value if getattr(r, "fuel_type", None) else None,
                "density_kg_per_l": r.density_kg_per_l,
                "changed_by": r.changed_by,
                "changed_at": str(r.changed_at) if r.changed_at else None,
                "comment": r.comment,
            }
        )
    return out


# --- Request planned activities ---
@router.get("/settings/planned-activities", response_model=List[schema_planned.PlannedActivityOut])
async def list_planned_activities(
    only_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "OPERATOR", "DEPT_USER"])),
):
    return await crud_planned.list_activities(db, only_active=only_active)


@router.post("/settings/planned-activities", response_model=schema_planned.PlannedActivityOut)
async def create_planned_activity(
    data: schema_planned.PlannedActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    return await crud_planned.create_activity(db, name=data.name, is_active=data.is_active)


@router.patch("/settings/planned-activities/{activity_id}", response_model=schema_planned.PlannedActivityOut)
async def update_planned_activity(
    activity_id: int,
    data: schema_planned.PlannedActivityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    obj = await crud_planned.update_activity(db, activity_id, name=data.name, is_active=data.is_active)
    if not obj:
        raise HTTPException(status_code=404, detail="Not found")
    return obj


@router.delete("/settings/planned-activities/{activity_id}")
async def delete_planned_activity(
    activity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    await crud_planned.delete_activity(db, activity_id)
    return {"ok": True}


# --- Support settings ---
class SupportSettings(BaseModel):
    enabled: Optional[bool] = False
    label: Optional[str] = ""
    url: Optional[str] = ""


def _support_settings_from_dict(raw: dict) -> SupportSettings:
    return SupportSettings(
        enabled=raw.get("enabled", "false").lower() == "true" if raw.get("enabled") else False,
        label=raw.get("label", ""),
        url=raw.get("url", ""),
    )


@router.get("/settings/support/public", response_model=SupportSettings)
async def get_support_settings_public(
    db: AsyncSession = Depends(get_db),
):
    d = await crud_app.get_settings_dict(db, "support")
    return _support_settings_from_dict(d)


@router.get("/settings/support", response_model=SupportSettings)
async def get_support_settings(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_any_role(["ADMIN", "OPERATOR", "DEPT_USER"])),
):
    d = await crud_app.get_settings_dict(db, "support")
    return _support_settings_from_dict(d)

@router.post("/settings/support", response_model=SupportSettings)
async def set_support_settings(
    data: SupportSettings,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    await crud_app.set_settings_dict(db, "support", {
        "enabled": str(data.enabled).lower(),
        "label": data.label or "",
        "url": data.url or "",
    })
    return data


# --- PWA settings ---
class PWASettings(BaseModel):
    app_name: Optional[str] = "Облік ПММ"
    short_name: Optional[str] = "ПММ"
    theme_color: Optional[str] = "#1a1a2e"
    background_color: Optional[str] = "#0f0f23"

@router.get("/settings/pwa", response_model=PWASettings)
async def get_pwa_settings(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    d = await crud_app.get_settings_dict(db, "pwa")
    return PWASettings(
        app_name=d.get("app_name", "Облік ПММ"),
        short_name=d.get("short_name", "ПММ"),
        theme_color=d.get("theme_color", "#1a1a2e"),
        background_color=d.get("background_color", "#0f0f23"),
    )

@router.post("/settings/pwa", response_model=PWASettings)
async def set_pwa_settings(
    data: PWASettings,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    await crud_app.set_settings_dict(db, "pwa", {
        "app_name": data.app_name or "",
        "short_name": data.short_name or "",
        "theme_color": data.theme_color or "",
        "background_color": data.background_color or "",
    })
    return data


@router.get("/settings/pwa/icons")
async def get_pwa_icons(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    return await _get_pwa_icons_info(db)


@router.post("/settings/pwa/icon")
async def upload_pwa_icon(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    variants = _render_png_variants(content)
    await crud_app.set_setting(db, "pwa.icon_192_b64", variants[192])
    await crud_app.set_setting(db, "pwa.icon_512_b64", variants[512])
    return await _get_pwa_icons_info(db)


@router.delete("/settings/pwa/icon")
async def delete_pwa_icon(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    await crud_app.set_setting(db, "pwa.icon_192_b64", "")
    await crud_app.set_setting(db, "pwa.icon_512_b64", "")
    return await _get_pwa_icons_info(db)


@router.get("/settings/pwa/icon/{size}.png")
async def get_pwa_icon_binary(
    size: int,
    db: AsyncSession = Depends(get_db),
):
    if size not in _PWA_ICON_SIZES:
        raise HTTPException(status_code=404, detail="Icon size not supported")
    key = f"pwa.icon_{size}_b64"
    payload = await crud_app.get_setting(db, key)
    if not payload:
        return Response(content=_default_icon_bytes(size), media_type="image/png")
    try:
        content = base64.b64decode(payload)
    except Exception:
        return Response(content=_default_icon_bytes(size), media_type="image/png")
    return Response(content=content, media_type="image/png")


@router.get("/settings/pwa/manifest.webmanifest")
async def get_dynamic_manifest(
    db: AsyncSession = Depends(get_db),
):
    d = await crud_app.get_settings_dict(db, "pwa")
    icons = await _get_pwa_icons_info(db)
    manifest = {
        "name": d.get("app_name", "Облік ПММ"),
        "short_name": d.get("short_name", "ПММ"),
        "description": "Система обліку паливно-мастильних матеріалів",
        "start_url": "/",
        "display": "standalone",
        "background_color": _normalize_color(d.get("background_color"), "#0f172a"),
        "theme_color": _normalize_color(d.get("theme_color"), "#1a2332"),
        "icons": [
            {
                "src": icons["icon_192_url"],
                "sizes": "192x192",
                "type": "image/png",
            },
            {
                "src": icons["icon_512_url"],
                "sizes": "512x512",
                "type": "image/png",
            },
        ],
    }
    return Response(
        content=json.dumps(manifest, ensure_ascii=False),
        media_type="application/manifest+json",
    )


class FeatureSettings(BaseModel):
    enable_reservations: bool = False


@router.get("/settings/features", response_model=FeatureSettings)
async def get_feature_settings(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    raw = await crud_app.get_setting(db, "features.enable_reservations")
    return FeatureSettings(enable_reservations=str(raw).strip().lower() == "true")


@router.post("/settings/features", response_model=FeatureSettings)
async def set_feature_settings(
    data: FeatureSettings,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(deps.require_role("ADMIN")),
):
    await crud_app.set_setting(db, "features.enable_reservations", str(bool(data.enable_reservations)).lower())
    return data
