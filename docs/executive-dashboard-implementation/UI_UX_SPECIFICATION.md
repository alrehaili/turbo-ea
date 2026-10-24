# UI/UX specification: Executive tab

**Status: specification, not implemented.** Conventions apply: MUI 6, tokens from `frontend/src/theme/tokens.ts`, Recharts through the RTL helpers (`lib/rechartsRtl.tsx`, `useChartTheme`, `useIsRtl`), `useApiQuery`, `useCurrency`, `useDateFormat`, `fiscalYearLabel`, and `canAccessPath` for drill-downs. Every string goes through i18n in **English and Arabic only**, per the fork's language policy (D-18, approved). Static field labels follow the theme rule (`UI_GUIDELINES.md` §3.5).

## 1. Navigation

- The top-level Dashboard tabs are unchanged: **Overview · Executive · My Workspace · Admin** (`features/dashboard/Dashboard.tsx`).
- Inside Executive, a secondary navigation: horizontal scrollable tabs on ≥ 1280 px; a select menu on narrower widths. Pages and URL `?tab=executive&page=<key>`:
  `overview` · `transformation` · `governance` · `impact` · `financial` · `services` · `portfolio` · `decisions`.
- A page is hidden when its required permission is absent (Financial without `costs.view`). Hidden pages never show as "denied".
- Deep links (`?page=governance&period=FY2027-Q2&org=<id>`) are restorable. The last page and filters persist per user in `localStorage` (convenience only).

## 2. Global header (all Executive pages)

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ [Page title]                       Period [FY2027 ▾]  Org [All organisations ▾] │
│ As of 22 Oct 2026 · Data completeness 78%          [Export ▾] [ⓘ Definitions]  │
└───────────────────────────────────────────────────────────────────────────────┘
```

- **Period** selector lists fiscal years (current and 3 prior) and quarters of the selected FY.
- **Org** is a tree picker over the organisation type (D-07), reusing `CardPicker` with `hierarchy`.
- Export: PPTX / XLSX through `loadReportExport` (FR-18).

## 3. KPI tile standard (reused on every page)

```
┌──────────────────────────────────────────┐
│ ● Initiative delivery health        ⓘ   │  ← status dot (green/amber/red/grey) + definition drawer
│ 83%   on track          ▲ +8 pts vs Q1   │  ← value · unit · delta (TrendIndicator)
│ Target 75% · Baseline 60%                │
│ ▁▂▃▅▆ (4-quarter sparkline)              │  ← omitted for restricted readers
│ 6 of 20 reported · Confidence: medium    │  ← completeness / coverage + confidence
│ As of 22 Oct 2026            View →      │  ← drill-down (only if canAccessPath)
└──────────────────────────────────────────┘
```

**States**

| State | Shown |
|---|---|
| `not_available` | "Not available" + reason ("No GovService records") + a stewardship hint for owners |
| `not_reported` | "Not reported" (grey) |
| `insufficient_data` | Value muted + "Low completeness" chip |
| `restricted` | Lock icon + "Requires cost permission" |
| `suppressed` | "Hidden (small group)" |

**Definition drawer**: formula, denominator, source entities, owner, verifier, frequency, target rationale, calculation version, last refreshed. The content comes from the KPI card and the registry.

**Money**: compact currency through the shared formatter (CR-05), showing the source currency; amounts in different currencies are never summed (D-05). A **status chip** reads Forecast / Estimated / Validated / Realised. Planned savings show a "conflicting estimates (n)" link when conflicts are excluded (D-24).

## 4. Pages and wireframes

### 4.1 CEO Executive Overview (landing; FR-06: six measures)

```
┌ Global header ───────────────────────────────────────────────────────────────┐
├──────────────────────────────────────────────────────────────────────────────┤
│ Summary sentence band: "Strategy 72% of plan · 2 initiatives off track ·      │
│ SAR 4.1M realised · 3 decisions awaiting you"  (rule-based in Phase 2)        │
├────────────────┬────────────────┬────────────────┬───────────────────────────┤
│ TR-01 Strategy │ TR-03 Delivery │ GOV-05 Decision│                           │
│ execution      │ health (4-state│ implementation │  DECISIONS NEEDING YOU    │
│ (ring to plan) │ stacked + cov.)│ (fallback      │  1. Critical risk R-12 …  │
├────────────────┼────────────────┤  GOV-01)       │     owner · 12 d · ⚠ SAR  │
│ FIN-01 Realised│ SVC-01 Digital │────────────────│  2. ADR-0042 awaiting 2   │
│ benefits FY    │ services % +   │ DEC-01 Strategic│     signatures · 9 d     │
│ [Realised][Val]│ SVC-02 automat.│ risks escalated│  3. Exception E-7 expires │
│ [Forecast]     │ (2 mini bars)  │ (count + top 3)│  … (top 5, link to page 8)│
└────────────────┴────────────────┴────────────────┴───────────────────────────┘
│ Pillar strip: one compact chip per pillar: name · progress · RAG               │
└──────────────────────────────────────────────────────────────────────────────┘
```

Exactly six KPI tiles, the decisions panel and the pillar strip. Nothing about card counts or completeness.

### 4.2 Digital Transformation Performance

Row 1: TR-01 by pillar (horizontal bar, progress vs plan) · TR-05 maturity (radar: current vs target, reusing the maturity overview component).
Row 2: TR-03 delivery state over time (stacked area by quarter) · TR-04 coverage.
Row 3: TR-02 milestone achievement (bar by quarter, achieved / late / missed) · DEC-04 dependency risks (list; optional LayeredDependencyView link).
Row 4: TR-06 capability improvement (heatmap link with the count of improved target capabilities).

### 4.3 EA Governance Effectiveness

A band of three column groups labelled **Activity · Effectiveness · Impact** (FR-11):

- Activity: GOV-01 coverage, review and ADR volume (context only, no target).
- Effectiveness: GOV-02, GOV-03, GOV-04, GOV-05, GOV-06.
- Efficiency strip: GOV-07 turnaround (median + distribution), GOV-08 bottlenecks (count, links).
- Impact (contribution): GOV-09 governed vs ungoverned bar pair, with cohort sizes and a "correlation, not causation" note.

The bottom table lists decisions with action progress ("3 of 5 actions closed"), each linking to the traceability view (FR-20).

### 4.4 EA Business Impact

KPI tiles IMP-01..08. A **"Decided vs executed"** paired bar (TIME decisions vs retirements and modernizations completed). Technology debt index trend with a component breakdown (stacked). Target-architecture realisation per plateau (progress bars). Integration standardization donut. Risk reduction waterfall (initial → residual).

### 4.5 Financial Benefits & ROI (`costs.view` + `benefits.view`)

```
┌ Realised (cash) FY ┐┌ Realised avoidance ┐┌ Validated (not yet ┐┌ Forecast / estimated ┐
│ SAR 4.1M  ▲        ││ SAR 1.2M           ││ realised) SAR 2.0M ││ SAR 6.5M (pipeline)  │
└────────────────────┘└────────────────────┘└────────────────────┘└──────────────────────┘
┌ Benefit realisation rate (FIN-04) ┐ ┌ ROI (FIN-08), "Not available until Finance ┐
│ realised vs validated by quarter  │ │ confirms all inputs", or value + composition│
└───────────────────────────────────┘ └─────────────────────────────────────────────┘
┌ Budget execution FY (FIN-07) ┐ ┌ Investment alignment (FIN-09) ┐ ┌ Productivity (FIN-10, │
│ phased actual vs budget      │ │ aligned vs unaligned spend    │ │ hours, separate)      │
└──────────────────────────────┘ └───────────────────────────────┘ └───────────────────────┘
┌ Benefits register table: ref · title · type · status chip · amount · period · owner ·        ┐
│ decision link · evidence count · Finance confirmed ✓   [filters] [open → benefit drawer]     │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

The four status totals are separate cards and are never summed (BENEFITS_AND_ROI_SPECIFICATION.md).

### 4.6 Services & Process Automation

- Left: **Service digitalization** (SVC-01) donut Digital / Hybrid / Manual / Not assessed, with the trend.
- Right: **Process automation** (SVC-02) donut Fully / Partially / Manual / Unknown, with the trend. A separator and caption make clear the two are different measures.
- Below: SVC-03 manual reduction, SVC-04 assessed maturity (with coverage), SVC-06 channel maturity.
- The specialist expander holds SVC-05 documentation coverage.

### 4.7 Architecture Portfolio Health (specialist)

The relocated phase-one charts, renamed: data completeness (PRT-01), lifecycle mix and past planned EOL (PRT-02), vendor support exposure (PRT-03), repository review status (PRT-04), TIME position and cost (PRT-05), largest card types. Header note: "Specialist view: repository and inventory indicators".

### 4.8 Executive Decisions & Escalations

A filterable, sortable list (AG Grid with column freeze per the grid convention, `useColumnFreeze`), with **Type** chips (Risk · Decision · Exception · Investment · Dependency · Cross-department). Columns: item · type · owner · age · due · consequence (SAR, objective, level) · status · link. Default sort: severity, then age. A row click opens the source record in a side drawer where one exists (`CardDetailSidePanel`, risk detail), else navigates.

## 5. Bilingual and RTL (FR-05)

- Keys live under `common.json` `dashboard.executive.*`, EN and AR authored together. Metamodel labels are resolved with `useTypeLabel` / `useOptionLabel` (never `.key`).
- RTL: secondary tabs and header mirror; charts use `mirrorChartMargin`, `makeRtlAxisTick`, `rtlTooltipStyle`; legends are MUI (direction-aware); the hero gradient flips; sparkline direction is mirrored.
- Numbers: Arabic-Indic digits are a **decision** (D-27). Default: follow the `ar` locale `Intl` behaviour; option: Latin digits via `numberingSystem: "latn"`.
- The SAR Riyal glyph falls back to "ر.س" / "SAR" when not renderable (`lib/currency.ts`).

## 6. Accessibility (NFR-04)

- Each chart is wrapped in `role="img"` with an `aria-label` summarising its values. A "View as table" toggle exposes the data.
- Status is never conveyed by colour alone (icon + text).
- Keyboard: the secondary navigation, tiles (drawer and drill-down) and legend items are focusable.
- Contrast ≥ 4.5:1 for text; captions use `text.secondary` only where they meet it.

## 7. Responsive (NFR-05)

| Width | Layout |
|---|---|
| ≥ 1920 | 3 columns + decisions panel (board-room) |
| 1280-1919 | 3 columns, decisions panel below on Overview |
| 768-1279 | 2 columns, secondary nav as select |
| < 768 | 1 column; tiles stack; tables become cards |

## 8. Reused components [Confirmed paths]

`KpiTile`, `Ring`, `Donut`, `HBars`, `ChartLegend` (phase-one `executive/ExecutiveTab.tsx`, to be extracted to `executive/components/`) · `TrendIndicator` (`features/dashboard/TrendIndicator.tsx`) · `MetricCard`, `ReportShell`, `ReportLegend` (`features/reports/`) · `RiskMatrix` (`features/grc/risk/`) · maturity radar (maturity module) · `LayeredDependencyView` · `CardPicker` (hierarchy) · `CardDetailSidePanel` · AG Grid + `useColumnFreeze` · `loadReportExport` · `useCurrency`, `useDateFormat`, `fiscalYearLabel`.
