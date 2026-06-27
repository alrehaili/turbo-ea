# Turbo EA — Change Governance Roadmap

> **Goal:** Make Turbo EA enterprise-grade at governing change from **current state → target state**, closing the clearest gaps against Ardoq, Avolution, Essential, Orbus, ADOIT, LeanIX, Alfabet, and HOPEX — and turning it into a sellable commercial product.
>
> **Sequencing principle:** Priority ≠ build order. Front-load cheap, high-ROI view-layer wins that ride existing data, generate executive-visible value, and de-risk/fund the big architectural bet (Scenario Planning). Build the impact engine *before* scenarios that depend on it.

**Legend:** Effort ★ (trivial) → ★★★★★ (multi-month). Value ★ → ★★★★★.
Status: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked.

---

## Progress log

- **Wave 1 complete (functional + tested):** #1 Change Impact Workbench, #2 Executive Strategy Map, #3 Application Rationalization Campaign. All have backend service + endpoint(s), frontend view, i18n ×10 locales, backend tests passing, OpenAPI + CHANGELOG updated. Remaining polish (docs/screenshots, a few pickers, first-class KPI field) tracked inline.
- **All four waves built (functional + tested).** Wave 1 (#1–#3), Wave 2 (#4 Freshness, #5 Tech Standards, #6 Resilience, #7 ARB), Wave 3 (#8/#9 Scenario Planning), Wave 4 (#10 Data Flow Map, #11 Integration Hub dashboard). Each: backend service+endpoint(s), frontend view, i18n ×10 locales, backend tests passing, OpenAPI + CHANGELOG updated. **110 backend tests green** across the new suites.
- **Deferred by design / environment (tracked inline):** OpenMetadata connector (needs live OM), generalized connector framework (YAGNI until 2nd connector), first-class KPI / RTO-RPO / Data-Domain metamodel fields, LDV graph overlays, and per-feature docs/screenshots + frontend unit tests. The **commercial track** (editions/licensing, SCIM, SOC 2, scale, pricing) is not started — it is the gate to actually selling and should be the next focus.
- **Known blocker (pre-existing, not from this work):** `frontend/src/features/reports/TransformationRoadmap.tsx` has 3 TS errors that block a full `npm run build`. New code compiles clean in isolation.

---

## Delivery waves at a glance

| Wave | Theme | Items | Why now |
|------|-------|-------|---------|
| **1** | Make the existing data *useful* | Change Impact Workbench · Strategy-to-Execution · App Rationalization | Mostly aggregation over relations/tables that already exist. Fast, executive-visible, funds the big bet. |
| **2** | Governance & trust | Standards/Radar/Exceptions · Repository Freshness · Resilience/Critical Service | Operationalizes principles; rides the impact engine; anchored to DORA/NIS2 you already ship. |
| **3** | The moat | Scenario Planning & Transition Architecture | Highest value, highest risk. Now de-risked by reusing the Wave 1 impact engine. |
| **4** | Reach & integration | Data Architecture + OpenMetadata · Connector framework | Environment-driven; let the framework crystallize from real connectors, not up front. |

**Cross-cutting commercial track** (runs in parallel — see bottom): licensing/editions, multi-tenancy hardening, audit/SOC 2 readiness, onboarding, pricing packaging.

---

## Definition of Done (applies to EVERY feature below)

Per the project conventions in `CLAUDE.md`, a feature is **not** done until all of these are true:

- [ ] Backend: models in `backend/app/models/` + imported in `__init__.py`; Alembic migration with sequential numbering; built-in-default changes use a guarded `UPDATE` migration.
- [ ] Permissions: new keys in `backend/app/core/permissions.py`; every mutating endpoint calls `PermissionService.require_permission()` / `require_permission()` dep.
- [ ] Routes: one file per domain in `backend/app/api/v1/`, registered in `router.py`, all `async def`.
- [ ] OpenAPI: ran `python scripts/dump_openapi.py` and committed `docs/api/openapi.json`.
- [ ] Workspace Transfer: any new table wired into `ENTITY_SECTIONS`/`CONFIG_SECTIONS`/bespoke `*_COLUMNS` per the checklist in `CLAUDE.md`. **(Easy to forget — gate every schema change on this.)**
- [ ] Frontend: lazy route in `App.tsx`; `api.*` client; types in `src/types/index.ts`; MUI 6 + design tokens (no hardcoded hex); singleton hooks use the inflight-promise pattern; boot settings go through `/settings/bootstrap`.
- [ ] i18n: keys in all 10 locales (`en` source + `de fr es it pt zh ru da ar`); RTL-safe for `ar`; metamodel labels carry `translations` dicts in `seed.py`.
- [ ] Tests: backend in `backend/tests/` (savepoint-rollback), frontend Vitest next to source; pure logic unit-tested.
- [ ] Docs: guide/admin pages in all 8 locale suffixes; screenshots in `scripts/screenshots/pages.ts` + referenced in docs; `nav:` in `mkdocs.yml`; glossary; `mkdocs build --strict` passes.
- [ ] Lint/format: `cd backend && ruff format . && ruff check .`; `cd frontend && npm run build && npm run test:run`.
- [ ] CHANGELOG + VERSION bumped once per PR (SemVer); matching `## [x.y.z]` heading.

---

## WAVE 1 — Make existing data useful (fastest ROI)

### 1.1 Change Impact Workbench  ·  Value ★★★★ · Effort ★★
*A focused "what breaks if I replace App X / retire Vendor Y / change Data Domain Z?" view. Affected capabilities, processes, interfaces, data, risks, projects, suppliers, controls, and critical paths — not just a generic graph. Usable standalone in the Architecture Review Board, and the **prerequisite impact engine for Scenario Planning (Wave 3)**.*

**Foundation that already exists:** MCP `analyze_impact`, `/reports/dependencies` (BFS depth), archive cascade-impact preview (`/cards/{id}/archive-impact`).

- [x] Backend: reusable `impact_service.py` (blast-radius BFS, grouped by EA layer, depth + shortest name-path tracking, criticality weighting, linked risks + initiatives). *(New shared engine; refactoring `analyze_impact`/archive-impact to call it deferred — not required for the feature.)*
- [x] Backend: criticality/critical-path weighting via existing `businessCriticality` field.
- [x] Endpoint: `GET /reports/impact?card_id=&change_type=replace|retire|modify&depth=` returning grouped affected cards + risks + initiatives. *(Suppliers/controls fold in once those features land.)*
- [x] Permissions: reused `reports.ea_dashboard` (no new key needed).
- [x] Frontend: `ChangeImpactWorkbench.tsx` — card picker, change-type selector, depth selector, summary metrics, grouped-by-layer impact tables, critical flag, linked-risk table. *(LDV/`C4DiagramView` graph render deferred — table view shipped first.)*
- [x] Backend tests (4, passing), i18n (all 10 locales), OpenAPI regenerated.
- [ ] **Remaining:** docs pages (8 locales) + screenshots (`pages.ts`) + frontend unit test + optional LDV graph render.
- [x] **Acceptance:** select any card + change type → affected cards grouped by layer with depth/path, plus risks & initiatives. ✅ verified by `tests/api/test_reports.py::TestChangeImpact`.

### 1.2 Strategy-to-Execution / Investment View  ·  Value ★★★★ · Effort ★★
*One traceable chain: Strategic objective → KPI/outcome → capability/value stream → initiative → project → application/data/technology. Makes architecture legible to executives, not just architects.*

**Foundation that already exists:** full relation chain — `relObjectiveToBC`, `relInitiativeToObjective`, `relInitiativeToBC`, `relInitiativeToApp`, `relProcessToObjective`; PPM; `kpi_snapshots`.

- [~] **Metamodel gap:** KPIs/outcomes not yet first-class. Shipped a pragmatic interim: the map surfaces a KPI/outcome opportunistically from the Objective's attributes (`kpi`/`outcome`/`targetMetric`/`successMetric`). **Remaining:** promote to a first-class field on `Objective` via `seed.py` + guarded migration + `translations`.
- [x] Backend: `GET /reports/strategy-map` (`strategy_map_service.py`) — objective → capability → initiative → application chain with per-initiative budget/actual/status read off the Initiative card; summary rollup.
- [x] Frontend: **Executive Strategy Map** (`ExecutiveStrategyMap.tsx`) — objectives, KPI chip, capabilities, initiatives with budget+status, applications, summary metrics. Drill-through links to each card.
- [x] Backend tests (2, passing), i18n (all 10 locales), OpenAPI regenerated.
- [ ] **Remaining:** first-class KPI field + PPM health (RAG) rollup from status reports + docs/screenshots + frontend unit test.
- [x] **Acceptance:** an executive can trace any objective to the apps delivering it and see budget. ✅ verified by `tests/api/test_reports.py::TestStrategyMap`.

### 1.3 Application Rationalization Campaign  ·  Value ★★★★ · Effort ★★★
*Package portfolio + cost + lifecycle + duplicate/modernization detection into a repeatable TIME workflow: assess → decide (Tolerate/Invest/Migrate/Eliminate) → nominate successor → calculate savings → link initiative → track progress. This is how LeanIX/Alfabet turn inventory into portfolio decisions.*

**Foundation that already exists:** portfolio bubbles, cost fields, lifecycle, TurboLens duplicates + modernization, `relInitiativeSuccessor`.

- [~] **Metamodel gap:** Application→Application successor captured as a nullable `successor_id` FK on `campaign_decisions` (self-contained, no metamodel migration). **Remaining (optional):** promote to a first-class `relApplicationSuccessor` landscape relation.
- [x] Backend: `rationalization_campaigns` (name, status, owner, target_savings) + `campaign_decisions` (card_id, TIME decision, successor_id, initiative_id, annual_cost, risk_note, planned_savings, progress) — `models/rationalization.py`, migration `112_add_rationalization_fork.py`.
- [x] Backend: permissions `rationalization.view` / `rationalization.manage` (wired into member/bpm_admin/viewer role dicts); full CRUD + savings/decision-mix rollup endpoints (`api/v1/rationalization.py`).
- [x] Workspace Transfer: both tables added to `ENTITY_SECTIONS` (roundtrip test green).
- [x] Frontend: **Application Rationalization Board** (`ApplicationRationalizationBoard.tsx`) — campaign list, TIME decision per app (inline editable), successor, annual cost, planned savings, progress bars, savings-vs-target rollup.
- [x] Backend tests (8, passing), i18n (all 10 locales incl. plurals), OpenAPI regenerated.
- [ ] **Remaining:** successor/initiative pickers in the add-app dialog (currently search-by-name for app only), seed_demo data, docs/screenshots, frontend unit test.
- [x] **Acceptance:** run a campaign, record TIME decisions, see total planned savings + per-app progress + elimination count. ✅ verified by `tests/api/test_rationalization.py`.

---

## WAVE 2 — Governance & trust

### 2.1 Architecture Standards, Technology Radar & Exception Management  ·  Value ★★★ · Effort ★★★
*Catalogue for technology/cloud/integration/data/security standards: Preferred / Allowed / Tolerated / Sunset / Prohibited. Exception requests linked to initiatives, ADRs, expiry dates, compensating controls, approvers. Makes the existing Principles operational.*

**Foundation that already exists:** Principles, ADRs, compliance findings, capability catalogue, risk lifecycle (exception-like state machine).

> **Decision:** built as a **clean, separate catalogue** (`tech_standards` / `tech_standard_exceptions`, `tech_standards.*` permissions), kept fully distinct from the fork's existing principle-linked `standards` table.
- [x] Backend: `tech_standards` (name, category, status enum, rationale, replacement_id self-FK, owner) + `tech_standard_exceptions` (standard_id, card_id/initiative_id, justification, compensating_controls, approver_id, expiry_date, status) — `models/tech_standard.py`, migration `114_add_tech_standards_fork.py`.
- [x] Backend: permissions `tech_standards.view` / `.manage` / `.approve_exception` (approval split from authoring); CRUD + exception request/decision endpoints + `GET /tech-standards/radar` (category×status matrix + open-exception counts). Expired approved exceptions surface as `expired` automatically.
- [x] Workspace Transfer: both tables wired into `ENTITY_SECTIONS` (roundtrip green); replacement_id self-FK resolves verbatim (module PKs preserved).
- [x] Frontend: **Technology Standards Radar** (`TechnologyStandardsRadar.tsx`) — radar/heatmap matrix (category rows × status rings, open-exception badges) + exception register tab with approve/reject + new-standard dialog.
- [x] Backend tests (8, passing), i18n (all 10 locales), OpenAPI regenerated.
- [ ] **Remaining:** standards-compliance scan (map apps→standards + flag violations), true polar-radar visual, docs/screenshots, frontend unit test.
- [x] **Acceptance:** classify a technology as Sunset/Prohibited, raise a time-boxed exception with compensating controls, route approval through a separate approver permission. ✅ verified by `tests/api/test_tech_standards.py`.

### 2.2 Repository Freshness View  ·  Value ★★★ · Effort ★★
*Who owns each area, when it was last confirmed, source system, confidence, unresolved data-quality issues. The cheap, shippable half of the Integration Hub — ship it before any connector framework.*

**Foundation that already exists:** `data_quality` scoring, stakeholders/owners, surveys (data-maintenance), ServiceNow source-of-truth thinking, events/audit trail.

- [x] Backend: added `last_confirmed_at`, `source_system`, `confidence` to `cards` (migration `113_add_card_freshness_fork.py`). `POST /cards/{id}/confirm` stamps `last_confirmed_at` (+ optional source/confidence), gated by `inventory.edit`/`card.edit`.
- [x] Backend: `GET /reports/freshness` (`freshness_service.py`) — coverage by owner/type/source/confidence, configurable stale threshold, open DQ issues, stale-record worklist.
- [x] Workspace Transfer: `source_system` + `confidence` added to `CARD_COLUMNS` + exporter/applier (roundtrip test green). `last_confirmed_at` intentionally instance-local (like `archived_at`), documented in the model.
- [x] Frontend: **Repository Freshness View** (`RepositoryFreshnessView.tsx`) — summary metrics, source/confidence breakdown, ownership coverage bars, stale-record worklist with inline **Confirm**.
- [x] Backend tests (4, passing), i18n (all 10 locales incl. plurals), OpenAPI regenerated.
- [ ] **Remaining:** docs/screenshots, frontend unit test.
- [x] **Acceptance:** an architect can see which areas are stale, who owns them, and confirm records inline. ✅ verified by `tests/api/test_reports.py::TestFreshness`.

### 2.3 Resilience / Critical Service View  ·  Value ★★★★ · Effort ★★★
*Business service → process → app → integration → infrastructure → supplier, with criticality, RTO/RPO, and single-point-of-failure detection. **Promoted to a numbered feature** — strongest regulatory tailwind (you already ship DORA + NIS2 in the compliance scanner) and reuses the Wave 1 impact engine.*

**Foundation that already exists:** `businessCriticality` field + options, Provider/supplier model, dependency/impact engine, DORA/NIS2 compliance scanner.

- [~] **Metamodel gap:** RTO/RPO read opportunistically from card attributes (`rto`/`rpo`). **Remaining:** first-class RTO/RPO/recovery-tier fields via `seed.py` + migration.
- [x] Backend: SPOF / concentration-risk analysis (`resilience_service.py`, reuses the `impact_service` walk); critical-service chains; supplier-SPOF flag.
- [x] Backend: `GET /reports/resilience` — critical-service chains, SPOFs, RTO/RPO coverage gaps.
- [x] Frontend: **Resilience / Critical Service View** (`ResilienceView.tsx`) — SPOF table (concentration + dependents), critical-services table with RTO/RPO + chain size, summary metrics.
- [x] Backend tests (2, passing), i18n (all 10 locales), OpenAPI regenerated.
- [ ] **Remaining:** first-class RTO/RPO fields, one-click promote-gap-to-risk, docs/screenshots.
- [x] **Acceptance:** see critical services, flagged SPOFs (concentration), and RTO/RPO gaps. ✅ verified by `tests/api/test_reports.py::TestResilience`.

### 2.4 Architecture Review Board View  ·  Value ★★★ · Effort ★ (near-free aggregation)
*Proposed solution, standards compliance, ADRs, exceptions, risks, decision, and sign-off in one screen. Almost pure aggregation once 1.1, 2.1, and ADRs exist.*

- [x] Backend: `arb_reviews` table (`models/arb_review.py`, migration `115`) + `arb.view`/`arb.manage` permissions + router with live governance-context aggregation (impact summary + risks + ADRs + standard exceptions for the subject card).
- [x] Frontend: **ARB View** (`ArchitectureReviewBoard.tsx`) — review list, detail dialog assembling impact/risks/ADRs/exceptions, approve/reject/defer decision (stamps reviewer + timestamp).
- [x] Workspace Transfer: `arb_reviews` wired into `ENTITY_SECTIONS`.
- [x] Backend tests (3, passing), i18n (all 10 locales).
- [ ] **Remaining:** docs/screenshots.
- [x] **Acceptance:** open one screen per proposal, see full governance context, record a decision. ✅ verified by `tests/api/test_arb.py`.

---

## WAVE 3 — The moat: Scenario Planning & Transition Architecture

### 3.1 Scenario Planning & Transition Architecture  ·  Value ★★★★★ · Effort ★★★★★
*Create a baseline, branch a scenario, add/change/retire cards and relations, compare As-Is vs To-Be, measure cost/risk/capability impact, then approve or merge into the real repository. The clearest single differentiator gap. **No scenario/baseline/branching model exists today — this is net-new architecture.***

**Foundation that already exists:** `approval_status`, TurboLens "proposed card" + dashed-border NEW-badge pattern, workspace export/import full-DB serializer, LDV diff rendering, the Wave 1 impact engine.

#### 3.1.0 Architecture spike (DONE)
- [x] Branching model decided: **copy-on-write delta/overlay** — `scenario_changes` stores only add/modify/retire deltas against the live baseline (reuses the proposed-card mental model, trivial diffing, small storage).
- [x] Merge-conflict resolution: **existence-based** — a modify/retire whose target card was since deleted is reported as a `conflict` and skipped (not silently lost); dry-run preview shows applied/conflict counts before writing.
- [x] Scope: cards (add/modify/retire of name/description/attributes). Relation-level changes deferred as an enhancement.

#### 3.1.1 Build
- [x] Backend: `scenarios` (name, status draft/review/approved/merged/discarded, owner, merged_by/at) + `scenario_changes` (op, card_type, target_card_id, name, payload delta, merge_status) — `models/scenario.py`, migration `116_add_scenarios_fork.py`.
- [x] Backend: permissions `scenarios.view` / `.manage` / `.merge`; full CRUD + change CRUD.
- [x] Backend: diff engine (`GET /scenarios/{id}/diff` — As-Is/To-Be + per-change impact rollup via `impact_service`), merge engine (`POST /scenarios/{id}/merge?dry_run=`) with conflict detection + `scenario.merged` audit event.
- [x] Workspace Transfer: `scenarios` + `scenario_changes` wired into `ENTITY_SECTIONS`.
- [x] Frontend: **Scenario Planning** (`ScenarioPlanning.tsx`) — list, detail with change table, As-Is/To-Be diff metrics + per-change impact, add-change dialog (add: type+name; modify/retire: card picker), merge with dry-run preview + conflict surfacing.
- [x] Backend tests (8, passing — incl. diff, merge apply, conflict detection, re-merge guard), i18n (all 10 locales incl. plurals).
- [ ] **Remaining:** relation-level scenario changes, baseline-drift (field-level) conflict detection, LDV dashed/NEW overlay render, approval-workflow UI polish, docs/screenshots.
- [x] **Acceptance:** branch a scenario, retire a card + add a successor, see As-Is/To-Be diff with impact, dry-run then merge into baseline with conflict handling + audit event. ✅ verified by `tests/api/test_scenarios.py`.

---

## WAVE 4 — Reach & integration (environment-driven)

### 4.1 Data Architecture & OpenMetadata Connector  ·  Value ★★★ (★★★★ for your env) · Effort ★★★
*Model Data Domains, Data Products, critical data entities, system of record, owners/stewards, classifications, retention, sharing, logical data flows. **Integrate OpenMetadata — do not rebuild it.** Let Turbo EA show the business & transformation context around the data.*

- [~] Metamodel: data domain read opportunistically from the Data Object's `dataDomain` attribute (no migration). **Remaining:** first-class Data Domain / Data Product card types + steward/classification/retention/SoR fields via `seed.py` + guarded migration + `translations`.
- [ ] **Deferred:** OpenMetadata connector (read lineage/entities → cards). Needs a live OpenMetadata instance to build/test; tracked for when the environment is available. Build via the migration adapter pattern (`sources/` registry).
- [x] Backend: `GET /reports/data-flow` (`data_flow_service.py`) — data objects grouped by domain with related applications / interfaces / IT components + orphan detection. Traverses existing `relAppToDataObj` / `relInterfaceToDataObj` (no schema change).
- [x] Frontend: **Data Domain & Flow Map** (`DataFlowMap.tsx`) — domain groups → data object → applications / interfaces / components, with orphan flags + summary metrics.
- [x] Backend tests (2, passing), i18n (all 10 locales), OpenAPI regenerated.
- [x] **Acceptance (partial):** data objects appear grouped by domain with their app/interface/component context, cross-system flow navigable. ✅ `tests/api/test_reports.py::TestDataFlow`. *(OpenMetadata population deferred.)*

### 4.2 Integration Hub + Data Freshness / Drift  ·  Value ★★★ · Effort ★★★★ (framework)
*Generalize the ServiceNow source-of-truth integration into a connector framework: Entra ID, Azure/AWS/GCP, Jira/Azure DevOps, GitHub/GitLab, OpenMetadata, CMDBs. Show last sync, source coverage, proposed changes, conflicts, manual overrides, stale records.*

> **Pushback / guardrail:** do **not** build a generalized framework before a second real connector needs it (your own migration-adapter convention says so — YAGNI). Ship the **Freshness View (2.2) first**, then add connectors one concrete integration at a time, and let the framework crystallize from 2–3 real implementations. Do **not** build a Virima-style discovery scanner — consume discovery data.

- [x] **Drift / sync-status dashboard shipped** (the consumable half): `GET /reports/integration-status` (`integration_status_service.py`) + **Integration Hub** view (`IntegrationStatusView.tsx`) — per-source last-sync, status, identity-map coverage, pending changes, staleness. Built over the existing ServiceNow tables; source-shaped so new connectors slot in.
- [ ] **Intentionally deferred (plan's own YAGNI guidance):** generalizing ServiceNow staging/identity-map/field-mapping into a reusable connector *framework* — do this only once a 2nd real connector exists, so the abstraction is driven by two implementations, not one.
- [ ] **Deferred:** additional connectors (Entra ID, a cloud provider, Jira/ADO) — add incrementally; do not build a Virima-style discovery scanner.
- [x] Backend tests (3, passing), i18n (all 10 locales), OpenAPI regenerated.
- [x] **Acceptance (drift dashboard):** every configured source shows last sync, coverage, pending changes, and staleness. ✅ `tests/api/test_reports.py::TestIntegrationStatus`. *(Framework + new connectors deferred by design.)*

---

## Cross-cutting commercial track (parallel — required to *sell* this)

Enterprise EA buyers (the LeanIX/Ardoq/Alfabet procurement crowd) gate on these regardless of features:

- [ ] **Editions & licensing** — Community vs Enterprise feature gating; license-key validation; per-seat/usage metering.
- [ ] **Multi-tenancy / isolation hardening** — verify tenant isolation across every new table; row-level scoping review.
- [ ] **SSO/SCIM at enterprise grade** — SCIM user provisioning, group→role mapping (SSO exists; SCIM likely doesn't).
- [ ] **Audit & compliance posture** — SOC 2 / ISO 27001 readiness; the mutation-batch ledger + event audit is a strong base, extend to all admin actions.
- [ ] **Performance at scale** — validate impact/dependency/scenario engines at 50k+ cards; index review; query budgets.
- [ ] **Onboarding & time-to-value** — guided setup, sample scenarios, the catalogues you already ship as accelerators.
- [ ] **Backup/restore & DR** — leverage workspace export; document RTO/RPO of the product itself.
- [ ] **Observability** — health/metrics endpoints, structured logs, error tracking.
- [ ] **Pricing & packaging** — map waves to tiers (e.g. Scenario Planning + Resilience + Connectors = Enterprise tier).
- [ ] **Security review** — run `/security-review` per wave; pen-test before GA.

---

## Recommended execution order (single list, for tracking)

1. [~] **1.1** Change Impact Workbench *(also unblocks 2.3 and 3.1)* — backend + endpoint + frontend + i18n + tests done; docs/screenshots pending
2. [~] **1.2** Strategy-to-Execution / Executive Strategy Map — backend + endpoint + frontend + i18n + tests done; first-class KPI field + PPM RAG + docs pending
3. [~] **1.3** Application Rationalization Campaign — models + migration + permissions + CRUD + board + i18n + tests + workspace transfer done; demo data/docs/pickers pending
4. [~] **2.2** Repository Freshness View — columns + migration + confirm endpoint + freshness report + view + i18n + tests + workspace transfer done; docs/screenshots pending
5. [~] **2.1** Standards / Technology Radar / Exceptions — clean separate catalogue: models + migration + permissions + CRUD + radar + exception workflow + view + i18n + tests + workspace transfer done; compliance-scan + docs pending
6. [~] **2.3** Resilience / Critical Service View — service + endpoint + view + i18n + tests done; first-class RTO/RPO fields + promote-to-risk pending
7. [~] **2.4** Architecture Review Board View — table + aggregation + view + i18n + tests + workspace transfer done; docs pending
8. [x] **3.1.0** Scenario Planning architecture spike — copy-on-write overlay + existence-based conflict detection
9. [~] **3.1.1** Scenario Planning & Transition Architecture — models + migration + permissions + diff + merge + view + i18n + tests + workspace transfer done; relation-level changes/LDV overlay/docs pending
10. [~] **4.1** Data Architecture + Data Flow Map — flow map + endpoint + view + i18n + tests done; first-class Data Domain/Product types + OpenMetadata connector deferred (needs live OM instance)
11. [~] **4.2** Integration Hub — drift/sync-status dashboard shipped (endpoint + view + i18n + tests); generalized connector framework + new connectors deferred by design (YAGNI until 2nd connector)

> Run the **commercial track** continuously alongside waves — it's not a phase, it's the difference between "open-source project" and "product you can sell."
