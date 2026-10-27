# Benefits Register

The **Benefits Register** (**Governance → Benefits Register**, `/benefits`) records the measurable business benefits expected from digital initiatives and architecture decisions, and tracks them until they are realised. Planned value, value reported by the business and value **confirmed by Finance** are kept apart everywhere: they are never added together.

## Who can do what

The register uses four permissions. No default role holds them; an administrator grants them under **Admin → Users & Roles**.

| Permission | Allows |
|---|---|
| `benefits.view` | See the register and non-financial outcomes |
| `benefits.manage` | Create and edit benefits, link initiatives, report actuals with evidence, record qualitative assessments, withdraw a benefit |
| `benefits.validate` | Validate the financial basis of a benefit (Finance) and reopen it |
| `benefits.confirm` | Confirm, reject or reverse a reported actual and allocate attributable amounts (Finance); close a benefit as not realised |

Every amount also needs **`costs.view`**. Without it the register and the reports show counts and statuses, but no amount.

A benefit linked to cards is shown only if you can see at least one of those cards. Cards you cannot see are left out of the benefit, and are kept when someone else edits it.

## Types of benefit

- **Financial**: *cost saving*, *cost avoidance* and *revenue*. A financial benefit has a currency (ISO code, for example SAR), which is kept as entered and never converted. Totals are always per currency.
- **Non-financial**: *productivity* and *other outcomes*. They never carry an amount and are never converted to money. Each one is either **measured by a KPI card** or **assessed qualitatively** by the business owner. If a productivity gain produces a real saving, record that saving as its own cost-saving benefit.

Each benefit names its **governing decision** (a signed decision record or an approved architecture review), or at least one **delivering initiative**, or both. A benefit without a decision is marked *No governance link*.

## Attribution to initiatives

A benefit can be linked to several initiatives. Each link is classified as **direct**, **contributing** or **not attributable**. The classification does not move any money by itself: only Finance allocates amounts, when it confirms an actual, each with a rationale. The allocations of one actual never exceed its amount, a *not attributable* initiative receives nothing, and nothing is allocated automatically — a single direct initiative is not given the full amount by default. Totals count each benefit once, however many initiatives it has. The contribution of enterprise architecture is shown only as counts (confirmed actuals with a governance link), never as money.

## Lifecycle of a financial benefit

1. **Planned.** The owner records the planned amount (one-time or annual), the expected fiscal year and the method and assumptions. A cost saving also needs a baseline (the annual run cost before the change); a cost avoidance needs the counterfactual cost and what was avoided.
2. **Validated by Finance.** A `benefits.validate` holder validates the basis. From then on the financial basis is locked; Finance can reopen it, with a reason.
3. **Actuals.** For each fiscal year, a `benefits.manage` holder reports the amount realised, with at least one evidence reference (for example an ERP voucher or a document link). It shows as *Reported, awaiting Finance* and does not count as realised.
4. **Finance confirmation.** A `benefits.confirm` holder confirms the actual with a Finance reference, and may allocate attributable amounts to initiatives, or rejects it with a reason. A confirmed actual can later be reversed with a reason.
5. **Closing.** A benefit can be withdrawn (if no actual is confirmed) or closed as *not realised*, always with a reason.

**Independent confirmation.** The person who confirms, rejects or reverses an actual must not have created the benefit, own it, have set its planned amount, or have reported that actual. This applies to everyone, administrators included; such a user sees why the buttons are not offered.

Every change is kept in the benefit's **History**, with who did it and when.

## Non-financial outcomes

- **Measured by a KPI**: the result is read from the KPI card's **verified** measurement for the fiscal year against its **ratified** target (*on target*, *off target*, *no verified measurement*, *target not ratified* …).
- **Assessed**: the business owner records an assessment for a fiscal year — *achieved*, *partially achieved* or *not achieved* — with a description and evidence. It is shown as **assessed**, never as verified KPI achievement.

## Executive reporting

The Executive tab's **Benefits** page shows, for the fiscal year of the selected period:

- **Planned value**: planned amounts of open benefits, not yet validated and validated, with one-time and annual amounts apart.
- **Reported, awaiting Finance**: actuals reported for the year that Finance has not confirmed.
- **Confirmed by Finance**: cost savings and revenue (FIN-01) and cost avoidance (FIN-02), and the **realisation rate** (FIN-04): confirmed value divided by the validated planned value of the benefits expected that year.
- **Attribution**: amounts Finance allocated as direct and contributing, the amount not allocated, and the totals by initiative.
- **Rationalization run-rate forecast**: the planned savings on rationalization decisions, an annual run-rate that is not tied to a fiscal year. It is never counted as realised. A decision already named by a benefit is left out of the forecast so its value is not counted twice.
- **Return on investment**: not calculated yet; it waits for the approval of the programme cost scope and the currency attestation.
- **Non-financial outcomes**: productivity and other outcomes, with KPI-verified results and assessed results shown apart.

The Overview's **business value** indicator shows the Finance-confirmed cost savings and revenue of the fiscal year, when they are in a single currency.
