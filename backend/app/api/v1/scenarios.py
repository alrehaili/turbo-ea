"""Scenario Planning & Transition Architecture API (Wave 3 #8/#9).

Copy-on-write overlay: a scenario stores add/modify/retire deltas against the
live baseline. ``/diff`` renders As-Is vs To-Be with an impact rollup; ``/merge``
applies the changes to the real repository with existence-based conflict
detection. See ``app.models.scenario``.

[FORK FEATURE]
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.card import Card
from app.models.scenario import (
    CHANGE_OPS,
    SCENARIO_STATUSES,
    Scenario,
    ScenarioChange,
)
from app.models.user import User
from app.services.event_bus import event_bus
from app.services.impact_service import gather_impact
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


# --------------------------------------------------------------------------- #
# Schemas                                                                      #
# --------------------------------------------------------------------------- #
class ScenarioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    description: str | None = None


class ScenarioUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    status: str | None = None


class ChangeCreate(BaseModel):
    op: str
    card_type: str | None = None
    target_card_id: uuid.UUID | None = None
    name: str | None = None
    payload: dict | None = None


# --------------------------------------------------------------------------- #
# Serialisation                                                               #
# --------------------------------------------------------------------------- #
def _scenario_dict(s: Scenario) -> dict:
    return {
        "id": str(s.id),
        "name": s.name,
        "description": s.description,
        "status": s.status,
        "merged_at": s.merged_at.isoformat() if s.merged_at else None,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


def _change_dict(c: ScenarioChange) -> dict:
    return {
        "id": str(c.id),
        "op": c.op,
        "card_type": c.card_type,
        "target_card_id": str(c.target_card_id) if c.target_card_id else None,
        "name": c.name,
        "payload": c.payload or {},
        "merge_status": c.merge_status,
    }


async def _get_scenario(db: AsyncSession, sid: uuid.UUID) -> Scenario:
    res = await db.execute(select(Scenario).where(Scenario.id == sid))
    s = res.scalar_one_or_none()
    if s is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return s


async def _changes(db: AsyncSession, sid: uuid.UUID) -> list[ScenarioChange]:
    res = await db.execute(
        select(ScenarioChange)
        .where(ScenarioChange.scenario_id == sid)
        .order_by(ScenarioChange.created_at)
    )
    return list(res.scalars().all())


# --------------------------------------------------------------------------- #
# Scenario CRUD                                                               #
# --------------------------------------------------------------------------- #
@router.get("")
async def list_scenarios(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "scenarios.view")
    res = await db.execute(select(Scenario).order_by(Scenario.created_at.desc()))
    scenarios = list(res.scalars().all())
    counts: dict[uuid.UUID, int] = {}
    cres = await db.execute(select(ScenarioChange.scenario_id))
    for (sid,) in cres.all():
        counts[sid] = counts.get(sid, 0) + 1
    return [{**_scenario_dict(s), "change_count": counts.get(s.id, 0)} for s in scenarios]


@router.post("", status_code=201)
async def create_scenario(
    body: ScenarioCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "scenarios.manage")
    s = Scenario(name=body.name, description=body.description, status="draft", created_by=user.id)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return _scenario_dict(s)


@router.get("/{scenario_id}")
async def get_scenario(
    scenario_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "scenarios.view")
    s = await _get_scenario(db, scenario_id)
    return {
        **_scenario_dict(s),
        "changes": [_change_dict(c) for c in await _changes(db, scenario_id)],
    }


@router.patch("/{scenario_id}")
async def update_scenario(
    scenario_id: uuid.UUID,
    body: ScenarioUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "scenarios.manage")
    s = await _get_scenario(db, scenario_id)
    data = body.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in SCENARIO_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status: {data['status']}")
    for key, value in data.items():
        setattr(s, key, value)
    await db.commit()
    await db.refresh(s)
    return _scenario_dict(s)


@router.delete("/{scenario_id}", status_code=204)
async def delete_scenario(
    scenario_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "scenarios.manage")
    s = await _get_scenario(db, scenario_id)
    await db.delete(s)
    await db.commit()


# --------------------------------------------------------------------------- #
# Changes                                                                     #
# --------------------------------------------------------------------------- #
@router.post("/{scenario_id}/changes", status_code=201)
async def add_change(
    scenario_id: uuid.UUID,
    body: ChangeCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "scenarios.manage")
    s = await _get_scenario(db, scenario_id)
    if s.status in ("merged", "discarded"):
        raise HTTPException(status_code=400, detail="Scenario is closed")
    if body.op not in CHANGE_OPS:
        raise HTTPException(status_code=400, detail=f"Invalid op: {body.op}")

    card_type = body.card_type
    name = body.name
    if body.op in ("modify", "retire"):
        if not body.target_card_id:
            raise HTTPException(status_code=400, detail="target_card_id required")
        res = await db.execute(select(Card).where(Card.id == body.target_card_id))
        target = res.scalar_one_or_none()
        if target is None:
            raise HTTPException(status_code=404, detail="Target card not found")
        card_type = target.type
        name = name or target.name
    elif body.op == "add":
        if not card_type or not name:
            raise HTTPException(status_code=400, detail="card_type and name required for add")

    change = ScenarioChange(
        scenario_id=scenario_id,
        op=body.op,
        card_type=card_type,
        target_card_id=body.target_card_id,
        name=name,
        payload=body.payload or {},
    )
    db.add(change)
    await db.commit()
    await db.refresh(change)
    return _change_dict(change)


@router.delete("/changes/{change_id}", status_code=204)
async def delete_change(
    change_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "scenarios.manage")
    res = await db.execute(select(ScenarioChange).where(ScenarioChange.id == change_id))
    c = res.scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=404, detail="Change not found")
    await db.delete(c)
    await db.commit()


# --------------------------------------------------------------------------- #
# Diff + impact                                                               #
# --------------------------------------------------------------------------- #
@router.get("/{scenario_id}/diff")
async def scenario_diff(
    scenario_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """As-Is vs To-Be: per-change before/after plus an aggregate impact rollup for
    the modified/retired cards (reuses the change-impact engine)."""
    await PermissionService.require_permission(db, user, "scenarios.view")
    await _get_scenario(db, scenario_id)
    changes = await _changes(db, scenario_id)

    # Resolve target cards for before-state.
    target_ids = {c.target_card_id for c in changes if c.target_card_id}
    cards: dict[uuid.UUID, Card] = {}
    if target_ids:
        res = await db.execute(select(Card).where(Card.id.in_(target_ids)))
        cards = {c.id: c for c in res.scalars().all()}

    rows: list[dict] = []
    affected_total = 0
    counts = {"add": 0, "modify": 0, "retire": 0}
    for c in changes:
        counts[c.op] = counts.get(c.op, 0) + 1
        before = None
        impact = None
        if c.target_card_id and c.target_card_id in cards:
            tc = cards[c.target_card_id]
            before = {"name": tc.name, "type": tc.type, "attributes": tc.attributes or {}}
            if c.op in ("modify", "retire"):
                try:
                    imp = await gather_impact(db, c.target_card_id, depth=1, change_type=c.op)
                    impact = imp["summary"]["total_affected"]
                    affected_total += impact
                except ValueError:
                    impact = None
        rows.append(
            {
                **_change_dict(c),
                "before": before,
                "missing_target": bool(
                    c.op in ("modify", "retire")
                    and c.target_card_id
                    and c.target_card_id not in cards
                ),
                "impact_affected": impact,
            }
        )

    return {
        "summary": {
            "changes": len(changes),
            "added": counts["add"],
            "modified": counts["modify"],
            "retired": counts["retire"],
            "impact_affected": affected_total,
        },
        "changes": rows,
    }


# --------------------------------------------------------------------------- #
# Merge                                                                       #
# --------------------------------------------------------------------------- #
@router.post("/{scenario_id}/merge")
async def merge_scenario(
    scenario_id: uuid.UUID,
    dry_run: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Apply the scenario's changes to the live repository.

    add → create card, modify → patch fields, retire → archive. Existence-based
    conflict detection: a modify/retire whose target card no longer exists is
    reported as a conflict and skipped. ``dry_run=true`` reports the outcome
    without writing.
    """
    await PermissionService.require_permission(db, user, "scenarios.merge")
    s = await _get_scenario(db, scenario_id)
    if s.status == "merged":
        raise HTTPException(status_code=400, detail="Scenario already merged")

    changes = await _changes(db, scenario_id)
    applied = 0
    conflicts = 0
    results: list[dict] = []
    now = datetime.now(timezone.utc)

    for c in changes:
        outcome = "applied"
        if c.op == "add":
            if not dry_run:
                card = Card(
                    type=c.card_type,
                    name=c.name or "(unnamed)",
                    attributes=(c.payload or {}).get("attributes", {}),
                    description=(c.payload or {}).get("description"),
                    status="ACTIVE",
                    approval_status="DRAFT",
                    created_by=user.id,
                    updated_by=user.id,
                )
                db.add(card)
                await db.flush()
            applied += 1
        else:
            res = await db.execute(
                select(Card).where(Card.id == c.target_card_id, Card.status == "ACTIVE")
            )
            target = res.scalar_one_or_none()
            if target is None:
                outcome = "conflict"
                conflicts += 1
            elif c.op == "retire":
                if not dry_run:
                    target.status = "ARCHIVED"
                    target.archived_at = now
                    target.updated_by = user.id
                applied += 1
            elif c.op == "modify":
                if not dry_run:
                    payload = c.payload or {}
                    if "name" in payload:
                        target.name = payload["name"]
                    if "description" in payload:
                        target.description = payload["description"]
                    if "attributes" in payload and isinstance(payload["attributes"], dict):
                        target.attributes = {**(target.attributes or {}), **payload["attributes"]}
                    target.updated_by = user.id
                applied += 1
        if not dry_run:
            c.merge_status = outcome
        results.append({"id": str(c.id), "op": c.op, "name": c.name, "outcome": outcome})

    if not dry_run:
        s.status = "merged"
        s.merged_by = user.id
        s.merged_at = now
        await event_bus.publish(
            "scenario.merged",
            {"id": str(s.id), "applied": applied, "conflicts": conflicts},
            db=db,
            user_id=user.id,
        )
        await db.commit()

    return {
        "dry_run": dry_run,
        "applied": applied,
        "conflicts": conflicts,
        "results": results,
    }
