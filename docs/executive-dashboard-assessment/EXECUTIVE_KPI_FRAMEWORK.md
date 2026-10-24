# Executive KPI framework

**Status: proposal.** Every target and threshold below is a **proposed starting point to be ratified** by the named owner. None is implemented, and none is a benchmark. Formulas reference existing Turbo-EA entities wherever they exist. No new entity is proposed where the information already lives elsewhere (see DATA_AND_FUNCTIONAL_GAP_ANALYSIS.md).

**Availability legend**

- **A**: available now (entity, API and data exist; only aggregation needed).
- **P**: partial (the entity or field exists, but a definition, data population or history is missing).
- **N**: new capability required.

**Complexity**: L = aggregate over existing data · M = new field, rule or history · H = new workflow, entity or integration.

**Audience**: CEO · VP (business VPs and sponsors) · DTGM (Digital Transformation GM) · EA (Chief Architect and EA office) · CFO.

**Global rules** (apply to every KPI) [Recommendation]

1. Every value carries `as_of`, `period`, `source`, `calculation_version` and a confidence or status flag.
2. Every aggregate counts only cards the caller can read (`CardReadScope`), excludes hidden card types consistently, and requires `costs.view` for money.
3. Missing data renders as "Not available", never as zero.
4. A KPI's target, baseline and owner are stored once, on a **`KPI` card** (existing type, see §F), not hard-coded in the dashboard.

---

## A. Digital transformation performance

| ID | KPI | Definition and formula | Rationale | Audience | Sources / APIs | Avail. | Freq. | Proposed target | Owner | Drill-down | Cx |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | Strategy execution index | Weighted mean of `Objective.progress` (0-100), weighted by `strategicImportance` or objective priority, for strategic objectives | One number for "are we executing the strategy?" | CEO, DTGM | `Objective` cards (`progress`, `objectiveType`), `relObjectiveToPillar`, `/reports/strategy-cascade` | P (field exists; population and update discipline unknown; no history) | Quarterly | ≥ 80% of plan-to-date (proposal) | Strategy Office | Pillar → Objective → supporting Initiatives (`relInitiativeToObjective`) | M |
| A2 | Roadmap milestone achievement | Milestones achieved on or before target ÷ milestones due in period | Plan versus delivery | CEO, DTGM | `roadmap_milestones` (`target_date`, `initiative_id`) | P (**no achieved date or status on milestones**; 0 in demo) | Monthly | ≥ 85% (proposal) | Transformation Office / PMO | Roadmap → milestone → initiative | M |
| A3 | Initiative delivery health | % of in-flight initiatives on track, with **reporting coverage** shown alongside | Early warning on the transformation portfolio | CEO, VP, DTGM | `ppm_status_reports`, `/reports/ppm/dashboard` | A (coverage in demo: 6 of 20) | Monthly | ≥ 75% on track; ≥ 90% reported in 30 days (proposal) | PMO | Initiative list → PPM detail | L |
| A4 | Digital maturity index | Latest `maturity_assessments.overall_score` vs previous and vs `target_level` | Maturity improvement over time | CEO, DTGM | `maturity_assessments`, `maturity_dimension_scores` (`level`, `target_level`), `/maturity/overview` | P (module exists with dated assessments; **0 in demo**) | Semi-annual | +0.5 level per year (proposal) | Digital Office | Dimension radar → evidence | L |
| A5 | Digitalized services % | Active `GovService` with `automationLevel ∈ {fullyAutomated, partiallyAutomated}` ÷ active GovService. Fully and partially reported separately. | National digital-service mandate | CEO, VP, DTGM | `GovService` (`serviceStatus`, `automationLevel`, `serviceType`) | P (type exists; **0 cards in demo**; "digitalized" definition needs ratification) | Quarterly | Fully ≥ 70% (proposal) | Service owners / Digital Office | Service catalogue (`/reports/service-traceability`) | L |
| A6 | Process automation % | Processes at or above the agreed automation level ÷ eligible active processes | Efficiency and transformation outcome | CEO, DTGM | `BusinessProcess.automationLevel`; `process_assessments.automation` for evidence | A (classification); P (evidence and threshold) | Quarterly | +10 pts per year (proposal) | Process Excellence | Process map → process | L |
| A7 | Manual process reduction | Δ count of `automationLevel = manual` vs baseline date | Demonstrates change, not a static state | CEO, DTGM | as A6 + **history** (events or snapshots) | P (needs history; card events hold old/new attributes but no KPI fact) | Quarterly | −20% per year (proposal) | Process Excellence | Processes that changed level in period | M |
| A8 | Beneficiary experience | Channel maturity mix (`Channel.channelMaturity`) and journey improvement opportunities realised | Outcome for citizens / customers | CEO, VP | `Channel`, `BeneficiaryJourney`, `improvement_opportunities` (`journey_card_id`, status) | P (types exist; satisfaction and SLA telemetry absent) | Quarterly | Defined by the CX owner | CX / Beneficiary Experience owner | Journey → steps → opportunities | M |
| A9 | Operational efficiency (process duration) | Median `BusinessProcess.durationDays` for priority processes vs baseline | Efficiency outcome | VP, DTGM | `BusinessProcess.durationDays` | P (static field; no measured actuals) | Quarterly | −15% vs baseline (proposal) | Process owners | Process | M |

## B. Enterprise architecture governance

| ID | KPI | Definition and formula | Rationale | Audience | Sources / APIs | Avail. | Freq. | Proposed target | Owner | Drill-down | Cx |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B1 | EA review coverage | In-scope initiatives with ≥ 1 ARB review or ADR ÷ in-scope initiatives in period | Is governance applied where it matters? | CEO, EA | `arb_reviews.subject_card_id`, `architecture_decision_cards`, Initiative cards | P (links exist; **"in scope" rule undefined**) | Quarterly | ≥ 90% of initiatives above the threshold (proposal) | Chief Architect | Unreviewed initiative list | M |
| B2 | Early architecture involvement | Reviews created before the initiative's design or funding milestone ÷ reviews | Value of EA is highest early | CEO, EA | `arb_reviews.created_at`, `Initiative.startDate`, ADM phase dates (`adm_phases`) | P (**no funding or design milestone timestamp**) | Quarterly | ≥ 70% (proposal) | EA Governance Office | Late-reviewed initiatives | M |
| B3 | Governance compliance | Cards compliant with mandated standards ÷ in-scope cards | Standards adherence | EA, CTO | `/tech-standards/compliance-scan`, `tech_standards.mandate` | A (scan exists; scope and evidence semantics need confirming) | Monthly | ≥ 85% (proposal) | Domain architects | Non-compliant cards | L |
| B4 | Exceptions: open, expiring, expired | Count of `tech_standard_exceptions` by status; % approved exceptions past `expiry_date` | Controlled deviation | EA, CTO | `tech_standard_exceptions` (`status`, `expiry_date`) | A (3 in demo) | Monthly | 0 expired-but-active (proposal) | Standards owner | Exception list | L |
| B5 | Decision implementation rate | Signed ADRs or approved ARB reviews whose implementation actions are closed ÷ signed or approved decisions older than N days | Does governance change anything? | CEO, EA | ADR (`status=signed`), ARB (`approved`) + **decision actions** | N (**no decision-action entity**) | Quarterly | ≥ 80% within 180 days (proposal) | Decision owners / PMO | Decision → actions | H |
| B6 | Corrective-action closure | Corrective actions closed by due date ÷ due | Governance effectiveness | EA, CRO | Today: risk mitigation occurrences, todos; **no cross-governance action entity** | P/N | Monthly | ≥ 85% (proposal) | Control owners | Action list | H (or M if the todo/mitigation model is reused) |
| B7 | Governance turnaround | Median days ARB `created_at` → `decided_at`; ADR draft → signed; card approval steps submitted → acted | Efficiency of governance | EA, DTGM | `arb_reviews`, ADR events, `approval_steps` (`acted_at`) | A (ARB, ADR); P (no explicit request timestamp distinct from creation) | Monthly | ≤ 10 working days (proposal) | EA Governance Office | Slowest cases | L |
| B8 | Governance → project success | On-track rate of reviewed initiatives vs non-reviewed | Evidence that governance helps | CEO, EA | B1 linkage × A3 | P (correlation only; **not causal**) | Semi-annual | Reviewed ≥ non-reviewed + 10 pts (proposal) | Chief Architect | Cohort comparison | M |
| B9 | Stuck approvals | Approvals pending > 30 days | Bottleneck signal | EA | `/reports/admin-dashboard` approval pipeline | A | Weekly | 0 (proposal) | EA office | Pipeline | L |

## C. Enterprise architecture business impact

| ID | KPI | Definition and formula | Rationale | Audience | Sources / APIs | Avail. | Freq. | Proposed target | Owner | Drill-down | Cx |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C1 | Duplicate applications eliminated | Applications with an `eliminate` / `migrate` decision that **reached ARCHIVED or lifecycle `endOfLife`** in period | Rationalization delivered, not just decided | CEO, CFO, EA | `assessment_decisions` + `cards.status` / lifecycle + `successor_id` | P (decision and retirement both exist, but **no link "retired because of decision X" and no retirement date field** beyond lifecycle and archive) | Quarterly | Per the rationalization plan | App portfolio owner | Decision → app → successor | M |
| C2 | Duplicate candidates | Open TurboLens duplicate clusters | Opportunity pipeline | EA | `turbolens_duplicate_clusters` | A | Quarterly | Trend down | EA | Cluster | L |
| C3 | Technology debt index | Weighted share of IT assets past vendor EOL, past lifecycle EOL, technically unsuitable (`technicalSuitability ∈ {unreasonable, inappropriate}`) or in exception | No uniform debt score exists; this is a composite proxy | CEO, CTO | `/reports/eol`, `card_flags.has_eol_coverage`, Application attributes, exceptions | P (components exist; **weighting and baseline not agreed**) | Quarterly | −15% per year (proposal) | CTO / Tech architecture | Debt items by domain | M |
| C4 | Capability improvement | Target capabilities whose `maturity` rose vs baseline ÷ target capabilities | Business capability uplift | CEO, VP | `BusinessCapability.maturity`, `strategicImportance`, `relInitiativeToBC` (56 rows) | P (**no history of maturity value**; events can reconstruct it) | Semi-annual | Defined by capability owners | Capability owners | Heatmap (`/reports/capability-heatmap`) | M |
| C5 | Modernization progress | Applications with a `migrate` / `invest` decision whose modernization initiative is completed ÷ such applications | Modernization delivered | CTO, EA | `assessment_decisions.initiative_id`, `progress`, initiative status | A/P (`progress` field exists) | Quarterly | Per plan | App portfolio owner | Decision → initiative | L |
| C6 | Architecture reuse | Shared-service applications reused by ≥ 2 organisations ÷ shared-service applications | Reuse avoids duplicate build | EA, CFO | `Application.sharedService`, `relOrgToApp` (40 rows) | A | Semi-annual | Trend up | EA | App → consuming orgs | L |
| C7 | Integration standardization | Interfaces via the government service bus (`viaGsb = true`) ÷ interfaces | Integration improvement | CTO, EA | `Interface.viaGsb`, `/reports/integration-status`, `/reports/interoperability` | A | Quarterly | ≥ 80% (proposal) | Integration architecture | Point-to-point list | L |
| C8 | Target architecture realization | Target-state cards (`architecture_state = target`) realised (became `current`) ÷ target-state cards planned for the period | Progress to the target architecture | CEO, EA | `cards.architecture_state`, `change_type`, `successor_id`, `/reports/gap-analysis`, NORA plateaus | P (**no realisation date**; history via events) | Quarterly | Per plateau plan | Enterprise architect | Gap analysis by plateau | M |
| C9 | Risks mitigated | Risks moved to mitigated or closed in period; residual vs initial level reduction | Risk impact of EA | CEO, CRO | `risks` (initial vs residual), status history in events | A | Quarterly | Trend | CRO | Risk register | L |

## D. Financial benefits and ROI

**Financial status taxonomy (mandatory on every money figure)** [Recommendation]: `forecast` (planned, unapproved) → `estimated` (business-case estimate) → `validated` (Finance-approved method and baseline) → `realised` (Finance-confirmed actual, in an accounting period). Only `realised` may be summed into "savings achieved". Totals of different statuses are **never** added together.

| ID | KPI | Definition and formula | Rationale | Audience | Sources / APIs | Avail. | Freq. | Proposed target | Owner | Drill-down | Cx |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D1 | Realised cost savings | Σ benefit amounts with status `realised` in the fiscal year | The CFO's first question | CEO, CFO | **Benefit ledger (new)** | N | Quarterly | Per approved benefit plan | CFO business partner | Benefit → decision → evidence | H |
| D2 | Validated cost avoidance | Σ `validated` avoidance with counterfactual and decision evidence | Avoided investment | CEO, CFO | Benefit ledger (new) + ADR / ARB link | N | Quarterly | — | CFO / Investment committee | Avoidance case | H |
| D3 | Planned / forecast benefits | Σ `planned_savings` de-duplicated per application (latest decision) + forecast benefits on the ledger | Pipeline visibility | CEO, CFO | `assessment_decisions.planned_savings`, `rationalization_assessments.target_savings` | A (planned savings); N (ledger) | Quarterly | — | App portfolio owner | Decision list | L |
| D4 | Opex run-rate reduction | Δ annual run cost (Σ `costTotalAnnual` + infra `operatingCost`) of live assets, current FY vs baseline FY, using `is_live_in_fiscal_year` | Recurring cost trend | CFO | Cost fields + `services/lifecycle.py` + **baseline snapshot** | P (run-rate computable now; **baseline history absent**) | Annual / quarterly | −5% per year (proposal) | Finance + owners | Cost treemap (`/reports/cost-treemap`) | M |
| D5 | Application consolidation savings (realised) | Σ `costTotalAnnual` of applications retired via an `eliminate` / `migrate` decision, as `realised` once Finance confirms | Rationalization payback | CFO | C1 + cost fields + ledger | P/N | Annual | — | App portfolio owner + Finance | Retired apps | M/H |
| D6 | Transformation and EA investment | Σ PPM actuals for transformation initiatives in the current FY; EA-office cost when tagged | Denominator for ROI | CFO | `ppm_cost_lines` (fiscal-year bound), tag or subtype for "transformation" and "EA" | P (needs tagging rule) | Quarterly | Within budget ±5% (proposal) | PMO + Finance | Initiative cost | M |
| D7 | Budget execution | FY actual ÷ FY budget (fiscal-year bound) | Spend control | CFO, CEO | `ppm_budget_lines.fiscal_year`, `ppm_cost_lines.date` | A (after the period fix) | Monthly | 90-105% of phased plan (proposal) | PMO | Initiative | L |
| D8 | EA-attributable ROI | (Σ realised benefits × agreed attribution share − EA cost) ÷ EA cost | Board-level justification | CEO, CFO | D1 + D6 + **attribution policy** | N | Annual | Ratified by CFO | CFO + Chief Architect | Benefit attribution table | H |
| D9 | Benefit realisation rate | Realised ÷ validated forecast, per benefit and period | Accountability for promised value | CEO, CFO | Benefit ledger | N | Quarterly | ≥ 80% (proposal) | Benefits Realisation Office | Benefit | H |
| D10 | Investment alignment | % of FY transformation spend on initiatives linked to a strategic objective | Strategic investment optimization | CEO, CFO | `relInitiativeToObjective` (25 rows), D6 | A/P | Quarterly | ≥ 90% (proposal) | Portfolio management | Unaligned spend | L |

**Double-counting rules** [Recommendation]

1. One application's saving is counted once, from its latest TIME decision, never per assessment.
2. A saving booked as `realised` is removed from `forecast` totals.
3. Avoidance and savings are reported separately and never summed.
4. Benefits shared by several initiatives are allocated by an explicit percentage that totals 100%.
5. Infrastructure costs inherited through relations are counted on the asset, not again on the application.

## E. Executive decision intelligence

| ID | KPI / list | Definition | Rationale | Audience | Sources / APIs | Avail. | Freq. | Proposed threshold | Owner | Drill-down | Cx |
|---|---|---|---|---|---|---|---|---|---|---|---|
| E1 | Strategic risks requiring escalation | Open risks with residual level `critical`, or `high` and overdue, linked to a strategic objective or critical capability | Only what needs the CEO | CEO | `risks`, `risk_cards`, `relObjectiveToBC`, `strategicImportance` | A/P (**no escalation flag or committee routing**) | Weekly | Every critical risk listed (proposal) | CRO | Risk detail | M |
| E2 | Decisions pending | ADRs in `in_review` / awaiting signature; ARB reviews `scheduled` or `deferred`; exceptions `requested`; with age | Decision backlog | CEO, EA | `architecture_decisions`, `arb_reviews`, `tech_standard_exceptions` | A | Weekly | None older than 30 days (proposal) | EA Governance Office | Decision record | L |
| E3 | Investment decisions pending | Initiatives of subtype `idea` / `program` awaiting approval, with `businessValue` and budget | Investment queue | CEO, CFO | Initiative cards (`initiativeStatus`, `businessValue`, `costBudget`), ADM gate approvals (`adm_phases.approved_at`) | P (**no explicit investment-gate status**) | Monthly | — | Investment committee | Initiative | M |
| E4 | Roadmap dependencies at risk | Initiatives on track whose predecessor (`relInitiativeSuccessor`, `ppm_dependencies`) is off track or late | Hidden delivery risk | CEO, DTGM | `ppm_dependencies`, `relInitiativeSuccessor`, status reports | A/P | Monthly | — | PMO | Dependency chain | M |
| E5 | Governance bottlenecks | Approvals pending > 30 days; ARB items deferred twice or more; exceptions expiring in 30 days | Throughput | EA | `approval_steps`, `arb_reviews`, exceptions | A | Weekly | 0 (proposal) | EA office | Case list | L |
| E6 | Cross-department issues | Initiatives or decisions linked to ≥ 2 organisations with an open risk or deferred decision | Needs CEO arbitration | CEO | `relOrgToInitiative`, risks, ARB | P | Monthly | — | DTGM | Case | M |
| E7 | Decisions with measurable consequences | Pending decisions with an attached cost, saving or strategic-objective link, ranked by value | Prioritise the CEO's attention | CEO | E2 + D3 + objective links | P | Weekly | Top 5 shown (proposal) | EA Governance Office | Decision record | M |

## F. Where KPI definitions, targets and actuals should live [Recommendation]

Use the existing **`KPI` card type**. It already models `unit`, `baselineValue`, `baselineDate`, `targetValue`, `targetValueDate`, `currentValue`, `direction`, `measurementFrequency`, `indicatorLevel`, `calculationFormula`, `dataSource` and `lastMeasuredDate`, and it relates to Objective (`relObjectiveToKPI`), Initiative (`relInitiativeToKPI`), GovService and BusinessProcess (`relKPIToGovService`, `relKPIToBusinessProcess`) and OrganizationalUnit (`relKPIToOrgUnit`). The only missing piece is a **time series of measured values** (see DATA_AND_FUNCTIONAL_GAP_ANALYSIS.md §3). It also inherits stakeholders (owner), comments, history, approval and permissions for free. Creating a parallel "executive KPI" table would duplicate it.
