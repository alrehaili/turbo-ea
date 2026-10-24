"""Executive dashboard, Phase 2: the CEO overview and the decisions view.

One named, versioned builder per KPI (no formula engine, C-03). Every builder
returns the same contract (``kpis.kpi``) so the page renders actual, target,
previous period, period, freshness, owner, confidence and drill-down uniformly,
and shows *Not available* instead of a number whenever a source, a decision or
a permission is missing. The Phase 1 Executive tab payload stays in
``app.services.executive_dashboard``; its builders are reused here, not copied.
"""
