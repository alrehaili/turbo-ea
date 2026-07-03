"""Multi-step governance approval (NORA stage gates).

[FORK FEATURE] — noraPlan.md WP2.2. See ``app.models.approval_step`` for the
data model and the endpoint in ``app.api.v1.cards`` for the HTTP surface.

Configuration lives in ``app_settings.general_settings``:

* ``governanceMode`` (bool, default False) — when off, the classic one-click
  approve/reject/reset behaviour is unchanged.
* ``governanceChain`` (list[str], default ["chief_architect",
  "ea_governance_committee"]) — ordered role keys; one ApprovalStep per entry.
* ``governanceSodEnabled`` (bool, default True) — segregation of duties: the
  submitter of a review round cannot approve any of its steps.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_settings import AppSettings
from app.models.approval_step import ApprovalStep
from app.models.user import User

DEFAULT_GOVERNANCE_CHAIN = ["chief_architect", "ea_governance_committee"]


async def get_governance_config(db: AsyncSession) -> dict:
    result = await db.execute(select(AppSettings).where(AppSettings.id == "default"))
    row = result.scalar_one_or_none()
    general = (row.general_settings if row else None) or {}
    chain = general.get("governanceChain") or DEFAULT_GOVERNANCE_CHAIN
    # Defensive: a chain must be a non-empty list of non-empty strings.
    chain = [str(r) for r in chain if r] or DEFAULT_GOVERNANCE_CHAIN
    return {
        "enabled": bool(general.get("governanceMode", False)),
        "chain": chain,
        "sod_enabled": bool(general.get("governanceSodEnabled", True)),
    }


async def get_steps(db: AsyncSession, card_id: uuid.UUID) -> list[ApprovalStep]:
    result = await db.execute(
        select(ApprovalStep).where(ApprovalStep.card_id == card_id).order_by(ApprovalStep.step_no)
    )
    return list(result.scalars().all())


async def clear_steps(db: AsyncSession, card_id: uuid.UUID) -> None:
    await db.execute(delete(ApprovalStep).where(ApprovalStep.card_id == card_id))


async def create_steps(
    db: AsyncSession, card_id: uuid.UUID, chain: list[str], submitted_by: uuid.UUID
) -> list[ApprovalStep]:
    """Start a fresh review round: drop any previous steps, create one pending
    step per chain role."""
    await clear_steps(db, card_id)
    steps = [
        ApprovalStep(
            card_id=card_id,
            step_no=i,
            required_role_key=role_key,
            status="pending",
            submitted_by=submitted_by,
        )
        for i, role_key in enumerate(chain)
    ]
    db.add_all(steps)
    await db.flush()
    return steps


def current_pending_step(steps: list[ApprovalStep]) -> ApprovalStep | None:
    for step in steps:
        if step.status == "pending":
            return step
    return None


def step_dict(step: ApprovalStep, actor_name: str | None = None) -> dict:
    return {
        "id": str(step.id),
        "step_no": step.step_no,
        "required_role_key": step.required_role_key,
        "status": step.status,
        "actor_user_id": str(step.actor_user_id) if step.actor_user_id else None,
        "actor_display_name": actor_name,
        "comment": step.comment,
        "acted_at": step.acted_at.isoformat() if step.acted_at else None,
    }


def mark_step(step: ApprovalStep, status: str, actor: User, comment: str | None) -> None:
    step.status = status
    step.actor_user_id = actor.id
    step.comment = comment
    step.acted_at = datetime.now(timezone.utc)


async def notify_role_members(
    db: AsyncSession,
    role_key: str,
    *,
    card_id: uuid.UUID,
    card_name: str,
    actor_display_name: str,
) -> None:
    """In-app notification to every active user holding the chain role."""
    from app.services.notification_service import create_notification

    result = await db.execute(select(User).where(User.role == role_key, User.is_active.is_(True)))
    for member in result.scalars().all():
        await create_notification(
            db,
            user_id=member.id,
            notif_type="approval_step_pending",
            title="Review requested",
            message=f'{actor_display_name} requests your review of "{card_name}"',
            link=f"/cards/{card_id}",
            data={"card_id": str(card_id)},
        )
