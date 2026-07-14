"""Reference Models API ([FORK] — noraPlan.md WP100.3).

Per-domain reference-model CRUD with a governed draft → published → archived
lifecycle (publish supersedes the previously published RM of the same domain),
hierarchical items, xlsx import/export in the canonical exchange layout, and
the ``/active`` endpoints that back the card-detail code-field pickers.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.reference_model import (
    RM_DOMAINS,
    RM_SOURCES,
    ReferenceModel,
    ReferenceModelItem,
)
from app.models.user import User
from app.services.event_bus import event_bus
from app.services.permission_service import PermissionService
from app.services.reference_models import (
    build_rm_workbook,
    item_counts,
    item_dict,
    items_for,
    model_dict,
    parse_rm_workbook,
    resolve_active_model,
    sort_items,
    upsert_items,
)

router = APIRouter(prefix="/reference-models", tags=["reference-models"])

_XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class ModelCreate(BaseModel):
    domain: str = Field(pattern="^(" + "|".join(RM_DOMAINS) + ")$")
    name: str = Field(min_length=1, max_length=255)
    name_ar: str | None = Field(default=None, max_length=255)
    description: str | None = None
    version: str = Field(default="1.0", max_length=32)
    source: str = Field(default="agency", pattern="^(" + "|".join(RM_SOURCES) + ")$")


class ModelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    name_ar: str | None = Field(default=None, max_length=255)
    description: str | None = None
    version: str | None = Field(default=None, max_length=32)
    source: str | None = Field(default=None, pattern="^(" + "|".join(RM_SOURCES) + ")$")


class ItemCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    name_ar: str | None = Field(default=None, max_length=255)
    description: str | None = None
    parent_id: uuid.UUID | None = None
    sort_order: int = 0


class ItemUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    name_ar: str | None = Field(default=None, max_length=255)
    description: str | None = None
    parent_id: uuid.UUID | None = None
    clear_parent: bool = False
    sort_order: int | None = None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
async def _get_model(db: AsyncSession, mid: uuid.UUID) -> ReferenceModel:
    row = (
        await db.execute(select(ReferenceModel).where(ReferenceModel.id == mid))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Reference model not found")
    return row


async def _get_item(db: AsyncSession, iid: uuid.UUID) -> ReferenceModelItem:
    row = (
        await db.execute(select(ReferenceModelItem).where(ReferenceModelItem.id == iid))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Reference model item not found")
    return row


async def _check_code_free(
    db: AsyncSession, model_id: uuid.UUID, code: str, exclude_id: uuid.UUID | None = None
) -> None:
    q = select(ReferenceModelItem.id).where(
        ReferenceModelItem.model_id == model_id, ReferenceModelItem.code == code
    )
    if exclude_id:
        q = q.where(ReferenceModelItem.id != exclude_id)
    if (await db.execute(q)).first() is not None:
        raise HTTPException(409, f"Code '{code}' already exists in this reference model")


async def _validate_parent(
    db: AsyncSession, model_id: uuid.UUID, parent_id: uuid.UUID, item_id: uuid.UUID | None = None
) -> None:
    parent = await _get_item(db, parent_id)
    if parent.model_id != model_id:
        raise HTTPException(400, "Parent item belongs to a different reference model")
    if item_id is not None:
        # Walk up the ancestor chain to reject cycles.
        cursor: ReferenceModelItem | None = parent
        while cursor is not None:
            if cursor.id == item_id:
                raise HTTPException(400, "Cannot set an item's parent to itself or a descendant")
            cursor = await _get_item(db, cursor.parent_id) if cursor.parent_id else None


def _safe_filename(name: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9؀-ۿ_-]+", "_", name).strip("_") or "reference_model"
    return f"{stem}.xlsx"


async def _user_names(db: AsyncSession, ids: set) -> dict:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    res = await db.execute(select(User.id, User.display_name).where(User.id.in_(ids)))
    return dict(res.all())


# --------------------------------------------------------------------------- #
# Active (published) models — declared before /{model_id}
# --------------------------------------------------------------------------- #
@router.get("/active-summary")
async def active_summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Cheap existence probe: which domains currently have a published RM."""
    await PermissionService.require_permission(db, user, "reference_models.view")
    rows = (
        (
            await db.execute(
                select(ReferenceModel.domain).where(ReferenceModel.status == "published")
            )
        )
        .scalars()
        .all()
    )
    published = set(rows)
    return {d: (d in published) for d in RM_DOMAINS}


@router.get("/active")
async def get_active(
    domain: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The published RM for a domain, with its flat item list (powers pickers)."""
    await PermissionService.require_permission(db, user, "reference_models.view")
    if domain not in RM_DOMAINS:
        raise HTTPException(422, f"Unknown domain '{domain}'")
    model = await resolve_active_model(db, domain)
    if model is None:
        return {"model": None, "items": []}
    items = await items_for(db, model.id)
    return {
        "model": model_dict(model, item_count=len(items)),
        "items": [item_dict(i) for i in sort_items(items)],
    }


# --------------------------------------------------------------------------- #
# Import (create-new form) — declared before /{model_id}
# --------------------------------------------------------------------------- #
@router.post("/import")
async def import_new_model(
    file: UploadFile = File(...),
    domain: str = Form(...),
    name: str = Form(...),
    name_ar: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new reference model from an xlsx file in the exchange layout."""
    await PermissionService.require_permission(db, user, "reference_models.manage")
    if domain not in RM_DOMAINS:
        raise HTTPException(422, f"Unknown domain '{domain}'")
    if not name.strip():
        raise HTTPException(422, "Name is required")
    rows, errors = parse_rm_workbook(await file.read())
    if not rows:
        raise HTTPException(400, "; ".join(errors) or "No importable rows found")
    model = ReferenceModel(
        domain=domain,
        name=name.strip()[:255],
        name_ar=(name_ar or "").strip()[:255] or None,
        source="agency",
        status="draft",
        created_by=user.id,
    )
    db.add(model)
    await db.flush()
    summary = await upsert_items(db, model, rows)
    await db.commit()
    return {"model": model_dict(model, item_count=len(rows)), "summary": summary, "errors": errors}


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
@router.get("")
async def list_models(
    domain: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reference_models.view")
    q = select(ReferenceModel).order_by(ReferenceModel.created_at.desc())
    if domain:
        q = q.where(ReferenceModel.domain == domain)
    models = list((await db.execute(q)).scalars().all())
    counts = await item_counts(db, [m.id for m in models])
    names = await _user_names(db, {m.published_by for m in models})
    return {"models": [model_dict(m, item_count=counts.get(m.id, 0), names=names) for m in models]}


@router.post("")
async def create_model(
    payload: ModelCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reference_models.manage")
    model = ReferenceModel(
        domain=payload.domain,
        name=payload.name,
        name_ar=payload.name_ar,
        description=payload.description,
        version=payload.version,
        source=payload.source,
        status="draft",
        created_by=user.id,
    )
    db.add(model)
    await db.commit()
    return model_dict(model, item_count=0)


@router.get("/{model_id}")
async def get_model(
    model_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reference_models.view")
    model = await _get_model(db, model_id)
    items = await items_for(db, model_id)
    names = await _user_names(db, {model.published_by})
    return {
        "model": model_dict(model, item_count=len(items), names=names),
        "items": [item_dict(i) for i in sort_items(items)],
    }


@router.patch("/{model_id}")
async def update_model(
    model_id: uuid.UUID,
    payload: ModelUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reference_models.manage")
    model = await _get_model(db, model_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(model, field, value)
    await db.commit()
    return model_dict(model)


@router.delete("/{model_id}")
async def delete_model(
    model_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reference_models.manage")
    model = await _get_model(db, model_id)
    if model.status == "published":
        raise HTTPException(409, "A published reference model cannot be deleted — archive it first")
    await db.delete(model)
    await db.commit()
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Lifecycle
# --------------------------------------------------------------------------- #
@router.post("/{model_id}/publish")
async def publish_model(
    model_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Publish a model (supersedes the previously published RM of its domain)."""
    await PermissionService.require_permission(db, user, "reference_models.manage")
    await PermissionService.require_permission(db, user, "governance.approve_step")
    model = await _get_model(db, model_id)
    if model.status == "published":
        raise HTTPException(400, "Reference model is already published")

    superseded = await resolve_active_model(db, model.domain)
    if superseded is not None and superseded.id != model.id:
        superseded.status = "archived"

    model.status = "published"
    model.published_by = user.id
    model.published_at = datetime.now(timezone.utc)
    await event_bus.publish(
        "reference_model.published",
        {
            "id": str(model.id),
            "domain": model.domain,
            "name": model.name,
            "superseded_id": str(superseded.id) if superseded else None,
        },
        db=db,
        user_id=user.id,
    )
    await db.commit()
    return model_dict(model)


@router.post("/{model_id}/archive")
async def archive_model(
    model_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reference_models.manage")
    model = await _get_model(db, model_id)
    if model.status == "archived":
        raise HTTPException(400, "Reference model is already archived")
    model.status = "archived"
    await event_bus.publish(
        "reference_model.archived",
        {"id": str(model.id), "domain": model.domain, "name": model.name},
        db=db,
        user_id=user.id,
    )
    await db.commit()
    return model_dict(model)


# --------------------------------------------------------------------------- #
# Items
# --------------------------------------------------------------------------- #
@router.post("/{model_id}/items")
async def create_item(
    model_id: uuid.UUID,
    payload: ItemCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reference_models.manage")
    model = await _get_model(db, model_id)
    await _check_code_free(db, model.id, payload.code)
    if payload.parent_id is not None:
        await _validate_parent(db, model.id, payload.parent_id)
    item = ReferenceModelItem(
        model_id=model.id,
        parent_id=payload.parent_id,
        code=payload.code,
        name=payload.name,
        name_ar=payload.name_ar,
        description=payload.description,
        sort_order=payload.sort_order,
    )
    db.add(item)
    await db.commit()
    return item_dict(item)


@router.patch("/items/{item_id}")
async def update_item(
    item_id: uuid.UUID,
    payload: ItemUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reference_models.manage")
    item = await _get_item(db, item_id)
    data = payload.model_dump(exclude_unset=True)
    clear_parent = data.pop("clear_parent", False)

    if "code" in data and data["code"] != item.code:
        await _check_code_free(db, item.model_id, data["code"], exclude_id=item.id)
    if clear_parent:
        data["parent_id"] = None
    elif data.get("parent_id") is not None:
        await _validate_parent(db, item.model_id, data["parent_id"], item_id=item.id)

    for field, value in data.items():
        setattr(item, field, value)
    await db.commit()
    return item_dict(item)


@router.delete("/items/{item_id}")
async def delete_item(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reference_models.manage")
    item = await _get_item(db, item_id)
    await db.delete(item)
    await db.commit()
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Export / import into an existing model
# --------------------------------------------------------------------------- #
@router.get("/{model_id}/export")
async def export_model(
    model_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reference_models.view")
    model = await _get_model(db, model_id)
    items = await items_for(db, model_id)
    data = build_rm_workbook(model, items)
    return StreamingResponse(
        iter([data]),
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{_safe_filename(model.name)}"'},
    )


@router.post("/{model_id}/import")
async def import_into_model(
    model_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upsert items by code from an xlsx file in the exchange layout."""
    await PermissionService.require_permission(db, user, "reference_models.manage")
    model = await _get_model(db, model_id)
    rows, errors = parse_rm_workbook(await file.read())
    if not rows:
        raise HTTPException(400, "; ".join(errors) or "No importable rows found")
    summary = await upsert_items(db, model, rows)
    await db.commit()
    return {"summary": summary, "errors": errors}
