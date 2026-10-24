# Implementation recommendations

**Status: proposal for review.** These recommendations will be reviewed with ChatGPT to produce the final implementation plan. Nothing here is approved or implemented. Sizes are relative (S ≈ days, M ≈ 1-2 weeks, L ≈ 3+ weeks) and are assumptions.

## Guiding principles

1. **Truth before polish.** Fix misleading numbers before adding new ones.
2. **Reuse before build.** Use the existing KPI card, todos, tag groups, PPM WBS, ADR, rationalization and improvement opportunities.
3. **Evidence before value claims.** No "savings" figure until the benefit ledger and Finance validation exist.
4. **Data before dashboards.** A page whose data is not populated ships as "Not available" with a stewardship action, not as zeros.
5. **Every change honours the project rules**: `CardReadScope`, `costs.view`, events with `db=`, workspace-transfer checklist, EN + AR strings, docs.

## Recommended sequence

### Phase 0: Ratify definitions (no code). S

- Approve the KPI catalogue subset for release 1 (EXECUTIVE_KPI_FRAMEWORK.md), with owners and proposed targets.
- Approve the financial status taxonomy, double-counting rules and attribution policy (EA_GOVERNANCE_AND_ROI_MODEL.md).
- Decide: hidden-type rule; one source of truth for initiative health and cost; "open risk" definition; EA-review "in scope" rule.
- Data stewardship plan for GovService, KPI cards, maturity assessments and Pillar → Objective links (all empty in the demo).

### Phase 1: Make phase one trustworthy (quick wins). S-M

| # | Change | Fixes |
|---|---|---|
| 1.1 | Initiatives: show reporting coverage first; a stale or missing report counts as amber | K14 |
| 1.2 | Budget vs actual bound to the current fiscal year (`fiscal_year.py`) | K18 |
| 1.3 | Planned savings: dedupe per application (latest decision), currency, "Forecast" chip | K16 |
| 1.4 | One hidden-type rule across `/reports/dashboard`, `/reports/executive` and the tile totals | K01, K10 |
| 1.5 | Remove Approved %; rename "Avg Completion" / "data quality" to "Data completeness" (EN, AR) | K12, K02 |
| 1.6 | Rename "End-of-life cards" to "Past end-of-life date" | K07 |
| 1.7 | `costs.view` gate on `/reports/ppm/dashboard` money fields | Confidentiality |
| 1.8 | Apply `CardReadScope` in the fork modules listed in G13 before any reuse | Confidentiality |
| 1.9 | Commit phase one with tests (currently uncommitted and without tests, by request) | Delivery hygiene |

### Phase 2: Targets, trends and the CEO landing page. M

- KPI definitions and targets on **`KPI` cards**; dashboard tiles read target, baseline and owner from them.
- `kpi_measurements` (history for KPI cards) and a key/value snapshot fact table extending the existing daily loop.
- KPI tile standard: value · target · Δ · status · as-of · definition drawer.
- Fiscal period selector; per-source freshness.
- CEO Executive Overview page (status strip, headline KPIs, decisions panel) on available KPIs: A3, A6, E1, E2, D7, plus A1 and B1 once data and rules exist.
- Executive Decisions & Escalations page (E1, E2, E5) with an escalation **tag group**.

### Phase 3: Governance effectiveness. M

- Decision actions via **todos linked to ADR / ARB** (owner, due date, closure); the decision shows "n of m actions closed".
- Governance page: B1, B2 (using ADM gate dates), B3, B4, B5, B7, B9.
- `realized_at` on improvement opportunities; ADR signed date exposed.

### Phase 4: Benefits register and financial page. L

- `benefits` table with the status lifecycle, approver, evidence, period and attribution; linked to ADR, TIME decision, opportunity or initiative.
- Financial page: D1-D7, D9, D10; D8 (ROI) only after the attribution policy is ratified.
- Finance-system integration through the extension data bridge, if available.

### Phase 5: Impact, services and the remaining pages. M-L

- Services & Automation (A5-A9) once GovService data is populated.
- Business Impact (C1-C9): link retirement to decision (C1), technology-debt composite (C3), capability maturity history (C4), target-state realisation date (C8).
- Digital Transformation page (A1-A4) with roadmap milestone achievement derived from PPM WBS milestones.
- Portfolio Health page (relocated phase-one charts).

### Phase 6: Executive experience. M

- Narrative insight panel (rule-based first; AI-assisted optional, scope-safe).
- Board-pack PPTX / XLSX export through the existing report export engine.
- Accessibility pass (chart text alternatives, keyboard, contrast) and a **bilingual RTL visual QA gate**.
- Performance: daily aggregates, per-scope caching.

## Highest executive value per effort

| Rank | Change | Value | Effort |
|---|---|---|---|
| 1 | Decisions & escalations panel (E1, E2, E5) on the landing page | Directly tells the CEO what to act on | S-M |
| 2 | Fix delivery health, budget and planned-savings integrity (1.1-1.3) | Prevents wrong executive conclusions | S |
| 3 | Targets and trends via KPI cards + history | Turns numbers into performance | M |
| 4 | Decision → action tracking (todos) | First verifiable governance-effectiveness metric | M |
| 5 | Benefits register with Finance validation | The only route to defensible savings and ROI | L |

## Risks to manage

| Risk | Mitigation |
|---|---|
| Empty data makes new pages look broken | Ship "Not available + stewardship action" states; populate through surveys |
| Stakeholders read forecasts as savings | Mandatory status chips; separate totals; Finance-owned "realised" |
| Confidentiality leak through aggregates | `CardReadScope` everywhere, `costs.view`, small-number suppression, fix G13 first |
| Scope creep into a parallel EA tool | Reuse rule; every new entity justified against existing ones |
| RTL defects reach executives | Bilingual visual QA as a release gate |

## Out of scope for this assessment

No code, schema, UI, test or build change was made for this assessment. (The phase-one Executive tab, the Windows `os.pread` fix and the narrow-screen navigation change were earlier, separate, uncommitted work.)
