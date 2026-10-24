# Existing dashboard assessment

**Scope.** The Dashboard module at `/` (`frontend/src/features/dashboard/Dashboard.tsx`) and its four tabs: Overview, Executive, My Workspace, Admin. Assessment date 2026-10-22, against the working tree on top of `4bf4807c` (the Executive tab is an uncommitted phase-one build).

**Evidence labels used throughout this folder**

- **[Confirmed]**: verified in source code, and where stated also against the running demo instance (NexaTech seed, local PostgreSQL 18).
- **[Recommendation]**: proposed change; nothing has been implemented.
- **[Assumption]**: inferred, not verified; needs confirmation by the named owner.

**Inspection method.** Source code was read for all four tabs. The **Executive tab was visually inspected** in Chrome at 1280 px in English on 2026-10-22. The **Overview, My Workspace and Admin tabs were not visually inspected** in this assessment; their findings come from code. **Arabic / RTL was not visually inspected.**

---

## 1. Module structure [Confirmed]

| Tab | Component | Data source | Gate |
|---|---|---|---|
| Overview | `OverviewTab.tsx` | `GET /reports/dashboard` (`backend/app/api/v1/reports.py:128`) | `reports.ea_dashboard` |
| Executive | `executive/ExecutiveTab.tsx` | `GET /reports/executive` (`backend/app/api/v1/executive_dashboard.py`) | `reports.executive_dashboard` (new key, admin-only by default) |
| My Workspace | `workspace/WorkspaceTab.tsx` + 8 sections | `GET /reports/my-workspace`, `/favorites`, `/cards/my-stakeholder`, todos, surveys, saved reports | any signed-in user |
| Admin | `admin/AdminTab.tsx` + 7 sections | `GET /reports/admin-dashboard` (`reports.py:389`), `/reports/data-quality`, `/reports/stakeholder-directory` | `admin.users` |

Tab selection, per-user default-tab pinning (`users.ui_preferences.dashboard_default_tab`) and permission-based tab hiding all live in `Dashboard.tsx:65-180`.

The Overview also embeds `AdmDashboardWidget` (`features/adm/AdmDashboardWidget.tsx`, `GET /adm/my-actions`), which lists the caller's open TOGAF ADM phase actions.

## 2. Overview tab: widget-by-widget

Every aggregate is computed in `reports.py:128-270` over ACTIVE cards the caller can read (`CardReadScope`, module mode).

| # | Widget | What it measures | Formula and denominator | Level | Exec value | Issues | Verdict |
|---|---|---|---|---|---|---|---|
| O1 | **Total Cards** | Size of the repository | `count(cards WHERE status=ACTIVE)`; no denominator | Activity | Low | **Includes cards of hidden card types** (118 of 391 in the demo; see §6.1). No scope or segment. | Relocate to the Admin/EA tab |
| O2 | **Avg Completion** | Mean `cards.data_quality` | `avg(data_quality)` over ACTIVE cards | Output (data stewardship) | Low for a CEO, high for an EA lead | **Label conflict**: the UI calls the same figure "Avg Completion" and "data quality". It is weighted field **completeness** from `fields_schema` weights, not accuracy or validity. Unweighted mean across all types, so 90 capability cards weigh more than 58 applications. | Retain for the EA view; rename to "Data completeness" |
| O3 | **Approved** (count) | Cards in approval state APPROVED | `count(approval_status='APPROVED')` | Activity | Low | Count with no denominator. In the demo **100% of cards are APPROVED** (the seed approves everything), so it cannot discriminate. Approval is a repository review state, not architecture compliance. | Improve: show as % plus "approved within N days" |
| O4 | **Broken** (count) | Approved cards edited since approval | `count(approval_status='BROKEN')` | Activity | Low | Useful data hygiene metric, meaningless to a CEO | Relocate to the Admin/EA tab |
| O1-O4 trend | 30-day trend arrows | Change vs the snapshot closest to 30 days ago | `kpi_snapshot_service.get_comparison_snapshot(days_ago=30)` | n/a | Medium | Only 4 metrics are snapshotted (`models/kpi_snapshot.py`). Trends are hidden for restricted readers (correct, `reports.py:255`). The demo has 1 snapshot, so it shows "Collecting". | Retain the mechanism and extend it (see TECHNICAL_READINESS.md) |
| O5 | **Needs your attention** band | Broken approvals, low-quality cards (DQ < 50), "end-of-life" cards, drafts | `OverviewTab.tsx:228-262` | Activity | Low | **"End-of-life cards" counts cards whose own lifecycle `endOfLife` date has passed** (current phase, `_current_lifecycle_phase`). It is not vendor end-of-support from `/reports/eol` (endoflife.date). Two different "EOL" meanings in one product. | Retain in the EA view; rename to "Retired (past end-of-life date)" |
| O6 | **Cards by Type** bar chart | Distribution by type | `group_by(Card.type)` | Activity | Low | Inventory size per type. Click-through to the filtered inventory is good. | Relocate |
| O7 | **Approval Status** donut | DRAFT / APPROVED / BROKEN / REJECTED split | as O3 | Activity | Low | as O3 | Relocate |
| O8 | **Completion Distribution** bar | Count of cards per DQ bucket (0-25, 25-50, 50-75, 75-100) | `reports.py:159-174`, SQL `between(25, 49.999)` | Output | Low | Bucket boundaries are float approximations (a 49.9995 score falls in no bucket). Negligible in practice. | Relocate |
| O9 | **Lifecycle Overview** bar | Cards per current lifecycle phase | `reports.py:176-193` | Activity | Medium | "Not set" is 118 of 391 in the demo (30%): the chart is dominated by missing data. | Retain; show "not set" as a data gap |
| O10 | **Recent Activity** | Last 20 events, scrubbed by read scope | `reports.py:195-242` | Activity | None for a CEO | Operational feed | Relocate to My Workspace |
| O11 | **My ADM actions** widget | Caller's open ADM phases | `/adm/my-actions` | Activity (personal) | None for a CEO | Personal work queue, not an organisational KPI | Relocate to My Workspace |

**Verdict.** [Confirmed] The Overview is a well-built **repository health dashboard** for EA practitioners. Every measure is activity or output level. None is an outcome, impact or financial value. This is appropriate for its audience, but it is not an executive dashboard. [Recommendation] Keep it as the "EA repository health" view and do not try to make it CEO-facing.

## 3. Executive tab (phase one, uncommitted)

Built on 2026-10-22. Backend: `backend/app/services/executive_dashboard.py` (pure builders) and `backend/app/api/v1/executive_dashboard.py` (orchestration). Frontend: `frontend/src/features/dashboard/executive/ExecutiveTab.tsx`.

| # | Widget | Formula (confirmed in code) | Level | Exec value | Issues | Verdict |
|---|---|---|---|---|---|---|
| E1 | Hero counts (cards, initiatives, processes) | `executive_dashboard.py:65` `load_portfolio`; PPM initiatives; BPM processes | Activity | Low | Same hidden-type inclusion as O1 | Replace with the strategic headline (see RECOMMENDED_DASHBOARD_STRUCTURE.md) |
| E2 | Avg data quality + ring | `avg(data_quality)` | Output | Low | Shows "61.6%" and a ring reading "62%" for the same number (redundant). Completeness, not quality. | Move to Portfolio Health |
| E3 | Approved % + ring | `APPROVED / total` | Activity | Low | 100% in the demo: no signal. See O3. | Remove from the CEO view |
| E4 | Processes with a published flow % | `with_diagram / total_processes` (`bpm_dashboard_service.py:21`) | Output (documentation) | Low | Measures BPMN **documentation** coverage, not automation or performance. Placed beside outcome tiles, a CEO may read it as "process maturity". | Move to Services & Automation as a documentation indicator |
| E5 | Initiatives off track | `health_schedule.offTrack` from the **latest PPM status report** (`ppm_portfolio_service.build_dashboard:494`) | Outcome (delivery) | High | **Misleading by omission**: in the demo 14 of 20 initiatives have **no status report**, so "0 off track" hides that 70% are unreported. A second, inconsistent source of truth also exists: `Initiative.attributes.initiativeStatus` (onTrack / atRisk / offTrack / onHold / completed), which this tile ignores. | Improve: show reporting coverage beside it; define one source of truth |
| E6 | Open critical & high risks | open = status not in {closed, accepted}; level = residual, else initial (`executive_dashboard.py:139`) | Outcome (exposure) | High | "Open" includes `mitigated` and `monitoring`, so the definition needs CRO sign-off. Risks are counted through `load_filtered_risks`, consistent with the register. | Retain; agree the definition |
| E7 | Planned savings (tile + panel) | `sum(assessment_decisions.planned_savings)` over **active and completed** assessments, readable ACTIVE cards (`executive_dashboard.py:167-210`) | Forecast (financial) | High, if trustworthy | Correctly tagged "Estimated, not realised". **Double-counting risk [Confirmed in logic]**: the same application in two assessments has its savings summed twice; there is no de-duplication by card. No currency or period, and no confidence or approval status. | Improve: dedupe per card (latest decision); add a financial status |
| E8 | Portfolio: largest card types + lifecycle donut | `by_type` + lifecycle | Activity | Low | **Total ≠ sum of bars [Confirmed]**: the centre total (391) includes hidden-type cards that the frontend type list cannot render. | Move to Portfolio Health |
| E9 | Risk exposure donut | open risks by level | Outcome | High | Good. No trend or target. | Retain |
| E10 | Delivery: stacked RAG schedule/cost/scope | latest status report per initiative | Outcome | High | Same "no report" dominance as E5 (grey is 70% of each bar). | Retain; lead with reporting coverage |
| E11 | Budget vs actual + "% spent" ring | `sum(ppm_budget_lines.amount)` vs `sum(ppm_cost_lines.actual)` (`ppm_portfolio_service.sum_budget_actual:253`) | Financial (spend) | High | **Not period-bound [Confirmed]**: all fiscal years of budget against all actuals ever recorded, so "54% spent" mixes years. It also ignores `Initiative.costBudget/costActual` attributes, a second inconsistent source. | Improve: fiscal-year bound, using `fiscal_year.py` |
| E12 | Processes: automation donut + maturity bars | `BusinessProcess.attributes.automationLevel / maturity` | Output (self-assessed classification) | Medium | Self-declared categorical values with no evidence or assessment date. Option labels and colours correctly come from the metamodel. | Retain; label as "self-assessed" |
| E13 | Rationalization TIME donut | count of decisions per `time_decision` | Output (decision) | Medium | Shows decided intent, not executed retirements. | Retain; pair it with "executed" |
| E14 | Footnote + generated time | static text + `generated_at` | n/a | n/a | Good transparency practice | Retain |

**Verdict.** [Confirmed] Phase one moves the tab from activity to some **outcome** measures (delivery health, risk exposure) and one **forecast** financial figure. It still has no targets, baselines, periods, trends, ownership or decisions, and three measures are misleading as built (E5, E7, E11). It is a credible **foundation**, not yet a CEO dashboard.

## 4. My Workspace tab [Confirmed, code only]

Personal and correctly per-user: favourites, todos, pending surveys, created cards, roles held, saved reports, recent activity on my cards, needs-attention. `GET /reports/my-workspace` excludes hidden card types (`reports.py:365-371`). **Executive value: none by design.** [Recommendation] Retain unchanged. It is the right home for O10 and O11.

## 5. Admin tab [Confirmed, code only]

KPI strip (active users, cards without stakeholders, overdue todos, stuck approvals), top contributors, stakeholder coverage by type, idle users and pending SSO invitations, approval pipeline by type, recent system activity, oldest overdue todos, and stakeholder directory. Gated on `admin.users`, excluding hidden types (`reports.py:407-430`). **Executive value: low**, but two measures are governance-relevant: *stakeholder coverage* (accountability) and *stuck approvals > 30 days* (governance throughput). [Recommendation] Surface those two, aggregated, in the EA Governance view; keep the rest admin-only.

## 6. Cross-cutting findings

### 6.1 Hidden card types are counted inconsistently [Confirmed]

`/reports/dashboard` and `/reports/executive` count every ACTIVE card. `/reports/my-workspace` and `/reports/admin-dashboard` exclude `card_types.is_hidden`. In the demo, 16 types are hidden after the NORA profile was applied, and 118 active cards belong to them (Organization 28, ITComponent 32, BusinessContext 18, TechCategory 16, Provider 15, Journey 5, Platform 4). The same "total cards" therefore differs by tab, and the Executive total does not match its own bar chart. [Recommendation] Decide one rule (most likely: exclude hidden types from every landscape KPI) and apply it everywhere.

### 6.2 No targets, baselines or reporting period anywhere [Confirmed]

No dashboard widget shows a target, threshold, baseline or period. `kpi_snapshots` holds 4 repository metrics. The metamodel already has a **`KPI` card type** with `baselineValue`, `targetValue`, `currentValue`, `direction`, `measurementFrequency` and `lastMeasuredDate`, plus relations to Objective, Initiative, GovService and BusinessProcess. **Nothing on the dashboard reads it**, and the demo has 0 KPI cards.

### 6.3 Two sources of truth for the same fact [Confirmed]

| Fact | Source A | Source B |
|---|---|---|
| Initiative health | `ppm_status_reports` (latest) | `Initiative.attributes.initiativeStatus` |
| Initiative budget / actual | `ppm_budget_lines` / `ppm_cost_lines` | `Initiative.attributes.costBudget / costActual` (PPM syncs these, per CLAUDE.md) |
| "End of life" | card lifecycle `endOfLife` phase | vendor support from endoflife.date (`/reports/eol`) |
| Automation level | `BusinessProcess.automationLevel` | `process_assessments.automation` (scored) and `GovService.automationLevel` |

### 6.4 Data freshness [Confirmed]

Values are computed live on each request. There is no data-as-of date per source, no "last status report older than N days" signal and no stale flag. `card_flags.py` already defines **stale** for the inventory, and `/reports/freshness` exists, but neither is used on the Executive tab.

### 6.5 Visual note [Confirmed, Executive tab, English, 1280 px]

After the 2026-10-22 redesign, the Executive tab renders a gradient hero, KPI tiles with rings, donuts and a stacked RAG chart without overflow. The visual quality is acceptable. The **content** is the gap: see UI_UX_REVIEW.md.
