"""Scenario Planning & Transition Architecture (Wave 3 #8/#9).

The architecture chosen in the plan spike is a **copy-on-write delta/overlay**:
a scenario stores only the *changes* (add / modify / retire) it makes against the
live baseline, not a full snapshot. This reuses the existing "proposed card"
mental model, makes As-Is vs To-Be diffing trivial, and keeps storage small.

* :class:`Scenario` — a named branch with an approval lifecycle.
* :class:`ScenarioChange` — one add/modify/retire operation against a card.

On **merge**, the changes are applied to the real repository (add → create card,
modify → patch fields, retire → archive). Merge performs existence-based conflict
detection: a modify/retire whose target card has since been deleted is reported
as a conflict and skipped rather than silently failing.

[FORK FEATURE]
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

SCENARIO_STATUSES = ("draft", "review", "approved", "merged", "discarded")
CHANGE_OPS = ("add", "modify", "retire")


class Scenario(UUIDMixin, TimestampMixin, Base):
    """A transition-architecture scenario branch (copy-on-write overlay)."""

    __tablename__ = "scenarios"

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="draft")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    merged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    merged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    changes = relationship(
        "ScenarioChange",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    __table_args__ = (Index("ix_scenarios_status", "status"),)


class ScenarioChange(UUIDMixin, TimestampMixin, Base):
    """A single add/modify/retire operation inside a scenario."""

    __tablename__ = "scenario_changes"

    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    op: Mapped[str] = mapped_column(String(8), nullable=False)
    # For add: the card type of the proposed card. For modify/retire: mirrors the
    # target card's type (denormalised for display).
    card_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # For modify/retire: the existing card being changed. NULL for add.
    target_card_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True
    )
    # Proposed name (add) or display name snapshot (modify/retire).
    name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # The delta: full field set for add, changed fields for modify, {} for retire.
    payload: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    # Outcome stamped on merge: applied / conflict / skipped.
    merge_status: Mapped[str | None] = mapped_column(String(16), nullable=True)

    __table_args__ = (
        Index("ix_scenario_changes_scenario_id", "scenario_id"),
        Index("ix_scenario_changes_target_card_id", "target_card_id"),
    )
