# Turbo EA — NORA-Oriented EA Views Implementation Plan

## 1. Purpose

This plan guides an AI coding agent or development team in extending the `alrehaili/turbo-ea` fork with a coherent, NORA-oriented Enterprise Architecture view experience.

The objective is **not** to recreate reports that Turbo EA already provides. The objective is to:

1. make existing views discoverable and organized by architecture domain and stakeholder question;
2. add the missing cross-domain and application-centric views;
3. reuse the configurable metamodel, cards, relations, permissions, saved reports, localization, and existing report components;
4. avoid unnecessary database changes;
5. keep all views useful for Saudi government EA practices and NORA architecture domains.

---

## 2. Important Instruction to the AI Agent

Before writing code:

1. Inspect the current branch and do not rely only on the upstream README.
2. Read:
   - `README.md`
   - `NORA.md`
   - `ViewPlan.md`
   - `CHANGELOG.fork.md`
   - `frontend/src/App.tsx`
   - `frontend/src/layouts/AppLayout.tsx`
   - `frontend/src/features/reports/`
   - backend report routes under `backend/app/api/v1/`
   - metamodel seed/configuration files
   - permission definitions and localization files
3. Produce a current-state inventory of all implemented views.
4. Map each requested view to:
   - an existing view that can be reused;
   - an existing view that needs enhancement;
   - a genuinely missing view.
5. Do not create duplicate reports with different names.
6. Implement one phase at a time.
7. Run frontend build, backend tests, and relevant lint/type checks after each phase.
8. Preserve Arabic/RTL, English, RBAC, cost redaction, saved reports, exports, print behavior, and card side-panel navigation.

---

## 2.5 Current-State Reconciliation (verified against the fork, 2026-07-16)

> **This section overrides the assumptions in sections 3–5 wherever they conflict.** The fork is much further along than the generic phase list assumes. Do not rebuild anything listed here — enhance it.

### Already implemented in this fork

| Plan item | Existing implementation | Route |
|---|---|---|
| **Phase 0 — View registry** | `frontend/src/features/reports/neaViewpoints.ts` — typed, data-driven registry of ~73 NEA viewpoints (bilingual en/ar names, domain, kind, level, status `available`/`planned`/`descoped`, deep-link path). 59 available, 4 planned, 10 descoped. | — |
| **Phase 1 — EA View Library** | `frontend/src/features/reports/EaViewLibraryPage.tsx` — domain-grouped table rendering the registry, already a **top-level nav tab** (`viewLibrary` in `AppLayout.tsx`). | `/view-library` |
| **Phase 2 — Application Summary** | `frontend/src/features/reports/ApplicationSummaryReport.tsx` + per-layer `LayerSummaryReport` | `/layers/application-summary` |
| Layer overviews (per-domain swim lanes) | `LayerSwimlaneOverview`, `LayersDashboard`, `TraceabilityView` — the six NORA layers each have an overview + summary page | `/layers/*` |
| Most of section 4's taxonomy | Existing reports: gap analysis, org chart, service traceability, KPI scorecard, reference models, interoperability, change impact, strategy map/cascade/house, value chain, data flow, integration status, resilience, freshness, tech landscape, transformation roadmap, capability map, matrix, portfolio, flexible portfolio, cost, EOL, data quality, process map, service catalogue, app modules | `/reports/*` (40 routes) |

### Navigation decision (binding)

**One tab, pages underneath.** The EA View Library at `/view-library` is the single discovery entry point. Do **not** add new top-level nav tabs for any phase below. Every new or enhanced view:

1. is a lazy-loaded page under `/reports/*` (or `/layers/*` when it is a layer summary);
2. registers exactly one entry in `neaViewpoints.ts` (which is the section 5 "viewRegistry" — extend that file, never create a second registry);
3. becomes discoverable only through the View Library, the Layers tab, and the existing Reports menu.

### Real remaining gaps (what the phases below should actually deliver)

- **Registry/Library polish** (was Phase 0/1): add search, per-view "question answered" text, favorites/recents, and permission/module awareness to `neaViewpoints.ts` + `EaViewLibraryPage.tsx`. Add a route-integrity test (every `path` resolves, no duplicate keys).
- **Application Summary depth** (was Phase 2): verify the 12 sections in Phase 2 against `ApplicationSummaryReport.tsx`; fill missing sections (security context, risks/findings, ADRs/initiatives, target-state classification). Add a "Visualize" action on Application cards linking to it.
- **Data architecture views** (Phase 6): CRUD matrix, ownership/stewardship, classification/sensitivity — mostly missing.
- **Technology deployment / cloud / residency modes** (Phase 7): partially covered by tech landscape + EOL + resilience; deployment & hosting grouping missing.
- **Standards exceptions / waivers** (Phase 8): principles & standards + security controls are seeded (fork migrations 149–151); an exception/waiver view is missing.
- **Current-vs-target comparison** (Phase 5): gap analysis + roadmap exist; explicit state classification overlay is missing.
- **Beneficiary experience** (Phase 9): beneficiary layer pages exist, but persona/journey card types are **descoped** in `noraPlan.md` — do not implement Phase 9 until that descope decision is reversed.

---

## 3. Current-State Understanding

Turbo EA already appears to provide a broad reporting surface, including:

- dashboard and inventory views;
- portfolio and flexible portfolio reports;
- capability map and heatmap behavior;
- lifecycle and transformation roadmap;
- dependency viewer;
- gap analysis;
- organization chart;
- service traceability;
- KPI scorecard;
- reference-model reporting;
- interoperability and integration reporting;
- change-impact and strategy-map reports;
- cost, matrix, data-quality, freshness, resilience, data-flow, EOL and integration-status reports;
- process map and BPM reports;
- application rationalization;
- technology standards radar;
- architecture review and governance functions;
- diagrams and card detail pages.

Therefore, development must focus on **composition, discoverability, cross-domain analysis, and missing stakeholder views** rather than creating another isolated chart collection.

---

## 4. Target View Taxonomy

Create a centralized view registry organized into the following domains.

### 4.1 Executive and Enterprise

- Enterprise Architecture Overview
- Strategy-to-Execution View
- Current-to-Target Architecture View
- Transformation Roadmap
- Architecture Risk and Compliance Overview
- EA View Library

### 4.2 Business Architecture

- Business Capability Map
- Capability Heatmap
- Capability-to-Application Mapping
- Business Service Traceability
- Process Landscape
- Organization and Responsibility View
- Value Stream Canvas

### 4.3 Beneficiary Experience

- Beneficiary Journey View
- Service Channel View
- Journey-to-Service-to-Application Traceability

### 4.4 Application Architecture

- Application Portfolio
- Application Landscape
- Application Summary
- Application Dependency and Context View
- Application Integration View
- Application Footprint Comparison
- Application Lifecycle and Disposition View
- Application Technology Standards Alignment

### 4.5 Data Architecture

- Data Domain and Data Object Landscape
- Conceptual Data Relationship View
- Data Flow and Exchange View
- Data Ownership and Stewardship View
- Application-to-Data CRUD Matrix
- Data Classification and Sensitivity View
- Data Lineage View, when lineage data is available

### 4.6 Technology Architecture

- Technology Portfolio
- Technology Reference Model
- Application Deployment View
- Technology Lifecycle and EOL View
- Cloud and Hosting View
- Technology Standards Compliance View

### 4.7 Security Architecture

- Security Controls Coverage View
- Application Security Context
- Data Security and Classification View
- Security Risk and Compliance View
- Identity and Access Dependency View

### 4.8 Governance and Delivery

- Principles and Standards Traceability
- Standards Compliance Matrix
- Architecture Decisions View
- Gaps and Recommendations View
- Initiatives and Architecture Roadmap
- Exception and Waiver View
- Architecture Review Status

---

## 5. Gap-Based Delivery Roadmap

## Phase 0 — Repository Audit and View Registry

> **STATUS: DONE (enhance only).** The registry exists as `neaViewpoints.ts` — see section 2.5. Remaining work: enrich entries with permission/module/question fields and add the route-integrity test.

### Goal

Establish one source of truth for every view in the product.

### Deliverables

- Create a typed `viewRegistry` containing:
  - unique view ID;
  - localized name;
  - architecture domain;
  - stakeholder questions answered;
  - route;
  - icon;
  - required permissions;
  - required modules;
  - supported card types;
  - current/target/both classification;
  - availability status;
  - data prerequisites.
- Reconcile navigation definitions with the registry.
- Generate a current-state matrix:
  - implemented;
  - partially implemented;
  - missing;
  - blocked by data.
- Add automated tests to detect broken routes and duplicate IDs.

### Acceptance Criteria

- Every report or architecture view is registered once.
- The registry can filter views by domain, permission and module.
- No existing route is removed.
- Existing deep links continue to work.

---

## Phase 1 — EA View Library

> **STATUS: DONE (enhance only).** Lives at `/view-library` as a top-level tab. Remaining work: search, favorites/recents, stakeholder-question browsing, permission-aware launchability.

### Goal

Make all available views discoverable without users knowing report names.

### User Experience

Create `/views` or `/reports/view-library`.

Users can browse by:

- architecture domain;
- stakeholder role;
- question answered;
- current, target or transition architecture;
- available data;
- favorites and recent views.

Each view card should show:

- name;
- plain-language question answered;
- domain;
- required data;
- availability;
- launch button;
- related views.

### Example Questions

- Which applications support this capability?
- Which applications exchange data with external government platforms?
- Which technologies are approaching end of life?
- What changes are required to reach the target architecture?
- Which standards exceptions affect critical applications?

### Acceptance Criteria

- Only authorized views are launchable.
- Disabled modules are represented correctly.
- Arabic and English are supported.
- RTL layout is visually correct.
- Search works across view names and questions.

---

## Phase 2 — Application Summary and “Visualize” Entry Point

> **STATUS: PARTIALLY DONE.** `ApplicationSummaryReport.tsx` exists at `/layers/application-summary`. Remaining work: audit it against the 12 sections below, fill gaps, and add the "Visualize" card action.

### Goal

Give every Application card a complete architecture-centric summary.

### Entry Points

- Add a `Visualize` action on Application cards.
- Add an `Architecture Summary` tab or page.
- Allow launch from application portfolio and dependency reports.

### Sections

1. Application identity and ownership
2. Business capabilities supported
3. Business services and processes supported
4. Data objects used, produced or mastered
5. Interfaces and integrations
6. Technology components and hosting
7. Security classifications and controls
8. Lifecycle, criticality and disposition
9. Costs, subject to existing permissions
10. Risks, findings, exceptions and standards
11. Related initiatives, ADRs and diagrams
12. Current and target-state classification

### Implementation Approach

- Frontend composition using existing card and relation APIs first.
- Add a backend aggregation endpoint only if measured performance is inadequate.
- Keep card detail as the canonical editing interface.

### Acceptance Criteria

- Works for an application with many relations and one with none.
- Archived or unauthorized objects are not exposed.
- Cost redaction remains intact.
- All related objects open in the existing card side panel.
- Loading and partial-error states are handled gracefully.

---

## Phase 3 — Capability-to-Application and Application Landscape Enhancements

### Goal

Turn existing capability and portfolio reports into decision-support views.

### Capability-to-Application View

Support:

- capability hierarchy;
- application count;
- application criticality;
- lifecycle/disposition overlay;
- duplication indicator;
- data-quality indicator;
- drill-down to applications;
- gap display for capabilities without adequate application support.

### Application Landscape

Allow grouping by:

- capability;
- business domain;
- organization;
- business service;
- deployment/hosting model;
- lifecycle;
- TIME disposition;
- reference-model domain.

Allow coloring by:

- criticality;
- lifecycle;
- risk;
- data quality;
- cloud status;
- standards compliance.

### Acceptance Criteria

- Uses configurable card and relation types, not hard-coded IDs where avoidable.
- Large portfolios remain usable.
- Filters are shareable and saveable.
- Empty groups are optional.
- Export and print remain available.

---

## Phase 4 — Application Integration and Dependency Analysis

### Goal

Provide a clear integration architecture view, not merely generic relationships.

### View Contents

- applications;
- interfaces/APIs;
- integration platforms;
- data exchanged;
- direction;
- protocol;
- frequency;
- synchronous/asynchronous classification;
- internal/external boundary;
- external government platform marker;
- owner;
- criticality;
- status;
- authentication pattern;
- encryption classification.

### Modes

1. Application context
2. End-to-end dependency
3. Integration hub
4. External integrations
5. Critical dependency chain
6. Target-state integration pattern

### Analysis

- point-to-point concentration;
- orphaned interfaces;
- undocumented interfaces;
- critical single points of failure;
- non-standard protocol usage;
- direct integration candidates for migration to an integration platform.

### Acceptance Criteria

- A user can select one application and see inbound and outbound integration.
- Direction and interface type are unambiguous.
- Cycles do not break rendering.
- Large graphs support depth limits and filtering.
- Missing interface metadata is visibly identified.

---

## Phase 5 — Current, Target and Transition Views

### Goal

Allow architecture elements and relationships to be compared across states.

### Minimum Model

Prefer existing attributes or lifecycle/scenario mechanisms before schema changes.

Each displayed item should be classifiable as:

- current only;
- retained;
- modified;
- new in target;
- retired;
- transitional.

### Views

- Current vs Target comparison
- Gap summary
- Transition architecture by wave
- Initiative-to-gap traceability
- Target application landscape
- Target technology deployment
- Target integration architecture

### Acceptance Criteria

- Users can distinguish current and target states visually.
- Gaps link to initiatives or recommendations.
- Roadmap items link back to impacted architecture elements.
- Historical/time-travel reporting is not confused with target architecture.

---

## Phase 6 — Data Architecture Views

### Goal

Complete the NORA data-domain presentation.

### Views

1. Data Domain Landscape
2. Data Object Relationship Model
3. Data Flow and Exchange
4. Data Ownership and Stewardship
5. Application–Data CRUD Matrix
6. Data Classification and Sensitivity
7. Data Lineage, only when reliable lineage exists

### Data Requirements

Confirm or configure:

- data domain;
- authoritative source;
- owner;
- steward;
- custodian;
- classification;
- personal/sensitive indicator;
- retention;
- producer;
- consumer;
- exchange/interface;
- CRUD relation.

### Acceptance Criteria

- Views distinguish authoritative source from consumer.
- Ownership roles are not merged into one generic owner.
- Classification is filterable.
- CRUD semantics are supported where present.
- Lineage is not inferred without evidence.

---

## Phase 7 — Technology Deployment and Cloud View

### Goal

Show where applications run and how their technical components are structured.

### View Contents

- application;
- environment;
- hosting model;
- cloud provider/platform;
- region or data residency classification;
- server/container/platform component;
- database;
- network/security component;
- technology product and version;
- lifecycle/EOL status;
- resilience/DR classification.

### Modes

- application deployment;
- environment comparison;
- cloud adoption;
- data residency;
- technology stack;
- shared-platform dependency;
- EOL exposure.

### Acceptance Criteria

- Production and non-production environments are distinguishable.
- Cloud/on-premise/hybrid grouping is supported.
- EOL warnings reuse existing EOL information.
- Deployment view can be scoped to one application or service.

---

## Phase 8 — Security and Standards Traceability

### Goal

Connect principles, standards, controls, risks and exceptions to architecture components.

### Views

- Principle-to-Standard traceability
- Standard-to-Application compliance
- Application security context
- Security control coverage
- Exception and waiver matrix
- Sensitive-data exposure
- Identity and access dependency
- Standards compliance by criticality

### Analysis

- critical applications without required controls;
- standards with low adoption;
- expired exceptions;
- prohibited or sunset technologies;
- sensitive data used by non-compliant applications;
- missing IAM integration.

### Acceptance Criteria

- Compliance status has a defined source and calculation.
- “Unknown” is distinct from “Non-compliant.”
- Exceptions show expiry and approval status.
- Sensitive security information follows permissions.
- Findings can link to risks, todos or initiatives.

---

## Phase 9 — Beneficiary Experience Views

> **STATUS: BLOCKED.** Persona/journey/beneficiary-registry building blocks are deliberately descoped in `noraPlan.md` (see the `descoped` entries in `neaViewpoints.ts`). Do not implement until that decision is reversed. The `/layers/beneficiary` pages already cover what current data supports.

### Goal

Support the NORA beneficiary-experience domain rather than treating CX as generic business metadata.

### Required Concepts

Use configurable card types if they already exist; otherwise introduce them through metamodel configuration before database schema changes:

- beneficiary/persona;
- journey;
- journey stage;
- touchpoint;
- channel;
- service;
- pain point;
- experience KPI;
- application;
- process.

### Views

- Beneficiary Journey
- Journey-to-Service Mapping
- Journey-to-Application Mapping
- Channel Landscape
- Pain Point and Improvement Heatmap

### Acceptance Criteria

- Journey stages are ordered.
- Touchpoints link to services, processes and applications.
- Pain points can link to gaps and initiatives.
- The view supports Arabic/RTL correctly.

---

## 6. Cross-Cutting Technical Requirements

### 6.1 Configurable Metamodel

- Do not assume every installation uses exactly the same internal IDs.
- Resolve card and relation types using stable keys or configurable mappings.
- Provide clear empty states when a required relation type is absent.
- Document required metamodel configuration per view.

### 6.2 Performance

- Avoid fetching every card and relation into the browser for large repositories.
- Use server-side aggregation when relation volume becomes high.
- Apply depth, domain and lifecycle filters server-side where possible.
- Add pagination or progressive loading for tables.
- Add graph node limits and explain truncation.

### 6.3 Permissions and Security

- Reuse existing RBAC.
- Backend authorization is mandatory; hiding navigation is not sufficient.
- Preserve field-level and cost redaction.
- Exclude unauthorized related objects from aggregations.
- Do not leak hidden cards through counts or tooltips.

### 6.4 Localization and RTL

Every new component must include:

- English localization;
- Arabic localization;
- RTL layout test;
- mirrored directional icons where appropriate;
- readable graph labels in Arabic;
- localized export labels.

### 6.5 Consistent Interaction

Every visual view should support, when applicable:

- filters;
- legend;
- search;
- zoom and fit;
- full screen;
- detail side panel;
- copy link;
- save configuration;
- print;
- export;
- empty state;
- data prerequisites/help;
- current/target indicator.

### 6.6 Accessibility

- Keyboard access for controls.
- Text alternatives for color-based status.
- Sufficient contrast.
- Table alternative for important graphs.
- Screen-reader labels for actions.

---

## 7. Suggested Architecture

### Frontend

Prefer:

- a centralized view registry;
- shared `ArchitectureViewShell`;
- shared filter components;
- shared card side panel;
- reusable graph legends;
- reusable “data prerequisite” empty state;
- report configuration persistence;
- lazy-loaded routes;
- domain-specific view components under `frontend/src/features/views/` or the existing reports structure.

Do not create a second parallel reporting framework unless the current report framework cannot support the requirements.

### Backend

Prefer:

- existing card, relation, metamodel and report APIs;
- dedicated aggregation endpoints only for performance or authorization correctness;
- generic typed graph response models;
- server-side filtering;
- stable API contracts;
- no database migrations for purely presentational views.

Possible generic response:

```json
{
  "nodes": [],
  "edges": [],
  "metrics": {},
  "filters": {},
  "truncated": false,
  "generatedAt": ""
}
```

### Data Contract

For every view, document:

- required card types;
- required relation types;
- required attributes;
- optional attributes;
- calculation rules;
- handling of unknown data;
- permission behavior;
- maximum expected volume.

---

## 8. Definition of Done for Every View

A view is complete only when:

- business question and target audience are documented;
- data prerequisites are documented;
- route and navigation are registered;
- permissions are enforced in frontend and backend;
- English and Arabic translations exist;
- RTL is tested;
- loading, empty, error and partial-data states work;
- card drill-down works;
- filters work;
- print/export behavior is defined;
- unit/component tests exist;
- backend tests exist where an endpoint is added;
- frontend production build succeeds;
- no existing report regression is introduced;
- documentation and screenshots are updated.

---

## 9. Recommended Build Order

1. Repository audit and central view registry
2. EA View Library
3. Application Summary and Visualize action
4. Capability-to-Application enhancements
5. Application Integration View
6. Current vs Target comparison
7. Data ownership, relationship and CRUD views
8. Technology Deployment and Cloud View
9. Standards and Security Traceability
10. Beneficiary Journey views
11. Advanced comparison and vulnerability views

This sequence delivers value early, avoids duplicate reports, and establishes reusable infrastructure before implementing complex domain views.

---

## 10. AI Agent Execution Prompt

Use the following prompt with a coding agent:

> You are working on the repository `https://github.com/alrehaili/turbo-ea`.
>
> Read `README.md`, `NORA.md`, `ViewPlan.md`, `CHANGELOG.fork.md`, `AGENTS.md`, the frontend routing/navigation, report components, backend report APIs, metamodel configuration, permissions and localization before changing code.
>
> Follow `EA_VIEWS_IMPLEMENTATION_PLAN.md`.
>
> First, audit the repository and create a table of implemented, partial, missing and data-blocked EA views. Do not implement anything until the audit confirms that the requested feature does not already exist under another name.
>
> Implement only the current phase. Reuse existing report shells, APIs, cards, relations, side panels, saved-report features, RBAC, localization and design tokens. Avoid database migrations unless the phase explicitly requires one and no configurable-metamodel solution is possible.
>
> Preserve Arabic/RTL, English, cost redaction, authorization, exports, print behavior and deep links.
>
> For the selected phase:
>
> 1. describe the business question;
> 2. identify existing reusable code;
> 3. list files to modify;
> 4. identify APIs and permissions;
> 5. implement the smallest coherent solution;
> 6. add tests;
> 7. run frontend build, type checks, lint and relevant backend tests;
> 8. report changed files, design decisions, limitations and test results.
>
> Never create a duplicate view merely because the requested name differs. Enhance or compose existing views whenever possible.

---

## 11. First Recommended Development Task

Phases 0 and 1 already exist (section 2.5). Start instead with the **View Library polish + Phase 2 completion** slice:

1. Extend `neaViewpoints.ts` entries with `question` (en/ar), `permission`, and `module` fields; make `EaViewLibraryPage.tsx` filter launchability by them and add a search box over names + questions.
2. Add a Vitest route-integrity test: every registry `path` matches a declared route in `App.tsx`; no duplicate `key`s.
3. Audit `ApplicationSummaryReport.tsx` against the 12 Phase-2 sections; fill missing sections by composing existing card/relation APIs.
4. Add the **Visualize** action on Application card detail linking to `/layers/application-summary?card={id}`.
5. Keep everything under the existing View Library tab — no new nav tabs, no backend schema changes.

Then proceed in this order: Phase 6 (data views) → Phase 7 (deployment/cloud) → Phase 8 (exceptions/waivers) → Phase 5 (current-vs-target) — these are the genuinely missing views.
