# Master implementation plan: Digital Transformation & EA Executive Performance Dashboard

**Status: final plan. Phase 1 decisions approved 2026-10-22. Implementation not yet authorised; nothing implemented.**
**Date:** 2026-10-22
**Baseline:** the 10-document assessment in `docs/executive-dashboard-assessment/` (index and superseded versions in that folder's `README.md`).

## 1. Goal

Answer the CEO's seven questions (BO-1..BO-7) with measures of **performance, governance effectiveness, organisational impact and ROI**, inside Turbo-EA. Repository activity moves to specialist views.

## 2. Recommended final architecture

- **Presentation**: the existing Dashboard → **Executive** tab (`frontend/src/features/dashboard/Dashboard.tsx`) gains a secondary navigation of eight pages. Overview, My Workspace and Admin are unchanged apart from corrections. **English and Arabic only** (fork policy, D-18).
- **API**: one scope-aware aggregate endpoint per page under `/reports/executive/*`, plus a drill-down endpoint, a traceability endpoint, KPI measurement endpoints and the benefits register API. Each response carries the per-KPI contract (value, target, baseline, delta, trend, status, confidence, completeness, as-of, calculation version, owner, drill-down, **currency**).
- **Backend**: `backend/app/services/executive/`, a context (read scope, cost and benefit permissions, period, org filter) plus one named, versioned **builder per KPI** (no formula engine). It refactors the phase-one `services/executive_dashboard.py` and reuses `bpm_dashboard_service.py`, `ppm_portfolio_service.py`, `risk_service`, `fiscal_year.py` (D-06), `lifecycle.py` and `eol_service`.
- **Data**:
  - **reused**: KPI cards, Objective / Pillar, Initiative + PPM, GovService, BusinessProcess + BPM, maturity, ARB, ADR, ADM, approval steps, tech standards and exceptions, rationalization, improvement opportunities, risks, todos, tags, documents, events;
  - **new**: `metric_snapshots`, `kpi_measurements`, `benefits` (+ `benefit_cards`, `benefit_evidence`), `todos.source_kind` / `source_id`, `improvement_opportunities.realized_at`, metamodel fields (`KPI.metricKey`, `GovService.digitalizationLevel`), and an initiative-report staleness setting (no default; D-02).
- **Money** (D-05): currency-aware; original currency metadata preserved; no conversion or relabeling until verified; totals only within one currency.
- **Security**: a **separate Security Remediation Track (SEC)** closes S-01..S-19 independently of the dashboard. It must pass CI before any affected API feeds executive reporting. Inside the dashboard: `CardReadScope` on every population, hidden types excluded (D-01), `costs.view` on money, new `benefits.*` and `kpis.measure` permissions, small-group suppression, export parity, and governance records redacted or omitted per D-30.

## 3. Confirmed implementation scope

FR-01..FR-20, CR-01..CR-10, SR-01..SR-09 and NFR-01..NFR-07 (`EXECUTIVE_BUSINESS_REQUIREMENTS.md`), delivered by the **SEC track** plus feature **Phases 0-6**. Out of scope: currency conversion, real-time telemetry, a separate executive frontend or database, and AI insights before Phase 6.

## 4. Decisions

| State | Count | IDs |
|---|---|---|
| Confirmed from the planning briefs | 16 | C-01..C-16 |
| **Approved 2026-10-22** | 8 | D-01, D-02, D-05, D-06, D-18, D-22, D-24, D-30 |
| **Approved 2026-10-24** | 6 | S-08, S-12 (security); D-03, D-04, D-07, D-17 (Phase 2, with changes) |
| Open | — | Every row of `DECISION_LOG.md` §3 not marked approved or deferred, plus D-37..D-42 (§3.1) |
| **Approved 2026-10-25** | 12 | D-19, D-21, D-26, D-17a (KPI history and linkage); D-10, D-13, D-28, D-32, D-33, D-34, D-35, D-36 (Phase 3, with changes) — D-11 **deferred** |
| Open and blocking | 11 | D-08 (Phase 5) · D-37..D-42 (Phase 3 batches 3.2-3.6, see `DECISION_LOG.md` §3.1) · D-12, D-14, D-15 (Phase 4) · D-31 (Phase 1, CR-04 only) |

## 5. Document map

| Document | Purpose |
|---|---|
| `EXECUTIVE_BUSINESS_REQUIREMENTS.md` | Objectives, audiences, FR / CR / SR / NFR requirements |
| `FINAL_KPI_DICTIONARY.md` | KPI standards, corrections CR-01..10 (aligned with the approved decisions), 49 KPI definitions |
| `DATA_MODEL_AND_RELATIONSHIPS.md` | Reused entities, new tables and fields, traceability relationships |
| `API_AND_BACKEND_DESIGN.md` | Layering, request context, response contract, endpoints, snapshots, testing |
| `UI_UX_SPECIFICATION.md` | Navigation, KPI tile standard, eight page wireframes, RTL, accessibility |
| `GOVERNANCE_MEASUREMENT_MODEL.md` | Activity / effectiveness / impact model and rules |
| `BENEFITS_AND_ROI_SPECIFICATION.md` | Benefits register, statuses, attribution methods, ROI |
| `SECURITY_REMEDIATION_PLAN.md` | SEC track: findings S-01..S-19, D-30 record treatment, work items WI-1..15, disclosure regression suite R1-R7 |
| `PHASED_DELIVERY_PLAN.md` | SEC track + feature Phases 0-6 with the full specification |
| `DECISION_LOG.md` | Confirmed, approved and open decisions |
| `DECISION_REVIEW_PACKAGE.md`, `FINAL_DECISION_RECOMMENDATIONS.md` | Review records (superseded in part by the approvals) |
| `PROGRESS_REPORT.md` | Status of the track and phases |
| `REQUIREMENTS_TRACEABILITY_MATRIX.md` | Requirement → design → KPI → phase → verification → finding |

## 6. Streams, phases and dependencies

| Stream / phase | Scope | Complexity | Depends on |
|---|---|---|---|
| **SEC track** (independent) | SEC-1 disclosure regression suite → SEC-2 name / id and money leaks (incl. S-18, S-19) → SEC-3 governance records (D-30), aggregates, hidden types (D-01), guard | M | Implementation authorisation only |
| Phase 0 | Remaining decisions, KPI ratification, data ownership and population | S (stakeholder time) | — |
| Phase 1 | Preserve and baseline the uncommitted work (D-22); KPI corrections CR-01..10 on the prototype | M | D-22 step before prototype edits; D-31 for CR-04 |
| Phase 2 | Executive navigation, CEO Overview, Decisions page, KPI history and provenance, filters, tile standard | L | Phase 1; SEC items for every reused API; D-03, D-04, D-07, D-17 |
| Phase 3 | Governance effectiveness in six batches: 3.1 activity, coverage, rule-based compliance · 3.2 transition history, exception lifecycle · 3.3 business calendar · 3.4 decision actions, GOV-05 · 3.5 architecture risks · 3.6 review coverage | M | Phase 2; 3.1 unblocked; 3.2 D-39/D-40 · 3.3 D-38 · 3.4 D-41 · 3.5 D-42 · 3.6 D-37 |
| Phase 4 | Benefits register, Financial & ROI, Business Impact, traceability | L | Phases 2, 3; D-12, D-14, D-15 |
| Phase 5 | Transformation, Services & Automation, Portfolio Health | M-L | Phase 2 + data; D-08 |
| Phase 6 | Export, insights, accessibility, bilingual RTL QA, performance | M | Phases 2-5 |

## 7. Implementation sequence after authorisation

1. **Preserve the uncommitted work** (D-22): non-destructive backup (patch + archive of untracked files, `backend/.env` excluded). Commits only on separate instruction.
2. **SEC-1**: disclosure regression suite (R1-R7). This is the **recommended first development task**: it needs no open decision, touches only tests, and fails on the known leaks.
3. **SEC-2** and **SEC-3** in severity order. Each is validated in CI (consolidated suites, diff coverage, mutation gates) **before deployment**.
4. **Phase 1** in parallel once the baseline commits are authorised: the four logical units (Windows fix · responsive navigation · Executive prototype · documentation), then CR corrections (CR-04 once D-31 is decided).
5. **Phase 2 onwards** after Phase 1, with the SEC items covering reused APIs merged.
6. **Phase 3** starts with **Batch 3.1** (no open decision); the later batches follow as D-37..D-42 are decided (`PHASED_DELIVERY_PLAN.md`, Phase 3).

## 8. Governance of this plan

- Open decisions are approved by their owners before the phase marked in `DECISION_LOG.md`.
- `PROGRESS_REPORT.md` statuses change only on the evidence defined in `PHASED_DELIVERY_PLAN.md`. Planning is not implementation.
