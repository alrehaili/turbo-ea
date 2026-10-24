# KPI inventory and validation

Every number currently shown on the Dashboard, validated against its implementation. "Value class" follows the results chain: **Activity → Output → Outcome → Impact → Financial value**. For each KPI, the demo value is what the NexaTech seed returned on 2026-10-22.

Legend: ✅ valid as labelled · ⚠️ valid but ambiguous or easy to misread · ❌ misleading as built.

## 1. Inventory

| ID | Tab | Label (EN) | Implementation | Formula | Denominator | Demo value | Value class | Validation |
|---|---|---|---|---|---|---|---|---|
| K01 | Overview | Total Cards | `reports.py:135-143` | `count(*)` ACTIVE, readable | none | 391 | Activity | ⚠️ includes 118 hidden-type cards; differs from My Workspace and Admin counting |
| K02 | Overview | Avg Completion | `reports.py:145-149` | `avg(cards.data_quality)` | all ACTIVE readable cards | 61.6 % | Output | ⚠️ the same number is called "data quality" on Executive. Completeness ≠ quality. Unweighted across types. |
| K03 | Overview | Approved | `reports.py:151-157` | `count(approval_status='APPROVED')` | none | 391 | Activity | ⚠️ no denominator. Seed approves 100%, so no signal. |
| K04 | Overview | Broken | same | `count(approval_status='BROKEN')` | none | 0 | Activity | ✅ for EA, irrelevant for a CEO |
| K05 | Overview | 30-day trend (×4) | `kpi_snapshot_service.py:88-160` | `(current − snapshot≈30d) / snapshot` | snapshot value | n/a (1 snapshot) | n/a | ✅ correctly suppressed for restricted readers (`reports.py:255`); only 4 metrics |
| K06 | Overview | Low data quality | `OverviewTab.tsx:228-262` | buckets 0-25 + 25-50 | none | — | Output | ✅ |
| K07 | Overview | End-of-life cards | same | `lifecycle_distribution.endOfLife` | none | 13 | Activity | ❌ label implies vendor EOL. It is "past its own end-of-life date" (retired but still ACTIVE). |
| K08 | Overview | Cards still in draft | same | `approval_status='DRAFT'` | none | 0 | Activity | ✅ |
| K09 | Overview | Lifecycle distribution | `reports.py:176-193` | current phase per card | n/a | none = 118 | Activity | ⚠️ 30% "Not set": a data gap that reads as a category |
| K10 | Executive | Active cards | `executive_dashboard.py:65` | as K01 | none | 391 | Activity | ⚠️ as K01; also ≠ sum of the type bars |
| K11 | Executive | Avg data quality | same | as K02 | as K02 | 61.6 % | Output | ⚠️ as K02; ring duplicates the number |
| K12 | Executive | Approved % | same | `APPROVED / total` | ACTIVE readable | 100 % | Activity | ❌ in a CEO context implies "architecture approved / compliant". It is repository review state. |
| K13 | Executive | Processes with a published flow | `bpm_dashboard_service.py:21` | `processes with published BPMN / processes` | ACTIVE readable BusinessProcess | 2.3 % | Output | ⚠️ documentation coverage, easily misread as process maturity or automation |
| K14 | Executive | Initiatives off track | `ppm_portfolio_service.py:494` | `count(latest report.schedule_health='offTrack')` | none shown | 0 of 20 | Outcome | ❌ 14 of 20 have no report, so "0 off track" overstates health. Ignores `initiativeStatus`. |
| K15 | Executive | Open critical & high risks | `executive_dashboard.py:139` | open = not closed/accepted; level = residual else initial | none | 5 (1 overdue) | Outcome | ⚠️ "open" includes mitigated and monitoring; definition needs CRO approval |
| K16 | Executive | Planned savings | `executive_dashboard.py:167-210` | `Σ planned_savings` (active and completed assessments) | none | $590 K | Forecast | ⚠️ correctly tagged estimated. ❌ risk: duplicates across assessments are summed; no currency, period or approval. |
| K17 | Executive | Delivery RAG (×3) | `ppm_portfolio_service.py:494` | latest report per initiative | initiatives | 5 / 1 / 0 / 14 | Outcome | ⚠️ the "no report" share dominates and must lead the visual |
| K18 | Executive | Budget vs actual, % spent | `ppm_portfolio_service.py:253` | `Σ budget_lines.amount`, `Σ cost_lines.actual` | budget | $6.6 M / $3.6 M, 54 % | Financial (spend) | ❌ not period-bound: all fiscal years mixed |
| K19 | Executive | Automation mix | BPM attributes | count per `automationLevel` | processes | 7 / 23 / 10 / 3 | Output | ⚠️ self-assessed classification, no evidence date |
| K20 | Executive | Maturity mix | BPM attributes | count per `maturity` | processes | — | Output | ⚠️ as K19 |
| K21 | Executive | Open risks by level | as K15 | | | 0 / 5 / 1 / 2 | Outcome | ✅ |
| K22 | Executive | TIME decisions | rationalization | count per `time_decision` | decisions | 4 / 4 / 3 / 2 | Output | ✅ but it is intent, not execution |
| K23 | Admin | Active users (30 d) | `reports.py:389+` | | active accounts | — | Activity | ✅ admin-only |
| K24 | Admin | Cards without stakeholders | same | | non-hidden cards | — | Output (accountability) | ✅ governance-relevant |
| K25 | Admin | Stuck approvals > 30 d | same | | | — | Activity (throughput) | ✅ governance-relevant |
| K26 | Admin | Overdue todos | same | | | — | Activity | ✅ admin-only |
| K27 | Workspace | Personal counters | `reports.py:273+` | | | — | n/a | ✅ personal |

## 2. Distribution by value class [Confirmed]

| Value class | Count (K01-K22) | Examples |
|---|---|---|
| Activity | 9 | totals, approvals, lifecycle, drafts |
| Output | 7 | data completeness, documentation coverage, classifications, decisions |
| Outcome | 5 | delivery health, risk exposure |
| Impact | **0** | — |
| Financial, realised or validated | **0** | — |
| Financial, spend or forecast | 2 | budget vs actual, planned savings |

**Key observation.** The dashboard has **no impact measure and no realised or validated financial measure**. Every number a CEO would ask about first ("what did transformation and EA deliver?") is absent. This is not a presentation problem: the underlying data is not captured (see DATA_AND_FUNCTIONAL_GAP_ANALYSIS.md).

## 3. KPIs to fix before any executive use

| Priority | KPI | Fix [Recommendation] |
|---|---|---|
| 1 | K14 initiatives off track | Show reporting coverage ("6 of 20 reported in the last 30 days") first; treat a stale or missing report as amber; choose one source of truth with the PMO |
| 2 | K18 budget vs actual | Bound to the current fiscal year with `fiscal_year.py` (the same rule as the cost reports in CLAUDE.md) |
| 3 | K16 planned savings | De-duplicate per application (latest decision wins); show currency; add financial status (`forecast` / `estimated` / `validated` / `realised`) |
| 4 | K01 / K10 total cards | Apply one hidden-type rule across all tabs |
| 5 | K12 approved % | Remove from the CEO view |
| 6 | K02 / K11 label | Rename to "Data completeness" in EN and AR, consistently |
| 7 | K07 end-of-life label | Rename to "Past end-of-life date"; keep vendor EOL distinct |
| 8 | K15 open risks | Approve the definition with the CRO; consider showing "open (unmitigated)" separately |

## 4. Historical comparison, targets and thresholds [Confirmed]

| Capability | State |
|---|---|
| Trend | Only K01-K04, via `kpi_snapshots` (daily, 4 columns) |
| Target | None on any widget. The `KPI` card type supports targets but is unused by the dashboard. |
| Threshold / RAG rule | Only PPM status-report RAG (manual) and risk level (matrix-derived) |
| Baseline | None. `KPI.baselineValue` and `baselineDate` exist but are unused. |
| Data as-of | `generated_at` on Executive only; no per-source freshness |
