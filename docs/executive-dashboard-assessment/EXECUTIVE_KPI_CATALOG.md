# Executive KPI catalog

Definitions are proposals, not current implemented calculations. “Available” means the raw data exists in code; it does not mean it is complete or validated.

| KPI | Business definition and proposed formula | Availability / source | Missing information and limitation | Recommended owner |
|---|---|---|---|---|
| EA review coverage | % in-scope initiatives/solutions with an ARB/ADM review in period = reviewed ÷ eligible | Partial: `arb_reviews`, ADM, initiatives | Eligibility rule and universal initiative-to-review linkage absent | Chief Architect / EA Governance |
| Early governance engagement | % reviewed before approval/funding/design threshold = early reviews ÷ reviewed | Partial: ARB `created_at`/`decided_at`, initiative dates | Request/intake and funding/design milestone timestamps absent | EA Governance Office |
| Architecture compliance | % in-scope items compliant at assessment date | Partial: standards scan/exceptions, card approvals | Scope, evidence, pass/fail semantics and denominator not uniform | Domain Architecture + Compliance |
| EA decision implementation | % signed ADR/ARB decisions with closed implementation actions | Partial: ADR/ARB decisions | No universal decision-action/closure model | Decision owner / PMO |
| Exception resolution | % exceptions closed before expiry; age of open exceptions | Partial: tech-standard exceptions | Expiry, remediation proof, and a canonical exception universe must be confirmed | Standards owner |
| Corrective-action closure | % actions closed by due date | Partial: risk tasks/ADM artefacts/todos | No cross-governance corrective-action entity | Control owner / PMO |
| Governance turnaround time | Median request-to-decision days | Partial: ARB timestamps, approval steps | Request timestamp and common case identifier absent | EA Governance Office |
| Application redundancy eliminated | Count/cost of applications actually retired after approved eliminate/consolidate decision | Partial: rationalization decisions, application lifecycle/successor | Planned decisions only; retirement verification, date and realised saving absent | Application Portfolio owner |
| Technology debt reduction | Change in approved debt score/value over period | Missing | Uniform debt score, baseline and remediation proof absent | CTO / Technology Architecture |
| Business capability improvement | Weighted actual maturity change for target capabilities | Partial: capability maturity attributes, maturity module | Baseline/target/assessment linkage and weighting absent | Business Capability owner |
| Digitalized services % | Digitalized active services ÷ eligible active services × 100 | Partial | Standard Service entity/digitalization definition and evidence absent | Service owner / Digital Office |
| Automated processes % | Processes at/above agreed automation level ÷ eligible active processes × 100 | Partial: `BusinessProcess.automationLevel`, process assessments | Taxonomy threshold, exclusions and evidence quality absent | Process Excellence owner |
| Integration improvement | % priority interfaces meeting agreed health/standard target, or reduction in manual handoffs | Partial: interfaces/relations and integration-status report | Priority, baseline, performance/SLA telemetry absent | Integration Architecture owner |
| Target architecture realization | Weighted planned target-state elements delivered/approved/operational ÷ target scope | Partial: `architecture_state`, `change_type`, successor, roadmaps | Delivery evidence, baseline scope and weighting absent | Enterprise Architect / Transformation Office |
| Verified cost savings | Finance-approved recurring/non-recurring savings realised in period | Missing | Planned savings must not be counted; no verification ledger | CFO Finance Business Partner |
| Avoided investment | Finance-approved avoided spend with counterfactual and decision evidence | Missing | No counterfactual/baseline/approval data | CFO / Investment Committee |
| Recurring cost reduction | Annualised finance-verified run-cost reduction from approved baseline | Missing | No validated baseline or realised actuals per benefit | Finance + service/application owner |
| EA programme costs | Approved EA operating/project cost in period | Partial: generic cost fields/PPM lines | EA cost centre/tagging and allocation rules absent | EA Office + Finance |
| EA-attributable ROI | `(verified EA-attributable benefits − EA programme cost) ÷ EA programme cost` | Missing | Attribution policy, verified benefits and programme cost ledger absent | CFO + Chief Architect |
| Forecast versus realised benefits | `(realised verified benefit − approved forecast)`, by benefit/period | Missing | Benefit forecast, periodisation, status and verification missing | Benefits Realisation Office |
| Strategic investment alignment | % spend / initiatives weighted by mapped strategic objective and objective priority | Partial: initiative-objective relations, PPM spend | Objective target/priority, allocation and relation completeness must be governed | Strategy Office / Portfolio Management |
| Executive risks/escalations | Count/value of open critical risks/overdue mitigation/escalated decisions | Partial: risk register and mitigation occurrences | Escalation threshold, executive owner and decision disposition absent | CRO / Executive Secretariat |

## Measurement guardrails

Do not label `target_savings`, `planned_savings`, business-case estimates, or an application’s `annual_cost` as realised or verified benefit. Retain financial status (`forecast`, `estimated`, `validated`, `realised`), approver, evidence reference, accounting period, source system, currency and calculation version for every financial measure.

