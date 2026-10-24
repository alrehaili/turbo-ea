# Security remediation plan (mandatory, Phase 1)

**Status (2026-10-24): SEC-1, SEC-2 and SEC-3 implemented, plus the Phase 1 security preparation (§9) and the final integration (§10) — PENDING VERIFICATION.** The targeted security tests pass locally; the full backend suite has not been run (stopped at the owner's request to save time and usage) and nothing has run in CI. Uncommitted. The implementation record, with per-finding evidence and residual risks, is in §8. §1-§7 are the original plan, kept unchanged for traceability.

- This is the **Security Remediation Track (SEC)**. It is **separate from the Executive Dashboard feature phases** (decision of 2026-10-22) and protects existing pages whether or not the dashboard proceeds.
- It **must pass CI before** any affected API feeds executive reporting (SR-08, confirmed decision C-05).
- Governing decisions **D-01** (hidden / unauthorized exclusion) and **D-30** (governance-record disclosure) are **approved** (`DECISION_LOG.md` §2).
- Stages: **SEC-1** regression suite (§6) → **SEC-2** name / id and money leaks → **SEC-3** governance records, aggregates, hidden types (`PHASED_DELIVERY_PLAN.md`).

**Rules being enforced** (CLAUDE.md, "A card read has one scope"): a card the caller may not read does not exist for them. That means no row, relation, graph node, count, name or id. Every card-returning or card-naming endpoint applies `CardReadScope` (`backend/app/services/card_read_scope.py`); a single hidden card returns 404; money requires `costs.view`.

## 1. Findings

All findings were verified by static inspection on 2026-10-22. No tests were run (planning restriction).

| ID | Endpoint(s) | File : line | What leaks to a restricted reader | Severity |
|---|---|---|---|---|
| S-01 | `GET /roadmaps/data`, `GET /roadmaps/{id}/data` | `api/v1/roadmaps.py:98-114` (`_compute_timeline`: `select(Card).where(Card.type == card_type, …)`, no scope) | **Names, lifecycle and grouping of cards of types the reader cannot see** | High |
| S-02 | `GET /reports/impact` (`change_impact`) | `api/v1/reports.py:~2476` → `services/impact_service.py` (2 card queries, no scope parameter) | Names and relations of hidden cards in the impact graph | High |
| S-03 | `GET /arb`, `GET /arb/{id}` | `api/v1/arb.py:64-70` (`_card_brief` → `select(Card.id, Card.name, Card.type)`) | Subject card name, type and id of a hidden card | High |
| S-04 | `GET /tech-standards/exceptions`, `GET /tech-standards`, `GET /tech-standards/{id}` | `api/v1/tech_standards.py:133-139` (`_card_brief_map`) | Names of hidden cards under exceptions and standards | High |
| S-05 | `GET /tech-standards/compliance-scan` | `services/tech_standards_scan.py` (1 card query, no scope) | Hidden cards listed as compliant or non-compliant | High |
| S-06 | `GET /rationalization/assessments/{id}`, `GET /rationalization/cards/{card_id}/decisions` | `api/v1/rationalization.py:108-114` (`_card_brief_map`), `:336` (`select(Card)`, no readable check) | Hidden application names in decisions; a hidden card's decisions by id | High |
| S-07 | `GET /rationalization/assessments`, `…/{id}` | `api/v1/rationalization.py:84, 99` | `target_savings`, `annual_cost`, `planned_savings` returned **without `costs.view`** | High (financial) |
| S-08 | `GET /reports/ppm/dashboard` | `api/v1/ppm_reports.py:37-49` → `ppm_portfolio_service.build_dashboard` | `total_budget`, `total_actual` **without `costs.view`** | High (financial) |
| S-09 | `GET /improvement-opportunities` | `api/v1/improvement_opportunities.py:81-86` (`_card_briefs`) | Names of hidden linked cards | High |
| S-10 | `GET /nora-program/dashboard` | `api/v1/nora_program.py:184+` (`select(Card.approval_status…)` :214, `architecture_state` :238, Pillar / Objective ids :385-394) | **Counts** including hidden cards (approvals, gaps, landscape, strategy) | Medium (aggregate disclosure) |
| S-11 | `GET /maturity/indicators`, `POST /maturity/assessments/{id}/refresh-suggestions` | `services/maturity_indicators.py` (2 card queries, no scope) | Landscape counts including hidden types | Medium |
| S-12 | `GET /improvement-opportunities/realized-value` | `api/v1/improvement_opportunities.py:149-194` | Counts of opportunities about hidden cards | Low-medium |
| S-13 | `GET /adm/workspaces/*` (artefacts `kind=card`, `initiative_id`) | `api/v1/adm.py:165-210, 272-284` | **Ids** of hidden cards (artefact `ref_id`, `initiative_id`) | Medium |
| S-14 | `POST /improvement-opportunities/ai-suggest` | `services/nora_authoring.py` (6 card queries, no scope) | Hidden cards sent to the LLM and reflected in suggestions | Medium |
| S-15 | `GET /reports/dashboard`, `/reports/executive` | `reports.py:128`, `executive_dashboard.py` | Hidden **card types** counted (CR-06); not a read-scope breach but an inconsistent disclosure of hidden-type volume | Low |
| S-16 | Sentinel sweep coverage | `tests/api/test_read_scope_sentinel_sweep.py` | The fixture seeds ADR and risk links to the sentinel only; ARB, exceptions, rationalization, opportunities, ADM, milestones are **never seeded**, so the sweep cannot detect S-03..S-13 | Test gap |
| S-17 | Read-scope guard | `tests/services/test_card_read_scope_guard.py` (matches `select(Card`) | `nora_program`, `rationalization`, `arb`, `tech_standards`, `adm`, `roadmaps` contain `select(Card…` without scope markers; the guard **would be expected to fail** on them (not run). CI status for the fork must be confirmed. | Test gap |

**Added during the decision review (2026-10-22, static inspection):**

| ID | Endpoint(s) | File : line | What leaks to a restricted reader | Severity |
|---|---|---|---|---|
| S-18 | `GET /reports/strategy-map` | `api/v1/reports.py:2481-2492` → `services/strategy_map_service.py:151-207` (no scope references) | Card names in the strategy map, **and `total_budget` / `total_actual` without `costs.view`** | High (+ financial) |
| S-19 | `GET /reports/freshness`, `/reports/resilience`, `/reports/data-flow`, `/reports/integration-status` | `api/v1/reports.py:2504, 2516, 2527, 2537` → `freshness_service`, `resilience_service`, `data_flow_service`, `integration_status_service` (0 scope references each) | Names, relations and status of hidden cards | High |

The read-scope guard checks markers **per module**, so these per-endpoint gaps inside `reports.py` (which references the scope elsewhere) are invisible to it. Only the sentinel sweep with suitable fixtures catches them (WI-12).

Only `api/v1/adr.py` among the fork governance modules already applies the scope. It is the **reference pattern**: `_adr_to_dict(…, read_scope)` drops hidden linked cards; writes keep hidden links (`hidden_card_ids`, `keep_hidden`).

## 2. Remediation principles

1. **Governance records (D-30, approved).** "Use linked-card redaction where the independently accessible record remains meaningful and safe; omit records where redaction cannot prevent disclosure. Preserve hidden links and underlying records." Applied per record type below. The classification is the technical application of the approved rule and is reviewed in the SEC-3 PR.

   | Record | Card linkage | Meaningful and safe after redaction? | Treatment |
   |---|---|---|---|
   | ADR (`architecture_decision_cards`) | Many cards; a standalone decision; free text out of scope per CLAUDE.md | Yes | **Redact** hidden links: name **and** id (existing `adr.py` pattern) |
   | Improvement opportunity (`improvement_opportunity_cards`) | Many cards; the record describes an improvement | Yes | **Redact** hidden links |
   | Tech standard (related cards) | Many cards; the standard stands alone | Yes | **Redact** hidden cards |
   | Roadmap milestone (`initiative_id`) | One initiative, but label and date describe the milestone | Yes | **Redact** the initiative link |
   | ADM workspace (`initiative_id`) | One initiative; the workspace is a programme container | Yes | **Redact** the initiative link |
   | Standard exception with a readable card but a hidden `initiative_id` | Secondary link only | Yes | **Redact** the initiative link |
   | ADM artefact of kind `card` (`ref_id`) | The artefact *is* the card reference | No | **Omit** the artefact row (the phase remains) |
   | ARB review (`subject_card_id`) | The subject is the record's identity; title, summary and decision notes typically name it | No | **Omit**: absent from lists, **404** on detail, excluded from counts |
   | Standard exception (`card_id`) | The exception exists for that card; the justification names it | No | **Omit**, as above |
   | Rationalization decision row (`card_id`) | The row is one application's decision | No | **Omit** the row; the assessment remains, and its counts and money totals are computed over readable rows only |
   | Risk ↔ cards (`risk_cards`) | Already scoped through `load_filtered_risks` | — | Unchanged; verified by the sweep |

   **Preservation**: write paths that replace a link set keep the links the caller never saw (`hidden_card_ids` / keep-hidden, as in `adr.py:407-418`); no record or link is deleted; omitted records remain fully visible to readers who may see the subject card.
2. **Multi-card records** follow the redaction rows above. Redaction removes both the name and the id of each hidden card.
3. **Aggregates** count only readable cards (`read_scope.where(Card, mode="module")`) and exclude hidden types (`visible_types_clause`) (D-01, approved).
4. **Money** requires `costs.view`: fields are omitted (not zeroed) and responses carry `"costs_restricted": true`.
5. **AI paths** refuse restricted readers (mirror TurboLens `_require_whole_landscape`) or pass only scoped data.
6. Services that serve user reads take a `read_scope` parameter (the guard's second test, `test_read_serving_services_take_a_scope`).

## 3. Work items

| WI | Fixes | Change | Tests (added in CI per project rules) |
|---|---|---|---|
| WI-1 | S-01 | `_compute_timeline(db, …, read_scope)` applies `where(Card, mode="module")` to both queries | API: a restricted reader sees no hidden-type rows; admin control sees them |
| WI-2 | S-02 | `gather_impact(db, center, …, read_scope)`: center via `require_card_readable`; traversal filters every hop | API: a hidden neighbour is absent from nodes and edges |
| WI-3 | S-03 | ARB list filters `subject_card_id` to readable (or null); detail 404 when the subject is hidden; `_card_brief` takes the scope | API list / detail 404 |
| WI-4 | S-04, S-05 | `_card_brief_map(db, ids, read_scope)`; exceptions on hidden cards omitted; a hidden `initiative_id` on a readable exception redacted; hidden cards redacted from standards; the compliance scan takes the scope (per §2) | API + service tests |
| WI-5 | S-06, S-07 | Rationalization: decision rows on hidden cards omitted (the assessment remains; totals over readable rows only); `/cards/{id}/decisions` → `require_card_readable`; money fields gated on `costs.view` | API: restricted + no-cost cases |
| WI-6 | S-08 | PPM dashboard omits `total_budget` / `total_actual` without `costs.view` | API |
| WI-7 | S-09, S-12, S-14 | Hidden cards redacted from opportunities (name and id; keep-hidden on write); realized-value counts only opportunities with ≥ 1 readable card or none; ai-suggest refuses restricted readers | API |
| WI-8 | S-10 | NORA dashboard: every card query takes the scope and the visible-type clause; strategy counts scoped | API: counts differ for the restricted reader by exactly the hidden sentinel |
| WI-9 | S-11 | `compute_indicators(db, read_scope)`; landscape-wide suggestions only for unrestricted readers | Service + API |
| WI-10 | S-13 | ADM: artefacts of kind `card` with a hidden `ref_id` omitted (the phase remains); hidden workspace `initiative_id` redacted; writes keep hidden links (per §2) | API |
| WI-11 | S-15 | `visible_types_clause` in `/reports/dashboard` and executive (CR-06) | API parity test across Overview / Executive / Workspace / Admin totals |
| WI-12 | S-16 | Extend the sweep fixture: ARB review on the sentinel, exception on the sentinel, rationalization decision on the sentinel, opportunity linking the sentinel, ADM artefact referencing the sentinel, roadmap over the sentinel's type, benefit and KPI rows | Sweep must stay green; non-vacuity control as admin |
| WI-13 | S-17 | Guard passes with no new allowlist entries (any allowlist entry needs a written reason) | Guard |
| WI-15 | S-18, S-19 | `gather_strategy_map`, `gather_freshness`, `gather_resilience`, `gather_data_flow`, `gather_integration_status` take `read_scope` and filter every card query; strategy-map omits budget / actual without `costs.view`. Must precede reuse of integration-status for IMP-06. | Sweep fixture covers these endpoints over the sentinel; API restricted and no-cost tests |
| WI-14 | Executive | All new executive endpoints: scope, `costs.view`, `benefits.*`, small-group suppression (SR-04), export parity (SR-05) | `tests/api/test_executive_*.py` restricted-reader matrix |

## 4. Aggregate disclosure controls

- **Totals = sum of visible breakdowns**: the total is never computed from a separate, unscoped query.
- **Trends from snapshots** are shown only to unrestricted readers (`reports.py:255` rule).
- **Small-group suppression (SR-04)**: with an org filter and a restricted reader, cells with n < 3 (D-20) return `suppressed`.
- **Drill-down parity**: every drill-down endpoint returns exactly the records counted, under the same scope.
- **Exports** (PPTX / XLSX) are generated from the same scoped payload, recorded via the data-export audit path, and money is omitted without `costs.view`.
- **Monetary aggregates** (D-05, D-24, approved):
  - amounts are summed only within one currency; mixed currencies are shown per currency or as "mixed currencies, not totalled", never converted;
  - planned-savings conflicts are excluded from authoritative totals;
  - money is omitted, never zeroed, without `costs.view`.

## 5. New permission keys (`core/permissions.py`)

`benefits.view`, `benefits.manage`, `benefits.validate`, `benefits.confirm`, `kpis.measure`. The existing `reports.executive_dashboard` is kept (admin-only by default; D-03 decides role grants). Labels go in the registry. If the frontend references them, the parity set in `frontend/src/lib/routePermissions.test.ts` is updated.

## 6. Disclosure regression coverage (SEC-1; SR-09)

The suite is written **before** the fixes, so it fails on the known leaks and passes once they are closed. It runs in CI with the consolidated backend suites (shards + aggregate, diff coverage, mutation gates). Nothing is run during planning.

| Ref | Channel | Test design | Location (proposal) |
|---|---|---|---|
| R1 | **Records and reports (names / ids)** | Extend `tests/api/test_read_scope_sentinel_sweep.py` fixtures with records linking the hidden sentinel card: ARB review (subject), standard exception, rationalization decision, improvement opportunity, ADM artefact (`kind=card`) and workspace initiative, roadmap over the sentinel's type, roadmap milestone initiative, strategy map / freshness / resilience / data-flow / integration-status / impact over the sentinel. The sweep asserts that no GET body contains the sentinel's name or id; non-vacuity control as admin. | sweep fixture |
| R2 | **Counts** | For each aggregate endpoint (`/reports/dashboard`, `/reports/executive`, `/nora-program/dashboard`, `/maturity/indicators`, `/improvement-opportunities/realized-value`, `/reports/bpm/dashboard`, `/reports/ppm/dashboard`, `/reports/strategy-map` summary, `/risks/metrics`), call it as admin and as a restricted reader with one hidden sentinel. Assert **restricted = admin − sentinel contribution**, and that hidden-type cards are excluded for both (D-01). | `tests/api/test_disclosure_counts.py` |
| R3 | **Charts** | Chart payloads (breakdown arrays, series, legends) contain no hidden type key or card name; **total = Σ breakdown** in every payload; the drill-down for a chart segment returns exactly the counted records. | `tests/api/test_disclosure_charts.py` |
| R4 | **Monetary aggregates** | On every money-bearing endpoint (`/reports/cost`, `/reports/cost-treemap`, `/reports/ppm/dashboard`, rationalization, `/reports/strategy-map`, `/reports/executive`): without `costs.view`, money fields are **absent** (not zero); with it, totals exclude hidden cards' amounts; no cross-currency sum (D-05); conflicting planned savings excluded (D-24). | `tests/api/test_disclosure_money.py` |
| R5 | **Governance records (D-30)** | For each row of the §2 table: omitted records are absent from lists and 404 on detail; redacted records lack the hidden name **and** id; a write replacing links keeps the hidden ones; the underlying rows still exist (as admin). | `tests/api/test_disclosure_governance_records.py` |
| R6 | **Exports** | Existing card exports (CSV / JSON / Excel) and future PPTX / XLSX executive exports apply the same scope and money rules; the data-export audit entry exists. | `tests/api/test_disclosure_exports.py` |
| R7 | **Static guard** | Keep `test_card_read_scope_guard.py` green with no new allowlist entries. Add a complementary static check that every `gather_*` call in `api/v1/reports.py` passes a `read_scope` argument, because the module-level guard cannot see per-endpoint gaps (S-18 / S-19). | `tests/services/test_report_gather_scope.py` |

## 7. Order and exit criteria

1. **SEC-1**: the §6 regression suite (WI-12 + R1-R7), committed failing where leaks exist.
2. **SEC-2**: WI-1, WI-2, WI-15, the scan part of WI-4, and money gating (WI-5 money part, WI-6, strategy-map in WI-15), High first.
3. **SEC-3**: governance records per §2 (WI-3, WI-4 records part, WI-5 records part, WI-7, WI-10), aggregates (WI-8, WI-9), hidden types (WI-11), guard (WI-13).
4. WI-14 belongs to the **feature phases**: it is applied to each new executive endpoint as it is built.

**Exit criteria for the SEC track**: regression suite R1-R7 green (§6); sweep green with the extended fixture; guard green without new allowlist entries; restricted-reader API tests for every WI; no money field without `costs.view` on any endpoint the executive dashboard reuses; a written security review in the PR Test Plan.

## 8. Implementation record (SEC-1 → SEC-3, 2026-10-24)

**State: implemented and verified on a local PostgreSQL test database. Uncommitted (D-22), not yet run in CI.** Nothing is marked *Completed* in `PROGRESS_REPORT.md` until it has passed CI and been merged.

### 8.1 How it was verified

| Check | Result |
|---|---|
| Extended sentinel sweep (`tests/api/test_read_scope_sentinel_sweep.py`) on the fixed code | **Pass** (sweep + non-vacuity control) |
| Same sweep on unmodified `HEAD` (`4bf4807c`, temporary worktree) | **Fails**: 24 routes leak the hidden card (ADM ×3, ARB ×2, EA requirements, improvement opportunities, NORA segments ×2, rationalization ×2, reference models ×2, `/reports/dashboard`, `/reports/freshness`, `/reports/impact`, `/reports/service-traceability`, roadmaps ×3, scenarios ×2, tech standards ×2) |
| New `tests/api/test_disclosure_regression.py` (17 tests) on the fixed code | **Pass** |
| Same file on unmodified `HEAD` | **15 of 16 fail** (the export test was added afterwards; the NORA dashboard name check already passed on `HEAD`) |
| New `tests/services/test_report_services_require_read_scope.py` (11 cases) | **Pass** |
| `tests/services/test_card_read_scope_guard.py` (incl. allowlist-not-stale) | **Pass** with no new allowlist entries (it failed on 10 modules before) |
| Existing suites of every touched module (32 files) | See §8.6 |
| **Full backend suite** | **Not run.** A first attempt hung on Windows (no `pytest-timeout`; the shell `timeout` did not stop it) and was killed; a re-run was stopped at the owner's request. **Deferred to CI** |
| `ruff format --check` + `ruff check` over `app/` and `tests/` | Clean |

### 8.2 Per-finding record

Abbreviations in the Tests column: **sweep** = the extended sentinel sweep, **DR** = `test_disclosure_regression.py`, **guard** = the read-scope static guard, **sig** = the required-`read_scope` signature guard.

| ID | Endpoint / module | Correction | Tests | Verification | Residual risk |
|---|---|---|---|---|---|
| S-01 | `GET /roadmaps/data`, `/roadmaps/{id}/data` (`roadmaps.py` `_compute_timeline`) | Timeline query scoped (`module` mode). Milestone initiative redacted (D-30). A `null` initiative on update keeps a hidden link | sweep; DR `test_roadmap_milestone_keeps_a_hidden_initiative_on_update` | Resolved | — |
| S-02 | `GET /reports/impact`; ARB review impact (`arb.py`); scenario diff (`scenarios.py`) → `impact_service.gather_impact` | `read_scope` required. A hidden centre returns 404, the same as an unknown one. Traversal never passes through a hidden card | sweep; DR `test_impact_*`, `test_unknown_card_and_hidden_card_answer_alike`; sig | Resolved | — |
| S-03 | `GET/PATCH/DELETE /arb`, `/arb/{id}` | A review with a hidden subject is **omitted**: absent from the list, 404 on detail, update and delete. Create or update with a hidden subject returns 404 | sweep; DR `test_arb_review_of_hidden_subject_is_omitted_not_deleted`, `test_write_naming_a_hidden_card_is_404` | Resolved | — |
| S-04 | `/tech-standards`, `/tech-standards/{id}`, `/tech-standards/exceptions`, radar | An exception on a hidden card is **omitted**. A hidden exception initiative or standard tech category is **redacted**. Radar counts cover visible exceptions only. Writes return 404 on hidden cards and keep hidden links | sweep; DR `test_write_naming_a_hidden_card_is_404` | Resolved | — |
| S-05 | `GET /tech-standards/compliance-scan` (`tech_standards_scan.py`) | `read_scope` required. Paths through hidden cards, categories or components are skipped | sweep; sig | Resolved | — |
| S-06 | `/rationalization/assessments/{id}`, `/rationalization/cards/{card_id}/decisions` | Decision rows on hidden cards are **omitted**; a hidden successor or initiative is **redacted**. The per-card route uses `require_card_readable`. Writes keep hidden links | sweep; DR `test_rationalization_money_and_hidden_decisions` | Resolved | — |
| S-07 | Rationalization money | Per-row `annual_cost` / `planned_savings` follow the card cost rule (`costs.view` or a stakeholder role). `target_savings` and totals need `costs.view`. Totals are summed over visible rows only | DR `test_rationalization_money_and_hidden_decisions` | Resolved | — |
| S-08 | `GET /reports/ppm/dashboard` totals | **Superseded by §9 (decided 2026-10-24, implemented).** Original note: The totals sum `ppm_cost_lines` / `ppm_budget_lines`, which every `ppm.view` holder can already read line by line through `/ppm/initiatives/{id}/costs` and `/budgets`. Under the current RBAC they disclose nothing new | — | **Open policy question:** should PPM financials require `costs.view`? Not decided here | If the answer is yes, the PPM line endpoints must change too, not only the dashboard |
| S-09 | `/improvement-opportunities` (list, create, update) | Hidden linked cards, initiative and journey card are **redacted**. An update that replaces `card_ids` re-adds the hidden ones. A `null` initiative or journey keeps a hidden link | sweep; DR `test_improvement_opportunity_keeps_hidden_cards_on_update` | Resolved | — |
| S-10 | `GET /nora-program/dashboard` | Every subsection is scoped and excludes hidden types: approvals, landscape, gaps, initiatives, waivers, compliance, strategy | sweep; DR `test_nora_dashboard_is_scoped` | Resolved (names / ids) | Count parity is asserted only through the sweep, not arithmetically (§8.4) |
| S-11 | `GET /maturity/indicators`, `POST …/refresh-suggestions`, assessment pre-fill | Whole-landscape analytics return 403 to restricted readers (TurboLens precedent), and their assessment pre-fill is skipped. Indicators exclude hidden types | DR `test_maturity_indicators_refuse_a_restricted_reader` | Resolved | Suggestion and evidence free text stored before the fix is not rewritten |
| S-12 | `GET /improvement-opportunities/realized-value` | **Superseded by §9 (decided 2026-10-24, implemented).** Original note: Under the approved D-30 table, opportunities are *redacted*, not omitted, so the reader already receives every opportunity in the list and the count reveals nothing more. The plan's WI-7 counting rule contradicted D-30 | — | Needs reviewer confirmation of the reclassification | — |
| S-13 | `/adm/workspaces*`, `/adm/phases/{id}`, artefacts | A card artefact with a hidden `ref_id` is **omitted**; the phase stays and its counts cover visible artefacts. A hidden workspace initiative is **redacted**. Artefact routes return 404 on hidden cards, and so do creates | sweep | Resolved | — |
| S-14 | `POST /improvement-opportunities/ai-suggest` | Returns 403 to restricted readers | DR `test_opportunity_ai_suggest_refuses_a_restricted_reader` (**written, not yet run**) | Implemented; test pending | Verified only when the test runs |
| S-15 | `GET /reports/dashboard`, KPI snapshots | `visible_type_clause` (new, `card_read_scope.py`) applied to every dashboard aggregate and to `compute_current_kpis` | DR `test_dashboard_counts_exclude_hidden_cards_and_hidden_types`, `test_kpi_snapshot_counts_exclude_hidden_types` | Resolved for `/reports/dashboard` | `/reports/executive` (the uncommitted prototype) is **left unchanged** as instructed: that is WI-14 / feature Phase 1 |
| S-16 | Sweep coverage | The fixture now seeds every record type of §2, plus scenarios, NORA segments, reference-model mappings and roadmaps over the sentinel's type. Required query params are filled from the seeded ids | sweep | Resolved | — |
| S-17 | Read-scope guard | Green with no new allowlist entries; it failed on 10 modules before | guard | Resolved locally | Fork CI state still to be confirmed on the PR |
| S-18 | `GET /reports/strategy-map` | Scoped. Per-initiative budget / actual follow the card cost rule. Totals are `null` without `costs.view`, with `costs_restricted: true` | sweep; DR `test_strategy_map_*`; sig | Resolved | — |
| S-19 | `/reports/freshness`, `/resilience`, `/data-flow`, `/integration-status` | `read_scope` required in each service and card loads scoped. Integration-status mapped counts join `Card` with the scope | sweep; sig | Resolved | — |

**Found and fixed during implementation:**

| ID | Endpoint / module | Correction | Tests | Verification |
|---|---|---|---|---|
| S-20 | `GET /reports/ppm/gantt` — Initiative card `cost_budget` / `cost_actual` returned without `costs.view` | The card cost rule is applied per initiative (`cost_card_ids`) | DR `test_gantt_redacts_card_cost_fields_without_costs_view` | Resolved |
| S-21 | `/nora-segments*`, `/nora-plateaus/{id}` landscape (`nora_landscape.py`) | Segment cards and the plateau landscape are scoped, with hidden types left out. A hidden segment root is redacted. Writes return 404 and keep a hidden root | sweep; sig | Resolved |
| S-22 | `/reports/gap-analysis`, `/service-traceability`, `/interoperability`, `/data-exchange-map`, reference-model explorer counts, `/technology-landscape`, `/strategy-cascade` | Every card query is scoped. The traceability root uses `require_card_readable`, and the walk goes through readable cards only. Hidden data objects are dropped with their ids | sweep; DR `test_service_traceability_*` | Resolved |
| S-23 | `/scenarios/{id}`, `/diff`, list counts, `add_change` echo, merge report | Changes naming hidden cards are omitted from responses and counts. Cost attributes in the payload and baseline are stripped by the card cost rule. Writes on hidden targets return 404 | sweep; DR `test_write_naming_a_hidden_card_is_404` | Resolved (responses; see residual 1) |
| S-24 | `/ea-requirements` | Same redact / keep-hidden pattern as opportunities | sweep; guard | Resolved |
| S-25 | `/reference-models/*`: mappings, item cards, coverage, unmapped inventory | Mapping rows on hidden cards are omitted (D-30) and coverage counts readable cards only. Mapping writes return 404 on hidden cards | sweep; sig | Resolved |
| S-26 | Event payloads (dashboard recent activity, `/events/my-cards`, card history): `adm_artefact.*` events carry the card as `ref_id` with `kind: "card"` | `scrub_event_payloads` now treats `ref_id` as a card id when `kind == "card"` | sweep (`/reports/dashboard`) | Resolved |

### 8.3 Files changed by the SEC track

- **Shared:** `services/card_read_scope.py` (`visible_type_clause`; `ref_id` in event scrubbing).
- **Services:** `impact_service.py`, `strategy_map_service.py`, `freshness_service.py`, `resilience_service.py`, `data_flow_service.py`, `integration_status_service.py`, `kpi_snapshot_service.py`, `maturity_indicators.py`, `tech_standards_scan.py`, `reference_models.py`, `nora_landscape.py`, `ppm_portfolio_service.py`.
- **API:** `reports.py`, `arb.py`, `scenarios.py`, `roadmaps.py`, `tech_standards.py`, `rationalization.py`, `ppm_reports.py`, `nora_program.py`, `nora_landscape.py`, `maturity.py`, `improvement_opportunities.py`, `ea_requirements.py`, `adm.py`, `reference_models.py`.
- **Tests:** `tests/api/test_read_scope_sentinel_sweep.py` (extended), `tests/api/test_disclosure_regression.py` (new), `tests/services/test_report_services_require_read_scope.py` (new).
- No schema change, migration, new permission key, or added/removed route. Response *shapes* are unchanged (values become `null` or rows are absent), so `docs/api/openapi.json` needs no regeneration for this track.

### 8.4 Coverage against §6

| Ref | State |
|---|---|
| R1 records and reports | Covered by the extended sweep |
| R2 counts | Covered: `/reports/dashboard` (restricted = admin − 1; hidden type excluded for both), the KPI snapshot, and the NORA dashboard (names only). **Not yet arithmetic-tested:** `/reports/bpm/dashboard`, `/reports/ppm/dashboard`, `/improvement-opportunities/realized-value`, `/risks/metrics`. `/reports/executive` is deferred to WI-14 |
| R3 charts | `total = Σ breakdown` for every distribution on `/reports/dashboard`. Per-segment drill-down parity is not tested (that dashboard has no segment drill-down endpoint) |
| R4 money | Strategy-map, Gantt, rationalization and card CSV / JSON exports, including the stakeholder bypass. The currency (D-05) and savings-conflict (D-24) rules belong to the feature phases (CR-04 / WI-14) |
| R5 governance records | DR covers ARB (omitted, 404, still visible to admin), roadmap milestone (redacted, kept on write), opportunity (redacted, kept on write) and the write-path 404s. The sweep covers the other §2 rows |
| R6 exports | DR covers card CSV / JSON (scope and money). The sweep covers the OData feed, reference-model export and risk export. PPTX / XLSX executive exports do not exist yet (WI-14) |
| R7 static guard | Implemented as a signature guard, not a text scan of `reports.py`: every shared report service takes a required keyword-only `read_scope`. A call without it is a `TypeError` on first use, and the guard fails if anyone gives the parameter a default |

### 8.5 Residual risks and pre-existing defects (not fixed; out of scope)

1. **Scenario merge** still *applies* changes that name cards hidden from the person merging. It reports and counts only the visible ones; the event keeps the true totals. Whether to refuse such a merge is a product decision.
2. **Segment resolution** expands relations from the root without checking whether intermediate cards are readable. The result is filtered, but a readable card reached only through a hidden one is still included.
3. **Free text** (ARB titles and notes, maturity evidence, scenario names) is out of scope by design (CLAUDE.md) and may name hidden cards.
4. **S-08** (PPM financial policy) needs a decision, and the **S-12** reclassification needs review.
5. **Pre-existing defect: `POST /adr` raises `TypeError`.** `adr_service.create_decision` lacks the fork's `committee` / `meeting_date` / `stage_no` arguments (a merge defect). The sweep seeds its ADR through the ORM to work around it.
6. **Pre-existing defect: the NORA dashboard "landscape" subsection** fails with a PostgreSQL `GROUP BY` error: `coalesce(architecture_state, :p)` is bound twice with different parameters. `_safe` swallows the error, so the subsection is always empty. This also happens on `HEAD`.
7. **Executive prototype** (`/reports/executive`) does not yet apply the hidden-type rule. That is WI-14, done when the endpoint is reworked in feature Phase 1.

### 8.6 Regression runs of existing suites

Run on 2026-10-24 against the local `turboea_test` database. The first combined run overlapped with another test session on the same database, which produced spurious failures (duplicate-user inserts, rolled-back fixtures). Every failing file was re-run on its own:

| Result | Tests | Cause | Action |
|---|---|---|---|
| Caused by SEC | `tests/services/test_tech_standards_scan.py` (4) | The tests called the scan without the now-required `read_scope` | Updated to pass `CardReadScope.everything()`; a restricted-scope test added. **5 / 5 pass** |
| Pre-existing (also fails on untouched `HEAD`) | `test_nora_program.py::TestAdrCommitteeFields::test_committee_fields_roundtrip`, `test_cards_type_read_permissions.py::TestWrites::test_adr_patch_keeps_links_the_caller_never_saw` | `POST /adr` `TypeError` (§8.5 item 5) | None (out of scope) |
| Pre-existing (also fails on untouched `HEAD`) | `test_reference_models.py::TestReferenceModelRelationships::test_create_list_delete_relationship` | Test posts domain `application`; the API accepts `applications` | None (out of scope) |
| Concurrency artefacts, pass in isolation | `test_card_read_scope_payloads.py`, `test_kpi_snapshot_service.py`, `test_my_workspace.py`, `test_reports_app_portfolio.py`, remaining `test_reference_models.py` | Two sessions on one test database | None |

**New security regressions: none observed** in the targeted and touched-module runs. The full suite was not run, so regressions in untouched modules cannot be excluded until CI runs.

**Frontend (no frontend file changed by SEC):**

- `npm run build` fails in `src/lib/agGridSetup.ts` (`AllCommunityModule` not exported) and `src/features/reports/MatrixReport.tsx` (read-only `current`). Cause: installed `ag-grid-community` is **32.3.9** while `package.json` requires **^35.3.1** — stale `node_modules` after the upstream merge. Neither file is modified. Not fixed: `node_modules` and the lockfile were deliberately left untouched; `npm ci` is the expected remedy, on authorisation.
- `npm run lint`: 2 errors (`react-hooks/rules-of-hooks`, conditional `useCallback`) in `src/features/cards/sections/SuccessorFieldSection.tsx`, plus 399 warnings. The file is not modified by SEC; not changed.

**Proposed `CHANGELOG.md` entry.** Not written yet: `CHANGELOG.md` and `VERSION` hold the uncommitted prototype's changes and are part of the D-22 commit plan.

> ### Security
> - Reports, governance records (ARB reviews, standard exceptions, rationalization decisions, ADM artefacts, roadmaps, scenarios, NORA segments, reference-model mappings, improvement opportunities, EA requirements) and their dashboards no longer reveal cards of types a role may not view, and cost figures on the strategy map, Gantt chart, rationalization and scenarios require the Costs permission.

## 9. Phase 1 security preparation (2026-10-24)

**State: implemented; focused tests pass locally; full suite and CI pending. Uncommitted.** The
SEC-1..SEC-3 fixes in §8 are unchanged, and so is the D-30 redact / omit behaviour of every
record type; §9 adds to them.

### 9.1 Changes

| Item | Endpoint / module | Correction | Tests (`tests/api/test_disclosure_phase1_prep.py`) | Local result |
|---|---|---|---|---|
| **S-08** (decision 2026-10-24) | `GET /reports/ppm/dashboard`; `GET/POST /ppm/initiatives/{id}/costs`, `/budgets`; `PATCH/DELETE /ppm/costs/{id}`, `/ppm/budgets/{id}`; `GET /reports/ppm/gantt` (`ppm.py`, `ppm_reports.py`, `ppm_portfolio_service.py`, `schemas/ppm.py`) | Portfolio `total_budget` / `total_actual` → `null` without `costs.view`, plus `costs_restricted`. Line `planned` / `actual` / `amount` and Gantt `capex_*` / `opex_*` → `null` unless `costs.view` or a stakeholder role on the initiative. Creating, editing or deleting a cost or budget line needs the same access (403). Counts, statuses and schedule / cost / scope RAG unchanged. The public PPM portal keeps its own `show_costs` setting (it passes no cost filter) | `test_ppm_dashboard_totals_need_costs_view`, `test_ppm_budget_lines_redact_amounts_and_refuse_blind_writes` (incl. stakeholder bypass), `test_ppm_cost_lines_and_gantt_rollups_redact_amounts` | Pass |
| **S-12** (decision 2026-10-24) | `GET /improvement-opportunities`, `/realized-value`, `PATCH /improvement-opportunities/{id}`, NORA dashboard `opportunities` (new `services/opportunity_access.py`) | An opportunity whose every linked card (cards, initiative, journey) is hidden is omitted from the list, 404 on update, and excluded from realized value and the NORA counts. An unlinked or partly readable one stays, with hidden links redacted (S-09 unchanged) | `test_opportunity_about_hidden_cards_only_is_omitted_and_uncounted` | Pass |
| **Scenario merge** (requirement 1) | `POST /scenarios/{id}/merge` (`scenarios.py`, `_merge_authorization`) | Each change is authorized like the equivalent direct write: `inventory.create` on the card type, `inventory.edit` / `inventory.archive` on the target (or the stakeholder grant), `relations.manage` for relation changes. A change naming a card hidden from the merger — including either end of a relation being removed — is **withheld**: not applied, not reported, not counted, marked `withheld`. A visible change the merger may not make is reported as `forbidden` and skipped. The merge event and response count only what the merger was shown, so the activity feed no longer carries the hidden-change totals §8.5 item 1 accepted | `test_merge_never_modifies_a_hidden_card` (incl. the activity-feed count), `test_merge_skips_changes_the_merger_may_not_make` | Pass |
| **Segment traversal** (requirement 2) | `nora_landscape.get_segment_card_ids` → `/nora-segments/{id}/cards`, the inventory `segment_id` filter (`cards.py`), report segment filters (`reports.py`) | `read_scope` now required. Traversal starts only from a readable root (a hidden root yields an empty segment), descends only through readable children, and takes related cards only from readable hierarchy members. Membership, and every count built on it, is never derived from a hidden card's hierarchy or relations | `test_segment_rooted_at_a_hidden_card_is_empty_for_the_reader`, `test_segment_descendants_do_not_pass_through_a_hidden_card` | Pass |

### 9.2 Verification actually run (2026-10-24, one test session at a time)

| Run | Result |
|---|---|
| `tests/api/test_disclosure_phase1_prep.py` (new) | **8 passed** |
| `tests/api/test_disclosure_regression.py` (incl. the S-14 test, first run) | **18 passed** |
| `tests/api/test_ppm_reports.py -k "dashboard or gantt"` | 9 passed |
| `tests/api/test_ppm.py -k "cost or budget"` | 22 passed |
| `tests/api/test_nora_landscape.py -k segment` | 3 passed |
| `tests/api/test_scenarios.py -k merge` | 3 passed, **2 failed — pre-existing**: `scenario_changes.op` is `String(8)` (`app/models/scenario.py`, unmodified), so `add_relation` / `remove_relation` changes cannot even be inserted. The new relation-change authorization path is therefore **not exercised by any test** |
| `ruff format` + `ruff check` on `app/` and the new tests | Clean |
| Preserved work (Windows fix, navigation, Executive prototype, CHANGELOG/VERSION, OpenAPI) | Byte-identical to the pre-SEC backup |

**Pending (not run, as instructed):** the full backend suite; the extended sentinel sweep and the
touched-module suites against the §9 changes; mutation testing; the frontend build (blocked by
the AG Grid mismatch, §8.6) and any frontend check; CI.

### 9.3 Remaining risks

1. **Frontend handling of `null` amounts is unverified.** The PPM cost / budget tabs, the
   portfolio KPI tiles and the Gantt now receive `null` for a reader without cost access; the
   UI was not changed or checked and may render `0`, a blank or "NaN".
2. **OpenAPI drift.** `PpmCostLineOut`, `PpmBudgetLineOut` and `PpmGanttItem` amount fields are
   now nullable, so `docs/api/openapi.json` must be regenerated (`scripts/dump_openapi.py`).
   Not done: that file also carries the uncommitted prototype's changes (D-22).
3. **Scenario relation changes** are blocked by the pre-existing `op` length defect; once it
   is fixed, the relation branch of `_merge_authorization` needs a test.
4. **Withheld scenario changes are never applied.** A scenario merged by someone who cannot
   see all its cards is marked merged; an authorized user cannot apply the withheld rest
   (same semantics as conflicts today). Whether to support a partial / re-merge is a product
   question.
5. **Executive prototype** (`/reports/executive`, uncommitted, untouched): it calls
   `ppm_portfolio_service.build_dashboard` directly and does **not** inherit the S-08 route-level
   redaction, does not apply the hidden-type rule, and does not use `opportunity_access`. It must
   adopt all three (WI-14) before it is exposed.
6. Unchanged from §8.5: free text, the `POST /adr` defect, the NORA landscape `GROUP BY` defect.
7. A stray `backend/%SystemDrive%/` directory (≈1 MB Windows cache) was created by the aborted
   full-suite run on 2026-10-24; it is untracked and should be deleted by the owner.

**Proposed `CHANGELOG.md` addition** (not written, D-22):

> - PPM budget, cost and portfolio amounts now require the Costs permission (or a stakeholder role on the initiative); scenario merges no longer change cards the person merging cannot see or edit; NORA segments and improvement-opportunity counts no longer include cards or records a role may not view.

## 10. Final security integration (2026-10-24)

**State: implemented; targeted backend tests pass; frontend tests could not run locally; full
suite and CI pending. Uncommitted.** It closes §9.3 items 1-5.

### 10.1 Changes

| Area | Files | Change |
|---|---|---|
| **Scenario merge integrity** | `api/v1/scenarios.py` | A merge that leaves any change unapplied for want of authority (`withheld` — names a card hidden from the merger; `forbidden` — the merger lacks the write permission) no longer marks the scenario `merged`: it stays open, the unapplied changes keep their row and status, and the response carries `complete: false`. A re-merge skips changes already `applied`, so a later authorized merger applies only the rest. The event is `scenario.merge_partial` (counts of applied / conflicts / forbidden only) instead of `scenario.merged`. Conflicts (existence / drift) keep their existing semantics: reported, skipped, and not blocking completion. Hidden changes are still never listed or counted for the merger; `complete: false` is the only signal, and it does not say which change or how many |
| **`scenario_changes.op` defect** | `models/scenario.py`, **migration `1162_widen_scenario_change_op.py`** (revises head `154`) | `VARCHAR(8)` → `VARCHAR(32)`, so `add_relation` / `remove_relation` changes can be saved. Widening is metadata-only in PostgreSQL; the downgrade narrows without deleting data and fails if relation changes exist |
| **Scenario UI** | `ScenarioPlanning.tsx`; `reports.json` (en, ar) | Merge preview warns when the merge would be partial ("Some changes need someone with broader permissions… the scenario stays open"); labels for the `forbidden` ("Not permitted") and `withheld` ("Pending") outcomes |
| **PPM financial access — UI** | `RestrictedAmount.tsx` (new), `PpmCostTab.tsx`, `PpmOverviewTab.tsx`, `PpmProjectDetail.tsx`, `PpmPortfolioView.tsx`, `ppmPortfolioModel.ts` (`costsWithheld`), `ExecutiveStrategyMap.tsx`, `types/index.ts`; `ppm.json` (en, ar) | Every withheld amount renders **"Restricted"** (lock icon, tooltip), never 0: cost / budget KPIs, variance, budget bars and charts (hidden), table amounts, portfolio cost bars and group totals (a group with a withheld row shows Restricted rather than an understated sum), portfolio total budget, strategy-map total budget. Add / edit / delete of cost and budget lines are hidden when restricted (the API refuses them). The project detail passes the card's effective `can_view_costs` — the same project-level rule the API applies (`costs.view` or a stakeholder role on that initiative) — and a `null` amount is treated as restricted even before that permission has loaded. Non-financial indicators are unchanged |
| **Executive endpoint** | `api/v1/executive_dashboard.py` (prototype; only the security wiring changed) | Hidden card types now excluded (D-01) from every aggregate — portfolio counts, process and rationalization loaders, delivery initiatives — in the card query itself, before aggregation, as `/reports/dashboard` does. Scope (`CardReadScope`), the risk register's scoped loader and the money rules were already applied and are unchanged: delivery money and planned savings need `costs.view` itself (the PPM portfolio rule, S-08; the rationalization totals rule, S-07), shown as `restricted`. No permission was broadened. The endpoint shows no improvement-opportunity figure; one added later must count through `opportunity_access` (S-12) |
| **OpenAPI** | `docs/api/openapi.json` | Regenerated with `scripts/dump_openapi.py`. Structural diff against the previous file: `PpmBudgetLineOut`, `PpmCostLineOut`, `PpmGanttItem` (nullable amounts) and the `/nora-program/dashboard` description (from the SEC-3 docstring); no path added or removed, so the prototype's routes are preserved |

### 10.2 Verification actually run (one test session at a time)

| Run | Result |
|---|---|
| `tests/api/test_disclosure_phase1_prep.py` (+3 new: partial merge kept open and completed by an authorized merger; relation change recorded + `relations.manage` enforced; executive scope / hidden types / cost rules) | **11 passed** |
| `tests/api/test_scenarios.py` (whole file) | **10 passed** — including the two relation tests that failed before the `op` fix |
| `tests/services/test_alembic_timestamp_defaults.py` | 197 passed, **4 failed — pre-existing**: migrations `1154`, `1155`, `1157`, `1159` (reference models, viewpoints) create `created_at` / `updated_at` without `server_default`; `1162` passes |
| `ruff format` / `ruff check` (`app/`, migration, tests) | Clean |
| `tsc --noEmit` (frontend) | No errors in changed files; 2 pre-existing (`agGridSetup.ts`, `MatrixReport.tsx`, the AG Grid mismatch) |
| ESLint (changed frontend files) | Clean |
| en / ar JSON | Valid |
| Vitest: `PpmCostTab.test.tsx` (+2 restricted cases), `ppmPortfolioModel.test.ts` (+`costsWithheld`) | **Could not run**: the global test setup imports `lib/agGridSetup.ts`, which fails on the installed `ag-grid-community` 32.3.9 vs required ^35.3.1. Written, **pending** a dependency reinstall |
| Preserved work | Windows fix, navigation, Executive service + frontend, CHANGELOG/VERSION byte-identical to the backup; `types/index.ts` differs from it only by the PPM type lines |

**Pending verification (not run):** the full backend suite; the extended sentinel sweep and
`test_disclosure_regression.py` re-run after §10; the migration applied to a real upgraded
database (`alembic upgrade head`); all frontend unit tests (blocked) and a visual check of the
PPM screens, scenario page and strategy map; mutation testing; CI.

### 10.3 Remaining risks

1. **Frontend unverified at runtime** — the Restricted rendering is type-checked and linted but
   no Vitest or browser check has run (AG Grid mismatch; `npm ci` needs authorisation).
2. **Pre-existing migration defect** — `1154`/`1155`/`1157`/`1159` lack timestamp server
   defaults: on an upgraded (not freshly created) database, inserts into those reference-model
   and viewpoint tables fail. Out of scope; needs its own fix.
3. **Migration `1162` not run against an upgraded database** — only the model (via `create_all`)
   is exercised by the tests.
4. **Partial-merge signal** — `complete: false` tells a merger that something they cannot apply
   remains (possibly hidden), without identifying it. Accepted as the minimum needed to keep
   unapplied work from being lost.
5. **Conflicts still do not block completion** (unchanged behaviour); a conflicting change is
   skipped permanently once the scenario is merged.
6. Unchanged: free text naming hidden cards; `POST /adr` `TypeError`; the NORA landscape
   `GROUP BY` defect; the stray `backend/%SystemDrive%/` directory.

### 10.4 Unresolved decisions

| ID | Question | Recommendation |
|---|---|---|
| U-1 | Should a scenario **conflict** (drift / missing target) also keep the scenario open, like an authorization skip? | Keep today's behaviour until a product owner decides; it is not a disclosure issue |
| U-2 | Who may complete a partially merged scenario — anyone with `scenarios.merge`, or only its creator / an admin? | Anyone with `scenarios.merge` (current); each change is still authorized individually |
| U-3 | Authorise `npm ci` to restore the declared AG Grid version so the frontend tests and build can run | Yes, before Phase 1 frontend work |
| U-4 | Schedule the fix for the four migrations without timestamp server defaults | Separate fix before the next release |
