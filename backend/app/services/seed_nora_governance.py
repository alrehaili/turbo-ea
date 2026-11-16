"""NORA demo governance cycle (NORAreadiness.md D5).

The NORA landscape seeders create every card as Draft, so the approval
coverage on the NORA program page read 0% and the governance chain was never
seen working. This seeder runs one completed approval cycle over the landscape
the other NORA seeders created:

* **Approved** — the strategy cards and the current core business, application,
  data and technology cards go through the configured approval chain (one
  step per chain role, each approved by a demo reviewer holding that role),
  with the same ``card.approval_status.*`` events the UI records.
* **In review / rejected** — a few cards stay mid-chain (first step approved,
  the rest pending) and one is rejected with a comment, so every state shows.
* **Governance mode** — switched on (unless an administrator already chose),
  so card pages show the chain and its steps.
* **Program tracker** — the first Phase 2 deliverable is approved, with its
  approver, date and evidence; the next one is in review.

KPI targets, verified values, initiative status reports, signed ADRs and
decided ARB reviews come from ``seed_demo_executive``, which runs before this.

Runs once per install (``seed_markers`` key ``nora_governance``).

[FORK]
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_settings import AppSettings
from app.models.card import Card
from app.models.nora_program import EaProgramDeliverable
from app.models.role import Role
from app.models.user import User
from app.services import governance_service as gov
from app.services.event_bus import event_bus
from app.services.seed_markers import demo_seed_completed, mark_demo_seed_completed

SEEDER_KEY = "nora_governance"

#: Card types whose current Draft cards are approved, in this order.
APPROVED_TYPES: list[str] = [
    "Pillar",
    "Objective",
    "BusinessCapability",
    "ProcessesGroup",
    "BusinessProcess",
    "GovService",
    "OrganizationalUnit",
    "Policy",
    "Application",
    "Interface",
    "DataObject",
    "Datacenter",
    "Server",
]

#: (type, how many of its cards, by name from the end) left in review.
IN_REVIEW: list[tuple[str, int]] = [("Application", 2), ("GovService", 1)]
#: (type, comment) — the last Draft card of the type is rejected.
REJECTED: list[tuple[str, str]] = [
    ("Policy", "Clauses must cite the NDMO classification before approval."),
]

#: Demo reviewers, one per role of the default chain.
REVIEWERS: dict[str, tuple[str, str]] = {
    "chief_architect": ("chief.architect@turboea.demo", "Demo Chief Architect"),
    "ea_governance_committee": ("ea.committee@turboea.demo", "Demo EA Governance Committee"),
}

#: Program tracker: (deliverable key, status, evidence) for Phase 2.
PROGRAM_STEPS: list[tuple[str, str, list[dict]]] = [
    (
        "p2_business_scope",
        "approved",
        [{"kind": "link", "ref": "/view-library", "label": "Business architecture scope"}],
    ),
    ("p2_business_data_collection", "inReview", []),
]


async def _reviewer(db: AsyncSession, role_key: str) -> User:
    email, name = REVIEWERS.get(role_key, (f"{role_key}@turboea.demo", f"Demo {role_key}"))
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        role_exists = (
            await db.execute(select(Role.key).where(Role.key == role_key))
        ).scalar_one_or_none()
        user = User(
            email=email,
            display_name=name,
            password_hash=None,
            role=role_key if role_exists else "member",
        )
        db.add(user)
        await db.flush()
    return user


async def _drafts(db: AsyncSession, type_key: str) -> list[Card]:
    rows = await db.execute(
        select(Card)
        .where(
            Card.type == type_key,
            Card.status == "ACTIVE",
            Card.approval_status == "DRAFT",
            Card.architecture_state == "current",
        )
        .order_by(Card.name)
    )
    return list(rows.scalars().all())


def plan_states(cards_by_type: dict[str, list[Card]]) -> dict[str, list[Card]]:
    """Split the Draft cards into approved / in review / rejected.

    Pure: the in-review and rejected cards are taken from the end of their
    type's name-sorted list, everything else of an approved type is approved.
    """
    in_review: list[Card] = []
    rejected: list[Card] = []
    held: set = set()
    for type_key, n in IN_REVIEW:
        picked = cards_by_type.get(type_key, [])[-n:] if n > 0 else []
        in_review.extend(picked)
        held.update(c.id for c in picked)
    for type_key, _comment in REJECTED:
        rest = [c for c in cards_by_type.get(type_key, []) if c.id not in held]
        if rest:
            rejected.append(rest[-1])
            held.add(rest[-1].id)
    approved = [
        c
        for type_key in APPROVED_TYPES
        for c in cards_by_type.get(type_key, [])
        if c.id not in held
    ]
    return {"approved": approved, "in_review": in_review, "rejected": rejected}


async def seed_nora_governance(db: AsyncSession) -> dict:
    if await demo_seed_completed(db, SEEDER_KEY):
        return {"skipped": True, "reason": "already seeded"}
    has_landscape = (
        await db.execute(select(Card.id).where(Card.type == "GovService").limit(1))
    ).scalar_one_or_none()
    if has_landscape is None:
        return {"skipped": True, "reason": "no NORA landscape"}

    # Governance mode on, so the chain and its steps show on the card pages.
    settings_row = (
        await db.execute(select(AppSettings).where(AppSettings.id == "default"))
    ).scalar_one_or_none()
    if settings_row is not None:
        general = dict(settings_row.general_settings or {})
        if "governanceMode" not in general:
            general["governanceMode"] = True
            settings_row.general_settings = general

    submitter = (
        (await db.execute(select(User).where(User.role == "admin").order_by(User.created_at)))
        .scalars()
        .first()
    )
    cards_by_type = {t: await _drafts(db, t) for t in APPROVED_TYPES}
    plan = plan_states(cards_by_type)
    reviewers: dict[str, User] = {}

    async def run_chain(card: Card, *, approve_steps: int | None, reject: str | None) -> str:
        """Submit ``card`` and act on its steps; return the resulting status."""
        chain = await gov.get_governance_chain(db, card.type)
        for role_key in chain:
            if role_key not in reviewers:
                reviewers[role_key] = await _reviewer(db, role_key)
        actor = submitter or reviewers[chain[0]]
        steps = await gov.create_steps(db, card.id, chain, submitted_by=actor.id)
        await event_bus.publish(
            "card.approval_status.submit",
            {"id": str(card.id), "approval_status": "IN_REVIEW"},
            db=db,
            card_id=card.id,
            user_id=actor.id,
        )
        status = "IN_REVIEW"
        to_approve = len(steps) if approve_steps is None else min(approve_steps, len(steps))
        for step in steps[:to_approve]:
            gov.mark_step(step, "approved", reviewers[step.required_role_key], None)
        if reject is not None and to_approve < len(steps):
            step = steps[to_approve]
            gov.mark_step(step, "rejected", reviewers[step.required_role_key], reject)
            status = "REJECTED"
            last_actor = reviewers[step.required_role_key]
            action = "reject"
        elif to_approve == len(steps):
            status = "APPROVED"
            last_actor = reviewers[steps[-1].required_role_key]
            action = "approve"
        else:
            last_actor = None
            action = None
        card.approval_status = status
        if action is not None:
            await event_bus.publish(
                f"card.approval_status.{action}",
                {"id": str(card.id), "approval_status": status},
                db=db,
                card_id=card.id,
                user_id=last_actor.id,
            )
        return status

    counts = {"approved": 0, "in_review": 0, "rejected": 0, "deliverables": 0}
    for card in plan["approved"]:
        await run_chain(card, approve_steps=None, reject=None)
        counts["approved"] += 1
    for card in plan["in_review"]:
        await run_chain(card, approve_steps=1, reject=None)
        counts["in_review"] += 1
    comments = dict(REJECTED)
    for card in plan["rejected"]:
        await run_chain(card, approve_steps=0, reject=comments[card.type])
        counts["rejected"] += 1

    # ── Program tracker: Phase 2 starts delivering ─────────────────────────
    approver = reviewers.get("ea_governance_committee") or await _reviewer(
        db, "ea_governance_committee"
    )
    for key, status, evidence in PROGRAM_STEPS:
        row = (
            await db.execute(select(EaProgramDeliverable).where(EaProgramDeliverable.key == key))
        ).scalar_one_or_none()
        if row is None or row.status in ("approved", "descoped"):
            continue
        row.status = status
        if evidence:
            row.evidence = [*(row.evidence or []), *evidence]
        if status == "approved":
            row.approved_by = approver.id
            row.approved_at = datetime.now(timezone.utc)
        counts["deliverables"] += 1

    await mark_demo_seed_completed(db, SEEDER_KEY)
    await db.commit()
    return counts
