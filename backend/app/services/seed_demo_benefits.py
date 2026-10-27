"""Benefits register demo data (Phase 4; SEED_DEMO or SEED_NORA).

Seeds a dozen benefits over the initiatives, KPI cards and governance records
the other demo seeders created, so every part of the register has something to
show: each benefit type and status, actuals reported / confirmed / rejected /
reversed, Finance allocations (direct, contributing, an unallocated remainder),
a rationalization decision superseded from the run-rate forecast (D-31),
KPI-measured and qualitatively assessed outcomes, and a benefit with no
governance link.

The benefits are owned and reported by a demo benefit owner and confirmed by a
separate demo Finance officer (D-29), so the signed-in administrator is
independent of every actual and may confirm the one left awaiting Finance. The
two demo users get no password (they cannot sign in) and the ``member`` role:
no Finance role is seeded (D-03).

Runs once per install (``seed_markers``), never inferred from the data.

[FORK]
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_settings import AppSettings
from app.models.arb_review import ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.benefit import Benefit, BenefitLink
from app.models.benefit_actual import BenefitActual, BenefitAllocation
from app.models.benefit_assessment import BenefitAssessment, BenefitHistory
from app.models.card import KPI_CARD_TYPE, Card
from app.models.improvement_opportunity import ImprovementOpportunity
from app.models.rationalization import AssessmentDecision
from app.models.user import User
from app.services.benefits import next_reference
from app.services.fiscal_year import current_fiscal_year, get_fiscal_year_start
from app.services.seed_markers import demo_seed_completed, mark_demo_seed_completed

SEEDER_KEY = "benefits"
DEFAULT_CURRENCY = "USD"

OWNER_EMAIL = "benefits.owner@turboea.demo"
FINANCE_EMAIL = "finance@turboea.demo"


async def _demo_user(db: AsyncSession, email: str, name: str) -> User:
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        user = User(
            email=email,
            display_name=name,
            password_hash=None,
            role="member",
            is_active=True,
        )
        db.add(user)
        await db.flush()
    return user


async def _cards(db: AsyncSession, type_key: str, limit: int) -> list[Card]:
    rows = await db.execute(
        select(Card)
        .where(Card.type == type_key, Card.status == "ACTIVE")
        .order_by(Card.name)
        .limit(limit)
    )
    return list(rows.scalars().all())


async def _first(db: AsyncSession, stmt) -> Any:
    return (await db.execute(stmt.limit(1))).scalars().first()


async def seed_benefits_demo_data(db: AsyncSession) -> dict:
    if await demo_seed_completed(db, SEEDER_KEY):
        return {"skipped": True, "reason": "already seeded"}

    initiatives = await _cards(db, "Initiative", 4)
    if not initiatives:
        return {"skipped": True, "reason": "no initiatives to attach benefits to"}
    while len(initiatives) < 3:
        initiatives.append(initiatives[0])
    i0, i1, i2 = initiatives[0], initiatives[1], initiatives[2]
    kpis = await _cards(db, KPI_CARD_TYPE, 2)
    apps = await _cards(db, "Application", 3)

    adr = await _first(
        db,
        select(ArchitectureDecision)
        .where(ArchitectureDecision.status == "signed")
        .order_by(ArchitectureDecision.reference_number),
    )
    arb = await _first(
        db, select(ArbReview).where(ArbReview.status == "approved").order_by(ArbReview.title)
    )
    rationalization = await _first(
        db,
        select(AssessmentDecision)
        .where(AssessmentDecision.planned_savings.is_not(None))
        .order_by(AssessmentDecision.planned_savings.desc()),
    )
    opportunity = await _first(
        db, select(ImprovementOpportunity).order_by(ImprovementOpportunity.title)
    )

    settings_row = (
        await db.execute(select(AppSettings).where(AppSettings.id == "default"))
    ).scalar_one_or_none()
    currency = ((settings_row.general_settings if settings_row else None) or {}).get(
        "currency"
    ) or DEFAULT_CURRENCY
    fy = current_fiscal_year(await get_fiscal_year_start(db))
    prev = fy - 1

    owner = await _demo_user(db, OWNER_EMAIL, "Demo Benefit Owner")
    finance = await _demo_user(db, FINANCE_EMAIL, "Demo Finance Officer")
    now = datetime.now(timezone.utc)

    def ago(days: int) -> datetime:
        return now - timedelta(days=days)

    counts = {"benefits": 0, "actuals": 0, "allocations": 0, "assessments": 0}

    async def benefit(
        title: str,
        benefit_type: str,
        measurement: str,
        *,
        description: str,
        status: str = "planned",
        initiatives_: list[tuple[Card, str]] = (),
        affected: list[Card] = (),
        decision: tuple[str, uuid.UUID] | None = None,
        kpi: Card | None = None,
        basis: dict | None = None,
        validated_days: int | None = None,
        close: tuple[str, str] | None = None,
        created_days: int = 120,
    ) -> Benefit:
        b = Benefit(
            reference=await next_reference(db),
            title=title,
            description=description,
            benefit_type=benefit_type,
            measurement=measurement,
            status=status,
            owner_id=owner.id,
            decision_kind=decision[0] if decision else None,
            decision_id=decision[1] if decision else None,
            kpi_card_id=kpi.id if kpi else None,
            created_by=owner.id,
            estimated_by=owner.id if basis and basis.get("planned_amount") is not None else None,
            **({"currency": currency} if basis else {}),
            **(basis or {}),
        )
        if validated_days is not None:
            b.validated_by = finance.id
            b.validated_at = ago(validated_days)
            b.validation_note = "Method, baseline and planned amount agreed with Finance."
        if close is not None:
            b.closed_by = finance.id if close[0] == "not_realised" else owner.id
            b.closed_at = ago(10)
            b.close_reason = close[1]
        db.add(b)
        await db.flush()
        seen: set[uuid.UUID] = set()
        for card, cls in initiatives_:
            if card.id in seen:
                continue
            seen.add(card.id)
            db.add(
                BenefitLink(benefit_id=b.id, card_id=card.id, role="initiative", classification=cls)
            )
        for card in affected:
            db.add(BenefitLink(benefit_id=b.id, card_id=card.id, role="affected"))
        history(b, "created", owner, created_days, to_status="planned")
        if validated_days is not None:
            history(b, "validated", finance, validated_days, "planned", "validated")
        if close is not None:
            history(
                b,
                close[0],
                finance if close[0] == "not_realised" else owner,
                10,
                "validated" if validated_days is not None else "planned",
                close[0],
                note=close[1],
            )
        counts["benefits"] += 1
        return b

    def history(
        b: Benefit,
        action: str,
        actor: User,
        days: int,
        from_status: str | None = None,
        to_status: str | None = None,
        *,
        note: str | None = None,
        changes: dict | None = None,
    ) -> None:
        db.add(
            BenefitHistory(
                benefit_id=b.id,
                action=action,
                from_status=from_status,
                to_status=to_status,
                note=note,
                changes=changes,
                actor_id=actor.id,
                occurred_at=ago(days),
            )
        )

    async def actual(
        b: Benefit,
        year: int,
        amount: float,
        status: str,
        *,
        reported_days: int,
        evidence: str,
        allocations: list[tuple[Card, str, float, str]] = (),
        reason: str | None = None,
    ) -> BenefitActual:
        a = BenefitActual(
            benefit_id=b.id,
            fiscal_year=year,
            amount=amount,
            status=status,
            reported_by=owner.id,
            reported_at=ago(reported_days),
            report_note=f"Realised in FY{year}, from the finance system extract.",
            evidence_refs=[{"kind": "reference", "text": evidence}],
        )
        history(
            b,
            "actual_reported",
            owner,
            reported_days,
            to_status="reported",
            changes={
                "fiscal_year": {"old": None, "new": year},
                "amount": {"old": None, "new": amount},
            },
        )
        if status in ("confirmed", "rejected", "reversed"):
            a.decided_by = finance.id
            a.decided_at = ago(reported_days - 5)
            if status == "rejected":
                a.decision_note = reason
                history(
                    b,
                    "actual_rejected",
                    finance,
                    reported_days - 5,
                    "reported",
                    "rejected",
                    note=reason,
                )
            else:
                a.finance_reference = f"FIN-{year}-{counts['actuals'] + 101:05d}"
                history(
                    b,
                    "actual_confirmed",
                    finance,
                    reported_days - 5,
                    "reported",
                    "confirmed",
                    changes={
                        "fiscal_year": {"old": None, "new": year},
                        "amount": {"old": None, "new": amount},
                    },
                )
        if status == "reversed":
            a.reversed_by = finance.id
            a.reversed_at = ago(reported_days - 20)
            a.reverse_reason = reason
            history(
                b,
                "actual_reversed",
                finance,
                reported_days - 20,
                "confirmed",
                "reversed",
                note=reason,
            )
        db.add(a)
        await db.flush()
        for card, cls, value, rationale in allocations:
            db.add(
                BenefitAllocation(
                    actual_id=a.id,
                    card_id=card.id,
                    classification=cls,
                    amount=value,
                    rationale=rationale,
                )
            )
            counts["allocations"] += 1
        counts["actuals"] += 1
        return a

    # 1. Cost saving, validated, a confirmed actual last year with Finance's
    #    allocations (direct + contributing + an unallocated remainder) and
    #    this year's actual awaiting Finance.
    b1 = await benefit(
        "Licence consolidation on the ERP platform",
        "cost_saving",
        "financial",
        description="Retire overlapping finance and procurement licences once the ERP "
        "consolidation completes.",
        status="validated",
        initiatives_=[(i0, "direct"), (i1, "contributing")],
        affected=apps[:2],
        decision=("adr", adr.id) if adr else None,
        basis={
            "recurrence": "annual",
            "planned_amount": 1_200_000.0,
            "baseline_amount": 3_000_000.0,
            "method_note": "Annual licence and support cost of the retired products, from "
            "the vendor contracts, less the added ERP licences.",
            "expected_fiscal_year": fy,
        },
        validated_days=100,
    )
    await actual(
        b1,
        prev,
        400_000.0,
        "confirmed",
        reported_days=60,
        evidence="ERP journal JV-48211 (licence termination credit)",
        allocations=[
            (i0, "direct", 250_000.0, "The consolidation retired the licences directly."),
            (i1, "contributing", 100_000.0, "Data migration enabled the early termination."),
        ],
    )
    await actual(
        b1,
        fy,
        450_000.0,
        "reported",
        reported_days=7,
        evidence="Procurement report PR-2291: contracts not renewed this year",
    )

    # 2. Cost avoidance with a counterfactual, confirmed this year.
    b2 = await benefit(
        "Avoided data-centre extension",
        "cost_avoidance",
        "financial",
        description="Moving workloads to the government cloud avoided the planned "
        "data-centre extension.",
        status="validated",
        initiatives_=[(i2, "direct")],
        decision=("arb", arb.id) if arb else None,
        basis={
            "recurrence": "one_time",
            "planned_amount": 800_000.0,
            "counterfactual_amount": 800_000.0,
            "counterfactual_note": "Capital cost of the rejected data-centre extension "
            "option in the architecture review.",
            "method_note": "Counterfactual taken from the approved review's costed options.",
            "expected_fiscal_year": fy,
        },
        validated_days=90,
    )
    await actual(
        b2,
        fy,
        750_000.0,
        "confirmed",
        reported_days=30,
        evidence="Capital plan revision CP-2026-07 (extension removed)",
        allocations=[
            (i2, "direct", 600_000.0, "The cloud migration made the extension unnecessary.")
        ],
    )

    # 3. Revenue, validated: this year's first actual rejected by Finance, then
    #    re-reported and confirmed (the current year's FIN-01 cash value).
    b3 = await benefit(
        "Online service fee collection",
        "revenue",
        "financial",
        description="New e-payment channel collects service fees previously waived.",
        status="validated",
        initiatives_=[(i1, "contributing")],
        decision=("adr", adr.id) if adr else None,
        basis={
            "recurrence": "annual",
            "planned_amount": 500_000.0,
            "method_note": "Fee schedule × expected transactions.",
            "expected_fiscal_year": fy,
        },
        validated_days=80,
    )
    await actual(
        b3,
        fy,
        320_000.0,
        "rejected",
        reported_days=25,
        evidence="Payment gateway monthly statements",
        reason="Includes fees collected before the new channel went live.",
    )
    await actual(
        b3,
        fy,
        280_000.0,
        "confirmed",
        reported_days=18,
        evidence="Payment gateway statements from the go-live date only",
        allocations=[
            (i1, "contributing", 100_000.0, "The payment integration was one of three enablers.")
        ],
    )

    # 4. A rationalization decision named by a benefit: its planned savings
    #    leave the run-rate forecast (D-31, I-71). Still planned.
    rd_amount = float(rationalization.planned_savings) if rationalization else 300_000.0
    await benefit(
        "Application rationalization saving",
        "cost_saving",
        "financial",
        description="Savings from the TIME decision, now tracked in the register.",
        initiatives_=[(i0, "contributing")],
        decision=("rationalization", rationalization.id) if rationalization else None,
        basis={
            "recurrence": "annual",
            "planned_amount": rd_amount,
            "method_note": "Planned savings carried over from the rationalization decision.",
            "expected_fiscal_year": fy + 1,
        },
    )

    # 5. Validated; last year's confirmation reversed after an audit.
    b5 = await benefit(
        "Shared printing service",
        "cost_saving",
        "financial",
        description="Central print service replaces departmental printers.",
        status="validated",
        initiatives_=[(i2, "contributing")],
        decision=("arb", arb.id) if arb else None,
        basis={
            "recurrence": "annual",
            "planned_amount": 150_000.0,
            "baseline_amount": 420_000.0,
            "method_note": "Departmental printer leases and consumables.",
            "expected_fiscal_year": prev,
        },
        validated_days=200,
    )
    await actual(
        b5,
        prev,
        140_000.0,
        "reversed",
        reported_days=120,
        evidence="Lease termination letters",
        reason="Audit found two leases were extended, not terminated; to be re-reported.",
    )

    # 6. Withdrawn.
    await benefit(
        "Mainframe hosting saving",
        "cost_saving",
        "financial",
        description="Planned exit from the mainframe hosting contract.",
        status="withdrawn",
        initiatives_=[(i1, "direct")],
        basis={"recurrence": "annual", "planned_amount": 900_000.0},
        close=("withdrawn", "The mainframe exit was descoped from the programme."),
    )

    # 7. Validated, then closed as not realised.
    await benefit(
        "Partner data resale revenue",
        "revenue",
        "financial",
        description="Revenue from selling anonymised datasets to partners.",
        status="not_realised",
        initiatives_=[(i2, "not_attributable")],
        decision=("adr", adr.id) if adr else None,
        basis={
            "recurrence": "annual",
            "planned_amount": 250_000.0,
            "method_note": "Partner demand survey.",
            "expected_fiscal_year": prev,
        },
        validated_days=300,
        close=("not_realised", "Data-sharing regulation prevented the resale."),
    )

    # 8. No governance link: an initiative only, still planned.
    await benefit(
        "Faster procurement cycle saving",
        "cost_saving",
        "financial",
        description="Shorter procurement cycle reduces expediting costs.",
        initiatives_=[(i0, "contributing")],
        basis={"recurrence": "annual", "planned_amount": 120_000.0, "expected_fiscal_year": fy},
    )

    # 9–12. Non-financial outcomes (D-43): KPI-measured and assessed.
    await benefit(
        "Shorter service request turnaround",
        "productivity",
        "kpi" if kpis else "qualitative",
        description="Staff hours saved by automating service request triage.",
        initiatives_=[(i2, "contributing")],
        kpi=kpis[0] if kpis else None,
        decision=("arb", arb.id) if arb else None,
    )
    if len(kpis) > 1:
        await benefit(
            "Higher citizen satisfaction with digital services",
            "non_financial",
            "kpi",
            description="Satisfaction measured by the digital services survey.",
            initiatives_=[(i0, "direct")],
            kpi=kpis[1],
        )
    b11 = await benefit(
        "Better cross-agency data sharing",
        "non_financial",
        "qualitative",
        description="Agencies reuse shared master data instead of re-collecting it.",
        initiatives_=[(i0, "direct"), (i1, "contributing")],
        decision=("opportunity", opportunity.id) if opportunity else None,
    )
    for year, outcome, days, note in (
        (prev, "partially_achieved", 200, "Two of five agencies consume the shared registry."),
        (fy, "achieved", 15, "All five agencies consume the shared registry."),
    ):
        db.add(
            BenefitAssessment(
                benefit_id=b11.id,
                fiscal_year=year,
                outcome=outcome,
                note=note,
                evidence_refs=[{"kind": "reference", "text": f"Registry access log FY{year}"}],
                assessed_by=owner.id,
                assessed_at=ago(days),
            )
        )
        history(
            b11,
            "assessed",
            owner,
            days,
            note=note,
            changes={
                "outcome": {"old": None, "new": outcome},
                "fiscal_year": {"old": None, "new": year},
            },
        )
        counts["assessments"] += 1
    await benefit(
        "Reduced manual reconciliation effort",
        "productivity",
        "qualitative",
        description="Finance staff spend less time on manual reconciliations.",
        initiatives_=[(i1, "contributing")],
    )

    await mark_demo_seed_completed(db, SEEDER_KEY)
    await db.commit()
    return {"loaded": True, **counts}
