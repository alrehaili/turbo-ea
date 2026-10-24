# Benefits register and ROI specification

**Status: specification, not implemented.** It satisfies FR-13, FR-14 and FR-19. Planned savings are never treated as realised (confirmed decision C-06).

## 1. Benefit taxonomy

| Dimension | Values | Rule |
|---|---|---|
| `benefit_type` | `cost_saving` · `cost_avoidance` · `revenue` · `productivity` · `non_financial` | Productivity (hours / FTE) and non-financial outcomes are **reported separately** and never enter cash totals or ROI (FR-19) |
| `status` | `forecast` → `estimated` → `validated` → `realised`; or `not_realised` / `withdrawn` | Forward-only except an explicit reopen by Finance; each step requires its evidence |
| `recurrence` | `one_time` · `recurring` (+ `recurring_months`) | A recurring benefit is realised per financial period; annualised figures are labelled as such |

| Status | Meaning | Set by (permission) | Required to enter |
|---|---|---|---|
| forecast | Expected; no costing | `benefits.manage` | title, type, owner, decision or initiative link |
| estimated | Business-case estimate | `benefits.manage` | estimated_amount, method note, baseline (if cost) |
| validated | Finance agrees method, baseline and counterfactual | `benefits.validate` | validated_amount, baseline_amount, counterfactual (avoidance), `validation` evidence |
| realised | Finance confirms the actual in a financial period | `benefits.confirm` | realised_amount, financial period, finance_reference, `finance_confirmation` evidence, ≥ 1 `implementation` evidence |
| not_realised | Did not materialise | `benefits.confirm` | reason |

## 2. Traceability (FR-20)

`EA intervention` (ARB review / ADR / rationalization assessment / maturity score) → `recommendation` (ADR options, TIME decision) → `management decision` (`decision_kind` + `decision_id`) → `implementation` (decision action todos; `initiative_id`; card retirement) → `business outcome` (`kpi_card_id` + `kpi_measurements`; card changes) → `verified benefit` (status `realised`, Finance-confirmed).

A benefit **must** link to exactly one decision record, or to an initiative when no decision exists (then flagged "no governance link" and excluded from the EA-contribution view).

## 3. Field specification (`benefits`)

| Field | Type | Required | Notes |
|---|---|---|---|
| reference | `B-000001` | auto | monotonic, like `R-000123` risks |
| title, description | text | title | |
| benefit_type, recurrence, recurring_months | enum, int | type | |
| currency | ISO 4217 | yes | set explicitly on every benefit; preserved as entered; never converted (D-05, approved); totals are per currency |
| baseline_amount | decimal | for cost_saving | annual run cost before the change |
| counterfactual_amount + counterfactual_note | decimal + text | for cost_avoidance | cost of the rejected alternative (e.g. from ADR `alternatives_considered`) |
| forecast_amount / estimated_amount / validated_amount / realised_amount | decimal | per status | each kept; realised vs forecast variance = realised − validated |
| financial_period_start / _end | date | for realised | fiscal-year aligned (`fiscal_year.py`) |
| expected_realisation_date | date | estimated+ | drives FIN-04 |
| owner_id | user | yes | benefit owner |
| verifier_id | user | validated+ | Finance business partner |
| validated_by / validated_at | user / ts | validated | system-set |
| finance_confirmed_by / finance_confirmed_at / finance_reference | user / ts / text | realised | system-set + ERP reference |
| decision_kind + decision_id | enum + UUID | yes* | `adr` / `arb` / `rationalization_decision` / `improvement_opportunity` |
| initiative_id | card FK | recommended | delivering initiative |
| kpi_card_id | card FK | for non_financial | outcome KPI |
| attribution_method | enum | validated+ | see §5 |
| attribution_rationale | text | validated+ | |
| attributable_amount | decimal, nullable | only via the approved method | never a fixed % (C-07) |
| affected cards | `benefit_cards` | — | |
| evidence | `benefit_evidence` | per status | kinds: implementation, baseline, validation, finance_confirmation |

## 4. Calculation rules

1. **No cross-status sums.** Each status has its own total. FIN-03 presents forecast, estimated and validated side by side.
2. **No double counting.**
   - (a) one benefit per (decision, benefit_type, affected scope); duplicates are flagged on create;
   - (b) a rationalization decision's `planned_savings` is shown as Forecast **only until** a benefit links to that decision;
   - (c) cost avoidance and cost saving are never added together;
   - (d) a recurring benefit counts once per period;
   - (e) infrastructure cost counted on the asset, not again on the application.
3. **Period**: realised amounts count in the fiscal period(s) of `financial_period_start..end`, prorated by month for multi-period recurring benefits.
4. **Realisation rate (FIN-04)** = Σ realised ÷ Σ validated for benefits with `expected_realisation_date` in the period.

## 5. Attribution (no fixed percentages; method to be approved, D-14)

The plan does **not** set an EA attribution percentage. Candidate methods, recorded per benefit in `attribution_method`:

| Method | Description | Amount effect |
|---|---|---|
| `full_transformation` (default) | Benefit reported as a transformation benefit; no EA share claimed | `attributable_amount` = null; excluded from the EA-ROI view |
| `ea_decisive` | Documented evidence that the EA intervention preceded and determined the decision (e.g. ADR selected the option producing the saving) | Finance decides the amount with a rationale; may equal the realised amount |
| `ea_contributing` | EA was one of several contributors | Finance-assessed amount with a rationale; no default share |
| `not_attributable` | No EA link | excluded |

Finance (`benefits.validate`) sets the method and amount. The dashboard shows totals per method, never one blended "EA value".

## 6. ROI (FIN-08)

```
ROI(period) = ( Σ realised cash benefits attributable in period  [FIN-01 + FIN-02, per approved method]
              − programme cost in the same period              [FIN-06, scope D-15] )
              ÷ programme cost in the same period
```

- Only `realised`, Finance-confirmed benefits. Productivity and non-financial benefits are excluded.
- The same period window for numerator and denominator (FY, or a rolling multi-year window chosen in D-15).
- Shown as **"Not available"** unless: every included benefit is confirmed, programme cost for the window exists, and the attribution method is approved.
- The composition drawer lists every contributing benefit and cost line.

## 7. Workflow and permissions (new keys, `core/permissions.py`)

| Key | Grants | Default roles (proposal, D-03) |
|---|---|---|
| `benefits.view` | View the register and amounts (also requires `costs.view` for money) | admin; executive role |
| `benefits.manage` | Create and edit; forecast / estimated transitions; evidence | admin; benefit owners' role |
| `benefits.validate` | Validate (method, baseline, attribution) | admin; Finance role |
| `benefits.confirm` | Confirm realised / not realised | admin; Finance role |

Segregation rule: the user who created or estimated a benefit cannot also confirm it (enforced server-side; D-29).

## 8. Acceptance criteria

- A benefit cannot reach `realised` without finance_reference, a financial period and the required evidence kinds.
- FIN-01 includes only realised cash benefits in the selected FY.
- Planned savings disappear from Forecast once a benefit links to the decision.
- ROI shows "Not available" when any condition in §6 fails.
- A user without `costs.view` sees no amounts anywhere (screen, export, drill-down).
- All transitions appear in the benefit's history and in the security audit log.
