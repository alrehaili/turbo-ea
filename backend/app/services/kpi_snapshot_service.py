"""Capture and read the daily dashboard series used to render dashboard trends.

The four series (total cards, average data quality, approved, broken) live in
the one KPI measurement history (``kpi_measurements``, decision D-19) as
``daily`` observations keyed ``dashboard.<series>``; migration 1164 moved the
``kpi_snapshots`` rows there unchanged. :class:`DailySnapshot` is the
one-day view the dashboard trend has always read.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.kpi_measurement import KIND_DAILY, STATUS_OBSERVED, KpiMeasurement
from app.services.card_read_scope import visible_type_clause

SERIES = ("total_cards", "avg_data_quality", "approved_count", "broken_count")
PREFIX = "dashboard."
VERSION = "dashboard@1"
INT_SERIES = frozenset({"total_cards", "approved_count", "broken_count"})


@dataclass(frozen=True)
class DailySnapshot:
    """One day of the four dashboard series."""

    snapshot_date: date
    total_cards: int = 0
    avg_data_quality: float = 0.0
    approved_count: int = 0
    broken_count: int = 0


async def store_daily(db: AsyncSession, snapshot_date: date, values: dict) -> None:
    """Upsert one day of the dashboard series (idempotent on the day)."""
    day = snapshot_date.isoformat()
    for series in SERIES:
        if series not in values:
            continue
        stmt = (
            pg_insert(KpiMeasurement)
            .values(
                kind=KIND_DAILY,
                metric_key=PREFIX + series,
                period_type="day",
                period_key=day,
                period_start=snapshot_date,
                period_end=snapshot_date,
                value=float(values[series]),
                calculation_version=VERSION,
                source="system",
                status=STATUS_OBSERVED,
            )
            .on_conflict_do_update(
                index_elements=["metric_key", "period_key"],
                index_where=text("kind = 'daily'"),
                set_={"value": float(values[series]), "recorded_at": func.now()},
            )
        )
        await db.execute(stmt)
    await db.flush()


async def _day(db: AsyncSession, snapshot_date: date) -> DailySnapshot | None:
    rows = await db.execute(
        select(KpiMeasurement.metric_key, KpiMeasurement.value).where(
            KpiMeasurement.kind == KIND_DAILY,
            KpiMeasurement.metric_key.in_([PREFIX + s for s in SERIES]),
            KpiMeasurement.period_start == snapshot_date,
        )
    )
    found = {key[len(PREFIX) :]: value for key, value in rows.all()}
    if not found:
        return None
    return DailySnapshot(
        snapshot_date=snapshot_date,
        **{s: (int(v) if s in INT_SERIES else float(v)) for s, v in found.items() if v is not None},
    )


async def compute_current_kpis(db: AsyncSession) -> dict:
    """Compute the four trend KPI values from the live cards table.

    Shared by the dashboard endpoint and the snapshot capture task so the two
    cannot drift. Hidden card types are left out, matching the dashboard totals
    the trend is compared against (decision D-01).
    """
    live = (Card.status == "ACTIVE", visible_type_clause(Card))
    total_result = await db.execute(select(func.count(Card.id)).where(*live))
    total_cards = total_result.scalar() or 0

    avg_result = await db.execute(select(func.avg(Card.data_quality)).where(*live))
    avg_data_quality = float(avg_result.scalar() or 0)

    approved_result = await db.execute(
        select(func.count(Card.id)).where(*live, Card.approval_status == "APPROVED")
    )
    approved_count = approved_result.scalar() or 0

    broken_result = await db.execute(
        select(func.count(Card.id)).where(*live, Card.approval_status == "BROKEN")
    )
    broken_count = broken_result.scalar() or 0

    return {
        "total_cards": int(total_cards),
        "avg_data_quality": round(avg_data_quality, 1),
        "approved_count": int(approved_count),
        "broken_count": int(broken_count),
    }


async def capture_snapshot(db: AsyncSession, snapshot_date: date | None = None) -> DailySnapshot:
    """Capture today's dashboard series as daily observations (idempotent).

    Re-running on the same day updates that day's observations in place. The
    caller owns the transaction — this flushes but does not commit, which keeps
    the nested-savepoint rollback pattern in tests behaving correctly.
    """
    target_date = snapshot_date or datetime.now(timezone.utc).date()
    kpis = await compute_current_kpis(db)
    await store_daily(db, target_date, kpis)
    return DailySnapshot(snapshot_date=target_date, **kpis)


async def has_any_snapshot(db: AsyncSession) -> bool:
    """Whether any day of the dashboard series has been captured yet."""
    found = await db.execute(
        select(KpiMeasurement.id)
        .where(KpiMeasurement.kind == KIND_DAILY, KpiMeasurement.metric_key.like(PREFIX + "%"))
        .limit(1)
    )
    return found.scalar_one_or_none() is not None


async def get_comparison_snapshot(
    db: AsyncSession,
    *,
    days_ago: int = 30,
    min_days: int = 0,
    max_days: int = 365,
) -> DailySnapshot | None:
    """Return the day closest to (today - days_ago) within [min_days, max_days].

    ``min_days=0`` means today's startup baseline is a valid comparison point
    on day one (delta measures "change since startup"); after the daily 02:00
    UTC loop starts rolling, prior days are preferred. Falls back to whatever
    day is closest to the target when no exact match exists.
    """
    today = datetime.now(timezone.utc).date()
    earliest = today - timedelta(days=max_days)
    latest = today - timedelta(days=min_days)
    target = today - timedelta(days=days_ago)

    result = await db.execute(
        select(KpiMeasurement.period_start)
        .where(
            KpiMeasurement.kind == KIND_DAILY,
            KpiMeasurement.metric_key.like(PREFIX + "%"),
            KpiMeasurement.period_start >= earliest,
            KpiMeasurement.period_start <= latest,
        )
        .distinct()
    )
    days = [d for (d,) in result.all()]
    if not days:
        return None
    return await _day(db, min(days, key=lambda d: abs((d - target).days)))


def compute_trend_block(
    *,
    current: dict,
    previous: DailySnapshot | None,
    preferred_days: int = 30,
) -> dict:
    """Build the ``trends`` block returned by /reports/dashboard.

    ``comparison_days`` reflects the actual age of the snapshot used, which may
    differ from ``preferred_days`` when the dataset is new (fallback to
    whatever snapshot is available).
    """

    def _delta_pct(curr: float, prev: float | None) -> float | None:
        if prev is None or prev == 0:
            return None
        return round(((curr - prev) / prev) * 100, 1)

    def _delta_abs(curr: float, prev: float | None) -> float | None:
        if prev is None:
            return None
        diff = curr - prev
        # Preserve int for count KPIs; round the float KPI (avg_data_quality).
        if isinstance(curr, int) and isinstance(prev, int):
            return int(diff)
        return round(diff, 1)

    if previous is not None:
        today = datetime.now(timezone.utc).date()
        comparison_days = max((today - previous.snapshot_date).days, 1)
    else:
        comparison_days = preferred_days

    fields = ("total_cards", "avg_data_quality", "approved_count", "broken_count")
    trends: dict = {
        "comparison_days": comparison_days,
        "snapshot_available": previous is not None,
        "snapshot_date": previous.snapshot_date.isoformat() if previous else None,
    }
    for field in fields:
        curr_val = current[field]
        prev_val = getattr(previous, field) if previous is not None else None
        trends[field] = {
            "current": curr_val,
            "previous": prev_val,
            "delta_abs": _delta_abs(curr_val, prev_val),
            "delta_pct": _delta_pct(curr_val, prev_val),
        }
    return trends
