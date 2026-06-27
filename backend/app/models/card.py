from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Card(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "cards"

    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    subtype: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cards.id"), index=True
    )
    lifecycle: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    attributes: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    approval_status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    data_quality: Mapped[float] = mapped_column(Float, default=0.0)
    external_id: Mapped[str | None] = mapped_column(String(500))
    alias: Mapped[str | None] = mapped_column(String(500))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    # Repository-freshness metadata (Wave 2 #4). last_confirmed_at is stamped
    # when a steward confirms the card is still accurate; source_system records
    # the system of record the data came from; confidence is a coarse
    # low/medium/high data-confidence marker. last_confirmed_at is instance-local
    # operational state (like archived_at) and is intentionally NOT carried in the
    # workspace-transfer bundle; source_system + confidence ARE transferred.
    last_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    source_system: Mapped[str | None] = mapped_column(String(200))
    confidence: Mapped[str | None] = mapped_column(String(20))
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    parent = relationship("Card", remote_side="Card.id", lazy="noload")
    children = relationship(
        "Card",
        back_populates="parent",
        remote_side="Card.parent_id",
        lazy="noload",
        viewonly=True,
    )
    tags = relationship("Tag", secondary="card_tags", lazy="noload")
    stakeholders = relationship("Stakeholder", back_populates="card", lazy="noload")
