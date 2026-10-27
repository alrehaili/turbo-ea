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

Two kinds of figure, never mixed: *period* figures are measured over the
selected period, and for a finished period only from dated records (else
"historical data unavailable"); *current-state* figures — escalated risks, the
operational governance pipeline, undated planned savings — describe today and
are labelled so whatever period is selected.
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
from app.services import ea_applicability as ea
from app.services import executive_dashboard as exe
from app.services import kpi_measurement_service as kms
from app.services import ppm_portfolio_service as portfolio
from app.services import risk_governance
from app.services.card_read_scope import CardReadScope, visible_type_clause
from app.services.executive import benefits as ben
from app.services.executive import decisions as dec
from app.services.executive import governance as gov
from app.services.executive import kpis, linkage, periods, strategy
from app.services.fiscal_year import get_fiscal_year_start
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/reports/executive", tags=["reports"])

#: How many escalations the overview's attention panel lists.
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
        group=dec.EXECUTIVE_ESCALATION,
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
            len(adrs),
            dec.adr_items(adrs, today) if can_adr else [],
            can_list=can_adr,
            group=dec.OPERATIONAL_PIPELINE,
        ),
        "arb": dec.section(
            len(arb),
            dec.arb_items(arb, today) if can_arb else [],
            can_list=can_arb,
            group=dec.OPERATIONAL_PIPELINE,
        ),
        "exceptions": dec.section(
            len(exceptions),
            dec.exception_items(exceptions, today) if can_exc else [],
            can_list=can_exc,
            group=dec.OPERATIONAL_PIPELINE,
        ),
    }
    return sections, picture


def _panel(risks: dict[str, Any]) -> dict[str, Any]:
    """The CEO attention panel: executive escalations only (the D-04 risk rule).

    The operational pipeline never appears here — no approved rule escalates it.
    The status and the full count travel with the items, so a reader who may not
    open the risk register sees "N escalated, restricted" rather than an empty
    panel that would read as "nothing needs attention".
    """
    if risks["status"] == "disabled":
        return {"status": "disabled", "count": 0, "items": [], "more": 0}
    count = risks.get("count", 0)
    if risks["status"] == "restricted":
        return {"status": "restricted", "count": count, "items": [], "more": 0}
    items = (risks.get("items") or [])[:PANEL_SIZE]
    return {"status": "ok", "count": count, "items": items, "more": max(0, count - len(items))}


async def _current_delivery(
    db: AsyncSession, read_scope: CardReadScope, general: dict, today
) -> dict[str, Any]:
    """Delivery health as of today, over today's in-flight initiatives."""
    initiatives = await exe.load_visible_initiatives(db, read_scope)
    latest = (
        await portfolio.latest_reports(db, [c.id for c in initiatives], as_of=today)
        if bool(general.get("ppmEnabled", False))
        else None
    )
    return exe.summarize_delivery_health(
        initiatives, latest, today=today, stale=exe.staleness_days(general)
    )


@router.get("/overview")
async def executive_overview(
    period: str | None = Query(None, max_length=12),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The six CEO indicators for one reporting period (default: the current
    fiscal quarter). Period figures for a finished period need dated evidence;
    current-state figures are labelled and measured today."""
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

    # History (D-19) is landscape-wide: read only by viewers who see the whole
    # landscape, as the dashboard trend always was.
    history_ok = read_scope.is_unrestricted(mode="module")

    async def _verified(key: str, p: periods.Period):
        if not history_ok:
            return None
        m = await kms.current_period_value(db, p.key, metric_key=key)
        return m if m is not None and m.status == "verified" else None

    previous_delivery = kpis.previous_from_history(prior, await _verified("TR-03", prior))
    if current.is_current:
        # The in-flight population is the cards' present status, which keeps no
        # history — so it is counted live for the current period only.
        delivery_tile = kpis.initiative_delivery(
            current,
            await _current_delivery(db, read_scope, general, today),
            prior,
            previous_delivery,
        )
        strategy_tile = kpis.strategy_execution(
            current, await strategy.strategy_achievement(db, read_scope, current, general, today)
        )
    else:
        # A finished period: only its verified period measurement (D-19).
        m = (
            await kms.current_period_value(db, current.key, metric_key="TR-03")
            if history_ok
            else None
        )
        delivery_tile = kpis.recorded_delivery(current, m, previous_delivery)
        strategy_tile = kpis.strategy_execution(current, None)

    currency = general.get("currency") or DEFAULT_CURRENCY
    can_costs = await _can(db, user, "costs.view")
    rationalization = exe.summarize_rationalization(
        await exe.load_rationalization_decisions(db, readable),
        can_view_costs=can_costs,
        can_view_rationalization=await _can(db, user, "rationalization.view"),
        currency=currency,
        superseded=await ben.all_superseded_ids(db),
    )
    # FIN-01 (Phase 4): Finance-confirmed cash of the period's fiscal year.
    if can_costs:
        bundles, _ = await ben.load_visible(db, read_scope)
        realised = {"status": "ok", "by_currency": ben.confirmed_cash(bundles, current.fy)}
    else:
        realised = {"status": "restricted"}

    sections, picture = await _decisions(db, user, read_scope, general, today)
    pipeline = {k: sections[k].get("count", 0) for k in ("adrs", "arb", "exceptions")}
    # Target, owner and ratification from each indicator's KPI card (D-26).
    links = await linkage.linked_cards(db, read_scope)

    return {
        "generated_at": now.isoformat(),
        "period": current.to_dict(),
        "previous_period": prior.to_dict(),
        "available_periods": periods.available(today, start_month),
        "fiscal_year_start": start_month,
        "currency": currency,
        "kpis": [
            strategy_tile,
            # GOV-05 (D-41): target and owner from its KPI card, the previous
            # period from its verified period measurement (D-19, D-26).
            linkage.apply_link(
                kpis.governance_effectiveness(
                    current,
                    await gov.decision_implementation(db, read_scope, current),
                    kpis.previous_from_history(prior, await _verified("GOV-05", prior)),
                ),
                links.get("GOV-05"),
            ),
            linkage.apply_link(delivery_tile, links.get("TR-03")),
            kpis.services_and_automation(current),
            kpis.business_value(current, rationalization["planned_savings"], realised),
            linkage.apply_link(
                kpis.decisions_and_escalations(current, picture, pipeline, today),
                links.get("DEC-01"),
            ),
        ],
        "escalations_panel": _panel(sections["risks"]),
    }


@router.get("/strategy")
async def executive_strategy(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Strategy achievement for the current period (D-21): strategic KPIs by
    objective and pillar, each with its evidence state, and execution apart.

    Lists KPI, objective and pillar names, so beyond the executive permission it
    needs card read access to them — every card is the caller's read scope, with
    hidden types left out; a card the caller cannot read is simply absent.
    """
    await PermissionService.require_permission(db, user, "reports.executive_dashboard")
    read_scope = await CardReadScope.load(db, user)
    general = await _general(db)
    start_month = await get_fiscal_year_start(db)
    now = datetime.now(timezone.utc)
    current = periods.parse(None, start_month, now.date())
    summary = await strategy.strategy_achievement(db, read_scope, current, general, now.date())
    return {"generated_at": now.isoformat(), **summary}


@router.get("/governance")
async def executive_governance(
    period: str | None = Query(None, max_length=12),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """EA governance effectiveness for one period (Batch 3.1, DECISION_LOG §3.1).

    Activity, effectiveness and impact kept apart; every figure without a
    defensible calculation is Not Available with its reason. Aggregates need the
    executive permission (D-03); the GOV-03 drill-down list needs
    ``tech_standards.view`` and is a separate call.
    """
    await PermissionService.require_permission(db, user, "reports.executive_dashboard")
    read_scope = await CardReadScope.load(db, user)
    start_month = await get_fiscal_year_start(db)
    now = datetime.now(timezone.utc)
    try:
        current = periods.parse(period, start_month, now.date())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    links = await linkage.linked_cards(db, read_scope)
    # GOV-05 history is landscape-wide (D-19, I-5): only for unrestricted readers.
    prior = periods.previous(current, start_month, now.date())
    history_ok = read_scope.is_unrestricted(mode="module")

    async def _verified(key: str):
        if not history_ok:
            return None
        m = await kms.current_period_value(db, prior.key, metric_key=key)
        return m if m is not None and m.status == "verified" else None

    general = await _general(db)
    summary = await gov.governance_summary(
        db,
        read_scope,
        current,
        gov03_link=links.get("GOV-03"),
        gov05_link=links.get("GOV-05"),
        gov05_previous=kpis.previous_from_history(prior, await _verified("GOV-05")),
        rsk01_link=links.get("RSK-01"),
        rsk01_previous=kpis.previous_from_history(prior, await _verified("RSK-01")),
        grc_enabled=bool(general.get("grcEnabled", True)),
        gov01_link=links.get("GOV-01"),
        gov01_previous=kpis.previous_from_history(prior, await _verified("GOV-01")),
        general=general,
    )
    return {"generated_at": now.isoformat(), "fiscal_year_start": start_month, **summary}


@router.get("/benefits")
async def executive_benefits(
    period: str | None = Query(None, max_length=12),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Benefits realisation for the fiscal year of the selected period
    (Phase 4 Batches 4.2 and 4.3, DECISION_LOG I-70..I-74).

    Planned, reported and Finance-confirmed value are separate sections and
    never summed; every amount is per currency and needs ``costs.view``.
    Non-financial outcomes are reported apart, with no amount. ROI is Not
    Available until Batch 4.4 (D-15, D-05)."""
    await PermissionService.require_permission(db, user, "reports.executive_dashboard")
    await PermissionService.require_permission(db, user, "benefits.view")
    read_scope = await CardReadScope.load(db, user)
    readable_clause = (*read_scope.where(Card, mode="module"), visible_type_clause(Card))
    general = await _general(db)
    start_month = await get_fiscal_year_start(db)
    now = datetime.now(timezone.utc)
    try:
        current = periods.parse(period, start_month, now.date())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    fy = current.fy
    bundles, readable = await ben.load_visible(db, read_scope)
    can_costs = await _can(db, user, "costs.view")
    allocation_ids = {
        al.card_id
        for b in bundles
        for allocs in b.allocations.values()
        for al in allocs
        if al.card_id in readable
    }
    financial = (
        ben.financial_summary(bundles, fy, readable, await ben.card_names(db, allocation_ids))
        if can_costs
        else {"status": "restricted"}
    )
    currency = general.get("currency") or DEFAULT_CURRENCY
    forecast = exe.summarize_rationalization(
        await exe.load_rationalization_decisions(db, readable_clause),
        can_view_costs=can_costs,
        can_view_rationalization=await _can(db, user, "rationalization.view"),
        currency=currency,
        superseded=await ben.all_superseded_ids(db),
    )["planned_savings"]
    return {
        "generated_at": now.isoformat(),
        "period": current.to_dict(),
        "available_periods": periods.available(now.date(), start_month),
        "fiscal_year": fy,
        "fiscal_year_start": start_month,
        # The register is read by fiscal year: a quarter shows its year (I-70).
        "quarter_selected": current.quarter is not None,
        "counts": ben.counts(bundles, fy),
        "financial": financial,
        # D-31: an annual run-rate forecast with no fiscal year, never realised.
        "run_rate_forecast": {**forecast, "temporal": "current_state"},
        "roi": ben.ROI_NOT_AVAILABLE,
        "outcomes": await ben.outcomes(db, bundles, fy, readable),
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
        if not current.is_current:
            # Same rule as the tile: no recorded population for a finished period.
            return {
                "key": key,
                "period": current.to_dict(),
                "status": "not_available",
                "reason": kpis.HISTORICAL_UNAVAILABLE,
                "rows": [],
            }
        initiatives = await exe.load_visible_initiatives(db, read_scope)
        latest = (
            await portfolio.latest_reports(db, [c.id for c in initiatives], as_of=today)
            if ppm_enabled
            else None
        )
        rows = exe.delivery_rows(
            initiatives, latest, today=today, stale=exe.staleness_days(general)
        )
        for row in rows:
            row["path"] = f"/ppm/{row['id']}" if ppm_enabled else f"/cards/{row['id']}"
        return {"key": key, "period": current.to_dict(), "status": "ok", "rows": rows}

    if key == "GOV-03":
        # The non-compliant assessed cards come from the standards module.
        await PermissionService.require_permission(db, user, "tech_standards.view")
        result = await gov.gov03_drilldown(db, read_scope)
        return {**result, "period": current.to_dict()}

    if key == "GOV-01":
        # Review records: architecture reviews or decision records (I-62).
        can_arb = await _can(db, user, "arb.view")
        can_adr = await _can(db, user, "adr.view")
        if not (can_arb or can_adr):
            raise HTTPException(status_code=403, detail="Not enough permissions")
        return {
            "key": key,
            "temporal": kpis.CURRENT_STATE,
            "as_of": today.isoformat(),
            "status": "ok",
            "can_assess": await _can(db, user, ea.ASSESS_PERMISSION),
            "rows": await gov.review_coverage_rows(
                db, read_scope, include_reviews=can_arb, include_adrs=can_adr
            ),
        }

    if key == "GOV-09":
        # Delivery states are initiative delivery data, gated as TR-03 is.
        if bool(general.get("ppmEnabled", False)):
            await PermissionService.require_permission(db, user, "ppm.view")
        return {
            "key": key,
            "temporal": kpis.CURRENT_STATE,
            "as_of": today.isoformat(),
            "status": "ok",
            "rows": await gov.governed_delivery_rows(db, read_scope, today, general),
        }

    if key == "RSK-01":
        # The architecture-related risks behind the count (D-42, I-56).
        if not bool(general.get("grcEnabled", True)):
            raise HTTPException(status_code=404, detail="Risk module is not enabled")
        await PermissionService.require_permission(db, user, "risks.view")
        return {
            "key": key,
            "temporal": kpis.CURRENT_STATE,
            "as_of": today.isoformat(),
            "status": "ok",
            "rows": await risk_governance.architecture_risk_rows(db, user, read_scope, today),
        }

    if key == "DEC-01":
        if not bool(general.get("grcEnabled", True)):
            raise HTTPException(status_code=404, detail="Risk module is not enabled")
        await PermissionService.require_permission(db, user, "risks.view")
        sections, _ = await _decisions(db, user, read_scope, general, today)
        # Current state: escalations are today's register whatever period is asked.
        return {
            "key": key,
            "temporal": kpis.CURRENT_STATE,
            "as_of": today.isoformat(),
            "status": "ok",
            "rows": sections["risks"]["items"],
        }

    raise HTTPException(status_code=404, detail="No drill-down for this KPI")
