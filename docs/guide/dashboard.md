# Dashboard

The Dashboard is the first screen you see after logging in. It provides a **quick overview** of the entire enterprise architecture status.

![Dashboard - Top View](../assets/img/en/01_dashboard.png)

## Top Navigation Bar

At the top of the screen, you will find the **main navigation bar** with the following elements:

- **Turbo EA** (logo): Click to return to the Dashboard from any section
- **Dashboard**: Overview of the architecture status
- **Inventory**: Complete listing of all cards
- **Reports**: Visual and analytical reports
- **BPM**: Business Process Management (if enabled)
- **Diagrams**: Visual architecture diagram editor
- **EA Delivery**: Architecture initiative management
- **Todos**: Pending tasks and assigned surveys
- **Search cards**: Quick search bar with autocomplete
- **+ Create**: Button to quickly create new cards
- **Notification bell**: System alerts and [notifications](notifications.md)
- **Profile icon**: Language selection, theme toggle, notification preferences, and administration access
- **Sponsor**: A purple-to-pink button next to the version number in the profile menu opens a dialog explaining why sponsorship matters, with a link to the blog and one-time or monthly options via GitHub Sponsors

## Summary Cards

The main section of the Dashboard displays **summary cards** indicating:

- **Total number of cards**: Count of all components registered in the platform
- **Distribution by type**: How many elements of each type exist (Applications, Organizations, Objectives, Capabilities, etc.)
- **Status overview**: Quick visualizations of the overall status

Clicking on a type card navigates to the [Inventory](inventory.md) pre-filtered to that type.

![Dashboard - Bottom View with Charts](../assets/img/en/02_dashboard_bottom.png)

## Charts and Statistics

In the bottom section of the Dashboard you will find:

- **Distribution by type chart**: Shows the proportion of each card type in your landscape
- **Approval status**: Indicates how many cards are approved, pending, broken, or rejected
- **Data quality**: Overall percentage of information completeness across all cards
- **Recent activity**: A feed of the latest changes — who edited what and when

## Executive tab

The **Executive** tab is a one-page summary of delivery, money and risk for senior leadership. It is shown to roles that hold the **`reports.executive_dashboard`** permission — administrators have it automatically; grant it to any other role under **Admin → Users & Roles**. Every figure counts only the cards you are allowed to see, and card types an administrator has hidden are left out of every total.

The tab has three pages: **Overview**, **Decisions** and **Details**.

**Overview** is the CEO view: six indicators — strategy achievement, EA governance effectiveness, initiative delivery, services and automation, business value, and decisions and escalations — each on a tile that shows the value, the target, the previous period, the reporting period, how fresh the data is, the owner, a confidence label and a link to the records behind it. A **Reporting period** selector chooses a fiscal year or one of its quarters; a figure is measured as of the period's last day (or today, for the current period). An indicator whose source or rule has not been decided yet shows **Not available** with the reason, never zero: today that applies to strategy achievement, governance effectiveness, services and automation, and realised business value. Planned savings appear on the business-value tile as a **Forecast** only. Targets and owners read **No linked KPI card** until each indicator is linked to a KPI card, and a target will show as ratified only once its owner has approved it through a suitable approval step. Initiative delivery compares with the previous period using the status reports dated before it; other indicators say *No history yet*. A panel lists the **decisions needing attention** that you can open.

**Decisions** lists what needs executive attention now: **executive-escalated risks** (open risks rated critical, or high and past their target date — a strategic category alone does not escalate a risk), with open and mitigated risks counted separately; architecture decision records awaiting signatures; architecture reviews scheduled or deferred; and standard exceptions requested. Everyone with the Executive tab sees the counts; seeing the records themselves needs that module's own view permission (risks, decision records, architecture reviews, technology standards).

**Details** holds the figures described below.

The header shows when the figures were generated, the date of the latest initiative status report, and a **Reporting period** selector that chooses the fiscal year of the budget figures (the fiscal year follows **Admin → Settings → Fiscal Year Start**).

**Headline figures.** Each tile has an information icon with a plain-language definition, a link to the page behind it, and a label saying where the figure comes from: **Recorded** (counted from records in Turbo EA), **Self-reported** (taken from status reports), **Forecast** (a planned estimate), **Restricted** (you lack the permission) or **Not available** (nothing records it yet). Nothing on the tab is a Finance-verified figure.

- **Initiatives on track**: of the in-flight initiatives that have a current status report, the share whose latest report is on track on schedule, cost and scope (the worst of the three decides).
- **Reporting coverage**: how many in-flight initiatives have a current status report. It is shown separately so that missing reports are never hidden inside the health figure.
- **Budget execution**: actual cost recorded in the selected fiscal year divided by the budget planned for that year.
- **Open critical & high risks**, with the number overdue.
- **Planned savings**: the forecast from rationalization decisions (see below).

**Delivery.** Every in-flight initiative is **On track**, **At risk**, **Off track** or **Unknown / not reported**. An initiative without a status report is *Unknown / not reported* — never counted as healthy and never as at risk. Completed and on-hold initiatives are not in flight and are listed separately. An administrator can set a **staleness threshold** (**Admin → Settings → Initiative report staleness**); reports older than it then also count as not reported. There is no default: until it is set, every existing report counts and the tab says so. When the PPM module is off, each initiative's own **Status** field is used instead of status reports. Budget and actual are for the selected fiscal year only — years are never added together, and a cost line with no date belongs to no year (the tab says how many there are).

**Planned savings.** Savings planned on rationalization decisions (active and completed assessments) are counted **once per application**: if two assessments give the same estimate, it counts once. If they give different estimates, the application is a **conflict**: it is left out of the total until someone reconciles the estimates, and the tab lists it with every estimate. The list names applications and assessments, so it also requires the **`rationalization.view`** permission; without it you see only how many conflicts there are. Planned savings are always a **Forecast**; **Realised savings** are shown separately as *Not available* until verified benefits are recorded. Planned savings are not yet tied to a fiscal year, because decisions carry no financial period.

**Risk exposure** shows open risks by level, and **Processes** shows automation level and maturity, with process documentation coverage (processes with a published flow) as a separate line — documentation is not automation or maturity.

**Repository metrics (specialist)** is a collapsed section with card counts, **data completeness** (the share of weighted fields filled in, not a measure of correctness), **repository review status** (whether cards were reviewed — not architecture compliance), the largest card types and the lifecycle mix, where the end-of-life slice reads **Past planned end-of-life**.

**Money and permissions.** Budget, actual and planned-savings figures require the **`costs.view`** permission; without it they show **Restricted** instead of a number. Amounts are shown in the currency set under **Admin → Settings → Currency**, which is the currency they were recorded in: nothing is converted, and amounts in different currencies are never added together. A section whose module is switched off says so instead of showing zeros.

## Workspace tab

The **Workspace** tab pulls together everything assigned to you: favorites, todos, pending surveys, recent activity on your cards, and the **Cards I Have a Role In** section.

That last section groups cards by the stakeholder role you hold (Application Owner, Business Owner, etc.) and lists the cards under each. If your role grants the `stakeholders.view` permission (admin, member and viewer roles by default), a small **person search** icon next to the section title lets you point it at **someone else** — pick a user from the autocomplete and the section refetches and re-renders with that user's roles and cards. The section title flips to "Roles held by {name}". Click the small close icon to return to your own roles. Useful for answering "what does this person own?" in one click.

## Admin tab — Stakeholder directory

Administrators (any role with `admin.users`) get a **Stakeholder directory** widget at the bottom of the Admin tab. It lists every card type that has at least one stakeholder, with the count of distinct holders for each. Expand a card type to see its roles, and inside each role the users who hold it together with the number of cards they cover. Click a user chip to expand its card list inline — each card name is itself a link to the card detail page. The whole tree (card type → role → user → cards) comes back in a single round-trip, so navigation is instant.

A **name filter** at the top of the widget narrows the tree to users matching the typed name or email; matching card types auto-expand so the matches are visible without an extra click. Use it to answer "where does Alice appear in the org?" in one second.

Beyond the directory, a small **hover popover** opens whenever the cursor pauses on a stakeholder name elsewhere in the app — on a card's Stakeholders tab, on a risk owner in the Risk Register, or on the Risk Detail page — and shows that user's full role-grouped stakeholder portfolio. Click any card in the popover to jump to it. The popover fetches once per user per session.
