# Verification results and reproducibility

Date: 28 October 2026. Host: Windows, repository `D:\dev\turbo-ea`. Existing backend `.venv` and frontend `node_modules` used. No dependencies installed. Source HEAD `3287b83fdbf56b419edce0256f35d0fb5bc03d02`.

## Executed checks

| Check | Result | Meaning/limits |
| --- | --- | --- |
| Git status before review | `?? backend/%SystemDrive%/` | Pre-existing untracked directory preserved; no tracked modifications initially |
| Upstream fetch/history | Success; baseline and ancestry in report 02 | No merge; fetched `main` at review time, not unseen branches |
| Backend mixed selected collection | 610 items collected across four files | Collection is not execution success |
| Initial mixed execution | One stale savings failure; DB-dependent cases skipped because test database unavailable | No DB-backed PASS; local test fixture attempted connection. No successful schema creation/drop observed. Subsequent execution deliberately selected pure cases. |
| Final pure business/NORA selection | **515 passed, 1 failed**, 516 collected, 1.85s pytest time | NORA definitions/translation completeness and pure executive calculations; not a domain-wide end-to-end result |
| JWT/encryption files | **49 passed, 2 errors**, 51 collected, 3.33s | Two `time.tzset` fixture errors on Windows; token/encryption remaining tests pass. Test-only weak-key warnings are not production-key evidence. |
| Four selected frontend files | **4 files / 28 tests passed**, 19.58s | Mocked/component tests; jsdom emitted canvas-not-implemented warning from currency glyph detection; not a browser failure |
| TypeScript | `node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json` — exit 0 | App source type checking; tests excluded by config; no Vite bundling/load/performance verification |
| Alembic graph | `.venv\Scripts\python.exe -m alembic heads` — `1175 (head)` | Offline graph inspection only, not migrated installed schema |
| Transfer descriptor introspection | Card successor absent from CARD_COLUMNS; ApprovalStep absent from ENTITY_SECTIONS; GovernanceTransitions present | Confirms FR-05 omission without DB access; no round-trip execution |

An initial TypeScript command named nonexistent `tsconfig.app.json` and returned TS5058. It was corrected to the repository's real `tsconfig.json`, which passed. Missing guessed file paths during exploration were corrected; they are not product defects.

## Commands

From repository root:

```powershell
git status --short
git fetch https://github.com/vincentmakes/turbo-ea.git main
git rev-parse HEAD
git rev-parse FETCH_HEAD
git merge-base HEAD FETCH_HEAD
git rev-list --left-right --count HEAD...FETCH_HEAD
git log --oneline HEAD..FETCH_HEAD
git diff FETCH_HEAD HEAD -- backend/pyproject.toml frontend/package.json
```

Final backend pure selection, from `backend` (the AST selector selects only synchronous top-level tests plus three explicitly pure definition classes):

```powershell
.\.venv\Scripts\python.exe -c "import ast,pytest; fs=['tests/services/test_executive_dashboard_kpis.py','tests/services/test_executive_governance.py','tests/services/test_nora_profile.py']; args=[]; [args.extend(f+'::'+n.name for n in ast.parse(open(f,encoding='utf-8').read()).body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')) for f in fs]; args += ['tests/services/test_nora_profile.py::TestNoraProfileDefinitions','tests/services/test_nora_profile.py::TestNoraCardTypeDefinitions','tests/services/test_nora_profile.py::TestNoraRelationTypeDefinitions']; raise SystemExit(pytest.main(args+['-o','addopts=','-ra','-p','no:cacheprovider']))"
.\.venv\Scripts\python.exe -m pytest tests/core/test_security.py tests/core/test_encryption.py -o addopts= -ra -p no:cacheprovider
.\.venv\Scripts\python.exe -m alembic heads
```

Frontend, from `frontend`:

```powershell
node node_modules/vitest/vitest.mjs run src/features/dashboard/executive/executiveFormat.test.ts src/features/dashboard/executive/executivePlurals.test.ts src/features/dashboard/executive/ExecutiveOverview.test.tsx src/features/dashboard/executive/ExecutiveDecisions.test.tsx
node node_modules/typescript/bin/tsc --noEmit -p tsconfig.json
```

Do not repeat the initial mixed command against an unreviewed database environment: `backend/tests/conftest.py:91–141` calls `drop_all/create_all` on the test database. Use a dedicated disposable database and assert its resolved host/database before running integration tests. No production connection or production service was intentionally used or supplied.

## FR-07 — Savings test retains an obsolete blocked-period expectation

**Category:** test/contract drift. **Severity:** P2. **Confidence:** Confirmed executed failure; stale expectation interpretation Probable, strongly supported by code decision comment.

**Sources:** `backend/tests/services/test_executive_dashboard_kpis.py:196–197`; `backend/app/services/executive_dashboard.py:463–466,513`; `frontend/src/features/dashboard/executive/ExecutiveBenefits.tsx:322–326`.

**Actual:** `test_savings_period_is_marked_blocked_on_d31` expects `{status: blocked, decision: D-31}`; current function returns `{status: run_rate, decision: D-31}`. Implementation explicitly states D-31 now defines annual run-rate forecasts without a fiscal year. Expected: tests and clients agree on the approved temporal contract, never representing forecast as realized savings.

**Impact/scope:** selected suite is red; not proof that the savings amount is wrong. Pilot can avoid authoritative savings reporting. Minimum correction: confirm intended D-31 contract, update the stale test and inspect all clients for that status; retain forecast/realized/period assertions. Do not change code back to obsolete behavior just to make the test pass.

**Validation:** focused test file green with assertions for run-rate labeling, separate confirmed actuals, deduplication, conflicts and permission-gated details. No correction applied by this evaluation.

## Coverage and limits

There are API/security/scoping, governance, fiscal-year, transfer, migration, executive and UI test sources. The declared coverage floors in pyproject/package metadata are not measurements from this review. No current aggregate coverage percentage or CI status is certified.

Important unexecuted scenarios: direct-ID and cross-module RBAC denials; departmental sharing policy; author/reviewer independence in every instrument; hidden cards in search/export/diagrams; financial redaction; attachment upload/download abuse; import dry-run/rollback/idempotency; completed-period calculations on real DB rows; benefits reversal/allocation; fresh/upgrade migrations; restore; non-Docker lifecycle jobs; internal IdP; denied internet operation; Arabic browser/export and keyboard use. Existing tests may cover parts of these; they were not run here.

No full test suite, full frontend build, dependency vulnerability scanner, load test, browser/E2E test, live API test, database migration, backup/restore or deployment was run. **NOT VERIFIED** applies, not PASS. Findings based on source are labeled static rather than falsely reproduced.
