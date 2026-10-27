"""Explicit risk ↔ EA governance-record relationships (D-42; Batch 3.5).

A risk is *architecture-related* only through a row here: a link to an
Architecture Decision Record, an ARB review or a technology-standard exception
that someone authorized recorded on purpose. Nothing is inferred from a risk's
category, source or wording (D-36).

``record_id`` names a row of one of three tables (``instrument`` says which),
so it carries no foreign key — the same shape as ``governance_transitions``.
The routes that delete a governance record remove its links and record that.

[FORK]
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin

LINK_ADR = "adr"
LINK_ARB = "arb"
LINK_EXCEPTION = "exception"
LINK_INSTRUMENTS = (LINK_ADR, LINK_ARB, LINK_EXCEPTION)


class RiskGovernanceLink(UUIDMixin, Base):
    __tablename__ = "risk_governance_links"

    risk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("risks.id", ondelete="CASCADE"), nullable=False
    )
    instrument: Mapped[str] = mapped_column(String(16), nullable=False)
    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "instrument IN ('adr', 'arb', 'exception')", name="ck_risk_governance_links_instrument"
        ),
        UniqueConstraint(
            "risk_id", "instrument", "record_id", name="uq_risk_governance_links_link"
        ),
        Index("ix_risk_governance_links_record", "instrument", "record_id"),
        Index("ix_risk_governance_links_risk", "risk_id"),
    )
