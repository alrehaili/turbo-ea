# Decision review package

**Purpose.** The final business decision package for the 30 open decisions in `DECISION_LOG.md`, to be reviewed before development begins.
> **Update 2026-10-22.** D-01, D-02, D-05, D-06, D-18, D-22, D-24 and D-30 have since been approved (see `DECISION_LOG.md` §2). This package is kept as the review record.

**Status.** Documentation only. **No decision in this package is approved.** Every "Recommended" entry is the planner's proposal and awaits the named owner's approval. Nothing has been implemented.
**Date:** 2026-10-22

**Sources:** `DECISION_LOG.md`, `PHASED_DELIVERY_PLAN.md`, `FINAL_KPI_DICTIONARY.md`, `DATA_MODEL_AND_RELATIONSHIPS.md`, `SECURITY_REMEDIATION_PLAN.md`, `BENEFITS_AND_ROI_SPECIFICATION.md`, `GOVERNANCE_MEASUREMENT_MODEL.md`, `UI_UX_SPECIFICATION.md`, and the project conventions in `CLAUDE.md`.

---

## 1. Summary

| Measure | Count |
|---|---|
| Open decisions | **30** (D-01 to D-30) |
| Phase-blocking (marked **B** in the log) | **15**: D-01, D-02, D-03, D-04, D-05, D-07, D-08, D-10, D-12, D-13, D-14, D-15, D-17, D-22, D-30 |
| Must be resolved **before Phase 1** | **7**: D-01, D-02, D-05, D-06, D-22, D-24, D-30 (five are blocking; D-06 and D-24 are needed by Phase 1 work but are non-blocking confirmations) |
| Needed before Phase 2 (Phase 0 deliverables) | D-03, D-04, D-07, D-17 (blocking); D-09, D-18, D-19, D-20, D-21, D-26, D-27 (non-blocking) |
| Can wait for Phases 3-6 | D-08, D-10, D-11, D-12, D-13, D-14, D-15, D-16, D-23, D-25, D-28, D-29 |
| Resolvable through **existing project conventions** without new business policy | 8 fully or partly: D-01 (partly), D-06, D-13, D-18 (partly), D-19, D-22 (partly), D-26, D-30. See §3. |

### Groups

| Group | Decisions |
|---|---|
| A. Executive / business | D-02, D-03, D-04, D-08, D-09, D-17, D-21, D-22, D-25 |
| B. EA governance | D-01, D-07, D-10, D-11, D-13, D-16, D-28 |
| C. Financial and ROI | D-05, D-06, D-14, D-15, D-24, D-29 |
| D. Technical and security | D-12, D-19, D-20, D-26, D-30 |
| E. UI/UX | D-18, D-23, D-27 |

---

## 2. Decisions in detail

Each entry gives: what must be decided · why it matters · options · recommended option and justification · consequences and dependencies · phase blocked · convention status.

### A. Executive / business decisions

#### D-02: Source of truth for initiative health, and the "Not reported" window **[B: Phase 1]**

- **Decide**: which record defines an initiative's delivery state, and how old a status report may be before the initiative counts as "Not reported".
- **Why it matters**: today the Executive tab shows "0 of 20 off track" while 14 of 20 initiatives have no report (CR-01). Two sources disagree: `ppm_status_reports` and `Initiative.attributes.initiativeStatus` (`FINAL_KPI_DICTIONARY.md` §2).
- **Options**:
  - (a) PPM status reports when the PPM module is on, else `initiativeStatus`;
  - (b) always `initiativeStatus`;
  - (c) always PPM reports.
  - Window: 30, 35 or 45 days.
- **Recommended**: (a) with a **35-day** window. PPM reports carry schedule, cost and scope separately, so they are the richer source, and the fallback keeps installs without PPM working. 35 days tolerates a monthly reporting cycle with a short delay.
- **Consequences / dependencies**: defines CR-01 / CR-02, TR-03 and TR-04. A shorter window raises "Not reported" counts. Under (b), schedule / cost / scope detail is lost.
- **Blocks**: Phase 1 (correctness fix).
- **Convention**: no. A PMO policy choice.

#### D-03: Role grants for the executive and benefit permissions **[B: Phase 2]**

- **Decide**: who receives `reports.executive_dashboard`, `benefits.view/manage/validate/confirm` and `kpis.measure`; whether to create default "Executive" and "Finance" roles.
- **Why it matters**: these control who sees executive and financial information. The phase-one key is admin-only today (wildcard).
- **Options**:
  - (a) new "Executive" and "Finance" roles, existing roles unchanged;
  - (b) grant to existing roles (member / viewer);
  - (c) admin-only until requested.
- **Recommended**: (a). Least privilege; no silent widening of existing roles; matches CLAUDE.md "Authorization must match RBAC and the UI".
- **Consequences / dependencies**: a seed or migration creates roles (data, not code). Depends on D-29 (segregation of duties for confirm).
- **Blocks**: Phase 2.
- **Convention**: partly. Least privilege is a convention; who gets access is business policy.

#### D-04: "Open risk" definition and the escalation mechanism **[B: Phase 2]**

- **Decide**: which risk statuses count as open, and how a risk is marked as needing executive escalation.
- **Why it matters**: drives the landing-page measure DEC-01 and the decisions list. Today "open" excludes only `closed` / `accepted`, so it includes `mitigated` and `monitoring`.
- **Options**:
  - Definition: (a) keep the current one, showing "unmitigated" separately; (b) exclude mitigated and monitoring.
  - Mechanism: (c) an "Escalation" tag group (no schema change); (d) new risk fields (`escalation_status`, `escalated_to`).
- **Recommended**: (a) + (c). It keeps continuity with the risk register's KPIs. A tag group needs no migration, and admins can change it.
- **Consequences / dependencies**: (d) needs a migration plus workspace-transfer work. Criteria for DEC-01 (critical, or high and overdue, or tagged) depend on this.
- **Blocks**: Phase 2.
- **Convention**: no. A CRO policy choice.

#### D-08: Service digitalization source and the canonical GovService definition **[B: Phase 5]**

- **Decide**:
  1. how a service is classified Digital / Hybrid / Manual;
  2. which GovService definition is canonical: `seed.py:4840` or `nora_profile.py:4462`.
- **Why it matters**: confirmed decision C-10 requires service digitalization to be separate from process automation. The live type has `automationLevel` but no digitalization field, and the NORA profile's `deliveryChannel` was never applied.
- **Options**:
  - (a) new single-select `digitalizationLevel`;
  - (b) derive from the multi-select `deliveryChannel`;
  - (c) reuse `GovService.automationLevel`, which conflates the two concepts and contradicts C-10.
- **Recommended**: (a), with the NORA profile as the canonical definition. An explicit owner-maintained field is auditable; derivation from channels needs a classification rule nobody has agreed.
- **Consequences / dependencies**: (a) is a metamodel field via seed plus a guarded migration (CLAUDE.md built-in default rule). Reconciling the two definitions may touch both seed files. Data population is needed (0 GovService records today).
- **Blocks**: Phase 5.
- **Convention**: no. The Digital Office defines "digital".

#### D-09: Eligible processes for automation KPIs, and the automation threshold

- **Decide**: which BusinessProcess cards are counted (hierarchy subtypes: category / group / process / variant) and what level counts as "automated".
- **Why it matters**: counting categories and groups alongside processes double-counts the hierarchy and distorts SVC-02 / SVC-03.
- **Options**:
  - (a) subtype `process` only, active only;
  - (b) all subtypes;
  - (c) leaf nodes only.
- **Recommended**: (a). Processes are the unit owners assess; categories are containers.
- **Consequences / dependencies**: processes without a subtype need a rule (proposal: counted as `process`). Missing `automationLevel` is shown as "Unknown" (C-10).
- **Blocks**: none (Phase 2 needs it for the landing-page automation figure).
- **Convention**: no.

#### D-17: KPI target values **[B: Phase 0, for release-1 KPIs]**

- **Decide**: approve or replace each proposed target in `FINAL_KPI_DICTIONARY.md` §3 (all marked "proposal").
- **Why it matters**: targets drive status colour and the executive read-out. A wrong target misleads.
- **Options**:
  - (a) owners ratify per KPI;
  - (b) launch without targets (neutral status) and add them later;
  - (c) accept the proposals as-is.
- **Recommended**: (a) for the six landing KPIs and Phase 1-2 KPIs. Others under (b) until their phase. Targets are management commitments, not planner choices.
- **Consequences / dependencies**: stored on KPI cards (C-02). Requires KPI cards to exist and owners to be appointed.
- **Blocks**: Phase 0 completion; practically needed before Phase 2 ships tiles.
- **Convention**: no.

#### D-21: Strategy progress source

- **Decide**: whether `Objective.progress` is entered manually or computed from linked KPIs.
- **Why it matters**: TR-01, the first landing measure, depends on it.
- **Options**:
  - (a) manual v1, computed later;
  - (b) computed now from `relObjectiveToKPI` KPIs.
- **Recommended**: (a). There are no KPI cards or objective-KPI links today (0 rows), so a computed index would be empty.
- **Consequences / dependencies**: manual values are medium confidence and need an update discipline (Strategy Office).
- **Blocks**: none (Phase 2).
- **Convention**: no.

#### D-22: Commit the uncommitted phase-one work as the Phase 1 baseline **[B: Phase 1]**

- **Decide**: whether the uncommitted phase-one Executive tab, the Windows `os.pread` fix and the narrow-screen navigation change become the Phase 1 baseline.
- **Why it matters**: Phase 1 corrections modify that code. Leaving it uncommitted risks loss and an untraceable baseline.
- **Options**:
  - (a) commit with tests in Phase 1;
  - (b) discard the prototype and rebuild in Phase 2;
  - (c) commit the unrelated fixes separately and the prototype in Phase 1.
- **Recommended**: (c). The Windows fix and the navigation change are unrelated to the dashboard and are easier to review alone; the prototype is the base Phase 1 corrects.
- **Consequences / dependencies**: requires tests per C-14 (the earlier "no tests" instruction applied to the prototype only); a CHANGELOG / VERSION decision (currently 2.32.0 in the working tree).
- **Blocks**: Phase 1.
- **Convention**: partly. Tests, changelog and one version bump per PR are conventions; whether to keep the prototype is a product decision.

#### D-25: Roadmap milestone achievement source

- **Decide**: where "milestone achieved" comes from for TR-02.
- **Why it matters**: `roadmap_milestones` has only `target_date`, so achievement cannot be measured today.
- **Options**:
  - (a) derive from PPM WBS milestones (`is_milestone`, `completion`, `end_date`);
  - (b) add `achieved_at` / `status` to `roadmap_milestones`;
  - (c) both: derive where linked, fields for roadmap-only milestones.
- **Recommended**: (c), deriving first. It reuses existing PPM data (no duplicate entity).
- **Consequences / dependencies**: (b) and (c) need a migration and workspace transfer. 0 milestones exist today.
- **Blocks**: none (Phase 5).
- **Convention**: partly. "Reuse before build" favours deriving.

### B. EA governance decisions

#### D-01: Exclude hidden card types from landscape totals **[B: Phase 1]**

- **Decide**: whether cards of card types an admin has hidden count in dashboard totals.
- **Why it matters**: today Overview and Executive include them (118 of 391 demo cards), My Workspace and Admin exclude them, so totals disagree across tabs (CR-06).
- **Options**:
  - (a) exclude everywhere;
  - (b) include everywhere;
  - (c) admin setting.
- **Recommended**: (a). Hidden means retired from the metamodel. Two existing endpoints already exclude them (`reports.py:365`, `:407`), which makes (a) the established precedent.
- **Consequences / dependencies**: Overview and Executive totals drop for installs with hidden types in use; this is a visible change (CHANGELOG). The demo data relies on hidden types (Organization, ITComponent and others), which interacts with D-07.
- **Blocks**: Phase 1.
- **Convention**: partly. The existing precedent supports (a); it is not a documented rule.

#### D-07: Organisation filter type **[B: Phase 2]**

- **Decide**: which card type represents organisations / departments for the filter.
- **Why it matters**: the NORA profile hides `Organization`, yet the demo relations use it (`relOrgToInitiative`, `relOrgToApp`), while NORA relations use `OrganizationalUnit`.
- **Options**:
  - (a) an admin setting naming the org type;
  - (b) fixed `OrganizationalUnit`;
  - (c) fixed `Organization`.
- **Recommended**: (a), with a data migration plan if an install switches. It keeps the metamodel data-driven (CLAUDE.md) and works for NORA and non-NORA installs.
- **Consequences / dependencies**: the filter maps populations through relation types keyed by type (CLAUDE.md multi-relation rule). Under D-01 (a), choosing a hidden type is invalid, so a setting must reject it.
- **Blocks**: Phase 2.
- **Convention**: partly. The data-driven metamodel principle supports a setting; the choice itself is business.

#### D-10: EA review "in scope" rule **[B: Phase 3]**

- **Decide**: which initiatives must receive EA review (the GOV-01 denominator).
- **Why it matters**: without a rule, review coverage has no denominator.
- **Options**:
  - (a) subtype program or project, plus FY budget ≥ an admin threshold;
  - (b) all initiatives;
  - (c) a tag `eaReviewRequired`.
- **Recommended**: (a) plus (c) as a manual override. Proportional governance; the threshold is a setting, not code.
- **Consequences / dependencies**: needs PPM budget data (or `costBudget`), and depends on D-02 for the source of truth.
- **Blocks**: Phase 3.
- **Convention**: no.

#### D-11: Early-engagement gate

- **Decide**: what event counts as "before investment / design" for GOV-02.
- **Why it matters**: early EA involvement is the strongest governance-value signal.
- **Options**:
  - (a) ADM Architecture Vision approval;
  - (b) `Initiative.startDate`;
  - (c) a new investment-gate status.
- **Recommended**: (a), falling back to (b). It reuses ADM (`adm_phases.approved_at`) with no new entity.
- **Consequences / dependencies**: 0 ADM workspaces today, so the fallback will dominate initially.
- **Blocks**: none (Phase 3).
- **Convention**: partly. "Reuse before build" favours (a).

#### D-13: Decision implementation actions **[B: Phase 3]**

- **Decide**: how ADR / ARB decisions carry implementation actions.
- **Why it matters**: without actions, decision implementation (GOV-05) cannot be measured.
- **Options**:
  - (a) extend `todos` with `source_kind` / `source_id`;
  - (b) a new decision-action table;
  - (c) reuse the risk mitigation-task pattern.
- **Recommended**: (a). Todos already have assignee, due date, status, notifications and the extension bridge, so no duplicate tasking system is needed (confirmed decision C-02).
- **Consequences / dependencies**: migration, plus a workspace-transfer id-bearing rewrite for `source_id`.
- **Blocks**: Phase 3.
- **Convention**: yes. C-02 ("no duplicate entities") and the reuse convention lead to (a).

#### D-16: Technology debt index components and weights

- **Decide**: the components and weighting of IMP-03.
- **Why it matters**: no uniform debt score exists; the composite must be explainable.
- **Options**:
  - (a) equal weights across vendor-support expired, past planned EOL, technically unsuitable, and active exception;
  - (b) risk-weighted by business criticality;
  - (c) defer IMP-03.
- **Recommended**: (a) for v1, reviewed after one quarter. It is simple and transparent in the definition drawer.
- **Consequences / dependencies**: needs a frozen baseline snapshot (D-19).
- **Blocks**: none (Phase 4).
- **Convention**: no. CTO policy.

#### D-28: Working-day calendar for governance turnaround

- **Decide**: which days count as working days for GOV-07.
- **Why it matters**: turnaround in working days must reflect the organisation's week.
- **Options**:
  - (a) Sunday-Thursday, no holiday table;
  - (b) Monday-Friday;
  - (c) configurable, with a holiday table.
- **Recommended**: (a) as the default, configurable later. This matches the bilingual Arabic-locale deployment.
- **Consequences / dependencies**: (c) adds a settings model.
- **Blocks**: none (Phase 3).
- **Convention**: no.

### C. Financial and ROI decisions

#### D-05: Instance currency and multi-currency **[B: Phase 1]**

- **Decide**: the reporting currency and whether amounts in other currencies are converted.
- **Why it matters**: CR-05 requires SAR formatting. The setting defaults to USD (`settings.py:73`). SAR is supported via the U+20C1 glyph (`frontend/src/lib/currency.ts`).
- **Options**:
  - (a) SAR single currency, no conversion;
  - (b) multi-currency with exchange rates.
- **Recommended**: (a). Every existing cost field is a bare number in the instance currency, so conversion would need rate management and per-amount currency on every cost field.
- **Consequences / dependencies**: an admin sets the currency to SAR; benefits store `currency` = instance currency; no FX. Existing amounts are assumed to already be SAR, which **must be confirmed by Finance**.
- **Blocks**: Phase 1.
- **Convention**: no. A CFO choice; the mechanism exists.

#### D-06: Fiscal year start

- **Decide**: confirm the existing fiscal-year-start setting for all executive KPIs.
- **Why it matters**: every period figure (CR-03 budget execution and others) depends on it.
- **Options**:
  - (a) use the configured setting (`fiscal_year.get_fiscal_year_start`);
  - (b) a separate executive fiscal calendar.
- **Recommended**: (a). One fiscal definition across cost reports and the dashboard (CLAUDE.md cost-report rule).
- **Consequences / dependencies**: Finance confirms the configured month. Naming follows "year named after the calendar year it ends in".
- **Blocks**: none, but needed by Phase 1 work.
- **Convention**: yes. Existing convention and setting.

#### D-14: Attribution method (no fixed percentages) **[B: Phase 4]**

- **Decide**: how a realised benefit is attributed to EA, given confirmed decision C-07 (no arbitrary fixed percentages).
- **Why it matters**: it determines whether any "EA contribution" or EA-ROI figure is defensible.
- **Options**:
  - (a) the per-benefit method enum (`full_transformation` default, `ea_decisive`, `ea_contributing`, `not_attributable`), with a Finance-assessed amount and rationale (`BENEFITS_AND_ROI_SPECIFICATION.md` §5);
  - (b) report transformation benefits only, never an EA share;
  - (c) evidence classification without amounts.
- **Recommended**: (a). It complies with C-07, keeps Finance accountable, and still allows (b) as the default behaviour.
- **Consequences / dependencies**: Finance workload per benefit. EA-ROI stays "Not available" until applied. Depends on D-12 and D-29.
- **Blocks**: Phase 4.
- **Convention**: no.

#### D-15: ROI programme-cost scope and window **[B: Phase 4]**

- **Decide**: which costs form the ROI denominator, and over which period.
- **Why it matters**: confirmed decision C-08 requires comparable costs over the same period; an undefined scope makes ROI arbitrary.
- **Options**:
  - Scope: (a) initiatives tagged `roiScope`; (b) all transformation initiatives; (c) plus EA office cost.
  - Window: FY only, or FY plus a rolling 3-FY window.
- **Recommended**: (a) plus an explicit inclusion decision on EA office cost, with FY plus an optional rolling 3-FY window. Benefits often lag costs, so a single FY understates ROI.
- **Consequences / dependencies**: tagging discipline. The EA office cost needs a source (it is not modelled today).
- **Blocks**: Phase 4.
- **Convention**: no.

#### D-24: Planned-savings dedupe rule

- **Decide**: how an application in several rationalization assessments contributes to planned savings.
- **Why it matters**: today its savings are summed once per assessment (CR-04).
- **Options**:
  - (a) latest decision per application across active and completed assessments;
  - (b) completed assessments only;
  - (c) highest value.
- **Recommended**: (a). It reflects the current intent and avoids inflation.
- **Consequences / dependencies**: superseded by a linked benefit once the register exists (Phase 4).
- **Blocks**: none, but needed by Phase 1 work.
- **Convention**: no. Owner: app portfolio owner.

#### D-29: Segregation of duties for benefit confirmation

- **Decide**: whether the creator or estimator of a benefit may also validate or confirm it.
- **Why it matters**: realised savings must be credible to the CFO and to auditors.
- **Options**:
  - (a) creator or estimator cannot confirm;
  - (b) no restriction;
  - (c) a different person at each status step.
- **Recommended**: (a). Standard financial control; minimal friction.
- **Consequences / dependencies**: server-side enforcement; requires at least two Finance users.
- **Blocks**: none (Phase 4).
- **Convention**: no.

### D. Technical and security decisions

#### D-12: Benefit storage **[B: Phase 4]**

- **Decide**: dedicated tables or a `Benefit` card type.
- **Why it matters**: the benefits register needs Finance-only transitions, typed money arithmetic and evidence.
- **Options**:
  - (a) dedicated `benefits` + `benefit_cards` + `benefit_evidence` tables;
  - (b) a `Benefit` card type (inherits stakeholders, comments, history, approval, workspace transfer).
- **Recommended**: (a). Card attributes have no field-level permission control for Finance-only status changes, and ROI needs typed columns. (b) remains viable if the CFO prefers card-based collaboration.
- **Consequences / dependencies**: (a) needs migrations, a workspace-transfer section and new permissions. (b) needs only seed data but weaker controls.
- **Blocks**: Phase 4.
- **Convention**: partly. The data-driven metamodel favours (b); security needs favour (a). Approval required.

#### D-19: Snapshot storage

- **Decide**: replace `kpi_snapshots` (4 fixed columns) with a key/value `metric_snapshots`, or keep both.
- **Why it matters**: trends and frozen periods need flexible history.
- **Options**:
  - (a) replace and migrate the 4 columns into rows;
  - (b) keep both.
- **Recommended**: (a). One history mechanism, no duplication.
- **Consequences / dependencies**: Overview trend code is switched to the new table in the same change.
- **Blocks**: none (Phase 2).
- **Convention**: yes. Engineering choice under the "no duplication" convention.

#### D-20: Small-group suppression threshold

- **Decide**: the minimum group size below which filtered aggregates are hidden from restricted readers.
- **Why it matters**: an org filter can reveal individual values (e.g. one application's cost) through small groups.
- **Options**: (a) n < 3; (b) n < 5; (c) no suppression.
- **Recommended**: (a). The common minimum that still keeps small departments usable.
- **Consequences / dependencies**: applies only to restricted readers with an org filter.
- **Blocks**: none (Phase 2).
- **Convention**: no. Security / data-protection policy.

#### D-26: KPI card ↔ builder link

- **Decide**: how a KPI card is linked to its calculation function.
- **Why it matters**: targets and owners on the card must be found by the matching builder.
- **Options**:
  - (a) a new `metricKey` text field on the KPI type;
  - (b) `cards.external_id`.
- **Recommended**: (a). `external_id` is owned by import and ServiceNow paths, so reusing it would collide.
- **Consequences / dependencies**: metamodel field via seed plus a guarded migration.
- **Blocks**: none (Phase 2).
- **Convention**: yes. Existing ownership of `external_id` and the built-in metamodel migration rule decide it.

#### D-30: Single-subject governance records about hidden cards **[B: Phase 1]**

- **Decide**: how ARB reviews, standard exceptions and rationalization decisions whose subject card is unreadable are treated.
- **Why it matters**: these records currently expose hidden card names (S-03, S-04, S-06).
- **Options**:
  - (a) omit from lists, 404 on detail;
  - (b) keep the record and redact the reference.
- **Recommended**: (a). CLAUDE.md: "a card the caller may not read does not exist for them … a single hidden card is 404". Multi-card records follow the ADR pattern (keep the record, drop hidden links).
- **Consequences / dependencies**: some users will see fewer governance records. Governance counts follow subject readability.
- **Blocks**: Phase 1.
- **Convention**: yes. Fully determined by the existing `CardReadScope` rule; recorded here for transparency.

### E. UI/UX decisions

#### D-18: Translation scope for new strings

- **Decide**: EN / AR only, or all 10 supported locales.
- **Why it matters**: CLAUDE.md requires all 10 locales for new strings; you earlier asked for EN / AR only for the prototype.
- **Options**:
  - (a) EN / AR during build, the other 8 before the release that exposes them;
  - (b) EN / AR only permanently (others fall back to English);
  - (c) all 10 in every PR.
- **Recommended**: (a). Respects the project convention at release while keeping build velocity.
- **Consequences / dependencies**: the i18n parity test may require the keys in all locales at commit time. Confirm whether CI enforces this before choosing (b).
- **Blocks**: none (Phase 2).
- **Convention**: partly. The convention says all 10; the timing is a product choice.

#### D-23: Summary insights

- **Decide**: rule-based or AI-assisted narrative on the landing page.
- **Options**:
  - (a) rule-based;
  - (b) AI-assisted, scope-safe;
  - (c) none.
- **Recommended**: (a) in Phase 2; (b) optional in Phase 6. It is deterministic and auditable, and needs no LLM configuration.
- **Consequences / dependencies**: (b) must pass only the caller-scoped payload (TurboLens precedent).
- **Blocks**: none (Phase 6).
- **Convention**: no.

#### D-27: Arabic numerals

- **Decide**: Arabic-Indic digits (the `ar` locale default) or Latin digits in the Arabic UI.
- **Why it matters**: executive readability and consistency with exports.
- **Options**:
  - (a) locale default (Arabic-Indic);
  - (b) Latin digits (`numberingSystem: "latn"`).
- **Recommended**: stakeholder preference. No technical constraint either way.
- **Consequences / dependencies**: applies to the shared formatter and the PPTX export.
- **Blocks**: none (Phase 2).
- **Convention**: no.

---

## 3. Decisions resolvable through existing conventions

These need **acknowledgement, not new policy**. They remain open until the owner acknowledges them.

| ID | Convention that determines the answer | Residual choice |
|---|---|---|
| D-06 | Existing fiscal-year setting and cost-report rule (CLAUDE.md) | Finance confirms the configured month |
| D-13 | C-02 (no duplicate entities), reuse convention | None |
| D-19 | No-duplication convention | None |
| D-26 | `external_id` ownership; built-in metamodel migration rule | None |
| D-30 | `CardReadScope` "omit entirely / 404" rule | None |
| D-01 (partly) | Precedent in `/reports/my-workspace` and `/reports/admin-dashboard` | Confirm that the precedent becomes the rule |
| D-18 (partly) | CLAUDE.md: all 10 locales | Timing (build vs release) |
| D-22 (partly) | Tests, changelog, one version bump per PR (C-14) | Keep or discard the prototype; split the unrelated fixes |

## 4. Timing

**Must be resolved before Phase 1 starts**: D-01, D-02, D-05, D-06, D-22, D-24, D-30. Of these, D-06 and D-30 are convention-determined and D-01 is largely precedent-determined. The genuinely new policy choices are **D-02, D-05, D-22 and D-24**.

**Phase 0 deliverables needed before Phase 2**: D-03, D-04, D-07, D-17 (blocking), plus D-09, D-18, D-19, D-20, D-21, D-26, D-27.

**Can wait**: Phase 3 (D-10, D-11, D-13, D-28); Phase 4 (D-12, D-14, D-15, D-16, D-29); Phase 5 (D-08, D-25); Phase 6 (D-23).

---

## 5. Decision table for review

All entries are **Open**. "Conv." = resolvable by existing convention (Y / Partly / N).

| ID | Group | Decision | Recommended (proposal) | Owner | Blocks | Needed by | Conv. |
|---|---|---|---|---|---|---|---|
| D-01 | Governance | Hidden card types in totals | Exclude everywhere | Chief Architect | **Ph 1** | Pre-Ph 1 | Partly |
| D-02 | Business | Initiative health source + window | PPM reports (fallback `initiativeStatus`), 35 days | PMO | **Ph 1** | Pre-Ph 1 | N |
| D-03 | Business | Role grants for new permissions | New Executive + Finance roles | CEO office + Chief Architect | **Ph 2** | Ph 0 | Partly |
| D-04 | Business | Open-risk definition + escalation | Keep definition; Escalation tag group | CRO | **Ph 2** | Ph 0 | N |
| D-05 | Financial | Currency | SAR single currency, no FX | CFO | **Ph 1** | Pre-Ph 1 | N |
| D-06 | Financial | Fiscal year start | Use the existing setting | CFO | — | Pre-Ph 1 | Y |
| D-07 | Governance | Organisation filter type | Admin setting (org type) | Chief Architect | **Ph 2** | Ph 0 | Partly |
| D-08 | Business | Service digitalization source; canonical GovService | New `digitalizationLevel`; NORA definition canonical | Digital Office | **Ph 5** | Ph 5 | N |
| D-09 | Business | Eligible processes / threshold | Subtype `process`, active | Process Excellence | — | Ph 2 | N |
| D-10 | Governance | EA review "in scope" rule | Program / project + budget threshold + tag override | Chief Architect | **Ph 3** | Ph 3 | N |
| D-11 | Governance | Early-engagement gate | ADM vision approval, fallback startDate | EA Governance Office | — | Ph 3 | Partly |
| D-12 | Technical | Benefit storage | Dedicated tables | Solution architect + CFO | **Ph 4** | Ph 4 | Partly |
| D-13 | Governance | Decision actions | Extend todos | Chief Architect | **Ph 3** | Ph 3 | Y |
| D-14 | Financial | Attribution method (no fixed %) | Per-benefit method enum, Finance-assessed | CFO + Chief Architect | **Ph 4** | Ph 4 | N |
| D-15 | Financial | ROI cost scope + window | `roiScope` tag; FY + rolling 3-FY | CFO | **Ph 4** | Ph 4 | N |
| D-16 | Governance | Tech debt index weights | Equal weights v1 | CTO | — | Ph 4 | N |
| D-17 | Business | KPI targets | Owners ratify release-1 KPIs | KPI owners | **Ph 0** | Ph 0 (before Ph 2) | N |
| D-18 | UI/UX | Translation scope | EN / AR in build; other 8 before release | Product owner | — | Ph 2 | Partly |
| D-19 | Technical | Snapshot storage | Replace with `metric_snapshots` | Solution architect | — | Ph 2 | Y |
| D-20 | Technical | Small-group suppression | n < 3 | CISO / data protection | — | Ph 2 | N |
| D-21 | Business | Strategy progress source | Manual v1 | Strategy Office | — | Ph 2 | N |
| D-22 | Business | Commit prototype as baseline | Commit fixes separately; prototype with tests in Ph 1 | Product owner | **Ph 1** | Pre-Ph 1 | Partly |
| D-23 | UI/UX | Summary insights | Rule-based; AI optional later | Product owner | — | Ph 6 | N |
| D-24 | Financial | Planned-savings dedupe | Latest decision per app | App portfolio owner | — | Pre-Ph 1 | N |
| D-25 | Business | Milestone achievement source | Derive from WBS; fields for roadmap-only | PMO | — | Ph 5 | Partly |
| D-26 | Technical | KPI ↔ builder link | `metricKey` field | Solution architect | — | Ph 2 | Y |
| D-27 | UI/UX | Arabic numerals | Stakeholder preference | Digital Office | — | Ph 2 | N |
| D-28 | Governance | Working-day calendar | Sun-Thu default | EA Governance Office | — | Ph 3 | N |
| D-29 | Financial | Segregation of duties | Creator cannot confirm | CFO | — | Ph 4 | N |
| D-30 | Technical | Hidden-subject governance records | Omit / 404 | CISO + Chief Architect | **Ph 1** | Pre-Ph 1 | Y |
