# Data integrity and reporting

Source inspection shows real integrity controls: PostgreSQL FKs, enum-like application validators, financial-benefit CHECK constraints and unique link keys (`models/benefit.py:130–175`), card reference uniqueness and a partial unique KPI metric index (`models/card.py:48,115–130`). Relation endpoints validate references/types/cardinality (`api/v1/relations.py:542–549,595–640`). Application checks are not automatically database race protection; concurrency behavior was not tested.

`database.py:23–25` supplies a request session; handlers own commits. Governance transition helpers add history to the same session without committing (`services/governance_transitions.py:117–155`), allowing state/history rollback together. Migration preview/apply and workspace diff/applier sources exist, but transaction rollback, duplicate replay and interrupted-import behavior are **NOT VERIFIED** with PostgreSQL. No actual database constraints were introspected on an installed instance.

## Reporting controls inspected

* `api/v1/executive_dashboard.py:55–124`: permission and card visibility applied before aggregation; costs are not loaded without `costs.view`; fiscal year derived from configured start month.
* `services/executive_dashboard.py` and `tests/services/test_executive_dashboard_kpis.py:39–217`: missing/stale reports do not become healthy, coverage is separate, budget currency/period named, conflicting savings excluded, agreeing application estimates deduplicated. Pure checks passed except FR-07.
* `api/v1/executive_overview.py:1–20,88–127`: distinguishes dated historical/period figures from today's pipeline; restricted record details need their module permission. Historical unavailability is not zero.
* `services/executive/benefits.py:92–185,227–274`: planned/validated versus reported/confirmed amounts, separate currencies, cash versus avoidance, fiscal-year actuals and assessed versus KPI-verified outcomes. This is good source design; the corresponding full database behavior was not executed.
* `services/executive/kpis.py:192–209,247–309`: independently verified implementation, review coverage and risk-state semantics are explicit. Governance history begins when recorded; older history is not reconstructed from arbitrary updated timestamps.

**Do not infer that all dashboards show only approved cards.** Base portfolio loaders summarize visible operational inventory; approval and verification are separate dimensions. The EA owner must accept the population of each published indicator. An accessible draft is not authoritative evidence merely because it appears in a count. Live expected-versus-actual reconciliation remains part of FR-09.

## FR-04 — Approved NORA deliverables can change without renewed approval

**Category:** governance/data integrity. **Severity:** P2. **Confidence:** Confirmed statically; runtime reproduction NOT VERIFIED.

**Sources:** `backend/app/api/v1/nora_program.py:565–606`, especially `:580–597`.

**Evidence/path:** update requires `nora.manage`. Approval permission is checked only when a supplied status becomes approved from a different status. An already-approved deliverable can receive changed evidence/title/description/owner while omitting status (or retaining approved); `approved_by` and `approved_at` remain and progress still counts it approved (`:151–181`). Expected: approved evidence represents the content actually reviewed, or a new review is needed after substantive edits. Actual: approval metadata survives changed evidence.

**Impact/scope:** misleading NORA completion/approval evidence. Pilot can use tracker provisionally with manual review; formal completion reporting affected before wider rollout.

**Minimum correction:** invalidate approval on substantive change or make approved content immutable pending reopen; compare reviewed fields and preserve audit history. Until then use approved exported evidence/manual signoff and do not claim live tracker approval enforces review of current contents.

**Validation:** approve a deliverable as reviewer, change its evidence as manager, and assert reset/re-review or edit refusal. Also ensure a genuine no-op does not unnecessarily invalidate approval.

## FR-05 — Workspace export/import loses successor links and card approval steps

**Category:** transfer fidelity/data recovery. **Severity:** P2 with a database-backup workaround. **Confidence:** Confirmed static omission; round-trip reproduction NOT VERIFIED.

**Sources:** `backend/app/models/card.py:78–80`; `models/approval_step.py:33–50`; `services/workspace_io/exporter.py:116–138,184–194`; `workspace_io/applier.py:1101,1212–1217`; entire declarative registry `workspace_io/sections.py` (notably other histories at `:445–478`).

**Evidence/path:** bespoke CARD_COLUMNS includes architecture_state/change_type/approval_status but no card successor reference. Applier has no successor restoration path. Registry imports governance transition history but contains no ApprovalStep entity section. The only successor_id in workspace section declarations belongs to rationalization AssessmentDecisions, not Card. Expected for full workspace clone: target/current replacement link and ordered card approval evidence survive with remapped card/user FKs. Actual: these two data classes are not serialized, while an approval_status may still transfer.

**Impact/scope:** broken gap/replacement traceability and unresumable/unsubstantiated card review after transfer. Does not prove pg_dump loses them. Pilot safe if database backups are the recovery mechanism and workspace transfer is excluded for official migration.

**Minimum correction:** add remappable successor references to bespoke card transfer and dependency-ordered approval-step serialization (including card/user remaps); preserve active review semantics. Add a two-instance round-trip and repeat-import no-op test. Do not export raw instance-local card/user UUIDs as the fix.

**Validation:** transfer a current/target pair plus a partially approved chain and verify successor identity, actor/submitter remapping, next approver, final approved history and idempotent import. Separately prove database restore includes these rows.

Executed read-only descriptor introspection confirmed `successor_id in CARD_COLUMNS: False`, `ApprovalStep exported: False`, `GovernanceTransitions exported: True`. This verifies registry omissions without opening a database; a real round-trip remains NOT VERIFIED.

## FR-06 — Plateau views project current records; they do not reconstruct history

**Category:** time-based reporting semantics. **Severity:** P2. **Confidence:** Confirmed implementation limitation; user interpretation Unverified.

**Sources:** `backend/app/services/nora_landscape.py:44–64,190–220`.

**Evidence/path:** phase_as_of classifies current lifecycle dates at a chosen date; plateau query loads currently non-archived cards and today's architecture_state. It does not select versions or membership effective on that past date. Expected if used as historical baseline: past membership/state should be stable and evidence-based. Actual: edits/additions/archives today change the same past-date output. Future lifecycle projection is a legitimate supported use.

**Impact/scope:** using this as official historical evidence would be misleading. No blocker for a pilot using named planned lifecycle plateaus.

**Minimum correction:** explicitly label lifecycle projection/current repository, retain approved baseline exports for history. Add historical persistence only if a real operational requirement demands it; do not block the pilot on a snapshot engine.

**Validation:** record a plateau result, change current state/add/archive a card, request the same date and document expected projection semantics. Never call it a preserved historical baseline without additional evidence.

Remaining unverified areas: concurrent duplicate creation, bulk savepoint/error semantics, mixed-currency budgets outside the inspected benefits path, leap/fiscal-year boundaries beyond unit cases, deleted linked record effects, real migration datasets, audit retention/legal holds and historical reproducibility. These require focused tests with known disposable data, not speculative findings or a repeated full suite.
