# Decision log

> **Status 2026-10-22 (Phase 1 decision resolution).** Eight decisions were approved by the business owner: D-01, D-02, D-05, D-06, D-22, D-24, D-30 (the Phase 1 set) and D-18 (by the instruction to preserve the fork's EN/AR language policy). They are recorded verbatim in §2 with their original IDs. **22 decisions remain unresolved** in §3, plus one new open item (D-31) raised by D-24. Recommendations in `FINAL_DECISION_RECOMMENDATIONS.md` are not approvals.

**Legend.** **Confirmed** = stated by the business owner (the user) in the planning brief or earlier in this engagement. **Approved** = explicitly approved by the business owner on the date shown. **Unresolved** = requires approval before the phase shown. **B** = blocking for that phase. "Recommendation" is the planner's proposal, **not** a decision.

## 1. Confirmed decisions

| ID | Decision | Source | Date |
|---|---|---|---|
| C-01 | One unified executive dashboard inside Turbo-EA. Top-level tabs Overview, Executive, My Workspace, Admin are kept; Executive expands into eight pages. | Planning brief §2 | 2026-10-22 |
| C-02 | Use existing KPI cards for definitions, owners, baselines, targets and relationships; no duplicate business entities. | Brief §1, §5 | 2026-10-22 |
| C-03 | No generic formula engine unless justified by the architecture. | Brief §5 | 2026-10-22 |
| C-04 | Missing data appears as "Not available" / "Not reported", never as zero. | Brief §5 | 2026-10-22 |
| C-05 | Security remediation precedes reuse of affected APIs. | Brief §4 | 2026-10-22 |
| C-06 | Benefits distinguish forecast, estimated, validated, realised, realised savings, cost avoidance and non-financial outcomes; planned savings are not realised savings. | Brief §7 | 2026-10-22 |
| C-07 | **No arbitrary fixed attribution percentages.** This supersedes the assessment's proposed 10-30% share (`EA_GOVERNANCE_AND_ROI_MODEL.md` §3.3). | Brief §8 | 2026-10-22 |
| C-08 | ROI uses verified, attributable financial benefits and comparable programme costs over the same period. | Brief §8 | 2026-10-22 |
| C-09 | Productivity improvements are reported separately unless actual financial savings are demonstrated. | Brief §8 | 2026-10-22 |
| C-10 | Service digitalization (Digital / Hybrid / Manual) is separate from process automation (Fully / Partially / Manual / Unknown). | Brief §9 | 2026-10-22 |
| C-11 | Bilingual English / Arabic with RTL; landing page limited to about six measures; specialist indicators in specialist views. | Brief §2, §10 | 2026-10-22 |
| C-12 | Initiative health has four states: On Track, At Risk, Off Track, Unknown / Not reported. | Brief §3 | 2026-10-22 |
| C-13 | Currency definitions and SAR formatting are required. | Brief §3 | 2026-10-22 |
| C-14 | Implementation follows the project's established validation approach (tests, CI gates). The phase-one "no tests" instruction applied to that prototype only. | Brief §11 (supersedes the earlier instruction for implementation phases) | 2026-10-22 |
| C-15 | Prior assessment documents are preserved and superseded versions identified. | Brief §1 | 2026-10-22 |
| C-16 | Organisation / department filters, reporting periods and KPI drill-downs are required. | Brief §2 | 2026-10-22 |

## 2. Approved decisions (original IDs preserved)

| ID | Approved decision (owner's wording, condensed only where marked) | Approved | Notes on application |
|---|---|---|---|
| D-01 | Approve consistent exclusion of hidden or unauthorized cards from dashboard metrics and aggregation results. | 2026-10-22 | Unauthorized = `CardReadScope` (existing); hidden = `card_types.is_hidden`. Applies to totals, breakdowns, charts, drill-downs, exports. |
| D-02 | Approve four initiative reporting states: On Track, At Risk, Off Track, and Unknown/Not Reported. Reporting coverage must be displayed separately. Reporting staleness must be configurable; do not invent a deadline. | 2026-10-22 | A staleness setting with **no default value**. While unset, only an initiative with no report is Not Reported. A missing or stale report is never counted as healthy and never auto-marked At Risk. Source of truth: PPM reports when enabled, `initiativeStatus` otherwise (as planned; owner may revisit). |
| D-05 | Approve currency-aware reporting. Preserve original currency metadata. Do not relabel or convert existing monetary values until verified. | 2026-10-22 | Payloads carry `currency`; records with their own currency (e.g. `Project.currency`) keep it; **no cross-currency sums** (totals per currency, or "mixed currencies, not totalled"); the instance setting is switched to SAR only after Finance verification. |
| D-06 | Follow the existing fiscal-year configuration. | 2026-10-22 | `general_settings.fiscalYearStart` via `services/fiscal_year.py`. |
| D-18 | Preserve the EN/AR language policy established by the Turbo-EA fork. | 2026-10-22 | New strings in `en` and `ar` only (`frontend/src/i18n/i18n.test.ts` pins `["en", "ar"]`; commit `82e09664`). CLAUDE.md's 10-locale text does not apply to this fork. |
| D-22 | Preserve the existing uncommitted changes safely. Plan separate logical commits for the Windows fix, responsive navigation, Executive prototype, and documentation. Do not perform commits yet. | 2026-10-22 | Procedure in `PHASED_DELIVERY_PLAN.md` Phase 1 step 1. Commits require a separate instruction. |
| D-24 | Deduplicate planned savings using benefit/application identity and financial period. Conflicting estimates must be flagged for reconciliation. Do not automatically select the latest or lowest amount as authoritative. Exclude unresolved conflicts from authoritative financial totals. | 2026-10-22 | Identity = linked benefit if present, else application (`card_id`), per financial period. Conflicts are listed with all candidate values and excluded from totals until reconciled. The period source for planned savings is open item **D-31**. |
| D-30 | Prevent restricted information from being disclosed through governance records. Use linked-card redaction where the independently accessible record remains meaningful and safe; omit records where redaction cannot prevent disclosure. Preserve hidden links and underlying records. | 2026-10-22 | Per-record-type application in `SECURITY_REMEDIATION_PLAN.md` §2. Hidden links are kept on write; no record is deleted; omitted records stay visible to authorized users. |

## 3. Unresolved decisions requiring approval

| ID | Question | Options | Recommendation | Owner | Needed by |
|---|---|---|---|---|---|
| D-03 | Who receives `reports.executive_dashboard`, `benefits.*`, `kpis.measure`? Create an "Executive" default role? | — | New "Executive" and "Finance" roles; existing roles unchanged | CEO office + Chief Architect | Phase 2 **B** |
| D-04 | Definition of "open risk" and the escalation mechanism | open = not closed / accepted (current) vs also excluding mitigated; escalation via tag group vs new fields | Keep the current definition, show "unmitigated" separately; tag group "Escalation" | CRO | Phase 2 **B** |
| D-07 | Organisation filter type: `Organization` (hidden in the NORA profile, used by demo relations) vs `OrganizationalUnit` (NORA) | setting-driven; migrate relations | Admin setting choosing the org type; plan a data migration if switching | Chief Architect | Phase 2 **B** |
| D-08 | Service digitalization source; GovService canonical definition (`seed.py:4840` vs `nora_profile.py:4462`) | (a) new `digitalizationLevel` field; (b) derive from `deliveryChannel` | (a) explicit field; canonical = NORA profile definition | Digital Office | Phase 5 **B** |
| D-09 | Eligible processes for automation KPIs, and the automation threshold | subtype `process` only vs all levels | subtype `process`, active only | Process Excellence | Phase 2 |
| D-10 | EA review "in scope" rule | budget threshold / subtype / tag | subtype program or project, plus an admin budget threshold | Chief Architect | Phase 3 **B** |
| D-11 | Early-engagement gate | ADM Architecture Vision approval vs `Initiative.startDate` vs a new investment gate | ADM gate, fallback startDate | EA Governance Office | Phase 3 |
| D-12 | Benefit storage | dedicated tables vs a `Benefit` card type | dedicated tables | Solution architect + CFO | Phase 4 **B** |
| D-13 | Decision actions | todos + `source_kind` / `source_id` vs a new table | todos extension | Chief Architect | Phase 3 **B** |
| D-14 | Attribution method (no fixed %) | method enum in `BENEFITS_AND_ROI_SPECIFICATION.md` §5 | Adopt the enum; Finance assesses per benefit with rationale | CFO + Chief Architect | Phase 4 **B** |
| D-15 | ROI programme-cost scope and window | which initiatives (tag `roiScope`), EA office cost inclusion, FY vs rolling 3-FY | tag-based scope; FY plus optional rolling 3-FY | CFO | Phase 4 **B** |
| D-16 | Technology debt index components and weights | — | Equal weights v1, reviewed after one quarter | CTO | Phase 4 |
| D-17 | KPI target values (all are proposals) | — | Owners ratify per KPI | Each KPI owner | Phase 2 **B** (reclassified from Phase 0, which was circular) |
| D-19 | Snapshot storage | replace `kpi_snapshots` with `metric_snapshots` (migrate) vs keep both | replace and migrate | Solution architect | Phase 2 |
| D-20 | Small-group suppression threshold | 3 / 5 | 3 | CISO / data protection | Phase 2 |
| D-21 | Strategy progress source | manual `Objective.progress` vs computed from linked KPIs | manual v1, computed later | Strategy Office | Phase 2 |
| D-23 | Summary insights | rule-based vs AI-assisted | rule-based; AI optional in Phase 6 | Product owner | Phase 6 |
| D-25 | Milestone achievement source | derive from PPM WBS milestones vs add fields to `roadmap_milestones` | derive from WBS; add fields only for roadmap-only milestones | PMO | Phase 5 |
| D-26 | KPI card ↔ builder link | new `metricKey` field vs `external_id` | `metricKey` field | Solution architect | Phase 2 |
| D-27 | Arabic numerals | Arabic-Indic (locale default) vs Latin digits | Stakeholder preference | Digital Office | Phase 2 |
| D-28 | Working-day calendar for turnaround | weekdays Sun-Thu vs Mon-Fri; holidays | Sun-Thu, no holiday table v1 | EA Governance Office | Phase 3 |
| D-29 | Segregation of duties for benefit confirmation | — | Creator or estimator cannot confirm | CFO | Phase 4 |
| D-31 | Financial period of rationalization planned savings (needed to apply D-24) — `assessment_decisions` and `rationalization_assessments` carry no period field | (a) FY of assessment completion (completed) or the current FY (active), via `fiscal_year_for`; (b) add an explicit period field to assessments (schema change); (c) treat planned savings as an annualised run-rate per application (period = the FY being reported) | (a) for Phase 1; revisit (b) with the benefits register in Phase 4 | App portfolio owner + CFO | Phase 1 (CR-04) **B** |
