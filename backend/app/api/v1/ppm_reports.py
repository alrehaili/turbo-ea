"""PPM — Portfolio-level dashboard KPIs, Gantt chart data, and grouping options.

These handlers are thin: everything they return is built by
``app.services.ppm_portfolio_service``, which the account-less portfolio portal
(``/web-portals/public/{slug}/ppm/portfolio``) shares. Keeping one builder is
what stops the authenticated and public boards drifting apart.

Authorization stays here, in the route layer — the service knows nothing about
users or permissions.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.ppm import PpmGanttItem, PpmGroupOption
from app.services import ppm_portfolio_service as portfolio
from app.services.card_read_scope import CardReadScope
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/reports/ppm", tags=["ppm-reports"])


@router.get("/group-options", response_model=list[PpmGroupOption])
async def ppm_group_options(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return card types that Initiative has relation types to (for grouping dropdown)."""
    await PermissionService.require_permission(db, user, "ppm.view")
    return await portfolio.build_group_options(db, read_scope=await CardReadScope.load(db, user))


@router.get("/dashboard")
async def ppm_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "ppm.view")

    initiatives = await portfolio.load_initiatives(
        db, portfolio.PortfolioScope(), read_scope=await CardReadScope.load(db, user)
    )
    init_ids = [c.id for c in initiatives]
    latest = await portfolio.latest_reports(db, init_ids)
    totals = await portfolio.sum_budget_actual(db, init_ids)
    out = portfolio.build_dashboard(initiatives, latest, totals)
    # Portfolio money totals need `costs.view` itself (S-08); the per-card
    # stakeholder bypass does not unlock a sum over many initiatives. The
    # non-financial indicators (counts, statuses, schedule / cost / scope RAG)
    # stay visible.
    can_view_costs = await PermissionService.has_app_permission(db, user, "costs.view")
    if not can_view_costs:
        out["total_budget"] = None
        out["total_actual"] = None
    out["costs_restricted"] = not can_view_costs
    return out


@router.get("/gantt", response_model=list[PpmGanttItem])
async def ppm_gantt(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    group_by: str | None = Query(
        None,
        description=(
            "Card type key to group by, or subtype:<key> to group every initiative "
            "under the top-most initiative of that Initiative subtype above it"
        ),
    ),
    architecture_state: str | None = Query(
        None, description="Filter by architecture_state (e.g., 'transition')"
    ),
):
    await PermissionService.require_permission(db, user, "ppm.view")

    read_scope = await CardReadScope.load(db, user)
    initiatives = await portfolio.load_initiatives(
        db, portfolio.PortfolioScope(), read_scope=read_scope
    )
    if architecture_state:  # [FORK] transition-architecture filter
        initiatives = [
            c
            for c in initiatives
            if (c.attributes or {}).get("architecture_state") == architecture_state
        ]
    latest = await portfolio.latest_reports(db, [c.id for c in initiatives])
    # The Initiative card's own cost fields follow the card endpoints' rule:
    # ``costs.view``, or a stakeholder role on that initiative.
    cost_card_ids: frozenset[uuid.UUID] | None = None
    if not await PermissionService.has_app_permission(db, user, "costs.view"):
        cost_card_ids = frozenset(
            await PermissionService.card_ids_with_cost_access(db, user, [c.id for c in initiatives])
        )
    return await portfolio.build_gantt_items(
        db,
        initiatives,
        latest,
        group_by=group_by,
        read_scope=read_scope,
        cost_card_ids=cost_card_ids,
    )
