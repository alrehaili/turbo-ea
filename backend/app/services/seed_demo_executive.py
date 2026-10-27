"""Executive dashboard demo data (SEED_DEMO or SEED_NORA).

The landscape seeders create cards, but the executive pages measure what
happened to them: status reports, ratified KPI targets and verified values,
decision history, implementation deadlines, exceptions, the business calendar,
review applicability, risk links and KPI history. Without those every figure is
correctly *Not available*. This seeder records that history over whichever
landscape is present (NexaTech or NORA), dated in the current fiscal quarter
and the one before, so each page has figures:

* **Delivery (TR-03)** — PPM on, recent status reports with a health mix,
  budget and cost lines for the fiscal year.
* **Strategy (TR-01)** — strategic objectives linked to approved KPI cards with
  ratified targets and verified values (on and off target), supporting
  initiatives.
* **KPI links** — KPI cards carrying ``metricKey`` for TR-03, GOV-05, GOV-01,
  RSK-01 and DEC-01 (target, owner, ratification), and a verified value for the
  previous quarter of each, so tiles show their previous period.
* **Governance** — ADRs signed and ARB reviews decided this quarter with their
  transition history (GOV-07), standard exceptions through their lifecycle
  (GOV-04), implementation deadlines, actions and independent verification
  (GOV-05), a confirmed business calendar (working days), EA review
  applicability (GOV-01, GOV-09), risk ↔ governance links (RSK-01) and two
  escalated risks (DEC-01).

GOV-03 needs IT components on governed technology categories; on a NORA
landscape those types are hidden by the profile, so it stays Not available.

Runs once per install (``seed_markers`` key ``executive``).

[FORK]
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_settings import AppSettings
from app.models.arb_review import ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.business_calendar import DEFAULT_WORKING_WEEKDAYS, BusinessCalendarYear
from app.models.card import KPI_CARD_TYPE, Card
from app.models.decision_implementation import DecisionImplementation
from app.models.ea_review_applicability import EaReviewApplicability
from app.models.governance_transition import GovernanceTransition
from app.models.kpi_measurement import KpiMeasurement, KpiTargetRatification
from app.models.ppm_cost_line import PpmBudgetLine, PpmCostLine
from app.models.ppm_status_report import PpmStatusReport
from app.models.relation import Relation
from app.models.risk import Risk
from app.models.risk_governance_link import RiskGovernanceLink
from app.models.stakeholder import Stakeholder
from app.models.tech_standard import StandardException, TechStandard
from app.models.todo import Todo
from app.models.user import User
from app.services.executive import periods
from app.services.fiscal_year import get_fiscal_year_start
from app.services.relation_orientation import orient_endpoints
from app.services.seed_markers import demo_seed_completed, mark_demo_seed_completed

SEEDER_KEY = "executive"
VERIFIER_EMAIL = "governance.office@turboea.demo"
PMO_EMAIL = "pmo@turboea.demo"

#: Health of each initiative's latest report, in name order; ``None`` = no report.
HEALTH_MIX = [
    ("onTrack", "onTrack", "onTrack"),
    ("onTrack", "onTrack", "onTrack"),
    ("onTrack", "atRisk", "onTrack"),
    ("onTrack", "onTrack", "onTrack"),
    ("atRisk", "onTrack", "onTrack"),
    ("onTrack", "onTrack", "onTrack"),
    ("offTrack", "atRisk", "onTrack"),
    ("onTrack", "onTrack", "onTrack"),
    ("onTrack", "onTrack", "atRisk"),
    ("onTrack", "onTrack", "onTrack"),
]


def _at(day: date, hour: int = 10) -> datetime:
    return datetime.combine(day, time(hour), tzinfo=timezone.utc)


async def _user(db: AsyncSession, email: str, name: str) -> User:
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        user = User(email=email, display_name=name, password_hash=None, role="member")
        db.add(user)
        await db.flush()
    return user


async def _active(db: AsyncSession, type_key: str) -> list[Card]:
    rows = await db.execute(
        select(Card).where(Card.type == type_key, Card.status == "ACTIVE").order_by(Card.name)
    )
    return list(rows.scalars().all())


async def _relate(db: AsyncSession, rel_type: str, source: Card, target: Card) -> None:
    """Idempotent on (type, source, target), stored in the type's direction."""
    source_id, target_id = await orient_endpoints(db, rel_type, source.id, target.id)
    exists = (
        await db.execute(
            select(Relation.id).where(
                Relation.type == rel_type,
                Relation.source_id == source_id,
                Relation.target_id == target_id,
            )
        )
    ).first()
    if exists is None:
        db.add(Relation(type=rel_type, source_id=source_id, target_id=target_id, attributes={}))


def _transition(db, instrument, record_id, from_status, to_status, actor, when, **extra):
    db.add(
        GovernanceTransition(
            instrument=instrument,
            record_id=record_id,
            from_status=from_status,
            to_status=to_status,
            actor_id=actor.id if actor else None,
            occurred_at=when,
            **extra,
        )
    )


async def seed_executive_demo_data(db: AsyncSession) -> dict:
    if await demo_seed_completed(db, SEEDER_KEY):
        return {"skipped": True, "reason": "already seeded"}
    initiatives = await _active(db, "Initiative")
    if not initiatives:
        return {"skipped": True, "reason": "no initiatives in the landscape"}

    admin = (
        (await db.execute(select(User).where(User.role == "admin").order_by(User.created_at)))
        .scalars()
        .first()
    )
    verifier = await _user(db, VERIFIER_EMAIL, "Demo EA Governance Office")
    pmo = await _user(db, PMO_EMAIL, "Demo PMO Lead")
    actor = admin or pmo

    today = date.today()
    start_month = await get_fiscal_year_start(db)
    fy, quarter = periods.current_quarter(today, start_month)
    current = periods.build(fy, quarter, start_month, today)
    previous = periods.previous(current, start_month, today)
    last_year = periods.build(fy - 1, None, start_month, today)
    q0 = current.start

    def in_quarter(offset: int) -> date:
        """A day this quarter, ``offset`` days in, never today or later."""
        return min(q0 + timedelta(days=offset), today - timedelta(days=1))

    counts: dict[str, int] = {}

    def bump(key: str, n: int = 1) -> None:
        counts[key] = counts.get(key, 0) + n

    # ── Settings: PPM on (delivery is read from status reports) ────────────
    row = (
        await db.execute(select(AppSettings).where(AppSettings.id == "default"))
    ).scalar_one_or_none()
    if row is not None:
        general = dict(row.general_settings or {})
        general["ppmEnabled"] = True
        row.general_settings = general

    # ── Delivery: status reports, budget and cost lines ────────────────────
    for idx, init in enumerate(initiatives[: len(HEALTH_MIX)]):
        schedule, cost, scope = HEALTH_MIX[idx]
        for back, health in ((45, ("onTrack", "onTrack", "onTrack")), (6 + idx, None)):
            s, c, sc = health or (schedule, cost, scope)
            db.add(
                PpmStatusReport(
                    initiative_id=init.id,
                    reporter_id=pmo.id,
                    report_date=today - timedelta(days=back),
                    schedule_health=s,
                    cost_health=c,
                    scope_health=sc,
                    summary="Monthly status report.",
                    accomplishments="Planned milestones for the month delivered.",
                    next_steps="Continue with the next release.",
                )
            )
            bump("status_reports")
        budget = 2_000_000.0 + 250_000.0 * idx
        for category, share in (("capex", 0.6), ("opex", 0.4)):
            db.add(
                PpmBudgetLine(
                    initiative_id=init.id,
                    fiscal_year=fy,
                    category=category,
                    amount=round(budget * share, 2),
                    description=f"FY{fy} {category} budget",
                )
            )
            bump("budget_lines")
        for month_back, share in ((200, 0.2), (120, 0.25), (40, 0.2)):
            spent = today - timedelta(days=month_back)
            if spent.year < q0.year - 1:
                continue
            db.add(
                PpmCostLine(
                    initiative_id=init.id,
                    description="Delivery partner invoice",
                    category="opex" if month_back == 40 else "capex",
                    planned=round(budget * share, 2),
                    actual=round(budget * share * (0.9 + 0.05 * (idx % 4)), 2),
                    date=spent,
                )
            )
            bump("cost_lines")

    # Two extra initiatives with no report: exempt and undetermined (GOV-09).
    extra = []
    for name in ("Records digitisation pilot", "Contact-centre refresh"):
        card = (
            await db.execute(select(Card).where(Card.type == "Initiative", Card.name == name))
        ).scalar_one_or_none()
        if card is None:
            card = Card(type="Initiative", name=name, status="ACTIVE", attributes={})
            db.add(card)
            await db.flush()
        extra.append(card)

    # ── KPI cards: strategic KPIs and the executive metric links ───────────
    async def kpi_card(name: str, attrs: dict) -> Card:
        card = (
            await db.execute(select(Card).where(Card.type == KPI_CARD_TYPE, Card.name == name))
        ).scalar_one_or_none()
        if card is None:
            card = Card(type=KPI_CARD_TYPE, name=name, status="ACTIVE", attributes={})
            db.add(card)
        card.attributes = {**(card.attributes or {}), **attrs}
        card.approval_status = "APPROVED"
        await db.flush()
        return card

    def ratify(card: Card) -> None:
        a = card.attributes or {}
        db.add(
            KpiTargetRatification(
                kpi_card_id=card.id,
                target_value=float(a["targetValue"]),
                target_date=a.get("targetValueDate"),
                baseline_value=float(a["baselineValue"])
                if a.get("baselineValue") is not None
                else None,
                unit=a.get("unit"),
                direction=a.get("direction"),
                ratified_by=verifier.id,
                ratified_at=_at(q0 - timedelta(days=20)),
                note="Target ratified by the accountable executive.",
            )
        )
        db.add(Stakeholder(card_id=card.id, user_id=pmo.id, role="responsible"))
        bump("ratified_targets")

    def measure(
        period: periods.Period,
        value: float,
        *,
        card: Card | None = None,
        metric: str | None = None,
        unit: str | None = None,
        num: float | None = None,
        den: float | None = None,
    ) -> None:
        db.add(
            KpiMeasurement(
                kind="period",
                metric_key=metric,
                kpi_card_id=card.id if card else None,
                period_type="quarter" if period.quarter else "fiscal_year",
                period_key=period.key,
                period_start=period.start,
                period_end=period.end - timedelta(days=1),
                observed_on=min(period.end - timedelta(days=1), today - timedelta(days=1)),
                value=value,
                numerator=num,
                denominator=den,
                unit=unit,
                calculation_version=f"{metric}@1" if metric else None,
                source="system" if metric else "manual",
                evidence=None if metric else "Quarterly measurement from the source system.",
                status="verified",
                recorded_by=None if metric else pmo.id,
                recorded_at=_at(min(period.end, today) - timedelta(days=1), 8),
                verified_by=verifier.id,
                verified_at=_at(min(period.end, today) - timedelta(days=1), 15),
            )
        )
        bump("verified_measurements")

    strategic_kpis = []
    for name, attrs, value in (
        (
            "% transactions via digital channels",
            {"unit": "%", "direction": "higherIsBetter", "targetValue": 92, "baselineValue": 55},
            81.0,
        ),
        (
            "Average CR issuance time",
            {"unit": "hours", "direction": "lowerIsBetter", "targetValue": 4, "baselineValue": 48},
            3.5,
        ),
        (
            "Duplicated systems retired",
            {
                "unit": "systems",
                "direction": "higherIsBetter",
                "targetValue": 6,
                "baselineValue": 0,
            },
            4.0,
        ),
        (
            "Citizen satisfaction with e-services",
            {"unit": "%", "direction": "higherIsBetter", "targetValue": 85, "baselineValue": 70},
            86.5,
        ),
        (
            "Workloads on government cloud",
            {"unit": "%", "direction": "higherIsBetter", "targetValue": 80, "baselineValue": 20},
            62.0,
        ),
    ):
        card = await kpi_card(name, attrs)
        ratify(card)
        measure(current, value, card=card, unit=attrs["unit"])
        measure(
            previous,
            value * 0.95 if attrs["direction"] == "higherIsBetter" else value * 1.1,
            card=card,
            unit=attrs["unit"],
        )
        # The closed previous fiscal year, verified (benefit outcomes, I-72).
        measure(
            last_year,
            value * 0.9 if attrs["direction"] == "higherIsBetter" else value * 1.2,
            card=card,
            unit=attrs["unit"],
        )
        strategic_kpis.append(card)
    # One KPI left with an unratified target, to show the state.
    unratified = await kpi_card(
        "Shared services adoption",
        {"unit": "%", "direction": "higherIsBetter", "targetValue": 60, "baselineValue": 10},
    )
    strategic_kpis.append(unratified)

    metric_cards = {}
    for metric, name, attrs in (
        (
            "TR-03",
            "Initiatives on track",
            {"unit": "%", "direction": "higherIsBetter", "targetValue": 80, "baselineValue": 50},
        ),
        (
            "GOV-05",
            "Decisions implemented on time",
            {"unit": "%", "direction": "higherIsBetter", "targetValue": 75, "baselineValue": 40},
        ),
        (
            "GOV-01",
            "EA review coverage",
            {"unit": "%", "direction": "higherIsBetter", "targetValue": 90, "baselineValue": 30},
        ),
        (
            "RSK-01",
            "Open architecture-related risks",
            {"unit": "risks", "direction": "lowerIsBetter", "targetValue": 3, "baselineValue": 8},
        ),
        (
            "DEC-01",
            "Executive-escalated risks",
            {"unit": "risks", "direction": "lowerIsBetter", "targetValue": 1, "baselineValue": 4},
        ),
    ):
        card = await kpi_card(name, {**attrs, "metricKey": metric})
        ratify(card)
        metric_cards[metric] = card
    # Previous-quarter verified values of the registered metrics (D-19).
    for metric, value, unit, num, den in (
        ("TR-03", 62.5, "percent", 5, 8),
        ("GOV-05", 50.0, "percent", 2, 4),
        ("GOV-01", 40.0, "percent", 2, 5),
        ("RSK-01", 5.0, "count", 5, 6),
        ("DEC-01", 3.0, "count", None, None),
    ):
        measure(previous, value, metric=metric, unit=unit, num=num, den=den)

    # Strategic objectives, their KPIs, pillars untouched; supporting initiatives.
    objectives = await _active(db, "Objective")
    for idx, obj in enumerate(objectives[:5]):
        obj.attributes = {**(obj.attributes or {}), "objectiveType": "strategic"}
        await _relate(db, "relObjectiveToKPI", obj, strategic_kpis[idx % len(strategic_kpis)])
        if idx == 0:
            await _relate(db, "relObjectiveToKPI", obj, strategic_kpis[-1])
        for init in initiatives[idx * 2 : idx * 2 + 2]:
            await _relate(db, "relInitiativeToObjective", init, obj)
        bump("strategic_objectives")

    # ── Governance records with their history (GOV-07) ─────────────────────
    async def adr(
        ref: str, title: str, signed_offset: int, created_back: int
    ) -> ArchitectureDecision:
        rec = (
            await db.execute(
                select(ArchitectureDecision).where(ArchitectureDecision.reference_number == ref)
            )
        ).scalar_one_or_none()
        if rec is None:
            rec = ArchitectureDecision(
                reference_number=ref,
                title=title,
                status="draft",
                context="Recorded to show governance turnaround and implementation.",
                decision=title,
                created_by=actor.id,
            )
            db.add(rec)
        signed = _at(in_quarter(signed_offset), 14)
        created = signed - timedelta(days=created_back)
        rec.created_at = created
        rec.status = "signed"
        rec.signed_at = signed
        rec.signatories = [
            {
                "user_id": str(verifier.id),
                "display_name": verifier.display_name,
                "email": verifier.email,
                "status": "signed",
                "signed_at": signed.isoformat(),
            }
        ]
        await db.flush()
        # Draft is a waiting state (D-39): say whom the wait is attributable to.
        waiting = (
            {"delay_attribution": "requester", "reason": "Sponsor revised the options."}
            if ref == "ADR-D02"
            else {"delay_attribution": "governance"}
        )
        _transition(db, "adr", rec.id, None, "draft", actor, created, **waiting)
        _transition(db, "adr", rec.id, "draft", "in_review", actor, created + timedelta(days=3))
        _transition(db, "adr", rec.id, "in_review", "signed", verifier, signed)
        bump("adrs_signed")
        return rec

    adrs = [
        await adr("ADR-D01", "Adopt the government cloud as the default hosting platform", 3, 21),
        await adr("ADR-D02", "Use the national integration bus for inter-agency exchange", 9, 12),
        await adr("ADR-D03", "Single identity provider for citizen services", 15, 30),
    ]

    async def review(init: Card, status: str, offset: int, created_back: int) -> ArbReview:
        decided = _at(in_quarter(offset), 11)
        created = decided - timedelta(days=created_back)
        rec = ArbReview(
            title=f"Architecture review: {init.name}",
            subject_card_id=init.id,
            summary="Solution architecture reviewed against the target architecture.",
            status=status,
            decision_notes="Conditions recorded in the review minutes."
            if status != "scheduled"
            else None,
            reviewer_id=verifier.id,
            decided_at=decided if status != "scheduled" else None,
            created_by=actor.id,
        )
        db.add(rec)
        await db.flush()
        rec.created_at = created
        _transition(db, "arb", rec.id, None, "scheduled", actor, created)
        if status == "deferred":
            _transition(
                db,
                "arb",
                rec.id,
                "scheduled",
                "deferred",
                verifier,
                decided,
                delay_attribution="requester",
                reason="Awaiting the cost model.",
            )
        elif status != "scheduled":
            _transition(db, "arb", rec.id, "scheduled", status, verifier, decided)
        bump(f"arb_{status}")
        return rec

    # Initiatives in name order: the first five governed (approved review),
    # the next five required but not reviewed (one rejected, one in progress).
    governed = initiatives[:5]
    ungoverned = initiatives[5:10]
    reviews = [
        await review(init, "approved", 2 + 3 * i, 10 + 2 * i) for i, init in enumerate(governed)
    ]
    if ungoverned:
        await review(ungoverned[0], "rejected", 12, 9)
    if len(ungoverned) > 1:
        await review(ungoverned[1], "deferred", 16, 6)

    # EA review applicability (D-37): required for the ten, exempt one, one undetermined.
    for init in governed + ungoverned:
        db.add(
            EaReviewApplicability(
                card_id=init.id,
                decision="required",
                criteria_reference="EA applicability criteria v1 §2 (budget and integration scope)",
                justification="Above the budget threshold and integrates with shared platforms.",
                decided_by=verifier.id,
                decided_at=_at(q0 - timedelta(days=30)),
            )
        )
        bump("applicability_assessments")
    db.add(
        EaReviewApplicability(
            card_id=extra[0].id,
            decision="not_required",
            criteria_reference="EA applicability criteria v1 §3 (pilot exemption)",
            justification="Time-boxed pilot with no integration and below the budget threshold.",
            decided_by=verifier.id,
            decided_at=_at(q0 - timedelta(days=25)),
        )
    )
    bump("applicability_assessments")

    # ── Decision implementation (GOV-05) ───────────────────────────────────
    async def implement(
        kind: str,
        decision_id: uuid.UUID,
        approved: datetime,
        due_offset: int,
        outcome: str,
        title: str,
    ) -> None:
        due = in_quarter(due_offset)
        impl = DecisionImplementation(
            decision_kind=kind,
            decision_id=decision_id,
            due_date=due,
            original_due_date=due,
            due_date_basis="with_decision",
            status="open",
        )
        instrument = f"{kind}_impl"
        db.add(impl)
        db.add(
            GovernanceTransition(
                instrument=instrument,
                record_id=decision_id,
                from_status=None,
                to_status="open",
                actor_id=actor.id,
                occurred_at=approved,
                event_kind="due_date_set",
                due_date=due,
            )
        )
        if outcome == "no_plan":
            return
        completed = outcome in ("verified_on_time", "verified_late", "awaiting")
        action_done = _at(due - timedelta(days=4))
        db.add(
            Todo(
                description=f"Implement: {title}",
                status="done" if completed else "open",
                assigned_to=pmo.id,
                created_by=actor.id,
                due_date=due,
                source_kind=kind,
                source_id=decision_id,
                completion_note="Delivered and in production." if completed else None,
                evidence_refs=[{"kind": "reference", "text": "Change record CHG-4471"}]
                if completed
                else None,
                completed_by=pmo.id if completed else None,
                completed_at=action_done if completed else None,
            )
        )
        bump("decision_actions")
        if not completed:
            return
        submitted = action_done + timedelta(days=1)
        impl.status = "submitted"
        impl.submitted_by = pmo.id
        impl.submitted_at = submitted
        impl.submission_note = "All actions complete with evidence."
        _transition(db, instrument, decision_id, "open", "submitted", pmo, submitted)
        if outcome == "awaiting":
            return
        verified = (
            _at(due - timedelta(days=1))
            if outcome == "verified_on_time"
            else _at(min(due + timedelta(days=6), today - timedelta(days=1)), 16)
        )
        impl.status = "verified"
        impl.verified_by = verifier.id
        impl.verified_at = verified
        impl.attestation = {
            "examined": "Change record and production configuration.",
            "demonstrates": "The decided option is live and the old path retired.",
            "confirmed": True,
            "actions": [],
        }
        _transition(db, instrument, decision_id, "submitted", "verified", verifier, verified)
        bump("decisions_verified")

    plan = [
        ("adr", adrs[0].id, adrs[0].signed_at, 10, "verified_on_time", adrs[0].title),
        ("adr", adrs[1].id, adrs[1].signed_at, 18, "verified_late", adrs[1].title),
        ("adr", adrs[2].id, adrs[2].signed_at, 22, "awaiting", adrs[2].title),
    ]
    for i, rev in enumerate(reviews[:4]):
        outcome = ("verified_on_time", "verified_on_time", "in_progress", "no_plan")[i]
        plan.append(("arb", rev.id, rev.decided_at, 8 + 4 * i, outcome, rev.title))
    for kind, did, approved, due_offset, outcome, title in plan:
        await implement(kind, did, approved, due_offset, outcome, title)

    # ── Standard exceptions through their lifecycle (GOV-04, GOV-07) ───────
    apps = await _active(db, "Application")
    standard = TechStandard(
        name="Legacy on-premise database engine",
        category="data",
        status="sunset",
        description="To be retired in favour of the managed cloud database service.",
        rationale="End of vendor support.",
        owner_id=verifier.id,
    )
    db.add(standard)
    await db.flush()

    async def exception(
        app: Card, story: str, expiry_offset: int, requested_back: int
    ) -> StandardException:
        expiry = in_quarter(expiry_offset)
        requested = _at(expiry - timedelta(days=requested_back))
        approved = requested + timedelta(days=5)
        exc = StandardException(
            standard_id=standard.id,
            card_id=app.id,
            justification="Migration scheduled with the platform upgrade.",
            compensating_controls="Additional monitoring and restricted access.",
            status="requested",
            created_by=actor.id,
        )
        db.add(exc)
        await db.flush()
        exc.created_at = requested
        _transition(db, "exception", exc.id, None, "requested", actor, requested)
        if story == "rejected":
            exc.status = "rejected"
            exc.decided_at = approved
            exc.approver_id = verifier.id
            _transition(
                db,
                "exception",
                exc.id,
                "requested",
                "rejected",
                verifier,
                _at(in_quarter(expiry_offset)),
            )
            return exc
        exc.status = "approved"
        exc.expiry_date = expiry
        exc.decided_at = approved
        exc.approver_id = verifier.id
        _transition(
            db,
            "exception",
            exc.id,
            "requested",
            "approved",
            verifier,
            approved,
            approved_expiry_date=expiry,
        )
        if story in ("on_time", "late", "awaiting"):
            submitted = _at(expiry - timedelta(days=6))
            exc.status = "remediation_submitted"
            exc.remediation_evidence = "Database migrated to the managed service."
            exc.remediation_submitted_by = pmo.id
            exc.remediation_submitted_at = submitted
            _transition(
                db, "exception", exc.id, "approved", "remediation_submitted", pmo, submitted
            )
        if story in ("on_time", "late"):
            verified = (
                _at(expiry - timedelta(days=2))
                if story == "on_time"
                else _at(min(expiry + timedelta(days=5), today - timedelta(days=1)))
            )
            exc.status = "remediated"
            exc.remediation_verified_by = verifier.id
            exc.remediation_verified_at = verified
            exc.remediation_verification_basis = "attested"
            _transition(
                db, "exception", exc.id, "remediation_submitted", "remediated", verifier, verified
            )
        bump(f"exceptions_{story}")
        return exc

    stories = [
        ("on_time", 5, 60),
        ("on_time", 9, 75),
        ("late", 7, 50),
        ("awaiting", 14, 40),
        ("expired", 11, 45),
        ("rejected", 4, 15),
    ]
    exceptions = []
    for i, (story, expiry_offset, back) in enumerate(stories):
        if apps:
            exceptions.append(await exception(apps[i % len(apps)], story, expiry_offset, back))

    # ── Business calendar confirmed for the fiscal year (working days) ─────
    if (
        await db.execute(select(BusinessCalendarYear).where(BusinessCalendarYear.fiscal_year == fy))
    ).scalar_one_or_none() is None:
        db.add(
            BusinessCalendarYear(
                fiscal_year=fy,
                working_weekdays=list(DEFAULT_WORKING_WEEKDAYS),
                holidays=[
                    {"date": f"{fy}-02-22", "name": "Founding Day"},
                    {"date": f"{fy}-09-23", "name": "Saudi National Day"},
                ],
                confirmed=True,
                confirmed_by=verifier.id,
                confirmed_at=_at(date(fy, 1, 5)),
            )
        )
        bump("calendar_years")

    # ── Risks: links to governance records (RSK-01) and escalations (DEC-01) ─
    risks = list(
        (
            await db.execute(
                select(Risk)
                .where(Risk.status.notin_(("closed", "accepted")))
                .order_by(Risk.reference)
            )
        )
        .scalars()
        .all()
    )
    targets = [
        ("adr", adrs[0].id),
        ("adr", adrs[1].id),
        ("arb", reviews[0].id if reviews else None),
    ]
    if exceptions:
        targets.append(("exception", exceptions[3 if len(exceptions) > 3 else 0].id))
    for risk, (instrument, record_id) in zip(risks, targets):
        if record_id is None:
            continue
        db.add(
            RiskGovernanceLink(
                risk_id=risk.id, instrument=instrument, record_id=record_id, created_by=verifier.id
            )
        )
        bump("risk_links")
    for risk, level, overdue in zip(risks[-2:], ("critical", "high"), (False, True)):
        risk.initial_level = level
        risk.residual_level = None
        if overdue:
            risk.target_resolution_date = today - timedelta(days=20)
        bump("escalated_risks")

    await mark_demo_seed_completed(db, SEEDER_KEY)
    await db.commit()
    return {"loaded": True, **counts}
