# Data and functional gap analysis

The whole application was surveyed (59 API modules, 90+ models, the live metamodel with the NORA profile applied). Counts are from the demo database on 2026-10-22. [Confirmed] unless marked otherwise.

## 1. Existing capabilities that support an executive dashboard

| Domain | What exists | Code | Demo data | Executive use |
|---|---|---|---|---|
| Strategy | Vision, Mission, Pillar, Objective (`progress`, `objectiveType`, `targetDate`, `kpi` text, `nationalAlignment`); strategy cascade and map reports | `seed.py`, `/reports/strategy-cascade`, `/reports/strategy-map` | 9 objectives; 0 pillar links | A1, D10 |
| KPIs | **`KPI` card type** with baseline, target, current, direction, frequency, formula and dates; relations to Objective, Initiative, GovService, BusinessProcess, OrgUnit, Project | NORA profile metamodel | **0 KPI cards** | Home for every executive KPI definition and target |
| Services | **`GovService`** (`serviceStatus`, `automationLevel`, `serviceType`, `serviceFee`); relations to process, application, capability, journey, persona, org | metamodel, `/reports/service-traceability` | **0 services** | A5 |
| Processes | BusinessProcess (`automationLevel`, `maturity`, `durationDays`, `riskLevel`); BPMN flows with versioned approval; process assessments (efficiency, effectiveness, compliance, automation scores) | `bpm*.py`, `process_assessments` | 43 processes, 1 published flow | A6, A7, A9 |
| Maturity | Maturity dimensions, dated assessments with `level` and `target_level`, overall score, evidence, approval; live indicators | `maturity.py`, `/maturity/overview` | **0 assessments** | A4 |
| Capabilities | BusinessCapability (`maturity`, `strategicImportance`, `isCoreCapability`); heatmap; initiative → capability (56) and objective → capability (69) links | `/reports/capability-heatmap` | 90 capabilities | C4 |
| Portfolio | Application (`timeModel`, suitability, criticality, `costTotalAnnual`, `costCapex`, `sharedService`, `automationLevel`); lifecycle; successor; EOL links | `/reports/app-portfolio`, `/reports/eol` | 58 applications | C1, C3, C6 |
| Rationalization | TIME assessments with per-app decision, successor, initiative, `annual_cost`, `planned_savings`, `progress` | `rationalization.py` | 1 assessment, 13 decisions | C1, C5, D3, D5 |
| Target state | `cards.architecture_state` / `change_type` / `successor_id`; gap analysis; NORA plateaus and segments; scenarios with diff and merge | `/reports/gap-analysis`, `nora_landscape.py`, `scenarios.py` | 2 scenarios | C8 |
| Delivery | Initiative (`initiativeStatus`, `businessValue`, `costBudget`/`costActual`, dates, sponsor); PPM status reports, WBS, tasks, budgets (by fiscal year), costs, risks, dependencies; Gantt | `ppm*.py` | 20 initiatives, 15 reports | A3, D6, D7, E4 |
| Roadmaps | Saved roadmaps with milestones (`target_date`, `initiative_id`) | `roadmaps.py` | 2 roadmaps, **0 milestones** | A2 |
| Governance | ARB reviews (`status`, `subject_card_id`, `decided_at`); ADRs (committee, meeting date, signatories, revisions, linked cards); ADM workspaces and phase gates with approvals; card approval steps; tech standards, compliance scan, exceptions with expiry; principles; EA requirements; NORA program deliverables (stage gates) | `arb.py`, `adr.py`, `adm.py`, `tech_standards.py`, `nora_program.py` | 6 ARB, 7 ADR, 3 exceptions, 54 deliverables, 0 ADM, 0 approval steps | B1-B9, E2, E5 |
| Risk and compliance | EA risk register (initial and residual matrix, owner, target date, acceptance), recurring mitigation tasks with audit, compliance findings → risk promotion | `risks.py`, `risk_mitigation_tasks.py`, TurboLens compliance | 10 risks | C9, E1 |
| Improvement | Improvement opportunities (`status` proposed → approved → inTransition → realized; linked initiative, journey, cards); realized-per-quarter widget | `improvement_opportunities.py` | **0 opportunities** | Bridge between governance and benefits (see EA_GOVERNANCE_AND_ROI_MODEL.md) |
| Cost and finance | Cost fields on applications and infrastructure; fiscal-year-bound cost reports (`is_live_in_fiscal_year`); currency setting | `lifecycle.py`, `fiscal_year.py`, `/reports/cost*` | yes | D4, D6, D7 |
| History | Event log with whole old/new `attributes` and `lifecycle` per change; mutation batches; daily `kpi_snapshots` (4 metrics); security audit log | `events`, `kpi_snapshot_service.py` | 52 events, 1 snapshot | Reconstruct trends; audit |
| Duplicates and AI | TurboLens duplicate clusters, modernization assessments, vendor analysis | `turbolens.py` | — | C2 |

## 2. Reusable data relationships [Confirmed]

| Chain | Relations | Rows in demo |
|---|---|---|
| Strategy → delivery | Pillar → Objective (`relNora2PillarObjective`, `relObjectiveToPillar`), Initiative → Objective (`relInitiativeToObjective`) | 0 / 25 |
| Strategy → capability | Objective → BusinessCapability (`relObjectiveToBC`) | 69 |
| Delivery → capability / app | Initiative → BC (`relInitiativeToBC`), Initiative → Application (`relInitiativeToApp`) | 56 / 41 |
| KPI measurement | Objective → KPI, Initiative → KPI, KPI → GovService / BusinessProcess / OrgUnit, Project → KPI | 0 (relations defined, unused) |
| Service delivery | GovService → BusinessProcess / Application / BC / Journey / Persona | 0 |
| Process → strategy | BusinessProcess → Objective, → Initiative | 11 / 11 |
| Ownership | Organization → Objective / Initiative / Application | 10 / 15 / 40 |
| Governance → card | ARB `subject_card_id`; ADR ↔ cards (`architecture_decision_cards`); exception → card and initiative; risk ↔ cards (`risk_cards`) | yes |
| Decision → delivery | `assessment_decisions.initiative_id`, `successor_id`; `improvement_opportunities.initiative_id` | yes |

**Implication.** Most of the traceability an executive dashboard needs is **already modelled**. The gaps are (a) the missing links at the end of the chain (decision → action → outcome → benefit), (b) missing history, and (c) unpopulated data, not missing entities.

## 3. Missing functionality and data

| # | Gap | Evidence | Impact | Recommended remedy | Reuse instead of duplicate |
|---|---|---|---|---|---|
| G1 | **KPI measurement history** | `KPI.currentValue` is one value; events can reconstruct changes but are not a fact table | No trend, no target-vs-actual over time | A `kpi_measurements` table (kpi_card_id, period, value, status, source, entered_by, evidence) | Keep the KPI card as the definition; history only |
| G2 | **Benefit ledger** | No entity holds a benefit amount with status, period, approver or evidence | No realised or validated savings, ROI or realisation rate | A `benefits` table linked to the existing decision, initiative or opportunity (see EA_GOVERNANCE_AND_ROI_MODEL.md) | Link to ADR, rationalization decision, improvement opportunity and initiative; do not create a new "project" |
| G3 | **Decision → implementation action** | ADR and ARB end at signed or approved; no action, owner, due date or closure | B5, B6 cannot be computed | Reuse **todos** (`todos` already has card link, assignee, due date, done, `is_system`) or the **risk mitigation task** pattern, linked to the ADR or ARB | Do not build a new tasking system |
| G4 | **Milestone achievement** | `roadmap_milestones` has `target_date` only | A2 impossible | Add `achieved_at` and `status`, or derive from the linked initiative / WBS milestone (`ppm_wbs.is_milestone`, `completion`) | Prefer deriving from PPM WBS milestones |
| G5 | **Funding / design gate timestamps** | No initiative gate dates | B2 unmeasurable | Use ADM phase approvals (`adm_phases.approved_at`) as gates; add an investment-gate status on Initiative if ADM is not used | Reuse ADM |
| G6 | **Realisation timestamps** | `improvement_opportunities` uses `updated_at` as the realised date (`improvement_opportunities.py:149-194`, documented in code); target-state cards have no realised date | Any later edit moves the date | Add `realized_at`; record a state-change event | — |
| G7 | **Baselines** | No financial or operational baseline snapshot | D4, A7, C3, C4 deltas impossible | Fiscal-year baseline snapshot of run-rate and key classifications; extend `kpi_snapshots` or use G1 | Extend the existing snapshot loop |
| G8 | **Financial status and attribution** | Money fields are bare numbers | Cannot separate forecast from realised | Status taxonomy on G2 entries; attribution share | — |
| G9 | **"In-scope" rules** | No definition of which initiatives require EA review | B1 denominator undefined | An admin setting (e.g. budget ≥ X, or subtype ∈ {program, project}) | Settings, not code |
| G10 | **Escalation routing** | Risks have no escalation flag or committee | E1 relies on a level heuristic | Add `escalated_to` / `escalation_status` to risks, or use a tag group "Escalation" | Prefer a **tag group** (no schema change) |
| G11 | **Data population** | 0 GovService, 0 KPI, 0 maturity assessments, 0 milestones, 0 opportunities in demo | Framework sections would show "Not available" | Data stewardship plan; surveys (existing module) to collect values | Reuse surveys |
| G12 | **Single source of truth** | Initiative health and cost have two sources each (EXISTING_DASHBOARD_ASSESSMENT.md §6.3) | Contradicting numbers | Rule: PPM is the source when the module is on; card attribute otherwise | — |
| G13 | **Read-scope coverage in fork modules** | `nora_program.py`, `rationalization.py`, `arb.py`, `tech_standards.py`, `maturity.py`, `improvement_opportunities.py`, `adm.py`, `roadmaps.py` query `Card` without referencing `CardReadScope` (only `adr.py` does) | Reusing their aggregates on an executive view could leak hidden-type cards or counts | Apply `CardReadScope` before reuse; the guard test `tests/services/test_card_read_scope_guard.py` matches `select(Card` and would be expected to flag these (not run, per the assessment restrictions) | — |

## 4. Required data model extensions (minimum set) [Recommendation]

Listed in order of executive value. Each was checked for overlap with existing entities.

1. `kpi_measurements` (G1): history for the existing KPI card.
2. `benefits` (G2, G8): amount, currency, type (saving / avoidance / revenue / non-financial), status (forecast / estimated / validated / realised), fiscal period, owner, approver, approved_at, evidence (document link), attribution %, plus links to one of {ADR, rationalization decision, improvement opportunity, initiative} and affected cards.
3. Decision actions (G3): **no new table**. Use `todos` with a link to an ADR or ARB review, or extend the mitigation-task pattern.
4. `realized_at` on improvement opportunities; `achieved_at` / `status` on roadmap milestones (G4, G6).
5. Fiscal-year baseline snapshots (G7): extend the `kpi_snapshots` capture loop with configurable metric keys.

Every one of these is a schema change (Alembic migration) and a workspace-transfer change (CLAUDE.md checklist). **None is made in this phase.**

## 5. Integration opportunities [Assumption: availability depends on the organisation]

| Source | Purpose | Existing hook |
|---|---|---|
| ERP / Finance (budget, actuals, cost centres) | Validated and realised benefits; EA programme cost | PPM cost lines can be loaded; the extension SDK data bridge (`ctx.data`) supports connectors |
| ServiceNow CMDB | Asset inventory, incidents (operational KPIs) | Existing ServiceNow integration (`servicenow.py`) |
| Service channels / CX platform | Satisfaction, transaction volumes, digital uptake | None; an extension connector would write to `kpi_measurements` |
| Project portfolio tool | Status and milestones | PPM import; extension bridge |
| National reporting portals (NORA, NEA) | Alignment evidence | `nea_evidence.py` evidence packs |
