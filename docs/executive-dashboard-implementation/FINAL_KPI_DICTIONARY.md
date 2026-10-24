# Final KPI dictionary

**Status: proposal for approval.** Targets and thresholds are **proposals to be ratified by the named owner** (`DECISION_LOG.md` D-17). Nothing is implemented. Requirement IDs refer to `EXECUTIVE_BUSINESS_REQUIREMENTS.md`.

## 1. Standards that apply to every KPI

| Standard | Rule |
|---|---|
| Definition home | One **`KPI` card** per executive KPI (existing NORA type). It holds `calculationFormula` (text), `unit`, `direction`, `measurementFrequency`, `indicatorLevel`, `baselineValue` / `baselineDate`, `targetValue` / `targetValueDate`, `dataSource`. The **owner** is a stakeholder role on the card. Relations go to Objective / Initiative / GovService / BusinessProcess / OrganizationalUnit. The KPI card's `key` attribute links it to the builder function (see `DATA_MODEL_AND_RELATIONSHIPS.md` §3.1). |
| Calculation | A named, versioned builder function per KPI in `backend/app/services/executive/` (no generic formula engine, C-03). |
| History | Each period's value is stored in `kpi_measurements` (manual or external KPIs) or `metric_snapshots` (computed KPIs) with `calculation_version`, `as_of`, `source`, `confidence`, `completeness`. |
| Period | Fiscal year and fiscal quarter, via `backend/app/services/fiscal_year.py`; displayed with `fiscalYearLabel`. |
| Missing data | `not_available` (no source or definition), `not_reported` (source exists, no submission; staleness applies only if configured, D-02), `insufficient_data` (completeness below the threshold). Never 0. |
| Confidence | `high` (system-derived, ≥ 90% completeness) · `medium` (self-assessed or 70-90%) · `low` (< 70% or unverified). Shown on every tile. |
| Completeness | % of the denominator population carrying the required input fields; shown beside the value. |
| Authorization | Caller's `CardReadScope` (module mode) on every population; hidden card types excluded (D-01, approved); money requires `costs.view`; benefit amounts additionally require `benefits.view` (D-03). |
| Org filter | Restricts the population to cards related to the selected organisation subtree (D-07). |
| Status colour | Against target, with `direction`: ≥ target green; within the tolerance band (proposal 10%) amber; otherwise red; no target means neutral. |

## 2. Corrections to existing KPIs (CR-01 to CR-10)

### CR-01 / CR-02: Initiative delivery health

- **Existing calculation** [Confirmed]: `ppm_portfolio_service.build_dashboard` (`backend/app/services/ppm_portfolio_service.py:494`) counts `schedule_health` / `cost_health` / `scope_health` from the **latest** `ppm_status_reports` row per initiative, with a `noReport` bucket. The Executive tile shows only `offTrack` ("0 of 20"), hiding that 14 of 20 have no report. `Initiative.attributes.initiativeStatus` is ignored.
- **Required change**:
  1. Four states (D-02, approved): **On Track**, **At Risk**, **Off Track**, **Unknown / Not Reported**.
  2. "Not Reported" = the initiative has no status report. A **reporting staleness threshold is configurable** (admin setting in `app_settings.general_settings`, **no default value**: no deadline is invented). Only when an owner sets it does a report older than the threshold also count as Not Reported.
  3. A missing or stale report is **never** counted as healthy and **never** automatically classified as At Risk.
  4. **Reporting coverage is displayed separately** from the state mix ("6 of 20 initiatives reported"), as its own indicator (TR-04).
  5. Initiatives in `initiativeStatus ∈ {completed, onHold}` are excluded from in-flight health and shown separately.
- **Data source**: `ppm_status_reports` (when PPM is enabled); fallback `Initiative.attributes.initiativeStatus` when PPM is off.
- **Business rule**: an initiative's overall state = the worst of its schedule, cost and scope health in its latest report (counted only if it is within the staleness threshold, when one is configured).
- **Acceptance criteria**:
  - An initiative with no report is counted as Not Reported, never as On Track or At Risk.
  - With a staleness threshold configured, an older report also counts as Not Reported; with none configured, no report is treated as stale.
  - The four state counts plus excluded initiatives equal the in-scope initiative count.
  - Coverage is a separate indicator with its own value and as-of date.
  - The org filter and read scope change the denominator.

### CR-03: Budget vs actual period

- **Existing calculation** [Confirmed]: `ppm_portfolio_service.sum_budget_actual` (`:253`) sums **all** `ppm_budget_lines.amount` and **all** `ppm_cost_lines.actual`. The "% spent" mixes years.
- **Required change**: budget = Σ `ppm_budget_lines.amount` where `fiscal_year` = the selected FY. Actual = Σ `ppm_cost_lines.actual` where `date` falls in the selected FY (`fiscal_year_for(date)`). Quarter selection is phased by `date`; budget has no quarter phasing, so the quarter view shows FY budget with a "FY budget" label.
- **Data source**: `ppm_budget_lines`, `ppm_cost_lines`, `fiscal_year.py`.
- **Business rule**: the same fiscal-year naming as the cost reports (a year is named after the calendar year it ends in).
- **Acceptance criteria**: changing the FY changes both figures. A cost line dated outside the FY is excluded. Totals reconcile to `/ppm/initiatives/{id}/budgets` and `/costs` filtered by FY. Hidden behind `costs.view` (Restricted state otherwise).

### CR-04: Planned savings duplication

- **Existing calculation** [Confirmed]: `executive_dashboard.summarize_rationalization` sums `assessment_decisions.planned_savings` across every decision in `active` / `completed` assessments. The same application in two assessments is counted twice.
- **Required change** (D-24, approved):
  1. **Identity** = the linked benefit when one exists (Phase 4), otherwise the application (`card_id`); deduplicated **per financial period**. The period source for planned savings is open item **D-31**: `assessment_decisions` carries no period field.
  2. Within one identity and period, decisions that agree (same `planned_savings`, same currency) count **once**.
  3. Decisions that **conflict** are **flagged for reconciliation**: listed with every candidate value and its assessment. **Neither the latest nor the lowest amount is selected automatically.** Unresolved conflicts are **excluded from authoritative financial totals**; the excluded count and candidate range are shown beside the total.
  4. Always labelled **Forecast**, and never part of any "savings achieved" figure. A linked benefit supersedes the planned figure once the register exists.
- **Acceptance criteria**:
  - An application in two assessments with equal amounts contributes once.
  - With different amounts, it contributes **nothing** to the total and appears in the conflicts list with both values.
  - The total equals Σ over non-conflicting identities.
  - Displayed with a Forecast chip and its currency.

### CR-05: Currency and SAR formatting

- **Existing state** [Confirmed]: the instance currency setting defaults to USD (`backend/app/api/v1/settings.py:73`, `GET /settings/currency`). SAR maps to the U+20C1 Riyal sign in `frontend/src/lib/currency.ts`, with a renderability fallback. The phase-one Executive tab builds money as `symbol + Intl compact`, which bypasses locale symbol placement.
- **Required change** (D-05, approved: "currency-aware reporting; preserve original currency metadata; do not relabel or convert existing monetary values until verified"):
  1. **No relabeling and no conversion** of existing amounts. The instance currency setting changes to SAR only after Finance verifies the stored amounts (an administrative action outside this plan's code changes). Records carrying their own currency (e.g. `Project.attributes.currency`) keep it.
  2. Every money figure is formatted by a shared compact formatter built on `useCurrency`'s formatter (`Intl.NumberFormat` with `style: "currency"` + `notation: "compact"`), so symbol position follows the locale (EN `⃁ 6.6M`; AR placement per `ar` locale rules).
  3. API responses carry `currency` beside every amount.
  4. **Totals are computed per currency.** Amounts in different currencies are never summed; a mixed set is shown per currency or as "mixed currencies, not totalled".
  5. Benefits store `currency` explicitly (Phase 4); no conversion.
- **Acceptance criteria**:
  - Every money figure shows the currency of its source (the Riyal sign, or "SAR" when the glyph is not renderable, once the setting is SAR) in EN and AR.
  - No hard-coded `$`.
  - Payloads include `currency`.
  - No total combines two currencies.
  - No stored amount is altered.

### CR-06: Hidden card types in totals

- **Existing state** [Confirmed]: `/reports/dashboard` (`reports.py:128`) and `/reports/executive` count every ACTIVE card. `/reports/my-workspace` (`reports.py:365`) and `/reports/admin-dashboard` (`reports.py:407`) exclude `card_types.is_hidden`. In the demo, 118 of 391 cards belong to hidden types.
- **Required change**: one helper, `visible_type_clause()` in `card_read_scope.py` or a sibling, excludes hidden types from every landscape aggregate, applied to the dashboard, executive, BPM, PPM and report aggregates (D-01, approved). Unauthorized cards remain excluded by `CardReadScope`. Implemented in the security track (WI-11) for `/reports/dashboard` and in feature Phase 1 for the executive aggregates.
- **Acceptance criteria**: Overview, Executive, My Workspace and Admin report the same total for the same caller. The Executive type chart sums to the total.

### CR-07: Approval vs compliance

- **Existing state** [Confirmed]: Executive shows "Approved 100%" (`approval_status`, a repository review state).
- **Required change**: remove it from executive pages. Keep it in Portfolio Health and Overview as **"Repository review status"**. Architecture compliance is a separate KPI (GOV-03) from the tech-standards scan.
- **Acceptance criteria**: no executive page labels approval as compliance. GOV-03 is sourced from `/tech-standards/compliance-scan` (scoped).

### CR-08: Data completeness label

- **Existing state** [Confirmed]: `cards.data_quality` (weighted field completeness from `fields_schema` weights) is labelled "Avg Completion" (Overview) and "Avg data quality" (Executive).
- **Required change**: rename to **"Data completeness"** / **"اكتمال البيانات"** everywhere. Report it type-weighted (mean of per-type means) on Portfolio Health only.
- **Acceptance criteria**: no UI string calls this metric "quality". Overview and Executive show the same value under the same name.

### CR-09: End-of-life vs vendor support

- **Existing state** [Confirmed]: the Overview attention band counts lifecycle phase `endOfLife` as "End-of-life cards". Vendor support status comes from `eol_service` (endoflife.date) and the manual `lifecycle.endOfLife`, via `card_flags.has_eol_coverage`.
- **Required change**: two distinct measures. **"Past planned end-of-life"** (lifecycle) and **"Vendor support expired / expiring"** (`resolve_eol_statuses`).
- **Acceptance criteria**: labels distinguish the two in EN and AR. Each drills to its own filtered list (lifecycle report vs EOL report).

### CR-10: Diagram coverage vs maturity

- **Existing state** [Confirmed]: "Processes with a published flow" (`bpm_dashboard_service.summarize_processes`) is shown as a headline tile.
- **Required change**: move it to Services & Automation as **"Process documentation coverage"** (secondary). Process maturity comes from `BusinessProcess.maturity` and `process_assessments` (SVC-04).
- **Acceptance criteria**: no executive headline uses diagram coverage. Its label says documentation.

## 3. KPI dictionary

Columns: **Formula / denominator** · **Sources** (entities and APIs) · **Period / frequency** · **Baseline & target** (proposal) · **Owner / verifier** · **Confidence & completeness rule** · **Drill-down** · **Auth** · **Phase**. The acceptance criteria follow each table.

### 3.1 CEO landing measures (subset, FR-06)

| Slot | KPI | Fallback until available |
|---|---|---|
| 1 | TR-01 Strategy execution index | TR-03 delivery health |
| 2 | TR-03 Initiative delivery health (4 states + coverage) | — |
| 3 | GOV-05 Decision implementation rate | GOV-01 review coverage |
| 4 | FIN-01 Realised benefits FY (with Validated and Forecast shown separately) | FIN-03 pipeline, labelled forecast |
| 5 | SVC-01 Service digitalization (Digital %) + SVC-02 automation | SVC-02 |
| 6 | DEC-01 Strategic risks requiring escalation | — |

### 3.2 Digital transformation (TR)

| ID | KPI | Formula / denominator | Sources | Period / freq | Baseline & target | Owner / verifier | Confidence & completeness | Drill-down | Auth | Ph |
|---|---|---|---|---|---|---|---|---|---|---|
| TR-01 | Strategy execution index | Σ(progress × weight) ÷ Σ weight over strategic Objectives (`objectiveType=strategic`) in scope; weight = priority (D-21) | `Objective.progress`, `relObjectiveToPillar` / `relNora2PillarObjective`, `/reports/strategy-cascade` | FY/Q; quarterly | Baseline = start-of-FY value; target 100% of plan-to-date (proposal) | Strategy Office / Transformation Office verifies | Medium (manual progress); completeness = objectives with progress updated in the quarter | Pillar → Objective → `relInitiativeToObjective` initiatives | `reports.executive_dashboard` + scope | 2 (data), 5 (page) |
| TR-02 | Roadmap milestone achievement | Milestones achieved by `target_date` ÷ milestones due in period | `roadmap_milestones` + PPM WBS milestones (`ppm_wbs.is_milestone`, `completion`, `end_date`) (D-25) | Q; monthly | Target ≥ 85% | PMO | High if derived from WBS | Roadmap → milestone → initiative | + `ppm.view` for WBS detail | 5 |
| TR-03 | Initiative delivery health | State mix (On / At risk / Off / Not reported) over in-flight initiatives in scope; headline = On Track ÷ reported | `ppm_status_reports`, Initiative cards | Monthly | Target ≥ 75% on track | PMO | Completeness = reporting coverage (TR-04) | Initiative list filtered by state → PPM detail | + scope | 1 (fix), 2 |
| TR-04 | Initiative reporting coverage | In-flight initiatives with an in-window report ÷ in-flight initiatives | as TR-03 | Monthly | Target ≥ 90% | PMO | High | Unreported list | + scope | 1 |
| TR-05 | Digital maturity index | Latest approved `maturity_assessments.overall_score`; Δ vs previous; gap to Σ `target_level` | `maturity_assessments`, `maturity_dimension_scores`, `/maturity/overview` (after the SR fix) | Semi-annual | Baseline = first approved assessment; target per assessment `target_level` | Digital Office; approver = `approved_by` | Medium (assessed); not_available if none approved | Dimension radar → evidence | `maturity.view` | 5 |
| TR-06 | Capability improvement | Target capabilities (`strategicImportance ∈ {high, critical}`) whose `maturity` rose vs baseline ÷ target capabilities | `BusinessCapability.maturity` + `metric_snapshots` (per-card baseline) | Semi-annual | Target per capability owner | Capability owners | Medium | Capability heatmap filtered | scope | 5 |

**Acceptance criteria (TR).**
- TR-01: objectives without progress count toward completeness, not as 0%.
- TR-02: an achieved-late milestone counts as not achieved for the period.
- TR-03 / TR-04: as CR-01 / CR-02.
- TR-05: unapproved assessments are excluded.
- TR-06: the baseline is frozen per FY.

### 3.3 EA governance (GOV). Activity / effectiveness / impact class shown in brackets

| ID | KPI | Formula / denominator | Sources | Period / freq | Baseline & target | Owner / verifier | Confidence | Drill-down | Auth | Ph |
|---|---|---|---|---|---|---|---|---|---|---|
| GOV-01 [activity] | EA review coverage | In-scope initiatives with ≥ 1 ARB review (`subject_card_id`) or linked ADR (`architecture_decision_cards`) ÷ in-scope initiatives (rule D-10) | `arb_reviews`, `architecture_decisions`, Initiative | Q | Target ≥ 90% | Chief Architect | High | Unreviewed initiatives | `arb.view` or `adr.view` + scope | 3 |
| GOV-02 [effectiveness] | Early engagement | Reviews whose first review date precedes the initiative gate (D-11: ADM phase approval or `startDate`) ÷ reviewed initiatives | ARB / ADR dates, `adm_phases.approved_at`, `Initiative.startDate` | Q | Target ≥ 70% | EA Governance Office | Medium | Late-reviewed list | as GOV-01 | 3 |
| GOV-03 [effectiveness] | Standards and principles compliance | In-scope cards compliant with mandated standards ÷ in-scope cards | `/tech-standards/compliance-scan` (`tech_standards_scan.py`, after the SR fix), `tech_standards.mandate` | Monthly | Target ≥ 85% | Domain architects | High (rule-based) | Non-compliant cards | `tech_standards.view` + scope | 3 |
| GOV-04 [effectiveness] | Exception resolution | Exceptions closed (approved with remediation done, or rejected) before `expiry_date` ÷ exceptions expiring in period; plus counts open / expiring in 30 days / expired-but-active | `tech_standard_exceptions` | Monthly | Target 0 expired-but-active | Standards owner | High | Exception list | `tech_standards.view` + scope | 3 |
| GOV-05 [effectiveness] | Decision implementation rate | Signed ADRs + approved ARB reviews older than N days (proposal 90) whose implementation actions are all closed ÷ such decisions | ADR, ARB + decision actions (todos, D-13) | Q | Target ≥ 80% within 180 days | Decision owners; verified by EA office | High once actions exist; not_available before Phase 3 | Decision → actions | `adr.view` / `arb.view` | 3 |
| GOV-06 [effectiveness] | Corrective action completion | Governance actions closed by due date ÷ actions due in period (decision actions + exception remediation + mitigation occurrences) | todos (typed source), `risk_mitigation_task_occurrences` | Monthly | Target ≥ 85% | Action owners | High | Action list | as sources | 3 |
| GOV-07 [efficiency] | Governance turnaround | Median days: ARB `created_at` → `decided_at`; ADR draft → signed (event timestamps); approval step submitted → `acted_at` | `arb_reviews`, events, `approval_steps` | Monthly | Target ≤ 10 working days | EA Governance Office | High | Slowest 10 | as sources | 3 |
| GOV-08 [efficiency] | Governance bottlenecks | Count: approvals pending > 30 d; ARB deferred ≥ 2×; exceptions `requested` > 14 d; ADR `in_review` > 21 d | as GOV-07 | Weekly | Target 0 | EA office | High | Case list (DEC-02) | as sources | 3 |
| GOV-09 [impact, contribution] | Governed vs ungoverned delivery | On-track rate (TR-03) of initiatives covered by GOV-01 minus that of uncovered initiatives | GOV-01 × TR-03 | Semi-annual | Reported, no target (correlation, not causation) | Chief Architect | Low-medium; shown with sample sizes, suppressed if n < 5 per cohort | Cohort lists | as sources | 3 |

**Acceptance criteria (GOV).**
- Every GOV tile carries its class label (Activity / Effectiveness / Impact).
- GOV-05 shows "Not available" until the action tracking ships.
- GOV-09 is displayed with "correlation, not causation" and the cohort sizes.

### 3.4 Business impact (IMP)

| ID | KPI | Formula / denominator | Sources | Period | Baseline & target | Owner | Confidence | Drill-down | Auth | Ph |
|---|---|---|---|---|---|---|---|---|---|---|
| IMP-01 | Applications retired through decisions | Applications with an `eliminate` / `migrate` decision (conflicting decisions for one application are flagged and excluded, per D-24) that became ARCHIVED or reached lifecycle `endOfLife` in period; ÷ such decisions due | `assessment_decisions`, `cards.status`, lifecycle, `successor_id` | Q | Per rationalization plan | App portfolio owner | High | Decision → app → successor | `rationalization.view` + scope | 4 |
| IMP-02 | Duplicate candidates open | Open TurboLens duplicate clusters | `turbolens_duplicate_clusters` | Q | Downward trend | EA | Medium (AI-detected) | Cluster | `turbolens.view` | 4 |
| IMP-03 | Technology debt index | Weighted share of live tech assets that are: vendor-support expired, past lifecycle EOL, technically unsuitable, or under an active exception (weights D-16) | `eol_service`, lifecycle, `Application.technicalSuitability`, exceptions | Q | Baseline FY start; target −15% per year | CTO | Medium | Debt items by domain | scope | 4 |
| IMP-04 | Modernization completion | `migrate` / `invest` decisions whose linked initiative is `completed` or `progress = 100` ÷ such decisions | `assessment_decisions.progress`, `initiative_id` | Q | Per plan | App portfolio owner | High | Decision list | as IMP-01 | 4 |
| IMP-05 | Architecture reuse | Shared-service applications (`sharedService = true`) used by ≥ 2 organisations ÷ shared-service applications | `Application.sharedService`, org → app relation (D-07) | Semi-annual | Upward trend | EA | High | App → consumers | scope | 4 |
| IMP-06 | Integration standardization | Interfaces with `viaGsb = true` ÷ interfaces | `Interface.viaGsb`, `/reports/integration-status` (only after WI-15 scopes it) | Q | Target ≥ 80% | Integration architecture | High | Point-to-point list | scope | 4 |
| IMP-07 | Target architecture realisation | Target-state cards (`architecture_state = target`) realised (now `current`, per events) in period ÷ target cards planned for the period's plateau | `cards.architecture_state`, `change_type`, `nora_plateaus.target_date`, events | Q | Per plateau | Enterprise architect | Medium (event-derived) | `/reports/gap-analysis` filtered | scope | 4 |
| IMP-08 | Risk reduction | Σ (initial level score − residual level score) for risks mitigated or closed in period; plus count | `risks` | Q | Trend | CRO | High | Risk register filtered | `risks.view` + scope | 4 |

**Acceptance criteria (IMP).**
- IMP-01 counts a retirement only with the decision link; planned decisions alone count 0 retirements.
- IMP-03 weights are visible in the definition drawer.

### 3.5 Financial (FIN). Money KPIs require `costs.view`; benefit KPIs also require `benefits.view`

| ID | KPI | Formula / denominator | Sources | Period | Baseline & target | Owner / verifier | Confidence | Drill-down | Ph |
|---|---|---|---|---|---|---|---|---|---|
| FIN-01 | Realised benefits (cash) | Σ `benefits.realised_amount` where `status = realised`, `benefit_type ∈ {cost_saving, revenue}`, `financial_period` in the selected FY | `benefits` (new) | FY/Q; quarterly | Target = Σ validated forecast for the FY | Benefit owner / **Finance confirms** | High (Finance-confirmed) | Benefit list → decision → evidence | 4 |
| FIN-02 | Realised cost avoidance | as FIN-01 with `benefit_type = cost_avoidance` and a documented counterfactual | `benefits` | FY | — | Finance | High | as FIN-01 | 4 |
| FIN-03 | Benefits pipeline | Σ amount by status ∈ {forecast, estimated, validated}, **reported separately per status, never summed**; includes CR-04 planned savings as Forecast until superseded by a benefit | `benefits`, `assessment_decisions` | FY | — | Benefits Realisation Office | By status | Pipeline list | 1 (planned), 4 |
| FIN-04 | Benefit realisation rate | Σ realised ÷ Σ validated forecast for benefits whose expected realisation fell in the period | `benefits` | FY | Target ≥ 80% | Finance | High | Benefit variance list | 4 |
| FIN-05 | Run-rate cost change | Σ annual run cost of live assets (`costTotalAnnual` + infra `operatingCost`, `is_live_in_fiscal_year`) current FY vs baseline FY snapshot | cost fields, `lifecycle.py`, `metric_snapshots` | FY | Target −5% per year | Finance + owners | Medium (recorded costs) | Cost treemap | 5 |
| FIN-06 | Transformation programme cost | Σ `ppm_cost_lines.actual` in the FY for initiatives in the ROI scope (D-15) | PPM, Initiative tag or subtype | FY/Q | Budget | PMO + Finance | High | Initiative cost | 1 (FY fix), 4 |
| FIN-07 | Budget execution | FY actual ÷ FY budget (CR-03) | PPM | FY/Q | 90-105% | PMO | High | Initiative | 1 |
| FIN-08 | ROI | (Σ FIN-01 + FIN-02, **attributable** per the method in D-14 − FIN-06) ÷ FIN-06, same period(s) | FIN-01/02/06 | FY (rolling 3 FY option) | Ratified by CFO | CFO | Only shown when all inputs are Finance-confirmed; otherwise "Not available" | ROI composition | 4 |
| FIN-09 | Investment alignment | FIN-06 spend on initiatives linked to a strategic Objective ÷ FIN-06 | `relInitiativeToObjective`, PPM | FY | Target ≥ 90% | Portfolio management | High | Unaligned spend | 2 |
| FIN-10 | Productivity benefits (non-cash) | Σ hours or FTE-equivalent from `benefits` with `benefit_type = productivity`; **reported separately**, never in FIN-01 or FIN-08 | `benefits` | FY | — | Benefit owner | Medium | Benefit list | 4 |

**Acceptance criteria (FIN).**
- No total mixes statuses or types.
- FIN-08 is hidden unless every contributing benefit is `realised` and Finance-confirmed and FIN-06 covers the same period.
- Every money value shows its currency.
- A restricted user without `costs.view` sees "Restricted", not numbers.

### 3.6 Services and process automation (SVC)

| ID | KPI | Formula / denominator | Sources | Period | Baseline & target | Owner | Confidence | Drill-down | Auth | Ph |
|---|---|---|---|---|---|---|---|---|---|---|
| SVC-01 | Service digitalization mix | Active `GovService` by digitalization level **Digital / Hybrid / Manual / Not assessed** (source D-08); headline = Digital ÷ assessed | GovService (`serviceStatus = active`), digitalization field or derived `deliveryChannel` | Q | Target Digital ≥ 70% | Service owners / Digital Office | Medium | Service catalogue filtered | scope | 5 |
| SVC-02 | Process automation mix | Eligible processes (D-09) by `automationLevel` **Fully / Partially / Manual / Unknown–not assessed** (missing value = Unknown) | `BusinessProcess.automationLevel` | Q | Target +10 pts fully per year | Process Excellence | Medium (self-assessed) | Process map filtered | `reports.bpm_dashboard` + scope | 2 (landing), 5 |
| SVC-03 | Manual process reduction | Δ count of manual eligible processes vs FY baseline snapshot | SVC-02 + `metric_snapshots` | Q | −20% per year | Process Excellence | Medium | Processes changed level | as SVC-02 | 5 |
| SVC-04 | Process maturity (assessed) | Mean of the latest `process_assessments.overall_score` for eligible processes assessed within 12 months; coverage shown | `process_assessments` | Semi-annual | Target per owner | Process owners | Medium; coverage = assessed ÷ eligible | Process → assessment | `bpm.view` | 5 |
| SVC-05 | Process documentation coverage (specialist) | Eligible processes with a published BPMN flow ÷ eligible (CR-10) | `process_flow_versions` | Q | — | BPM admin | High | Process list | as SVC-02 | 5 |
| SVC-06 | Channel maturity | `Channel.channelMaturity` mix (basic → proactive) | Channel cards | Semi-annual | — | CX owner | Medium | Channels | scope | 5 |

**Acceptance criteria (SVC).**
- SVC-01 and SVC-02 are never combined into one figure.
- Missing classification shows as "Not assessed" / "Unknown".
- An eligible-process rule applies (default: subtype `process` only, excluding `category` / `group` / `variant`; D-09).

### 3.7 Portfolio health (PRT, specialist page)

| ID | KPI | Formula | Sources | Auth | Ph |
|---|---|---|---|---|---|
| PRT-01 | Data completeness (CR-08) | Mean of per-type mean `data_quality`, visible types | `cards.data_quality` | scope | 1 |
| PRT-02 | Lifecycle mix and past planned EOL (CR-09) | Current phase distribution; count past `endOfLife` | lifecycle | scope | 1 |
| PRT-03 | Vendor support exposure (CR-09) | Live tech assets with support expired or expiring in 12 months ÷ assets with EOL coverage; coverage % | `eol_service.resolve_eol_statuses`, `card_flags` | scope | 5 |
| PRT-04 | Repository review status (CR-07) | Approval-status mix | `approval_status` | scope | 1 |
| PRT-05 | Application TIME position | Count and annual cost by `timeModel` | Application | scope + `costs.view` for cost | 5 |

### 3.8 Decisions and escalations (DEC)

| ID | KPI / list | Rule | Sources | Auth | Ph |
|---|---|---|---|---|---|
| DEC-01 | Strategic risks requiring escalation | Open (D-04) risks with residual (else initial) level `critical`, or `high` and past `target_resolution_date`, or tagged with the escalation tag group (D-04); ranked by level, then age | `risks`, `risk_cards`, tags | `risks.view` + scope | 2 |
| DEC-02 | Decisions pending | ADR `in_review` / awaiting signatures; ARB `scheduled` / `deferred`; exceptions `requested`; with age and owner | ADR, ARB, exceptions | per source + scope | 2 |
| DEC-03 | Investment decisions pending | Initiatives at an unapproved ADM gate or with an investment-gate status pending (D-11) | `adm_phases`, Initiative | `adm.view` + scope | 3 |
| DEC-04 | Dependencies at risk | In-flight initiatives whose predecessor (`ppm_dependencies`, `relInitiativeSuccessor`) is Off Track or Not reported | PPM | `ppm.view` + scope | 5 |
| DEC-05 | Cross-department issues | Escalated or deferred items whose subject relates to ≥ 2 organisations (D-07) | DEC-01/02 + org relations | as sources | 5 |

**Acceptance criteria (DEC).**
- Each row shows owner, age, due date, consequence (cost, objective or level) and a link that opens the record.
- Items the caller cannot read do not appear in the list or in its count.
