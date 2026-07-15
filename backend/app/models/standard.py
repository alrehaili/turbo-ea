from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class Standard(Base, UUIDMixin, TimestampMixin):
    """An architecture standard — a concrete specification that implements one or
    more EA principles (e.g. "Approved RDBMS is PostgreSQL")."""

    __tablename__ = "standards"

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    rationale: Mapped[str | None] = mapped_column(Text)
    implications: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    catalogue_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    # Grouping domain, e.g. "Integration Architecture", "Cybersecurity".
    domain: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Proposed adoption status, e.g. "Mandatory", "Conditional mandatory".
    adoption: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Authoritative-source codes this standard traces back to (["SA-01", ...]).
    source_ids: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")


class StandardPrinciple(Base):
    """Many-to-many link between an architecture standard and the EA principles it
    implements."""

    __tablename__ = "standard_principles"

    standard_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("standards.id", ondelete="CASCADE"),
        primary_key=True,
    )
    principle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ea_principles.id", ondelete="CASCADE"),
        primary_key=True,
    )
