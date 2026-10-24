# Recommended executive dashboard structure

**Status: recommendation.** Nothing is implemented. KPI IDs refer to EXECUTIVE_KPI_FRAMEWORK.md. "Available now" marks what can ship on existing data; everything else waits for the capability named.

## 1. Information architecture

```
Dashboard
├── Overview            (EA repository health: unchanged, EA audience)
├── Executive           ◀── becomes a section with its own sub-navigation
│   ├── 1 CEO Executive Overview          (landing page)
│   ├── 2 Digital Transformation Performance
│   ├── 3 EA Governance Effectiveness
│   ├── 4 EA Business Impact
│   ├── 5 Financial Benefits & ROI          (costs.view required)
│   ├── 6 Services & Process Automation
│   ├── 7 Architecture Portfolio Health
│   └── 8 Executive Decisions & Escalations
├── My Workspace        (unchanged)
└── Admin               (unchanged)
```

Global controls on every Executive page: **fiscal period** (FY / quarter), **organisation / segment filter** (reusing NORA segments and Organization cards), **language** (EN / AR), and **export** (PPTX / XLSX through the existing report export engine).

Every KPI tile follows one standard: **value · target · Δ vs last period · status · as-of · definition drawer**.

## 2. Pages

### 1. CEO Executive Overview (landing)

| Zone | Content | KPIs | Available now? | Reuse |
|---|---|---|---|---|
| Status strip | One tile per strategic pillar: progress vs plan, RAG, owner | A1 by pillar | ⚠️ needs Pillar → Objective links and `Objective.progress` populated | strategy cascade |
| Value strip | Realised · Validated · Forecast benefits FY (three separate figures) | D1, D2, D3 | ❌ D1 and D2 need the benefit ledger; D3 available | `KpiTile` |
| Headline KPIs (6) | Delivery health with coverage, digitalized services %, process automation %, open critical risks, budget execution FY, governance coverage | A3, A5, A6, E1, D7, B1 | A3, A6, E1 available; D7 after the period fix; A5 and B1 need data or rules | `KpiTile`, `TrendIndicator` |
| Decisions needing you | Top 5 items from page 8 | E1, E2, E7 | ✅ partial (E2 available) | — |
| Insight panel | Three generated sentences ("Initiative health improved…") | derived | ❌ (later; optionally AI-assisted) | TurboLens AI plumbing |

### 2. Digital Transformation Performance

Strategy execution by pillar and objective (A1) · roadmap milestone achievement (A2) · initiative delivery health and reporting coverage (A3) · digital maturity radar and trend (A4) · dependency risks (E4).
Reuse: strategy cascade / map, PPM Gantt, maturity overview radar, LayeredDependencyView.

### 3. EA Governance Effectiveness

Four-level model (EA_GOVERNANCE_AND_ROI_MODEL.md §3.1): reach (B1, B2), efficiency (B7, B9), adherence (B3, B4, B5, B6), contribution (B8).
Reuse: ARB list, ADR grid, tech-standards compliance scan, exceptions list, Admin approval pipeline (aggregated).

### 4. EA Business Impact

Rationalization executed vs decided (C1, C5) · duplicate candidates (C2) · technology debt index (C3) · capability improvement (C4) · reuse (C6) · integration standardization (C7) · target-architecture realisation by plateau (C8) · risks mitigated (C9).
Reuse: rationalization board, TurboLens duplicates, EOL report, capability heatmap, gap analysis, integration status.

### 5. Financial Benefits & ROI (requires `costs.view`)

Benefits by status, never summed across statuses (D1-D3) · realisation rate (D9) · run-rate reduction vs baseline (D4) · consolidation savings (D5) · transformation and EA investment (D6) · budget execution (D7) · investment alignment (D10) · ROI (D8, only after the attribution policy is ratified).
Reuse: cost treemap (FY-bound), PPM budget and cost lines, `fiscal_year.py`.

### 6. Services & Process Automation

Digitalized services, fully vs partially (A5) · automation mix and trend (A6, A7) · manual process reduction · process duration (A9) · BPMN documentation coverage as a secondary indicator (K13) · beneficiary journey and channel maturity (A8).
Reuse: service traceability report, process map, BPM dashboard aggregation (`bpm_dashboard_service.py`).

### 7. Architecture Portfolio Health

The current Executive tab's portfolio content relocated: application landscape by criticality, TIME position, lifecycle mix, data completeness (renamed), EOL exposure, cost by domain. Audience: VP / CTO / EA.
Reuse: phase-one Executive charts (`Donut`, `HBars`), Overview charts, app-portfolio report.

### 8. Executive Decisions & Escalations

One prioritised list across sources: escalated risks (E1), pending ADR signatures and ARB items (E2), investment decisions (E3), dependency conflicts (E4), governance bottlenecks (E5), cross-department issues (E6), ranked by consequence (E7). Each row shows owner, age, due, consequence and a link to the record.
Reuse: risk register, ADR, ARB, exceptions, PPM dependencies.

## 3. Fate of today's components

| Component | Decision |
|---|---|
| Overview tab | **Keep** as EA repository health (rename the "Avg Completion" label) |
| Executive hero counts | **Replace** with the pillar status strip |
| Data quality / Approved % tiles | **Relocate** to Portfolio Health; drop Approved % from executive pages |
| Processes-with-flow tile | **Relocate** to Services & Automation as a documentation indicator |
| Initiatives off track | **Improve** (coverage first) → Overview headline A3 |
| Open critical & high risks | **Keep** → E1 |
| Planned savings | **Improve** (dedupe, status, currency) → Financial page as "Forecast" |
| Portfolio / lifecycle charts | **Relocate** to Portfolio Health |
| Delivery RAG + budget | **Improve** (FY-bound) → Transformation and Financial pages |
| Process automation / maturity | **Keep** → Services & Automation, labelled self-assessed |
| TIME donut | **Keep** → Business Impact, paired with "executed" |
| My Workspace, Admin | **Keep** unchanged; surface stakeholder coverage and stuck approvals (aggregated) on the Governance page |
