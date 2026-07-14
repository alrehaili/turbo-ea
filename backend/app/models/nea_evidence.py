"""NEA alignment / evidence-pack export ([FORK] — noraPlan.md WP5.3).

A generated, immutable snapshot of an agency's NORA posture — BRM coverage,
shared-service candidates, standards-compliance summary, EA maturity score,
program status and approval history — rendered to a multi-sheet ``.xlsx`` for
NEA federation and audit. Like ``workspace_transfers``, the binary lives on
disk (``data/nea_evidence_packs/{id}.xlsx``) so Postgres stays lean; the row
tracks the generation lifecycle and headline summary. Packs are **immutable
once generated** — there is no update path, only generate / download / delete.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

NEA_PACK_STATUSES = ("generating", "ready", "failed")


class NeaEvidencePack(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "nea_evidence_packs"

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="generating", nullable=False)
    filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Headline numbers surfaced in the UI without opening the workbook.
    summary: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
