# UI/UX assessment

## Evidence and limitation

No visual browser inspection was available. This assessment is based on React components, routes and static marketing screenshots present in the repository, not on a live runtime or real user data.

## Reusable capabilities

- MUI layout primitives, theme tokens, responsive grids and cards already power the dashboard (`frontend/src/features/dashboard/OverviewTab.tsx`).
- Recharts powers bar and pie charts and has explicit RTL support helpers (`frontend/src/lib/rechartsRtl.ts`, `OverviewTab.tsx`).
- Existing drill-down destinations include Inventory filters, card details, PPM project detail, GRC risk detail, BPM process views and numerous report pages (`frontend/src/App.tsx`).
- Existing visual/report patterns include portfolio, cost treemap, capability heatmap, lifecycle, roadmap, dependencies, data quality, EOL, strategy, target-state, standards and BPM/PPM dashboards.
- AG Grid supports tabular drill-down and React Flow/BPMN.js supports architecture/process exploration (`frontend/package.json`).

## Executive suitability

The current dashboard shell is a good delivery location: it supports permissions, default-tab preferences, responsive layout and attention links. The present Overview is not sufficient as a CEO dashboard: its measures are primarily repository health (card count, completion/data quality, approval status and lifecycle) and it lacks a governed executive narrative, period selector, KPI target/actual/comparator, benefit-verification status, ownership, and exception/escalation workflow.

Recommended placement: add a permission-controlled **Executive Dashboard** view under Dashboard, not a replacement for the operational Overview. Use a summary-to-detail interaction: enterprise headline → portfolio/domain/department filter → KPI detail → source report/card/decision. Avoid exposing raw cost/individual risk data where the caller lacks existing card and cost permissions.

## English, Arabic and RTL

English and Arabic are explicitly registered as supported locales in `frontend/src/i18n/index.ts`. Arabic is in `RTL_LOCALES`; `App.tsx` selects the RTL Emotion cache and `frontend/src/theme/emotionCache.ts` uses `stylis-plugin-rtl`. Dashboard chart code has RTL tick/legend/margin handling. This is strong code evidence for bilingual/RTL capability.

It remains unverified that every proposed new chart, third-party visual, number format, truncation rule, export, date format, colour meaning and drill-down route is visually correct in Arabic. Executive UI acceptance must include bilingual visual QA and RTL chart/accessibility checks.

## Needed redesign

- Executive information architecture: six strategic outcome tiles, trends and confidence/provenance; concise decision/escalation queue.
- Semantic colour and RAG conventions, including non-colour cues and accessible labels.
- KPI definition drawer: formula, period, inclusion rules, owner, source freshness and confidence.
- Department/domain/KPI drill-down using existing card type, relation and report routes.
- Explicit split between financial forecast/estimate and finance-verified realised benefit.
- Empty, partial and restricted-data states; never show an authoritative-looking zero for missing data.

