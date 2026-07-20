"""Structured SWOT entries for Environment-Analysis governed documents.

[FORK FEATURE] — noraPlan.md WP3.3.

The NORA "Environment Analysis / SWOT" document (a SoAW ``doc_type``) authors
its four quadrants as rich text. To make a *weakness* or *threat* promotable
into the Improvement-Opportunity registry (mirroring the compliance-finding →
risk bridge), the quadrants also carry structured rows here: one
:class:`SwotEntry` per bullet, tagged with its quadrant, optionally linked to
the improvement opportunity it was promoted into.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

# strength / weakness = internal; opportunity / threat = external. Only
# weakness + threat are promotable to improvement opportunities.
SWOT_QUADRANTS = ("strength", "weakness", "opportunity", "threat")
PROMOTABLE_QUADRANTS = ("weakness", "threat")


class SwotEntry(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "swot_entries"

    soaw_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("statement_of_architecture_works.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quadrant: Mapped[str] = mapped_column(String(16), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    # Back-link once this entry has been promoted (idempotent promotion), so
    # the UI shows "Open opportunity" instead of "Promote".
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("improvement_opportunities.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
