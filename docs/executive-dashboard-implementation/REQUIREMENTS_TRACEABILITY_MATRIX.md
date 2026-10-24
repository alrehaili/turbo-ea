# Requirements traceability matrix

Each requirement (`EXECUTIVE_BUSINESS_REQUIREMENTS.md`) is traced to its design, KPIs, phase, decisions, verification and the source assessment finding. Verification describes the test that will prove it in CI. **None has been executed.**

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
| FR-01 | UI_UX_SPECIFICATION §1, §4 | — | 2 (+ 3-5 pages) | C-01 | Vitest: sub-nav renders permitted pages; e2e smoke | Assessment RECOMMENDED_DASHBOARD_STRUCTURE §1 |
| FR-02 | API_AND_BACKEND §2; DATA_MODEL §4.2 | all | 2 | D-07, C-16 | API: org filter narrows denominators; hidden org → 404 | UI_UX_REVIEW §4 |
| FR-03 | API §2; KPI dictionary §1 | all | 2 | D-06 | API: period changes values; FY naming | KPI_INVENTORY §4 |
| FR-04 | API §4 drilldown | all | 2 | — | API: drill-down rows = KPI numerator under the same scope | UI_UX_REVIEW §1 |
| FR-05 | UI_UX §5 | — | 2-6 | C-11, D-18 (approved: EN/AR only), D-27 | i18n parity for EN / AR (`i18n.test.ts`); Phase 6 RTL visual QA sign-off | UI_UX_REVIEW §1 |
| FR-06 | UI_UX §4.1; KPI dictionary §3.1 | 6 landing | 2 | C-11 | Vitest: exactly 6 tiles + decisions panel | EXISTING_DASHBOARD §3 |
| FR-07 | UI_UX §3; API §3 | all | 2 | D-17, D-19 | Vitest: tile renders target / delta / as-of; API returns them | KPI_INVENTORY §4 |
| FR-08 | KPI dictionary §1; UI_UX §3 | all | 1-2 | C-04 | Builder tests: missing → `not_available` / `not_reported`, never 0 | KPI_INVENTORY K14 |
| FR-09 | DATA_MODEL §3.1 | all | 2 | C-02, D-26 | API: target / owner read from the KPI card | DATA_AND_FUNCTIONAL_GAP G1 |
| FR-10 | DATA_MODEL §3.2, §3.2b | all | 2 | D-19 | Snapshot freeze test; measurement CRUD + event test | TECHNICAL_READINESS §3 |
| FR-11 | GOVERNANCE_MEASUREMENT_MODEL | GOV-01..09 | 3 | D-10, D-11, D-28 | GOV builder tests; class labels | EA_GOVERNANCE_AND_ROI_MODEL §3.1 |
| FR-12 | DATA_MODEL §3.3; API §4 | GOV-05, GOV-06 | 3 | D-13 | API: actions on ADR / ARB; GOV-05 end-to-end | GAP G3 |
| FR-13 | BENEFITS_AND_ROI §1-3, §7 | FIN-01..04, FIN-10 | 4 | C-06, D-12, D-29 | API: transitions require evidence; segregation of duties | GAP G2 |
| FR-14 | BENEFITS_AND_ROI §6 | FIN-08 | 4 | C-07, C-08, D-14, D-15 | Builder: ROI Not available unless all inputs are confirmed | EA_GOVERNANCE_AND_ROI_MODEL §5 |
| FR-15 | DATA_MODEL §4.1 | SVC-01 | 5 | C-10, D-08 | Builder: four buckets incl. Not assessed | — |
| FR-16 | KPI dictionary §3.6 | SVC-02 | 2, 5 | C-10, D-09 | Builder: missing value → Unknown | KPI_INVENTORY K19 |
| FR-17 | UI_UX §4.8 | DEC-01..05 | 2, 3, 5 | D-04 | API: list omits unreadable items; sort | EXISTING_DASHBOARD §3 |
| FR-18 | UI_UX §2; API §7 | — | 6 | — | Export parity + audit test | TECHNICAL_READINESS §7 |
| FR-19 | BENEFITS_AND_ROI §1, §6 | FIN-10 | 4 | C-09 | Builder: productivity excluded from FIN-01 / FIN-08 | — |
| FR-20 | API §4 traceability; BENEFITS_AND_ROI §2 | — | 3 (v1), 4 | — | API: chain for a fixture decision | EA_GOVERNANCE_AND_ROI_MODEL §2 |
| CR-01 / 02 | KPI dictionary §2 | TR-03, TR-04 | 1 | C-12, D-02 (approved) | Builder + API: Not Reported is never On Track or At Risk; coverage separate; staleness only when configured | KPI_INVENTORY K14 |
| CR-03 | KPI dictionary §2 | FIN-07 | 1 | D-06 (approved) | Builder: out-of-FY lines excluded | K18 |
| CR-04 | KPI dictionary §2 | FIN-03 | 1 | D-24 (approved), D-31 (open) | Builder: agreeing duplicates counted once; conflicts flagged and excluded from totals | K16 |
| CR-05 | KPI dictionary §2 | money KPIs | 1 | C-13, D-05 (approved) | API currency field; no cross-currency totals; no stored amount altered; Vitest formatter EN / AR | — |
| CR-06 | KPI dictionary §2; SECURITY WI-11 | totals | SEC-3 + 1 | D-01 (approved) | API parity across four tabs | K01 / K10, EXISTING_DASHBOARD §6.1 |
| CR-07 | KPI dictionary §2 | PRT-04, GOV-03 | 1 | — | Vitest: no "approved" tile on executive pages | K12 |
| CR-08 | KPI dictionary §2 | PRT-01 | 1 | — | i18n key review; Vitest label | K02 / K11 |
| CR-09 | KPI dictionary §2 | PRT-02, PRT-03 | 1 | — | Vitest labels; separate drill-downs | K07 |
| CR-10 | KPI dictionary §2 | SVC-05 | 1 | — | No headline uses documentation coverage | K13 |
| SR-01 | SECURITY §3 WI-1..11, WI-15 | — | SEC | C-05, D-01, D-30 (approved) | Extended sentinel sweep green; guard green | GAP G13; S-18 / S-19 |
| SR-02 | SECURITY §4 | — | SEC + 2 | D-01 | Totals = Σ visible breakdowns test; drill-down parity | EXISTING_DASHBOARD §6.1 |
| SR-03 | SECURITY WI-5, WI-6, WI-15 | money | SEC | D-05 | API: no money without `costs.view` (incl. strategy-map) | TECHNICAL_READINESS §4; S-18 |
| SR-04 | SECURITY §4 | — | 2 | D-20 | API: n < 3 → suppressed | TECHNICAL_READINESS §4 |
| SR-05 | SECURITY §4; API §7 | — | 6 | — | Export audit entry exists; parity | — |
| SR-06 | BENEFITS_AND_ROI §7 | — | 4 | D-03, D-29 | API: validate / confirm permission tests | — |
| SR-07 | SECURITY WI-12, WI-14 | — | 1-6 | — | Restricted-reader matrix per endpoint | — |
| SR-08 | PHASED_DELIVERY SEC track exit | — | SEC | C-05 | SEC exit checklist | — |
| SR-09 | SECURITY §6 (R1-R7) | — | SEC-1 | — | Regression suite fails before the fixes and passes after | S-16, S-17, S-18, S-19 |
| NFR-01 | API §8 | — | 2-6 | — | Benchmark p95 at 50k cards (Phase 6) | TECHNICAL_READINESS §6 |
| NFR-02 | DATA_MODEL §3.2 | — | 2 | — | Frozen-period test | TECHNICAL_READINESS §3 |
| NFR-03 | API §7 | — | 2, 4 | — | Event + audit-log tests | TECHNICAL_READINESS §5 |
| NFR-04 | UI_UX §6 | — | 6 | — | Accessibility checks + manual review | UI_UX_REVIEW §1 |
| NFR-05 | UI_UX §7 | — | 2-6 | — | Visual review at listed widths | UI_UX_REVIEW §1 |
| NFR-06 | API §5 | — | 2-5 | C-03 | Code review: no formula engine | TECHNICAL_READINESS §2 |
| NFR-07 | PHASED_DELIVERY (all) | — | all | C-14 | CI gates | CLAUDE.md |
