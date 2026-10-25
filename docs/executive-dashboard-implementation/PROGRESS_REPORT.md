# Progress report

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
