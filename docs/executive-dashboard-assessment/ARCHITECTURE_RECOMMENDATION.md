# Architecture recommendation

## Options

| Option | Maintainability / data reuse | Security / authorization | Scalability | Complexity | Assessment |
|---|---|---|---|---|---|
| A. Inside Turbo-EA | Highest reuse of models, report services, routing, i18n, design system and drill-downs | Reuses JWT, `PermissionService`, `CardReadScope` and cost redaction | Suitable for the existing application deployment; purpose-built aggregate APIs can scale independently | Lowest incremental complexity | Best starting option |
| B. Separate executive frontend using existing APIs | Duplicates UX, i18n/RTL, session and navigation concerns; can reuse APIs only where sufficient | Requires a secure BFF/API gateway and strict parity with Turbo-EA authorization | Independently deployable/scalable | High: identity, aggregation contracts, data freshness and drill-down handoff | Justified only for a materially separate executive product/channel |
| C. Hybrid | Internal dashboard can reuse UI while a narrowly scoped external display uses read models | Can preserve central API authorization if read APIs are designed correctly | Enables later high-scale/public-board style display | Medium/high: two experiences and two contracts | Sensible evolution path, not phase-one default |

## Recommendation: A, with an internal read-model boundary

Implement the executive dashboard inside the existing Turbo-EA frontend and backend, but expose purpose-specific, permission-aware read APIs rather than aggregating every card type in the browser. This keeps the data-driven metamodel, current reporting services, bilingual MUI/RTL layer, existing drill-down paths and enforcement mechanisms. It also minimizes risk that an independent UI inadvertently exposes cost or card data outside the caller’s scope.

The implementation plan, once approved, should establish a dashboard query layer that:

- reuses `CardReadScope` and cost access enforcement on every aggregate;
- returns metric value, target, period, trend, freshness, calculation version, confidence and drill-down filter;
- differentiates unavailable, partial, estimated, forecast, validated and realised facts;
- caches/rolls up expensive aggregates without making a financial KPI stale or unauditable;
- makes runtime metamodel field/schema checks explicit; and
- retains a stable API contract for a future hybrid/external frontend.

Do not create a separate operational database or duplicate the core inventory merely for the dashboard. A finance-system integration/read model may be necessary for verified benefits, but its source ownership and reconciliation must be defined by Finance before dashboard development.

