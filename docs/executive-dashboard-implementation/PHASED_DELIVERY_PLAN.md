# Phased delivery plan

**Status: plan, not started.** Complexity: S (≈ days) · M (≈ 1-2 weeks) · L (≈ 3+ weeks), for one experienced developer familiar with the codebase. These are assumptions to validate.

**Every phase and track** follows the project's validation approach (CLAUDE.md): tests for every change (API success / 403-404 / rejected input; Vitest for components; regression tests for fixes), diff coverage ≥ 80%, mutation score on changed lines (run in CI, not locally by an agent), ruff and ESLint, Alembic + workspace-transfer checklist for schema changes, OpenAPI regenerated, CHANGELOG + VERSION bump once per PR (documentation-only changes take no bump), user docs updated. **Translations: English and Arabic only, per the fork's language policy (D-18, approved).** **Nothing is executed during planning.**

**Two separate streams** (decision of 2026-10-22: security remediation is separated from the Executive Dashboard feature phases):

```
SECURITY REMEDIATION TRACK (independent of the dashboard; protects existing pages)
  SEC-1 disclosure regression suite ─▶ SEC-2 name/id + money leaks ─▶ SEC-3 governance records + aggregates
                                                                              │ SEC exit (validated in CI)
EXECUTIVE DASHBOARD FEATURE PHASES                                            ▼  gate for reuse of affected APIs
  Phase 0 ──▶ Phase 1 ──▶ Phase 2 ──┬─▶ Phase 3 ──┐
  (decide)    (baseline +  (overview, │             ├─▶ Phase 6 (reporting, QA)
              KPI          history,   └─▶ Phase 4 ──┤
              correctness) decisions)      ▲        │
                                           └─ Phase 5 (needs 2 + data)
```

- The security track starts as soon as implementation is authorised. It does not wait for Phase 0 or Phase 1, and it never touches the Executive prototype files.
- Feature **Phase 2 onwards** may reuse an affected API only after the security work item covering it has passed CI (C-05).

---

## Security remediation track (SEC)

Full findings and work items are in `SECURITY_REMEDIATION_PLAN.md`. The decisions it depends on are both approved: D-01, D-30.

| Item | Content |
|---|---|
| Objective and scope | Close S-01..S-19 so no restricted card information or unauthorized monetary value leaks through any endpoint, count, chart, export or drill-down, independently of the Executive Dashboard redesign |
| Stages | **SEC-1** disclosure regression suite (WI-12 + the regression coverage in `SECURITY_REMEDIATION_PLAN.md` §6), written to fail on the known leaks · **SEC-2** name / id leaks and money gating (WI-1, WI-2, WI-4 scan part, WI-5 money part, WI-6, WI-15) · **SEC-3** governance-record handling per D-30 (WI-3, WI-4 records part, WI-5 records part, WI-7, WI-10), aggregate counts (WI-8, WI-9), hidden-type exclusion per D-01 (WI-11), guard (WI-13) |
| Existing components reused | `CardReadScope`, `require_card_readable`, `hidden_card_ids`, the ADR redaction pattern, `costs.view` (cost-report convention), TurboLens `_require_whole_landscape`, sentinel sweep, read-scope guard |
| Backend changes | Scope and money gating in `roadmaps.py`, `reports.py` (impact, strategy-map, freshness, resilience, data-flow, integration-status) and their services, `arb.py`, `tech_standards.py`, `tech_standards_scan.py`, `rationalization.py`, `ppm_reports.py`, `improvement_opportunities.py`, `nora_program.py`, `maturity_indicators.py`, `adm.py`, `nora_authoring.py`; `visible_types_clause` in `/reports/dashboard` |
| Frontend changes | Null-safe handling where money fields may be omitted (`PpmPortfolioView` already null-checks `total_budget`; `ExecutiveStrategyMap` must be checked); no other UI change |
| Database changes | None |
| API changes | **Behaviour changes** (CHANGELOG "Security"): money omitted without `costs.view` (PPM dashboard, rationalization, strategy-map); single-subject governance records about hidden cards omitted (404 on detail); hidden card references redacted from multi-card records; totals exclude hidden types |
| Security considerations | Hidden links preserved on write; no record deleted; omitted records remain visible to authorized users (D-30). Exports and drill-downs follow the screen rules. |
| Dependencies | Authorization to implement. D-01 and D-30 are approved; no other decision blocks the track. |
| Acceptance criteria | Extended sweep green with non-vacuity control; guard green without new allowlist entries; restricted-reader and no-cost API tests per work item; count, chart and money regression tests green (§6 of the security plan) |
| Deliverables | One PR per stage (SEC-1, SEC-2, SEC-3); a security review in each PR Test Plan; CHANGELOG "Security" entries |
| Risks | Fork modules or extensions relying on unscoped reads; clients expecting money fields; the fork's CI state unknown (S-17) |
| Complexity | M |
| Definition of completion | All three stages merged with green CI including mutation gates. **Validated in CI before any deployment.** PROGRESS = Completed. |

---

## Phase 0: KPI definitions, business decisions, data ownership

| Item | Content |
|---|---|
| Objective and scope | Ratify the KPI dictionary, targets, owners and rules; resolve the remaining open decisions as their phases approach; start data population |
| Existing components reused | KPI card type (definitions), surveys (data collection), stakeholder roles (owners), tag groups |
| Backend / frontend / DB / API changes | **None** (configuration and data entry only) |
| Security considerations | Approve role grants for `reports.executive_dashboard` and the benefit permissions (D-03) |
| Dependencies | Executive sponsor, CFO, Chief Architect, PMO, Digital Office availability |
| Acceptance criteria | Phase 1 decisions approved (**done 2026-10-22**, except the new D-31); Phase 2 blocking decisions (D-03, D-04, D-07, D-17) approved before Phase 2; each release-1 KPI has a named owner and an approved target; the stewardship plan has dates |
| Deliverables | Updated decision log; approved KPI dictionary (v1.0); data stewardship plan; KPI cards created for release-1 KPIs (by owners, in the app) |
| Risks | Decision latency; unavailable Finance input; data owners not appointed |
| Complexity | S (effort is stakeholder time) |
| Definition of completion | Sign-off recorded in the decision log; `PROGRESS_REPORT.md` Phase 0 = Completed |

## Phase 1: Prototype baseline and KPI correctness

| Item | Content |
|---|---|
| Objective and scope | Establish a clean, tested baseline of the existing uncommitted work (D-22) and apply corrections CR-01..CR-10 (`FINAL_KPI_DICTIONARY.md` §2) to the Executive prototype. Security fixes are **not** in this phase (see the security track). |
| Step 1: preserve and baseline (D-22, approved; commits require a separate instruction) | (1) **Non-destructive backup**: a `git diff` patch of tracked changes saved outside the repo, plus an archive of untracked files (`backend/app/api/v1/executive_dashboard.py`, `backend/app/services/executive_dashboard.py`, `backend/app/services/bpm_dashboard_service.py`, `frontend/src/features/dashboard/executive/`, the new docs). Exclude `backend/.env`. No `git stash`, `git clean` or `git checkout -- .`. (2) **Four logical commits or PRs** from `main`: **(a) Windows fix** (`brand_icons.py`) + regression test + patch version and CHANGELOG line; **(b) responsive navigation** (`AppLayout.tsx`) + Vitest + CHANGELOG line; **(c) Executive prototype** (executive backend / frontend / types / EN + AR strings / permission key / `users.py` literal / BPM refactor / user docs / OpenAPI spec) + tests + its own CHANGELOG entry (the current 2.32.0 entry is split so that the Windows fix moves to (a)); **(d) documentation** (both docs folders), no version bump. |
| Existing components reused | `fiscal_year.py`, `lifecycle.py`, `eol_service`, `lib/currency.ts`, `useCurrency`, settings, phase-one builders |
| Backend changes | Executive builders: four-state health + coverage with a configurable staleness setting that has **no default** (D-02); FY-bound budget / actual (D-06); currency-aware payloads with per-currency totals and no cross-currency sums (D-05); planned-savings dedupe by identity + financial period, with conflicts flagged and excluded from totals (D-24, D-31); `visible_types_clause` in the executive aggregates (D-01) |
| Frontend changes | Four-state health with a separate coverage indicator; FY label on budget; Forecast chip; currency-aware formatter (no relabeling); "conflicting estimates" indicator; remove Approved %; renames: Data completeness / Past planned end-of-life / Process documentation coverage (EN, AR); Overview label fixes |
| Database changes | None (the staleness setting lives in `app_settings.general_settings`; no migration) |
| API changes | `/reports/executive` payload: `coverage`, `not_reported`, `currency`, per-currency money, `conflicts` for planned savings |
| Security considerations | The executive endpoint already applies `CardReadScope` and keeps `costs.view` on money. It must not reuse an affected API before its SEC work item passes. |
| Dependencies | D-22 baseline (step 1) before any prototype edit; D-31 for CR-04; D-01 / D-02 / D-05 / D-06 / D-24 approved |
| Acceptance criteria | All CR-xx acceptance criteria met; Overview / Executive / Workspace / Admin totals agree; no monetary total mixes currencies; conflicting planned savings are excluded from totals and listed |
| Deliverables | The four baseline units; 1-2 correctness PRs; tests; CHANGELOG; EN + AR docs |
| Risks | Splitting the CHANGELOG entry; prototype defects surfacing during testing |
| Complexity | M |
| Definition of completion | Merged with green CI including mutation gates; PROGRESS = Completed |

## Phase 2: CEO overview, KPI history, decision intelligence

| Item | Content |
|---|---|
| Objective and scope | Executive secondary navigation; CEO Overview (six measures + decisions panel + pillar strip); Decisions & Escalations page; KPI history and provenance; period and org filters; KPI tile standard |
| Existing components reused | KPI cards, `_kpi_snapshot_loop`, `TrendIndicator`, phase-one tiles and charts, `CardPicker` (hierarchy), AG Grid + `useColumnFreeze`, risk register, ADR / ARB / exceptions |
| Backend changes | `services/executive/` package (context, population, registry, builders TR-01/03/04, GOV-01 fallback, FIN-03/07/09, SVC-02, DEC-01/02), snapshots and period freeze, measurement endpoints |
| Frontend changes | Executive sub-navigation, global header, KPI tile, definition drawer, Overview page, Decisions page, measurement entry on KPI card detail (reusing a card tab) |
| Database changes | **As built (2026-10-25):** one table `kpi_measurements` replacing `kpi_snapshots` (migration `1164`, data copied, D-19 — no separate `metric_snapshots`); `kpi_target_ratifications` (D-17a); partial unique index `uq_cards_kpi_metric_key`; `metricKey` field on the KPI type through NORA profile v11 (D-26). The escalation tag group was withdrawn under D-04. |
| API changes | `/reports/executive/{overview,decisions,portfolio}`, `/reports/executive/kpi/{key}/drilldown`, `/kpis/{id}/measurements`; `/reports/executive` kept as an alias for one release |
| Security considerations | Trends only for unrestricted readers; small-group suppression; `kpis.measure` permission; drill-down parity |
| Dependencies | Phase 1 complete; SEC work items covering every reused API passed CI. **Decided 2026-10-24:** D-03 (no seeded roles; executive permission grants aggregates only), D-04 (existing open definition; automated escalation; manual escalation deferred), D-07 (OrganizationalUnit; **org filter not built until relations and data exist**, new relation types need separate approval), D-17 (KPI cards hold targets; card approval is not owner ratification, so targets show unratified). **Decided 2026-10-25:** D-19, D-21, D-26, D-17a (see `DECISION_LOG.md` §2). **Previously open:** D-19 (KPI history storage — blocks snapshots and measurement history; previous-period values are derived from dated source records where possible), D-21 (strategy progress — blocks TR-01), D-26 (KPI card link — blocks targets and owners on tiles), D-09 (eligible processes — blocks SVC-02), D-20 (small-group suppression — needed with the org filter). Slots 2 and 5 depend on Phases 3 and 4 (D-10, D-13; D-12, D-14, D-15). |
| Acceptance criteria | Overview shows ≤ 6 KPI tiles each with target, delta, as-of and drill-down; missing data shows Not available / Not reported; period and org filters change values; Q-close values frozen; the restricted-reader matrix passes |
| Deliverables | PRs for backend package, history, frontend pages; user docs (Dashboard guide EN + AR); screenshots per the screenshot contract |
| Risks | KPI cards not populated → many "Not available" tiles; org-type ambiguity (D-07) |
| Complexity | L |
| Definition of completion | Merged, documented, CI green; PROGRESS = Completed |

## Phase 3: EA governance effectiveness

Rules: `DECISION_LOG.md` §3.1 (D-10, D-13, D-28, D-32..D-36 approved with changes 2026-10-25; D-11 deferred; details I-7..I-13). Classes are never mixed: **Activity** (governance happened), **Effectiveness** (governance was acted on), **Impact** (contribution to outcomes). Anything without a defensible calculation shows **Not Available** with its reason.

| Item | Content |
|---|---|
| Objective and scope | An EA Governance page in the Executive Dashboard that shows activity, effectiveness and impact apart; delivered in six batches, each usable on its own |
| Existing components reused | Executive router `api/v1/executive_overview.py`, `services/executive/*` (periods, kpis tile contract, linkage, registry), `kpi_measurement_service` daily capture and verification (D-19), `metricKey` linkage (D-26), target ratification (D-17a), `tech_standards_scan.py`, ADR / ARB / exception models, Todo, risk register, `CardReadScope`, `visible_type_clause`, `ExecutiveTab` navigation |
| Security considerations | `reports.executive_dashboard` for aggregates (D-03); record lists need the module permission (`adr.view`, `arb.view`, `tech_standards.view`, `risks.view`); module-mode `CardReadScope` with hidden types excluded before anything is counted (D-01); governance records about hidden cards omitted or redacted as their modules do (D-30); landscape-wide history only for unrestricted readers (I-5) |
| Definition of completion | Every batch: one focused validation pass (its new and directly affected tests only), docs and translations (EN, AR) updated; PROGRESS = Completed only after the owner's commit authorisation |

### Batch sequence

| Batch | Scope | Blocked by | Depends on |
|---|---|---|---|
| **3.1** | Governance page; activity counts; assessment coverage; rule-based standards compliance (GOV-03) with drill-down; GOV-03 registered for daily capture and KPI-card linkage | — (all rules approved) | Phase 2 |
| 3.2 | Auditable transition history for ADR, ARB, exceptions; exception states withdrawn / remediated with verified evidence; GOV-04 exception resolution; GOV-07 elapsed time | D-39 (processing time only), D-40 (remediated only) | 3.1 |
| 3.3 | Business calendar (Sun–Thu default, holiday configuration, validity); GOV-07 working-day figures | D-38 | 3.2 |
| 3.4 | Decision actions on ADR / ARB (Todo source link, owner, due date, evidence); implementation verification; GOV-05 with No Plan; overview tile switches to GOV-05 | D-41 | 3.2 (transition history dates the decisions) |
| 3.5 | Architecture risks from explicit governance links; verified reduction stays Not Available | D-42 | 3.1 |
| 3.6 | GOV-01 review coverage and GOV-09 governed vs ungoverned delivery from approved applicability | D-37 | 3.1 |

Out of Phase 3: GOV-02 early engagement (D-11 deferred); repeat violations (needs per-card compliance history); business and financial impact (Phase 4).

### Batch 3.1 — Governance page, activity, coverage, rule-based compliance

| Item | Content |
|---|---|
| Backend | `services/tech_standards_scan.py`: add the assessed population (I-8) beside the existing violations, same chain, same hidden-path cuts, existing `/tech-standards/compliance-scan` response unchanged. New `services/executive/governance.py`: **activity** for the selected period: ADRs signed (`signed_at` in period), ARB approved / rejected by latest decision date (I-12) with deferred apart, exceptions by current state (requested, approved active, expired, rejected) labelled current-state; withdrawn / remediated shown Not Available until 3.2. **Effectiveness**: GOV-03 compliance (I-9) and assessment coverage (I-10) as two figures, Unavailable per I-11; GOV-04, GOV-05, GOV-07 Not Available with their blocking decision. **Impact**: architecture risks, GOV-09, business value Not Available with reasons. `api/v1/executive_overview.py`: `GET /reports/executive/governance?period=`; drill-down `GET /reports/executive/kpi/GOV-03/drilldown` (needs `tech_standards.view`). `services/executive/registry.py`: `GOV-03` (percent, `GOV-03@1`). `kpi_measurement_service.observe_executive_metrics`: GOV-03 observation (numerator compliant, denominator assessed). `services/nora_profile.py`: profile v12 pass appending the `GOV-03` option to `KPI.metricKey` when missing (additive, admin labels untouched) |
| Frontend | `features/dashboard/executive/ExecutiveGovernance.tsx` (three labelled sections, tile contract of `ExecutiveKpiTile`, Not Available reasons, drill-down list); `ExecutiveTab.tsx` page `governance`; overview governance tile links to it (I-7); types in `src/types/index.ts`; keys under `dashboard.executive.governancePage.*` in `en/common.json` and `ar/common.json`; `routePermissions` unchanged (same tab) |
| Database | None. No migration; no workspace-transfer change |
| Tests | `backend/tests/services/test_executive_governance.py` (activity dating, deferred apart, coverage vs compliance, expired waiver = violation, Unavailable cases); `backend/tests/services/test_tech_standards_scan.py` (population, hidden path cut); `backend/tests/api/test_executive_governance_api.py` (403 without `reports.executive_dashboard`; hidden card absent from every count; drill-down 403 without `tech_standards.view`; invalid period 422); capture test for GOV-03; Vitest `ExecutiveGovernance.test.tsx` (class labels, Not Available, wording never "architecture compliance") |
| Docs | `docs/guide/dashboard.md` Executive section (EN; AR sibling); CHANGELOG + VERSION minor bump; PROGRESS / RTM rows P3-01, P3-04 |
| Acceptance | Activity, Effectiveness, Impact rendered as separate labelled sections; compliance and coverage are separate figures; compliance is labelled rule-based technology standards compliance; no figure without a defensible calculation (Not Available + reason); a card the viewer cannot read changes no count; GOV-03 daily observations start with no backfill; a KPI card can carry `metricKey = GOV-03` and the tile shows its ratified target only |

### Batch 3.2 — Transition history, exception lifecycle, GOV-04, GOV-07 elapsed

> **Status 2026-10-26 (v2.38.0): implemented.** Transition history, exception `decided_at`, GOV-07 elapsed (I-14..I-19); after D-39 / D-40 were approved the same day: governance-controlled processing time, the remediation / withdrawal lifecycle, audited hard delete and GOV-04 (I-20..I-28). Database tests Pending Verification. Batch 3.3 not started.

| Item | Content |
|---|---|
| Backend | Transition events on every status change: ARB (`api/v1/arb.py`), exceptions (`api/v1/tech_standards.py`), ADR (verify the existing `adr.py` events cover draft → in_review → signed and revisions). Exception states `withdrawn`, `remediated` (verified evidence, verifier per D-40); expiry never resolves. GOV-04 counts only exceptions whose lifecycle is recorded; GOV-07 elapsed calendar days per instrument; processing time after D-39 |
| Database | Migration on `tech_standard_exceptions` (decision / withdrawal / remediation timestamps, actors, evidence); `server_default=sa.func.now()` on any timestamp column; **workspace-transfer checklist** (`.claude/rules/workspace-transfer.md`) |
| Acceptance | No history manufactured for earlier records (shown "lifecycle not recorded"); deferred is never final; an expired waiver with the violation still present counts as unresolved |

### Batch 3.3 — Business calendar

| Item | Content |
|---|---|
| Backend / frontend | Calendar configuration (working week, holidays per fiscal year, confirmation) in admin settings; working-day function; GOV-07 working-day variant Not Available while the period is not valid (D-28, D-38) |
| Acceptance | Sun–Thu default; a period touching an unconfirmed year yields no working-day figure |

### Batch 3.4 — Decision actions and implementation verification

| Item | Content |
|---|---|
| Backend | Todo source link (`source_kind`, `source_id`, index), owner and due date required for decision actions, evidence per D-41; `/adr/{id}/actions`, `/arb/{id}/actions`; verification record; GOV-05 implemented / not yet verified / No Plan / overdue against the approved implementation due date |
| Database | Migration (todo columns; verification table; implementation due date field per D-41); workspace-transfer id-bearing rewrite for the source link |
| Frontend | Actions panel on ADR preview and ARB detail reusing the todo UI; GOV-05 tile on overview and Governance page |
| Acceptance | `GOVERNANCE_MEASUREMENT_MODEL.md` §6 GOV-05 end-to-end test (signed → actions → evidence → independent verification → implemented); a self-verification is refused |

### Batch 3.5 — Architecture risks

Explicit risk ↔ governance-record links (D-42); counts of linked open risks by residual level; verified reduction Not Available.

### Batch 3.6 — Review coverage and governed delivery

Applicability per D-37; GOV-01 over initiatives assessed as requiring review; GOV-09 cohorts with sizes, suppressed below 5 per cohort, "contribution, not causation".

## Phase 4: Business impact, benefits realisation, ROI

| Item | Content |
|---|---|
| Objective and scope | Benefits register with workflow; Financial & ROI page; Business Impact page; full traceability view |
| Existing components reused | Rationalization decisions, initiatives / PPM, improvement opportunities, risks, KPI cards and measurements, documents / attachments, audit log, events, TurboLens duplicates, EOL service, gap analysis |
| Backend changes | `benefit_service.py` (transitions, segregation of duties, dedupe checks); financial and impact builders (FIN-01..10, IMP-01..08); traceability endpoint; `realized_at` on opportunities |
| Frontend changes | Benefits register table + benefit drawer (status stepper, evidence), Financial page, Impact page, traceability view |
| Database changes | `benefits`, `benefit_cards`, `benefit_evidence`; `improvement_opportunities.realized_at`; `roiScope` tag group (data) |
| API changes | `/benefits*`, `/reports/executive/{financial,impact}`, `/reports/executive/traceability/...` |
| Security considerations | `benefits.*` permissions; Finance-only confirm; segregation of duties (D-29); money behind `costs.view`; audit-log kinds added in all locales |
| Dependencies | Phase 2; Phase 3 Batch 3.4 for decision actions (implementation evidence); D-12, D-14, D-15, D-16, D-29 |
| Acceptance criteria | `BENEFITS_AND_ROI_SPECIFICATION.md` §8 criteria; IMP-01 decided-vs-executed correct on fixtures |
| Deliverables | PRs, tests, user docs (new Benefits guide page EN + AR + nav), glossary terms |
| Risks | Finance process not ready → register empty; attribution method not approved → ROI stays Not available (by design) |
| Complexity | L |
| Definition of completion | Merged and documented; PROGRESS = Completed |

## Phase 5: Digital transformation, services, processes, maturity, portfolio intelligence

| Item | Content |
|---|---|
| Objective and scope | Transformation page (TR-01..06, DEC-04); Services & Automation page (SVC-01..06); Portfolio Health page (PRT-01..05); DEC-03/05 |
| Existing components reused | Strategy cascade, maturity overview radar, PPM WBS milestones, GovService, BusinessProcess / BPM, process assessments, channels, EOL report, app portfolio, LayeredDependencyView |
| Backend changes | Remaining builders; milestone derivation from WBS; service-digitalization derivation |
| Frontend changes | Three pages; relocation of phase-one portfolio charts |
| Database changes | `GovService.digitalizationLevel` (seed + guarded migration) **or** `deliveryChannel` canonicalisation (D-08); optionally `roadmap_milestones.achieved_at` / `status` (D-25) |
| API changes | `/reports/executive/{transformation,services}`; portfolio endpoint completed |
| Security considerations | As Phase 2; maturity indicators and integration-status already scoped by the security track (WI-9, WI-15) |
| Dependencies | Phase 2; data populated (GovService, maturity, pillars); D-08, D-09, D-16, D-25 |
| Acceptance criteria | SVC-01 and SVC-02 shown separately with Not assessed / Unknown; TR-02 matches WBS milestones; Portfolio page holds all relocated specialist measures |
| Deliverables | PRs, tests, docs |
| Risks | GovService definition drift (seed vs NORA profile); thin data |
| Complexity | M-L |
| Definition of completion | Merged and documented; PROGRESS = Completed |

## Phase 6: Executive reporting, bilingual validation, accessibility, final QA

| Item | Content |
|---|---|
| Objective and scope | Board-pack export; summary sentence band (rule-based; AI optional per D-23); accessibility pass; bilingual RTL visual QA; performance hardening; screenshots and docs |
| Existing components reused | `loadReportExport` (PPTX / XLSX), saved reports, `scripts/screenshots/` Playwright capture, Playwright e2e suite (`frontend/e2e/`) |
| Backend changes | Insight rules; optional caching; export audit |
| Frontend changes | Export actions, `role="img"` + "view as table", keyboard focus, RTL fixes found in QA |
| Database changes | None expected |
| API changes | Export endpoints if server-side generation is chosen |
| Security considerations | Export parity and auditing (SR-05); AI insight receives only the caller-scoped payload |
| Dependencies | Phases 2-5 |
| Acceptance criteria | WCAG 2.1 AA checks pass on executive pages; Arabic RTL review signed off by a native-speaker stakeholder; p95 ≤ 2 s at 50k cards on the benchmark dataset; e2e smoke spec for the Executive pages; screenshots in docs (EN + AR) |
| Deliverables | PRs, QA report, final user guide, release notes |
| Risks | Late RTL defects; export fidelity in Arabic |
| Complexity | M |
| Definition of completion | Sign-off by the executive sponsor; PROGRESS = Completed |
