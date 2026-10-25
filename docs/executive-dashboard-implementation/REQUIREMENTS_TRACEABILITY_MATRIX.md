# Requirements traceability matrix

Each requirement (`EXECUTIVE_BUSINESS_REQUIREMENTS.md`) is traced to its design, KPIs, phase, decisions, verification and the source assessment finding. Verification describes the test that will prove it in CI. **Nothing has run in CI.** Rows marked *implemented* name the local focused tests that ran (SEC track, and Phase 1 on 2026-10-24).

## Business objectives → pages and KPIs

| BO | Page(s) | KPIs | Phase |
|---|---|---|---|
| BO-1 | Overview, Transformation | TR-01..06, FIN-09 | 2, 5 |
| BO-2 | Governance | GOV-01..08 | 3 |
| BO-3 | Governance, Impact | GOV-05, GOV-06, GOV-09, IMP-01, IMP-04, IMP-07 | 3, 4 |
| BO-4 | Services & Automation, Transformation | SVC-01..06, TR-05, TR-06 | 5 |
| BO-5 | Impact, Portfolio Health | IMP-01..03, IMP-06, IMP-08, PRT-02/03 | 4, 5 |
| BO-6 | Financial & ROI | FIN-01..10 | 4 |
| BO-7 | Decisions, Overview | DEC-01..05 | 2, 3, 5 |

## Requirements

| Req | Design reference | KPIs | Phase | Decisions | Verification (CI) | Source finding |
|---|---|---|---|---|---|---|
| FR-01 | UI_UX_SPECIFICATION §1, §4 | — | 2 (+ 3-5 pages) | C-01 | Vitest: sub-nav renders permitted pages; e2e smoke. **Phase 2: implemented 2026-10-25, no tests run, uncommitted.** Sub-navigation with Overview, Decisions, Details (`ExecutiveTab.tsx`); later-phase pages not listed until built. Vitest not written | Assessment RECOMMENDED_DASHBOARD_STRUCTURE §1 |
| FR-02 | API_AND_BACKEND §2; DATA_MODEL §4.2 | all | 2 | D-07, C-16 | API: org filter narrows denominators; hidden org → 404. **Blocked:** D-07 approved OrganizationalUnit but the filter is not built until relations and data exist (no new relation types without separate approval) | UI_UX_REVIEW §4 |
| FR-03 | API §2; KPI dictionary §1 | all | 2 | D-06 | API: period changes values; FY naming. **Phase 2: implemented 2026-10-25, no tests run, uncommitted.** `period=FY2027` / `FY2027-Q2` on the overview and drill-down; as of the period end; 422 on a malformed or future period. Unit + API tests written, not run | KPI_INVENTORY §4 |
| FR-04 | API §4 drilldown | all | 2 | — | API: drill-down rows = KPI numerator under the same scope. **Phase 2: implemented 2026-10-25, no tests run, uncommitted.** `/reports/executive/kpi/{key}/drilldown` for TR-03 (rows from the same classifier as the count; `ppm.view`) and DEC-01 (`risks.view`). Tests written, not run | UI_UX_REVIEW §1 |
| FR-05 | UI_UX §5 | — | 2-6 | C-11, D-18 (approved: EN/AR only), D-27 | i18n parity for EN / AR (`i18n.test.ts`); Phase 6 RTL visual QA sign-off | UI_UX_REVIEW §1 |
| FR-06 | UI_UX §4.1; KPI dictionary §3.1 | 6 landing | 2 | C-11 | Vitest: exactly 6 tiles + decisions panel. **Phase 2: implemented 2026-10-25, no tests run, uncommitted.** Six tiles + decisions panel; four are Not available with reasons (D-21, Phase 3, D-08/D-09, Phase 4). Pillar strip and summary band not built (D-21) | EXISTING_DASHBOARD §3 |
| FR-07 | UI_UX §3; API §3 | all | 2 | D-17, D-19 | Vitest: tile renders target / delta / as-of; API returns them. **Phase 2: implemented 2026-10-25, no tests run, uncommitted.** Tile renders value, target, previous, period, freshness, owner, confidence, provenance, drill-down. Target and owner read *No linked KPI card* (D-26); history-based delta blocked (D-19) | KPI_INVENTORY §4 |
| FR-08 | KPI dictionary §1; UI_UX §3 | all | 1-2 | C-04 | Builder tests: missing → `not_available` / `not_reported`, never 0. **Phase 1: implemented 2026-10-24, not in CI, uncommitted.** `not_available` status (realised savings), `null` headline when nobody reported, Restricted for money; every headline tile carries a provenance chip (Recorded / Self-reported / Forecast / Restricted / Not available) | KPI_INVENTORY K14 |
| FR-09 | DATA_MODEL §3.1 | all | 2 | C-02, D-26 | API: target / owner read from the KPI card. **Blocked:** D-17 approved KPI cards as the target source; matching a computed KPI to its card needs D-26 (open), and ratification needs a mechanism other than card approval | DATA_AND_FUNCTIONAL_GAP G1 |
| FR-10 | DATA_MODEL §3.2, §3.2b | all | 2 | D-19 | Snapshot freeze test; measurement CRUD + event test. **Blocked:** D-19 (snapshot storage) open | TECHNICAL_READINESS §3 |
| FR-11 | GOVERNANCE_MEASUREMENT_MODEL | GOV-01..09 | 3 | D-10, D-11, D-28 | GOV builder tests; class labels | EA_GOVERNANCE_AND_ROI_MODEL §3.1 |
| FR-12 | DATA_MODEL §3.3; API §4 | GOV-05, GOV-06 | 3 | D-13 | API: actions on ADR / ARB; GOV-05 end-to-end | GAP G3 |
| FR-13 | BENEFITS_AND_ROI §1-3, §7 | FIN-01..04, FIN-10 | 4 | C-06, D-12, D-29 | API: transitions require evidence; segregation of duties | GAP G2 |
| FR-14 | BENEFITS_AND_ROI §6 | FIN-08 | 4 | C-07, C-08, D-14, D-15 | Builder: ROI Not available unless all inputs are confirmed | EA_GOVERNANCE_AND_ROI_MODEL §5 |
| FR-15 | DATA_MODEL §4.1 | SVC-01 | 5 | C-10, D-08 | Builder: four buckets incl. Not assessed | — |
| FR-16 | KPI dictionary §3.6 | SVC-02 | 2, 5 | C-10, D-09 | Builder: missing value → Unknown | KPI_INVENTORY K19 |
| FR-17 | UI_UX §4.8 | DEC-01..05 | 2, 3, 5 | D-04 | API: list omits unreadable items; sort. **Phase 2: implemented 2026-10-25, no tests run, uncommitted.** Decisions page: escalated risks (D-04 rule), ADRs awaiting signatures, ARB pending, exceptions requested; counts scoped, records gated per module; hidden-card records omitted (D-30). API test written, not run | EXISTING_DASHBOARD §3 |
| FR-18 | UI_UX §2; API §7 | — | 6 | — | Export parity + audit test | TECHNICAL_READINESS §7 |
| FR-19 | BENEFITS_AND_ROI §1, §6 | FIN-10 | 4 | C-09 | Builder: productivity excluded from FIN-01 / FIN-08 | — |
| FR-20 | API §4 traceability; BENEFITS_AND_ROI §2 | — | 3 (v1), 4 | — | API: chain for a fixture decision | EA_GOVERNANCE_AND_ROI_MODEL §2 |
| CR-01 / 02 | KPI dictionary §2 | TR-03, TR-04 | 1 | C-12, D-02 (approved) | Builder + API: Not Reported is never On Track or At Risk; coverage separate; staleness only when configured. **Phase 1: implemented 2026-10-24, not in CI, uncommitted.** `summarize_delivery_health` / `report_state`; setting `initiativeReportStalenessDays` (no default; `GET`/`PATCH /settings/initiative-report-staleness`, admin, audited). Tests: `test_executive_dashboard_kpis.py` (10 delivery cases), `test_executive_dashboard_phase1.py::test_delivery_is_four_states_with_coverage_separate`, `ExecutiveTab.test.tsx`. Pass | KPI_INVENTORY K14 |
| CR-03 | KPI dictionary §2 | FIN-07 | 1 | D-06 (approved) | Builder: out-of-FY lines excluded. **Phase 1: implemented 2026-10-24, not in CI, uncommitted.** `load_fiscal_money` + `fiscal_year_bounds`; `?fiscal_year=` on `/reports/executive`; undated cost lines counted, never summed. Tests: FY bounds for all 12 start months, `test_budget_is_one_fiscal_year_in_the_named_currency`, `test_fiscal_year_follows_the_start_month_setting`. Pass. Quarter view not built (Phase 2 period filter) | K18 |
| CR-04 | KPI dictionary §2 | FIN-03 | 1 | D-24 (approved), D-31 (open) | Builder: agreeing duplicates counted once; conflicts flagged and excluded from totals. **Phase 1: implemented 2026-10-24, not in CI, uncommitted.** Identity = application (`card_id`); conflicts listed with every candidate and excluded; payload `period: {status: blocked, decision: D-31}`. **Period half blocked on D-31**: the figure is not bound to a fiscal year and the UI says so. Conflict detail (names, assessments, estimates, range) needs `rationalization.view` as well as `costs.view`; without it only `conflict_count` is returned (review H1, see SR-16). Tests: 6 builder cases + `test_planned_savings_conflicts_are_excluded` (incl. a costs-only role). Pass | K16 |
| CR-05 | KPI dictionary §2 | money KPIs | 1 | C-13, D-05 (approved) | API currency field; no cross-currency totals; no stored amount altered; Vitest formatter EN / AR. **Phase 1: implemented 2026-10-24, not in CI, uncommitted.** Every money block carries `currency` (the instance setting: PPM lines and planned savings carry no currency of their own); `formatCompactMoney` formats in the payload currency with the SAR glyph override; no conversion, no write to any amount, no change to the currency setting. Tests: `executiveFormat.test.ts`, API asserts `currency`. Pass. AR rendering checked by unit only (Pending Verification: visual). **Open: Finance verification that the instance currency setting is the currency the stored amounts were entered in (D-05)** — until then every label is unverified; the manual states the rule | — |
| CR-06 | KPI dictionary §2; SECURITY WI-11 | totals | SEC-3 + 1 | D-01 (approved) | API parity across four tabs. **SEC-3 part implemented:** `/reports/dashboard` and KPI snapshots exclude hidden types (`test_dashboard_counts_exclude_hidden_cards_and_hidden_types`, `test_kpi_snapshot_counts_exclude_hidden_types`). **Phase 1: implemented 2026-10-24, not in CI, uncommitted.** Executive aggregates apply `CardReadScope` (module) + `visible_type_clause` in every card query and on the initiative population before counting (`test_executive_applies_scope_hidden_types_and_cost_rules`, pass). Cross-tab parity test not written (Pending Verification) | K01 / K10, EXISTING_DASHBOARD §6.1 |
| CR-07 | KPI dictionary §2 | PRT-04, GOV-03 | 1 | — | Vitest: no "approved" tile on executive pages. **Phase 1: implemented 2026-10-24, not in CI, uncommitted.** Approved % removed from payload and headline; approval mix shown only as "Repository review status" in the collapsed specialist section. GOV-03 is Phase 3. Test: `ExecutiveTab.test.tsx` (terminology). Pass | K12 |
| CR-08 | KPI dictionary §2 | PRT-01 | 1 | — | i18n key review; Vitest label. **Phase 1: implemented 2026-10-24, not in CI, uncommitted.** "Data completeness" / «اكتمال البيانات» on Executive (`data_completeness`) and on Overview / Admin / attention band (EN + AR). Same card-weighted value as Overview; the type-weighted variant belongs to the Phase 5 Portfolio Health page. Other locales keep their previous text (D-18) | K02 / K11 |
| CR-09 | KPI dictionary §2 | PRT-02, PRT-03 | 1 | — | Vitest labels; separate drill-downs. **Phase 1: implemented 2026-10-24, not in CI, uncommitted.** Lifecycle wording is "Past planned end-of-life" (Executive donut + Overview attention band, EN + AR) and drills to the lifecycle report. The vendor-support measure (PRT-03) is Phase 5 | K07 |
| CR-10 | KPI dictionary §2 | SVC-05 | 1 | — | No headline uses documentation coverage. **Phase 1: implemented 2026-10-24, not in CI, uncommitted.** Headline tile removed; shown as a secondary line "Process documentation coverage … not automation or maturity" in the Processes section (`documentation_coverage`) | K13 |
| SR-01 | SECURITY §3 WI-1..11, WI-15 | — | SEC | C-05, D-01, D-30 (approved) | Extended sentinel sweep green; guard green. **SEC: implemented 2026-10-24, verified locally, not yet in CI:** sweep and guard pass; the sweep fails on 24 routes at `HEAD` (SECURITY §8.1) | GAP G13; S-18 / S-19 |
| SR-02 | SECURITY §4 | — | SEC + 2 | D-01 | Totals = Σ visible breakdowns test; drill-down parity. **SEC part:** Σ test on `/reports/dashboard` passes; drill-down parity remains for Phase 2 | EXISTING_DASHBOARD §6.1 |
| SR-03 | SECURITY WI-5, WI-6, WI-15 | money | SEC | D-05 | API: no money without `costs.view` (incl. strategy-map). **SEC: implemented 2026-10-24, verified locally, not yet in CI:** strategy-map, Gantt, rationalization, scenarios, card exports tested; **S-08 decided and implemented 2026-10-24** (PPM dashboard, cost / budget lines, Gantt rollups; `test_disclosure_phase1_prep.py`, pass) | TECHNICAL_READINESS §4; S-18 |
| SR-04 | SECURITY §4 | — | 2 | D-20 | API: n < 3 → suppressed | TECHNICAL_READINESS §4 |
| SR-05 | SECURITY §4; API §7 | — | 6 | — | Export audit entry exists; parity | — |
| SR-06 | BENEFITS_AND_ROI §7 | — | 4 | D-03, D-29 | API: validate / confirm permission tests | — |
| SR-07 | SECURITY WI-12, WI-14 | — | 1-6 | — | Restricted-reader matrix per endpoint. **Phase 1 prerequisite:** the executive endpoint must adopt S-08, D-01 hidden types and `opportunity_access` (SECURITY §9.3 item 5). **Phase 1: implemented 2026-10-24, not in CI, uncommitted.** S-08 + D-01 kept (FY money read only with `costs.view`; restricted response carries the period, no amounts). Still no opportunity figure, so `opportunity_access` is not yet needed | — |
| SR-08 | PHASED_DELIVERY SEC track exit | — | SEC | C-05 | SEC exit checklist. **Pending verification:** targeted tests pass locally; full backend suite not run; CI run, merge and PR security review outstanding (SECURITY §8) | — |
| SR-09 | SECURITY §6 (R1-R7) | — | SEC-1 | — | Regression suite fails before the fixes and passes after. **SEC: implemented 2026-10-24, verified locally, not yet in CI:** `test_disclosure_regression.py` fails 15 / 16 at `HEAD`, passes 17 / 17 after; R2 / R3 partly covered (SECURITY §8.4) | S-16, S-17, S-18, S-19 |
| NFR-01 | API §8 | — | 2-6 | — | Benchmark p95 at 50k cards (Phase 6) | TECHNICAL_READINESS §6 |
| NFR-02 | DATA_MODEL §3.2 | — | 2 | — | Frozen-period test | TECHNICAL_READINESS §3 |
| NFR-03 | API §7 | — | 2, 4 | — | Event + audit-log tests | TECHNICAL_READINESS §5 |
| NFR-04 | UI_UX §6 | — | 6 | — | Accessibility checks + manual review | UI_UX_REVIEW §1 |
| NFR-05 | UI_UX §7 | — | 2-6 | — | Visual review at listed widths | UI_UX_REVIEW §1 |
| NFR-06 | API §5 | — | 2-5 | C-03 | Code review: no formula engine | TECHNICAL_READINESS §2 |
| NFR-07 | PHASED_DELIVERY (all) | — | all | C-14 | CI gates | CLAUDE.md |

## Security additions (2026-10-24)

| Req | Design reference | Phase | Decisions | Verification | State |
|---|---|---|---|---|---|
| SR-10 PPM money needs `costs.view` | SECURITY §9, §10 | SEC | S-08 (approved 2026-10-24) | 3 API tests pass; UI renders "Restricted" (tsc + ESLint clean; 2 Vitest cases written, blocked by the AG Grid mismatch) | Implemented; frontend runtime and CI pending |
| SR-11 Opportunities counted only when independently accessible | SECURITY §9 | SEC | S-12 (approved 2026-10-24), D-30 | API test over list, realized value, NORA dashboard, update 404 | Implemented; focused test passes; CI pending |
| SR-12 Scenario merge never modifies hidden or unauthorized cards | SECURITY §9, §10 | SEC | D-01, D-30 | 4 API tests (hidden withheld, forbidden skipped, partial merge stays open and is completed later, relation change + `relations.manage`) | Implemented; tests pass; migration `1162` not yet run on an upgraded DB |
| SR-13 Segment membership never derived through hidden cards | SECURITY §9 | SEC | D-01 | 2 API tests (hidden root, hidden intermediate) | Implemented; focused tests pass; CI pending |
| SR-14 Executive endpoint applies the module rules before aggregation | SECURITY §10 | SEC → Phase 1 | D-01, S-07, S-08, S-12 | API test (scope, hidden types, total = Σ breakdown, money restricted) | Implemented; test passes; CI pending |
| SR-15 OpenAPI reflects nullable PPM amounts | SECURITY §10 | SEC | — | Regenerated; structural diff reviewed | Done; CI drift check pending |
| SR-16 Executive savings conflict detail follows the rationalization permission | Phase 1 review H1 | 1 | D-30, SR-07 | Unit (`test_conflict_detail_needs_rationalization_view`), API (`finance` role: count only, no names or amounts), Vitest (count-only notice) | Implemented 2026-10-24; focused tests pass; uncommitted; CI pending |


## Phase 1 additions (2026-10-24)

| Req | Design reference | Phase | Decisions | Verification | State |
|---|---|---|---|---|---|
| P1-01 Reporting period and freshness shown | UI_UX §3 | 1 | D-06 | Vitest: FY label, period select refetches with `?fiscal_year=` | Implemented; test passes; CI pending |
| P1-02 Staleness threshold configurable, no default | KPI dictionary CR-01 | 1 | D-02 | API: admin-only GET/PATCH, 403 for non-admin, 422 for 0, clearable to `null`; audit row (`report_staleness_days`) | Implemented; test passes; CI pending |
| P1-03 Forecast and realised savings kept apart | KPI dictionary CR-04; C-06 | 1 | D-24 | Builder: `realized_savings = not_available`, planned savings `provenance = forecast` | Implemented; test passes; CI pending |
| P1-04 Savings financial period | KPI dictionary CR-04 | 1 | **D-31 (open)** | — | **Blocked**: no period field or rule invented. Interim presentation (application-only total) awaits business confirmation |
| P1-05 User documentation reflects the corrected tab | CLAUDE.md docs rule | 1 | D-18 | `docs/guide/dashboard.{md,ar.md}`, `docs/admin/settings.{md,ar.md}` rewritten; endpoint docstring corrected | Done (review M1); `mkdocs build --strict` not run; other 8 locale pages unchanged (D-18) |
| P1-06 Release record | CLAUDE.md changelog rule | 1 | — | `VERSION` 2.34.0, `CHANGELOG.md` `[2.34.0]` entry | Done (review M2); uncommitted |
| P1-07 Currency verification | KPI dictionary CR-05 | 1 | **D-05** | Finance confirms the instance currency setting against the stored amounts | **Open** (review M3): an administrative / Finance check, not a code change |

## Phase 2 additions (2026-10-25)

| Req | Design reference | Phase | Decisions | Verification | State |
|---|---|---|---|---|---|
| P2-01 Executive permission grants aggregates only | D-03 | 2 | D-03 | API test: counts visible, records `restricted` without module permission; drill-down 403 without `ppm.view` / `risks.view` | Implemented; test written, not run |
| P2-02 Escalation rule; open, mitigated, escalated separate | D-04 | 2 | D-04 | 6 unit cases (critical, residual wins, high overdue / mitigated, closed, strategic not a signal, separate counts) | Implemented; tests written, not run |
| P2-03 Previous period without a history table | KPI dictionary §1 | 2 | D-19 (open) | Unit `test_previous_delivery_is_never_recounted_over_todays_population`; API `test_previous_period_is_never_recounted_over_todays_initiatives` | **Revised by review correction H-1 (2026-10-25):** the previous-period delivery value is `historical_unavailable` — the in-flight population has no history, so it is no longer recomputed from today's cards. Pass (local) |
| P2-04 No fabricated targets or values | D-17, C-04 | 2 | D-17, D-26 | Unit: every tile `target.status = not_linked`; blocked KPIs `not_available`, value `null` | Implemented; tests written, not run |
| P2-05 Org filter | UI spec §2 | 2 | D-07 | — | **Blocked** until relations and data exist |

## Phase 2 review corrections (2026-10-25)

Approved by the owner on 2026-10-25 (findings H-1–H-4, M-1, M-3, M-5 of the Phase 2 review). Uncommitted. Results are from one focused local pass (`PROGRESS_REPORT.md`, *Phase 2 review corrections*). "Pass (scratch)" = Vitest run under a scratch config that stubs only the AG Grid setup import, because local `node_modules` (AG Grid 32.3.9) does not match the lockfile (35.3.1).

| Req | Finding | Decisions | Verification | State |
|---|---|---|---|---|
| P2-06 Historical KPIs use only dated evidence for the selected period | H-1 | C-04, D-19 (open) | Unit `test_current_and_finished_periods`, `test_finished_period_delivery_is_historical_unavailable_not_a_value`; API `test_finished_period_shows_historical_unavailable_and_current_state_apart`, `test_finished_period_drilldown_lists_no_rows`; Vitest `ExecutiveOverview.test.tsx` (historical case) | Implemented. Backend pass; frontend pass (scratch). Rebuilding past membership from lifecycle dates or history events needs a decision — not done |
| P2-07 Period-based vs current-state figures | H-2 | D-31 (unchanged) | Unit `test_decisions_tile_is_current_state_whatever_period_is_selected`, `test_business_value_never_uses_the_forecast_as_value`; API (same as P2-06); Vitest current-state chip and Period row | Implemented. Backend pass; frontend pass (scratch) |
| P2-08 CEO panel holds executive escalations only; operational pipeline separate | H-3 | D-04 | API `test_attention_panel_holds_escalations_only`; unit `test_decision_section_lists_records_only_with_permission` (group); Vitest `ExecutiveDecisions.test.tsx` | Implemented, no new escalation rule. Backend pass; frontend pass (scratch) |
| P2-09 Complete Arabic plurals; no English fallback; RTL order | H-4 | D-18 | Vitest `executivePlurals.test.ts` (all six forms for every counted executive key; counts 0, 1, 2, 4, 11, 100 resolve in Arabic), `executiveFormat.test.ts` (currency isolate in `ar` only), `i18n.test.ts` | Implemented. Pass (scratch). Browser re-check not done |
| P2-10 Restricted state instead of an empty panel | M-1 | D-03 | API `test_decisions_counts_for_everyone_records_only_with_module_permission` (`escalations_panel` restricted with count); Vitest restricted and zero-count cases | Implemented. Backend pass; frontend pass (scratch) |
| P2-11 Coverage beside delivery health; neutral warnings | M-3 | D-02 | Vitest coverage headline, shortfall and unset-threshold warnings, and no warning at full coverage with a threshold | Implemented, no fixed threshold. Pass (scratch) |
| P2-12 Drill-down links only with module permission; none to a disabled module | M-5 | D-03 | Vitest drill-down permission case; unit `test_delivery_from_card_status_offers_no_ppm_link`; `routePermissions.ts` entries | Implemented. Pass (scratch); `routePermissions.test.ts` keeps 3 pre-existing parity failures unrelated to this change |
| P2-13 Executive-friendly explanations; no decision IDs, phases or raw period keys on screen | M-2 | C-04, D-17 | `executiveFormat.test.ts` (`unavailableReason`); `ExecutiveOverview.test.tsx` (M-2 case: plain wording, six "No approved target yet", no `D-n`, no `FY…-Q…`) | Implemented. Pass (scratch) |
| P2-14 Period in the URL, shared across Executive pages; loading state without stale figures | M-4 | D-06 | `ExecutiveOverview.test.tsx` (M-4 cases); `ExecutiveDetailsPage.test.tsx` (FY switch hides kept figures; follows the period's FY) | Implemented. Pass (scratch). Normal-config run pending `npm ci` |
| P2-15 Titles wrap; escalations first on mobile, RTL included | M-7 | C-11 | `ExecutiveOverview.test.tsx` (M-7 case: no `noWrap`, `dir="auto"`); panel order is CSS (`order: {xs: -1, lg: 0}`) | Implemented. Pass (scratch); placement not browser-checked at 390 px |

## KPI history, strategy achievement and linkage (2026-10-25)

| Req | Decision | Verification | State |
|---|---|---|---|
| P2-16 One KPI measurement history replacing `kpi_snapshots`, data preserved | D-19, I-1 | Migration `1164` (copy + drop + downgrade); `test_kpi_snapshot_service.py`, `test_reports.py::TestDashboard` trend cases, `test_main_loops.py` | Implemented; tests passed. Migration not run against a real database |
| P2-17 Daily observations vs verified period measurements; period value = last observation in the period | D-19, I-2 | `test_period_value_is_the_last_observation_inside_the_period`, `test_daily_observation_is_one_row_per_metric_per_day` | Implemented; passed |
| P2-18 Append-only audited corrections; frozen verified closed periods | D-19 | `test_correction_is_append_only_audited_and_needs_reverification`, `test_open_period_value_is_not_frozen`, `test_measurement_events_reach_the_card_history`, API correction test | Implemented; passed |
| P2-19 `kpis.measure` / `kpis.verify`; no self-verification | D-19, I-3 | `test_nobody_verifies_their_own_measurement`, `test_verify_needs_kpis_verify_and_another_person`, `test_record_needs_kpis_measure` | Implemented; passed |
| P2-20 Visibility: card history follows `CardReadScope`; landscape history only for unrestricted readers | D-19, I-5, D-01 | `test_hidden_kpi_type_does_not_exist_for_the_reader`, `test_metric_history_is_withheld_from_a_restricted_reader` | Implemented; passed |
| P2-21 Target ratification by an authorized approver; invalidated on change | D-17a | `test_target_states_and_invalidation_on_change`, `test_ratification_needs_the_approver_authority_not_the_owner_role` | Implemented; passed |
| P2-22 `metricKey`: registered, unique (validator + DB index), `admin.metamodel`, all write paths | D-26 | `test_metric_key_must_be_registered_unique_and_authorized`, `test_metric_key_uniqueness_is_enforced_by_the_database`, `test_restoring_a_card_whose_key_is_taken_is_refused`, PATCH / bulk-create / bulk-update API tests | Implemented; passed. Workspace-import path not covered by a test |
| P2-23 Tiles show linked target, owner, ratification; judged only when ratified | D-26, D-17a | `test_linked_tile_shows_target_owner_and_judges_only_when_ratified`, `test_assess_needs_a_ratified_target_and_a_direction` | Implemented; **Pending verification** (written, not run) |
| P2-24 Previous / finished periods from verified history only | D-19 | `test_previous_and_finished_period_come_only_from_verified_history` | Implemented; **Pending verification** |
| P2-25 Strategy achievement: X of Y + coverage, objective/pillar drill-down, execution apart, no weights, no `Objective.progress` | D-21 | `test_strategy_tile_counts_on_target_among_measured_with_coverage`, `test_strategy_tile_is_never_zero_without_evidence`, `test_kpi_state_follows_the_evidence_order` | Implemented; **Pending verification**. No API test for `/reports/executive/strategy` yet |
| P2-26 KPI card performance UI; Strategy page | D-19, D-21 | `tsc` + `eslint` clean | Implemented; **Pending verification** (no Vitest written; frontend tests blocked until `npm ci`) |
