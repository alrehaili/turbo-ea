"""Executive dashboard, Phase 2 — the CEO overview, decisions view and drill-downs.

Gated on ``reports.executive_dashboard``, which grants aggregates only (D-03):
listing a record still needs that record's module permission (``risks.view``,
``adr.view``, ``arb.view``, ``tech_standards.view``, ``ppm.view``), money needs
``costs.view`` and rationalization detail ``rationalization.view``. Every
population is the caller's ``CardReadScope`` with hidden card types left out
(D-01), applied before anything is counted; governance records about hidden
cards are omitted or redacted exactly as their own modules do (D-30).

The KPI builders live in ``app.services.executive``; this module only loads the
scoped inputs, checks permissions and assembles the response.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
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
from app.services.card_read_scope import CardReadScope, visible_type_clause
from app.services.executive import decisions as dec
from app.services.executive import kpis, periods
from app.services.fiscal_year import get_fiscal_year_start
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/reports/executive", tags=["reports"])

#: How many items the overview's "decisions needing attention" panel shows.
PANEL_SIZE = 5


async def _general(db: AsyncSession) -> dict[str, Any]:
    row = (
        await db.execute(select(AppSettings).where(AppSettings.id == "default"))
    ).scalar_one_or_none()
    return (row.general_settings if row else None) or {}


async def _can(db: AsyncSession, user: User, key: str) -> bool:
    return await PermissionService.has_app_permission(db, user, key)


async def _decisions(
    db: AsyncSession, user: User, read_scope: CardReadScope, general: dict, today
) -> tuple[dict[str, Any], dec.RiskPicture | None]:
    """The four decision sections, each a scoped count plus a gated list."""
    grc_enabled = bool(general.get("grcEnabled", True))
    picture = None
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
        picture = dec.classify_risks(risk_rows, today)
    can_risks = await _can(db, user, "risks.view")
    risks = dec.section(
        len(picture.escalated) if picture else 0,
        await dec.risk_items(db, picture.escalated, today) if picture and can_risks else [],
        can_list=can_risks,
        enabled=grc_enabled,
    )
    if picture is not None:
        risks |= {"open": picture.open, "mitigated": picture.mitigated}

    adrs = await dec.pending_adrs(db)
    arb = await dec.pending_arb(db, read_scope)
    exceptions = await dec.pending_exceptions(db, read_scope)
    can_adr = await _can(db, user, "adr.view")
    can_arb = await _can(db, user, "arb.view")
    can_exc = await _can(db, user, "tech_standards.view")
    sections = {
        "risks": risks,
        "adrs": dec.section(
            len(adrs), dec.adr_items(adrs, today) if can_adr else [], can_list=can_adr
        ),
        "arb": dec.section(
            len(arb), dec.arb_items(arb, today) if can_arb else [], can_list=can_arb
        ),
        "exceptions": dec.section(
            len(exceptions),
            dec.exception_items(exceptions, today) if can_exc else [],
            can_list=can_exc,
        ),
    }
    return sections, picture


def _panel(sections: dict[str, Any]) -> list[dict[str, Any]]:
    """Top items for the overview: escalated risks first, then the oldest
    pending decisions. Only records the caller may list appear."""
    risks = sections["risks"].get("items") or []
    pending = [
        item for key in ("adrs", "arb", "exceptions") for item in (sections[key].get("items") or [])
    ]
    pending.sort(key=lambda i: -(i.get("age_days") or 0))
    return (risks + pending)[:PANEL_SIZE]


@router.get("/overview")
async def executive_overview(
    period: str | None = Query(None, max_length=12),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The six CEO indicators for one reporting period (default: the current
    fiscal quarter), with the previous period where it can be derived."""
    await PermissionService.require_permission(db, user, "reports.executive_dashboard")
    read_scope = await CardReadScope.load(db, user)
    readable = (*read_scope.where(Card, mode="module"), visible_type_clause(Card))
    general = await _general(db)
    start_month = await get_fiscal_year_start(db)
    now = datetime.now(timezone.utc)
    today = now.date()
    try:
        current = periods.parse(period, start_month, today)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    prior = periods.previous(current, start_month, today)

    ppm_enabled = bool(general.get("ppmEnabled", False))
    stale = exe.staleness_days(general)
    initiatives = await exe.load_visible_initiatives(db, read_scope)
    ids = [c.id for c in initiatives]
    if ppm_enabled:
        now_reports = await portfolio.latest_reports(db, ids, as_of=current.as_of)
        prior_reports = await portfolio.latest_reports(db, ids, as_of=prior.as_of)
        delivery_now = exe.summarize_delivery_health(
            initiatives, now_reports, today=current.as_of, stale=stale
        )
        delivery_prior = exe.summarize_delivery_health(
            initiatives, prior_reports, today=prior.as_of, stale=stale
        )
    else:
        # A card's status field keeps no history: no previous-period value.
        delivery_now = exe.summarize_delivery_health(
            initiatives, None, today=current.as_of, stale=stale
        )
        delivery_prior = None

    currency = general.get("currency") or DEFAULT_CURRENCY
    rationalization = exe.summarize_rationalization(
        await exe.load_rationalization_decisions(db, readable),
        can_view_costs=await _can(db, user, "costs.view"),
        can_view_rationalization=await _can(db, user, "rationalization.view"),
        currency=currency,
    )

    sections, picture = await _decisions(db, user, read_scope, general, today)
    pending = {k: sections[k].get("count", 0) for k in ("adrs", "arb", "exceptions")}

    return {
        "generated_at": now.isoformat(),
        "period": current.to_dict(),
        "previous_period": prior.to_dict(),
        "available_periods": periods.available(today, start_month),
        "fiscal_year_start": start_month,
        "currency": currency,
        "kpis": [
            kpis.strategy_execution(current),
            kpis.governance_effectiveness(current),
            kpis.initiative_delivery(current, delivery_now, delivery_prior, prior),
            kpis.services_and_automation(current),
            kpis.business_value(current, rationalization["planned_savings"]),
            kpis.decisions_and_escalations(current, picture, pending),
        ],
        "decisions_panel": _panel(sections),
    }


@router.get("/decisions")
async def executive_decisions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Escalated risks and pending governance decisions, current state."""
    await PermissionService.require_permission(db, user, "reports.executive_dashboard")
    read_scope = await CardReadScope.load(db, user)
    general = await _general(db)
    now = datetime.now(timezone.utc)
    sections, _ = await _decisions(db, user, read_scope, general, now.date())
    return {"generated_at": now.isoformat(), **sections}


@router.get("/kpi/{key}/drilldown")
async def executive_kpi_drilldown(
    key: str,
    period: str | None = Query(None, max_length=12),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The records behind a KPI's value, under the same scope and rules.

    The rows come from the module the KPI summarises, so listing them needs
    that module's view permission as well as the executive one.
    """
    await PermissionService.require_permission(db, user, "reports.executive_dashboard")
    read_scope = await CardReadScope.load(db, user)
    general = await _general(db)
    start_month = await get_fiscal_year_start(db)
    today = datetime.now(timezone.utc).date()
    try:
        current = periods.parse(period, start_month, today)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if key == "TR-03":
        ppm_enabled = bool(general.get("ppmEnabled", False))
        if ppm_enabled:
            # Status-report health is PPM data.
            await PermissionService.require_permission(db, user, "ppm.view")
        initiatives = await exe.load_visible_initiatives(db, read_scope)
        latest = (
            await portfolio.latest_reports(db, [c.id for c in initiatives], as_of=current.as_of)
            if ppm_enabled
            else None
        )
        rows = exe.delivery_rows(
            initiatives, latest, today=current.as_of, stale=exe.staleness_days(general)
        )
        for row in rows:
            row["path"] = f"/ppm/{row['id']}" if ppm_enabled else f"/cards/{row['id']}"
        return {"key": key, "period": current.to_dict(), "rows": rows}

    if key == "DEC-01":
        if not bool(general.get("grcEnabled", True)):
            raise HTTPException(status_code=404, detail="Risk module is not enabled")
        await PermissionService.require_permission(db, user, "risks.view")
        sections, _ = await _decisions(db, user, read_scope, general, today)
        return {"key": key, "period": current.to_dict(), "rows": sections["risks"]["items"]}

    raise HTTPException(status_code=404, detail="No drill-down for this KPI")
