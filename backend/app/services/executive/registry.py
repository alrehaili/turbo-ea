"""Registered executive calculations a KPI card may be linked to (D-26).

A KPI card's ``metricKey`` must name one of these: it is how a computed
indicator finds the card that carries its definition, target, owner and
baseline. Only calculations that produce a value are listed — an indicator
that is still "not available" has nothing to link a target to. Each entry is
also a series in the measurement history (``kpi_measurements.metric_key``),
captured daily and closed into period values (D-19).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegisteredMetric:
    key: str
    unit: str  # "percent" / "count"
    version: str


METRICS: dict[str, RegisteredMetric] = {
    # Share of in-flight initiatives on track, among those that reported.
    "TR-03": RegisteredMetric("TR-03", "percent", "TR-03@3"),
    # Open risks meeting the D-04 executive-escalation rule.
    "DEC-01": RegisteredMetric("DEC-01", "count", "DEC-01@2"),
    # Rule-based technology-standards compliance: compliant ÷ assessed (D-33).
    "GOV-03": RegisteredMetric("GOV-03", "percent", "GOV-03@1"),
    # Decisions independently verified by their original approved deadline ÷
    # decisions due (D-32, D-41). A period figure: see ``PERIOD_CALCULATED``.
    "GOV-05": RegisteredMetric("GOV-05", "percent", "GOV-05@1"),
}

#: Metrics whose closed-period value is calculated for that period from its
#: recorded history, not taken from the last daily observation (D-19, I-2).
#: GOV-05's daily observation is the running figure of the fiscal quarter that
#: day falls in, so the last observation of a fiscal year would be its fourth
#: quarter's figure, not the year's.
PERIOD_CALCULATED = frozenset({"GOV-05"})


def is_registered(key: str) -> bool:
    return key in METRICS
