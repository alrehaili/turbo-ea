# Final decision recommendations and implementation readiness

> **Superseded in part (2026-10-22).** The business owner approved D-01, D-02, D-05, D-06, D-18, D-22, D-24 and D-30. See `DECISION_LOG.md` §2 for the approved wording. Two approvals **differ** from the recommendations below: **D-24** must not select the lowest (or latest) amount, and conflicts are excluded from totals; **D-30** uses redaction where the record stays meaningful and safe, and omission otherwise. Everything else here remains a recommendation.

**Status: recommendations only. No decision is approved by this document.** All 30 decisions remain **Open** in `DECISION_LOG.md` until you approve them. "Codex recommendation" means the planner's proposal. Documentation only: no code, schema, migration, test, build or commit.
**Date:** 2026-10-22
**Inputs:** `DECISION_REVIEW_PACKAGE.md`, `DECISION_LOG.md`, `MASTER_IMPLEMENTATION_PLAN.md`, `PHASED_DELIVERY_PLAN.md`, the assessment documents, the proposed directions in your brief (treated as **directions, not authorizations**), and the application code.

---

## 1. Verification performed

| Check | Result | Evidence |
|---|---|---|
| Instance currency default | **USD** unless an admin changed it | `backend/app/api/v1/settings.py:73` (`currency: str = "USD"`); `GET /settings/currency` |
| SAR display support | Exists: U+20C1 glyph with renderability fallback | `frontend/src/lib/currency.ts:10`, `currency.test.ts` |
| Per-card currency data | **A `currency` attribute exists on `Project` cards** (NORA metamodel), populated by `seed_demo_nora.py` / `seed_nora_strategic.py`, so mixed currencies are possible | Live metamodel listing (2026-10-22); seed files |
| Fiscal-year configuration | Exists: `general_settings.fiscalYearStart` (1-12, January by default); a year is named after the calendar year it ends in | `backend/app/services/fiscal_year.py:1-7` |
| Translation convention | **The fork is EN/AR-only**: the parity test pins `LOCALES = ["en", "ar"]` | `frontend/src/i18n/i18n.test.ts:36`; commit `82e09664` "NORA 2.0 … EN/AR-only UI". This **differs from CLAUDE.md's 10-locale rule**. |
| PPM money consumers | `PpmPortfolioView` already null-checks `total_budget`, so gating money is low-risk | `frontend/src/features/ppm/PpmPortfolioView.tsx:850` |
| ADR read-scope approach | Keeps the record, drops hidden linked cards from the payload, preserves hidden links on write (`hidden_card_ids`), filters list queries by scope | `backend/app/api/v1/adr.py:76-98, 217, 277, 407-418` |
| CLAUDE.md scope rule | "A single hidden card is 404"; ADR / SoAW **free text is out of scope by design** | CLAUDE.md "A card read has one scope" |
| **New security finding S-18** | `GET /reports/strategy-map` → `gather_strategy_map(db)`: **no read scope and no `costs.view`**; returns card names and `total_budget` / `total_actual` to any `reports.ea_dashboard` holder | `reports.py:2481-2492`; `services/strategy_map_service.py:151-207` (no scope references) |
| **New security finding S-19** | `GET /reports/freshness`, `/resilience`, `/data-flow`, `/integration-status` call `gather_*` services with **no read scope** | `reports.py:2504, 2516, 2527, 2537`; services have 0 scope references |
| Read-scope guard limitation | The guard checks scope markers **per module**. `reports.py` references the scope elsewhere, so per-endpoint gaps in it are invisible to the guard; only the sentinel sweep (with suitable fixtures) catches them | `tests/services/test_card_read_scope_guard.py:23-60` |
| Live data checks | **Not performed this session**: the local PostgreSQL was stopped and was not started (documentation-only task). Currency values, rationalization duplicates and the configured fiscal month must be verified before Phase 1 | — |

---

## 2. Review of all 30 decisions

**Classification**:

- **Policy**: a business-policy decision; your explicit approval is required.
- **Technical**: an implementation choice with no new business policy.
- **Convention**: already determined by an established Turbo-EA convention.

**Verdicts**:

- **Approve**: recommendation verified and unchanged.
- **Modify**: recommendation revised here.
- **Defer**: decide before the phase shown.

### 2.1 The seven Phase 1 decisions (detailed)

#### D-01: Exclude hidden or unauthorized cards consistently from dashboard metrics

- **Verified**: two distinct mechanisms.
  1. *Unauthorized cards* are already excluded by `CardReadScope` on `/reports/dashboard` and `/reports/executive`. That is an established convention, not a decision.
  2. *Hidden card types* (`card_types.is_hidden`) are included by `/reports/dashboard` and `/reports/executive` but excluded by `/reports/my-workspace` (`reports.py:365`) and `/reports/admin-dashboard` (`reports.py:407`).
- **Classification**: part 1 Convention; part 2 Policy (it changes visible totals).
- **Verdict**: **Approve**, with the wording clarified to "unauthorized cards: always excluded (existing convention); hidden-type cards: excluded from every dashboard metric".
- **Dependencies / risks**: totals drop for installs whose data still uses hidden types; the demo uses 7 hidden types holding 118 cards. Interacts with D-07: the org filter must not point at a hidden type. A CHANGELOG entry is needed.
- **Your approval required**: **Yes** (the hidden-type part).

#### D-02: Initiative health states and missing reports

- **Verified**: four states are already confirmed (C-12). The current code buckets missing reports as `noReport` (`ppm_portfolio_service.py:494`), but the Executive tile shows only `offTrack`, so missing reports look healthy by omission.
- **Classification**: Policy (source of truth and freshness window).
- **Verdict**: **Modify**, to follow your direction:
  - (a) **Unknown / Not reported** is its own state, never counted as On Track and never auto-promoted to At Risk;
  - (b) the headline shows reporting coverage beside the state mix;
  - (c) source of truth: PPM status reports when the module is on, `initiativeStatus` otherwise (unchanged proposal);
  - (d) the freshness window value (proposal 35 days) is **yours to set**. Until set, only "no report at all" counts as Not reported, so no staleness policy is invented.
- **Dependencies / risks**: the assessment doc `IMPLEMENTATION_RECOMMENDATIONS.md` §Phase 1 item 1.1 says "a stale or missing report counts as amber", which **contradicts** this direction (see §7). Coverage will look poor initially (6 of 20 in the demo).
- **Your approval required**: **Yes** (source of truth and window).

#### D-05: SAR for executive reporting

- **Verified**: the default currency is USD; SAR glyph support exists; `Project` cards carry their own `currency` attribute; PPM and cost fields are bare numbers with no currency.
- **Classification**: Policy (CFO) + a data verification.
- **Verdict**: **Modify**:
  - Phase 1 makes formatting currency-aware and adds `currency` to payloads **without relabeling** anything;
  - before the instance setting is switched to SAR, run a read-only pre-check listing every card with a `currency` attribute ≠ SAR and confirm with Finance that stored PPM and cost amounts are SAR;
  - **no conversion and no relabeling** of amounts whose currency is unverified;
  - mismatched records are reported, not converted.
- **Dependencies / risks**: relabeling USD amounts as SAR would misstate figures by about 3.75×. Benefits (Phase 4) store currency explicitly.
- **Your approval required**: **Yes** (CFO confirmation of the stored-amount currency, and the switch).

#### D-06: Reuse the existing fiscal-year configuration

- **Verified**: `fiscalYearStart` exists and is used by the cost reports and PPM charts (`fiscal_year.py`, `frontend/src/lib/fiscalYear.ts`).
- **Classification**: Convention.
- **Verdict**: **Approve** (reuse). Only the configured month value needs confirmation, which is data, not policy.
- **Dependencies / risks**: none beyond confirming the month.
- **Your approval required**: **No** (convention). Finance should confirm the configured month.

#### D-22: Preserve the prototype and establish a clean Git baseline

- **Verified**: the working tree holds four unrelated change sets:
  - (1) Windows `os.pread` fix (`brand_icons.py`);
  - (2) narrow-screen navigation (`AppLayout.tsx`);
  - (3) the phase-one Executive tab (backend, frontend, types, translations, permission key, `users.py` literal, BPM refactor, user docs, OpenAPI spec);
  - (4) documentation (two docs folders).

  `CHANGELOG.md` / `VERSION` (2.32.0) currently **mix (1) and (3)** in one entry.
- **Classification**: Policy (it authorises commits and the version plan) + Technical.
- **Verdict**: **Modify**: preserve everything, split into reviewable units (procedure in §5.4), and add tests per C-14 before each code unit merges. Documentation-only commits take **no version bump** (CLAUDE.md convention).
- **Dependencies / risks**: re-editing CHANGELOG / VERSION when splitting; a risk of losing untracked files if any destructive git command is used (avoid `git stash` without `-u` and avoid `git clean`).
- **Your approval required**: **Yes** (commit authorization and version plan).

#### D-24: Prevent duplicated planned savings

- **Verified**: `assessment_decisions` has `card_id`, `planned_savings`, `assessment_id`, `updated_at`, but **no period field**. Assessments have `status` (draft / active / completed / archived) and timestamps, but no "authoritative" flag. Today's code sums every decision in active and completed assessments.
- **Classification**: Policy (app portfolio owner).
- **Verdict**: **Modify**, following your direction not to assume the latest assessment is authoritative:
  - (a) **identity** = application (`card_id`) + reporting period, where the period is the fiscal year in which the decision's assessment is active or completed (`fiscal_year_for`);
  - (b) within one identity, if all decisions agree, count once;
  - (c) if they **conflict** (different `planned_savings` or `time_decision`), count the application **once at the lower amount** (conservative) and show a "conflicting estimates" count with drill-down. The portfolio owner resolves conflicts in the rationalization module;
  - (d) once the benefits register exists, a benefit linked to the decision supersedes planned savings for that identity;
  - (e) planned savings are always labelled **Forecast**.
- **Dependencies / risks**: the conservative rule may understate the pipeline; a later "authoritative assessment" flag would be a schema change (out of scope now).
- **Your approval required**: **Yes** (the conflict rule and period definition).

#### D-30: Restricted card information through governance records

- **Verified, ADR approach**: keep the record, drop hidden linked cards (name **and** id), preserve hidden links on write. Free text is out of scope by convention.
- **Evaluation for single-subject records** (ARB `subject_card_id`, standard exceptions, rationalization decision rows):
  - **Redact (ADR-style)**: the record stays visible with an empty subject. It still reveals that a review, exception or decision exists, and its title or notes frequently name the subject (free text is out of scope, so it is not scrubbed). This is acceptable for ADR because an ADR is a standalone decision about many cards. An ARB review, an exception or a decision row is **about exactly one card**, so its subject is its identity.
  - **Omit**: the record does not exist for the reader (list omission, 404 on detail, excluded from counts). This matches "a single hidden card is 404".
- **Classification**: Policy (security policy choice), strongly guided by convention.
- **Verdict**: **Modify** into a two-part rule:
  - (a) **multi-card records** (improvement opportunities, ADM artefacts, standards' card lists) follow the ADR pattern exactly;
  - (b) **single-subject records** are **omitted** (list, detail 404, aggregates);
  - (c) aggregates count governance records only when their subject is readable, so screen and counts agree.
- **Dependencies / risks**: holders of `arb.view` without card access see fewer reviews. Admins (wildcard) are unaffected.
- **Your approval required**: **Yes**.

### 2.2 The other 23 decisions

| ID | Decision | Class | Verdict | Verification / justification | Dependencies & risks | Approval? | Phase |
|---|---|---|---|---|---|---|---|
| D-03 | Role grants for new permissions | Policy | Defer | `reports.executive_dashboard` is admin-only today (wildcard); Executive and Finance roles proposed | D-29; access widening is irreversible in practice | Yes | 2 |
| D-04 | Open-risk definition + escalation | Policy | Defer | Current open = not closed / accepted (`executive_dashboard.py:139`); a tag group needs no schema | CRO input | Yes | 2 |
| D-07 | Organisation filter type | Policy | Defer | `Organization` is hidden in the NORA profile but used by demo relations; NORA uses `OrganizationalUnit` | D-01 (must not be a hidden type); possible data migration | Yes | 2 |
| D-08 | Service digitalization source; canonical GovService | Policy | Defer | Two definitions (`seed.py:4840`, `nora_profile.py:4462`); live type lacks `deliveryChannel`; 0 GovService cards | Metamodel migration; data population | Yes | 5 |
| D-09 | Eligible processes / threshold | Policy | Defer | Subtypes category / group / process / variant exist | Processes without a subtype need a rule | Yes | 2 |
| D-10 | EA review "in scope" rule | Policy | Defer | No rule today | D-02 source of truth; budget data | Yes | 3 |
| D-11 | Early-engagement gate | Policy (convention-guided) | Defer | `adm_phases.approved_at` exists; 0 ADM workspaces | Fallback to `startDate` dominates initially | Yes | 3 |
| D-12 | Benefit storage | Technical with policy impact | Defer | No field-level permissions on card attributes | Migration + transfer | Yes | 4 |
| D-13 | Decision actions | **Convention** | Approve (convention) | Todos have assignee, due date, status, notifications (`models/todo.py`); C-02 no duplicates | Migration (two columns) + transfer rewrite | No | 3 |
| D-14 | Attribution method (no fixed %) | Policy | Defer | C-07 confirmed | Finance workload | Yes | 4 |
| D-15 | ROI cost scope + window | Policy | Defer | EA office cost not modelled | Tagging discipline | Yes | 4 |
| D-16 | Tech debt index weights | Policy | Defer | Components exist (EOL, lifecycle, suitability, exceptions) | Baseline snapshot (D-19) | Yes | 4 |
| D-17 | KPI targets | Policy | **Modify** (classification) | Marked "blocks Phase 0", which is circular: Phase 0 is where it is decided. It actually blocks **Phase 2** tiles | KPI cards must exist (0 today) | Yes | 2 |
| D-18 | Translation scope | **Convention (fork)** | **Modify** → EN/AR per fork convention | `i18n.test.ts:36` pins en / ar; commit `82e09664` EN/AR-only UI | Conflicts with CLAUDE.md's 10-locale text; CLAUDE.md should be updated separately to record the fork rule | No (convention) | 2 |
| D-19 | Snapshot storage | **Convention** | Approve (convention) | `kpi_snapshots` has 4 fixed columns; no-duplication convention | Overview trend code migrates in the same change | No | 2 |
| D-20 | Small-group suppression | Policy (security) | Defer | No suppression exists | — | Yes | 2 |
| D-21 | Strategy progress source | Policy | Defer | `Objective.progress` is a number field; 0 objective-KPI links | Manual values = medium confidence | Yes | 2 |
| D-23 | Summary insights | Policy | Defer | TurboLens AI plumbing exists | Scope-safe payload only | Yes | 6 |
| D-25 | Milestone achievement source | Policy (convention-guided) | Defer | `roadmap_milestones` lacks achievement; `ppm_wbs.is_milestone` exists | 0 milestones | Yes | 5 |
| D-26 | KPI card ↔ builder link | **Convention** | Approve (convention) | `external_id` is owned by import and ServiceNow paths | Metamodel migration | No | 2 |
| D-27 | Arabic numerals | Policy (UX preference) | Defer | `Intl` `ar` default is Arabic-Indic | Export consistency | Yes | 2 |
| D-28 | Working-day calendar | Policy | Defer | — | — | Yes | 3 |
| D-29 | Segregation of duties | Policy | Defer | — | Needs ≥ 2 Finance users | Yes | 4 |

---

## 3. Implementation decision table

All 30 remain **Open** until you approve them. "Approval" = requires your explicit approval.

### 3.1 Ready for approval now (recommendation verified, unchanged)

| ID | Description | Codex recommendation | Class | Proposed resolution | Approval | Phase | Reason / consequences |
|---|---|---|---|---|---|---|---|
| D-01 | Hidden / unauthorized cards in metrics | Approve | Policy (hidden types) + Convention (unauthorized) | Unauthorized: always excluded (existing). Hidden types: excluded from every dashboard metric | **Yes** | 1 | Consistent totals across tabs; visible drop where hidden types hold data |

### 3.2 Needing modification (revised here; then approval)

| ID | Description | Codex recommendation | Class | Proposed resolution | Approval | Phase | Reason / consequences |
|---|---|---|---|---|---|---|---|
| D-02 | Initiative health and missing reports | Modify | Policy | Four states; Not reported never healthy, never auto at-risk; coverage shown; PPM source with `initiativeStatus` fallback; freshness window set by you (until then, only "no report" = Not reported) | **Yes** | 1 | Removes misleading "0 off track" |
| D-05 | SAR reporting | Modify | Policy + data check | Currency-aware formatting and payload now; pre-check of `Project.currency` and stored amounts; switch to SAR only after CFO confirmation; never convert or relabel unverified amounts | **Yes** | 1 | Avoids misstating USD as SAR |
| D-17 | KPI targets | Modify (classification) | Policy | Reclassify as blocking Phase 2 (not Phase 0) | **Yes** | 2 | Removes a circular dependency |
| D-22 | Preserve prototype, Git baseline | Modify | Policy + Technical | Backup, then split into: Windows fix · nav change · prototype · docs; tests per unit; docs without a version bump | **Yes** | 1 | Clean, reviewable baseline; no loss |
| D-24 | Planned-savings duplication | Modify | Policy | Identity = application + FY; agree → once; conflict → once at the lower amount + conflict flag; linked benefit supersedes; always Forecast | **Yes** | 1 | No inflation; no "latest wins" assumption |
| D-30 | Governance records about hidden cards | Modify | Policy (security) | Multi-card records: ADR pattern. Single-subject records: omitted (list, 404, counts) | **Yes** | 1 | Closes S-03, S-04, S-06 without free-text leaks through orphans |

### 3.3 Technical conventions already established (no business approval; still Open until acknowledged)

| ID | Description | Codex recommendation | Class | Proposed resolution | Approval | Phase | Reason / consequences |
|---|---|---|---|---|---|---|---|
| D-06 | Fiscal year | Approve (convention) | Convention | Reuse `fiscalYearStart`; Finance confirms the configured month | No | 1 | One fiscal definition app-wide |
| D-13 | Decision actions | Approve (convention) | Convention | Extend todos (`source_kind`, `source_id`) | No | 3 | No duplicate tasking entity |
| D-18 | Translation scope | Modify → convention | Convention (fork) | EN + AR, per the fork's parity test and commit `82e09664` | No | 2 | CLAUDE.md text should be reconciled separately |
| D-19 | Snapshot storage | Approve (convention) | Convention | Replace `kpi_snapshots` with `metric_snapshots` | No | 2 | One history mechanism |
| D-26 | KPI ↔ builder link | Approve (convention) | Convention | New `metricKey` field on the KPI type | No | 2 | `external_id` is owned by imports |

### 3.4 Can safely wait (decide before the phase shown)

| ID | Description | Codex recommendation | Class | Proposed resolution (proposal) | Approval | Phase | Reason / consequences |
|---|---|---|---|---|---|---|---|
| D-03 | Role grants | Defer | Policy | New Executive + Finance roles | Yes | 2 | Least privilege |
| D-04 | Open risk + escalation | Defer | Policy | Keep definition; Escalation tag group | Yes | 2 | No schema change |
| D-07 | Org filter type | Defer | Policy | Admin setting naming the org type (not hidden) | Yes | 2 | Data-driven; NORA and non-NORA |
| D-09 | Eligible processes | Defer | Policy | Subtype `process`, active | Yes | 2 | Avoids hierarchy double count |
| D-20 | Small-group threshold | Defer | Policy | n < 3 | Yes | 2 | Disclosure control |
| D-21 | Strategy progress | Defer | Policy | Manual v1 | Yes | 2 | No KPI links yet |
| D-27 | Arabic numerals | Defer | Policy | Stakeholder preference | Yes | 2 | Display only |
| D-10 | EA review scope | Defer | Policy | Program / project + budget threshold + tag | Yes | 3 | GOV-01 denominator |
| D-11 | Early-engagement gate | Defer | Policy | ADM gate, fallback startDate | Yes | 3 | Reuses ADM |
| D-28 | Working days | Defer | Policy | Sun-Thu default | Yes | 3 | Turnaround accuracy |
| D-12 | Benefit storage | Defer | Technical + policy | Dedicated tables | Yes | 4 | Finance-only transitions |
| D-14 | Attribution method | Defer | Policy | Per-benefit method enum, Finance-assessed | Yes | 4 | Complies with C-07 |
| D-15 | ROI scope / window | Defer | Policy | `roiScope` tag; FY + rolling 3-FY | Yes | 4 | Comparable periods |
| D-16 | Tech debt weights | Defer | Policy | Equal weights v1 | Yes | 4 | Transparent |
| D-29 | Segregation of duties | Defer | Policy | Creator cannot confirm | Yes | 4 | Financial control |
| D-08 | Service digitalization | Defer | Policy | `digitalizationLevel`; NORA definition canonical | Yes | 5 | Separate from automation (C-10) |
| D-25 | Milestone source | Defer | Policy | Derive from WBS; fields for roadmap-only | Yes | 5 | Reuse first |
| D-23 | Insights | Defer | Policy | Rule-based; AI optional | Yes | 6 | Auditable |

**Totals**: 1 ready · 6 modify · 5 convention · 18 wait = 30. Approval required for 25; 5 are conventions.

---

## 4. Plan changes needed (to apply **only after** the related approval)

These are **pending** edits, deliberately not yet applied, so the plan does not imply approval.

| Document | Section | Change | Triggered by |
|---|---|---|---|
| `FINAL_KPI_DICTIONARY.md` | §2 CR-01/02 | The freshness window becomes "set by owner; until set, only missing reports = Not reported"; state "never auto at-risk" | D-02 |
| `FINAL_KPI_DICTIONARY.md` | §2 CR-04; §3.5 FIN-03 | Replace "latest decision" with the identity + FY + conflict rule | D-24 |
| `FINAL_KPI_DICTIONARY.md` | §2 CR-05 | Add the pre-check and the no-relabel rule | D-05 |
| `DECISION_LOG.md` | D-17 row | "Needed by" → Phase 2 | D-17 |
| `DECISION_LOG.md` | D-18 row | Record the fork EN/AR convention | D-18 |
| `SECURITY_REMEDIATION_PLAN.md` | §2 principle 1 | State the two-part rule (multi-card ADR pattern; single-subject omit) | D-30 |
| `PHASED_DELIVERY_PLAN.md` | Phase 1 | Add the baseline procedure (§5.4) as the first step; add S-18 / S-19 fixes | D-22, findings |
| `UI_UX_SPECIFICATION.md` / dictionary | Translations | "EN + AR (fork convention)" replaces "other locales per D-18" | D-18 |

**Applied now (factual, no decision implied):** `SECURITY_REMEDIATION_PLAN.md` gains findings **S-18** and **S-19** and work item **WI-15**. `PROGRESS_REPORT.md` is updated with planning progress only.

---

## 5. Implementation readiness

### 5.1 Phase 1 tasks that can begin without unresolved business decisions (after you authorise implementation)

| Task | Basis |
|---|---|
| WI-12 extend the sentinel sweep fixture (ARB, exceptions, rationalization, opportunities, ADM, milestones, plus strategy-map / freshness / resilience / data-flow / integration-status over the sentinel) | Tests only; no policy |
| S-01 roadmaps timeline scope | CLAUDE.md scope rule |
| S-02 impact graph scope | CLAUDE.md scope rule |
| S-05 compliance scan scope | CLAUDE.md scope rule |
| S-09 improvement-opportunity briefs (multi-card → ADR pattern) | ADR precedent |
| S-10 NORA dashboard counts, S-11 maturity indicators, S-12 realized-value counts | CLAUDE.md scope rule (aggregates count readable cards only) |
| S-13 ADM hidden ids dropped (multi-reference → ADR pattern) | ADR precedent |
| S-14 ai-suggest refuses restricted readers | TurboLens `_require_whole_landscape` precedent |
| **S-18** strategy-map scope; **S-19** freshness / resilience / data-flow / integration-status scope | CLAUDE.md scope rule |
| S-07, S-08, S-18 money gated on `costs.view` | Established cost-report convention (CLAUDE.md, `cost_report`) |
| CR-03 fiscal-year-bound budget vs actual | D-06 is convention |
| CR-05 (part) currency-aware formatter and `currency` in payloads, **no relabel** | Display only |
| CR-07, CR-08, CR-09, CR-10 label and placement corrections (EN + AR) | Explicitly requested corrections; no policy |

### 5.2 Blocked Phase 1 tasks

| Task | Blocked by |
|---|---|
| Any change to the uncommitted prototype files (CR-01..CR-10 on the Executive tab) | **D-22** (baseline first) |
| CR-06 hidden-type exclusion (S-15, WI-11) | **D-01** |
| CR-01 / CR-02 freshness window (the four-state structure can be built; the window value cannot) | **D-02** |
| Switching the instance currency to SAR | **D-05** + data pre-check |
| CR-04 dedupe rule | **D-24** |
| S-03 ARB, S-04 exceptions, S-06 rationalization decision rows (single-subject handling) | **D-30** |

### 5.3 Security fixes independent of the dashboard redesign

S-01, S-02, S-03*, S-04*, S-05, S-06*, S-07, S-08, S-09, S-10, S-11, S-12, S-13, S-14, **S-18**, **S-19** (* after D-30). None touches the Executive tab files. They can ship on their own branch from `main`, in parallel with the D-22 baseline work. **They protect existing pages today**, regardless of the dashboard.

### 5.4 Preserving the uncommitted work safely

Procedure for when you authorise it. **Not executed.**

1. **Backup first, non-destructively**:
   - `git diff > <outside-repo>/turbo-ea-wip.patch` (tracked changes);
   - archive the untracked files: `backend/app/api/v1/executive_dashboard.py`, `backend/app/services/executive_dashboard.py`, `backend/app/services/bpm_dashboard_service.py`, `frontend/src/features/dashboard/executive/`, and the new `.md` files in both docs folders;
   - keep `backend/.env` (gitignored) out of every archive and commit.
2. **Branch**: `git switch -c baseline/exec-dashboard-wip` from the current `main`. No `git stash`, `git clean` or `git checkout -- .`.
3. **Split into reviewable units** on separate branches or PRs, each from `main`:
   - (a) **Windows fix** (`brand_icons.py`) + regression test + its own patch version and CHANGELOG line;
   - (b) **narrow-screen nav** (`AppLayout.tsx`) + Vitest + CHANGELOG line;
   - (c) **phase-one prototype** (executive backend / frontend / types / translations / permission / `users.py` literal / BPM refactor / user docs / OpenAPI spec) + tests per C-14 + version 2.32.0 entry rewritten to cover only the prototype;
   - (d) **planning docs** (both folders), with no version bump.
4. Run `ruff format` / `ruff check` before each backend commit (CLAUDE.md). CI runs the consolidated suites: backend shards + aggregate, frontend shards + E2E, diff coverage, mutation gates. Mutation testing is **not** run locally by an agent (CLAUDE.md).

### 5.5 Recommended order after approval

1. **D-22 baseline**: backup, then units (a), (b), (d) (fast, independent) and (c) with tests.
2. **WI-12 sweep fixture**: it must fail on the known leaks (proof).
3. **Independent security fixes**, High first: S-01, S-02, S-18, S-19, S-05, S-09, S-13, S-14, then money S-07 / S-08 / S-18, then counts S-10 / S-11 / S-12.
4. **D-30-dependent fixes**: S-03, S-04, S-06.
5. **Correctness on the prototype**: CR-03, CR-05 (part), CR-07..CR-10, then CR-01 / CR-02 (window per D-02), CR-04 (per D-24), CR-06 (per D-01).
6. **Phase 1 exit**: extended sweep green, guard green, restricted-reader tests for every work item, money never without `costs.view`, CI green including mutation gates. **Security fixes deploy only after this validation.**
7. Then Phase 2, subject to the Phase 2 decisions (D-03, D-04, D-07, D-17 and others).

---

## 6. Summary of the 30 decisions

| Bucket | Count | IDs |
|---|---|---|
| Ready for approval | 1 | D-01 |
| Needing modification | 6 | D-02, D-05, D-17, D-22, D-24, D-30 |
| Established conventions | 5 | D-06, D-13, D-18, D-19, D-26 |
| Can safely wait | 18 | D-03, D-04, D-07, D-09, D-20, D-21, D-27 (Ph 2) · D-10, D-11, D-28 (Ph 3) · D-12, D-14, D-15, D-16, D-29 (Ph 4) · D-08, D-25 (Ph 5) · D-23 (Ph 6) |
| **Requiring your explicit approval** | **25** | All except D-06, D-13, D-18, D-19, D-26 |
| Phase-1 decisions | 7 | D-01, D-02, D-05, D-06, D-22, D-24, D-30 (6 need approval; D-06 is convention) |

## 7. Contradictions and risks in the existing plan

| # | Issue | Where | Recommended handling |
|---|---|---|---|
| 1 | "A stale or missing report counts as amber" contradicts the D-02 direction (Not reported is neither healthy nor at risk) | `docs/executive-dashboard-assessment/IMPLEMENTATION_RECOMMENDATIONS.md` §Phase 1 item 1.1 | The superseded assessment stays as-is; the implementation plan follows D-02 |
| 2 | D-24 "latest decision wins" conflicts with your direction | `FINAL_KPI_DICTIONARY.md` §2 CR-04, §3.5 FIN-03; `DECISION_LOG.md` D-24 | Pending edit after approval (§4) |
| 3 | D-17 blocks "Phase 0", which is circular | `DECISION_LOG.md` | Reclassify to Phase 2 (§4) |
| 4 | CLAUDE.md requires 10 locales; the fork's test and practice are EN/AR-only | CLAUDE.md vs `i18n.test.ts:36` | Follow the fork; reconcile CLAUDE.md in a separate docs change |
| 5 | The security plan missed S-18 (strategy-map: scope **and** money) and S-19 (four `gather_*` reports); IMP-06 planned to reuse integration-status | `SECURITY_REMEDIATION_PLAN.md`, `FINAL_KPI_DICTIONARY.md` IMP-06 | S-18 / S-19 added now; fix before reuse |
| 6 | The read-scope guard cannot see per-endpoint gaps inside a module that references the scope elsewhere (`reports.py`) | `test_card_read_scope_guard.py` | Rely on the extended sentinel sweep (WI-12) |
| 7 | CHANGELOG / VERSION 2.32.0 mixes the Windows fix with the prototype | working tree | Split per §5.4 |
| 8 | Relabeling stored amounts as SAR without verification would misstate figures | D-05 | Pre-check + CFO confirmation |
| 9 | Live data checks were not performed this session (DB stopped) | §1 | Run the read-only pre-checks before Phase 1 |
| 10 | Omitting single-subject records reduces what `arb.view` / `tech_standards.view` holders see | D-30 | Communicate in release notes; admins unaffected |
| 11 | The CI state of the fork is unknown (guard may already fail on fork modules, S-17) | — | First CI run on the baseline branch establishes it |
