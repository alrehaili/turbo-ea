# Security remediation plan (mandatory, Phase 1)

**Status: plan, not implemented. No code changed.**

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
