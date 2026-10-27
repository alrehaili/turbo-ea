"""Benefits register rules (D-12, D-14, D-29, D-31, D-43; Phase 4 Batch 4.1).

* **Benefit**: ``planned`` → ``validated`` (financial only, by
  ``benefits.validate``), or closed as ``not_realised`` / ``withdrawn`` with a
  reason. Validation locks the financial basis; reopening returns it to
  ``planned`` with a reason. Type and measurement never change after creation.
* **Actuals** (financial benefits, I-67): ``reported`` with evidence →
  ``confirmed`` (Finance reference) or ``rejected``; a confirmed actual may be
  ``reversed``. Whoever confirms, rejects or reverses must be independent of
  the benefit (creator, owner, estimator) and of the actual (its reporter) —
  403 ``self_confirmation`` for everyone, administrators included (D-29).
* **Attribution** (D-14, I-68): each initiative link is ``direct``,
  ``contributing`` or ``not_attributable``. Only Finance allocates money, when
  confirming an actual, each amount with a rationale; one actual's allocations
  never exceed it, and nothing is allocated automatically.
* **Outcomes** (D-43): productivity and non-financial benefits carry no amount.
  A KPI-measured one is judged from the KPI's verified measurement (reports);
  a qualitative one by append-only assessments, labelled *assessed*.

Every change appends a ``benefit_history`` row and publishes ``benefit.*``
with ``db=``. Helpers flush at most and never commit.

[FORK]
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.arb_review import ArbReview
from app.models.architecture_decision import ArchitectureDecision
from app.models.benefit import (
    ALLOCATABLE,
    CLASSIFICATIONS,
    CLOSED_STATUSES,
    COST_AVOIDANCE,
    COST_SAVING,
    DECISION_ADR,
    DECISION_ARB,
    DECISION_KINDS,
    DECISION_OPPORTUNITY,
    DECISION_RATIONALIZATION,
    FINANCIAL_TYPES,
    MEASUREMENT_FINANCIAL,
    MEASUREMENT_KPI,
    MEASUREMENT_QUALITATIVE,
    OUTCOME_TYPES,
    RECURRENCES,
    ROLE_AFFECTED,
    ROLE_INITIATIVE,
    STATUS_NOT_REALISED,
    STATUS_PLANNED,
    STATUS_VALIDATED,
    STATUS_WITHDRAWN,
    Benefit,
    BenefitLink,
)
from app.models.benefit_actual import (
    CONFIRMED,
    LIVE_STATUSES,
    REJECTED,
    REPORTED,
    REVERSED,
    BenefitActual,
    BenefitAllocation,
)
from app.models.benefit_assessment import OUTCOMES, BenefitAssessment, BenefitHistory
from app.models.card import KPI_CARD_TYPE, Card
from app.models.improvement_opportunity import ImprovementOpportunity
from app.models.rationalization import AssessmentDecision
from app.services.card_read_scope import CardReadScope
from app.services.decision_implementation import resolve_evidence
from app.services.event_bus import event_bus
from app.services.governance_transitions import LifecycleError

VIEW_PERMISSION = "benefits.view"
MANAGE_PERMISSION = "benefits.manage"
VALIDATE_PERMISSION = "benefits.validate"
CONFIRM_PERMISSION = "benefits.confirm"
#: Every amount additionally needs the existing cost permission (I-66).
COSTS_PERMISSION = "costs.view"

#: The module permission that shows a governing decision (I-73).
DECISION_VIEW_PERMISSION = {
    DECISION_ADR: "adr.view",
    DECISION_ARB: "arb.view",
    DECISION_RATIONALIZATION: "rationalization.view",
    DECISION_OPPORTUNITY: "grc.view",
}

INITIATIVE_TYPE = "Initiative"
MAX_TITLE = 300
MAX_FINANCE_REFERENCE = 200
MIN_FISCAL_YEAR = 2000
MAX_FISCAL_YEAR = 2100
#: Rounding tolerance when comparing summed allocations with an actual.
CENT = 0.005

_CURRENCY = re.compile(r"^[A-Z]{3}$")
_REFERENCE = re.compile(r"^B-(\d+)$")

#: Fields of the financial basis, locked once the benefit is validated.
BASIS_FIELDS = (
    "currency",
    "recurrence",
    "planned_amount",
    "baseline_amount",
    "counterfactual_amount",
    "counterfactual_note",
    "method_note",
    "expected_fiscal_year",
)
#: Fields editable on any open benefit.
GENERAL_FIELDS = ("title", "description", "owner_id", "decision_kind", "decision_id", "kpi_card_id")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _amount(value: Any, code: str, *, positive: bool = False) -> float | None:
    if value is None:
        return None
    try:
        number = round(float(value), 2)
    except (TypeError, ValueError):
        raise LifecycleError(422, code, "Amounts must be numbers") from None
    if number < 0 or (positive and number <= 0):
        raise LifecycleError(422, code, "Amounts must be positive")
    return number


def _fiscal_year(value: Any, *, required: bool, code: str = "invalid_fiscal_year") -> int | None:
    if value is None:
        if required:
            raise LifecycleError(422, code, "A fiscal year is required")
        return None
    try:
        year = int(value)
    except (TypeError, ValueError):
        raise LifecycleError(422, code, "A fiscal year is a year") from None
    if not MIN_FISCAL_YEAR <= year <= MAX_FISCAL_YEAR:
        raise LifecycleError(422, code, "The fiscal year is out of range")
    return year


def is_financial(benefit: Benefit) -> bool:
    return benefit.measurement == MEASUREMENT_FINANCIAL


def is_open(benefit: Benefit) -> bool:
    return benefit.status not in CLOSED_STATUSES


async def next_reference(db: AsyncSession) -> str:
    """The next monotonic ``B-NNNNNN`` reference (as risks' ``R-NNNNNN``)."""
    highest = 0
    for (ref,) in (await db.execute(select(Benefit.reference))).all():
        match = _REFERENCE.match(ref or "")
        if match:
            highest = max(highest, int(match.group(1)))
    return f"B-{highest + 1:06d}"


# ── History (I-75) ───────────────────────────────────────────────────────


async def record(
    db: AsyncSession,
    benefit: Benefit,
    action: str,
    actor_id: uuid.UUID | None,
    *,
    from_status: str | None = None,
    to_status: str | None = None,
    note: str | None = None,
    changes: dict | None = None,
) -> BenefitHistory:
    """Append one history row and publish ``benefit.<action>`` with ``db=``.

    ``changes`` holds labels and amounts only, never an id."""
    row = BenefitHistory(
        benefit_id=benefit.id,
        action=action,
        from_status=from_status,
        to_status=to_status,
        note=note,
        changes=changes or None,
        actor_id=actor_id,
        occurred_at=_now(),
    )
    db.add(row)
    await event_bus.publish(
        f"benefit.{action}",
        {
            "benefit_id": str(benefit.id),
            "reference": benefit.reference,
            "from_status": from_status,
            "to_status": to_status,
        },
        db=db,
        user_id=actor_id,
    )
    return row


# ── Loading ─────────────────────────────────────────────────────────────


@dataclass
class BenefitBundle:
    benefit: Benefit
    links: list[BenefitLink] = field(default_factory=list)
    actuals: list[BenefitActual] = field(default_factory=list)
    allocations: dict[uuid.UUID, list[BenefitAllocation]] = field(default_factory=dict)
    assessments: list[BenefitAssessment] = field(default_factory=list)

    def card_ids(self) -> set[uuid.UUID]:
        ids = {link.card_id for link in self.links}
        if self.benefit.kpi_card_id:
            ids.add(self.benefit.kpi_card_id)
        return ids

    def linked_ids(self) -> set[uuid.UUID]:
        """Initiatives and affected cards — where evidence may live (I-69)."""
        return {link.card_id for link in self.links}

    def initiative_links(self) -> dict[uuid.UUID, BenefitLink]:
        return {lk.card_id: lk for lk in self.links if lk.role == ROLE_INITIATIVE}

    def live_actual(self, fiscal_year: int) -> BenefitActual | None:
        for a in self.actuals:
            if a.fiscal_year == fiscal_year and a.status in LIVE_STATUSES:
                return a
        return None


async def load_bundles(db: AsyncSession, benefits: Sequence[Benefit]) -> list[BenefitBundle]:
    """Each benefit with its links, actuals, allocations and assessments."""
    bundles = {b.id: BenefitBundle(b) for b in benefits}
    if not bundles:
        return []
    ids = list(bundles)
    for link in (
        await db.execute(select(BenefitLink).where(BenefitLink.benefit_id.in_(ids)))
    ).scalars():
        bundles[link.benefit_id].links.append(link)
    actuals = (
        (
            await db.execute(
                select(BenefitActual)
                .where(BenefitActual.benefit_id.in_(ids))
                .order_by(BenefitActual.fiscal_year.desc(), BenefitActual.reported_at.desc())
            )
        )
        .scalars()
        .all()
    )
    by_actual: dict[uuid.UUID, BenefitBundle] = {}
    for a in actuals:
        bundles[a.benefit_id].actuals.append(a)
        by_actual[a.id] = bundles[a.benefit_id]
    if by_actual:
        for alloc in (
            await db.execute(
                select(BenefitAllocation).where(BenefitAllocation.actual_id.in_(list(by_actual)))
            )
        ).scalars():
            by_actual[alloc.actual_id].allocations.setdefault(alloc.actual_id, []).append(alloc)
    for row in (
        await db.execute(
            select(BenefitAssessment)
            .where(BenefitAssessment.benefit_id.in_(ids))
            .order_by(BenefitAssessment.assessed_at.desc(), BenefitAssessment.id)
        )
    ).scalars():
        bundles[row.benefit_id].assessments.append(row)
    return [bundles[b.id] for b in benefits]


async def visible_bundles(
    db: AsyncSession, read_scope: CardReadScope, bundles: Iterable[BenefitBundle]
) -> tuple[list[BenefitBundle], set[uuid.UUID]]:
    """The benefits the reader may see, and the readable card ids among them.

    A benefit that links cards is visible only when at least one linked card is
    readable (I-66, as S-12): one about hidden cards only is omitted."""
    bundles = list(bundles)
    all_ids = {cid for b in bundles for cid in b.card_ids()}
    readable = await read_scope.readable_card_ids(db, all_ids, mode="module")
    visible = []
    for b in bundles:
        linked = b.linked_ids()
        if linked and not (linked & readable):
            continue
        visible.append(b)
    return visible, readable


# ── Validation of inputs ─────────────────────────────────────────────────


async def check_decision(db: AsyncSession, kind: str | None, decision_id: Any) -> uuid.UUID | None:
    """A governing decision (I-73): a signed ADR, an approved ARB review, a
    rationalization decision or an improvement opportunity that exists."""
    if kind is None and decision_id is None:
        return None
    if kind not in DECISION_KINDS:
        raise LifecycleError(422, "invalid_decision", f"Unknown decision kind: {kind!r}")
    try:
        did = uuid.UUID(str(decision_id))
    except ValueError:
        raise LifecycleError(422, "invalid_decision", "A decision id is required") from None
    model = {
        DECISION_ADR: ArchitectureDecision,
        DECISION_ARB: ArbReview,
        DECISION_RATIONALIZATION: AssessmentDecision,
        DECISION_OPPORTUNITY: ImprovementOpportunity,
    }[kind]
    row = await db.get(model, did)
    approved = row is not None and (
        (kind == DECISION_ADR and row.status == "signed")
        or (kind == DECISION_ARB and row.status == "approved")
        or kind in (DECISION_RATIONALIZATION, DECISION_OPPORTUNITY)
    )
    if not approved:
        raise LifecycleError(
            422,
            "invalid_decision",
            "The decision must exist (a signed ADR or an approved ARB review)",
        )
    return did


async def check_cards(
    db: AsyncSession,
    read_scope: CardReadScope,
    ids: Iterable[Any],
    *,
    type_key: str | None,
    code: str,
) -> list[uuid.UUID]:
    """Readable, active cards (of ``type_key`` when given); 422 otherwise."""
    out: list[uuid.UUID] = []
    for raw in ids:
        try:
            cid = uuid.UUID(str(raw))
        except ValueError:
            raise LifecycleError(422, code, "Unknown card") from None
        if cid in out:
            continue
        card = await db.get(Card, cid)
        if (
            card is None
            or card.status != "ACTIVE"
            or (type_key is not None and card.type != type_key)
            or not await read_scope.readable_card_ids(db, [cid], mode="module")
        ):
            raise LifecycleError(422, code, "Unknown card")
        out.append(cid)
    return out


def _check_type(benefit_type: str | None, measurement: str | None) -> str:
    if benefit_type in FINANCIAL_TYPES:
        if measurement not in (None, MEASUREMENT_FINANCIAL):
            raise LifecycleError(
                422, "invalid_measurement", "A financial benefit is measured in money"
            )
        return MEASUREMENT_FINANCIAL
    if benefit_type in OUTCOME_TYPES:
        if measurement not in (MEASUREMENT_KPI, MEASUREMENT_QUALITATIVE):
            raise LifecycleError(
                422,
                "invalid_measurement",
                "A non-financial benefit is measured by a KPI or assessed qualitatively",
            )
        return measurement
    raise LifecycleError(422, "invalid_type", f"Unknown benefit type: {benefit_type!r}")


def _basis(measurement: str, data: dict) -> dict[str, Any]:
    """The financial basis from the request; none at all for an outcome (D-43)."""
    present = {k for k in BASIS_FIELDS if data.get(k) is not None}
    if measurement != MEASUREMENT_FINANCIAL:
        money = present & {"currency", "planned_amount", "baseline_amount", "counterfactual_amount"}
        if money:
            raise LifecycleError(
                422, "outcome_not_monetised", "A non-financial benefit carries no amount"
            )
        return {k: None for k in BASIS_FIELDS}
    currency = _text(data.get("currency"))
    currency = currency.upper() if currency else None
    if currency is None or not _CURRENCY.match(currency):
        raise LifecycleError(
            422, "currency_required", "A financial benefit needs its ISO 4217 currency"
        )
    recurrence = data.get("recurrence")
    if recurrence not in RECURRENCES:
        raise LifecycleError(422, "invalid_recurrence", "Say whether it is one-time or annual")
    return {
        "currency": currency,
        "recurrence": recurrence,
        "planned_amount": _amount(data.get("planned_amount"), "invalid_amount"),
        "baseline_amount": _amount(data.get("baseline_amount"), "invalid_amount"),
        "counterfactual_amount": _amount(data.get("counterfactual_amount"), "invalid_amount"),
        "counterfactual_note": _text(data.get("counterfactual_note")),
        "method_note": _text(data.get("method_note")),
        "expected_fiscal_year": _fiscal_year(data.get("expected_fiscal_year"), required=False),
    }


async def _set_links(
    db: AsyncSession,
    read_scope: CardReadScope,
    benefit: Benefit,
    existing: list[BenefitLink],
    initiatives: list[dict] | None,
    affected: list[Any] | None,
) -> list[BenefitLink]:
    """Replace the links the caller sent; links to cards the caller cannot read
    are kept as they are (a replace-set write keeps what was never shown)."""
    hidden = await read_scope.hidden_card_ids(db, [lk.card_id for lk in existing], mode="module")
    kept = [lk for lk in existing if lk.card_id in hidden]
    result = list(kept)
    if initiatives is None:
        result += [lk for lk in existing if lk.role == ROLE_INITIATIVE and lk not in kept]
    else:
        classes: dict[str, str] = {}
        for item in initiatives:
            cls = item.get("classification")
            if cls not in CLASSIFICATIONS:
                raise LifecycleError(
                    422,
                    "invalid_classification",
                    "Classify each initiative as direct, contributing or not attributable",
                )
            classes[str(item.get("card_id"))] = cls
        ids = await check_cards(
            db, read_scope, classes, type_key=INITIATIVE_TYPE, code="invalid_initiative"
        )
        current = {lk.card_id: lk for lk in existing if lk.role == ROLE_INITIATIVE}
        for cid in ids:
            link = current.get(cid) or BenefitLink(
                benefit_id=benefit.id, card_id=cid, role=ROLE_INITIATIVE
            )
            link.classification = classes[str(cid)]
            db.add(link)
            result.append(link)
    if affected is None:
        result += [lk for lk in existing if lk.role == ROLE_AFFECTED and lk not in kept]
    else:
        ids = await check_cards(db, read_scope, affected, type_key=None, code="invalid_card")
        current = {lk.card_id: lk for lk in existing if lk.role == ROLE_AFFECTED}
        for cid in ids:
            link = current.get(cid) or BenefitLink(
                benefit_id=benefit.id, card_id=cid, role=ROLE_AFFECTED
            )
            db.add(link)
            result.append(link)
    keep_ids = {id(lk) for lk in result}
    for lk in existing:
        if id(lk) not in keep_ids:
            await db.delete(lk)
    return result


def _require_governance_anchor(benefit: Benefit, links: list[BenefitLink]) -> None:
    if benefit.decision_kind is None and not any(lk.role == ROLE_INITIATIVE for lk in links):
        raise LifecycleError(
            422,
            "anchor_required",
            "Name the governing decision or at least one delivering initiative",
        )


async def _check_kpi(
    db: AsyncSession, read_scope: CardReadScope, measurement: str, kpi_card_id: Any
) -> uuid.UUID | None:
    if measurement != MEASUREMENT_KPI:
        if kpi_card_id is not None:
            raise LifecycleError(422, "invalid_kpi", "Only a KPI-measured outcome names a KPI")
        return None
    if kpi_card_id is None:
        raise LifecycleError(422, "kpi_required", "A KPI-measured outcome needs its KPI card")
    (cid,) = await check_cards(
        db, read_scope, [kpi_card_id], type_key=KPI_CARD_TYPE, code="invalid_kpi"
    )
    return cid


# ── Create and edit ─────────────────────────────────────────────────────


async def create_benefit(
    db: AsyncSession, read_scope: CardReadScope, data: dict, actor_id: uuid.UUID
) -> BenefitBundle:
    title = _text(data.get("title"))
    if title is None or len(title) > MAX_TITLE:
        raise LifecycleError(422, "title_required", "A title of at most 300 characters")
    measurement = _check_type(data.get("benefit_type"), data.get("measurement"))
    basis = _basis(measurement, data)
    benefit = Benefit(
        reference=await next_reference(db),
        title=title,
        description=_text(data.get("description")),
        benefit_type=data["benefit_type"],
        measurement=measurement,
        status=STATUS_PLANNED,
        owner_id=data.get("owner_id") or actor_id,
        decision_kind=data.get("decision_kind"),
        decision_id=await check_decision(db, data.get("decision_kind"), data.get("decision_id")),
        kpi_card_id=await _check_kpi(db, read_scope, measurement, data.get("kpi_card_id")),
        created_by=actor_id,
        estimated_by=actor_id if basis.get("planned_amount") is not None else None,
        **basis,
    )
    db.add(benefit)
    await db.flush()
    links = await _set_links(
        db, read_scope, benefit, [], data.get("initiatives") or [], data.get("affected") or []
    )
    _require_governance_anchor(benefit, links)
    await db.flush()
    await record(db, benefit, "created", actor_id, to_status=STATUS_PLANNED)
    return BenefitBundle(benefit, links)


def _change(changes: dict, name: str, old: Any, new: Any) -> None:
    if old != new:
        changes[name] = {"old": old, "new": new}


async def update_benefit(
    db: AsyncSession,
    read_scope: CardReadScope,
    bundle: BenefitBundle,
    data: dict,
    actor_id: uuid.UUID,
    *,
    owner_names: dict[uuid.UUID, str] | None = None,
) -> BenefitBundle:
    """Edit an open benefit. The financial basis only while ``planned``."""
    benefit = bundle.benefit
    if not is_open(benefit):
        raise LifecycleError(409, "benefit_closed", "A closed benefit is not edited")
    changes: dict[str, Any] = {}
    if "title" in data:
        title = _text(data["title"])
        if title is None or len(title) > MAX_TITLE:
            raise LifecycleError(422, "title_required", "A title of at most 300 characters")
        _change(changes, "title", benefit.title, title)
        benefit.title = title
    if "description" in data:
        desc = _text(data["description"])
        _change(changes, "description", benefit.description, desc)
        benefit.description = desc
    if "owner_id" in data and data["owner_id"] is not None:
        new_owner = uuid.UUID(str(data["owner_id"]))
        if new_owner != benefit.owner_id:
            names = owner_names or {}
            changes["owner"] = {
                "old": names.get(benefit.owner_id) if benefit.owner_id else None,
                "new": names.get(new_owner),
            }
            benefit.owner_id = new_owner
    if "decision_kind" in data or "decision_id" in data:
        kind = data.get("decision_kind")
        did = await check_decision(db, kind, data.get("decision_id"))
        if (kind, did) != (benefit.decision_kind, benefit.decision_id):
            changes["decision"] = {"old": benefit.decision_kind, "new": kind}
        benefit.decision_kind, benefit.decision_id = kind, did
    if "kpi_card_id" in data:
        benefit.kpi_card_id = await _check_kpi(
            db, read_scope, benefit.measurement, data["kpi_card_id"]
        )
    if any(k in data for k in BASIS_FIELDS):
        if benefit.status != STATUS_PLANNED:
            raise LifecycleError(
                409, "basis_locked", "The financial basis of a validated benefit is locked"
            )
        merged = {k: getattr(benefit, k) for k in BASIS_FIELDS} | {
            k: data[k] for k in BASIS_FIELDS if k in data
        }
        basis = _basis(benefit.measurement, merged)
        for k, v in basis.items():
            _change(changes, k, getattr(benefit, k), v)
            setattr(benefit, k, v)
        if "planned_amount" in changes:
            benefit.estimated_by = actor_id
    if "initiatives" in data or "affected" in data:

        def _summary(links: list[BenefitLink]) -> list[str]:
            # Labels only (I-75): how many links of each role and class.
            labels = [
                f"{lk.role}:{lk.classification}" if lk.classification else lk.role for lk in links
            ]
            return sorted(f"{label} x{labels.count(label)}" for label in set(labels))

        before = {(lk.card_id, lk.role, lk.classification) for lk in bundle.links}
        old_summary = _summary(bundle.links)
        bundle.links = await _set_links(
            db, read_scope, benefit, bundle.links, data.get("initiatives"), data.get("affected")
        )
        if before != {(lk.card_id, lk.role, lk.classification) for lk in bundle.links}:
            changes["links"] = {"old": old_summary, "new": _summary(bundle.links)}
    _require_governance_anchor(benefit, bundle.links)
    await db.flush()
    if changes:
        await record(db, benefit, "updated", actor_id, changes=changes)
    return bundle


# ── Benefit status ──────────────────────────────────────────────────────


async def validate(
    db: AsyncSession, benefit: Benefit, note: str | None, actor_id: uuid.UUID
) -> Benefit:
    """Finance agrees the financial basis (I-67): method, planned amount and
    expected fiscal year; a baseline for a saving, a counterfactual for an
    avoidance."""
    if not is_financial(benefit):
        raise LifecycleError(422, "not_financial", "Only a financial benefit is validated")
    if benefit.status != STATUS_PLANNED:
        raise LifecycleError(409, "invalid_state", "Only a planned benefit is validated")
    missing = [
        name
        for name, ok in (
            ("method_note", benefit.method_note),
            ("planned_amount", benefit.planned_amount is not None),
            ("expected_fiscal_year", benefit.expected_fiscal_year),
            ("baseline_amount", benefit.benefit_type != COST_SAVING or benefit.baseline_amount),
            (
                "counterfactual",
                benefit.benefit_type != COST_AVOIDANCE
                or (benefit.counterfactual_amount is not None and benefit.counterfactual_note),
            ),
        )
        if not ok
    ]
    if missing:
        raise LifecycleError(
            422, "basis_incomplete", "The financial basis is incomplete: " + ", ".join(missing)
        )
    benefit.status = STATUS_VALIDATED
    benefit.validated_by = actor_id
    benefit.validated_at = _now()
    benefit.validation_note = _text(note)
    await record(
        db,
        benefit,
        "validated",
        actor_id,
        from_status=STATUS_PLANNED,
        to_status=STATUS_VALIDATED,
        note=benefit.validation_note,
        changes={
            "planned_amount": {"old": None, "new": benefit.planned_amount},
            "currency": {"old": None, "new": benefit.currency},
        },
    )
    return benefit


async def reopen(db: AsyncSession, benefit: Benefit, reason: str | None, actor_id: uuid.UUID):
    """Return a validated benefit to ``planned`` so its basis can change."""
    reason = _text(reason)
    if benefit.status != STATUS_VALIDATED:
        raise LifecycleError(409, "invalid_state", "Only a validated benefit is reopened")
    if reason is None:
        raise LifecycleError(422, "reason_required", "Say why the benefit is reopened")
    benefit.status = STATUS_PLANNED
    await record(
        db,
        benefit,
        "reopened",
        actor_id,
        from_status=STATUS_VALIDATED,
        to_status=STATUS_PLANNED,
        note=reason,
    )
    return benefit


async def close(
    db: AsyncSession, bundle: BenefitBundle, outcome: str, reason: str | None, actor_id: uuid.UUID
) -> Benefit:
    """``withdrawn`` (no confirmed actual) or ``not_realised``, with a reason."""
    benefit = bundle.benefit
    reason = _text(reason)
    if outcome not in (STATUS_WITHDRAWN, STATUS_NOT_REALISED):
        raise LifecycleError(422, "invalid_outcome", f"Unknown outcome: {outcome!r}")
    if not is_open(benefit):
        raise LifecycleError(409, "benefit_closed", "The benefit is already closed")
    if reason is None:
        raise LifecycleError(422, "reason_required", "Say why the benefit is closed")
    if outcome == STATUS_WITHDRAWN and any(a.status == CONFIRMED for a in bundle.actuals):
        raise LifecycleError(
            409,
            "confirmed_actuals",
            "A benefit with Finance-confirmed actuals is not withdrawn; reverse them first",
        )
    if any(a.status == REPORTED for a in bundle.actuals):
        raise LifecycleError(
            409, "actual_pending", "An actual awaits Finance; confirm or reject it first"
        )
    previous = benefit.status
    benefit.status = outcome
    benefit.closed_by = actor_id
    benefit.closed_at = _now()
    benefit.close_reason = reason
    await record(
        db, benefit, outcome, actor_id, from_status=previous, to_status=outcome, note=reason
    )
    return benefit


# ── Actuals (I-67, I-68) ─────────────────────────────────────────────────


def independence_conflicts(benefit: Benefit, actual: BenefitActual) -> set[uuid.UUID]:
    """Who may not confirm, reject or reverse ``actual`` (D-29)."""
    people = {benefit.created_by, benefit.owner_id, benefit.estimated_by, actual.reported_by}
    people.discard(None)
    return people  # type: ignore[return-value]


def _require_independent(benefit: Benefit, actual: BenefitActual, actor_id: uuid.UUID) -> None:
    # No exception for administrators (D-29): the rule is about the person.
    if actor_id in independence_conflicts(benefit, actual):
        raise LifecycleError(
            403,
            "self_confirmation",
            "Finance confirmation must come from someone who did not create, own, "
            "estimate or report this benefit",
        )


async def report_actual(
    db: AsyncSession,
    read_scope: CardReadScope,
    bundle: BenefitBundle,
    data: dict,
    actor_id: uuid.UUID,
    *,
    current_fiscal_year: int,
) -> BenefitActual:
    benefit = bundle.benefit
    if not is_financial(benefit):
        raise LifecycleError(422, "not_financial", "Only a financial benefit reports actuals")
    if benefit.status != STATUS_VALIDATED:
        raise LifecycleError(
            409, "not_validated", "Actuals are reported once Finance validated the benefit"
        )
    fy = _fiscal_year(data.get("fiscal_year"), required=True)
    if fy > current_fiscal_year:
        raise LifecycleError(422, "future_fiscal_year", "An actual is not reported in advance")
    if bundle.live_actual(fy) is not None:
        raise LifecycleError(
            409, "actual_exists", "This fiscal year already has a reported or confirmed actual"
        )
    amount = _amount(data.get("amount"), "invalid_amount")
    if amount is None:
        raise LifecycleError(422, "invalid_amount", "The amount realised is required")
    linked = bundle.linked_ids()
    evidence = await resolve_evidence(
        db,
        data.get("evidence"),
        linked,
        await read_scope.readable_card_ids(db, linked, mode="module"),
    )
    actual = BenefitActual(
        benefit_id=benefit.id,
        fiscal_year=fy,
        amount=amount,
        status=REPORTED,
        reported_by=actor_id,
        reported_at=_now(),
        report_note=_text(data.get("note")),
        evidence_refs=evidence,
    )
    db.add(actual)
    await db.flush()
    bundle.actuals.insert(0, actual)
    await record(
        db,
        benefit,
        "actual_reported",
        actor_id,
        to_status=REPORTED,
        note=actual.report_note,
        changes={"fiscal_year": {"old": None, "new": fy}, "amount": {"old": None, "new": amount}},
    )
    return actual


def _find_actual(bundle: BenefitBundle, actual_id: uuid.UUID) -> BenefitActual:
    for a in bundle.actuals:
        if a.id == actual_id:
            return a
    raise LifecycleError(404, "actual_not_found", "Actual not found")


async def _allocations(
    db: AsyncSession,
    read_scope: CardReadScope,
    bundle: BenefitBundle,
    actual: BenefitActual,
    items: list[dict] | None,
) -> list[BenefitAllocation]:
    """Finance's attributable amounts (D-14): to direct / contributing
    initiatives only, each with a rationale, never more than the actual."""
    links = bundle.initiative_links()
    readable = await read_scope.readable_card_ids(db, list(links), mode="module")
    out: list[BenefitAllocation] = []
    seen: set[uuid.UUID] = set()
    for item in items or []:
        try:
            cid = uuid.UUID(str(item.get("card_id")))
        except ValueError:
            cid = None
        link = links.get(cid) if cid else None
        if link is None or cid not in readable or cid in seen:
            raise LifecycleError(
                422, "invalid_allocation", "Allocate to each linked initiative at most once"
            )
        if link.classification not in ALLOCATABLE:
            raise LifecycleError(
                422,
                "not_attributable",
                "A not-attributable initiative receives no allocation",
            )
        amount = _amount(item.get("amount"), "invalid_allocation", positive=True)
        rationale = _text(item.get("rationale"))
        if amount is None or rationale is None:
            raise LifecycleError(
                422, "rationale_required", "Each allocation needs an amount and a rationale"
            )
        seen.add(cid)
        out.append(
            BenefitAllocation(
                actual_id=actual.id,
                card_id=cid,
                classification=link.classification,
                amount=amount,
                rationale=rationale,
            )
        )
    if sum(a.amount for a in out) > actual.amount + CENT:
        raise LifecycleError(
            422,
            "over_allocated",
            "Allocations may not exceed the confirmed amount in total",
        )
    return out


async def confirm_actual(
    db: AsyncSession,
    read_scope: CardReadScope,
    bundle: BenefitBundle,
    actual_id: uuid.UUID,
    data: dict,
    actor_id: uuid.UUID,
) -> BenefitActual:
    benefit = bundle.benefit
    actual = _find_actual(bundle, actual_id)
    if actual.status != REPORTED:
        raise LifecycleError(409, "invalid_state", "Only a reported actual is confirmed")
    _require_independent(benefit, actual, actor_id)
    reference = _text(data.get("finance_reference"))
    if reference is None or len(reference) > MAX_FINANCE_REFERENCE:
        raise LifecycleError(
            422, "finance_reference_required", "Give the Finance reference (200 characters)"
        )
    allocations = await _allocations(db, read_scope, bundle, actual, data.get("allocations"))
    actual.status = CONFIRMED
    actual.decided_by = actor_id
    actual.decided_at = _now()
    actual.finance_reference = reference
    actual.decision_note = _text(data.get("note"))
    for alloc in allocations:
        db.add(alloc)
    bundle.allocations[actual.id] = allocations
    await db.flush()
    await record(
        db,
        benefit,
        "actual_confirmed",
        actor_id,
        from_status=REPORTED,
        to_status=CONFIRMED,
        note=actual.decision_note,
        changes={
            "fiscal_year": {"old": None, "new": actual.fiscal_year},
            "amount": {"old": None, "new": actual.amount},
            "allocated": {"old": None, "new": round(sum(a.amount for a in allocations), 2)},
        },
    )
    return actual


async def reject_actual(
    db: AsyncSession,
    bundle: BenefitBundle,
    actual_id: uuid.UUID,
    reason: str | None,
    actor_id: uuid.UUID,
) -> BenefitActual:
    actual = _find_actual(bundle, actual_id)
    if actual.status != REPORTED:
        raise LifecycleError(409, "invalid_state", "Only a reported actual is rejected")
    _require_independent(bundle.benefit, actual, actor_id)
    reason = _text(reason)
    if reason is None:
        raise LifecycleError(422, "reason_required", "Say why the actual is rejected")
    actual.status = REJECTED
    actual.decided_by = actor_id
    actual.decided_at = _now()
    actual.decision_note = reason
    await record(
        db,
        bundle.benefit,
        "actual_rejected",
        actor_id,
        from_status=REPORTED,
        to_status=REJECTED,
        note=reason,
        changes={"fiscal_year": {"old": None, "new": actual.fiscal_year}},
    )
    return actual


async def reverse_actual(
    db: AsyncSession,
    bundle: BenefitBundle,
    actual_id: uuid.UUID,
    reason: str | None,
    actor_id: uuid.UUID,
) -> BenefitActual:
    """Withdraw a confirmation (a correction); its allocations stop counting."""
    actual = _find_actual(bundle, actual_id)
    if actual.status != CONFIRMED:
        raise LifecycleError(409, "invalid_state", "Only a confirmed actual is reversed")
    _require_independent(bundle.benefit, actual, actor_id)
    reason = _text(reason)
    if reason is None:
        raise LifecycleError(422, "reason_required", "Say why the confirmation is reversed")
    actual.status = REVERSED
    actual.reversed_by = actor_id
    actual.reversed_at = _now()
    actual.reverse_reason = reason
    await record(
        db,
        bundle.benefit,
        "actual_reversed",
        actor_id,
        from_status=CONFIRMED,
        to_status=REVERSED,
        note=reason,
        changes={
            "fiscal_year": {"old": None, "new": actual.fiscal_year},
            "amount": {"old": actual.amount, "new": None},
        },
    )
    return actual


# ── Qualitative assessments (D-43) ───────────────────────────────────────


async def assess(
    db: AsyncSession,
    read_scope: CardReadScope,
    bundle: BenefitBundle,
    data: dict,
    actor_id: uuid.UUID,
    *,
    current_fiscal_year: int,
) -> BenefitAssessment:
    benefit = bundle.benefit
    if benefit.measurement != MEASUREMENT_QUALITATIVE:
        raise LifecycleError(
            422, "not_qualitative", "Only a qualitative outcome is assessed; a KPI is measured"
        )
    if not is_open(benefit):
        raise LifecycleError(409, "benefit_closed", "A closed benefit is not assessed")
    fy = _fiscal_year(data.get("fiscal_year"), required=True)
    if fy > current_fiscal_year:
        raise LifecycleError(422, "future_fiscal_year", "An outcome is not assessed in advance")
    outcome = data.get("outcome")
    if outcome not in OUTCOMES:
        raise LifecycleError(422, "invalid_outcome", f"Unknown outcome: {outcome!r}")
    note = _text(data.get("note"))
    if note is None:
        raise LifecycleError(422, "note_required", "Describe what was observed")
    linked = bundle.linked_ids()
    evidence = await resolve_evidence(
        db,
        data.get("evidence"),
        linked,
        await read_scope.readable_card_ids(db, linked, mode="module"),
    )
    row = BenefitAssessment(
        benefit_id=benefit.id,
        fiscal_year=fy,
        outcome=outcome,
        note=note,
        evidence_refs=evidence,
        assessed_by=actor_id,
        assessed_at=_now(),
    )
    db.add(row)
    await db.flush()
    bundle.assessments.insert(0, row)
    await record(
        db,
        benefit,
        "assessed",
        actor_id,
        note=note,
        changes={"outcome": {"old": None, "new": outcome}, "fiscal_year": {"old": None, "new": fy}},
    )
    return row
