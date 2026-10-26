"""Business calendar administration (D-28, D-38; Executive dashboard Batch 3.3).

The EA Governance Office's working week and official holidays per fiscal year,
and their confirmation. Every route needs ``admin.business_calendar`` (held by
no default role; administrators through the wildcard), and every write is an
admin audit record. The working-day figures read the calendar server-side.

[FORK]
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.business_calendar import BusinessCalendarYear
from app.models.user import User
from app.services import audit_log
from app.services import business_calendar as bc
from app.services.fiscal_year import get_fiscal_year_start
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/business-calendar", tags=["business-calendar"])

PERMISSION = "admin.business_calendar"


class Holiday(BaseModel):
    date: str = Field(max_length=10)
    name: str = Field(max_length=200)


class CalendarYearUpdate(BaseModel):
    working_weekdays: list[int] | None = Field(default=None, max_length=7)
    holidays: list[Holiday] = Field(default_factory=list, max_length=bc.MAX_HOLIDAYS)


def _error(err: bc.CalendarError) -> HTTPException:
    return HTTPException(status_code=422, detail={"code": err.code, "message": str(err)})


async def _year(db: AsyncSession, fy: int) -> BusinessCalendarYear | None:
    return await db.scalar(
        select(BusinessCalendarYear).where(BusinessCalendarYear.fiscal_year == fy)
    )


async def _audit(db, user, action: str, fy: int, *, changes=None, context=None) -> None:
    label = f"FY{fy}"
    await audit_log.record(
        db,
        action=action,
        category="admin",
        actor=user,
        target=("business_calendar", label, label),
        changes=changes or None,
        context={"fiscal_year": label, **(context or {})},
    )


@router.get("")
async def list_years(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    """Every maintained fiscal year, oldest first, with its confirmation."""
    await PermissionService.require_permission(db, user, PERMISSION)
    start_month = await get_fiscal_year_start(db)
    rows = (
        await db.execute(select(BusinessCalendarYear).order_by(BusinessCalendarYear.fiscal_year))
    ).scalars()
    return {
        "fiscal_year_start": start_month,
        "default_working_weekdays": bc.DEFAULT_WORKING_WEEKDAYS,
        "years": [bc.serialize(r, start_month) for r in rows],
    }


@router.put("/{fiscal_year}")
async def save_year(
    fiscal_year: int,
    body: CalendarYearUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create or replace a fiscal year's working week and holidays.

    Changing a confirmed year withdraws its confirmation (I-38)."""
    await PermissionService.require_permission(db, user, PERMISSION)
    start_month = await get_fiscal_year_start(db)
    try:
        bc.validate_fiscal_year(fiscal_year)
        week = bc.validate_working_weekdays(body.working_weekdays)
        holidays = bc.validate_holidays(
            fiscal_year, start_month, [h.model_dump() for h in body.holidays]
        )
    except bc.CalendarError as err:
        raise _error(err) from err
    row = await _year(db, fiscal_year)
    created = row is None
    if created:
        row = BusinessCalendarYear(fiscal_year=fiscal_year, working_weekdays=[], holidays=[])
        db.add(row)
    changes = bc.apply_edit(row, week, holidays)
    if created or changes:
        await _audit(
            db,
            user,
            "admin.business_calendar.created" if created else "admin.business_calendar.updated",
            fiscal_year,
            changes=None if created else changes,
            context={"working_days": bc.weekday_labels(week), "holiday_count": len(holidays)}
            if created
            else None,
        )
    await db.commit()
    await db.refresh(row)
    return bc.serialize(row, start_month)


async def _set_confirmed(db, user, fiscal_year: int, confirmed: bool) -> dict:
    await PermissionService.require_permission(db, user, PERMISSION)
    start_month = await get_fiscal_year_start(db)
    row = await _year(db, fiscal_year)
    if row is None:
        raise HTTPException(status_code=404, detail="No calendar for that fiscal year")
    if row.confirmed != confirmed:
        row.confirmed = confirmed
        row.confirmed_by = user.id if confirmed else None
        row.confirmed_at = datetime.now(timezone.utc) if confirmed else None
        await _audit(
            db,
            user,
            "admin.business_calendar.confirmed"
            if confirmed
            else "admin.business_calendar.unconfirmed",
            fiscal_year,
            context={
                "working_days": bc.weekday_labels(row.working_weekdays or []),
                "holiday_count": len(row.holidays or []),
            },
        )
    await db.commit()
    await db.refresh(row)
    return bc.serialize(row, start_month)


@router.post("/{fiscal_year}/confirm")
async def confirm_year(
    fiscal_year: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """Confirm a fiscal year's calendar so its working-day figures count (D-38)."""
    return await _set_confirmed(db, user, fiscal_year, True)


@router.post("/{fiscal_year}/unconfirm")
async def unconfirm_year(
    fiscal_year: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    """Withdraw a confirmation; the year's working-day figures become Not Available."""
    return await _set_confirmed(db, user, fiscal_year, False)
