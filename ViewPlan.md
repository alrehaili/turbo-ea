# Essential Viewer Inspired EA Views Plan

## 1. Executive Summary

This branch explores Enterprise Architecture views inspired by Essential Viewer and implements only the safest high-priority view that can be delivered with existing Turbo EA data, APIs, permissions, and frontend architecture.

Essential Viewer is used only as a functional and navigation reference. No Essential Viewer code is copied. The implementation strategy is additive: prefer existing cards, relations, report endpoints, RBAC, saved-report infrastructure, side panels, localization, and Material UI patterns. Database and backend changes are explicitly avoided unless a future phase is approved.

Primary implemented change in this branch:

- Expose the existing Process Landscape Map as a first-class Reports route and navigation item, inspired by Essential Viewer's Business Process Hierarchy, Business Process Hierarchy Application Mapping, and Business Domain Process Analysis views.

References reviewed:

- Essential Viewer repository: https://github.com/essentialproject/essential_viewer
- Essential Viewer demo home: https://essentialviewer.com/demo/report?XML=reportXML.xml&XSL=home.xsl&cl=en-gb&LABEL=Home
- Essential Viewer Enterprise Architecture portal: https://essentialviewer.com/demo/report?LABEL=General+Enterprise+Architecture+Portal&PMA=essential_baseline_v5_Class83&XML=reportXML.xml&XSL=common%2Fportal_template.xsl

## 2. Current Turbo EA Views and Capabilities

Turbo EA already has a broad EA reporting surface:

- Dashboard: portfolio counts, quality, lifecycle, approval status, user workspace, admin governance/adoption panels.
- Inventory: configurable card grid, filters, saved views, card detail side panel/pages.
- Reports: portfolio, flexible portfolio, capability map, lifecycle, transformation roadmap, dependency viewer, gap analysis, organization chart, service traceability, KPI scorecard, reference models, interoperability, change impact, strategy map, cost, matrix, data quality, repository freshness, resilience, data flow, integration status, EOL, saved reports.
- Governance: scenario planning, application rationalization, technology standards radar, Architecture Review Board.
- BPM: process dashboard, process navigator, BPMN process flow editor/viewer, embedded BPM reports including a Process Map.
- Diagrams: diagram list, viewer, editor, linked cards, perspectives.
- GRC: governance, risk register, compliance overview/findings.
- Reference catalogues: capability catalogue, process catalogue, value stream catalogue, principles catalogue.
- Delivery: SoAW, ADRs, initiative workspace, PPM integration.

Relevant frontend patterns:

- Route-level pages are lazy-loaded in `frontend/src/App.tsx`.
- Main navigation is declared in `frontend/src/layouts/AppLayout.tsx`.
- Report pages use `ReportShell`, shared export/print behavior, saved report hooks, localization, and card side panels.
- Frontend API calls use `api.get/post/patch/delete` from `frontend/src/api/client.ts`.

Relevant backend/API patterns:

- Card data: `GET /api/v1/cards`, `GET /api/v1/cards/{id}`, `GET /api/v1/relations`.
- Metamodel data: `GET /api/v1/metamodel/types`, `GET /api/v1/metamodel/relation-types`.
- Reports data: `GET /api/v1/reports/*` and `GET /api/v1/reports/bpm/*`.
- Permissions: report pages generally require `reports.ea_dashboard`, `reports.bpm_dashboard`, `reports.portfolio`, or module-specific read permissions.

Relevant data entities:

- Core EA inventory: `Card`, `CardType`, `Relation`, `RelationType`, `Tag`, `Stakeholder`.
- Business/process/application/data modeling via data-driven card types such as `BusinessCapability`, `BusinessProcess`, `Application`, `DataObject`, `Organization`, `BusinessContext`, `ITComponent`, `Interface`, `Initiative`.
- BPM process flows through BPM-specific process flow tables and BusinessProcess cards.

## 3. Essential Viewer Views and Patterns Reviewed

The Essential Viewer repository is organized by EA domains such as business, application, information, integration, technology, enterprise, common, and view library assets. The demo portal groups views into user-facing domains:

- Enterprise: strategy overview, roadmap dashboard, IT asset dashboard, EA principles, decision dashboard, navigator, data issue catalogue.
- Business: business capability dashboard, application landscape, business capability tree, domain process analysis, domain IT analysis, value stream application mapping, value stream canvas/summary, process hierarchy, organization structure model.
- Application: application reference model, application disposition, application dashboard, application summary, dependency viewer, information dependency model, impact analysis, rationalization, footprint comparison, technology strategy alignment, cost analysis, lifecycle view.
- Information and Data: information reference model, data subject/object summaries and models, data object provider model, data security model.
- Technology: technology reference model, vulnerability analysis, product summary, node summary.
- Support/Catalogues: view library, all-instances catalogues, completeness checks, duplicate dashboards, instance relationship trees.

Useful presentation/navigation patterns:

- Portal-style view library grouped by EA concern.
- Cross-view navigation from one entity to related views.
- Catalogue/table views paired with visual summaries.
- Drill-down from portfolio dashboards into summary pages.
- Heatmap overlays and lifecycle/status overlays.
- Entity summary views that combine description, relationships, diagrams, plans, decisions, costs, and risks.

## 4. Gap Analysis

Turbo EA already covers many Essential Viewer capabilities:

- Business capability map exists and supports heatmap overlays and application links.
- Dependency viewer, matrix, data quality, lifecycle, cost, EOL, service traceability, reference models, interoperability, strategy map, change impact, rationalization, standards radar, process catalogue, value stream catalogue, and process map are already present.
- Card detail pages already act as configurable entity summaries.
- Diagrams and BPM process flows cover graphical modeling.
- Saved reports, export, print, localization, and RBAC are already mature.

Gaps compared to Essential Viewer:

- No unified EA View Library landing page that groups views by concern and explains what each view answers.
- Some existing views are embedded but not directly discoverable from top-level Reports navigation.
- No dedicated Application Summary report page that composes portfolio, dependencies, information flows, technology, decisions, standards, risks, lifecycle, and costs around one application.
- No Application Footprint Comparison view that compares two applications by supported capabilities/processes/data/technology.
- No explicit Application Technology Strategy Alignment view that joins applications to technology standards compliance in one application-scoped view.
- Value stream canvas exists conceptually through value stream catalogue and BPM reports, but not as an Essential-style single value stream canvas with stages, capabilities, organizations, applications, KPIs, and pain points.
- Supplier impact and license views would need stronger supplier/license data coverage before implementation.
- Technology vulnerability analysis requires external vulnerability data and product-version normalization.

## 5. Recommended Views Ranked by Priority

| Priority | View | Implementation status | Data requirement |
| --- | --- | --- | --- |
| High | Process Landscape Map | Implement in this branch by exposing existing page as top-level report | Existing data only |
| High | EA View Library | Plan only | Existing data only |
| High | Application Summary | Plan only | Existing data only, optional backend aggregation later |
| Medium | Application Footprint Comparison | Plan only | Existing data only, optional backend aggregation later |
| Medium | Application Technology Alignment | Plan only | Existing data plus technology standards mappings |
| Medium | Value Stream Canvas | Plan only | Existing data, stronger value stream stage modeling optional |
| Low | Supplier Impact Map | Plan only | Future data-model/metamodel enhancement for suppliers/contracts/licenses |
| Low | Technology Vulnerability Analysis | Plan only | Future integration/data enhancement |

## 6. Detailed Implementation Plans

### 6.1 Process Landscape Map

- Business purpose: Help architects and process owners understand the process hierarchy, maturity/automation/risk overlays, and the applications/data objects supporting processes.
- Target users: Enterprise architects, business architects, process owners, application owners, transformation planners.
- Essential Viewer inspiration: Business Process Hierarchy, Business Process Hierarchy Application Mapping, Business Domain Process Analysis, Business Process Model.
- Existing support: `BusinessProcess`, `Application`, `DataObject`, `Organization`, `BusinessContext` cards; relations `relProcessToApp`, `relProcessToDataObj`, `relProcessToOrg`, `relProcessToBizCtx`; existing frontend `ProcessMapReport`; existing backend `GET /api/v1/reports/bpm/process-map`.
- Data gaps/limitations: Process maturity, automation, risk, and process type are useful only when configured/populated in attributes. Location-specific process mapping is not covered unless locations are modeled as cards and related to processes.
- Suggested navigation location: Reports menu as `Process Map`, beside Capability Map and Matrix. Keep the embedded BPM report tab unchanged.
- UI structure: Report shell toolbar for heatmap metric, display depth, related overlays, organization/context filters; hierarchical process cards; drill-down breadcrumbs; detail drawer; card side panel.
- Implementation approach: Add lazy route `/reports/process-map`, add Reports nav item, reuse existing localized `reports.processMap` label, keep existing backend endpoint and permission.
- Dependencies: Existing BPM report endpoint and `reports.bpm_dashboard` permission.
- Risks to existing functionality: Low. Additive route/nav only. Existing BPM tab remains unchanged.
- Status: Implemented in this branch.
- Data classification: Using existing data only.
- Acceptance criteria:
  - Users with report/BPM report access can open `/reports/process-map`.
  - Reports menu includes Process Map.
  - Embedded BPM Process Map still works.
  - Empty data renders the existing empty state.
  - Existing filters, drill-down, side panel, print/copy-link controls still work.
- Test scenarios:
  - Route smoke test by building frontend.
  - Navigate from Reports menu to Process Map.
  - Direct-load `/reports/process-map`.
  - Verify no backend schema/API change.

### 6.2 EA View Library

- Business purpose: Give users an Essential-style catalogue of EA views organized by question and architecture domain.
- Target users: New users, executives, architects, admins onboarding teams.
- Essential Viewer inspiration: Home/Enterprise Architecture portal and View Library.
- Existing support: Existing routes, permissions, i18n, report pages, module gates.
- Data gaps/limitations: None for a static/metadata-driven landing page. Later enhancement could read route/view metadata from a central registry.
- Suggested navigation location: Reports menu as `View Library`, or Dashboard quick link.
- UI structure: Domain bands such as Enterprise, Business, Application, Data, Technology, Governance, Support; each row shows view name, question answered, required permission, and launch action.
- Implementation approach: Add `frontend/src/features/reports/ViewLibraryPage.tsx`; create a local view registry that mirrors current routes and permissions; filter unavailable views using `useAuthContext` permissions and module hooks.
- Dependencies: Existing permission map in user context; module hooks for BPM/PPM/GRC.
- Risks to existing functionality: Low if additive. Risk is stale registry if routes change; can be mitigated by keeping entries close to nav definitions in a later refactor.
- Priority: High.
- Data classification: Using existing data only.
- Acceptance criteria:
  - Lists current views grouped by EA domain.
  - Hides or disables views the user lacks permission/module access for.
  - Launches existing routes without changing them.
  - All text localized.
- Test scenarios:
  - Viewer/member/admin permission snapshots.
  - Module disabled states.
  - Navigation link smoke tests.

### 6.3 Application Summary

- Business purpose: Provide one application-centric page answering what the application does, who owns it, what capabilities/processes/data/technology it supports, its lifecycle, costs, risks, decisions, standards exceptions, and diagrams.
- Target users: Application owners, architects, portfolio managers, risk/compliance teams.
- Essential Viewer inspiration: Application Summary, Application Dependency Viewer, Application Information Dependency Model, Application Impact Analysis, Application Technology Strategy Alignment, Application Cost Summary.
- Existing support: Card detail, `GET /cards/{id}`, `GET /relations?card_id=`, stakeholders/documents/comments/todos/resources/risks tabs, dependency report, impact report, cost redaction.
- Data gaps/limitations: A polished single API aggregation would reduce round-trips but is optional. Some sections depend on relation quality and configured relation types.
- Suggested navigation location: Application card action, Reports menu, and portfolio drill-down action.
- UI structure: Application picker; KPI strip; relationship sections for business, data, technology, delivery/governance, risk/compliance; dependency mini-map; lifecycle and cost panels; links to card detail and diagrams.
- Implementation approach: Frontend-only first using existing card and relation APIs; optional future backend endpoint `GET /reports/application-summary?card_id=` for aggregation/performance.
- Dependencies: Inventory view permission; costs visible only through existing cost access rules.
- Risks to existing functionality: Low if read-only and card detail remains canonical edit surface.
- Priority: High.
- Data classification: Using existing data only; optional backend enhancement.
- Acceptance criteria:
  - Select an Application and see grouped relationships.
  - Cost fields respect current redaction.
  - Missing sections render as empty states, not errors.
  - Links open card detail/side panel.
- Test scenarios:
  - Application with no relations.
  - Application with multiple relation types.
  - User without `costs.view`.
  - Archived/hidden related cards excluded consistently.

### 6.4 Application Footprint Comparison

- Business purpose: Compare two applications for rationalization, overlap, replacement, and consolidation analysis.
- Target users: Portfolio managers, rationalization campaign owners, architects.
- Essential Viewer inspiration: Application Footprint Comparison and Application Rationalisation Analysis.
- Existing support: Application cards, relations to capabilities/processes/data/technology, existing rationalization module, matrix report.
- Data gaps/limitations: Comparison quality depends on consistent application-to-capability/process/data mappings.
- Suggested navigation location: Governance > App Rationalization and Reports.
- UI structure: Two application pickers; overlap score; side-by-side grouped footprint; unique vs shared capabilities/processes/data/technology; lifecycle/cost/risk comparison.
- Implementation approach: Frontend-only initially using `GET /relations?card_id=` for both apps and card lookup by IDs. Optional backend aggregation later.
- Dependencies: Inventory and relations view permissions.
- Risks to existing functionality: Low.
- Priority: Medium.
- Data classification: Using existing data only; optional backend enhancement.
- Acceptance criteria:
  - Compare two active Application cards.
  - Display shared and unique footprint.
  - Preserve cost redaction.
  - Link to rationalization campaign where available.
- Test scenarios:
  - Same app selected twice.
  - One app with no footprint.
  - Large relation set.

### 6.5 Application Technology Alignment

- Business purpose: Show whether an application's technology stack aligns with standards and where exceptions or sunset risks exist.
- Target users: Solution architects, technology governance, ARB.
- Essential Viewer inspiration: Application Technology Strategy Alignment and Technology Reference Model.
- Existing support: Technology standards radar, ITComponent cards, Application-ITComponent relations, standard exceptions, EOL report.
- Data gaps/limitations: Requires consistent relations from Application to ITComponent and standards classification fields. Detailed product/version vulnerability data is not available.
- Suggested navigation location: Governance > Technology Radar and application summary.
- UI structure: Application picker; technology stack table; standard status chips; exception status; lifecycle/EOL warnings; recommended action list.
- Implementation approach: Reuse existing standards APIs and relation APIs; no DB changes.
- Dependencies: `tech_standards.view`, `inventory.view`, `relations.view`, possibly `eol.view`.
- Risks to existing functionality: Low if read-only.
- Priority: Medium.
- Data classification: Existing data plus optional future backend aggregation.
- Acceptance criteria:
  - Shows standards status for linked technologies.
  - Flags sunset/prohibited technologies.
  - Links to exception workflow.
- Test scenarios:
  - App with no IT components.
  - App with tolerated/sunset/prohibited technology.
  - User lacking standards permission.

### 6.6 Value Stream Canvas

- Business purpose: Show one value stream with stages, related processes, capabilities, organizations, applications, KPIs, issues, and initiatives.
- Target users: Business architects, transformation leads, process owners.
- Essential Viewer inspiration: Value Stream Canvas, Value Streams Application Mapping, Value Stream Summary.
- Existing support: Value stream catalogue, BusinessContext subtype `valueStream`, BPM value-stream matrix, processes, applications, organizations, KPIs/metrics if modeled.
- Data gaps/limitations: Explicit ordered value stream stages may need stronger modeling if not already represented by processes or child BusinessContext cards.
- Suggested navigation location: Value Stream Catalogue and Reports.
- UI structure: Horizontal stage canvas; stage cards with processes/apps/capabilities; KPI/risk/issues side panel; organization filter.
- Implementation approach: Implement only after confirming current value stream stage modeling in customer/demo data. Avoid schema changes; use hierarchy or relation attributes for ordering if already present.
- Dependencies: BPM/value stream data quality.
- Risks to existing functionality: Medium if stage semantics are guessed incorrectly.
- Priority: Medium.
- Data classification: Existing data if stages are modeled; otherwise future data-model/metamodel enhancement.
- Acceptance criteria:
  - Render one value stream as ordered stages.
  - Preserve empty/missing stage states.
  - Link each stage/process/app to card detail.
- Test scenarios:
  - Value stream with no stages.
  - Stages with repeated applications.
  - Organization filter changes stage content.

### 6.7 Supplier Impact Map

- Business purpose: Understand supplier concentration and business/application impact.
- Target users: Vendor managers, procurement, risk, architecture.
- Essential Viewer inspiration: Supplier Impact Map and Supplier License Management.
- Existing support: Can be approximated if suppliers are modeled as Provider/Organization cards and related to applications/technologies.
- Data gaps/limitations: No guaranteed supplier/license/contract model in core assumptions.
- Suggested navigation location: Future Supplier Management or Reports.
- Implementation approach: Document only until supplier/license data conventions are established.
- Dependencies: Future metamodel/data-model agreement.
- Risks to existing functionality: Medium if implemented with weak assumptions.
- Priority: Low.
- Data classification: Only after future database/data-model or metamodel enhancement.

### 6.8 Technology Vulnerability Analysis

- Business purpose: Show vulnerability exposure by technology product/version and impacted applications/services.
- Target users: Security architects, technology owners, risk/compliance teams.
- Essential Viewer inspiration: Technology Security Vulnerability Analysis.
- Existing support: ITComponent cards, EOL integration, technology standards.
- Data gaps/limitations: Requires normalized product/version inventory and vulnerability feed integration.
- Suggested navigation location: GRC/Technology Radar.
- Implementation approach: Document only.
- Dependencies: Future external vulnerability data integration.
- Risks to existing functionality: Medium/high due to external data freshness and false-positive risk.
- Priority: Low.
- Data classification: Only after future data/integration enhancement.

## 7. Expected Files, APIs, and Entities Involved

Implemented Process Landscape Map:

- Frontend files:
  - `frontend/src/App.tsx`
  - `frontend/src/layouts/AppLayout.tsx`
  - Existing `frontend/src/features/reports/ProcessMapReport.tsx`
  - Existing locale files under `frontend/src/i18n/locales/*/nav.json` and `reports.json`
- Backend files:
  - Existing `backend/app/api/v1/bpm_reports.py`
- API endpoints:
  - Existing `GET /api/v1/reports/bpm/process-map`
- Data entities:
  - `Card`, `Relation`, `BusinessProcess`, `Application`, `DataObject`, `Organization`, `BusinessContext`
- Permissions:
  - Existing `reports.ea_dashboard` for Reports menu access
  - Existing endpoint gate `reports.bpm_dashboard`

Planned future views:

- Frontend: new pages under `frontend/src/features/reports/`, route/nav additions in `App.tsx` and `AppLayout.tsx`, locale updates.
- Backend: optional future report aggregation endpoints in `backend/app/api/v1/reports.py`; no migrations unless explicitly approved.
- APIs/entities: existing cards, relations, metamodel, risks, standards, diagrams, BPM, saved reports.

## 8. Implementation Feasibility Statement

| View | Feasibility |
| --- | --- |
| Process Landscape Map | Using existing data only |
| EA View Library | Using existing data only |
| Application Summary | Using existing data only, with optional backend enhancement |
| Application Footprint Comparison | Using existing data only, with optional backend enhancement |
| Application Technology Alignment | Using existing data only if standards/technology relations are populated, with optional backend enhancement |
| Value Stream Canvas | Using existing data only if value stream stages are modeled; otherwise future data-model enhancement |
| Supplier Impact Map | Only after future database/data-model or metamodel enhancement |
| Technology Vulnerability Analysis | Only after future data/integration enhancement |

## 9. Risks, Dependencies, Assumptions, and Regression Precautions

Risks:

- View discoverability changes can expose pages to users who can see navigation but lack the endpoint permission. Mitigation: keep existing endpoint RBAC; navigation remains under Reports and the backend fails closed.
- Process Map depends on BPM report permission even when surfaced under Reports. Mitigation: document this dependency and avoid changing permissions in this branch.
- Existing i18n keys are reused. Mitigation: no new localization burden for the implemented change.
- Cost-bearing fields must remain redacted by existing backend behavior. Mitigation: no new cost endpoint introduced.
- Large portfolios can make client-side relation-heavy views slower. Mitigation: future aggregation endpoints can be added after measuring.

Assumptions:

- The current branch contains existing work from `feature/nora-alignment`; this branch is intentionally created from that HEAD and does not revert unrelated work.
- `AGENTS.md` is untracked user/workspace context and is not modified by this branch.
- Existing report permissions are acceptable for the direct Process Map route.

Regression precautions:

- No database migration.
- No backend logic change for implemented view.
- No API contract change.
- Existing BPM embedded Process Map remains unchanged.
- Frontend build/lint tests should be run after routing/nav changes.

## 10. Acceptance Criteria and Test Scenarios

Process Landscape Map:

- Acceptance:
  - `/reports/process-map` renders `ProcessMapReport`.
  - Reports menu contains `Process Map`.
  - Existing BPM reports tab still renders `ProcessMapReport`.
  - Direct route uses the existing backend endpoint and does not add new API behavior.
  - App builds without TypeScript errors.
- Tests:
  - Run frontend lint/build.
  - Manual navigation smoke test in browser if dev server is available.
  - Verify empty process data path still renders existing empty state.

EA View Library:

- Acceptance:
  - Grouped view cards by EA domain.
  - Permission/module-aware launch buttons.
  - All labels localized.
- Tests:
  - Permission matrix render tests.
  - Route link smoke tests.

Application Summary:

- Acceptance:
  - Application picker loads active applications.
  - Sections show grouped relations and empty states.
  - Cost redaction preserved.
- Tests:
  - No-relations app.
  - Rich app with business/data/technology/governance/risk links.
  - No cost permission.

Application Footprint Comparison:

- Acceptance:
  - Compare two apps and show shared/unique footprints.
  - Link all footprint items to card detail.
- Tests:
  - Same app selected twice.
  - One app without mappings.
  - Large relation list.

Application Technology Alignment:

- Acceptance:
  - Show linked technology and standard posture.
  - Flag EOL/sunset/prohibited items.
- Tests:
  - No technology links.
  - Mixed standard statuses.
  - Missing standards permission.

Value Stream Canvas:

- Acceptance:
  - Render selected value stream stages in order.
  - Show stage applications/processes/capabilities.
- Tests:
  - No stages.
  - Repeated application in multiple stages.
  - Organization filter.

Supplier Impact Map:

- Acceptance:
  - Deferred until supplier/license model is approved.
- Tests:
  - Not applicable in this phase.

Technology Vulnerability Analysis:

- Acceptance:
  - Deferred until vulnerability data integration is approved.
- Tests:
  - Not applicable in this phase.

## 11. Phased Delivery Roadmap

Phase 1: Safe discoverability improvements, no database/backend changes.

- Implement direct Process Landscape Map route and Reports menu item.
- Optionally implement EA View Library using only existing route metadata.

Phase 2: Entity-centered summaries using existing APIs.

- Application Summary.
- Application Footprint Comparison.
- Application Technology Alignment using existing standards/technology data.

Phase 3: Business architecture canvases.

- Value Stream Canvas after confirming stage modeling conventions.

Phase 4: Data/integration-dependent advanced views.

- Supplier Impact Map after supplier/license/contract modeling is agreed.
- Technology Vulnerability Analysis after normalized product/version and vulnerability feed integration are available.
