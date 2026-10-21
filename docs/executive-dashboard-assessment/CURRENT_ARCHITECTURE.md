# Current architecture baseline

## Assessment boundary

This is a static code assessment of the repository on 2026-10-21. No running instance, database contents, browser session, build, test, migration, or configuration was inspected. Consequently, source-code capabilities are **implemented in code**, while whether they are enabled, populated, or used correctly in a customer workspace is **unverified**.

## Technology and deployment

| Area | Implemented baseline | Evidence |
|---|---|---|
| Frontend | React 19 + TypeScript + Vite; React Router; lazy route loading | `frontend/package.json`, `frontend/src/App.tsx` |
| UI/design system | Material UI 6, Emotion, Material Symbols, Cairo font | `frontend/package.json`, `frontend/src/theme/` |
| Charts/visualisation | Recharts, React Flow, AG Grid, BPMN.js, Gantt | `frontend/package.json` |
| Backend | Python 3.11+, FastAPI async handlers, Pydantic, SQLAlchemy async | `backend/pyproject.toml`, `backend/app/api/v1/` |
| Persistence | PostgreSQL-oriented SQLAlchemy models; JSONB for metamodel attributes | `backend/app/models/card.py`, `backend/app/models/relation.py` |
| Schema evolution | Alembic | `backend/alembic/` |
| Runtime | Docker Compose with backend, frontend, edge nginx, optional Ollama/MCP | `docker-compose.yml`, `README.md` |

## Application modules and navigation

The route map is substantial and split at page boundaries with `lazy()` in `frontend/src/App.tsx`. Implemented modules include Dashboard, Inventory/Cards, View Library, Layers, Reports, BPM, PPM, Diagrams, EA Delivery (SoAW/ADR/ADM), GRC, NORA programme, maturity, reference models, rationalization, scenarios, catalogues, administration, web portals and TurboLens. Navigation composition and feature/permission filtering are implemented in `frontend/src/layouts/AppLayout.tsx` and `frontend/src/layouts/navItems.ts`.

The current home dashboard is operational/repository-oriented, not an executive performance dashboard. It contains Overview, My Workspace, and Admin tabs (`frontend/src/features/dashboard/Dashboard.tsx`). Overview calls `GET /reports/dashboard`, shows repository count, data quality, approval distribution, lifecycle distribution, recent activity, and attention links (`frontend/src/features/dashboard/OverviewTab.tsx`; `backend/app/api/v1/reports.py:128`).

## Core domain model

Turbo-EA is data-driven: `Card` is the inventory aggregate and `CardType.fields_schema` defines configurable fields. A card has type, subtype, parent hierarchy, lifecycle JSON, attribute JSON, status, approval status, data-quality score, architecture state/change type/successor and freshness metadata (`backend/app/models/card.py`). Typed `Relation` rows connect two cards with relation attributes (`backend/app/models/relation.py`); relation type schemas define the allowed pairs and fields (`backend/app/models/relation_type.py`). Built-in types and relations are seed defaults, not hardcoded application entities (`backend/app/services/seed.py`).

Important purpose-built tables supplement cards:

- PPM: `ppm_status_reports`, `ppm_cost_lines`, `ppm_budget_lines`, tasks, WBS, dependencies and PPM risks.
- BPM: process diagram, element, message-flow, version and process-assessment tables.
- Governance: `arb_reviews`, `architecture_decisions`, `statement_of_architecture_works`, `approval_steps`, `ea_principles`, standards/exceptions.
- GRC: `risks`, `risk_cards`, mitigation tasks/occurrences.
- Portfolio action: `rationalization_assessments` and `assessment_decisions`.
- Trend history: `kpi_snapshots`, limited to repository total/data quality/approval/broken counts (`backend/app/models/kpi_snapshot.py`).

## APIs and reusable services

REST routes are registered centrally in `backend/app/api/v1/router.py`; public API documentation is generated to `docs/api/openapi.json`. Reusable aggregation endpoints relevant to an executive dashboard include:

- `GET /reports/dashboard`, `/portfolio`, `/cost`, `/cost-treemap`, `/capability-heatmap`, `/roadmap`, `/gap-analysis`, `/strategy-map`, `/data-quality`, `/freshness`, `/integration-status` — `backend/app/api/v1/reports.py`.
- `GET /reports/bpm/dashboard` and BPM matrices/maps — `backend/app/api/v1/bpm_reports.py`.
- `GET /reports/ppm/dashboard`, `/gantt`, and PPM line/report APIs — `backend/app/api/v1/ppm_reports.py`, `ppm.py`.
- Risk metrics/register — `backend/app/api/v1/risks.py`.
- ARB, ADR, ADM, maturity, NORA and rationalization APIs — corresponding route files in `backend/app/api/v1/`.

Services that should be reused rather than reimplementing logic include `card_read_scope.py` (row-level card visibility), `permission_service.py`, `cost_field_filter.py`, `cost_value.py`, `data_quality.py`, `ppm_portfolio_service.py`, and the report aggregation services.

## Identity, access and information protection

Authentication and user routing live in `backend/app/api/v1/auth.py` and `frontend/src/features/auth/`. API routes resolve a current user with `get_current_user` and require named permissions through `PermissionService`; permissions are centrally defined in `backend/app/core/permissions.py`. `CardReadScope` restricts read aggregations by accessible cards. The dashboard endpoint explicitly uses this scope, while hiding trend comparisons for restricted views (`backend/app/api/v1/reports.py`). Cost fields are additionally redacted unless the user has `costs.view` or eligible stakeholder access (`backend/app/services/cost_field_filter.py`).

This is a suitable security foundation, but executive aggregates must preserve these checks: never compute a global finance/governance figure then merely hide its UI tile.

