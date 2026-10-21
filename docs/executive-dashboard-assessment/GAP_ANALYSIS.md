# Gap analysis

## Already supported and reusable

- Data-driven EA inventory, relationships, hierarchy, lifecycle, approval and data-quality concepts.
- Capability, process, application, technology, initiative, objective/pillar, roadmap and target-architecture building blocks.
- BPM automation/maturity classifications and diagrams; PPM budget/cost/status/task data.
- Risk register, mitigation tasks, ARB reviews, ADRs, ADM gates, standards/exceptions, maturity and NORA programme modules.
- Existing reporting/chart infrastructure and permission-aware aggregation endpoints.

## Priority gaps

| Gap | Effect on executive dashboard | Priority | Required response |
|---|---|---|---|
| No finance-verified benefits model | Cannot claim savings, avoidance, ROI or realised benefit | Critical | Add governed benefit-realisation data/process with finance approval and evidence |
| No common KPI catalog/fact history | KPI targets, trends, comparisons and auditability cannot be consistently delivered | Critical | Define KPI metadata, targets, period facts, calculation version and provenance |
| No universal governance intake/action/closure chain | Coverage, early engagement, implementation and turnaround KPIs are weak | High | Model governance case/request, decision, action, due date, owner, closure/evidence |
| Incomplete digitalization semantics | “Digitalized service” is not safely measurable | High | Define/standardize service and digitalization taxonomy with evidence and ownership |
| Automation data is classification-oriented | Automation percentage is possible only after business rules; realised automation impact is absent | High | Agree threshold, denominator and periodic process assessment/evidence |
| Target-realisation lacks delivery proof | Architecture-state cards alone cannot establish delivered outcomes | High | Relate target elements/roadmap milestones to initiatives and verified delivery status |
| Portfolio costs are not finance reconciled | Spend/benefit/ROI may be misleading | High | Finance source-of-record, currency, fiscal calendar and reconciliation status |
| Relationship/data completeness is unverified | Cross-domain KPI denominators can be biased | High | Data stewardship, quality rules, exception management and adoption monitoring |
| Snapshot history is narrow | Historical executive trends are unavailable for most KPIs | High | Periodic KPI fact capture/backfill with retained calculation context |
| Executive UX is absent | Existing dashboard remains operational, not CEO-oriented | Medium | Design executive dashboard information architecture and bilingual acceptance criteria |

## Architecture and data risks

1. JSONB/metamodel flexibility means a field can exist in one workspace but not another; KPI logic must check schema/version and never assume a seed default is populated.
2. Cost visibility is deliberately permission-sensitive. Aggregates can leak restricted values if a new endpoint bypasses `CardReadScope` or cost filtering.
3. Manual RAG/status fields and self-assessment can be useful leading indicators but are not audited evidence of business outcome.
4. Planned rationalization savings must stay visually and semantically separate from verified financial benefits.
5. Existing reports use different domain-specific denominators. A cross-portfolio executive KPI must publish inclusion/exclusion rules and data freshness.

## Sequenced next steps (assessment only)

1. Establish an executive KPI governance workshop: definitions, accountability, thresholds, periods, data sources, finance-verification rules and drill-down rights.
2. Profile a representative workspace for actual type schemas, field completeness, relation coverage, cost data and module enablement.
3. Select a small phase-one set that can be honestly calculated from present data (portfolio delivery RAG, process automation classification, risk exposure, repository/architecture health, planned rationalization pipeline).
4. Specify the benefit-realisation, governance-action and KPI-history data products before committing to ROI or financial impact visuals.
5. Create a bilingual UX prototype and validate it with CEO/ExCo, Finance, EA governance, portfolio and process owners.

