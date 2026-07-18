from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class ViewpointDefinition(Base, UUIDMixin, TimestampMixin):
    """NORA/DGA EA Viewpoint registry — governs all 67 viewpoints."""

    __tablename__ = "viewpoint_definitions"

    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(200), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(200), nullable=False)

    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    # Domains: strategic_alignment, business, beneficiary_experience, data,
    # applications, technology, security

    level: Mapped[str] = mapped_column(String(20), nullable=False)
    # Levels: conceptual, logical, physical

    type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Types: list, matrix, diagram

    description_en: Mapped[str | None] = mapped_column(String(500))
    description_ar: Mapped[str | None] = mapped_column(String(500))

    building_blocks: Mapped[list | None] = mapped_column(JSONB, default=[])
    # Array of card-type keys required for this viewpoint

    target_route: Mapped[str | None] = mapped_column(String(200))
    # In-app route: /inventory?type=X, /reports/matrix, /view-library/pending, etc.

    status: Mapped[str] = mapped_column(String(20), default="available")
    # Status: available (engine works, seeding needed), partial (config needed),
    # missing (new blocks/renderer), done (seeded)

    sort_order: Mapped[int] = mapped_column(default=0)
