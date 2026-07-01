"""Integration Hub — sync status / drift dashboard (Wave 4 #11).

The consumable half of the Integration Hub: a single view of every configured
data source, its last sync, coverage (identity-mapped cards), and pending
changes / staleness. Built over the existing ServiceNow integration tables —
which already implement the staging + identity-map + field-level source-of-truth
pattern the plan wants to generalise.

Per plan.md #11 (and Turbo EA's own YAGNI guidance for the migration adapters),
the *generalised connector framework* and additional connectors are intentionally
deferred until a second real connector exists; this dashboard is source-shaped so
it can absorb them when they arrive.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.servicenow import (
    SnowConnection,
    SnowIdentityMap,
    SnowStagedRecord,
    SnowSyncRun,
)


async def gather_integration_status(db: AsyncSession) -> dict:
    """One row per source connection: last sync, coverage, pending changes."""
    conns = (await db.execute(select(SnowConnection))).scalars().all()

    # Last sync run per connection.
    last_run: dict[uuid.UUID, SnowSyncRun] = {}
    runs = (
        (await db.execute(select(SnowSyncRun).order_by(SnowSyncRun.started_at.desc())))
        .scalars()
        .all()
    )
    for run in runs:
        last_run.setdefault(run.connection_id, run)

    # Identity-map coverage (mapped cards) per connection.
    coverage: dict[uuid.UUID, int] = {}
    for cid, count in (
        await db.execute(
            select(SnowIdentityMap.connection_id, func.count()).group_by(
                SnowIdentityMap.connection_id
            )
        )
    ).all():
        coverage[cid] = count

    # Pending staged records (drift awaiting review) per connection, via run join.
    pending: dict[uuid.UUID, int] = {}
    for cid, count in (
        await db.execute(
            select(SnowSyncRun.connection_id, func.count())
            .join(SnowStagedRecord, SnowStagedRecord.sync_run_id == SnowSyncRun.id)
            .where(SnowStagedRecord.status == "pending")
            .group_by(SnowSyncRun.connection_id)
        )
    ).all():
        pending[cid] = count

    now = datetime.now(timezone.utc)
    rows: list[dict] = []
    stale = 0
    total_pending = 0
    for c in conns:
        run = last_run.get(c.id)
        last_at = run.completed_at or run.started_at if run else None
        days_since = None
        if last_at:
            la = last_at if last_at.tzinfo else last_at.replace(tzinfo=timezone.utc)
            days_since = (now - la).days
        is_stale = days_since is None or days_since > 7
        if is_stale:
            stale += 1
        total_pending += pending.get(c.id, 0)
        rows.append(
            {
                "id": str(c.id),
                "name": c.name,
                "source_type": "servicenow",
                "is_active": c.is_active,
                "last_sync_at": last_at.isoformat() if last_at else None,
                "last_sync_status": run.status if run else None,
                "days_since_sync": days_since,
                "is_stale": is_stale,
                "mapped_cards": coverage.get(c.id, 0),
                "pending_changes": pending.get(c.id, 0),
            }
        )

    rows.sort(key=lambda r: r["name"].lower())
    return {
        "summary": {
            "connections": len(conns),
            "stale_connections": stale,
            "pending_changes": total_pending,
            "mapped_cards": sum(coverage.values()),
        },
        "connections": rows,
    }
