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
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.card import Card
from app.models.reference_model import (
    REFERENCE_MODEL_RELATIONSHIP_TYPES,
    RM_DOMAINS,
    RM_MAPPING_STATUSES,
    RM_MAPPING_TYPES,
    RM_SOURCES,
    ReferenceModel,
    ReferenceModelItem,
    ReferenceModelMapping,
    ReferenceModelRelationship,
    ReferenceModelVersion,
)
from app.models.user import User
from app.services.event_bus import event_bus
from app.services.permission_service import PermissionService
from app.services.reference_models import (
    RM_DOMAIN_CARD_TYPES,
    build_rm_workbook,
    compute_model_coverage,
    diff_snapshots,
    explicit_mappings_for_model,
    is_retiring,
    item_counts,
    item_dict,
    items_for,
    leaf_item_ids,
    mapping_dict,
    model_dict,
    parse_rm_workbook,
    resolve_active_model,
    scan_domain_card_codes,
    snapshot_items,
    sort_items,
    upsert_items,
    version_dict,
    versions_for,
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


_MAPPING_TYPE_RE = "^(" + "|".join(RM_MAPPING_TYPES) + ")$"
_MAPPING_STATUS_RE = "^(" + "|".join(RM_MAPPING_STATUSES) + ")$"


class MappingCreate(BaseModel):
    card_id: uuid.UUID
    mapping_type: str = Field(default="primary", pattern=_MAPPING_TYPE_RE)
    mapping_status: str = Field(default="confirmed", pattern=_MAPPING_STATUS_RE)
    rationale: str | None = None
    confidence: int | None = Field(default=None, ge=0, le=100)


class MappingUpdate(BaseModel):
    mapping_type: str | None = Field(default=None, pattern=_MAPPING_TYPE_RE)
    mapping_status: str | None = Field(default=None, pattern=_MAPPING_STATUS_RE)
    rationale: str | None = None
    confidence: int | None = Field(default=None, ge=0, le=100)


_RELATIONSHIP_TYPE_RE = "^(" + "|".join(REFERENCE_MODEL_RELATIONSHIP_TYPES) + ")$"


class RelationshipCreate(BaseModel):
    target_item_id: uuid.UUID
    relationship_type: str = Field(default="supports", pattern=_RELATIONSHIP_TYPE_RE)
    description: str | None = None


class NarrativePanel(BaseModel):
    """One editable poster panel (RMPlan Phase 3 / §18)."""

    id: str = Field(min_length=1, max_length=48)
    title: str = Field(default="", max_length=120)
    title_ar: str = Field(default="", max_length=120)
    kind: str = Field(default="text", pattern="^(text|list)$")
    text: str = Field(default="", max_length=4000)
    text_ar: str = Field(default="", max_length=4000)
    items: list[str] = Field(default_factory=list)
    items_ar: list[str] = Field(default_factory=list)
    placement: str = Field(default="grid", pattern="^(header|grid)$")

    @field_validator("items", "items_ar")
    @classmethod
    def _clamp_items(cls, v: list[str]) -> list[str]:
        return [str(s)[:300] for s in v[:30]]


class NarrativePayload(BaseModel):
    panels: list[NarrativePanel] = Field(default_factory=list, max_length=24)


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
# Browse (RMPlan Phase 1) — landing overview + per-model summary + item cards.
# Counts merge the card-detail code field (implicit *primary* classification)
# with the explicit reference_model_mappings rows (Phase 2), deduped by card.
# --------------------------------------------------------------------------- #
def _descendant_item_ids(items: list[ReferenceModelItem], root_id: uuid.UUID) -> set[uuid.UUID]:
    children: dict[uuid.UUID, list[ReferenceModelItem]] = {}
    for i in items:
        if i.parent_id:
            children.setdefault(i.parent_id, []).append(i)
    out = {root_id}
    stack = [root_id]
    while stack:
        for child in children.get(stack.pop(), []):
            if child.id not in out:
                out.add(child.id)
                stack.append(child.id)
    return out


@router.get("/overview")
async def browse_overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Landing-page metrics: per domain, the active RM + mapped-inventory KPIs."""
    await PermissionService.require_permission(db, user, "reference_models.view")
    out = []
    for domain in RM_DOMAINS:
        card_type, code_field = RM_DOMAIN_CARD_TYPES[domain]
        entry: dict = {
            "domain": domain,
            "card_type": card_type,
            "code_field": code_field,
            "model": None,
        }
        model = await resolve_active_model(db, domain)
        if model is not None:
            items = await items_for(db, model.id)
            card_codes = await scan_domain_card_codes(db, domain)
            mappings = await explicit_mappings_for_model(db, model.id)
            cov = compute_model_coverage(items, card_codes, mappings)
            entry["model"] = model_dict(model, item_count=len(items))
            entry.update(
                {
                    "covered_items": cov["covered_items"],
                    "total_cards": cov["total_cards"],
                    "mapped_cards": cov["mapped_cards"],
                    "unmatched_cards": cov["unmatched_cards"],
                    "uncoded_cards": cov["uncoded_cards"],
                }
            )
        out.append(entry)
    return {"models": out}


@router.get("/{model_id}/summary")
async def model_summary(
    model_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The model with its item tree annotated with mapped-inventory counts."""
    await PermissionService.require_permission(db, user, "reference_models.view")
    model = await _get_model(db, model_id)
    card_type, code_field = RM_DOMAIN_CARD_TYPES[model.domain]
    items = await items_for(db, model_id)
    card_codes = await scan_domain_card_codes(db, model.domain)
    mappings = await explicit_mappings_for_model(db, model.id)
    cov = compute_model_coverage(items, card_codes, mappings)
    per_item = cov["per_item"]
    out_items = []
    for i in sort_items(items):
        d = item_dict(i)
        own, total = per_item.get(i.id, (set(), set()))
        d["mapped_direct"] = len(own)
        d["mapped_total"] = len(total)
        out_items.append(d)
    return {
        "model": model_dict(model, item_count=len(items)),
        "card_type": card_type,
        "code_field": code_field,
        "items": out_items,
        "totals": {
            "total_items": len(items),
            "covered_items": cov["covered_items"],
            "total_cards": cov["total_cards"],
            "mapped_cards": cov["mapped_cards"],
            "unmatched_cards": cov["unmatched_cards"],
            "uncoded_cards": cov["uncoded_cards"],
        },
    }


@router.get("/{model_id}/items/{item_id}/cards")
async def item_mapped_cards(
    model_id: uuid.UUID,
    item_id: uuid.UUID,
    include_descendants: bool = True,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Inventory cards mapped to one item — via the RM code field or an
    explicit mapping row. Explicit mappings carry type/status/rationale; a
    code-only match surfaces as an implicit ``primary`` mapping."""
    await PermissionService.require_permission(db, user, "reference_models.view")
    model = await _get_model(db, model_id)
    items = await items_for(db, model_id)
    by_id = {i.id: i for i in items}
    item = by_id.get(item_id)
    if item is None or item.model_id != model.id:
        raise HTTPException(404, "Item not found")

    scope_ids = _descendant_item_ids(items, item.id) if include_descendants else {item.id}
    scope_codes = {by_id[i].code for i in scope_ids if i in by_id}

    _card_type, code_field = RM_DOMAIN_CARD_TYPES[model.domain]

    # Explicit mappings to items in scope (keyed by card; prefer the one on the
    # selected item itself over a descendant's for the surfaced metadata).
    mappings = await explicit_mappings_for_model(db, model.id)
    explicit_by_card: dict[uuid.UUID, ReferenceModelMapping] = {}
    for m in mappings:
        if m.item_id in scope_ids and m.mapping_status != "rejected":
            cur = explicit_by_card.get(m.card_id)
            if cur is None or (cur.item_id != item.id and m.item_id == item.id):
                explicit_by_card[m.card_id] = m

    # Code-matched cards of the domain type.
    rows = await db.execute(select(Card).where(Card.status != "ARCHIVED"))
    all_cards = {c.id: c for c in rows.scalars().all()}

    result: list[dict] = []
    seen: set[uuid.UUID] = set()

    def _emit(card: Card, code: str | None, m: ReferenceModelMapping | None) -> None:
        result.append(
            {
                "id": str(card.id),
                "name": card.name,
                "type": card.type,
                "subtype": card.subtype,
                "status": card.status,
                "approval_status": card.approval_status,
                "data_quality": card.data_quality,
                "code": code,
                "source": "explicit" if m else "code",
                "mapping_id": str(m.id) if m else None,
                "mapping_type": m.mapping_type if m else "primary",
                "mapping_status": m.mapping_status if m else None,
                "rationale": m.rationale if m else None,
                "confidence": m.confidence if m else None,
            }
        )

    for card in all_cards.values():
        code = (card.attributes or {}).get(code_field)
        code = code.strip() if isinstance(code, str) and code.strip() else None
        m = explicit_by_card.get(card.id)
        if (code and code in scope_codes) or m is not None:
            seen.add(card.id)
            _emit(card, code, m)
        if len(result) >= 500:
            break
    # Explicit mappings whose card isn't of the domain type still surface.
    for cid, m in explicit_by_card.items():
        if cid not in seen and cid in all_cards and len(result) < 500:
            card = all_cards[cid]
            code = (card.attributes or {}).get(code_field)
            code = code.strip() if isinstance(code, str) and code.strip() else None
            _emit(card, code, m)

    result.sort(key=lambda c: (c["code"] or "~", c["name"].lower()))
    return {"item": item_dict(item), "code_field": code_field, "cards": result}


# --------------------------------------------------------------------------- #
# Explicit mappings (RMPlan Phase 2) — M:N card↔item with metadata
# --------------------------------------------------------------------------- #
@router.get("/items/{item_id}/mappings")
async def list_item_mappings(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Explicit mappings on one item, with the linked card's name/type."""
    await PermissionService.require_permission(db, user, "reference_models.view")
    item = await _get_item(db, item_id)
    rows = (
        (
            await db.execute(
                select(ReferenceModelMapping).where(ReferenceModelMapping.item_id == item.id)
            )
        )
        .scalars()
        .all()
    )
    card_ids = {m.card_id for m in rows}
    cards = {}
    if card_ids:
        for c in (await db.execute(select(Card).where(Card.id.in_(card_ids)))).scalars().all():
            cards[c.id] = {"id": str(c.id), "name": c.name, "type": c.type, "subtype": c.subtype}
    names = await _user_names(db, {m.reviewed_by for m in rows})
    return {
        "mappings": [{**mapping_dict(m, names=names), "card": cards.get(m.card_id)} for m in rows]
    }


@router.post("/items/{item_id}/mappings")
async def create_item_mapping(
    item_id: uuid.UUID,
    payload: MappingCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Map an inventory card to a reference-model item."""
    await PermissionService.require_permission(db, user, "reference_models.map")
    item = await _get_item(db, item_id)
    card = (await db.execute(select(Card).where(Card.id == payload.card_id))).scalar_one_or_none()
    if card is None:
        raise HTTPException(404, "Card not found")
    existing = (
        await db.execute(
            select(ReferenceModelMapping).where(
                ReferenceModelMapping.item_id == item.id,
                ReferenceModelMapping.card_id == payload.card_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(409, "This card is already mapped to this item")
    now = datetime.now(timezone.utc)
    mapping = ReferenceModelMapping(
        model_id=item.model_id,
        item_id=item.id,
        card_id=payload.card_id,
        mapping_type=payload.mapping_type,
        mapping_status=payload.mapping_status,
        rationale=payload.rationale,
        confidence=payload.confidence,
        reviewed_at=now if payload.mapping_status == "confirmed" else None,
        reviewed_by=user.id if payload.mapping_status == "confirmed" else None,
        created_by=user.id,
    )
    db.add(mapping)
    await db.flush()
    await event_bus.publish(
        "reference_model_mapping.created",
        {
            "id": str(mapping.id),
            "model_id": str(item.model_id),
            "item_id": str(item.id),
            "item_code": item.code,
            "card_id": str(payload.card_id),
            "card_name": card.name,
            "mapping_type": mapping.mapping_type,
        },
        db=db,
        user_id=user.id,
        card_id=payload.card_id,
    )
    await db.commit()
    return mapping_dict(mapping)


@router.patch("/mappings/{mapping_id}")
async def update_mapping(
    mapping_id: uuid.UUID,
    payload: MappingUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reference_models.map")
    mapping = (
        await db.execute(
            select(ReferenceModelMapping).where(ReferenceModelMapping.id == mapping_id)
        )
    ).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(404, "Mapping not found")
    data = payload.model_dump(exclude_unset=True)
    if "mapping_type" in data:
        mapping.mapping_type = data["mapping_type"]
    if "rationale" in data:
        mapping.rationale = data["rationale"]
    if "confidence" in data:
        mapping.confidence = data["confidence"]
    if "mapping_status" in data and data["mapping_status"] != mapping.mapping_status:
        mapping.mapping_status = data["mapping_status"]
        if mapping.mapping_status == "confirmed":
            mapping.reviewed_at = datetime.now(timezone.utc)
            mapping.reviewed_by = user.id
    await event_bus.publish(
        "reference_model_mapping.updated",
        {
            "id": str(mapping.id),
            "item_id": str(mapping.item_id),
            "card_id": str(mapping.card_id),
            "mapping_type": mapping.mapping_type,
            "mapping_status": mapping.mapping_status,
        },
        db=db,
        user_id=user.id,
        card_id=mapping.card_id,
    )
    await db.commit()
    return mapping_dict(mapping)


@router.delete("/mappings/{mapping_id}", status_code=204)
async def delete_mapping(
    mapping_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reference_models.map")
    mapping = (
        await db.execute(
            select(ReferenceModelMapping).where(ReferenceModelMapping.id == mapping_id)
        )
    ).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(404, "Mapping not found")
    card_id = mapping.card_id
    item_id = mapping.item_id
    await db.delete(mapping)
    await event_bus.publish(
        "reference_model_mapping.deleted",
        {"id": str(mapping_id), "item_id": str(item_id), "card_id": str(card_id)},
        db=db,
        user_id=user.id,
        card_id=card_id,
    )
    await db.commit()


async def _item_briefs(db: AsyncSession, item_ids: set[uuid.UUID]) -> dict[uuid.UUID, dict]:
    """Return {item_id: {id, code, name, model_id, model_domain, model_name}}."""
    if not item_ids:
        return {}
    items = (
        (await db.execute(select(ReferenceModelItem).where(ReferenceModelItem.id.in_(item_ids))))
        .scalars()
        .all()
    )
    model_ids = {i.model_id for i in items}
    models = {}
    if model_ids:
        for m in (
            (await db.execute(select(ReferenceModel).where(ReferenceModel.id.in_(model_ids))))
            .scalars()
            .all()
        ):
            models[m.id] = {"domain": m.domain, "name": m.name}
    out: dict[uuid.UUID, dict] = {}
    for i in items:
        model = models.get(i.model_id, {})
        out[i.id] = {
            "id": str(i.id),
            "code": i.code,
            "name": i.name,
            "name_ar": i.name_ar,
            "model_id": str(i.model_id),
            "model_domain": model.get("domain"),
            "model_name": model.get("name"),
        }
    return out


def _relationship_dict(r: ReferenceModelRelationship, briefs: dict[uuid.UUID, dict]) -> dict:
    return {
        "id": str(r.id),
        "relationship_type": r.relationship_type,
        "description": r.description,
        "source_item": briefs.get(r.source_item_id),
        "target_item": briefs.get(r.target_item_id),
    }


@router.get("/relationship-types")
async def relationship_types(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The vocabulary of cross-model relationship types (RMPlan §10)."""
    await PermissionService.require_permission(db, user, "reference_models.view")
    return {"relationship_types": list(REFERENCE_MODEL_RELATIONSHIP_TYPES)}


@router.get("/items/{item_id}/relationships")
async def list_item_relationships(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Cross-model relationships where this item is the source or the target."""
    await PermissionService.require_permission(db, user, "reference_models.view")
    item = await _get_item(db, item_id)
    rows = (
        (
            await db.execute(
                select(ReferenceModelRelationship).where(
                    or_(
                        ReferenceModelRelationship.source_item_id == item.id,
                        ReferenceModelRelationship.target_item_id == item.id,
                    )
                )
            )
        )
        .scalars()
        .all()
    )
    ids: set[uuid.UUID] = {item.id}
    for r in rows:
        ids.add(r.source_item_id)
        ids.add(r.target_item_id)
    briefs = await _item_briefs(db, ids)
    outgoing = [
        {**_relationship_dict(r, briefs), "direction": "outgoing"}
        for r in rows
        if r.source_item_id == item.id
    ]
    incoming = [
        {**_relationship_dict(r, briefs), "direction": "incoming"}
        for r in rows
        if r.target_item_id == item.id and r.source_item_id != item.id
    ]
    return {"item": briefs.get(item.id), "outgoing": outgoing, "incoming": incoming}


@router.post("/items/{item_id}/relationships", status_code=201)
async def create_item_relationship(
    item_id: uuid.UUID,
    payload: RelationshipCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Link this item to another reference-model item with a typed relationship."""
    await PermissionService.require_permission(db, user, "reference_models.map")
    source = await _get_item(db, item_id)
    if payload.target_item_id == source.id:
        raise HTTPException(400, "An item cannot be related to itself")
    target = await _get_item(db, payload.target_item_id)
    existing = (
        await db.execute(
            select(ReferenceModelRelationship).where(
                ReferenceModelRelationship.source_item_id == source.id,
                ReferenceModelRelationship.target_item_id == target.id,
                ReferenceModelRelationship.relationship_type == payload.relationship_type,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(409, "This relationship already exists")
    rel = ReferenceModelRelationship(
        source_item_id=source.id,
        target_item_id=target.id,
        relationship_type=payload.relationship_type,
        description=payload.description,
        created_by=user.id,
    )
    db.add(rel)
    await db.flush()
    await event_bus.publish(
        "reference_model_relationship.created",
        {
            "id": str(rel.id),
            "source_item_id": str(source.id),
            "target_item_id": str(target.id),
            "relationship_type": rel.relationship_type,
        },
        db=db,
        user_id=user.id,
    )
    briefs = await _item_briefs(db, {source.id, target.id})
    await db.commit()
    return _relationship_dict(rel, briefs)


@router.delete("/relationships/{relationship_id}", status_code=204)
async def delete_relationship(
    relationship_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reference_models.map")
    rel = (
        await db.execute(
            select(ReferenceModelRelationship).where(
                ReferenceModelRelationship.id == relationship_id
            )
        )
    ).scalar_one_or_none()
    if rel is None:
        raise HTTPException(404, "Relationship not found")
    await db.delete(rel)
    await event_bus.publish(
        "reference_model_relationship.deleted",
        {"id": str(relationship_id)},
        db=db,
        user_id=user.id,
    )
    await db.commit()


@router.get("/{model_id}/unmapped-inventory")
async def unmapped_inventory(
    model_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Cards of the model's domain type not mapped to any of its items —
    neither via a resolving code field nor an explicit mapping."""
    await PermissionService.require_permission(db, user, "reference_models.view")
    model = await _get_model(db, model_id)
    card_type, code_field = RM_DOMAIN_CARD_TYPES[model.domain]
    items = await items_for(db, model.id)
    item_codes = {i.code for i in items}
    mappings = await explicit_mappings_for_model(db, model.id)
    mapped_card_ids = {m.card_id for m in mappings if m.mapping_status != "rejected"}

    rows = await db.execute(select(Card).where(Card.type == card_type, Card.status != "ARCHIVED"))
    cards = []
    for card in rows.scalars().all():
        if card.id in mapped_card_ids:
            continue
        code = (card.attributes or {}).get(code_field)
        code = code.strip() if isinstance(code, str) and code.strip() else None
        if code and code in item_codes:
            continue  # classified via code
        cards.append(
            {
                "id": str(card.id),
                "name": card.name,
                "type": card.type,
                "subtype": card.subtype,
                "status": card.status,
                "approval_status": card.approval_status,
                "data_quality": card.data_quality,
                "code": code,  # a non-resolving code, or None (truly unclassified)
            }
        )
    cards.sort(key=lambda c: c["name"].lower())
    return {"card_type": card_type, "code_field": code_field, "cards": cards}


@router.get("/{model_id}/gaps")
async def coverage_gaps(
    model_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Coverage + gap analysis (RMPlan Phase 4 / §8).

    Classifies the model's leaf capabilities into: uncovered (no mapped card),
    duplicate support (≥2 mapped cards — possible redundancy), and retiring-only
    (every mapped card is phasing out / end-of-life). Returns KPI totals, the
    flagged gap rows, and a per-leaf coverage matrix.
    """
    await PermissionService.require_permission(db, user, "reference_models.view")
    model = await _get_model(db, model_id)
    card_type, code_field = RM_DOMAIN_CARD_TYPES[model.domain]
    items = await items_for(db, model.id)
    card_codes = await scan_domain_card_codes(db, model.domain)
    mappings = await explicit_mappings_for_model(db, model.id)
    cov = compute_model_coverage(items, card_codes, mappings)
    per_item = cov["per_item"]  # {item_id: (own_set, total_set)}
    leaves = leaf_item_ids(items)
    by_id = {i.id: i for i in items}

    # Card meta (name + lifecycle) for every card that could be mapped.
    explicit_ids = {m.card_id for m in mappings if m.mapping_status != "rejected"}
    where = Card.type == card_type
    if explicit_ids:
        where = or_(where, Card.id.in_(explicit_ids))
    rows = await db.execute(
        select(Card.id, Card.name, Card.lifecycle).where(where, Card.status != "ARCHIVED")
    )
    meta = {cid: (name, lifecycle) for cid, name, lifecycle in rows.all()}

    gaps: list[dict] = []
    matrix: list[dict] = []
    uncovered = duplicate = retiring = 0

    for iid in leaves:
        item = by_id.get(iid)
        if item is None:
            continue
        own = per_item.get(iid, (set(), set()))[0]
        card_names = [meta.get(cid, ("", None))[0] for cid in own if cid in meta]
        retiring_flag = bool(own) and all(is_retiring(meta.get(cid, ("", None))[1]) for cid in own)
        coverage = "covered" if own else "none"
        matrix.append(
            {
                "item_id": str(iid),
                "code": item.code,
                "name": item.name,
                "name_ar": item.name_ar,
                "mapped": len(own),
                "coverage": coverage,
                "lifecycle_risk": retiring_flag,
                "duplicate": len(own) >= 2,
            }
        )
        base = {
            "item_id": str(iid),
            "code": item.code,
            "name": item.name,
            "name_ar": item.name_ar,
            "mapped": len(own),
            "cards": sorted(n for n in card_names if n),
        }
        if not own:
            uncovered += 1
            gaps.append({**base, "kind": "no_mapping"})
        else:
            if len(own) >= 2:
                duplicate += 1
                gaps.append({**base, "kind": "duplicate"})
            if retiring_flag:
                retiring += 1
                gaps.append({**base, "kind": "retiring_only"})

    matrix.sort(key=lambda r: r["code"])
    gap_order = {"no_mapping": 0, "duplicate": 1, "retiring_only": 2}
    gaps.sort(key=lambda g: (gap_order.get(g["kind"], 9), g["code"]))
    total_leaves = len(leaves)
    covered_leaves = total_leaves - uncovered

    return {
        "model": model_dict(model, item_count=len(items)),
        "totals": {
            "total_items": len(items),
            "total_leaves": total_leaves,
            "covered_leaves": covered_leaves,
            "uncovered_leaves": uncovered,
            "duplicate_leaves": duplicate,
            "retiring_leaves": retiring,
            "unmapped_cards": cov["unmatched_cards"] + cov["uncoded_cards"],
            "coverage_pct": round(covered_leaves / total_leaves * 100) if total_leaves else 0,
        },
        "gaps": gaps,
        "matrix": matrix,
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


@router.patch("/{model_id}/narrative")
async def update_narrative(
    model_id: uuid.UUID,
    payload: NarrativePayload,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Replace the model's poster narrative (RMPlan Phase 3)."""
    await PermissionService.require_permission(db, user, "reference_models.manage")
    model = await _get_model(db, model_id)
    model.narrative = payload.model_dump()
    await event_bus.publish(
        "reference_model.narrative_updated",
        {"id": str(model.id), "panels": len(payload.panels)},
        db=db,
        user_id=user.id,
    )
    await db.commit()
    items = await items_for(db, model.id)
    return model_dict(model, item_count=len(items))


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
class SubmitPayload(BaseModel):
    change_summary: str | None = Field(default=None, max_length=2000)


class RejectPayload(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


@router.post("/{model_id}/submit")
async def submit_for_review(
    model_id: uuid.UUID,
    payload: SubmitPayload | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Move a draft into review (the governance gate before publishing)."""
    await PermissionService.require_permission(db, user, "reference_models.manage")
    model = await _get_model(db, model_id)
    if model.status not in ("draft",):
        raise HTTPException(400, "Only a draft can be submitted for review")
    model.status = "in_review"
    await event_bus.publish(
        "reference_model.submitted",
        {"id": str(model.id), "domain": model.domain, "name": model.name},
        db=db,
        user_id=user.id,
    )
    await db.commit()
    return model_dict(model)


@router.post("/{model_id}/reject")
async def reject_model(
    model_id: uuid.UUID,
    payload: RejectPayload | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Reject a model in review, sending it back to draft (governance action)."""
    await PermissionService.require_permission(db, user, "reference_models.manage")
    await PermissionService.require_permission(db, user, "governance.approve_step")
    model = await _get_model(db, model_id)
    if model.status != "in_review":
        raise HTTPException(400, "Only a model in review can be rejected")
    model.status = "draft"
    await event_bus.publish(
        "reference_model.rejected",
        {
            "id": str(model.id),
            "domain": model.domain,
            "name": model.name,
            "reason": (payload.reason if payload else None),
        },
        db=db,
        user_id=user.id,
    )
    await db.commit()
    return model_dict(model)


@router.post("/{model_id}/publish")
async def publish_model(
    model_id: uuid.UUID,
    payload: SubmitPayload | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Publish a model (supersedes the previously published RM of its domain)
    and snapshot its item tree as a preserved version."""
    await PermissionService.require_permission(db, user, "reference_models.manage")
    await PermissionService.require_permission(db, user, "governance.approve_step")
    model = await _get_model(db, model_id)
    if model.status == "published":
        raise HTTPException(400, "Reference model is already published")

    superseded = await resolve_active_model(db, model.domain)
    if superseded is not None and superseded.id != model.id:
        superseded.status = "archived"

    now = datetime.now(timezone.utc)
    model.status = "published"
    model.published_by = user.id
    model.published_at = now

    items = await items_for(db, model.id)
    db.add(
        ReferenceModelVersion(
            model_id=model.id,
            version=model.version,
            change_summary=(payload.change_summary if payload else None),
            snapshot=snapshot_items(items),
            item_count=len(items),
            published_by=user.id,
            published_at=now,
        )
    )
    await event_bus.publish(
        "reference_model.published",
        {
            "id": str(model.id),
            "domain": model.domain,
            "name": model.name,
            "version": model.version,
            "superseded_id": str(superseded.id) if superseded else None,
        },
        db=db,
        user_id=user.id,
    )
    await db.commit()
    return model_dict(model, item_count=len(items))


@router.get("/{model_id}/versions")
async def list_versions(
    model_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Preserved publish snapshots for a model, newest first."""
    await PermissionService.require_permission(db, user, "reference_models.view")
    model = await _get_model(db, model_id)
    versions = await versions_for(db, model.id)
    names = await _user_names(db, {v.published_by for v in versions})
    return {"versions": [version_dict(v, names=names) for v in versions]}


@router.get("/{model_id}/versions/{version_id}")
async def get_version(
    model_id: uuid.UUID,
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "reference_models.view")
    version = (
        await db.execute(
            select(ReferenceModelVersion).where(
                ReferenceModelVersion.id == version_id,
                ReferenceModelVersion.model_id == model_id,
            )
        )
    ).scalar_one_or_none()
    if version is None:
        raise HTTPException(404, "Version not found")
    names = await _user_names(db, {version.published_by})
    return version_dict(version, names=names, include_snapshot=True)


@router.get("/{model_id}/versions/{version_id}/diff")
async def diff_version(
    model_id: uuid.UUID,
    version_id: uuid.UUID,
    against: str = "current",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Diff a version against the live model (``against=current``) or another
    version (``against=<version_id>``), by item code."""
    await PermissionService.require_permission(db, user, "reference_models.view")
    model = await _get_model(db, model_id)

    async def _load(vid: uuid.UUID) -> ReferenceModelVersion:
        v = (
            await db.execute(
                select(ReferenceModelVersion).where(
                    ReferenceModelVersion.id == vid,
                    ReferenceModelVersion.model_id == model_id,
                )
            )
        ).scalar_one_or_none()
        if v is None:
            raise HTTPException(404, "Version not found")
        return v

    base = await _load(version_id)
    if against == "current":
        after = snapshot_items(await items_for(db, model.id))
        after_label = "current"
    else:
        try:
            other_id = uuid.UUID(against)
        except ValueError as exc:
            raise HTTPException(422, "against must be 'current' or a version id") from exc
        other = await _load(other_id)
        after = other.snapshot or []
        after_label = str(other.id)
    return {
        "base": {"version_id": str(base.id), "version": base.version},
        "against": after_label,
        "diff": diff_snapshots(base.snapshot or [], after),
    }


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
