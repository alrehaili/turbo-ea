"""Executive dashboard — one aggregate payload for the Dashboard's Executive tab.

Gated on ``reports.executive_dashboard``. The payload is aggregates (counts,
distributions, totals) with one record-level exception: the list of
applications whose planned-savings estimates conflict, which names the
application and each assessment's estimate so the conflict can be reconciled.
That list needs ``costs.view`` and ``rationalization.view`` (the rationalization
module's own read permission) and names only cards the caller may read; without
``rationalization.view`` only the number of conflicts is returned. No
individual risk is ever listed.

The endpoint applies the same rules as the modules it summarises, before
anything is aggregated, and grants nothing those modules would not: every count
is over the cards the caller may read with hidden card types left out (D-01, as
``/reports/dashboard``); delivery money follows the PPM portfolio rule and
rationalization savings the rationalization totals rule — both need
``costs.view`` itself (S-08, S-07). Risks come from the register's own scoped
loader. No improvement-opportunity figure is shown yet; one added later must
count through ``services/opportunity_access`` (S-12). The shaping rules live in
``app.services.executive_dashboard``.

Phase 1 (KPI correctness): initiative health is four states with reporting
coverage kept separate (D-02); budget and actuals are for one fiscal year
(D-06); planned savings are deduplicated with conflicts excluded (D-24); every
money block names its currency and nothing is converted (D-05). Amounts carry
no currency of their own, so they are labelled with the instance currency.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.risks import load_filtered_risks
from app.api.v1.settings import DEFAULT_CURRENCY
from app.database import get_db
from app.models.app_settings import AppSettings
from app.models.card import Card
from app.models.user import User
from app.services import executive_dashboard as exe
from app.services import ppm_portfolio_service as portfolio
from app.services.bpm_dashboard_service import build_bpm_dashboard
from app.services.card_read_scope import CardReadScope, visible_type_clause
from app.services.executive.benefits import all_superseded_ids
from app.services.fiscal_year import current_fiscal_year, get_fiscal_year_start
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/executive")
async def executive_dashboard(
    fiscal_year: int | None = Query(None, ge=1900, le=2200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """``fiscal_year`` selects the period of the budget figures (default: the
    current fiscal year, from the ``fiscalYearStart`` setting)."""
    await PermissionService.require_permission(db, user, "reports.executive_dashboard")
    read_scope = await CardReadScope.load(db, user)
    # Scope and the hidden-type rule go into every card query below, so they
    # apply before aggregation rather than to the finished figures.
    readable = (*read_scope.where(Card, mode="module"), visible_type_clause(Card))
    can_view_costs = await PermissionService.has_app_permission(db, user, "costs.view")

    settings_row = (
        await db.execute(select(AppSettings).where(AppSettings.id == "default"))
    ).scalar_one_or_none()
    general = (settings_row.general_settings if settings_row else None) or {}
    # Defaults match GET /settings/*-enabled: PPM is opt-in, BPM and GRC opt-out.
    ppm_enabled = bool(general.get("ppmEnabled", False))
    bpm_enabled = bool(general.get("bpmEnabled", True))
    grc_enabled = bool(general.get("grcEnabled", True))
    # Amounts are recorded in the instance currency; it is named, never converted.
    currency = general.get("currency") or DEFAULT_CURRENCY
    start_month = await get_fiscal_year_start(db)
    current_fy = current_fiscal_year(start_month)
    fy = fiscal_year or current_fy

    now = datetime.now(timezone.utc)
    portfolio_section = await exe.load_portfolio(db, readable)

    # Initiatives the caller may read, hidden types left out (D-01). Loaded with
    # or without PPM: without it, ``initiativeStatus`` is the health source.
    initiatives = await exe.load_visible_initiatives(db, read_scope)
    init_ids = [c.id for c in initiatives]
    latest = await portfolio.latest_reports(db, init_ids) if ppm_enabled else None
    delivery = exe.summarize_delivery_health(
        initiatives, latest, today=now.date(), stale=exe.staleness_days(general)
    )
    # Money needs PPM's lines; totals need costs.view itself (S-08) — the
    # amounts are not even read without it.
    money = (
        await exe.load_fiscal_money(db, init_ids, fy=fy, start_month=start_month)
        if ppm_enabled and can_view_costs
        else None
    )
    delivery["budget"] = exe.summarize_budget(
        money,
        enabled=ppm_enabled,
        fy=fy,
        start_month=start_month,
        current_fy=current_fy,
        currency=currency,
        can_view_costs=can_view_costs,
    )

    if bpm_enabled:
        processes = exe.summarize_processes(await build_bpm_dashboard(db, readable))
    else:
        processes = exe.section(exe.DISABLED)

    if grc_enabled:
        risk_rows = await load_filtered_risks(
            db,
            status=None,
            category=None,
            level=None,
            owner_id=None,
            card_ids=None,
            card_types=None,
            source_type=None,
            search=None,
            overdue=False,
            read_scope=read_scope,
        )
        risks = exe.summarize_risks(risk_rows, today=now.date())
    else:
        risks = exe.section(exe.DISABLED)

    rationalization = exe.summarize_rationalization(
        await exe.load_rationalization_decisions(db, readable),
        can_view_costs=can_view_costs,
        can_view_rationalization=await PermissionService.has_app_permission(
            db, user, "rationalization.view"
        ),
        currency=currency,
        # A decision a benefit names is counted in the register (D-31, I-71).
        superseded=await all_superseded_ids(db),
    )

    return {
        "generated_at": now.isoformat(),
        "can_view_costs": can_view_costs,
        "currency": currency,
        "ppm_enabled": ppm_enabled,
        "portfolio": portfolio_section,
        "delivery": delivery,
        "processes": processes,
        "risks": risks,
        "rationalization": rationalization,
    }
