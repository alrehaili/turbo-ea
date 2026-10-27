# Progress report

## Phase 3 — EA governance effectiveness: decisions recorded, plan ready (2026-10-25)

**State: planning only. No application code, model, migration, API or frontend file has changed; no test or build was run.** Base: `main` at `1e5968bb` (2.36.1). Documentation changes are uncommitted.

- Approved with changes: D-10, D-13, D-28, D-32, D-33, D-34, D-35, D-36. Deferred: D-11. Implementation details I-7..I-13 recorded for review. All in `DECISION_LOG.md` §3.1.
- Still open, each blocking one later batch: D-37 (3.6), D-38 (3.3), D-39 and D-40 (3.2, parts), D-41 (3.4), D-42 (3.5).
- Batch plan with files, tests and acceptance criteria: `PHASED_DELIVERY_PLAN.md`, Phase 3. Traceability: `REQUIREMENTS_TRACEABILITY_MATRIX.md` P3-01..P3-14.
- **Next: Batch 3.1** (activity, assessment coverage, rule-based standards compliance GOV-03). It needs no open decision and no schema change.
- The local database was not running during the review, so record volumes (how much history each indicator has) were not counted.

### Continuation prompt (Batch 3.1)

> Continue Phase 3 of the Executive Dashboard on `main` (base `1e5968bb`, v2.36.1). Do not repeat the assessment. Read `docs/executive-dashboard-implementation/DECISION_LOG.md` §3.1 (approved D-10, D-13, D-28, D-32..D-36; D-11 deferred; I-7..I-13) and `PHASED_DELIVERY_PLAN.md` "Batch 3.1", then implement Batch 3.1 exactly as specified: assessed population in `tech_standards_scan.py`, new `services/executive/governance.py`, `GET /reports/executive/governance` and the `GOV-03` drill-down, `GOV-03` in the registry and daily capture, NORA profile v12 option for `KPI.metricKey`, `ExecutiveGovernance.tsx` page with EN/AR strings, user manual and CHANGELOG / VERSION minor bump. Keep Activity, Effectiveness and Impact apart; show Not Available with its reason for every indicator whose batch is not built. Do not start Batches 3.2-3.6 (D-37..D-42 are open). One focused validation pass at the end (the batch's new and directly affected tests only); no full suites, builds, mutation tests or `npm ci`. Do not commit or push without my authorisation. Update `PROGRESS_REPORT.md` and the RTM rows P3-01..P3-03 when done.

## Current correction pass — 2026-10-25, main based on f00776f7

This section supersedes older branch/working-tree and pending-test statements below;
those entries remain historical records. Independent validation of `f00776f7` ran
1,179 tests: **1,167 passed, 12 failed, 0 skipped**, with no new Executive Dashboard
behavioral regression. Later historical entries already record successful Phase 2
validation; early "not run" entries do not mean the tests were never subsequently run.

The user authorized corrections of those failures only, on `main`, without a branch,
commit, push, full suite, mutation testing, build or dependency reinstall. No new
Executive Dashboard phase, KPI formula or approved decision changes are included.

### Corrections (2.36.1, uncommitted)

| Root cause | Correction and safety boundary |
|---|---|
| Four migrations omitted timestamp defaults | New **1165**, after 1164, installs `now()` only on missing timestamp defaults in `viewpoint_definitions`, `reference_model_mappings`, `reference_model_versions`, `reference_model_relationships`. Published 1154/1155/1157/1159 are unchanged. Existing values, types, nullability and custom defaults are preserved. Downgrade retains the additive repair, as 151 does. The recurrence guard recognizes only these four explicitly repaired historical migrations. |
| Executive permission absent from complete default-role maps | BPM Admin, Member and Viewer explicitly **deny** `reports.executive_dashboard`; Admin keeps its existing wildcard. No executive access is granted automatically or existing custom role grant revoked. |
| Missing fork route policies and stale permission expectations | 84 routes receive inventory/report/module policies; reference-model management matches its nav's manage authority. Two public viewpoint catalogue routes are explicitly ungated; their destination pages retain their own gates. Tests read the backend permission registry, including `adm.view`, instead of a hand-kept subset. |
| Upstream locale guard assumed nine non-English languages | Checker derives targets from the runtime EN/AR registry; dormant translations remain unchanged. Two genuinely missing Arabic governance labels are added. Eight singular differences express count grammatically: only count omission in exact zero/one/two forms is permitted; other placeholders and variable-count forms remain strict. Frontend parity also checks nested labels and ADM. |
| 44 transfer blobs lacked classification | Five receive reference rewriting; 39 receive individually justified exemptions. The adjacent ADM card-kind soft FK is repaired too. Module UUIDs, prose and external source URLs are preserved. |

### Transfer audit of the 44 fields

| Fields | Treatment |
|---|---|
| `ScenarioChanges.payload`, `.baseline` | Remap relation-operation endpoints/removal ids and embedded card/tag references; deltas and drift checks must name the imported landscape. |
| `Roadmaps.config` | Current UI stores type/group keys; the API accepts a configuration bag, so reuse report remapping defensively for card/tag scopes. |
| `WebPortals.tiles` | Rewrite local card links in targets; preserve labels, external URLs and module links. |
| `AdmPhaseArtefacts.ref_url` | Rewrite local card links; preserve external URLs. Also remap the adjacent `ref_id` only for `kind="card"`; module artefacts keep their UUIDs. |
| 37 prose/evidence fields | Preserve descriptions, notes, rationale, evidence and narratives verbatim. UUID mentions in historical prose are not executable references. Exhaustive exemptions and reasons are in `test_workspace_io_id_bearing_columns.py`. |
| `NoraSegments.related_type_keys` | Metamodel keys, not instance-local UUIDs. |
| `ReferenceModelVersions.snapshot` | `snapshot_items()` stores code/parent_code, names, description and sort order; no card/relation/tag references. |

No table/column or on-disk bundle shape is added; workspace format remains **1**.
New rewriters use existing source-id maps, preview and conservative healing rules.
Legacy bundles without source-id maps retain existing unresolved-reference behavior.

### Post-correction validation

One post-correction pass completed under the normal configurations, using local
PostgreSQL `turboea_test` with `TEST_DB_REQUIRED=1`. **All 12 original failing cases
pass. No tests were retried.**

| Focused check | Passed | Failed | Skipped |
|---|---:|---:|---:|
| Backend: original feature/security/compatibility selection plus new migration and transfer regressions | 1,053 | 0 | 0 |
| Frontend: executive components, KPI section, Dashboard, route policies/guard and EN/AR parity | 221 | 0 | 0 |
| Total | **1,274** | **0** | **0** |

The migration regression exercises actual corrective PostgreSQL DDL against isolated
tables, preserves existing rows/custom defaults, repeats the upgrade and verifies inserts
without explicit timestamps still work after downgrade. It does not substitute
`create_all` for migration validation. Transfer regressions cover preview/apply count
agreement, card/relation remapping, stable module ids/prose/external URLs and repeat-import
idempotency; the existing transfer remap unit/integration selections also pass.

Additional checks: Ruff formatting/lint on changed Python files and ESLint on changed
TypeScript files pass; `git diff --check` is clean; Alembic has one head, **1165**;
`check_locales.py report --base f00776f7` exits 0 with **0 fatal UI gaps**. Nonfatal
documentation/suspect-value observations are not UI failures. No full suites, mutation
testing, build, `npm ci`, browser run, commit or push was performed. Test-only warnings
remain (short fixture JWT key; Recharts dimensions in jsdom); they are not failures.

### File inventory

| Area | Changed files |
|---|---|
| Additive DB repair | `backend/alembic/versions/1165_fork_timestamp_defaults.py` (new); `backend/tests/services/test_alembic_timestamp_defaults.py`; `backend/tests/services/test_alembic_1165_timestamp_defaults.py` (new) |
| Least-privilege defaults | `backend/app/core/permissions.py`; `backend/tests/core/test_permissions.py` |
| Route coverage | `frontend/src/lib/routePermissions.ts`; `frontend/src/lib/routePermissions.test.ts` |
| EN/AR checks and labels | `scripts/i18n/check_locales.py`; `backend/tests/services/test_check_locales.py`; `frontend/src/i18n/i18n.test.ts`; `frontend/src/i18n/locales/ar/grc.json`; fork override in `CLAUDE.md` |
| Transfer classification/rewriting | `backend/app/services/workspace_io/remap.py`; `backend/app/services/workspace_io/sections.py`; `backend/tests/services/test_workspace_io_id_bearing_columns.py`; `backend/tests/services/test_workspace_io_remap.py`; `backend/tests/services/test_workspace_io_fork_blob_roundtrip.py` (new) |
| Release/progress record | `VERSION` (2.36.1); `CHANGELOG.md`; this progress report |

Migration 1165 is provided for deployment, not applied to a development/production
workspace. Finance currency verification, D-31, disabled fork GitHub Actions and
phase-wide browser/release validation remain outside this correction pass.

---

**Reporting date:** 2026-10-24 (updated after the SEC-1 to SEC-3 implementation, the Phase 1 security preparation, the final integration, and the Phase 1 KPI-correctness implementation)
**Rule:** planning documents do not count as implementation. A track or phase becomes *Completed* only when its definition of completion in `PHASED_DELIVERY_PLAN.md` is met (merged, tested, documented). **The Security Remediation Track is implemented and committed but not yet run in CI. Phase 1 (KPI correctness) is functionally implemented, including the review corrections, and uncommitted, with focused local tests only. D-31 and currency verification remain open.**

## Status

| Stream / phase | Status | Notes |
|---|---|---|
| **Security Remediation Track (SEC)** | **Pending verification** (implemented incl. §9 preparation and §10 final integration; full backend suite not run; frontend tests blocked; not in CI; uncommitted) | SEC-1, SEC-2 and SEC-3 were implemented on 2026-10-24 under D-01 and D-30. All 26 findings are resolved: S-08 and S-12 were decided on 2026-10-24 and implemented, together with scenario-merge authorization and readable-only segment traversal (`SECURITY_REMEDIATION_PLAN.md` §9; 8 new focused tests pass). Locally, the extended sweep, 17 new disclosure tests, the signature guard and the read-scope guard pass. On unmodified `HEAD` the same sweep fails on 24 routes and 15 of 16 of the new tests fail. The full backend suite was not run (stopped at the owner's request) and the new S-14 test has not run yet; both are deferred to CI. Evidence: `SECURITY_REMEDIATION_PLAN.md` §8. The track is not *Completed* until it is committed, green in CI and merged. |
| Phase 0: decisions, KPI ratification, data ownership | **In Progress** (planning) | Phase 1 decisions approved 2026-10-22 (D-01, D-02, D-05, D-06, D-22, D-24, D-30) plus D-18. 23 decisions remain open (11 blocking, incl. the new D-31). KPI ratification and data stewardship not started. |
| Phase 1: prototype baseline and KPI correctness | **Pending verification** (functionally implemented 2026-10-24, review corrections H1 and M1–M3 applied, VERSION 2.34.0; focused tests pass locally; not in CI; uncommitted) | CR-01..CR-10 applied to the Executive tab (see *Phase 1 implementation record* below). Two items stay **open as business decisions, not implementation gaps**: the financial period of planned savings (**D-31**) and **Finance verification of the instance currency** (D-05). Not *Completed* until committed, green in CI (incl. mutation gates) and merged. |
| Phase 2: CEO overview, KPI history, decision intelligence | **In Progress** (D-19, D-21, D-26, D-17a implemented on branch `executive-kpi-history` (`0ce8920b` + merge-readiness round, uncommitted), locally validated and browser-checked 2026-10-25 as 2.36.0; not merged, not in CI; unblocked scope committed 2026-10-25 as 2.35.0; review corrections H-1–H-4, M-1, M-3, M-5 applied 2026-10-25, uncommitted; focused backend tests pass; frontend tests pass only under a scratch config — see *Phase 2 review corrections*; not in CI) | D-03, D-04, D-07, D-17 approved with changes on 2026-10-24. Built: Executive sub-navigation, CEO overview with the standard KPI tile, period filter, decisions page, drill-downs. **Blocked:** KPI history (D-19), targets and owners on tiles (D-26, then a ratification mechanism per D-17), org filter (D-07: relations and data), TR-01 (D-21), SVC-02 (D-09); slots 2 and 5 wait for Phases 3 and 4. See *Phase 2 implementation record*. |
| Phase 3: EA governance effectiveness | **Not Started** | Blocked by D-10, D-13 |
| Phase 4: Business impact, benefits realisation, ROI | **Not Started** | Blocked by D-12, D-14, D-15 |
| Phase 5: Transformation, services, processes, maturity, portfolio | **Not Started** | Blocked by D-08; needs data |
| Phase 6: Reporting, bilingual validation, accessibility, QA | **Not Started** | Depends on Phases 2-5 |

*Phase 0 is shown as In Progress because its decision work has begun. This is planning progress, not implementation.*

## Planning progress (documentation only, all uncommitted)

| Deliverable | State |
|---|---|
| Comprehensive assessment (10 docs) + index `README.md` | Written; superseded 2026-10-21 docs identified |
| Implementation plan (13 docs) | Written; aligned with the approved decisions on 2026-10-22 |
| Decision review package + final recommendations | Written; superseded in part by the approvals (notes added) |
| Security plan | Updated: S-18, S-19, WI-15; D-30 record-treatment table; disclosure regression suite R1-R7; separate SEC track; **§8 implementation record (2026-10-24)** |
| Phased plan | Restructured: SEC track separated from feature phases; Phase 1 = baseline + KPI correctness |
| Contradictions resolved | D-02 staleness (no invented deadline); D-24 conflict rule (no latest / lowest selection); D-05 currency (no relabel, no cross-currency sums); D-17 reclassified to Phase 2; EN/AR language policy throughout; amber-for-missing-report statement superseded |

## Earlier work that is **not** a phase completion

| Item | State | Plan |
|---|---|---|
| Executive tab prototype | Built, **uncommitted, no tests** | Phase 1 unit (c) |
| Windows startup fix (`brand_icons.py`) | **Uncommitted** | Phase 1 unit (a) |
| Responsive navigation (`AppLayout.tsx`) | **Uncommitted** | Phase 1 unit (b) |
| Planning documentation | **Uncommitted** | Phase 1 unit (d), no version bump |
| Security remediation (SEC-1..SEC-3 code + tests) | **Uncommitted**, verified locally | Its own commit, separate from units a-d, on authorisation. CHANGELOG entry proposed in `SECURITY_REMEDIATION_PLAN.md` §8 |

## Blockers and risks

| # | Item | Impact | Owner |
|---|---|---|---|
| 1 | Feature-phase implementation not yet authorised (SEC was authorised and is implemented) | Feature phases cannot start | Business owner |
| 2 | Uncommitted work: backed up before SEC began (`C:\Users\user\turbo-ea-backups\2026-10-22-pre-sec`, verified with `git apply --check -R`) but not committed | Possible loss of the SEC work done after the backup | Business owner (authorise commits) |
| 3 | D-31 open (financial period of planned savings) | Blocks the period half of CR-04 only: planned savings are deduplicated per application with conflicts excluded, but are not bound to a fiscal year | App portfolio owner + CFO |
| 4 | **Currency verification open (D-05)**; other live-data checks not done: savings conflicts, fiscal month, report dates | PPM lines and planned savings store no currency, so the Executive tab labels them with the instance currency setting. Until Finance confirms the setting matches the stored amounts, every money figure on the tab may carry the wrong currency label. No amount is converted and the setting is not changed by code | Tech lead + Finance |
| 5 | Fork CI state unknown; the read-scope guard is now green locally (S-17) | Possible pre-existing failures elsewhere | Tech lead |
| 6 | Empty data (KPI cards, GovService, maturity, milestones, pillars, opportunities) | Feature pages would show "Not available" | Data owners |
| 7 | ~~S-08 / S-12 decisions~~ — decided and implemented 2026-10-24 | — | — |
| 8 | Pre-existing defects found during SEC: `POST /adr` raises `TypeError` (merge defect); the NORA dashboard's landscape subsection has a `GROUP BY` error and is always empty | ADR creation is broken; one dashboard section is empty | Tech lead |
| 9 | Frontend build fails: installed `ag-grid-community` 32.3.9 vs required ^35.3.1 (stale `node_modules`); lint has 2 pre-existing errors in `SuccessorFieldSection.tsx` | No green frontend build locally (no frontend file changed by SEC) | Tech lead (`npm ci` on authorisation) |
| 10 | Full backend suite not run locally (first run hung on Windows, re-run stopped to save usage) | Regressions in untouched modules not excluded until CI | Tech lead |
| 11 | ~~Frontend / OpenAPI for nullable PPM amounts~~ — UI renders "Restricted" and the spec is regenerated (§10); the frontend tests written for it cannot run until item 9 is fixed | Runtime UI unverified | Tech lead |
| 12 | ~~`scenario_changes.op` length~~ — fixed by migration `1162` (§10); migration not yet run on an upgraded database | — | Tech lead |
| 13 | ~~Executive endpoint security~~ — hidden types now excluded; scope and money rules confirmed; no opportunity figure yet (§10) | — | — |
| 14 | Pre-existing migrations `1154`/`1155`/`1157`/`1159` create timestamps without `server_default` (guard test fails) | Inserts into those tables fail on upgraded installs | Tech lead |
| 15 | Unresolved decisions U-1..U-4 (`SECURITY_REMEDIATION_PLAN.md` §10.4) | Scenario conflict policy, partial-merge completion, `npm ci`, migration fix | Business owner + tech lead |

## Phase 1 implementation record (2026-10-24)

Implemented in the working tree on `main` (no branch, **uncommitted**, not deployed), on top of v2.33.0 (`8f7251a0`). Scope A–F of the Phase 1 brief; nothing outside the Executive tab, its endpoint, one admin setting and the Overview relabels.

### What was implemented

| Item | Rule applied | Where |
|---|---|---|
| A. Initiative delivery | Four states (On track / At risk / Off track / Unknown-not reported); worst of schedule, cost, scope in the latest report; no report, a stale report or an unrecognised value is *not reported*, never healthy and never At Risk; completed / on-hold initiatives excluded and shown separately; **coverage is its own figure** (reported ÷ in flight, stale count, newest and oldest counted report dates); headline = On track ÷ *reporting* initiatives (null when none reported). PPM off → `initiativeStatus` is the source (D-02 note). | `services/executive_dashboard.py` `report_state`, `summarize_delivery_health` |
| A. Staleness | `general_settings.initiativeReportStalenessDays`, **no default**; unset ⇒ no report is ever stale, and the tab says so. Admin-only `GET` / `PATCH /settings/initiative-report-staleness` (1–3650 or `null` to clear), audited as `report_staleness_days`; a card in Admin → Settings. | `api/v1/settings.py`, `features/admin/InitiativeReportStalenessSetting.tsx` |
| B. Financial period | `fiscalYearStart` via `fiscal_year.py`; budget = budget lines of the selected FY; actuals = cost lines dated inside it (`fiscal_year_bounds`, new pure helper); years never combined; undated cost lines counted, never summed. `?fiscal_year=` (1900–2200) with a period selector listing the years that have lines plus the current one. Each initiative's **own** lines only, as the PPM board's KPI bar, so the merged v2.178 roll-ups cannot double-count. | `load_fiscal_money`, `summarize_budget`, `api/v1/executive_dashboard.py` |
| B. Cost permission | Totals need `costs.view` itself (S-08 portfolio rule); without it the amounts are **not read at all**, the response names the period only, and the UI shows `RestrictedAmount`. | as above |
| C. Planned savings | Identity = application (`card_id`); agreeing estimates count once (`duplicates_merged`); differing estimates are a conflict: listed with every candidate and assessment, **excluded** from the total, range shown; no latest / lowest pick; a decision with no estimate is not a candidate. Labelled Forecast. Realised savings are a separate `not_available` figure. | `summarize_planned_savings`, `summarize_rationalization` |
| C. Savings period | **Blocked (D-31).** No period field or rule invented; payload `period: {status: "blocked", decision: "D-31"}` and the tab says the figure is not tied to a fiscal year. | — |
| D. Currency | Every money block names `currency` (the instance setting: PPM lines and planned savings have no currency of their own, so it is their source currency). Formatted with `Intl` currency + compact notation in the **payload** currency, SAR glyph override reused from `lib/currency.ts`. No conversion, no relabel, no cross-currency total, no change to the currency setting. | `executiveFormat.ts` |
| E. Terminology | "Data completeness" (Executive + Overview + Admin tab + attention band); Approved % removed, approval mix shown as "Repository review status" (not compliance); "Past planned end-of-life"; process diagrams shown as "Process documentation coverage … not automation or maturity" and removed from the headline; repository metrics (card counts, completeness, review status, types, lifecycle) moved into a collapsed **specialist** section, out of the CEO headline. | `ExecutiveTab.tsx`, `en`/`ar` `common.json` |
| F. Visibility | Unchanged and re-checked: `CardReadScope` (module mode) + `visible_type_clause` in every card query and on the initiative population before counting; risks through the register's scoped loader; type chart and lifecycle donut sum to the total. | endpoint |
| UI | Five headline tiles, each with a plain-language definition, a provenance chip (Recorded / Self-reported / Forecast / Restricted / Not available; legend states nothing is Finance-verified yet) and a permission-checked drill-down (`/ppm`, `/grc?tab=risk`, `/rationalization`, `/reports/data-quality`, `/reports/lifecycle`, conflict rows → card). Generated time and latest report date in the header. Responsive grid; RTL via the existing chart helpers. | `ExecutiveTab.tsx` |

### Reused, not duplicated

`CardReadScope`, `visible_type_clause`, `PermissionService` (`costs.view`), `ppm_portfolio_service.load_initiatives` / `latest_reports`, `fiscal_year.py` (`get_fiscal_year_start`, `current_fiscal_year`, `fiscal_year_for`), `risks.load_filtered_risks`, `bpm_dashboard_service`, `RestrictedAmount`, `lib/currency.ts` (`currencySymbolOverride`), `fiscalYearLabel`, `useApiQuery`, `useDateFormat`, the settings audit helper `_audit_setting`, the existing chart building blocks and RTL helpers.

### Files changed

Backend: `app/services/executive_dashboard.py`, `app/api/v1/executive_dashboard.py`, `app/api/v1/settings.py`, `app/services/fiscal_year.py`; new tests `tests/services/test_executive_dashboard_kpis.py`, `tests/api/test_executive_dashboard_phase1.py`. Frontend: `features/dashboard/executive/ExecutiveTab.tsx`, new `executiveFormat.ts`, `features/admin/InitiativeReportStalenessSetting.tsx`, `features/admin/SettingsAdmin.tsx` (one card), `types/index.ts`, `i18n/locales/{en,ar}/{common,admin}.json`; new tests `executiveFormat.test.ts`, `ExecutiveTab.test.tsx`; `OverviewTab.test.tsx` (relabel). `docs/api/openapi.json` regenerated. Review corrections added `docs/guide/dashboard.{md,ar.md}`, `docs/admin/settings.{md,ar.md}`, `CHANGELOG.md` (2.34.0) and `VERSION` (2.34.0). No new permission key, no new table, no Phase 1 migration. (The separate startup fix, merge migration `1163` joining the `1162` and `156` heads, is committed and pushed as `7ead9e07`; it is not part of the Phase 1 working-tree changes.)

### Payload changes (`GET /reports/executive`)

Added `currency`, `ppm_enabled`, `?fiscal_year=`. `portfolio`: `avg_data_quality` → `data_completeness`, `approved_pct` removed, `last_updated` added. `delivery`: replaced `off_track` / `health_*` with `source`, `staleness_days`, `in_flight`, `excluded`, `states`, `on_track_pct`, `coverage`, `dimensions`; `budget` now per fiscal year with `currency`, `execution_pct`, `undated_cost_lines`, `available_years`. `processes.diagram_coverage` → `documentation_coverage`. `rationalization`: `applications`, `realized_savings`; `planned_savings` gains `currency`, `applications_counted`, `duplicates_merged`, `conflict_count`, `conflict_detail` (`ok` / `restricted`), `conflicts` and `excluded_range` (both `null` without `rationalization.view`), `period`, and `provenance` is now `forecast`. The Executive tab is the only consumer.

### Review corrections (2026-10-24)

An implementation review of the working tree found one High and three Medium items; all four are corrected (uncommitted). The Low items (L1–L11 of the review) are not corrected and are listed under *Pending verification*.

| Finding | Correction | Evidence |
|---|---|---|
| **H1** — the planned-savings conflict list named applications and assessments and each assessment's estimate to any caller with `reports.executive_dashboard` + `costs.view`, bypassing the rationalization module's own `rationalization.view` | `summarize_rationalization(..., can_view_rationalization=)`: without `rationalization.view` the response keeps the total and `conflict_count` but sets `conflicts` and `excluded_range` to `null` (the range would reveal both estimates of a single conflict) and `conflict_detail: "restricted"`. The tab shows a locked count-only notice (EN + AR). Cards in the list are still limited to the caller's readable, visible-type cards | Unit test `test_conflict_detail_needs_rationalization_view`; API test extended with a `finance` role (costs, no rationalization); Vitest `shows only the conflict count without rationalization access` — all pass |
| **M1** — the user manual and the endpoint docstring described the old tab ("aggregates only, never card names", data quality, approved share, all-time budget) | `docs/guide/dashboard.md` / `.ar.md` Executive section rewritten; `docs/admin/settings.md` / `.ar.md` gain *Initiative report staleness*; the endpoint docstring names the conflict list as the one record-level exception and its permissions | Review of the text; `mkdocs build --strict` **not run** |
| **M2** — no CHANGELOG entry or VERSION bump | `VERSION` 2.34.0; `CHANGELOG.md` `[2.34.0] - 2026-10-24` with Added / Changed / Security entries | — |
| **M3** — money is labelled with the instance currency without verification | Documented in the manual and the docstring (amounts shown in the currency set under Admin → Settings, never converted). **The verification itself stays open**: it is a Finance decision, not a code change (blocker 4) | — |

### Validation

| Check | Result |
|---|---|
| `python -m ruff check` / `ruff format` on changed backend files | Clean |
| `npx tsc -b --noEmit` | Clean |
| Backend focused run, after the review corrections: `test_executive_dashboard_kpis.py`, `test_executive_dashboard_phase1.py`, `test_disclosure_phase1_prep.py::test_executive_applies_scope_hidden_types_and_cost_rules` (local Postgres `turboea_test`) | **28 tests passed, exit code 0, no skips or failures** (20 builder, 7 API, 1 disclosure). The project's pytest output prints no final count line; the count is from the progress dots and `-rfEs`. The earlier run before H1 gave 27 / 27. |
| `test_audit_log_guard.py` (first focused run only) | 3 **pre-existing** failures unrelated to this change: fork routes `settings.py::update_framework_profile` / `update_strategy_house` / `update_governance_settings` and `metamodel.py::*_standard` record no audit row, and 3 fork exports are unlisted. The new staleness route **does** record (checked with the guard's own detector). |
| Frontend focused run, after the review corrections: `features/dashboard/executive` (`ExecutiveTab.test.tsx`, `executiveFormat.test.ts`) and `i18n.test.ts` | **3 files, 155 tests passed.** An earlier run also covered `OverviewTab.test.tsx`: its relabelled assertion is updated, but the file has 6 **pre-existing** failures — it expects "Browse by Type" and the trend caption, which `OverviewTab.tsx` no longer renders (component untouched here). |
| `ruff` / `tsc` after the review corrections | Clean |
| Not run | Full backend and frontend suites, ESLint, `mkdocs build --strict`, mutation testing, build, e2e, CI, a browser check |

### Pending verification

**Open business decisions (not implementation gaps):**

- **D-31** — the financial period of planned savings. Until decided, savings are deduplicated per application only and the tab says they are not tied to a fiscal year.
- **Currency verification (D-05)** — Finance confirms that the instance currency setting is the currency the PPM lines and planned savings were entered in. Until then every money label on the tab is unverified.
- **Interim savings presentation** (review M4) — whether an application-only total is acceptable before D-31, or should be hidden.

**Release validation:**

- Visual check of the tab in EN and AR (RTL) at phone and desktop widths, in a browser.
- Live data: real initiative report dates, savings conflicts, the instance currency and fiscal month.
- A cross-tab parity test (Overview / Executive / Workspace / Admin totals for one caller, CR-06).
- CI: diff coverage, mutation score on changed lines, the OpenAPI drift check.
- `mkdocs build --strict` for the rewritten manual pages; the other 8 locale pages of `dashboard` and `settings` still describe the old tab (D-18).
- Open Low review items, not corrected: PPM-off tile hint and `/ppm` drill-down (L1), one unrecognised health value counted inconsistently between the state and the dimension chart (L2), UTC date for staleness (L3), "1 conflicts" grammar (L4), no loading cue on period change (L5), tile colour by worst state (L6), `0%` completeness on an empty population (L7), relabels EN/AR only (L8), Arabic digit systems (L9, D-27), selector label contrast (L10), parent and child initiatives both counted (L11).
- Tests not yet written: API tests for the PPM-off path, a hidden Initiative type and Overview / Executive total parity.

### Limitations and decisions

- **D-31 (open, blocking)**: the period half of the savings identity. Planned savings are deduplicated per application across all active / completed assessments, not per fiscal year.
- **D-18**: new strings are EN + AR only, as the approved fork language policy requires (CLAUDE.md's 10-locale rule does not apply to this fork); the other 8 locales fall back to English for new keys and keep their previous text for the four relabelled Overview keys.
- Currency: PPM lines and planned savings carry no currency of their own, so per-currency totals reduce to the instance currency. Should the instance setting change, existing amounts would be read in the new currency — that switch stays an administrative action after Finance verification (D-05).
- Quarter view of budget (CR-03) is not built; the Phase 2 period filter owns it.
- Initiative identity for health is the card; parent and child initiatives are each counted (no roll-up of health).

### Next (Phase 2)

Phase 2 is still blocked on D-03, D-04, D-07 and D-17. Once they are decided: the `services/executive/` package with one builder per KPI (moving these builders in unchanged), the Executive sub-navigation and CEO Overview (six measures), KPI history (`metric_snapshots`), org filter, quarter periods, and a per-KPI drill-down endpoint reusing the scoped populations above.

## Phase 2 implementation record (2026-10-25)

Implemented in the working tree on `main` (uncommitted, not deployed), on top of the uncommitted Phase 1 work. Scope: only the Phase 2 work not blocked by an open decision.

### Decisions applied (approved 2026-10-24, `DECISION_LOG.md` §2)

| Decision | How it is applied |
|---|---|
| D-03 | No role seeded. `reports.executive_dashboard` gates the three new routes and grants aggregates only: record lists need `risks.view`, `adr.view`, `arb.view`, `tech_standards.view`; drill-down rows need `ppm.view` (delivery) or `risks.view` (escalations); money still needs `costs.view` and rationalization detail `rationalization.view`. `kpis.measure` is not added yet (no measurement entry built). |
| D-04 | `services/executive/decisions.py`: open = not `closed` / `accepted`; escalated = open and residual (else initial) level `critical`, or `high` and overdue (target date passed, not `mitigated`); `strategic` category is not a signal; open, mitigated and escalated reported separately; no manual escalation. |
| D-07 | No organisation filter and no new relation type. |
| D-17 | Every tile carries `target` / `owner` blocks; both read **No linked KPI card** (`not_linked`, D-26). When linked, the contract already has an `unratified` state, and the card approval workflow is not treated as ratification. |

### What was built

| Item | Where |
|---|---|
| Routes `GET /reports/executive/overview?period=`, `GET /reports/executive/decisions`, `GET /reports/executive/kpi/{key}/drilldown?period=` (keys `TR-03`, `DEC-01`) | `api/v1/executive_overview.py`, registered in `router.py` |
| KPI contract + six named, versioned builders (`TR-01@0`, `GOV-05@0`, `TR-03@2`, `SVC-01@0`, `FIN-01@0`, `DEC-01@1`); confidence per KPI dictionary §1 | `services/executive/kpis.py` |
| Periods: `FY2027` / `FY2027-Q2`, as of the period's last day or today, previous period, selectable list (current FY + 3 prior, started quarters only) | `services/executive/periods.py`, `fiscal_year.fiscal_quarter_bounds` |
| Decisions: escalated risks, ADRs `in_review`, ARB `scheduled` / `deferred` (hidden subject omitted, D-30), exceptions `requested` (hidden card omitted, D-30) | `services/executive/decisions.py` |
| Previous-period delivery from dated reports | `ppm_portfolio_service.latest_reports(as_of=)` (default unchanged) |
| One initiative population for both executive endpoints; drill-down rows from the same classifier | `executive_dashboard.load_visible_initiatives`, `delivery_rows` |
| Executive sub-navigation (`?page=overview|decisions|details`); CEO overview (six tiles + "decisions needing attention" panel + period selector); decisions page; Phase 1 page moved to *Details* | `ExecutiveTab.tsx`, `ExecutiveOverview.tsx`, `ExecutiveKpiTile.tsx`, `ExecutiveDecisions.tsx`, `ExecutiveDetailsPage.tsx` (was `ExecutiveTab.tsx`) |
| EN + AR strings (84 keys each); user manual EN + AR; VERSION 2.35.0 + CHANGELOG; OpenAPI regenerated | `common.json`, `docs/guide/dashboard{,.ar}.md` |

### What each CEO indicator shows today

| Slot | KPI | Status |
|---|---|---|
| Strategy achievement | TR-01 | Not available — D-21 open (and no objective records progress) |
| EA governance effectiveness | GOV-05 / GOV-01 | Not available — Phase 3 (D-10, D-13) |
| Initiative delivery | TR-03 + coverage | Available for the current period, coverage shown beside it. A finished period and the previous-period comparison read *Historical data unavailable* (review correction H-1) |
| Services and automation | SVC-01 / SVC-02 | Not available — D-08, D-09 |
| Business value | FIN-01 | Not available — Phase 4; planned-savings forecast shown as a labelled detail only (D-31 open, currency unverified) |
| Decisions and escalations | DEC-01 + DEC-02 | Available as a labelled **current-state** figure whatever period is selected; the operational pipeline is counted beside it, not as escalations (H-2, H-3); no previous value until D-19 |

No target, baseline, benefit or maturity score is fabricated, and nothing is calculated from forecast savings.

### Validation

| Check | Result |
|---|---|
| `python -m ruff check` / `ruff format --check` on every changed backend file and test | Clean |
| `npx tsc -b --noEmit` | Clean |
| Route registration and static guards | The three routes are in the generated OpenAPI spec; the read-scope guard's markers are present in the new module; the bulk-export detector does not flag it |
| Tests | **None run (owner's instruction, 2026-10-25).** Written but not executed: `tests/services/test_executive_overview.py`, `tests/api/test_executive_overview_api.py`. No frontend test was written for the Phase 2 pages. `ExecutiveTab.test.tsx` was renamed `ExecutiveDetailsPage.test.tsx` with its imports updated; it has not been re-run. |

### Pending verification

- Running the two new backend test files and the renamed frontend test; Vitest for the overview, tile and decisions page.
- Browser check of the three pages in EN and AR (RTL) at phone and desktop widths.
- `mkdocs build --strict`; CI (diff coverage, mutation gates, OpenAPI drift).

### Remaining Phase 2 work (blocked)

- KPI history and frozen period values — D-19.
- Targets, baselines, owners and RAG on tiles — D-26, then a ratification mechanism (D-17).
- KPI measurement entry and `kpis.measure` — with the history storage (D-19).
- Organisation filter — D-07 relations and data, separately approved; D-20 suppression.
- TR-01 — D-21; SVC-02 — D-09.
- Summary sentence band and pillar strip (UI spec §4.1) — need TR-01 and pillar progress (D-21).
- Still open from Phase 1: D-31 and currency verification (D-05).

### Phase 2 review corrections (2026-10-25)

A focused review of the Overview and Decisions pages (browser, EN/AR, desktop and 390 px; API as admin and as a role holding only `reports.executive_dashboard`) found four High and seven Medium issues. The owner approved fixing **H-1 to H-4, M-1, M-3 and M-5**; the rest stay open (below). Applied in the working tree, **uncommitted**, no version bump.

| Finding | Correction | Where |
|---|---|---|
| **H-1** Past periods counted today's initiatives (population from current status; previous-period comparison likewise) | A period is *current* when it has not ended (`Period.is_current`). The in-flight population comes from each card's present status, which keeps no history, so TR-03 is computed **only for the current period**. A finished period, and every previous-period comparison, returns `historical_unavailable` — no value, no coverage, no drill-down rows. No lifecycle date or history event is used to rebuild membership: that would be a new rule (open, below). | `periods.py`, `kpis.initiative_delivery` (`TR-03@3`), `executive_overview.py` (`_current_delivery`, TR-03 drill-down) |
| **H-2** Current-state figures carried the selected period's label | Every tile carries `temporal`: `period` or `current_state`. DEC-01 is `current_state` with `period: null` and `as_of` today; the planned-savings forecast is tagged `current_state` (still not tied to a fiscal year, D-31 unchanged). The tile shows a **Current state** chip and "Current state · as of …" in the Period row; a finished period shows a notice above the tiles. | `kpis.py` (`DEC-01@2`, `FIN-01@1`), `ExecutiveKpiTile.tsx`, `ExecutiveOverview.tsx` |
| **H-3** Routine governance mixed with escalations | Each decisions section carries `group`: `executive_escalation` (risks, D-04) or `operational_pipeline` (ADRs awaiting signature, ARB scheduled / deferred, exceptions requested). The overview panel is now **Executive escalations** and lists escalated risks only (`escalations_panel`, replaces `decisions_panel`). The Decisions page renders the two groups separately. No new escalation rule. | `decisions.py`, `executive_overview.py` (`_panel`), `ExecutiveDecisions.tsx` |
| **H-4** Arabic counts fell back to English; mixed-direction text reordered | All six Arabic plural forms (zero, one, two, few, many, other) for every counted `dashboard.executive.*` string (25 keys, Phase 1 included); `_other` now holds the 100+ form. Record titles render with `dir="auto"`, meta fragments as `<bdi>` isolates, and in an RTL locale the currency part of compact money is a left-to-right isolate ("$US" no longer). EN/AR policy (D-18) unchanged. | `ar/common.json`, `en/common.json`, `ExecutiveOverview.tsx`, `executiveFormat.ts` |
| **M-1** "Nothing you can open needs attention" while escalations existed | The panel carries `status` and the full `count`; a restricted reader sees "N escalated risks" and why the records are withheld. "No risk meets the criteria" appears only when the count is zero. A restricted Decisions section with a zero count says "Nothing pending". | `executive_overview.py`, `ExecutiveOverview.tsx`, `ExecutiveDecisions.tsx` |
| **M-3** Headline health dominated low coverage | Coverage is a bold line under the value ("Reporting coverage 35.3%: 6 of 17 …"). A warning states the actual shortfall ("11 of 17 in-flight initiatives have no current status report; the on-track share covers only the 6 that reported") and, when no staleness threshold is configured, that any report counts as current, with the oldest counted report date. No fixed percentage threshold was introduced. | `ExecutiveOverview.tsx`, `kpis.py` (`oldest_report_date`) |
| **M-5** "View records" linked to pages the caller cannot open, or to a disabled module | `/rationalization`, `/arb`, `/tech-standards` added to `ROUTE_PERMISSIONS` (`rationalization.view`, `arb.view`, `tech_standards.view`), so links and typed URLs are gated like the backend. TR-03 offers no `/ppm` link when its source is the card status (PPM off) or the period has ended. Backend checks unchanged. | `routePermissions.ts`, `kpis.py` |

**Validation (one focused pass, 2026-10-25):**

| Check | Result |
|---|---|
| `ruff check` / `ruff format` on changed backend files and tests | Clean |
| `pytest tests/services/test_executive_overview.py tests/api/test_executive_overview_api.py tests/services/test_executive_dashboard_kpis.py tests/api/test_executive_dashboard_phase1.py` (local PostgreSQL) | **66 passed**, 0 failed, 0 skipped |
| `tsc -p tsconfig.json --noEmit` | 2 errors, both in untouched files (`lib/agGridSetup.ts`, `reports/MatrixReport.tsx`) from the AG Grid mismatch below; no error in any changed file |
| Vitest, normal config | **Cannot start locally**: every suite fails in `src/test/setup.ts` → `lib/agGridSetup.ts` because `node_modules` holds AG Grid **32.3.9** while `package-lock.json` pins **35.3.1** (stale install after the upstream merge; reproduced on the untouched `searchRank.test.ts`). Needs `npm ci`, which was out of scope. |
| Vitest, scratch config (outside the repo) stubbing only `@/lib/agGridSetup` | 7 files, 180 tests: **177 passed**. The 6 executive and i18n files pass, including the new `ExecutiveOverview.test.tsx`, `ExecutiveDecisions.test.tsx`, `executivePlurals.test.ts` and the RTL currency case. `routePermissions.test.ts` has **3 pre-existing parity failures** unrelated to this change (85 fork routes absent from `ROUTE_PERMISSIONS`, and `/ea-delivery/adm` naming an unknown `adm.view`); the three routes added here are no longer among the unreviewed ones. |
| Not run | Full suites, mutation testing, builds, `mkdocs build --strict`, a browser re-check of the corrected pages |

**Still open after the corrections:**

- M-6 (drill-down endpoints not used by the UI) and the Low findings L-1 to L-7. (M-2, M-4 and M-7 were done in the follow-up below.)
- Historical delivery membership: rebuilding which initiatives were in flight in a past period (from lifecycle dates or card-history events) is a **new business rule** and needs a decision; until then past periods show *Historical data unavailable*. KPI history storage (D-19) remains the general route to frozen period values.
- Local frontend environment: reinstall dependencies (`npm ci`) so Vitest runs under the normal config; then re-run the executive tests and the `routePermissions` parity test, and decide how to treat its 85 pre-existing unreviewed fork routes.
- No version bump or CHANGELOG entry was made for these corrections.

### Phase 2 UI corrections M-2, M-4, M-7 (2026-10-25)

Approved by the owner after the review corrections; frontend and user manual only — no API, business rule, permission or database change. Uncommitted, no version bump.

| Finding | Correction | Where |
|---|---|---|
| **M-2** Decision IDs ("Waiting for decision D-21"), phase numbers ("phase 3") and raw period keys ("FY2026-Q3") shown to executives | An unavailable tile now says what has to be agreed or confirmed, per indicator (e.g. strategy: "Shown once it is agreed how progress on strategic objectives is measured"; business value: "Shown once realised benefits are confirmed by Finance"). The payload keeps the decision IDs for the project records; the screen no longer cites them. Target and owner read "No approved target yet" / "Not assigned yet"; the footnote, the governance hint and the savings-period note were reworded the same way. Previous-period text uses the formatted period name. No `dashboard.executive.*` string in EN or AR now mentions a decision ID, a phase or "KPI card". | `executiveFormat.unavailableReason`, `ExecutiveKpiTile.tsx`, `en`/`ar` `common.json` |
| **M-4** No loading state on period change; period lost on reload and between pages | The period lives in the URL (`?tab=executive&page=…&period=FY2026-Q3`, `useExecutivePeriod`); a malformed value is ignored. Switching pages keeps it (`ExecutiveTab` already copies the query string; the Overview's link to Decisions and the Decisions tile's drill link carry it). Details follows the fiscal year of the chosen period and choosing a year there sets `period=FY<year>`. While a new period loads, both pages show a progress bar and **none** of the previous period's figures (the kept payload is used only for the selector's options). A period the Overview cannot show (e.g. a future budget year chosen on Details) gives a message and a **Show the current period** button instead of an error. Decisions remain current state, as before. | `useExecutivePeriod.ts`, `ExecutiveOverview.tsx`, `ExecutiveDetailsPage.tsx`, `ExecutiveKpiTile.tsx` |
| **M-7** Record titles truncated (losing the reference; cut at the wrong end in RTL); escalations a long scroll away on a phone | Titles wrap (`overflow-wrap: anywhere`, `dir="auto"`, start-aligned) instead of `noWrap`. Below the `lg` breakpoint the **Executive escalations** panel is placed first, above the six tiles (CSS `order`, which also holds in RTL), and no longer stretches to the tile column's height. | `ExecutiveOverview.tsx` |

**Validation (lightweight, 2026-10-25):**

| Check | Result |
|---|---|
| `tsc -p tsconfig.json --noEmit` | 2 errors, both pre-existing in untouched files (`lib/agGridSetup.ts`, `reports/MatrixReport.tsx`, AG Grid 32.3.9 installed vs 35.3.1 locked); none in changed files |
| `eslint src/features/dashboard/executive src/lib/routePermissions.ts` | Clean |
| Vitest, scratch config (outside the repo, stubs only `@/lib/agGridSetup`): the 6 executive files + `i18n.test.ts` | **6 files, 178 tests passed** — new cases for M-2 (plain-language reasons, no IDs or raw keys), M-4 (URL period requested, no stale figures while loading, selection written to the URL, way back from an unavailable period, period carried to Decisions, Details follows the period's fiscal year) and M-7 (titles wrap, `dir="auto"`) |
| **Normal frontend validation** | **Pending** — not possible until dependencies are reinstalled (`npm ci`, deferred by the owner) |
| Not run | Backend tests (no backend change in this round), full suites, mutation testing, builds, `mkdocs build --strict`, browser check at 390 px in AR |

**Remaining after this round:** M-6, L-1 to L-7, the historical-membership decision, `npm ci` and the normal-config frontend run, a browser check of the corrected pages (EN/AR, desktop and phone), and a version bump with CHANGELOG entry when these corrections are committed.

### KPI history, strategy achievement and KPI linkage (D-19, D-21, D-26, D-17a — 2026-10-25)

Approved with changes on 2026-10-25 (`DECISION_LOG.md` §2 and the implementation details I-1 to I-6 in §2.1). Implemented in the working tree, **uncommitted, not deployed, no version bump**. No demo measurements, targets or history were created.

**Batch 1 — data model, rules and API**

| Item | Where |
|---|---|
| One history `kpi_measurements` (daily observations + period measurements, append-only corrections, frozen verified closed periods) and `kpi_target_ratifications`; migration `1164` copies every `kpi_snapshots` row into four daily series and drops the old table (downgrade rebuilds it) | `models/kpi_measurement.py`, `alembic/versions/1164_kpi_measurement_history.py` |
| Dashboard trend and maturity indicator read the history; the daily loop also records the executive metrics and closes ended periods (last observation inside the period, `submitted`) | `services/kpi_snapshot_service.py`, `main.py`, `services/maturity_indicators.py` |
| Rules: record / correct (reason required) / verify (never one's own) / ratify; target unratified again when target, date, baseline, unit or direction change | `services/kpi_measurement_service.py` |
| Permissions `kpis.measure`, `kpis.verify`, `kpis.ratify_targets` (+ card permission `card.ratify_kpi_target` for an admin-defined approver stakeholder role); no default role or built-in stakeholder role holds them | `core/permissions.py` |
| `/kpis/{card}/performance`, `/kpis/{card}/measurements`, `/kpis/measurements/{id}/corrections`, `/kpis/measurements/{id}/verify`, `/kpis/{card}/target-ratifications`, `/kpis/metrics/{key}/history` | `api/v1/kpi_measurements.py` |
| `metricKey`: registry (`TR-03`, `DEC-01`), one validator on create, update, bulk create, bulk update, restore and workspace import; `admin.metamodel` to change; extensions refused; DB partial unique index | `services/kpi_metric_link.py`, `services/executive/registry.py`, `card_write_service.py`, `api/v1/cards.py`, `workspace_io/applier.py`, `models/card.py`, `nora_profile.py` (v11) |
| Workspace transfer: KPI-card measurements and ratifications travel; landscape-wide system series stay per instance | `workspace_io/sections.py` |

**Batch 2 — executive integration and UI**

| Item | Where |
|---|---|
| Tiles linked to their KPI card: target, ratification state, owner (`responsible` stakeholders), on/off target only for a ratified target with a direction; an unreadable card is "not linked" | `services/executive/linkage.py`, `executive_overview.py` |
| Previous period and finished periods of TR-03 from **verified** period measurements only (unrestricted readers); a submitted value says "awaiting verification" | `services/executive/kpis.py` |
| TR-01 strategy achievement: "X of Y measured on target" + coverage (measured of linked); objective and pillar rollups; per-KPI state and attainment; execution (supporting initiatives' delivery) apart; current period only; `Objective.progress` unused | `services/executive/strategy.py`, `GET /reports/executive/strategy` |
| Executive **Strategy** page; strategy tile; tile target/owner/KPI-card link | `ExecutiveStrategy.tsx`, `ExecutiveTab.tsx`, `ExecutiveOverview.tsx`, `ExecutiveKpiTile.tsx` |
| KPI card detail: **Performance and target** section (record, correct, verify, ratify, history) | `features/cards/sections/KpiPerformanceSection.tsx`, `CardDetailContent.tsx` |
| EN/AR strings (Arabic plural forms included) | `common.json`, `cards.json` |

**Validation**

| Check | Result |
|---|---|
| `ruff check` / `ruff format`; `import app.main` | Clean |
| One focused backend pass (batch 1, before the owner stopped further test runs): `test_kpi_measurement_service.py`, `test_kpi_measurements_api.py`, `test_kpi_snapshot_service.py`, `test_main_loops.py`, `test_reports.py::TestDashboard`, executive overview service + API, disclosure regression, permissions, read-scope guard, id-bearing guard, timestamp-default guard, NORA profile | **All new and updated tests passed.** Failures were pre-existing only: `reports.executive_dashboard` absent from three default role maps; 44 fork columns not in the id-bearing allowlist; four fork migrations (1154, 1155, 1157, 1159) without timestamp server defaults; the read-scope guard cannot read files on Windows (`charmap`); plus the NORA version assertion, since updated to 11 and not re-run |
| Batch 2 | **Pending verification — not run (owner's instruction).** New unit tests written in `test_executive_overview.py` (strategy tile, on-target rule, KPI states, linked tile, history-based previous and finished periods) |
| `tsc --noEmit` | Only the 2 pre-existing AG Grid errors; none in changed files |
| `eslint` on the executive pages and the KPI section | Clean |
| Frontend tests, normal config | Pending `npm ci` (unchanged) |
| Not run | Migration up/down on a real database, `docs/api/openapi.json` regeneration (routes added — CI drift check will flag it), browser check, full suites, mutation testing |

**Remaining limitations**

- No KPI, Pillar or Objective→KPI data exists on this instance: strategy achievement shows *Not available* until KPI cards are linked, targets ratified and measurements verified.
- Strategy achievement is current-period only: the strategic links keep no history (same rule as H-1).
- Executive metric history starts accumulating from deployment; nothing is backfilled. Period values for system metrics need a person with `kpis.verify` to verify them before they show as history.
- KPI card `currentValue` / `lastMeasuredDate` are not synchronised from the history (I-4).
- Monthly periods are not supported (I-1).
- An admin must create the "KPI target approver" stakeholder role (with `card.ratify_kpi_target`) or grant `kpis.ratify_targets`; none exists by default.
- ~~User manual pages for the KPI section and the Strategy page are not written yet.~~ Written 2026-10-25 (see below).

### Completion round (2026-10-25, branch `executive-kpi-history`)

Resumed from `b1689c29` on another machine. The implementation was checked against D-17a, D-19, D-21 and D-26; no business rule was added. Uncommitted, not deployed.

| Gap found | Correction | Where |
|---|---|---|
| A KPI card's `unit` is free text, but the measurement column was `String(32)` (and the ratification `String(64)`): a longer unit made recording or ratifying fail with a server error | Both `unit` columns are `Text`; migration `1164` changed before it has run anywhere | `models/kpi_measurement.py`, `alembic/versions/1164_kpi_measurement_history.py` |
| The KPI section offered **Verify** on the viewer's own measurement, which the server always refuses | The button is hidden for one's own row; `recorded_by` / `verified_by` added to the TypeScript type | `KpiPerformanceSection.tsx`, `types/index.ts` |
| No API test for `GET /reports/executive/strategy` | Three tests: permission, on-target counting from verified values and ratified targets, hidden KPI type left out | `tests/api/test_executive_overview_api.py` |
| No Vitest for the KPI section | `KpiPerformanceSection.test.tsx` | — |
| Two Vitest assertions still expected the pre-D-21 "not yet agreed" strategy wording | Updated to the approved wording | `executiveFormat.test.ts`, `ExecutiveOverview.test.tsx` |
| `kpi_metric_link` claimed every attribute write path calls it | Docstring names the two that do not (ServiceNow pull, platform-migration apply); the DB index alone guards them | `services/kpi_metric_link.py` |
| OpenAPI spec not regenerated | Regenerated | `docs/api/openapi.json` |
| User manual | Strategy page and *KPI cards: performance and target* written; Overview text updated (EN + AR) | `docs/guide/dashboard{,.ar}.md` |
| Version | 2.36.0 with CHANGELOG entry | `VERSION`, `CHANGELOG.md` |

**Validation (one focused pass)**

| Check | Result |
|---|---|
| Migration `1164` | Isolated copy (`CREATE DATABASE … TEMPLATE`) of the local upgraded database at rev `1163`: upgrade, downgrade, upgrade. Both `kpi_snapshots` rows became eight `dashboard.*` daily observations with their dates and capture times, and came back identical on downgrade; all indexes and `uq_cards_kpi_metric_key` created. Copy dropped afterwards; the source database was not touched and stays at `1163`. Not run against production |
| Backend | `ruff check` / `ruff format` clean. `test_kpi_measurement_service.py`, `test_kpi_measurements_api.py`, `test_kpi_snapshot_service.py`, `test_executive_overview.py` (batch 2), `test_executive_overview_api.py` (incl. the 3 new strategy tests), `test_main_loops.py`, `test_reports.py::TestDashboard`: **all pass**. `test_workspace_io_id_bearing_columns.py` fails only on the 44 pre-existing fork columns (the two new `unit` columns are allowlisted) |
| Frontend | Vitest `KpiPerformanceSection.test.tsx` + `features/dashboard/executive/`: 37/37 pass under the normal config. ESLint clean on the changed files; `tsc --noEmit` reported nothing |
| Not run | Full suites, mutation testing, builds, `mkdocs build --strict`, browser check, CI |

**Remaining**

- Browser check of the Strategy page and the KPI section (EN/AR, desktop and phone) — **Pending verification**.
- `mkdocs build --strict`, CI (diff coverage, mutation gates) — **Pending verification**.
- Pre-existing guard failures (id-bearing allowlist for 44 fork columns, `reports.executive_dashboard` in default role maps, fork migrations without timestamp defaults, the read-scope guard's Windows encoding) are unchanged.
- No KPI, Pillar or Objective→KPI data exists locally; strategy achievement correctly shows *Not available* until KPI cards are linked, targets ratified and measurements verified. No demo values were created.
- The other 8 locale manual pages still describe the earlier Executive tab (D-18).


### Merge-readiness round (2026-10-25, branch `executive-kpi-history`, on top of `0ce8920b`)

No business rule changed. Uncommitted, not merged, not deployed.

**Integration paths.** ServiceNow pull (`_apply_create` / `_apply_update`) and platform-migration apply (`_apply_single_card`, create and update) wrote card attributes directly, many cards in one transaction with no per-row savepoint: an invalid `metricKey` was accepted silently and a duplicate tripped `uq_cards_kpi_metric_key`, aborting the **whole** run. Both now call `kpi_metric_link.guard_inbound`, which reuses `validate_metric_key` (registered key, one ACTIVE card per key, `admin.metamodel` of the person who started the run; none for a system run). A refused link is reverted on its own — to the card's previous link, or dropped on a new card — the rest of the record lands, and the reason is written to the staged record's `error_message`. Archived cards are left as they are (restore checks them). `external_id`, identity maps, events and every other field behave as before. The check runs before the card is touched: the first version assigned the attributes first, and the guard's own lookup autoflushed the duplicate — the new test caught it.

**Security and data review.** `/kpis/*` reads and writes now also 404 for an admin-hidden (soft-deleted) KPI type, as I-5 requires; before, only a per-role View deny was enforced. Everything else matched the decisions and needed no change: `CardReadScope` on every KPI read (404, inventory mode); hidden types excluded from strategy and tile linkage; `kpis.measure` / `kpis.verify` / `kpis.ratify_targets` (or `card.ratify_kpi_target`) enforced server-side; no self-verification, a correction is a new submitted row the corrector cannot verify; any change to target, date, baseline, unit or direction makes the target unratified; corrections are append-only; landscape-wide history only for unrestricted executive readers; strategy rows carry ids, names and owner display names only.

**Browser review** (local Vite + backend on a disposable copy of the dev database, created with `CREATE DATABASE … TEMPLATE` and dropped afterwards; three throwaway local users; scenario data existed only in the copy, nothing was written to the real environment):

| Area | Result |
|---|---|
| Strategy, EN desktop | Empty state correct with no strategic objective. Populated: "0 of 1 on target", "1 of 3 strategic KPIs measured with verified data", state chips, pillar and objective roll-ups, execution apart ("Not available, 0 of 1 in-flight initiatives reported"); attainment 89.2 % = (88 − 55) ÷ (92 − 55) |
| KPI section, EN desktop | Record → *Awaiting verification*, no Verify on one's own row; Ratify → *Ratified*; second user verifies → *Verified*; correction with reason → new row awaiting verification, old row *Superseded*, corrector has no Verify; changing the target → *Not ratified*, `invalidated`, KPI leaves "measured" |
| Viewer (no `kpis.*`) | History visible, no Record / Verify / Correct / Ratify; server returns 403 for all three writes and for the Strategy endpoint |
| AR desktop and 390 px | RTL mirrored correctly; no horizontal page scroll at 390 px (EN and AR); tables scroll inside their card |

Defects found and fixed: (1) **Medium** — at 390 px the KPI name column collapsed to a few letters per line (`overflowWrap: anywhere`); now `minWidth: 160` and the table scrolls. (2) **Medium** — the target caption read "Not ratified by the owner" (EN) / "لم يعتمده المالك" (AR), contradicting D-17a (the approver ratifies, not the owner); now "Not ratified" / "غير معتمد". (3) **Low** — a KPI with no target date read "Target 92 % by —" and "Ratify a target of 92 % by —"; no-date variants added (EN/AR). (4) **Low** — the period key wrapped at its hyphen on a phone; the status column was too narrow for a correction reason.

**Validation (one focused pass, re-run once after the ServiceNow fix)**

| Check | Result |
|---|---|
| `ruff format --check`, `ruff check` | Clean |
| Backend: `test_kpi_metric_link_inbound.py` (new, 10 cases), `test_kpi_measurements_api.py` (+1 hidden-type test), `test_kpi_measurement_service.py`, `test_executive_overview_api.py`, `test_executive_overview.py`, `test_migration_apply_exact.py`, `test_servicenow_sync_engine.py`, `test_servicenow_archive.py` | 186 passed |
| Frontend: `KpiPerformanceSection.test.tsx`, `features/dashboard/executive/`, `i18n.test.ts` | 180 passed; ESLint clean; `tsc --noEmit` 0 errors |
| OpenAPI | Regenerated: no change (no contract change) |
| Alembic | Single head `1164`; branch contains `origin/main` (fast-forward) |
| Not run | Full suites, mutation testing, builds, `mkdocs build --strict`, CI |

**Pre-existing, unrelated (not in scope, unchanged):** 44 fork columns missing from the id-bearing allowlist; `reports.executive_dashboard` absent from three default role maps; fork migrations 1154, 1155, 1157, 1159 without timestamp server defaults; the read-scope guard cannot read files on Windows (`charmap`).


## Phase 3 — Batch 3.1: Governance page, activity, coverage, GOV-03 (2026-10-26, v2.37.0)

Implemented exactly to `PHASED_DELIVERY_PLAN.md` Batch 3.1 and the §3.1 rules. No new business rule: I-7..I-13 were verified against the approved decisions first and all operationalise them (ARB latest-decision-date dating, deferred apart; expired waiver = violation; coverage reported beside compliance; Not Available with reason for every unbuilt indicator). Uncommitted, not merged, not deployed. Batches 3.2-3.6 not started (D-37..D-42 open).

**Backend.** `tech_standards_scan.assess_standard_compliance` adds the assessed population (I-8), compliant/violating split (I-9) and the coverage denominator (I-10) beside the unchanged violation scan, same chain and same hidden-path cuts; Unavailable per I-11 (`no_governed_category` / `type_hidden` / `no_assessed_population`). New `services/executive/governance.py` builds Activity, Effectiveness and Impact apart. `GET /reports/executive/governance?period=` and the `GOV-03` drill-down (`tech_standards.view`) in `executive_overview.py`. `GOV-03` registered (`GOV-03@1`, percent); daily observation in `observe_executive_metrics` (recorded only when assessable, I-13, no backfill). NORA profile **v12** appends the GOV-03 option to `KPI.metricKey` (seed + idempotent injection pass). The overview governance tile now links to the page (I-7).

**Frontend.** `ExecutiveGovernance.tsx` (three labelled sections; GOV-03 via `ExecutiveKpiTile` showing its ratified target; coverage as a separate figure; drill-down list; Not Available tiles with plain reasons), `governance` page in `ExecutiveTab.tsx`, types in `src/types/index.ts`, EN + AR strings under `dashboard.executive.governancePage.*` (D-18). No DB/migration; no workspace-transfer change.

**Validation (one focused pass).**

| Check | Result |
|---|---|
| `ruff format --check`, `ruff check` (app + new tests) | Clean |
| Backend new/affected tests collect | 36 collected, no import/fixture errors (`test_tech_standards_scan.py` +3, `test_executive_governance.py` 8, `test_executive_governance_api.py` 5, `test_kpi_measurement_service.py` +2) |
| Backend tests run | **Pending Verification — NOT executed.** No PostgreSQL or Docker on this host, so the 36 backend tests were only collected, never run; they stay Pending Verification until they pass against PostgreSQL (CI: diff coverage + mutation gates). |
| Frontend `ExecutiveGovernance.test.tsx`, `i18n.test.ts`, `executivePlurals.test.ts` | 160 passed (scratch config stubbing the AG Grid setup import, per the Phase 2 note) |
| ESLint (touched files) | Clean |
| `tsc --noEmit` | Clean for the batch's files; two pre-existing unrelated errors remain (`agGridSetup.ts` AG Grid version mismatch; `MatrixReport.tsx`) |
| OpenAPI | Regenerated (`+49` lines: the new governance path; version-agnostic) |
| Not run | Full suites, mutation testing, builds, `mkdocs build --strict`, CI |

**Docs.** `docs/guide/dashboard.md` + `.ar.md`: Governance page described, five-page list, GOV-03 on the executive-metric list. Other 8 locales fall back to English (D-18). CHANGELOG `[2.37.0]`, VERSION `2.37.0`.


## Phase 3 — Batch 3.2 (unblocked part): transition history, GOV-07 elapsed (2026-10-26, v2.38.0)

Implemented on `main` (uncommitted, not merged, not deployed) to `PHASED_DELIVERY_PLAN.md` Batch 3.2, limited to what D-39 and D-40 do not block. Details settled within D-34 / D-35 are recorded as I-14..I-19 in `DECISION_LOG.md` for review; no new business rule. Batches 3.3-3.6 not started.

**Pre-check.** The 36 Batch 3.1 backend tests were **not** run: there is still no PostgreSQL or Docker on this host. They remain **Pending Verification**, and so do this batch's database tests.

**Backend.**
- New append-only table `governance_transitions` (model `models/governance_transition.py`, migration `1166`, server defaults on `occurred_at` / `created_at` / `updated_at`); created empty, nothing backfilled (I-14).
- `tech_standard_exceptions.decided_at`, nullable with no server default so earlier decisions stay undated (I-16).
- One writer, `services/governance_transitions.py`, called in the same transaction as each status change:
  - ADR: create (shared `adr_service.create_decision`), duplicate, revise, request signatures, sign (final signature, sharing the `signed_at` instant), recall, reject, PATCH status.
  - ARB: create and PATCH status. The `decided_at` / reviewer stamp rule is unchanged.
  - Exceptions: request and approve / reject.
  - A same-status save records nothing (I-15).
- Read endpoints, each gated by the instrument's own view permission and read scope (a hidden subject card is 404):
  - `GET /arb/{id}/transitions` (`arb.view`)
  - `GET /adr/{id}/transitions` (`adr.view`)
  - `GET /tech-standards/exceptions/{id}/transitions` (`tech_standards.view`)
  - The actor is returned as `{id, display_name}` only. The response says `recorded: false` when there is no history.
- Exception responses carry `decided_at`.
- `services/executive/governance.py`: GOV-07 **elapsed** calendar days per instrument (median and slowest, never pooled), with untimed decisions counted as *lifecycle not recorded* (I-17, I-18).
  - Processing time is Not Available (D-39) and working days are Not Available (D-38).
  - GOV-04 and the withdrawn / remediated lifecycle are Not Available, naming D-40.
- Workspace transfer: section `GovernanceTransitions` (actor remapped by email); `decided_at` travels by introspection. No `FORMAT_VERSION` change.
- No permission was added or changed.

**Frontend.** The Governance page gains a *Governance turnaround (elapsed)* card with one figure per instrument, the basis of each, the not-recorded count, and the two Not Available notes. The old blanket turnaround tile is removed. Types are in `src/types/index.ts`, and EN + AR strings are under `dashboard.executive.governancePage.turnaround.*` (D-18); the unused `reason.turnaround` key was removed. The exception-resolution reason and the current-state hint now name the pending lifecycle rules.

**Docs.** `docs/guide/dashboard.md` + `.ar.md` (turnaround, history from 2.38.0, Not Available cases); CHANGELOG `[2.38.0]`; VERSION `2.38.0`; OpenAPI regenerated (+125 lines: three history paths, `decided_at`); RTM P3-04..P3-06; DECISION_LOG I-14..I-19; PHASED_DELIVERY_PLAN Batch 3.2 status.

**Validation (one focused pass).**

| Check | Result |
|---|---|
| `ruff check`, `ruff format` (app + touched tests) | Clean |
| `python -c "import app.main"`; Alembic heads | Imports clean; single head `1166` |
| Backend run (no DB): `test_governance_transitions.py`, `test_executive_governance.py`, `test_alembic_timestamp_defaults.py`, `test_workspace_io_id_bearing_columns.py`, `test_adr_service.py`, `test_extension_adr_bridge.py` | **228 passed**, 43 skipped (database-backed) |
| Backend collected, **Pending Verification — not executed** (need PostgreSQL) | `test_governance_transitions_api.py` (11), the 7 new DB cases in `test_executive_governance.py`, `test_gov07_elapsed_ignores_a_hidden_cards_exception`, the workspace round-trip case, plus the 36 Batch 3.1 tests |
| Static guards `test_card_read_scope_guard.py`, `test_audit_log_guard.py` (`PYTHONUTF8=1`) | Read-scope guard passes. 3 audit-log guard failures, **identical on the unchanged tree** (fork routes in `settings.py`, `metamodel.py`, `migration.py`, `nea_evidence.py`, `reference_models.py` — none touched here); pre-existing, out of scope |
| Frontend `ExecutiveGovernance.test.tsx`, `executivePlurals.test.ts`, `i18n.test.ts` | **162 passed** (temporary config stubbing the AG Grid setup import, as before) |
| ESLint (touched files) | Clean |
| `tsc --noEmit` | No new errors; the two pre-existing ones remain (`agGridSetup.ts`, `MatrixReport.tsx`) |
| Not run | Full suites, mutation testing, builds, `mkdocs build --strict`, `npm ci`, CI |

**Open for approval (resolved later the same day).** D-39 and D-40 were approved with changes; see the next section.


## Phase 3 — Batch 3.2 completed after D-39 / D-40 (2026-10-26, v2.38.0)

D-39 and D-40 were approved with changes on 2026-10-26 and are recorded in `DECISION_LOG.md` §3.1 with the owner's wording, followed by I-20..I-28. The rest of Batch 3.2 is built on the same transition infrastructure; the elapsed-time figures, permissions and dashboard behaviour delivered earlier the same day are unchanged. Uncommitted, not merged, not deployed. Batch 3.3 and later not started.

**D-39 — governance-controlled processing time.**
- Migration `1167` adds `reason` and `delay_attribution` (`governance` / `requester` / `external`, checked) to `governance_transitions`. Existing rows stay NULL.
- The attribution is recorded on the move **into** a waiting state, by the person making it:
  - ARB `PATCH` to `deferred` (refused on any other status with 422 `delay_only_on_deferral`);
  - ADR create, recall and reject (each enters `draft`).
- `requester` and `external` need a reason (422 `delay_reason_required`). Nothing is defaulted.
- `processing_days` subtracts only requester / external intervals that carry a reason. The window runs from the creation transition to the first decision.
- A record is never timed when its history starts after creation, its chain is broken, or a draft / deferral interval has no attribution. Such records are counted by cause beside the figure.
- Exceptions have no waiting state (no `info_requested` was added), so a fully recorded exception's processing time equals its elapsed time.

**D-40 — exception remediation and withdrawal.**
- **States:** `remediation_submitted` (evidence required, `tech_standards.manage`) → `remediated` only through `POST …/remediation/verify` by a `tech_standards.approve_exception` holder who is neither the requester nor the submitter (403 `self_verification`). A verifier can instead return it to `approved` with a note.
- **Withdrawal:** `withdrawn` from requested or approved, with a reason, by the requester or a `tech_standards.manage` holder.
- **Expiry and waivers:** expiry stays derived and never resolves anything. A submitted, unverified remediation keeps its waiver until expiry; this rule is applied in the compliance scan, the radar counts, the NORA programme waiver counts, the NEA evidence pack and both report pages.
- **Columns (migration `1167`):** `status` widened to 32 characters, plus the remediation evidence, submitter / verifier and their times, and the withdrawal actor, time and reason. All nullable with no defaults, so no remediation or withdrawal is invented for the past.
- **Hard delete:** needs the new permission `tech_standards.delete_exception` (no default role; admins through the wildcard) and a `reason`. It writes an admin audit record (`admin.tech_standard_exception.deleted`) and a final `deleted` history row. `tech_standards.manage` no longer deletes exceptions.
- **Standard delete:** a standard whose exceptions left `requested` cannot be deleted (409 `exceptions_have_lifecycle`).
- **GOV-04:**
  - Eligible population: approvals recorded in the history whose expiry falls in the period and has passed, about readable cards.
  - Value: verified on or before expiry ÷ eligible.
  - Reported apart, never in the numerator: remediated late, awaiting verification, expired unresolved, withdrawn, rejected after approval.
  - Approvals that predate the history are counted as "not recorded"; requests rejected in the period are counted separately.

**API.** `POST /tech-standards/exceptions/{id}/remediation`, `…/remediation/verify` and `…/withdraw`; `DELETE …/exceptions/{id}?reason=`. Exception responses add the lifecycle fields and `past_expiry`. The history endpoints return `reason` and `delay_attribution`. OpenAPI was regenerated (+476 lines in total for Batch 3.2).

**Frontend.**
- New `ExceptionLifecycleActions` on the Technology Standards exception register: approve / reject, submit remediation, verify or return (disabled for the requester and the submitter), withdraw, and a permanent delete that needs a reason. The new states have their own chips.
- The Governance page:
  - Activity shows every exception state apart.
  - A GOV-04 card with all outcome buckets.
  - Governance-controlled time beside each elapsed figure, with untimed causes.
- `ExceptionWaiverMatrix` and `StandardsComplianceMatrix` treat remediated / withdrawn as closed, and a submitted remediation as still waived until expiry.
- EN + AR strings (`common`, `reports`, and `admin` for the audit label and context fields).

**Workspace transfer.** The three new user FKs on `StandardExceptions` are remapped by email. `remediation_evidence`, `withdrawal_reason` and `GovernanceTransitions.reason` are allowlisted as prose in the id-bearing guard. The round-trip test covers the new columns.

**Docs.** `docs/guide/dashboard.md` + `.ar.md` (GOV-04, governance-controlled time, exception lifecycle, delay attribution, deletion); CHANGELOG `[2.38.0]` extended (VERSION unchanged, same unreleased batch); DECISION_LOG D-39 / D-40 and I-20..I-28; RTM P3-04..P3-06; PHASED_DELIVERY_PLAN status.

**Validation (one focused pass).**

| Check | Result |
|---|---|
| `ruff check`, `ruff format` | Clean |
| App import; Alembic heads | Clean; single head `1167` |
| Backend run without DB (transition/lifecycle unit tests, governance pure tests, scan, timestamp-default guard, id-bearing guard, permission registry, ADR service, ADR bridge, read-scope guard) | **406 passed**, 60 skipped (database-backed) |
| Audit-log guard | 3 failures, **the same pre-existing set** (`settings.py`, `metamodel.py`, `migration.py`, `nea_evidence.py`, `reference_models.py`); none from this work |
| Backend collected, **Pending Verification — not executed** (no PostgreSQL) | `test_governance_transitions_api.py` (21), DB cases in `test_executive_governance.py` / `test_executive_governance_api.py` / `test_tech_standards_scan.py`, the workspace round-trip case, `test_tech_standards.py`, `test_arb.py`, `test_adr.py`, and the 36 Batch 3.1 tests |
| Frontend Vitest: `features/dashboard/executive/`, `features/tech-standards/`, `exceptionStatusReports.test.tsx`, `i18n.test.ts`, `SecurityLogTypes.test.ts` | **216 passed** (temporary config stubbing the AG Grid setup import) |
| ESLint (touched files) | No errors (pre-existing warnings in `ExceptionWaiverMatrix.tsx`) |
| `tsc --noEmit` | No new errors; the two pre-existing ones remain |
| Not run | Full suites, mutation testing, builds, `mkdocs build --strict`, `npm ci`, CI |

**Remaining unresolved business rules.**
- D-37 (Batch 3.6), D-38 (Batch 3.3), D-41 (Batch 3.4) and D-42 (Batch 3.5) stay open, as before.
- I-20..I-28 are implementation details within the approved D-39 / D-40 and are recorded for review, in particular:
  - the waiver staying active while a remediation awaits verification (I-23);
  - withdrawal allowed from requested or approved only (I-23);
  - the GOV-04 "due" test using today for "has passed" (I-26);
  - refusing to delete a standard with decided exceptions (I-28).
- No evidence format beyond text was introduced (no document attachment). If the owner wants documents as remediation evidence, that is a follow-up.
- Duplicate and revise create an ADR draft with no attribution, so such revisions stay untimed for processing time unless a later move records one.

## Phase 3 — Batch 3.2 refinement: the owner's six clarifications (2026-10-26, v2.38.1)

The completed Batch 3.2 was reviewed against the owner's six clarifications of 2026-10-26 and corrected where it fell short. D-39 and D-40 are unchanged; the details are recorded as I-29..I-34 in `DECISION_LOG.md`. Migration `1167` is untouched; one additive migration, `1168`, carries the two new columns. Uncommitted, not merged, not deployed.

| # | Clarification | Finding | Correction |
|---|---|---|---|
| 1 | Waiver stays applicable during remediation; expiry never extended | Already held (`WAIVER_ACTIVE_STATUSES`; no lifecycle step writes `expiry_date`) | None; confirmed by test (I-29) |
| 2 | Withdrawal after expiry, until terminal; never verified remediation | After expiry already allowed; `remediation_submitted` could not be withdrawn | `WITHDRAW_FROM` adds `remediation_submitted`; register UI offers it (I-30) |
| 3 | GOV-04 against the period and the original approved expiry | Outcome read from the **current** state, so later events rewrote completed periods; the deadline was the **current**, editable `expiry_date` | Approval transition stores `approved_expiry_date`; GOV-04 uses the first recorded approval, its approved expiry and the history up to the period's end; today is used only while the period runs (I-31) |
| 4 | Verification needs the violation resolved | Any independent verifier could verify on evidence text alone | `standard_usage_persists` (scan chain): 409 `violation_persists` while the usage remains; `attested` with a mandatory note where the pair cannot be assessed; basis stored (I-32) |
| 5 | Elapsed independent of processing time | Already held | None; DB-backed test added (I-34) |
| 6 | Hard deletion: admin-only, reason, audit; retained rows reveal nothing | Retained rows kept evidence / reasons, and the `deleted` row held the deletion reason | Deletion clears `reason` on the record's transitions; the `deleted` row has none; reason in the audit record only (I-33) |

**Code.** `services/governance_transitions.py` (withdraw states, approved expiry on approval, verification check, async `record_deletion` with redaction); `services/tech_standards_scan.py` (`standard_usage_persists`); `api/v1/tech_standards.py` (verify runs the check; delete uses the cleaned reason; `remediation_verification_basis` in responses); `services/executive/governance.py` (`original_approval`, period-bounded `classify_resolution`, `exception_resolution`); models + migration `1168`; `ExceptionLifecycleActions.tsx` (Verify opens a dialog with an optional note; withdraw from awaiting verification); EN/AR strings (4 keys).

**Workspace transfer.** Both new columns are plain scalars on covered sections (`GovernanceTransitions`, `StandardExceptions`) and transfer with no change; no id-bearing column added.

**Docs.** `docs/guide/dashboard.md` + `.ar.md`; CHANGELOG `[2.38.1]`; VERSION `2.38.1`; OpenAPI regenerated (route descriptions only); DECISION_LOG I-29..I-34; RTM P3-04..P3-06.

**Validation (one focused pass).** PostgreSQL turned out to be reachable on this host, so the database-backed tests of the changed areas were executed rather than left Pending Verification.

| Check | Result |
|---|---|
| `ruff check`, `ruff format --check` (backend) | Clean |
| Alembic heads | Single head `1168` |
| Backend: `test_governance_transitions.py`, `test_executive_governance.py`, `test_tech_standards_scan.py`, `test_executive_governance_api.py`, `test_governance_transitions_api.py`, `test_tech_standards.py`, `test_workspace_io_roundtrip.py`, id-bearing and timestamp-default guards | **392 passed, 9 failed** — all 9 pre-existing and reproduced on the committed HEAD: 5 ADR cases (`POST /adr` passes `committee` / `meeting_date` / `stage_no` that `adr_service.create_decision` does not accept, since the v2.29.0 upstream merge) and 4 card-type-category round-trip cases |
| Two stale Batch 3.1/3.2 assertions fixed | GOV-03 drill-down (Billing now holds an active waiver, so it is correctly not a violation); processing time is a per-instrument figure, not one Not Available block |
| Frontend Vitest: `ExceptionLifecycleActions`, `exceptionStatusReports`, `ExecutiveGovernance` | **30 passed** |
| `tsc --noEmit`, ESLint (touched files) | No errors |
| `check_locales.py report` | 0 fatal gaps |
| Not run | Full suites, mutation testing, builds, `mkdocs build --strict`, `npm ci`, CI |

**Rules added for approval** (each reported in its I-row): withdrawal from `remediation_submitted` (I-30); "original approved expiry" = the first recorded approval after a rejection and re-approval, and approvals recorded under 2.38.0 counted as *lifecycle not recorded* (I-31); the `attested` verification path for pairs the scan cannot assess, and the check being on usage rather than the standard's later radar status (I-32); clearing earlier rows' free text on hard deletion (I-33).

**Remaining blocking issues.**
- ~~`POST /adr` fails with a `TypeError` for every request~~ — **fixed the same day**: `adr_service.create_decision` now takes `committee`, `meeting_date` and `stage_no` (pre-existing since the v2.29.0 merge, outside Batch 3.2). Regression tests in `test_adr.py` / `test_adr_service.py` fail before the fix; the ADR suites and the 5 ADR transition-history cases now pass (170 tests).
- Structured references to existing card documents or attachments as remediation evidence are not built (I-32); evidence text can cite them as links.

## Phase 3 — Batch 3.2: owner rulings on I-30..I-33 (2026-10-26, v2.38.1)

The owner ruled on the four rules the refinement added: **I-30 approved**; **I-31, I-32 and I-33 approved with changes**. The implementation was reviewed against the rulings and corrected only where needed. The ADR `POST /adr` fix is accepted as implemented and unchanged. Migrations `1166`..`1168` are unchanged; one additive migration, `1169`, adds the evidence references. Uncommitted, not merged, not deployed. Batch 3.3 not started.

| Rule | Ruling | Finding | Correction |
|---|---|---|---|
| I-30 Withdrawal during verification | Approved; mandatory reason and audit record | Already held: reason required (422), and each withdrawal writes an append-only transition row with actor, time and reason | None |
| I-31 Approval cycles | Approved with changes: each distinct cycle keeps its approved expiry; GOV-04 uses the applicable cycle and its period | Each approval already stored its expiry, but GOV-04 always used the **first** approval | `approval_cycles` splits the history at each approval decision; GOV-04 uses the latest cycle due in the period, that cycle's transitions and its own approved expiry; a cycle without a recorded expiry is never given one |
| I-32 Verification evidence | Approved with changes: a note alone is insufficient where the scan cannot assess | A note was enough for `attested` | The submission cites the card's existing documents / file attachments (`remediation_evidence_refs`, migration `1169`); an unassessable verification needs at least one still on the card **and** the note (422 `verifiable_evidence_required`); references to another card are refused; register dialog lists the card's documents and files to cite |
| I-33 Immutable, confidential history | Approved with changes: never rewrite or erase history; restrict sensitive text in ordinary responses; document retention | Hard deletion cleared earlier rows' reasons | Redaction removed: deletion only appends; free-text reasons in the exception history, and evidence / withdrawal text in exception lists, only for the requester and holders of `manage` / `approve_exception` (`reason_withheld`, `lifecycle_text_withheld`); retention documented in I-33 |

**Code.** `services/executive/governance.py` (`approval_cycles`, applicable cycle); `services/governance_transitions.py` (`resolve_evidence_refs`, `live_evidence_refs`, evidence requirement in `verify_remediation`, `record_deletion` append-only, `may_read_lifecycle_text`, `transition_history(withhold_reason=)`); `api/v1/tech_standards.py` (evidence refs on submission, live evidence count on verification, text gating on lists and history); model + migration `1169`; `ExceptionLifecycleActions.tsx` (cite card documents / files); EN/AR strings (5 new keys, verify hint updated).

**Workspace transfer.** `remediation_evidence_refs` holds document / file-attachment ids, which an import preserves (module rows keep their primary keys), so it is allowlisted as `MODULE_IDS` in the id-bearing guard; no remap needed.

**Validation (one focused pass).**

| Check | Result |
|---|---|
| `ruff check`, `ruff format --check` (backend) | Clean |
| Alembic heads | Single head `1169` |
| Backend against PostgreSQL: `test_governance_transitions.py`, `test_executive_governance.py`, `test_tech_standards_scan.py`, `test_governance_transitions_api.py`, `test_executive_governance_api.py`, `test_tech_standards.py`, `test_adr.py`, `test_adr_service.py`, id-bearing and timestamp-default guards | **434 passed, 0 failed** |
| Frontend Vitest: `ExceptionLifecycleActions`, `exceptionStatusReports`, `ExecutiveGovernance` | **32 passed** |
| `tsc --noEmit`, ESLint (touched files) | No errors |
| `check_locales.py report`; OpenAPI | 0 fatal gaps; regenerated |
| Not run | Full suites, mutation testing, builds, `mkdocs build --strict`, `npm ci`, the workspace round-trip suite (4 pre-existing category failures, unrelated) |

**Interpretations to confirm** (within the rulings, no new business rule beyond them):
- The applicable cycle for a period is the **latest** cycle whose approved expiry fell due in it; an exception counts once per period (I-31).
- An exception with no card cannot cite card evidence, so an unassessable remediation of it cannot be verified (I-32).
- The confidentiality rule covers the exception's free text (evidence, evidence references, return notes, withdrawal reasons); ADR and ARB delay reasons in their history endpoints are unchanged (I-33).
- The withdrawal's audit record is its transition row; withdrawal does not write to the admin security log, which records administrative actions such as the hard delete (I-30).

**Remaining issues.**
- 4 workspace-transfer round-trip tests for card-type categories fail on the committed HEAD too; unrelated to Batch 3.2.
- No new blocking issue in the changed functionality.

## Phase 3 — Batch 3.2: decisions A–D (2026-10-26, v2.38.1)

The owner approved decisions A–D from the focused review with clarifications; they are recorded as I-35..I-37 in `DECISION_LOG.md`. The completed ADR creation fix and the earlier Batch 3.2 changes are preserved; migrations `1166`..`1169` are unchanged and one additive migration, `1170`, was needed. Uncommitted, not merged, not deployed. Batch 3.3 not started.

| Decision | Built |
|---|---|
| **A** GOV-04 approval cycles | Primary figure and distribution stay **unique exceptions** (`unit_of_count: "exceptions"`, outcomes sum to `eligible`); a separate `approval_cycles` breakdown classifies every due cycle, earlier rejected ones included, in cycles; the Governance page labels both and says cycle counts are never added to exception counts. |
| **B** Expiry changes | `change_expiry`: on an approved / awaiting-verification exception a changed expiry needs a reason and appends an `expiry_changed` event (previous expiry, new expiry, actor, time, reason; status unchanged). GOV-04 uses each cycle's expiry **in force by the period's end** (`effective_expiry`). Expiry events are excluded from GOV-07 decisions. |
| **C** Evidence integrity | Cited files fingerprinted by content (SHA-256 + size), documents by their link; re-checked at verification (409 `evidence_changed`); at least one unchanged file required where the scan cannot assess (422 `evidence_integrity_unavailable`); explicit verifier attestation — examined / demonstrates / confirmed (422 `attestation_required`) — kept with the confirmed fingerprints in `remediation_attestation`. No file is copied; older evidence is not refused. The verify dialog collects the attestation. |
| **D** Delay-reason confidentiality | ADR history: reason text for `adr.manage`, creator, signatories; ARB history: for `arb.manage`, creator, assigned reviewer; others get attribution, times and `reason_withheld`. |

**Migration `1170`.** Adds `governance_transitions.event_kind` (checked: NULL or `expiry_changed`) and `previous_expiry_date`, and `tech_standard_exceptions.remediation_attestation` (JSONB). All nullable, no server defaults, nothing backfilled. Downgrade refuses while expiry-change events exist. Existing rows stay status transitions (`event_kind` NULL).

**Workspace transfer.** The new scalar columns transfer with no change. `remediation_attestation` holds prose and document / file ids (module PKs preserved on import) and is allowlisted as `MODULE_IDS`; it deliberately stores no user id (the verifier is the remapped `remediation_verified_by` column).

**Docs.** `docs/guide/dashboard.md` + `.ar.md`; CHANGELOG `[2.38.1]`; OpenAPI regenerated; DECISION_LOG I-35..I-37; RTM P3-04..P3-06.

**Validation (one focused pass).**

| Check | Result |
|---|---|
| `ruff check`, `ruff format --check` (backend) | Clean |
| Alembic heads | Single head `1170` |
| Backend against PostgreSQL: `test_governance_transitions.py`, `test_executive_governance.py`, `test_tech_standards_scan.py`, `test_governance_transitions_api.py`, `test_executive_governance_api.py`, `test_tech_standards.py`, `test_adr.py`, `test_arb.py`, `test_adr_service.py`, id-bearing and timestamp-default guards | **468 passed, 0 failed** |
| Frontend Vitest: `ExceptionLifecycleActions`, `exceptionStatusReports`, `ExecutiveGovernance` | **33 passed** |
| `tsc --noEmit`, ESLint (touched files) | No errors |
| `check_locales.py report`; OpenAPI | 0 fatal gaps; regenerated |
| Not run | Full suites, mutation testing, builds, `mkdocs build --strict`, `npm ci`, the workspace round-trip suite |

**Limitations reported (not blockers).**
- A document is a link: its target cannot be fingerprinted, so links alone can never establish integrity for an unassessable remediation (at least one file is required).
- No screen edits an exception's expiry; the change is API-only, as before, and now needs a reason when the exception is approved.
- The ARB "assigned reviewer" is `reviewer_id`, which is stamped when the review is decided or deferred; there is no separate pre-assignment field.

**Remaining blockers.** None in the changed functionality. The 4 card-type-category workspace round-trip failures remain pre-existing and unrelated.

## Phase 3 — Batch 3.2 closed (2026-10-26, v2.38.1)

Batch 3.2 is closed at v2.38.1 and committed to `main`. Scope is frozen: nothing below is in progress.

**Completed**
- Governance transition history for ADR, ARB and exceptions (migrations `1166`..`1170`), append-only, with delay attribution (D-39) and expiry-change events (I-35).
- GOV-07 elapsed time and governance-controlled processing time per instrument (I-17, I-18, I-20..I-22, I-34).
- GOV-04 exception resolution over unique exceptions, with the period cut, each cycle's expiry in force and a separate approval-cycle breakdown (I-26, I-31, I-35).
- Exception lifecycle: remediation submission, independent verification (scan check, or fingerprinted file evidence plus verifier attestation where the scan cannot assess), return, withdrawal from any non-terminal state, audited admin-only hard delete (I-23..I-33, I-36).
- Confidentiality: exception lifecycle text and ADR / ARB delay reasons restricted to the people who act on the record (I-33, I-37).
- `POST /adr` creation fix (committee / meeting date / stage fields), with regression tests.
- Final focused validation: 468 backend tests (PostgreSQL) and 33 frontend tests passed; lint, types and locale parity clean.

**Explicitly deferred (not part of Batch 3.2)**
- Integrity of linked documents' targets (only files can be fingerprinted; links alone cannot back an unassessable verification).
- A screen to edit an exception's expiry date (API only), and screens to record or view ADR / ARB delay attribution and history (API only).
- A separate ARB reviewer-assignment field (the "assigned reviewer" is the recorded decider).
- Delay attribution on ADR duplicate / revise (such revisions stay untimed for processing time).
- Working-day figures (D-38, Batch 3.3) and the other open decisions D-37, D-41, D-42 (Batches 3.4–3.6).
- Not run before commit: full suites, mutation testing, builds, `mkdocs build --strict`, the workspace round-trip suite (its 4 card-type-category failures are pre-existing and unrelated). There is no CI on this fork.

## Phase 3 — Batch 3.3: business calendar and GOV-07 working days (2026-10-27, v2.39.0)

D-38 was approved on 2026-10-27 (the EA Governance Office owns the calendar; authorized administrators maintain official Saudi holidays by fiscal year; a period is valid only when all its fiscal-year calendars are confirmed; otherwise working-day GOV-07 is Not Available). Recorded in `DECISION_LOG.md` with details I-38..I-41. **Committed on `main`** as `481f1238` ("Executive dashboard Phase 3 Batch 3.3: business calendar, GOV-07 working days (v2.39.0)"); not deployed. *(Corrected 2026-10-27: this section originally said uncommitted.)*

**Backend.**
- `models/business_calendar.py` + migration `1171`: `business_calendar_years` (fiscal year, working week, holidays, confirmation, confirming user / time). Additive; no row created.
- `services/business_calendar.py`: validation (fiscal year, working week, holidays inside the year), `apply_edit` (a change to a confirmed year withdraws the confirmation), `BusinessCalendar.working_days` (half-open count on each day's own fiscal-year calendar; `None` when any spanned year is unconfirmed), `load_calendar`, `serialize`.
- `api/v1/business_calendar.py`: `GET /business-calendar`, `PUT /business-calendar/{fy}`, `POST …/{fy}/confirm`, `POST …/{fy}/unconfirm`; new permission `admin.business_calendar` (no default role); admin audit records `admin.business_calendar.created` / `updated` / `confirmed` / `unconfirmed`.
- `services/executive/governance.py`: `working_days_block` / `working_days_figure` — GOV-07 elapsed working days per instrument over the same decisions; Not Available (`calendar_not_confirmed`, with the years) unless every fiscal year of the period is confirmed; spans into unconfirmed years counted by cause.
- Workspace transfer: config section `BusinessCalendar` (natural key `fiscal_year`; `confirmed_by` and `confirmed_at` not carried).

**Frontend.** `BusinessCalendarSection.tsx` in Settings → General (shown to `admin.business_calendar` holders): fiscal year, working days, holidays, save, confirm / withdraw. Governance page: working-day figures under each instrument, or the unconfirmed years named. EN/AR strings (admin, common, security-log labels).

**Docs.** `docs/admin/settings.md` + `.ar.md` (business calendar), `docs/guide/dashboard.md` + `.ar.md` (working days), CHANGELOG `[2.39.0]`, VERSION `2.39.0`, DECISION_LOG D-38 + I-38..I-41, PHASED_DELIVERY_PLAN status, RTM P3-07.

**Validation: Pending Verification.** As instructed, no tests, builds, type checks or browser checks were run. Only `ruff check` / `ruff format`, the app import and the Alembic head (`1171`) were checked. Tests written and not executed: `tests/services/test_business_calendar.py`, `tests/api/test_business_calendar_api.py`, the GOV-07 working-day cases in `tests/services/test_executive_governance.py`, `test_business_calendar_roundtrip` in `tests/services/test_workspace_io_roundtrip.py`, `BusinessCalendarSection.test.tsx`, and two cases in `ExecutiveGovernance.test.tsx`. OpenAPI regenerated (`scripts/dump_openapi.py`).

**Rules added for approval.** A change to a confirmed year withdraws its confirmation (I-38); the half-open working-day count and UTC dating (I-39).

**Deferred.** Governance-controlled processing time in working days (stays calendar days, I-41); importing a holiday file (option (b) of D-38, not chosen).

## Phase 3 — Batch 3.4: decision actions, implementation verification, GOV-05 (2026-10-27, v2.40.0)

D-41 was approved **with changes** on 2026-10-27 (verifier independence from execution, signatories allowed when independent; credible evidence per action without a file requirement or fingerprinting; original and revised deadlines with reasons and history; decisions without linked cards verifiable through directly associated evidence; GOV-05 with the excluded population and planning coverage disclosed). Recorded in `DECISION_LOG.md` with details I-42..I-49. Implemented on `main`, **uncommitted**, not deployed. Batches 3.5 and 3.6 not started.

**Backend.**
- Migration `1172`: `todos.source_kind` / `source_id` (+ index), `completion_note`, `evidence_refs`, `completed_by`, `completed_at`; new table `decision_implementations` (deadline in force, original deadline and its basis, `open` / `submitted` / `verified`, submitter, verifier, attestation); `governance_transitions` gains instruments `adr_impl` / `arb_impl`, event kinds `due_date_set` / `due_date_changed`, and `due_date` / `previous_due_date`. Everything nullable without defaults on existing tables; downgrade refuses while records exist.
- `services/decision_implementation.py`: the one definition of decision actions, evidence checks, submission, independent verification, deadlines and the GOV-05 classification (`outcome_at`, `due_in_force`).
- `api/v1/decision_actions.py`: under `/adr/{id}` and `/arb/{id}` — `GET …/implementation`, `POST …/actions`, `PATCH` / `DELETE …/actions/{id}`, `POST …/actions/{id}/complete` / `reopen`, `POST …/implementation/submit` / `verify`, `PUT …/implementation/due-date`. New permission `governance.verify_implementation` (no default role).
- ADR signing approves a proposed deadline; the ARB approve request takes `implementation_due_date`; deleting a draft ADR or an ARB review removes its actions and implementation record (history rows kept).
- Generic todo routes and the extension todos bridge refuse to change or delete a decision action (409), except the bridge's mirror fields; the todo list returns `source_kind` / `source_id`.
- `services/executive/governance.py`: `decision_implementation` (GOV-05) replaces the Not Available placeholder; `kpis.governance_effectiveness` builds the overview tile `GOV-05@1` from it.
- Workspace transfer: new section `DecisionImplementations` (user FKs by email); `completed_by` added to the Todos section; `evidence_refs`, `completion_note`, `submission_note` and `attestation` allowlisted (module ids or prose — no card id is stored in the evidence).

**Frontend.** `features/decision-implementation/DecisionImplementationPanel.tsx` on the ADR preview and in the ARB review dialog (deadline with original and revisions, actions, complete-with-evidence, submit, verify / return, history); the ARB *Approve* button asks for the optional implementation deadline; the Governance page shows a GOV-05 card (rate, outcomes, revised deadlines, decisions without a deadline, planning coverage). Types in `src/types/index.ts`; EN/AR strings (`delivery`, `reports`, `common`).

**Docs.** `docs/guide/delivery.md` + `.ar.md` (*Implementing a decision*), `docs/guide/dashboard.md` + `.ar.md` (GOV-05; governance no longer listed as Not Available), CHANGELOG `[2.40.0]`, VERSION `2.40.0`, DECISION_LOG D-41 + I-42..I-49, PHASED_DELIVERY_PLAN status, RTM P3-08 / P3-09 / FR-12, GOVERNANCE_MEASUREMENT_MODEL §3.3 and §6 amended, `D41_DECISION_AND_BATCH_3_4_INSTRUCTIONS.md` marked superseded. OpenAPI regenerated.

**Validation: Pending Verification.** As instructed, no tests, builds, type checks or browser checks were run. Only `ruff check` / `ruff format`, the app import, the Alembic head (`1172`), ESLint on the changed frontend files and the OpenAPI dump were run. Tests written and not executed: `tests/services/test_decision_implementation.py`, `tests/api/test_decision_actions_api.py` (including the end-to-end acceptance flow and the self-verification refusal), `test_decision_implementation_and_actions_roundtrip` in `tests/services/test_workspace_io_roundtrip.py`, the GOV-05 tile cases in `tests/services/test_executive_overview.py`, the updated case in `tests/services/test_executive_governance.py`, `DecisionImplementationPanel.test.tsx`, and three GOV-05 cases in `ExecutiveGovernance.test.tsx`.

**Rules added for review.** The "authorized governance owner" who revises a deadline is the decision's manage-permission holder (`adr.manage` / `arb.manage`) (I-46); an approved deadline cannot be removed, only revised (I-46); any change to an action after submission returns the implementation to `open` (I-44).

**Not built.** No new attachment target on ADR / ARB records — a system reference is the evidence for a decision with no linked card (I-49).

### Batch 3.4 completion (2026-10-27, v2.40.0)

The owner approved the four rules added for review and asked for GOV-05 to join the KPI infrastructure, without widening the batch.

- **Rules (I-44, I-45, I-46).** Deadline revisions by `adr.manage` / `arb.manage` with a reason and history, and no removal of an approved deadline — as built. Decision authors may verify when independent — as built. **Changed:** only a *material* change (action added, reopened or deleted; owner or due date changed) returns a submitted implementation to In progress and is refused once verified; rewording a description is cosmetic and accepted in every state (`decision_implementation.is_material_change`).
- **GOV-05 in the KPI infrastructure (I-50).** Registered in `services/executive/registry.py` (`GOV-05@1`) with `PERIOD_CALCULATED`; `KPI.metricKey` option (NORA profile v13, pass 4h now adds GOV-03 and GOV-05 when missing); `kpi_measurement_service.observe_executive_metrics` records the current quarter's GOV-05 when a decision is due; `close_ended_periods` records GOV-05's closed-period value calculated for that period, only for periods the capture ran in. Overview tile: KPI-card target and owner (`linkage.apply_link`) and the previous period's verified value. Governance page: `decision_implementation_tile` rendered with `ExecutiveKpiTile`, the breakdown and coverage beneath it. The calculation, the original-deadline rule and the planning-coverage disclosure are unchanged.
- **Strings.** EN/AR: the GOV-05 tile description and the overview slot hint (it described GOV-05 as complete follow-up actions, which D-32 rules out).
- **Correction.** Batch 3.3 is committed on `main` (`481f1238`); the progress report, plan and RTM now say so.
- **Pre-existing test fixed.** `test_nora_profile.py` still asserted profile v11 after v12 shipped in Batch 3.1; it now asserts v13.

**Validation: Pending Verification.** No tests or builds run; `ruff`, the app import and ESLint on the changed frontend files only. Tests written and not executed: the GOV-05 capture and period-close cases in `test_kpi_measurement_service.py`, the option pass in `test_nora_profile.py`, the previous-period case in `test_executive_overview.py`, the material / cosmetic cases in `test_decision_implementation.py`, and the GOV-05 tile cases in `ExecutiveGovernance.test.tsx`.

## Phase 3 — Batch 3.5: architecture risk indicators (2026-10-27, v2.41.0)

D-42 was approved on 2026-10-27 (explicit risk ↔ governance-record links; architecture-related only through a link; `risks.manage` plus record visibility; audited link, unlink and deletion; no leaks through names, counts or drill-downs; current-state indicators; RSK-01 in the KPI infrastructure; verified reduction Not Available). Recorded in `DECISION_LOG.md` with details I-51..I-56. Implemented on `main`, **uncommitted**, not deployed. Batch 3.6 not started.

**Backend.**
- Migration `1173` / `models/risk_governance_link.py`: `risk_governance_links` (risk FK with cascade, instrument, record id without FK, linker, time; unique per risk and record). Existing `risk_cards` untouched.
- `services/risk_governance.py`: record description and visibility (ADR `adr.view`; ARB `arb.view` + readable subject card; exception `tech_standards.view` + readable card), link / unlink one at a time with `risk.governance_linked` / `risk.governance_unlinked` events, removal on record deletion (`reason: record_deleted`), the figures (each risk once; D-04 open / escalated / mitigated; overlapping breakdowns marked non-additive; reduction Not Available) and the drill-down rows (records the reader cannot open counted, never named).
- `api/v1/risk_governance.py`: `GET/POST /risks/{id}/governance-links`, `DELETE /risks/{id}/governance-links/{instrument}/{record_id}`, `GET /adr/{id}/risks`, `GET /arb/{id}/risks`. ADR draft delete, ARB delete, exception hard delete and standard delete remove the record's links.
- Executive: Governance page Impact section carries `architecture_risks` and the `architecture_risk_tile` (RSK-01, current state, KPI-card link, previous period's verified value); `GET /reports/executive/kpi/RSK-01/drilldown` under `risks.view`; RSK-01 registered (`RSK-01@1`) with daily capture when a link exists; `KPI.metricKey` option via NORA profile v14. The CEO Overview is unchanged.
- Workspace transfer: section `RiskGovernanceLinks` (linker by email; risk and record ids are module PKs kept on import).

**Frontend.** `GovernanceRecordsSection` on the risk detail page (list, add by record type, remove); `LinkedRisksList` on the ADR preview and in the ARB review dialog; the Governance page Impact section shows RSK-01 as a KPI tile with a visible current-state label, the breakdown, a Verified risk-reduction Not Available tile and the drill-down for `risks.view` holders. EN/AR strings (`common`, `grc`).

**Docs.** `docs/guide/risks.md` + `.ar.md` (*Linking risks to governance records*), `docs/guide/dashboard.md` + `.ar.md` (RSK-01), CHANGELOG `[2.41.0]`, VERSION `2.41.0`, DECISION_LOG D-42 + I-51..I-56, PHASED_DELIVERY_PLAN status, RTM P3-10, OpenAPI regenerated.

**Validation: Pending Verification.** No tests or builds run. Only `ruff check` / `ruff format`, the app import, the Alembic head (`1173`), ESLint on the changed frontend files and the OpenAPI dump. Tests written and not executed: `tests/api/test_risk_governance_api.py`, the RSK-01 cases in `test_kpi_measurement_service.py` and `test_executive_overview.py`, `test_risk_governance_links_roundtrip`, the v14 cases in `test_nora_profile.py`, `GovernanceRecordsSection.test.tsx` (with `LinkedRisksList`) and the RSK-01 cases in `ExecutiveGovernance.test.tsx`.

**Limitations.** Figures are current state: links and risk statuses keep no history, so a past period shows only its verified RSK-01 measurement (from the day capture starts; nothing backfilled). The record picker on the risk page lists the records the user may see with no search beyond the list's own filter. Link events carry no card, so they appear in the audit/event log rather than on card history timelines.
