# API and backend design

**Status: design proposal, not implemented.** It follows the backend conventions in `CLAUDE.md`: routes in `backend/app/api/v1/` registered in `router.py`, `async` handlers, `PermissionService`, `CardReadScope`, no raw SQL, events with `db=`, no DB session held across slow work, the OpenAPI spec regenerated with `scripts/dump_openapi.py`.

## 1. Layering

```
api/v1/executive/                 thin route handlers (auth, scope, period, filter parsing)
   overview.py  transformation.py  governance.py  impact.py
   financial.py services.py  portfolio.py  decisions.py  benefits.py  kpis.py
services/executive/               pure builders + loaders (mutation-testable; mutmut skips decorated handlers)
   context.py        ExecContext(read_scope, can_view_costs, can_view_benefits, period, org_filter, currency)
   population.py     scoped card populations (visible types, org subtree, ACTIVE)
   kpi_registry.py   metric_key → builder, version, required permissions
   transformation.py governance.py impact.py financial.py services.py portfolio.py decisions.py
   snapshots.py      daily capture + period freeze into metric_snapshots
services/benefit_service.py       benefit CRUD + status transitions (flush, never commit)
```

The phase-one modules `services/executive_dashboard.py` and `api/v1/executive_dashboard.py` are **refactored into** this layout (their builders move into `services/executive/*`). `services/bpm_dashboard_service.py` is kept and reused.

## 2. Request context

Every executive endpoint takes `?period=FY2027` or `FY2027-Q2` (default: the current FY via `fiscal_year.current_fiscal_year`) and `?org=<card_id>` (optional; validated readable via `require_card_readable`, else 404).

`ExecContext` is built once per request:

- `read_scope = CardReadScope.load(db, user)`, module mode;
- `can_view_costs = has_app_permission(costs.view)`;
- `can_view_benefits = has_app_permission(benefits.view)` (D-03);
- `period` from `fiscal_year.py`;
- `org_filter`: subtree card ids (D-07);
- `currency` from settings (CR-05).

Builders never re-derive permissions.

## 3. Response contract (every KPI)

```json
{
  "metric_key": "TR-03",
  "value": 0.83,
  "display": {"numerator": 5, "denominator": 6, "unit": "%"},
  "status": "ok | not_available | not_reported | insufficient_data | restricted",
  "breakdown": [{"key": "onTrack", "count": 5}, {"key": "notReported", "count": 14}],
  "target": 0.75, "baseline": 0.6, "direction": "higherIsBetter",
  "delta_prev_period": 0.08, "trend": [{"period": "FY2027-Q1", "value": 0.75}],
  "confidence": "medium", "completeness": 30.0,
  "as_of": "2026-10-22T00:00:00Z", "period": "FY2027",
  "calculation_version": "1", "currency": null,
  "owner": {"id": "…", "display_name": "…"},
  "kpi_card_id": "…", "drill_down": {"path": "/ppm", "query": {"health": "offTrack"}}
}
```

- `target`, `baseline`, `direction` and `owner` come from the KPI card (`metricKey`).
- `trend` comes from `metric_snapshots` and is **omitted for restricted readers** (landscape-wide facts).
- Owner shape is `_user_response_lite` (no email).
- A money KPI without `costs.view` returns `status: "restricted"`, with `value`, `breakdown` and `trend` set to null.

## 4. Endpoints

| Method | Path | Purpose | Gate | Phase |
|---|---|---|---|---|
| GET | `/reports/executive/overview` | Six landing KPIs + top-5 decisions | `reports.executive_dashboard` | 2 |
| GET | `/reports/executive/transformation` | TR-01..06, DEC-04 | same | 5 |
| GET | `/reports/executive/governance` | GOV-01..09 | same (each KPI additionally needs its source permission, else `restricted`) | 3 |
| GET | `/reports/executive/impact` | IMP-01..08 | same | 4 |
| GET | `/reports/executive/financial` | FIN-01..10 | same + `costs.view` (page-level 403 if absent; tile hidden in nav) | 4 |
| GET | `/reports/executive/services` | SVC-01..06 | same | 5 |
| GET | `/reports/executive/portfolio` | PRT-01..05 | same | 1 (relocation), 5 |
| GET | `/reports/executive/decisions` | DEC-01..05 list, paginated | same | 2 |
| GET | `/reports/executive/kpi/{metric_key}/drilldown` | Records behind a KPI value (scoped, paginated) | same + source permission | 2 |
| GET | `/reports/executive/traceability/{decision_kind}/{id}` | Chain view (FR-20) | same + source permission | 4 |
| GET | `/reports/executive` | **Kept** for one release as a compatibility alias of `/overview`, then removed | — | 2 |
| GET/POST | `/kpis/{card_id}/measurements` | List / add a measurement | `inventory.view`+card read / `kpis.measure` (new, D-03) or card-level `card.edit` | 2 |
| PATCH | `/kpi-measurements/{id}` | Correct / verify | owner or `kpis.measure` | 2 |
| GET/POST | `/benefits` | List (filters: status, type, period, decision, initiative) / create | `benefits.view` / `benefits.manage` | 4 |
| GET/PATCH/DELETE | `/benefits/{id}` | Read / edit (not status) / delete draft | as above | 4 |
| POST | `/benefits/{id}/estimate`, `/validate`, `/confirm`, `/not-realised`, `/withdraw` | Status transitions with evidence | `benefits.manage` / `benefits.validate` / `benefits.confirm` | 4 |
| POST | `/benefits/{id}/evidence`, DELETE `/benefit-evidence/{id}` | Evidence links | `benefits.manage` | 4 |
| GET/POST | `/adr/{id}/actions`, `/arb/{id}/actions` | Decision actions (todos with source) | `adr.view` / `adr.create` (or sign) · `arb.view` / `arb.manage` | 3 |

Existing endpoints changed by the **Security Remediation Track** are in `SECURITY_REMEDIATION_PLAN.md` §3. Those changed by feature **Phase 1** (KPI correctness) are in `FINAL_KPI_DICTIONARY.md` §2.

## 5. Builders and rules

- One builder per `metric_key`. Signature `async def build(ctx: ExecContext, db) -> MetricResult`. The pure part (`summarize_*`) is separate from loading (the same split as phase one, `executive_dashboard.py`).
- Builders that need an unscoped landscape figure for a snapshot run inside `snapshots.py` only, with an unrestricted context, and never serve a user directly.
- Visible-type rule (CR-06): `population.visible_types_clause()` is used by every builder and by `/reports/dashboard` (Overview).
- Hidden or unreadable cards are excluded **before** aggregation. Totals are computed from the same filtered set as the breakdowns (no total from a separate unscoped query).
- Money (D-05, approved): every amount carries `currency`; aggregates are grouped per currency and never converted; a mixed set returns per-currency values with `"mixed_currency": true`.
- Planned savings (D-24, approved): dedupe by identity + financial period; conflicts are returned in `conflicts[]` with candidate values and excluded from `total`.
- Initiative health (D-02, approved): four states + a separate `coverage`; the staleness threshold is read from settings and is unset by default.
- Small-group suppression (SR-04, D-20): when `org` is set and the caller is restricted, any breakdown cell with n < threshold returns `suppressed: true` instead of a value.

## 6. Snapshots and period freeze

- The daily loop (`_kpi_snapshot_loop`) iterates `kpi_registry` and upserts `metric_snapshots(period_type="day")`. It runs inside `startup_lock`-safe, idempotent code; no session is held across non-DB work.
- On the first run after a quarter or FY closes, it writes `period_type="quarter"` / `"fy"` rows once (frozen; later runs skip existing keys).
- A backfill command reconstructs past quarters where events allow (optional, flagged `confidence=low`).

## 7. Events and audit

- Benefit and measurement writes publish `benefit.*` / `kpi_measurement.*` events with `db=`. Status transitions record `{"status": {"old", "new"}}`.
- Finance confirmation and validation also write a security audit-log entry (`audit_log.record`, `items=[{"kind": "benefit.confirmed", …}]`). The new kinds are added to `AUDIT_ITEM_KINDS` + templates in all locales (CLAUDE.md three-place rule).
- Exports (`FR-18`) call the existing data-export audit path.

## 8. Performance

- One request per page; each builder runs one or two grouped queries over the scoped population, no N+1.
- Heavy historical figures come from `metric_snapshots`.
- Optional per-(scope hash, period, org) cache of 5-15 min, invalidated on relevant events.
- Respect the 30-connection pool: no parallel endpoint fan-out from the frontend.

## 9. Testing (project validation approach, run in CI, not now)

| Layer | Tests |
|---|---|
| Builders | `backend/tests/services/executive/test_*.py`: pure builders over fixture rows, including not-reported, restricted and dedupe cases |
| Endpoints | `backend/tests/api/test_executive_*.py`: success, 403 without the permission, `restricted` without `costs.view`, a hidden-type card excluded from counts **and** totals |
| Disclosure regression | `SECURITY_REMEDIATION_PLAN.md` §6 (R1-R7): sentinel sweep fixtures, count / chart / money / governance-record / export tests, `gather_*` scope check |
| Read-scope guard | `tests/services/test_card_read_scope_guard.py` passes for every module (allowlist only with a reason) |
| Migrations | timestamp-default guard; workspace-transfer id-bearing guard; round-trip tests |
| Mutation | diff mutation score per `scripts/mutation/floors.toml` (builders are plain functions so mutmut can mutate them) |
