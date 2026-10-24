"""Executive dashboard — one aggregate payload for the Dashboard's Executive tab.

Gated on ``reports.executive_dashboard``. The payload is aggregates only (no
card names, no individual risks). It applies the same rules as the modules it
summarises, before anything is aggregated, and grants nothing those modules
would not: every count is over the cards the caller may read with hidden card
types left out (D-01, as ``/reports/dashboard``); delivery money follows the
PPM portfolio rule and rationalization savings the rationalization totals rule
— both need ``costs.view`` itself (S-08, S-07). Risks come from the register's
own scoped loader. No improvement-opportunity figure is shown yet; one added
later must count through ``services/opportunity_access`` (S-12). The shaping
rules live in ``app.services.executive_dashboard``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.v1.risks import load_filtered_risks
from app.database import get_db
from app.models.app_settings import AppSettings
from app.models.card import Card
from app.models.card_type import CardType
from app.models.user import User
from app.services import executive_dashboard as exe
from app.services import ppm_portfolio_service as portfolio
from app.services.bpm_dashboard_service import build_bpm_dashboard
from app.services.card_read_scope import CardReadScope, visible_type_clause
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/executive")
async def executive_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
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

    portfolio_section = await exe.load_portfolio(db, readable)

    if ppm_enabled:
        initiatives = await portfolio.load_initiatives(
            db, portfolio.PortfolioScope(), read_scope=read_scope
        )
        hidden_types = set(
            (await db.execute(select(CardType.key).where(CardType.is_hidden.is_(True))))
            .scalars()
            .all()
        )
        initiatives = [c for c in initiatives if c.type not in hidden_types]
        init_ids = [c.id for c in initiatives]
        ppm = portfolio.build_dashboard(
            initiatives,
            await portfolio.latest_reports(db, init_ids),
            await portfolio.sum_budget_actual(db, init_ids),
        )
        delivery = exe.summarize_delivery(ppm, can_view_costs=can_view_costs)
    else:
        delivery = exe.section(exe.DISABLED)

    if bpm_enabled:
        processes = exe.summarize_processes(await build_bpm_dashboard(db, readable))
    else:
        processes = exe.section(exe.DISABLED)

    now = datetime.now(timezone.utc)
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
    )

    return {
        "generated_at": now.isoformat(),
        "can_view_costs": can_view_costs,
        "portfolio": portfolio_section,
        "delivery": delivery,
        "processes": processes,
        "risks": risks,
        "rationalization": rationalization,
    }
