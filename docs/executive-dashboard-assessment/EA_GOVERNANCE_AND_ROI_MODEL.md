# EA governance effectiveness and benefits-realisation model

## 1. The value chain to be evidenced

```
EA governance intervention ─▶ Architecture recommendation ─▶ Management decision
        (ARB review,               (ADR options, ARB             (ADR signed, ARB approved,
         compliance scan,           decision notes, TIME          TIME decision, exception
         maturity assessment)       recommendation)               approved or rejected)
                                                                        │
                                                                        ▼
  Financial / non-financial benefit ◀── Business outcome ◀────────── Implementation
  (benefit ledger: forecast →          (KPI movement, retired       (actions closed,
   validated → realised)                app, capability uplift)      initiative delivered)
```

**Principle.** Governance activity does not automatically create value. Each link must be **recorded and evidenced**. A KPI may only claim a benefit for EA when every link back to the intervention exists.

## 2. Can Turbo-EA trace this chain today? [Confirmed]

| Link | Can it be recorded? | Entity / field | Gap |
|---|---|---|---|
| Intervention exists | ✅ | `arb_reviews`, compliance scan, `maturity_assessments`, TurboLens duplicate clusters | ARB has no "request received" timestamp distinct from `created_at` |
| Intervention → recommendation | ⚠️ partial | ADR `alternatives_considered`, `decision`; ARB `decision_notes` (free text) | Recommendation is free text; options are not structured |
| Recommendation → decision | ✅ | ADR `status` (draft → in_review → signed), `signatories`, `committee`, `meeting_date`; ARB `status`, `decided_at`; TIME `time_decision`; exception `decision` | ADR signed date is in events, not a column |
| Decision → affected scope | ✅ | ADR ↔ cards, ARB `subject_card_id`, TIME decision `card_id` / `successor_id` / `initiative_id` | — |
| Decision → implementation | ❌ | No action entity linked to a decision (DATA_AND_FUNCTIONAL_GAP_ANALYSIS.md G3) | Cannot say whether a decision was carried out |
| Implementation → delivery | ⚠️ partial | Initiative and PPM (status reports, WBS completion); `assessment_decisions.progress`; card archive or lifecycle | No explicit "implemented" status on the decision |
| Delivery → outcome | ⚠️ partial | KPI cards (no history); card attribute changes (in events); capability maturity (no history) | No measured before/after |
| Outcome → benefit | ❌ | `planned_savings` (estimate only); `improvement_opportunities.status=realized` (count only, date approximated by `updated_at`) | No benefit amount, status, period, approver or evidence |
| Benefit → attribution | ❌ | — | No attribution share; no counterfactual |

**Conclusion.** Turbo-EA can trace **intervention → decision → scope** today. It **cannot verify** implementation, outcome or financial benefit. Any executive claim of "EA delivered X savings" is currently **unsupportable from system data**.

## 3. Recommended measurement model [Recommendation]

### 3.1 Governance effectiveness: four levels

| Level | Question | Measures (see EXECUTIVE_KPI_FRAMEWORK.md) | Evidence threshold |
|---|---|---|---|
| L1 Reach | Is governance applied where it should be? | B1 coverage, B2 early involvement | Review or ADR linked to the initiative |
| L2 Efficiency | Is it fast and not a bottleneck? | B7 turnaround, B9 / E5 stuck items | Timestamps |
| L3 Adherence | Are decisions and standards followed? | B3 compliance, B4 exceptions, B5 decision implementation, B6 corrective actions | Action closure with evidence |
| L4 Contribution | Does governed work perform better? | B8 cohort comparison, C1-C9 impact, D1-D9 financial | Outcome measured before/after **and** linked decision |

Report L1-L3 as **governance performance**. Report L4 only with the evidence and attribution rules below, labelled **"contribution"**, never as causation.

### 3.2 Benefit lifecycle

| Status | Meaning | Who sets it | Required evidence | Shown on the CEO view as |
|---|---|---|---|---|
| `forecast` | Expected, not yet costed | Benefit owner | Decision link | "Pipeline" (separate total) |
| `estimated` | Business-case estimate with method | Benefit owner | Business case document | "Estimated" (separate total) |
| `validated` | Finance agrees the method and baseline | Finance business partner | Baseline, method, approver, date | "Validated (not yet realised)" |
| `realised` | Finance confirms the actual in an accounting period | Finance | Actuals reference, period, approver | "Realised": the only figure called savings |
| `not_realised` | Did not materialise | Benefit owner + Finance | Reason | Counted in the realisation rate denominator |

**Rules.** Totals of different statuses are never summed. A benefit moves forward only with the evidence listed. Each benefit has exactly one owner and links to exactly one decision record (ADR, TIME decision, ARB review or improvement opportunity) plus its affected cards. Amounts carry currency and fiscal period (`fiscal_year.py` convention: the year is named after the calendar year it ends in).

### 3.3 Attribution

- **Default: no attribution.** A realised benefit is reported as "transformation benefit", not "EA benefit".
- **EA contribution** may be claimed only when the decision record shows that the EA intervention (ARB review, ADR, rationalization assessment) **preceded and shaped** the decision, and Finance ratifies an attribution share (proposal: a fixed policy share, e.g. 10-30%, agreed once by the CFO and the Chief Architect, not negotiated per item).
- **Avoided cost** requires a documented counterfactual (the option rejected in the ADR's `alternatives_considered`, with its cost) and Finance validation.

### 3.4 Non-financial benefits

Capability maturity uplift (C4), digitalized services (A5), automation (A6), risk reduction (C9) and beneficiary experience (A8) are recorded as KPI movements on `KPI` cards with `kpi_measurements` history. They are linked to the decision and initiative through existing relations (`relInitiativeToKPI`, `relObjectiveToKPI`).

## 4. Minimum implementation to make the chain verifiable [Recommendation]

1. **Decision actions**: reuse `todos` (or the mitigation-task pattern) linked to the ADR or ARB review; the decision shows "n of m actions closed".
2. **Benefit ledger**: one table, the statuses above, linked to existing decision records.
3. **KPI history**: `kpi_measurements` for existing KPI cards.
4. **Realisation timestamps**: `realized_at` on improvement opportunities; the signed date surfaced on ADR.
5. **Traceability view**: a drill-down that renders the chain for one decision (intervention → decision → actions → initiative → KPI → benefit), reusing the card detail and relation views.

## 5. What must not be claimed [Recommendation]

- `planned_savings`, `target_savings`, `annual_cost` or business-case estimates as savings achieved.
- A retired application's cost as a saving without Finance confirmation (licences and contracts may continue).
- A KPI improvement as caused by EA without the decision link and attribution policy.
- Governance volume (number of reviews or ADRs) as value.
