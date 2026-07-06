"""Plateaus (time-slices) + segment scopes ([FORK] — noraPlan.md WP5.4).

Two small governance overlays on the single canonical landscape (never a copy):

* ``nora_plateaus`` — named target dates (e.g. "2027 Interim", "2030 Target").
  A plateau is an *as-of date*: the frontend reclassifies each card's lifecycle
  phase (plan → phaseIn → active → phaseOut → endOfLife) as of that date to show
  a time-slice of the landscape without duplicating any card.
* ``nora_segments`` — named cross-entity filter scopes. A segment is rooted on a
  card (typically a BusinessCapability); its scope is that root plus, optionally,
  its hierarchy descendants and the cards related to them (optionally narrowed to
  a set of card types). Segments are applied as a lens across inventory/reports —
  the blueprint's ``ArchitectureScope`` slimmed to a filter-set entity, per the
  plan's YAGNI guidance.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class NoraPlateau(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "nora_plateaus"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    built_in: Mapped[bool] = mapped_column(Boolean, default=False)


class NoraSegment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "nora_segments"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    root_card_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="SET NULL"), nullable=True
    )
    include_descendants: Mapped[bool] = mapped_column(Boolean, default=True)
    include_related: Mapped[bool] = mapped_column(Boolean, default=True)
    # When non-empty, related cards are narrowed to these card-type keys.
    related_type_keys: Mapped[list] = mapped_column(JSONB, default=list)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
