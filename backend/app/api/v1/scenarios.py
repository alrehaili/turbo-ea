"""Scenario Planning & Transition Architecture API (Wave 3 #8/#9).

Copy-on-write overlay: a scenario stores add/modify/retire (card) and
add_relation/remove_relation (relation) deltas against the live baseline.
``/diff`` renders As-Is vs To-Be with an impact rollup; ``/merge`` applies the
changes to the real repository with both **existence** and **baseline-drift**
(field-level) conflict detection. See ``app.models.scenario``.

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
from app.models.card_type import CardType
from app.models.relation import Relation
from app.models.relation_type import RelationType
from app.models.scenario import (
    CHANGE_OPS,
    RELATION_CHANGE_OPS,
    SCENARIO_STATUSES,
    Scenario,
    ScenarioChange,
)
from app.models.user import User
from app.services.card_read_scope import CardReadScope, require_card_readable
from app.services.cost_field_filter import cost_field_keys_from_card_schema
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
        "baseline": c.baseline,
        "merge_status": c.merge_status,
    }


def _capture_modify_baseline(target: Card, payload: dict) -> dict:
    """Snapshot the live values of exactly the fields a modify change touches."""
    base: dict = {}
    if "name" in payload:
        base["name"] = target.name
    if "description" in payload:
        base["description"] = target.description
    if isinstance(payload.get("attributes"), dict):
        live_attrs = target.attributes or {}
        base["attributes"] = {k: live_attrs.get(k) for k in payload["attributes"]}
    return base


def _field_drift(change: ScenarioChange, live: Card) -> list[str]:
    """Fields whose live value has moved away from the captured baseline.

    A non-empty result means the card was edited on the baseline after this
    change was captured, so applying the modify would clobber that edit.
    """
    base = change.baseline or {}
    drift: list[str] = []
    if "name" in base and live.name != base["name"]:
        drift.append("name")
    if "description" in base and live.description != base["description"]:
        drift.append("description")
    if "attributes" in base:
        live_attrs = live.attributes or {}
        for k, bv in base["attributes"].items():
            if live_attrs.get(k) != bv:
                drift.append(f"attributes.{k}")
    return drift


async def _relation_exists(
    db: AsyncSession, rel_type: str, source_id: uuid.UUID, target_id: uuid.UUID
) -> Relation | None:
    res = await db.execute(
        select(Relation).where(
            Relation.type == rel_type,
            Relation.source_id == source_id,
            Relation.target_id == target_id,
        )
    )
    return res.scalar_one_or_none()


async def _get_scenario(db: AsyncSession, sid: uuid.UUID) -> Scenario:
    res = await db.execute(select(Scenario).where(Scenario.id == sid))
    s = res.scalar_one_or_none()
    if s is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return s


def _referenced_card_ids(c: ScenarioChange) -> set[uuid.UUID]:
    """Every card a change names: its target, or a relation change's two ends."""
    ids: set[uuid.UUID] = {c.target_card_id} if c.target_card_id else set()
    payload = c.payload or {}
    for key in ("source_id", "target_id"):
        value = payload.get(key)
        if value:
            try:
                ids.add(uuid.UUID(str(value)))
            except ValueError:
                continue
    return ids


async def _visible_changes(
    db: AsyncSession, changes: list[ScenarioChange], read_scope: CardReadScope
) -> list[ScenarioChange]:
    """The changes the reader may see.

    A change is about the card(s) it names, and its name, payload and baseline
    describe them, so a change naming a hidden card is omitted rather than
    redacted (decision D-30). The rows themselves are untouched.
    """
    refs = {c.id: _referenced_card_ids(c) for c in changes}
    hidden = await read_scope.hidden_card_ids(
        db, set().union(*refs.values()) if refs else set(), mode="module"
    )
    return [c for c in changes if not refs[c.id] & hidden]


async def _cost_policy(
    db: AsyncSession, user: User, changes: list[ScenarioChange]
) -> tuple[dict[str, frozenset[str]], set[uuid.UUID]] | None:
    """None when the caller sees every cost; else (cost keys per type, cost-ok ids).

    The rule is the card endpoints' one: ``costs.view``, or a stakeholder role
    on the card itself.
    """
    if await PermissionService.has_app_permission(db, user, "costs.view"):
        return None
    type_keys = {c.card_type for c in changes if c.card_type}
    rows = (
        await db.execute(
            select(CardType.key, CardType.fields_schema).where(CardType.key.in_(type_keys))
        )
    ).all()
    keys = {k: cost_field_keys_from_card_schema(schema) for k, schema in rows}
    target_ids = [c.target_card_id for c in changes if c.target_card_id]
    allowed = (
        await PermissionService.card_ids_with_cost_access(db, user, target_ids)
        if target_ids
        else set()
    )
    return keys, allowed


def _strip_costs(attrs, card_type: str | None, card_id: uuid.UUID | None, policy):
    """``attrs`` without cost-typed keys, unless the policy lets the caller see them."""
    if policy is None or not isinstance(attrs, dict):
        return attrs
    keys, allowed = policy
    if card_id is not None and card_id in allowed:
        return attrs
    cost_keys = keys.get(card_type or "", frozenset())
    return {k: v for k, v in attrs.items() if k not in cost_keys}


def _redacted_change_dict(c: ScenarioChange, policy) -> dict:
    out = _change_dict(c)
    if policy is None:
        return out
    payload = dict(out["payload"])
    if "attributes" in payload:
        payload["attributes"] = _strip_costs(
            payload["attributes"], c.card_type, c.target_card_id, policy
        )
    out["payload"] = payload
    if isinstance(out["baseline"], dict) and "attributes" in out["baseline"]:
        out["baseline"] = {
            **out["baseline"],
            "attributes": _strip_costs(
                out["baseline"]["attributes"], c.card_type, c.target_card_id, policy
            ),
        }
    return out


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
    all_changes = list((await db.execute(select(ScenarioChange))).scalars().all())
    for c in await _visible_changes(db, all_changes, await CardReadScope.load(db, user)):
        counts[c.scenario_id] = counts.get(c.scenario_id, 0) + 1
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
    changes = await _visible_changes(
        db, await _changes(db, scenario_id), await CardReadScope.load(db, user)
    )
    policy = await _cost_policy(db, user, changes)
    return {
        **_scenario_dict(s),
        "changes": [_redacted_change_dict(c, policy) for c in changes],
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
    payload = body.payload or {}
    baseline: dict | None = None
    target_card_id = body.target_card_id

    if body.op in ("modify", "retire"):
        if not body.target_card_id:
            raise HTTPException(status_code=400, detail="target_card_id required")
        await require_card_readable(db, user, body.target_card_id, mode="module")
        res = await db.execute(select(Card).where(Card.id == body.target_card_id))
        target = res.scalar_one_or_none()
        if target is None:
            raise HTTPException(status_code=404, detail="Target card not found")
        card_type = target.type
        name = name or target.name
        if body.op == "modify":
            baseline = _capture_modify_baseline(target, payload)
    elif body.op == "add":
        if not card_type or not name:
            raise HTTPException(status_code=400, detail="card_type and name required for add")
    elif body.op in RELATION_CHANGE_OPS:
        target_card_id = None  # relation ops don't target a single card
        if body.op == "add_relation":
            rel_type = payload.get("relation_type")
            src = payload.get("source_id")
            tgt = payload.get("target_id")
            if not (rel_type and src and tgt):
                raise HTTPException(
                    status_code=400,
                    detail="add_relation requires relation_type, source_id, target_id",
                )
            rt = (
                await db.execute(select(RelationType).where(RelationType.key == rel_type))
            ).scalar_one_or_none()
            if rt is None:
                raise HTTPException(status_code=404, detail="Relation type not found")
            cards = (await db.execute(select(Card).where(Card.id.in_([src, tgt])))).scalars().all()
            read_scope = await CardReadScope.load(db, user)
            card_by_id = {
                str(c.id): c for c in cards if read_scope.readable(c.id, c.type, mode="module")
            }
            if str(src) not in card_by_id or str(tgt) not in card_by_id:
                raise HTTPException(status_code=404, detail="Source or target card not found")
            name = name or f"{card_by_id[str(src)].name} → {card_by_id[str(tgt)].name}"
        else:  # remove_relation
            rel_id = payload.get("relation_id")
            if not rel_id:
                raise HTTPException(status_code=400, detail="remove_relation requires relation_id")
            rel = (
                await db.execute(select(Relation).where(Relation.id == rel_id))
            ).scalar_one_or_none()
            if rel is None or await (await CardReadScope.load(db, user)).hidden_card_ids(
                db, {rel.source_id, rel.target_id}, mode="module"
            ):
                raise HTTPException(status_code=404, detail="Relation not found")
            # Snapshot the relation so the merge can detect if it changed since.
            payload = {
                "relation_id": str(rel.id),
                "relation_type": rel.type,
                "source_id": str(rel.source_id),
                "target_id": str(rel.target_id),
            }
            baseline = {"existed": True}

    change = ScenarioChange(
        scenario_id=scenario_id,
        op=body.op,
        card_type=card_type,
        target_card_id=target_card_id,
        name=name,
        payload=payload,
        baseline=baseline,
    )
    db.add(change)
    await db.commit()
    await db.refresh(change)
    return _redacted_change_dict(change, await _cost_policy(db, user, [change]))


@router.delete("/changes/{change_id}", status_code=204)
async def delete_change(
    change_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "scenarios.manage")
    res = await db.execute(select(ScenarioChange).where(ScenarioChange.id == change_id))
    c = res.scalar_one_or_none()
    if c is None or not await _visible_changes(db, [c], await CardReadScope.load(db, user)):
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
    read_scope = await CardReadScope.load(db, user)
    changes = await _visible_changes(db, await _changes(db, scenario_id), read_scope)
    policy = await _cost_policy(db, user, changes)

    # Resolve target cards for before-state.
    target_ids = {c.target_card_id for c in changes if c.target_card_id}
    cards: dict[uuid.UUID, Card] = {}
    if target_ids:
        res = await db.execute(select(Card).where(Card.id.in_(target_ids)))
        cards = {c.id: c for c in res.scalars().all()}

    rows: list[dict] = []
    affected_total = 0
    drift_total = 0
    counts = {op: 0 for op in ("add", "modify", "retire", "add_relation", "remove_relation")}
    for c in changes:
        counts[c.op] = counts.get(c.op, 0) + 1
        before = None
        impact = None
        drift: list[str] = []
        if c.target_card_id and c.target_card_id in cards:
            tc = cards[c.target_card_id]
            before = {
                "name": tc.name,
                "type": tc.type,
                "attributes": _strip_costs(tc.attributes or {}, tc.type, tc.id, policy),
            }
            if c.op == "modify":
                drift = _field_drift(c, tc)
                if drift:
                    drift_total += 1
            if c.op in ("modify", "retire"):
                try:
                    imp = await gather_impact(
                        db,
                        c.target_card_id,
                        depth=1,
                        change_type=c.op,
                        read_scope=read_scope,
                    )
                    impact = imp["summary"]["total_affected"]
                    affected_total += impact
                except ValueError:
                    impact = None
        rows.append(
            {
                **_redacted_change_dict(c, policy),
                "before": before,
                "missing_target": bool(
                    c.op in ("modify", "retire")
                    and c.target_card_id
                    and c.target_card_id not in cards
                ),
                "drift": drift,
                "impact_affected": impact,
            }
        )

    return {
        "summary": {
            "changes": len(changes),
            "added": counts["add"],
            "modified": counts["modify"],
            "retired": counts["retire"],
            "relations_added": counts["add_relation"],
            "relations_removed": counts["remove_relation"],
            "impact_affected": affected_total,
            "drift_conflicts": drift_total,
        },
        "changes": rows,
    }


# --------------------------------------------------------------------------- #
# Merge                                                                       #
# --------------------------------------------------------------------------- #
async def _merge_authorization(
    db: AsyncSession, user: User, c: ScenarioChange, hidden: set[uuid.UUID]
) -> str:
    """``"ok"``, ``"withheld"`` or ``"forbidden"`` for one change at merge time.

    A merge writes to the live repository, so each change needs the authority
    the equivalent direct write would: ``inventory.create`` on the card type,
    ``inventory.edit`` / ``inventory.archive`` on the target card (or the
    matching stakeholder grant), ``relations.manage`` for relation changes.
    A change naming a card hidden from the merger is withheld outright: it is
    never applied and never reported to them, so a scenario cannot be used to
    modify — or learn about — a card its merger may not read.
    """
    refs = _referenced_card_ids(c)
    if c.op == "remove_relation":
        rel_id = (c.payload or {}).get("relation_id")
        if rel_id:
            row = (
                await db.execute(
                    select(Relation.source_id, Relation.target_id).where(
                        Relation.id == uuid.UUID(str(rel_id))
                    )
                )
            ).first()
            if row is not None:
                refs |= {row[0], row[1]}
    if refs & hidden:
        return "withheld"
    if c.op == "add":
        allowed = await PermissionService.check_permission(
            db, user, "inventory.create", card_type_key=c.card_type
        )
    elif c.op == "modify":
        allowed = await PermissionService.check_permission(
            db, user, "inventory.edit", c.target_card_id, "card.edit"
        )
    elif c.op == "retire":
        allowed = await PermissionService.check_permission(
            db, user, "inventory.archive", c.target_card_id, "card.archive"
        )
    else:  # add_relation / remove_relation, as the relation routes require
        allowed = await PermissionService.check_permission(db, user, "relations.manage")
    return "ok" if allowed else "forbidden"


@router.post("/{scenario_id}/merge")
async def merge_scenario(
    scenario_id: uuid.UUID,
    dry_run: bool = Query(False),
    force: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Apply the scenario's changes to the live repository.

    add → create card, modify → patch fields, retire → archive,
    add_relation → create relation, remove_relation → delete relation.

    Conflict detection: (a) **existence** — a modify/retire whose target card no
    longer exists, an add_relation whose relation already exists, or a
    remove_relation whose relation is gone; (b) **baseline drift** — a modify
    whose target field has moved on the live baseline since the change was
    captured. Conflicts are reported and skipped. ``force=true`` overrides drift
    (existence conflicts are never force-applied). ``dry_run=true`` reports the
    outcome without writing.
    """
    await PermissionService.require_permission(db, user, "scenarios.merge")
    s = await _get_scenario(db, scenario_id)
    if s.status == "merged":
        raise HTTPException(status_code=400, detail="Scenario already merged")

    changes = await _changes(db, scenario_id)
    read_scope = await CardReadScope.load(db, user)
    refs_all: set[uuid.UUID] = set()
    for c in changes:
        refs_all |= _referenced_card_ids(c)
    hidden = await read_scope.hidden_card_ids(db, refs_all, mode="module")
    applied = 0
    conflicts = 0
    results: list[dict] = []
    now = datetime.now(timezone.utc)

    # A change left unapplied for want of authority keeps the scenario open, so
    # someone with that authority can merge the rest later; a re-merge never
    # re-applies what an earlier partial merge already applied.
    complete = True
    for c in changes:
        if c.merge_status == "applied":
            continue
        outcome = "applied"
        authorization = await _merge_authorization(db, user, c, hidden)
        if authorization == "withheld":
            # Not applied, not reported, not counted (D-30): the merger cannot
            # see the card, so the scenario cannot change it on their behalf.
            complete = False
            if not dry_run:
                c.merge_status = "withheld"
            continue
        if authorization == "forbidden":
            outcome = "forbidden"
            complete = False
        elif c.op == "add":
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
        elif c.op == "add_relation":
            payload = c.payload or {}
            src = uuid.UUID(payload["source_id"])
            tgt = uuid.UUID(payload["target_id"])
            existing = await _relation_exists(db, payload["relation_type"], src, tgt)
            if existing is not None:
                outcome = "conflict"
                conflicts += 1
            else:
                if not dry_run:
                    db.add(
                        Relation(
                            type=payload["relation_type"],
                            source_id=src,
                            target_id=tgt,
                            attributes=payload.get("attributes") or {},
                        )
                    )
                    await db.flush()
                applied += 1
        elif c.op == "remove_relation":
            payload = c.payload or {}
            rel = (
                await db.execute(
                    select(Relation).where(Relation.id == uuid.UUID(payload["relation_id"]))
                )
            ).scalar_one_or_none()
            if rel is None:
                outcome = "conflict"
                conflicts += 1
            else:
                if not dry_run:
                    await db.delete(rel)
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
                drift = _field_drift(c, target)
                if drift and not force:
                    outcome = "drift"
                    conflicts += 1
                else:
                    if not dry_run:
                        payload = c.payload or {}
                        if "name" in payload:
                            target.name = payload["name"]
                        if "description" in payload:
                            target.description = payload["description"]
                        if "attributes" in payload and isinstance(payload["attributes"], dict):
                            target.attributes = {
                                **(target.attributes or {}),
                                **payload["attributes"],
                            }
                        target.updated_by = user.id
                    applied += 1
        if not dry_run:
            c.merge_status = outcome
        results.append({"id": str(c.id), "op": c.op, "name": c.name, "outcome": outcome})

    if not dry_run:
        if complete:
            s.status = "merged"
            s.merged_by = user.id
            s.merged_at = now
        # Withheld changes are not in these totals: the event reaches every
        # reader's recent-activity feed, so a count of them would disclose how
        # many hidden changes the scenario carried. A partial merge leaves the
        # scenario open and says so only by its event type.
        await event_bus.publish(
            "scenario.merged" if complete else "scenario.merge_partial",
            {
                "id": str(s.id),
                "applied": applied,
                "conflicts": conflicts,
                "forbidden": sum(1 for r in results if r["outcome"] == "forbidden"),
            },
            db=db,
            user_id=user.id,
        )
        await db.commit()

    # Totals cover the changes the merger was shown; withheld ones are absent.
    # ``complete`` is False when something stays unapplied for want of
    # authority — it says that much, never which change or how many.
    return {
        "dry_run": dry_run,
        "complete": complete,
        "applied": applied,
        "conflicts": conflicts,
        "forbidden": sum(1 for r in results if r["outcome"] == "forbidden"),
        "results": results,
    }
