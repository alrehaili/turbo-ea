"""Business calendar: working week and official holidays per fiscal year (D-28, D-38).

Owned by the EA Governance Office and maintained by holders of
``admin.business_calendar``. One row per fiscal year carries that year's working
week (ISO weekdays, Sunday–Thursday by default) and its official Saudi holidays.
A year counts for working-day figures only once it is **confirmed**; a
reporting period touching a year that is missing or unconfirmed has no
working-day figure (Not Available), never a guessed one.

[FORK]
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin

#: ISO weekdays (Monday = 1 … Sunday = 7) of the default Saudi working week.
DEFAULT_WORKING_WEEKDAYS = [7, 1, 2, 3, 4]


class BusinessCalendarYear(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "business_calendar_years"

    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    working_weekdays: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=lambda: list(DEFAULT_WORKING_WEEKDAYS)
    )
    #: ``[{"date": "YYYY-MM-DD", "name": "..."}]``, sorted by date.
    holidays: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    confirmed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
