# Executive business requirements

**Status: draft for approval. Planning only, nothing implemented.**
**Baseline:** the 10-document assessment in `docs/executive-dashboard-assessment/` (2026-10-22). That folder's `README.md` identifies superseded documents.
**Requirement IDs** are referenced by every other document in this folder and traced in `REQUIREMENTS_TRACEABILITY_MATRIX.md`.

## 1. Purpose

Upgrade Turbo-EA's Dashboard → **Executive** tab into a Digital Transformation & Enterprise Architecture **Executive Performance Dashboard**. It must measure performance, governance effectiveness, organisational impact and ROI, not repository activity.

## 2. CEO questions (business objectives)

| ID | Question the dashboard must answer | Primary pages |
|---|---|---|
| BO-1 | Are we achieving our digital transformation strategy and roadmap? | Overview, Transformation |
| BO-2 | How effective is our EA governance? | Governance |
| BO-3 | Are architecture decisions being implemented and producing results? | Governance, Impact |
| BO-4 | Are we improving digital services, business processes and organisational capabilities? | Services & Automation, Transformation |
| BO-5 | Are we reducing duplication, technology debt, inefficiencies and risks? | Impact, Portfolio Health |
| BO-6 | What measurable business benefits and financial returns have been achieved? | Financial & ROI |
| BO-7 | Which issues require executive intervention or decisions? | Decisions & Escalations, Overview |

## 3. Stakeholders and audiences

| Audience | Needs | Access (proposal, see `DECISION_LOG.md` D-03) |
|---|---|---|
| CEO / executive committee | Six headline measures, decisions, value realised | `reports.executive_dashboard` (+ `costs.view` for money) |
| VPs / sponsors | Their organisation's slice; delivery and services | same, filtered by organisation |
| Digital Transformation GM | Strategy, roadmap, services, automation, maturity | same |
| Chief Architect / EA office | Governance, impact, portfolio health | same + specialist views (Overview tab) |
| CFO / Finance business partner | Benefits register, validation, ROI | `costs.view` + new benefit permissions (see `SECURITY_REMEDIATION_PLAN.md` §5) |
| CRO | Escalated risks | `risks.view` |

## 4. Functional requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | The Executive tab contains eight pages: CEO Executive Overview, Digital Transformation Performance, EA Governance Effectiveness, EA Business Impact, Financial Benefits & ROI, Services & Process Automation, Architecture Portfolio Health, Executive Decisions & Escalations. The top-level tabs Overview, Executive, My Workspace and Admin are kept. | Must |
| FR-02 | Every Executive page supports an **organisation / department filter** (the organisation card type and hierarchy; see D-07). | Must |
| FR-03 | Every Executive page supports a **reporting period** selector (fiscal year, fiscal quarter), defaulting to the current fiscal year, named with the existing `fiscalYearLabel`. | Must |
| FR-04 | Every KPI drills down to the **evidence records** behind it (filtered list or record), respecting the caller's permissions. | Must |
| FR-05 | Full **English and Arabic** support, including RTL layout, numerals and currency formatting. English and Arabic are the only UI languages, per the fork's language policy (D-18, approved). | Must |
| FR-06 | The CEO landing page shows **about six headline measures** plus a decisions panel. Repository counts, completeness and technical inventories stay in specialist views. | Must |
| FR-07 | Each KPI shows **value, target, baseline, delta vs the previous period, status, reporting date and trend**. | Must |
| FR-08 | Missing data renders as **"Not available"** (no data source) or **"Not reported"** (source exists, no submission), never as zero. | Must |
| FR-09 | KPI **definitions, owners, baselines and targets** are held on existing **`KPI` cards**. | Must |
| FR-10 | KPI **measurement history and calculation provenance** (source, as-of, calculation version, confidence) are recorded without duplicating KPI card metadata. | Must |
| FR-11 | EA governance effectiveness KPIs (coverage, early engagement, compliance, decision implementation, exceptions, corrective actions, turnaround, bottlenecks, governed vs ungoverned outcomes), distinguishing activity, effectiveness and impact. | Must |
| FR-12 | Architecture decisions (ADR, ARB) can carry **implementation actions** with owner, due date and closure. | Must |
| FR-13 | A **Finance-verifiable benefits register** linked to decisions, initiatives and evidence (full field list in `BENEFITS_AND_ROI_SPECIFICATION.md`). | Must |
| FR-14 | **ROI** uses only verified, attributable financial benefits and comparable programme costs over the same period. | Must |
| FR-15 | **Service digitalization** is reported as Digital / Hybrid / Manual (+ Not assessed), separately from process automation. | Must |
| FR-16 | **Process automation** is reported as Fully automated / Partially automated / Manual / Unknown–not assessed. | Must |
| FR-17 | A prioritised **decisions and escalations** list across risks, ADR, ARB, exceptions, investment gates and dependencies. | Must |
| FR-18 | **Board-pack export** (PPTX / XLSX) of Executive pages, with the same authorization as the screen. | Should |
| FR-19 | Productivity improvements are reported **separately** from financial savings unless cash savings are demonstrated. | Must |
| FR-20 | A **traceability view** renders, for one decision: intervention → recommendation → decision → implementation → outcome → benefit. | Should |

## 5. KPI correction requirements (existing defects)

Full specifications are in `FINAL_KPI_DICTIONARY.md` §2.

| ID | Defect | Priority |
|---|---|---|
| CR-01 | Missing initiative status reports are shown as healthy delivery | Must |
| CR-02 | Initiative health must distinguish On Track / At Risk / Off Track / Unknown–Not reported | Must |
| CR-03 | Budget and actual aggregated across unrelated fiscal years | Must |
| CR-04 | Planned savings duplicated across rationalization assessments | Must |
| CR-05 | Missing currency definition and SAR formatting (currency-aware, no relabeling or conversion; D-05) | Must |
| CR-06 | Hidden card types counted inconsistently in totals | Must |
| CR-07 | Repository approval % confused with architecture compliance | Must |
| CR-08 | Data completeness described as organisational data quality | Must |
| CR-09 | Card end-of-life dates confused with vendor support expiry | Must |
| CR-10 | Published process diagrams confused with process maturity | Must |

## 6. Security requirements (mandatory, precede reuse)

Details are in `SECURITY_REMEDIATION_PLAN.md`. Delivered by the separate Security Remediation Track (SEC), not by the feature phases.

| ID | Requirement |
|---|---|
| SR-01 | Consistent `CardReadScope` enforcement on every endpoint the executive dashboard reuses, and on all affected fork modules (NORA, rationalization, ARB, tech standards, maturity, improvement opportunities, ADM, roadmaps, impact). |
| SR-02 | Card-level and aggregate-level authorization: no count, chart, total, export or drill-down may reveal a card the caller cannot read. |
| SR-03 | Financial values require `costs.view` on every endpoint (including PPM dashboard and rationalization). |
| SR-04 | Small-group disclosure control on filtered aggregates for restricted readers. |
| SR-05 | Exports apply the same rules as the screen and are recorded in the security audit log. |
| SR-06 | Benefit verification and Finance confirmation are separately permissioned actions. |
| SR-07 | Authorization tests for restricted users cover every new or changed endpoint, and extend the sentinel sweep fixture to every affected module. |
| SR-08 | The **Security Remediation Track (SEC)**, separate from the dashboard feature phases, passes CI for each affected API before that API feeds executive reporting. |
| SR-09 | **Regression coverage** for information disclosure through reports, counts, charts, monetary aggregates, governance records and exports (`SECURITY_REMEDIATION_PLAN.md` §6) is in place before the fixes and stays in CI. |

## 7. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-01 | Each Executive page loads with **one** aggregate request (no per-tile fan-out); p95 ≤ 2 s at 50k cards (target, proposal). |
| NFR-02 | Historical values are immutable per period and reproducible from stored facts (no recomputation from current state). |
| NFR-03 | Every manual financial or KPI entry is auditable (who, when, old → new) through events with `db=` and the audit-log contract. |
| NFR-04 | WCAG 2.1 AA for executive pages: text alternatives for charts, keyboard access, contrast. |
| NFR-05 | Mobile and tablet usable (≥ 768 px) and board-room display (≥ 1920 px). |
| NFR-06 | No generic formula engine. KPIs are named, versioned, tested builder functions. |
| NFR-07 | Follow the project's conventions: Alembic migrations, workspace-transfer checklist, permission registry, EN + AR translations (fork policy), docs, changelog and version, tests and mutation gates. |

## 8. Out of scope (proposal)

Real-time telemetry integration, currency conversion (reporting is currency-aware and never converts or relabels amounts; D-05), a separate executive frontend or database, AI-generated insights before Phase 6, and changes to Overview, My Workspace and Admin beyond the corrections listed.
