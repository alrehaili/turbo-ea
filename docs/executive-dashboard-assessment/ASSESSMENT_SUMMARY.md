# Executive dashboard readiness summary

## Overall conclusion

Turbo-EA is ready to host an initial executive dashboard inside the existing application, particularly for architecture/portfolio/process/governance visibility and drill-down. It is **not yet ready to make defensible executive claims about verified financial benefits, cost avoidance, ROI, or broad transformation outcomes** without new governed data collection and calculation capabilities.

## What is already supported

- A secure, data-driven EA inventory with cards, relationships, hierarchy, lifecycle, approval and data quality.
- Business capability, business process, application, technology, initiative, strategy, roadmap and target-state building blocks.
- BPM automation/maturity classifications and process diagrams; PPM RAG, budgets, costs, tasks and portfolio APIs.
- ARB, ADR, ADM, principle/standard/exception, risk/mitigation, maturity, NORA and rationalization modules.
- Existing reports, Recharts/MUI visual components, bilingual English/Arabic localization and RTL code paths.

## What can be calculated immediately, subject to workspace data quality

- Current portfolio and repository health, approval/data-quality/lifecycle distributions.
- Process counts, automation/maturity classifications, risk classification and BPM diagram coverage through `/reports/bpm/dashboard`.
- PPM portfolio RAG and recorded budget/actual totals through `/reports/ppm/dashboard`.
- Risk exposure/mitigation status through `/risks/metrics` and the register.
- Planned rationalization pipeline, clearly labelled **planned/estimated**, not realised savings.
- Existing standards/exceptions, architecture-state and strategy/roadmap drill-down views where configured.

## What requires new data collection

- Finance-approved benefit cases, baselines, forecast/actual periodisation, verification evidence, benefit owner and EA-attribution method.
- A common governance intake/review/decision/action/closure model with timestamps and evidence.
- Agreed service digitalization definition and evidence; automation denominator/threshold and assessment cadence.
- Technology debt baseline/score and target-realisation delivery evidence.
- KPI targets, owners, thresholds, historical facts, calculation provenance and data-freshness status.

## What requires application development

- An Executive Dashboard view and dedicated authorization-aware aggregate API/read-model layer.
- KPI catalog/target/history/provenance capability.
- Benefit-realisation and financial-verification capability, ideally integrated/reconciled with Finance.
- Governance corrective-action/implementation tracking and executive escalation flow.
- Executive-oriented bilingual/RTL UX, filters, narrative, drill-down and empty/partial-data states.

## Key architecture risks

- Treating configurable JSON fields or unverified relation coverage as a complete enterprise baseline.
- Leaking restricted cost/card data through totals that bypass existing permission/read-scope controls.
- Presenting planned rationalization savings or manual status as realised financial value.
- Making target-realisation claims from target-state modeling without delivery and operational evidence.
- Building a parallel external dashboard before a stable KPI and security contract exists.

## Recommended next step

Approve a discovery/design phase, not implementation: profile actual workspace data and module enablement; ratify a KPI catalog with Finance, EA Governance, PMO, Digital and process owners; identify a small honest phase-one KPI set; and produce a bilingual executive UX prototype. The recommended deployment option is an internal Turbo-EA dashboard backed by purpose-specific, permission-aware read APIs.

## Assessment evidence

Primary code references are documented in `CURRENT_ARCHITECTURE.md` and include `backend/app/api/v1/router.py`, `backend/app/api/v1/reports.py`, `backend/app/api/v1/bpm_reports.py`, `backend/app/api/v1/ppm_reports.py`, `backend/app/models/`, `backend/app/services/seed.py`, `frontend/src/App.tsx`, `frontend/src/features/dashboard/`, and `frontend/src/i18n/index.ts`.
