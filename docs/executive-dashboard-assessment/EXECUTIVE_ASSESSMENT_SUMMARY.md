# Executive assessment summary

**Purpose.** An assessment of the Turbo-EA Dashboard, especially the Executive tab, for transformation into a decision-oriented executive dashboard. Documentation only: no code, schema, UI, test or build changes were made.

**Evidence.** Source code across the whole application; the live demo database (NexaTech seed + NORA profile); visual inspection of the Executive tab (English, 1280 px). The Overview, My Workspace and Admin tabs, Arabic RTL, mobile and dark mode were **not** visually inspected. Findings are labelled [Confirmed], [Recommendation] or [Assumption] in the detailed files.

**Relationship to earlier documents.** This set supersedes the 2026-10-21 readiness documents in this folder (`ASSESSMENT_SUMMARY.md`, `GAP_ANALYSIS.md`, `EXECUTIVE_KPI_CATALOG.md` and others). It extends them with a widget-level validation of the phase-one Executive tab and a corrected view of what the metamodel already supports (KPI, GovService and maturity entities).

## 1. What is good about the existing dashboard?

- **Sound engineering base** [Confirmed]: permission-gated tabs; every aggregate filtered by the caller's read scope; money gated by `costs.view` on the Executive tab; bilingual EN/AR strings with RTL-aware charts; metamodel-driven labels and colours.
- **The Overview is a solid EA repository-health view** for practitioners (data completeness, approvals, lifecycle, attention band with filtered drill-downs, 30-day trends).
- **The phase-one Executive tab introduces outcome measures** (delivery RAG, risk exposure), labels planned savings honestly as estimated, refuses to show zeros for disabled modules, and is visually clean (gradient hero, KPI rings, donuts, stacked RAG).
- **The data model is richer than the dashboard uses**: a `KPI` card type with baseline, target and current values; `GovService` with automation level; dated maturity assessments; strategy cascade relations; ADR, ARB, exceptions, ADM gates; rationalization decisions; improvement opportunities; event history.

## 2. What is missing from the CEO's perspective?

- **No targets, baselines, periods or trends** on any executive KPI.
- **No realised or validated financial value**: no benefit ledger, no ROI, no realisation rate.
- **No decision or escalation view**: nothing says what the CEO must decide.
- **No impact measures**: 0 of 22 dashboard KPIs measure impact. All are activity, output, outcome or forecast.
- **No verifiable governance → outcome chain**: decisions end at "signed", with no implementation actions or outcome link.
- **No strategic headline**: the page opens on repository size, not on progress against the strategy.

## 3. Which KPIs are misleading, unclear or irrelevant?

| KPI | Problem |
|---|---|
| Initiatives off track ("0 of 20") | 14 of 20 initiatives have no status report; "0" overstates health. It ignores the `initiativeStatus` attribute. |
| Budget vs actual / "54% spent" | Sums every fiscal year; not period-bound |
| Planned savings ($590K) | Correctly marked estimated, but duplicates across assessments are summed; no currency or approval |
| Total cards (391) | Includes 118 cards of hidden types; differs from My Workspace and Admin; ≠ sum of the type chart |
| Approved % (100%) | Repository review state presented beside outcomes; the seed approves everything |
| "Avg Completion" vs "data quality" | Same number, two names; it is completeness, not quality |
| "End-of-life cards" | Past their own lifecycle date, not vendor end-of-support |
| Processes with a published flow (2.3%) | Documentation coverage, easily read as process maturity |
| Repository counts, recent activity, ADM actions | Irrelevant to a CEO (keep them in the EA and personal views) |

## 4. Which existing features and data can be reused?

`KPI` cards (targets, owners, Objective / Initiative / Service / Process relations) · `GovService` (digitalized services) · BusinessProcess automation and maturity · maturity assessments · strategy cascade · PPM status, WBS, budget and cost · rationalization decisions · ADR, ARB, exceptions, compliance scan, ADM gates, approval steps · risk register and mitigation tasks · improvement opportunities · events and `kpi_snapshots` · fiscal-year rules · todos (as decision actions) · tag groups (escalation) · surveys (data collection) · report export (board pack) · phase-one tiles and charts · RTL chart helpers.

## 5. Which new capabilities are needed?

1. **KPI history**: `kpi_measurements` for KPI cards, plus a key/value snapshot fact table.
2. **Benefits register**: financial status lifecycle (forecast → estimated → validated → realised), approver, evidence, period and attribution, linked to existing decision records.
3. **Decision → action tracking**: reuse todos linked to ADR / ARB.
4. **Small field additions**: `realized_at` (opportunities), milestone achievement (or derive from PPM WBS), investment-gate timing (or ADM gates), escalation (tag group).
5. **Read-scope fixes** in the fork modules that query cards without `CardReadScope` (NORA program, rationalization, ARB, tech standards, maturity, improvement opportunities, ADM, roadmaps), and a `costs.view` gate on `/reports/ppm/dashboard` money.

## 6. What changes would deliver the highest executive value?

1. A **Decisions & Escalations** panel on the landing page (escalated risks, pending signatures and ARB items, bottlenecks). Data mostly exists.
2. **Integrity fixes** to delivery health, budget and planned savings, so no executive is misled.
3. **Targets and trends** through KPI cards and history, which turn numbers into performance.
4. **Decision → action tracking**, the first verifiable measure of governance effectiveness.
5. A **benefits register with Finance validation**, the only defensible route to savings and ROI.

## 7. Recommended implementation sequence

| Phase | Content | Size |
|---|---|---|
| 0 | Ratify KPI definitions, owners, targets, financial taxonomy, attribution policy, and the hidden-type and source-of-truth rules; data stewardship plan | S |
| 1 | Integrity quick wins (coverage-first delivery health, FY-bound budget, deduplicated savings, hidden-type rule, labels, PPM cost gate, read-scope fixes); commit phase one with tests | S-M |
| 2 | KPI cards for targets + KPI history + snapshot facts; KPI tile standard; period selector; CEO Overview and Decisions pages | M |
| 3 | Decision actions (todos), governance effectiveness page | M |
| 4 | Benefits register and Financial & ROI page | L |
| 5 | Services & Automation, Business Impact, Transformation and Portfolio Health pages | M-L |
| 6 | Narrative insights, board-pack export, accessibility and bilingual RTL QA, performance | M |

**Recommended architecture**: extend the existing Dashboard → Executive tab with purpose-built, scope-aware aggregate endpoints, plus two narrow supporting capabilities (KPI history, benefits register). No separate executive database or frontend, and no duplicate entities.

## Document index

| File | Content |
|---|---|
| EXISTING_DASHBOARD_ASSESSMENT.md | Widget-by-widget review of all four tabs, with verdicts |
| KPI_INVENTORY_AND_VALIDATION.md | Every current KPI: formula, denominator, demo value, value class, validation |
| EXECUTIVE_KPI_FRAMEWORK.md | 44 proposed KPIs across five dimensions, with formulas, sources, owners and proposed targets |
| DATA_AND_FUNCTIONAL_GAP_ANALYSIS.md | Reusable capabilities, relations, gaps G1-G13, minimum schema extensions |
| EA_GOVERNANCE_AND_ROI_MODEL.md | Value-chain traceability, governance effectiveness levels, benefit lifecycle, attribution |
| UI_UX_REVIEW.md | CEO-perspective UX review, accessibility, RTL, component reuse |
| RECOMMENDED_DASHBOARD_STRUCTURE.md | Eight-page executive structure and the fate of each current component |
| TECHNICAL_READINESS.md | APIs, aggregation, history, access control, audit, performance, security |
| IMPLEMENTATION_RECOMMENDATIONS.md | Phased plan, value-per-effort ranking, risks |
