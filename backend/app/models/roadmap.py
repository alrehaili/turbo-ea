from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Roadmap(Base, UUIDMixin, TimestampMixin):
    """A saved transformation roadmap view — a named, scoped lifecycle timeline.

    ``config`` holds the view configuration (the swimlane grouping dimension, the
    card type that forms the bars, the time window and any filters) so the view is
    reproducible. The roadmap itself stores no card data: the timeline is computed
    on demand from each card's ``lifecycle`` JSONB plus the relation graph.

    [FORK FEATURE]
    """

    __tablename__ = "roadmaps"

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )


class RoadmapMilestone(Base, UUIDMixin, TimestampMixin):
    """A transformation milestone plotted on a roadmap (e.g. "ERP go-live").

    Optionally tied to an Initiative card via ``initiative_id`` so the marker can
    link through to the initiative driving the change.

    [FORK FEATURE]
    """

    __tablename__ = "roadmap_milestones"

    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roadmaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(300), nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    initiative_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id", ondelete="SET NULL")
    )
    color: Mapped[str | None] = mapped_column(String(20))
