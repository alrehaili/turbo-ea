# Executive UI/UX review

**Inspection method.**

- **Executive tab: visually inspected** in Chrome at 1280 px, English, light theme, on 2026-10-22, after the chart redesign.
- **Overview, My Workspace, Admin: source code only.**
- **Arabic / RTL: not visually inspected.** RTL findings come from code (`frontend/src/lib/rechartsRtl.tsx`, `hooks/useIsRtl.ts`, the RTL Emotion cache).
- **Mobile widths and dark mode: not inspected.**

## 1. Assessment from a CEO's perspective

| Criterion | Current state | Finding | Severity |
|---|---|---|---|
| Information hierarchy | Hero → 6 KPI tiles → 5 domain cards | Clean visual hierarchy, but the **top of the page answers "how big is the repository?"** (391 cards, 20 initiatives, 43 processes) instead of "are we on track, and what needs me?" [Confirmed] | High |
| Executive readability | Large numerals, few labels, compact money ($6.6M) | Good legibility. Several labels need EA vocabulary to interpret: "Processes with a published flow", "TIME decisions", "Data quality". [Confirmed] | Medium |
| Visual clarity and consistency | MUI cards, token colours, consistent RAG palette (`RAG_COLORS`), metamodel colours for types and options | Consistent. Risk severity and RAG use different reds (`SEVERITY_COLORS.critical` vs `RAG_COLORS.red`), which is acceptable but should be one semantic scale. [Confirmed] | Low |
| Technical detail | Card counts by type, lifecycle phases, BPMN coverage | Too much repository detail for a CEO; belongs one level down. [Confirmed] | Medium |
| Chart selection | Donuts for composition, stacked bars for RAG, horizontal bars for rankings, rings for % | Appropriate choices. Donuts with 5-6 slices are at the limit. **The RAG stacked bars are dominated by grey "no report"**, so the eye reads "unknown" first; that is correct information, but it should be stated, not shown. [Confirmed] | Medium |
| KPI cards and labelling | Value + caption, ring on some | Rings duplicate the number ("61.6%" next to "62%"). No target, delta or status colour per KPI. [Confirmed] | High |
| Executive summary and insights | None | No narrative ("3 things to know this month"), no automatic insight. [Confirmed] | High |
| Baselines and targets | None | No KPI is shown against a target or baseline (KPI_INVENTORY_AND_VALIDATION.md §4). [Confirmed] | Critical |
| Reporting period and trends | `generated_at` only | No period selector, no "as of" per source, no trend on any Executive KPI. [Confirmed] | Critical |
| Decision prioritisation | None | Nothing tells the CEO what to decide; the risk badge "1 overdue" is the only call to action. [Confirmed] | Critical |
| Drill-down | "Open" per card to the module page, permission-checked | Works, but lands on generic module pages (inventory, PPM), not on the filtered subset behind the number. [Confirmed] | Medium |
| Responsive design | MUI Grid breakpoints; legends wrap under donuts | Verified at 1280 px. Narrower widths are untested. The nav uses the hamburger drawer below 1536 px (uncommitted change). [Confirmed at 1280 px] | Low |
| Accessibility | Coloured segments with text legends and counts | Colour is not the only cue on legends (counts and labels shown). **Rings and stacked bars have no text alternative** (no `aria-label` / `role="img"`); tooltips are mouse-only. No keyboard path into chart segments. Grey-on-white captions may fail contrast. [Confirmed in code; contrast not measured] | Medium |
| Arabic and English, RTL | All Executive strings exist in `en` and `ar` (`common.json`, `dashboard.executive.*`); charts use `mirrorChartMargin`, `makeRtlAxisTick`, `rtlTooltipStyle`; the hero gradient flips; legends are MUI (direction-aware) | Code is RTL-aware, but **visually unverified**. Risks: `Intl` compact notation in `ar` renders Arabic-Indic digits and words (e.g. "٦٫٦ مليون") with the currency symbol prefixed. This may be desirable, but it must be confirmed with stakeholders. The SVG ring text and rotation are direction-neutral. [Assumption until visually verified] | Medium |

## 2. What a CEO needs to see in the first 10 seconds [Recommendation]

1. **Overall status**: a short, plain-language summary per strategic pillar, on track / at risk / off track, with the period.
2. **Value delivered**: realised and validated benefits for the fiscal year against plan, with forecast shown separately.
3. **What needs a decision**: the top 5 escalations and pending decisions, each with owner, age and consequence.
4. **Direction of travel**: a trend arrow and target for each headline KPI.

Everything else is one click down.

## 3. Component reuse [Confirmed components; Recommendation on placement]

| Existing component | Location | Reuse in the redesign |
|---|---|---|
| `KpiTile` + `Ring` | `features/dashboard/executive/ExecutiveTab.tsx` | Headline KPIs; add target, delta and status |
| `Donut`, `HBars`, `ChartLegend` | same file | Composition views on domain pages; extract to a shared component when reused |
| `TrendIndicator` | `features/dashboard/TrendIndicator.tsx` | Delta vs previous period on every KPI |
| `MetricCard`, `ReportShell`, `ReportLegend` | `features/reports/` | Domain drill-down pages |
| `RiskMatrix` | `features/grc/risk/RiskMatrix.tsx` | Executive risk view |
| `LayeredDependencyView` | `features/reports/` | Roadmap dependencies (E4) |
| Capability heatmap, cost treemap, strategy cascade, gap analysis | `features/reports/` | Drill-downs from C4, D4, A1, C8 |
| RTL chart helpers, `useChartTheme`, design tokens | `lib/rechartsRtl.tsx`, `hooks/useChartTheme.ts`, `theme/tokens.ts` | Mandatory for every new chart |
| `useApiQuery`, `useDateFormat`, `useCurrency`, `canAccessPath` | hooks / lib | Data loading, formatting, permission-checked drill-down |
| Saved reports + report export (PPTX / XLSX) | `features/reports/`, `loadReportExport` | Board-pack export of the executive view |

## 4. Specific UI recommendations [Recommendation]

1. Replace the hero repository counts with the **pillar status strip** (see RECOMMENDED_DASHBOARD_STRUCTURE.md).
2. Every KPI tile shows **value · target · delta vs last period · status colour · as-of date**, plus an info icon opening a definition drawer (formula, owner, source, freshness).
3. Remove the rings where the number is already shown, or show the ring as **progress to target** instead of a restatement.
4. Lead delivery with **reporting coverage** ("6 of 20 initiatives reported in 30 days") before the RAG mix.
5. Show **financial status chips** on every money figure (Forecast / Estimated / Validated / Realised), with separate totals.
6. Add a **period selector** (fiscal year and quarter), defaulting to the current fiscal year and named with `fiscalYearLabel`.
7. Make drill-downs **filtered**: the click lands on exactly the records behind the number (inventory query params, risk register filters).
8. Accessibility: `role="img"` + `aria-label` summarising each chart; keyboard-focusable legend items; contrast-checked captions; never colour alone.
9. **Bilingual QA gate**: visual review of every executive screen in Arabic RTL before release, including number and currency formatting, truncation, chart axes and PPTX export.
10. A **print / board-pack** mode: one page per section, light theme forced, export via the existing PPTX engine.
