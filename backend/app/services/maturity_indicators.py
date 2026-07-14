"""Automated evidence indicators for the EA maturity self-assessment.

[FORK FEATURE] — automated maturity assessment.

Each built-in maturity dimension gets a small set of **indicators** computed
live from the repository (coverage ratios, adoption counts, quality averages).
The indicators aggregate into a **suggested level** on the fixed 1–5 scale.
The suggestion is *advisory*: assessments pre-fill ``suggested_level`` and the
``evidence`` snapshot on each score row, but the assessor always confirms the
actual ``level`` (repository-derived evidence cannot see off-tool practices
such as committees, mandates or funding).

Indicator shapes:
* ratio — ``value = 100 * numerator / denominator`` (skipped when the
  denominator is zero, so an agency without initiatives isn't scored on
  initiative planning);
* adoption — ``value = min(100, 100 * count / target)`` for practices where
  "enough of them exist" is the signal (principles, ADRs, ADM workspaces).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import Text, and_, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.adm import AdmWorkspace
from app.models.architecture_decision import ArchitectureDecision
from app.models.card import Card
from app.models.card_type import CardType
from app.models.ea_principle import EAPrinciple
from app.models.kpi_snapshot import KpiSnapshot
from app.models.maturity import MATURITY_MAX_LEVEL
from app.models.nea_evidence import NeaEvidencePack
from app.models.ppm_cost_line import PpmBudgetLine, PpmCostLine
from app.models.ppm_status_report import PpmStatusReport
from app.models.ppm_wbs import PpmWbs
from app.models.process_diagram import ProcessDiagram
from app.models.relation import Relation
from app.models.risk import Risk
from app.models.soaw import SoAW
from app.models.stakeholder import Stakeholder
from app.models.turbolens import TurboLensComplianceFinding

# Suggested-level bands over the 0–100 indicator average.
_LEVEL_BANDS: tuple[tuple[float, int], ...] = (
    (85.0, 5),
    (65.0, 4),
    (45.0, 3),
    (25.0, 2),
)

# Adoption targets: "this many is a fully established practice".
_TARGET_PRINCIPLES = 10
_TARGET_ADRS = 10
_TARGET_ADM_WORKSPACES = 3
_TARGET_RISKS = 5
_TARGET_TRANSITION_CARDS = 10
_TARGET_NEA_PACKS = 2
_KPI_WINDOW_DAYS = 30


def suggest_level(indicator_values: list[float]) -> int | None:
    """Band the indicator average into a 1–5 suggested level."""
    if not indicator_values:
        return None
    avg = sum(indicator_values) / len(indicator_values)
    for threshold, level in _LEVEL_BANDS:
        if avg >= threshold:
            return level
    return 1


def _ratio(key: str, numerator: int, denominator: int) -> dict | None:
    if denominator <= 0:
        return None
    return {
        "key": key,
        "kind": "ratio",
        "value": round(100 * numerator / denominator, 1),
        "numerator": numerator,
        "denominator": denominator,
    }


def _adoption(key: str, count: int, target: int) -> dict:
    return {
        "key": key,
        "kind": "adoption",
        "value": round(min(100.0, 100 * count / target), 1),
        "numerator": count,
        "denominator": target,
    }


def _quality(key: str, avg: float | None, count: int) -> dict | None:
    if not count or avg is None:
        return None
    return {
        "key": key,
        "kind": "quality",
        "value": round(avg, 1),
        "numerator": None,
        "denominator": None,
    }


_ACTIVE = Card.status != "ARCHIVED"


async def _count(db: AsyncSession, q) -> int:
    return int((await db.execute(q)).scalar() or 0)


async def _cards_with_lifecycle(db: AsyncSession, type_key: str | None = None) -> tuple[int, int]:
    """(cards with a non-empty lifecycle, total cards) — optionally for one type."""
    has_lc = case(
        (
            and_(Card.lifecycle.isnot(None), cast(Card.lifecycle, Text) != "{}"),
            1,
        )
    )
    q = select(func.count(Card.id), func.count(has_lc)).where(_ACTIVE)
    if type_key:
        q = q.where(Card.type == type_key)
    total, with_lc = (await db.execute(q)).one()
    return int(with_lc or 0), int(total or 0)


async def _linked_count(db: AsyncSession, a_type: str, b_type: str) -> int:
    """Distinct active cards of ``a_type`` related to any card of ``b_type``."""
    ca, cb = aliased(Card), aliased(Card)
    ids: set = set()
    for a_col, b_col in (
        (Relation.source_id, Relation.target_id),
        (Relation.target_id, Relation.source_id),
    ):
        q = (
            select(a_col)
            .join(ca, ca.id == a_col)
            .join(cb, cb.id == b_col)
            .where(ca.type == a_type, cb.type == b_type, ca.status != "ARCHIVED")
        )
        ids |= {r for (r,) in (await db.execute(q)).all()}
    return len(ids)


async def _layer_quality(db: AsyncSession) -> dict[str, tuple[float | None, int]]:
    """Layer (card-type category) → (avg data quality, card count)."""
    rows = (
        await db.execute(
            select(CardType.category, func.avg(Card.data_quality), func.count(Card.id))
            .join(CardType, CardType.key == Card.type)
            .where(_ACTIVE)
            .group_by(CardType.category)
        )
    ).all()
    return {cat: (float(avg) if avg is not None else None, int(n)) for cat, avg, n in rows if cat}


async def compute_indicators(db: AsyncSession) -> dict[str, dict]:
    """Compute the per-dimension indicator sets and suggested levels.

    Returns ``{dimension_key: {"indicators": [...], "score": float | None,
    "suggested_level": int | None}}`` for every built-in dimension key.
    Custom (agency-added) dimensions have no automated indicators.
    """
    today = date.today()
    layer_q = await _layer_quality(db)

    # ── Shared aggregates ────────────────────────────────────────────────
    total_cards, approved_cards = (
        await db.execute(
            select(
                func.count(Card.id),
                func.count(case((Card.approval_status == "APPROVED", 1))),
            ).where(_ACTIVE)
        )
    ).one()
    total_cards, approved_cards = int(total_cards or 0), int(approved_cards or 0)

    async def type_count(type_key: str) -> int:
        return await _count(db, select(func.count(Card.id)).where(_ACTIVE, Card.type == type_key))

    apps = await type_count("Application")
    caps = await type_count("BusinessCapability")
    processes = await type_count("BusinessProcess")
    data_objects = await type_count("DataObject")
    it_components = await type_count("ITComponent")
    initiatives = await type_count("Initiative")

    out: dict[str, dict] = {}

    def emit(dim_key: str, indicators: list[dict | None]) -> None:
        kept = [i for i in indicators if i is not None]
        values = [i["value"] for i in kept]
        score = round(sum(values) / len(values), 1) if values else None
        out[dim_key] = {
            "indicators": kept,
            "score": score,
            "suggested_level": suggest_level(values),
        }

    # ── governance ───────────────────────────────────────────────────────
    principles = await _count(db, select(func.count(EAPrinciple.id)))
    adrs = await _count(db, select(func.count(ArchitectureDecision.id)))
    emit(
        "governance",
        [
            _ratio("approval_coverage", approved_cards, total_cards),
            _adoption("principles_defined", principles, _TARGET_PRINCIPLES),
            _adoption("adr_practice", adrs, _TARGET_ADRS),
        ],
    )

    # ── business_architecture ────────────────────────────────────────────
    apps_with_cap = await _linked_count(db, "Application", "BusinessCapability") if apps else 0
    procs_with_flow = await _count(
        db,
        select(func.count(func.distinct(ProcessDiagram.process_id)))
        .join(Card, Card.id == ProcessDiagram.process_id)
        .where(_ACTIVE),
    )
    biz_avg, biz_n = layer_q.get("Business", (None, 0))
    emit(
        "business_architecture",
        [
            _ratio("capability_app_mapping", apps_with_cap, apps),
            _ratio("process_documentation", procs_with_flow, processes),
            _quality("layer_quality", biz_avg, biz_n),
        ],
    )

    # ── application_architecture ─────────────────────────────────────────
    app_lc, _ = await _cards_with_lifecycle(db, "Application")
    apps_with_interface = await _linked_count(db, "Application", "Interface") if apps else 0
    app_avg, app_n = layer_q.get("Application", (None, 0))
    emit(
        "application_architecture",
        [
            _quality("layer_quality", app_avg, app_n),
            _ratio("lifecycle_coverage", app_lc, apps),
            _ratio("integration_documentation", apps_with_interface, apps),
        ],
    )

    # ── data_architecture ────────────────────────────────────────────────
    data_owned = await _count(
        db,
        select(func.count(func.distinct(Stakeholder.card_id)))
        .join(Card, Card.id == Stakeholder.card_id)
        .where(_ACTIVE, Card.type == "DataObject"),
    )
    data_used = await _linked_count(db, "DataObject", "Application") if data_objects else 0
    data_avg, data_n = layer_q.get("Data", (None, 0))
    emit(
        "data_architecture",
        [
            _quality("layer_quality", data_avg, data_n),
            _ratio("data_ownership", data_owned, data_objects),
            _ratio("data_usage_mapping", data_used, data_objects),
        ],
    )

    # ── technology_architecture ──────────────────────────────────────────
    tech_lc, _ = await _cards_with_lifecycle(db, "ITComponent")
    tech_categorised = (
        await _linked_count(db, "ITComponent", "TechCategory") if it_components else 0
    )
    tech_avg, tech_n = layer_q.get("Technology", (None, 0))
    emit(
        "technology_architecture",
        [
            _quality("layer_quality", tech_avg, tech_n),
            _ratio("lifecycle_coverage", tech_lc, it_components),
            _ratio("tech_category_mapping", tech_categorised, it_components),
        ],
    )

    # ── security_compliance ──────────────────────────────────────────────
    findings_total, findings_ok = (
        await db.execute(
            select(
                func.count(TurboLensComplianceFinding.id),
                func.count(case((TurboLensComplianceFinding.status == "compliant", 1))),
            )
        )
    ).one()
    open_risks, overdue_risks = (
        await db.execute(
            select(
                func.count(Risk.id),
                func.count(
                    case(
                        (
                            and_(
                                Risk.target_resolution_date.isnot(None),
                                Risk.target_resolution_date < today,
                            ),
                            1,
                        )
                    )
                ),
            ).where(Risk.status.notin_(("closed", "accepted")))
        )
    ).one()
    risks_total = await _count(db, select(func.count(Risk.id)))
    sec_avg, sec_n = layer_q.get("Security", (None, 0))
    emit(
        "security_compliance",
        [
            _ratio("compliance_posture", int(findings_ok or 0), int(findings_total or 0)),
            _ratio(
                "risk_hygiene",
                int(open_risks or 0) - int(overdue_risks or 0),
                int(open_risks or 0),
            ),
            _adoption("risk_practice", risks_total, _TARGET_RISKS),
            _quality("layer_quality", sec_avg, sec_n),
        ],
    )

    # ── methodology ──────────────────────────────────────────────────────
    workspaces = await _count(db, select(func.count(AdmWorkspace.id)))
    inits_with_soaw = await _count(
        db,
        select(func.count(func.distinct(SoAW.initiative_id))).where(SoAW.initiative_id.isnot(None)),
    )
    emit(
        "methodology",
        [
            _adoption("adm_adoption", workspaces, _TARGET_ADM_WORKSPACES),
            _ratio("soaw_coverage", inits_with_soaw, initiatives),
        ],
    )

    # ── performance ──────────────────────────────────────────────────────
    inits_reporting = await _count(
        db,
        select(func.count(func.distinct(PpmStatusReport.initiative_id))),
    )
    inits_budgeted = len(
        {r for (r,) in (await db.execute(select(func.distinct(PpmBudgetLine.initiative_id)))).all()}
        | {r for (r,) in (await db.execute(select(func.distinct(PpmCostLine.initiative_id)))).all()}
    )
    kpi_days = await _count(
        db,
        select(func.count(func.distinct(func.date(KpiSnapshot.created_at)))).where(
            KpiSnapshot.created_at >= datetime.now(timezone.utc) - timedelta(days=_KPI_WINDOW_DAYS)
        ),
    )
    emit(
        "performance",
        [
            _ratio("status_reporting", inits_reporting, initiatives),
            _ratio("budget_tracking", inits_budgeted, initiatives),
            _adoption("kpi_trend_tracking", kpi_days, _KPI_WINDOW_DAYS),
        ],
    )

    # ── change_transition ────────────────────────────────────────────────
    inits_with_wbs = await _count(
        db,
        select(func.count(func.distinct(PpmWbs.initiative_id))),
    )
    transition_cards = await _count(
        db,
        select(func.count(Card.id)).where(
            _ACTIVE, Card.architecture_state.in_(("transition", "target"))
        ),
    )
    lc_cards, lc_total = await _cards_with_lifecycle(db)
    emit(
        "change_transition",
        [
            _ratio("initiative_planning", inits_with_wbs, initiatives),
            _adoption("target_state_modeling", transition_cards, _TARGET_TRANSITION_CARDS),
            _ratio("lifecycle_planning", lc_cards, lc_total),
        ],
    )

    # ── national_alignment ───────────────────────────────────────────────
    caps_from_catalogue = await _count(
        db,
        select(func.count(Card.id)).where(
            _ACTIVE,
            Card.type == "BusinessCapability",
            Card.attributes.op("?")("catalogueId"),
        ),
    )
    nea_packs = await _count(
        db,
        select(func.count(NeaEvidencePack.id)).where(NeaEvidencePack.status == "ready"),
    )
    emit(
        "national_alignment",
        [
            _ratio("catalogue_alignment", caps_from_catalogue, caps),
            _adoption("nea_evidence", nea_packs, _TARGET_NEA_PACKS),
        ],
    )

    return out


__all__ = ["compute_indicators", "suggest_level", "MATURITY_MAX_LEVEL"]
