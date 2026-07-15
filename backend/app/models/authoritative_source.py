"""Authoritative source register — the laws, policies, controls, and standards
that EA principles and standards trace back to.

[FORK FEATURE] — Backs §8 of the Saudi Government EA catalog: Saudi (DGA, NCA,
SDAIA/NDMO, PDPL) and international (ISO, NIST, IETF, W3C, OMG, Open Group)
sources, each addressed by a stable code (``SA-01``, ``INT-13``) that
principles and standards reference via their ``source_ids`` arrays.
"""

from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class AuthoritativeSource(Base, UUIDMixin, TimestampMixin):
    """One entry in the authoritative-source register."""

    __tablename__ = "authoritative_sources"

    # Stable reference code, e.g. "SA-01" (Saudi) or "INT-13" (international).
    code: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    authority: Mapped[str | None] = mapped_column(String(128), nullable=True)
    classification: Mapped[str | None] = mapped_column(String(256), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
