# EA governance measurement model

**Status: design proposal.** It refines `docs/executive-dashboard-assessment/EA_GOVERNANCE_AND_ROI_MODEL.md`. KPI IDs refer to `FINAL_KPI_DICTIONARY.md` §3.3.

## 1. Three classes, never mixed

| Class | Meaning | KPIs | How it is shown |
|---|---|---|---|
| **Activity** | Governance happened | Review volume, ADR volume, GOV-01 coverage | Context, labelled "Activity"; no value claim |
| **Effectiveness** | Governance was timely, adhered to and acted on | GOV-02 early engagement, GOV-03 compliance, GOV-04 exception resolution, GOV-05 decision implementation, GOV-06 corrective actions, GOV-07 turnaround, GOV-08 bottlenecks | Targets and trends |
| **Impact (contribution)** | Governed work performs better / produces outcomes | GOV-09 governed vs ungoverned; benefits linked to governed decisions (BENEFITS_AND_ROI_SPECIFICATION.md) | Cohort comparison with sample sizes; "contribution, not causation" |

## 2. Lifecycle of a governed decision (entities reused)

| Step | Entity | Timestamp source | Gap closed by |
|---|---|---|---|
| 1 Intake / request | `arb_reviews.created_at` (ARB); ADR created | `created_at` | A distinct "request received" date is not needed (D-11 confirms `created_at`) |
| 2 Review | ARB `scheduled`; ADR `draft` → `in_review` | events | — |
| 3 Recommendation | ADR `alternatives_considered`, `decision`; ARB `decision_notes` | — | Optional structured options later (out of scope) |
| 4 Decision | ADR `signed` (signatories); ARB `approved` / `rejected` / `deferred` + `decided_at`; exception decision; TIME decision | events / `decided_at` | Surface the ADR signed timestamp from events in the API |
| 5 Implementation actions | **todos with `source_kind` / `source_id`** (DATA_MODEL_AND_RELATIONSHIPS.md §3.3) | todo status and due date | New (Phase 3) |
| 6 Delivery | Initiative / PPM (status reports, WBS completion), card archive or lifecycle, `assessment_decisions.progress` | events, reports | — |
| 7 Outcome | KPI card measurements (`kpi_measurements`), card attribute changes, risk residual | measurement period | New (Phase 2) |
| 8 Benefit | `benefits` linked to the decision | status transitions | New (Phase 4) |

## 3. Measurement rules

1. **Scope (GOV-01 denominator)**: initiatives meeting the "in scope" rule (D-10). Proposal: subtype `program` or `project`, and FY budget ≥ an admin-set threshold, or tag `eaReviewRequired`. The rule is a setting, not code.
2. **Early engagement (GOV-02)**: first ARB review or ADR linked to the initiative dated **before** the gate (D-11). Proposal: the ADM phase for Architecture Vision approved, else `Initiative.startDate`.
3. **Decision implemented (GOV-05)**: every action todo linked to the decision is done, **and** at least one action exists (a decision without actions is "no plan", reported separately). Window: decisions signed or approved ≥ 90 days before period end.
4. **Corrective action (GOV-06)**: union of decision actions, exception remediation actions (`source_kind=exception`) and risk mitigation occurrences. On time = completed ≤ due date.
5. **Exception resolution (GOV-04)**: an approved exception is resolved when closed (the card becomes compliant per scan, or the exception is rejected / withdrawn) before `expiry_date`. "Expired-but-active" = approved, past expiry, card still non-compliant.
6. **Turnaround (GOV-07)**: median working days (fiscal calendar, weekends per D-28) request → decision, per instrument.
7. **Bottleneck (GOV-08)**: thresholds as in the dictionary (proposals).
8. **Contribution (GOV-09)**: two cohorts of in-scope initiatives in the period, governed (GOV-01 true) vs not. Report the on-track rate of each, the counts, and suppress when either cohort has n < 5. Never labelled "impact of EA".

## 4. Data quality controls

- Decisions without linked cards are flagged ("unscoped decision").
- Actions without owner or due date are flagged and excluded from on-time rates.
- An ARB review with `decided_at` before `created_at` is flagged as invalid.

## 5. Authorization

Governance KPIs count only governance records whose subject card(s) the caller can read (module-mode `CardReadScope`). Records about hidden cards are omitted from counts, matching the "omit entirely" rule (`SECURITY_REMEDIATION_PLAN.md`). A KPI whose source permission (`arb.view`, `adr.view`, `tech_standards.view`) the caller lacks returns `restricted`.

## 6. Acceptance criteria (model level)

- Each governance tile shows its class label.
- GOV-05 is computable end-to-end for a test decision: ADR signed → two actions → both done → counted as implemented in the next period.
- GOV-09 shows cohort sizes and the suppression rule.
- Removing read access to a decision's subject card removes that decision from every governance count for that user.
