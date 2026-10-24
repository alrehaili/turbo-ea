# Progress report

**Reporting date:** 2026-10-24 (updated after the SEC-1 to SEC-3 implementation and the Phase 1 security preparation and the final integration)
**Rule:** planning documents do not count as implementation. A track or phase becomes *Completed* only when its definition of completion in `PHASED_DELIVERY_PLAN.md` is met (merged, tested, documented). **Only the Security Remediation Track has been implemented, and it is not yet committed or run in CI.**

## Status

| Stream / phase | Status | Notes |
|---|---|---|
| **Security Remediation Track (SEC)** | **Pending verification** (implemented incl. §9 preparation and §10 final integration; full backend suite not run; frontend tests blocked; not in CI; uncommitted) | SEC-1, SEC-2 and SEC-3 were implemented on 2026-10-24 under D-01 and D-30. All 26 findings are resolved: S-08 and S-12 were decided on 2026-10-24 and implemented, together with scenario-merge authorization and readable-only segment traversal (`SECURITY_REMEDIATION_PLAN.md` §9; 8 new focused tests pass). Locally, the extended sweep, 17 new disclosure tests, the signature guard and the read-scope guard pass. On unmodified `HEAD` the same sweep fails on 24 routes and 15 of 16 of the new tests fail. The full backend suite was not run (stopped at the owner's request) and the new S-14 test has not run yet; both are deferred to CI. Evidence: `SECURITY_REMEDIATION_PLAN.md` §8. The track is not *Completed* until it is committed, green in CI and merged. |
| Phase 0: decisions, KPI ratification, data ownership | **In Progress** (planning) | Phase 1 decisions approved 2026-10-22 (D-01, D-02, D-05, D-06, D-22, D-24, D-30) plus D-18. 23 decisions remain open (11 blocking, incl. the new D-31). KPI ratification and data stewardship not started. |
| Phase 1: prototype baseline and KPI correctness | **Not Started** | Baseline procedure planned (D-22). Commits await a separate instruction. CR-04 is blocked by D-31. |
| Phase 2: CEO overview, KPI history, decision intelligence | **Not Started** | Blocked by D-03, D-04, D-07, D-17; depends on Phase 1 and the relevant SEC items |
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
| 3 | D-31 open (financial period of planned savings) | Blocks CR-04 only | App portfolio owner + CFO |
| 4 | Live data checks not done (local DB stopped): currency values, savings conflicts, fiscal month | D-05 verification; CR-04 sizing | Tech lead + Finance |
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
