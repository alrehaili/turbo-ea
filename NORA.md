# NORA Alignment Analysis for Turbo EA

**Source document**: Guideline for National Overall Reference Architecture (NORA) V1.0, Digital Government Authority (DGA), Kingdom of Saudi Arabia, 2 January 2024 (Document No: DGA-1-2-1-212).

**Purpose of this document**: Compare NORA against Turbo EA's current capabilities (metamodel, views, governance, reporting) and define a concrete implementation backlog so Turbo EA can serve Saudi government entities as a NORA-compliant EA tool while remaining TOGAF-compatible.

---

## 1. NORA Summary

### 1.1 Context — the NEA Framework

NORA is the *methodology guideline* inside the Saudi **National Enterprise Architecture (NEA) Framework**. The NEA Framework consists of:

- **Long-term plan** (vision & objectives) and **strategy / policy** layers
- **Meta Model**, **Maturity Model** (measured via **Qiyas**), and **Best Practice** assets
- **Five Reference Models**: PRM, BRM, DRM, ARM, TRM/SP
- **Segment Architecture** and **NEA System Capability Building**
- **Continuous Governance**
- **NORA** itself — the how-to guideline agencies follow to build their own EA

Agencies must align their EA to the national reference models so the whole-of-government can identify reusable/shared components and consolidate IT investment.

### 1.2 The five NEA reference models

| Model | Content | Relationship |
|---|---|---|
| **PRM** — Performance Reference Model | Outcome-focused measurement framework; measurement indicators / KPIs | Sets performance standards for all other models |
| **BRM** — Business Reference Model | Whole-of-government classification of business functions: **Business Area → Line of Business (LoB) → Business Function → Sub-Business Function** | Drives ARM, DRM, TRM |
| **ARM** — Application Reference Model | Categorisation of **Application Systems, Application Components, Application Interfaces**; identifies sharing/reuse/consolidation opportunities | Supports BRM |
| **DRM** — Data Reference Model | **Data Model, Data Classifications, Data Structures, Data Exchanges**; standardises data for reuse | Supplies data to ARM |
| **TRM** — Technology Reference Model | **Service Area → Service Category → Service Standard** taxonomy of technologies + technology standards for interoperability | Supports ARM/DRM and end users |

Optional additional models: Security Reference Model, Service Reference Model, Infrastructure Reference Model, Performance Architecture.

### 1.3 The NORA methodology — 10 stages + continuous governance

| Stage | Name | Key deliverables (artifacts) |
|---|---|---|
| 1 | Develop EA Project Strategy | EA value propositions, goals, scope, approach, cost estimate; approved EA Project Strategy; e-transformation maturity assessment (Qiyas) |
| 2 | Develop EA Project Plan | EA committees & teams (EA Governance Committee, EA Working Team, Business-Domain WT, IT WT); approved EA Project Plan |
| — | **Continuous Governance** (all stages) | Program management, Change management, Capability management, Policy management, Performance management |
| 3 | Analyze Current State | EA Requirements; Environment Analysis Report (internal + external); **SWOT Analysis Report** |
| 4 | Develop EA Framework | EA Vision/Mission, **Architecture Objectives**, **Architecture Principles**, EA Framework structure, taxonomy, **EA documentation standard**, **artifact review & approval process** |
| 5 | Build Reference Models | Agency PRM, BRM, ARM, DRM, TRM (aligned to NEA models) |
| 6 | Build Current Architecture | Current **BA, AA, DA, TA** + per-domain artifacts (below) + **Summary of Improvement Opportunities** |
| 7 | Build Target Architecture | Target BA, AA, DA, TA (3–5 year blueprint); target architecture directions |
| 8 | Develop Transition Plan | Gap analysis → **Transition project list → prioritised list → transition roadmap → resource plan** |
| 9 | Develop Management Plan | **EA Usage Plan**, **EA Management Plan** |
| 10 | Execute & Maintain | Execution, maintenance, **maturity assessment** |

Every stage's deliverables require **EA Governance Committee approval** — artifact-level review/approval is the backbone of the methodology.

### 1.4 Required artifacts per architecture domain

**Business Architecture (BA)** — Purpose/Direction; BA Principles; Business Areas (BRM); Lines of Business (BRM); Business Functions (BRM); Sub-Business Functions (BRM); Business Processes; **Organization Chart**; **Service Catalogue**.

**Application Architecture (AA)** — Purpose/Direction; AA Principles; Application Systems (ARM); Application Components (ARM); Application Interfaces (ARM); **Application Catalogue**; Application Functions; Application Relationships; Application Overview (diagram).

**Data Architecture (DA)** — Purpose/Direction; DA Principles; Data Model (DRM); **Data Classifications** (DRM); Data Structures (DRM); **Data Exchanges** (DRM); Conceptual Data Model; Logical Data Model; **Data Flow Diagrams**; **Database Portfolio Catalogue**; **Data Dictionary**.

**Technology Architecture (TA)** — Purpose/Direction; TA Principles; Service Areas (TRM); Service Categories (TRM); **Service Standards** (TRM); Infrastructure Overview (diagram); Infrastructure Description; **Hardware Catalogue**; **Software Catalogue**.

### 1.5 Governance model

- **e-Transformation Committee** — top-level sponsor; approves EA Project Strategy; DGA communicates with it to initiate agency EA.
- **EA Governance Committee** — steers the EA project; approves *every* stage deliverable; recommended to report to the e-Transformation Committee.
- **EA Core Team / EA Working Team / Business-Domain Working Team / IT Working Team** — build the artifacts.
- **Chief Architect** — presents deliverables for approval.
- **Five continuous governance areas**: Program (schedule/budget/progress tracking), Change (awareness & promotion), Capability (training, org structure), Policy (standards & regulations mandating adoption), Performance (KPIs measuring EA success).

### 1.6 Principles and standards

NORA requires agencies to define **architecture principles per domain** (EA-wide + BA/AA/DA/TA principles), an **EA documentation standard**, **technology service standards** (TRM), and **data standards** (DRM). Policy management turns architecture decisions into binding agency policies.

---

## 2. NORA ↔ Turbo EA Capability Mapping

Legend: ✅ supported · 🟡 partial · ❌ missing · 🔁 exists but needs rename/adaptation for NORA

### 2.1 Reference models & taxonomies

| NORA concept | Turbo EA today | Status | Notes |
|---|---|---|---|
| BRM 4-level taxonomy (Business Area → LoB → Business Function → Sub-Business Function) | `BusinessCapability` with unlimited hierarchy + `capabilityLevel` (L1–L5, Macro) | 🔁 | Hierarchy mechanics exist; NORA needs **named levels** and BRM-code per node. The Capability Catalogue import is the natural vehicle for a **NEA BRM catalogue** |
| ARM (Application Systems / Components / Interfaces) | `Application` (+ subtypes Business Application, Microservice, AI Agent, Deployment), `Interface` (Logical Interface, API, MCP Server) | ✅ | Terminology maps cleanly: System→Application, Component→Microservice subtype, Interface→Interface. Needs ARM category code field |
| DRM (Data Model / Classification / Structure / Exchange) | `DataObject` (hierarchy, generic attributes) | 🟡 | DataObject covers "data entity" only. **Data Classification** (Saudi NDMO levels), **Data Exchange**, **Database Portfolio**, **Data Dictionary** are missing |
| TRM (Service Area → Category → Standard) | `TechCategory` (hierarchy) + `ITComponent` (Software/Hardware/SaaS/PaaS/IaaS/Service/AI Model) | 🟡 | TechCategory ≈ Service Area/Category. **Service Standard** (a technology standard with status: emerging/current/declining/retired) is missing |
| PRM (measurement indicators / KPIs) | `Objective` card; `kpi_snapshots` (tool-internal metrics only); calculated fields | 🟡 | No first-class **KPI / Performance Indicator** entity linked to Objectives and services. Calculations engine is a strong foundation |
| Service Catalogue (business/digital services) | `BusinessContext` subtype "Business Product"; no service entity | ❌ | Need a **GovService** card type (citizen/business/government-facing digital services with delivery channels, maturity) |

### 2.2 Architecture domains and artifacts

| NORA artifact | Turbo EA today | Status | Notes |
|---|---|---|---|
| Organization Chart | `Organization` type with hierarchy + subtypes | ✅ | Hierarchy view on card detail; no dedicated org-chart visual report |
| Business Processes | `BusinessProcess` + full BPM module (BPMN 2.0, versions, approval workflow, assessments) | ✅ | Stronger than NORA requires |
| Application Catalogue | Inventory (AG Grid), Excel import/export, CSV/JSON export | ✅ | |
| Application Relationships / Overview | Relations + Dependencies Report (LDV), DrawIO diagrams | ✅ | |
| Data Flow Diagrams | DrawIO diagrams; `flowDirection` on `relAppToInterface` | 🟡 | Free-form only; no data-exchange entity to make flows reportable |
| Database Portfolio Catalogue | Nothing dedicated (ITComponent/Software can approximate) | ❌ | |
| Data Dictionary | Nothing | ❌ | |
| Conceptual/Logical Data Model | DrawIO diagrams (free-form) | 🟡 | Acceptable as diagrams; no model registry |
| Hardware / Software Catalogue | `ITComponent` subtypes Hardware/Software + EOL integration | ✅ | EOL (endoflife.date) integration is a differentiator |
| Infrastructure Overview | DrawIO + Dependencies Report | ✅ | |
| Service Standards (TRM) | Nothing | ❌ | Needs new entity with compliance status per ITComponent |
| SWOT / Environment Analysis Report | Nothing structured (documents/attachments only) | ❌ | |
| Summary of Improvement Opportunities | TurboLens (duplicates, modernization) partially generates these | 🟡 | TurboLens output is not yet a governable "improvement opportunity" record |

### 2.3 Current vs Target architecture and transition

| NORA concept | Turbo EA today | Status | Notes |
|---|---|---|---|
| Current architecture (as-is landscape) | The whole inventory *is* the current architecture | ✅ | |
| Target architecture (3–5y blueprint) | Lifecycle phases (plan/phase-in/active/phase-out/end-of-life); TurboLens Architect target architecture + proposed cards | 🟡 | Lifecycle dates imply future states, but there is **no architecture-state dimension** (current/transition/target) and no plateau/roadmap-slice concept to view "the landscape as of 2028" per state. TimelineSlider partially covers time travel |
| Gap analysis (current vs target) | TurboLens Architect gap analysis (AI-driven, per assessment) | 🟡 | No systematic current-vs-target gap report across the whole landscape |
| Transition projects / roadmap / resources | `Initiative` (Idea/Program/Project/Epic) + full PPM module (WBS, tasks, budgets, costs, risks, Gantt) + Roadmap report | ✅ | Strong. Needs the gap→project linkage (which gaps does this initiative close) |

### 2.4 Governance

| NORA concept | Turbo EA today | Status | Notes |
|---|---|---|---|
| Artifact review & approval process | `approval_status` on every card (approve/reject/reset, auto-BROKEN on edit); BPM flow-version approval workflow | 🟡 | Card-level approval exists but is single-step. NORA needs a **multi-step review → Chief Architect → EA Governance Committee** workflow with an audit trail per stage deliverable |
| EA Governance Committee / e-Transformation Committee / working teams | Roles (RBAC) + stakeholder roles per card type | 🔁 | RBAC can model committees as roles; needs seeded NORA role set + a committee/decision log (ADR is close) |
| Architecture decisions log | ADR module (status, context, alternatives, consequences, sign-off) | ✅ | Map to committee decisions; add committee/meeting metadata |
| Architecture principles (EA + per-domain) | `ea_principles` + PrinciplesAdmin + Principles Catalogue + GRC Governance tab | 🟡 | Exists but has no **domain** attribute (BA/AA/DA/TA), no approval workflow, no principle→card compliance link |
| Policy management | Compliance regulations catalogue (GRC) — regulation-driven scanner | 🔁 | The compliance engine can host **agency policies and NEA/DGA policies** as "regulations" and scan for violations |
| Performance management (EA KPIs) | Dashboard KPIs, data-quality scoring, kpi_snapshots trends | 🟡 | Measures tool adoption/data quality, not EA program outcomes; needs PRM KPIs |
| Program management of EA project | PPM module | 🔁 | Run the "EA implementation" itself as an Initiative with WBS mapped to NORA stages |
| Maturity assessment (Qiyas) | Nothing | ❌ | Needs a maturity-assessment module or survey template |
| Stage deliverable tracking (10 stages) | Nothing | ❌ | Needs an "EA Program" checklist/tracker keyed to NORA stages and linking evidence (cards, reports, documents, diagrams) |

### 2.5 Platform / cross-cutting

| NORA need | Turbo EA today | Status | Notes |
|---|---|---|---|
| Arabic UI (government mandate) | `ar` locale with full RTL support | ✅ | Major advantage; ensure all new NORA features ship with `ar` translations first-class |
| Self-hosting / data sovereignty | Fully self-hosted Docker stack | ✅ | Critical for KSA government (data residency) |
| Whole-of-government alignment (report to DGA) | Workspace transfer (TEA↔TEA), OData feeds, MCP server, OpenAPI | 🟡 | No DGA/NEA submission format; exports exist to build one |
| Documentation standard | Metamodel is data-driven; card layouts configurable | ✅ | Admin can shape artifacts to the agency's documentation standard |
| "Fact sheets"→"cards" naming vs NORA "artifacts" | Cards | 🔁 | Keep "cards" internally; expose NORA terminology through metamodel labels + translations (data, not code) |

### 2.6 What exists but should be renamed/adapted (via metamodel data, not code)

| Turbo EA element | NORA-aligned presentation |
|---|---|
| `BusinessCapability` | "Business Function (BRM)" — relabel via `translations`; add `brmCode`, `brmLevel` (Business Area / LoB / Business Function / Sub-Business Function) fields |
| Layer "Strategy & Transformation" | Keep; hosts PRM artifacts (Objectives, KPIs) |
| Layer "Business Architecture" | Matches NORA BA directly |
| Layer "Application & Data" | NORA separates **AA** and **DA** — split visually (see §5) |
| Layer "Technical Architecture" | NORA "Technology Architecture (TA)" — label change only |
| `Initiative` | "Transition Project" in NORA reports (relabel or add subtype) |
| `ea_principles` | Split/attribute by domain: EA, BA, AA, DA, TA principles |
| Compliance regulations | Add NEA/DGA policy packs (NDMO data standards, NCA ECC, DGA digital standards) alongside GDPR-style packs |
| TurboLens "modernization/duplicates" | Feed into a governable "Improvement Opportunity" record (NORA Stage 6.6) |

---

## 3. Implementation Backlog

Grouped by priority. Every item lists: **NORA requirement → module/screen → entities & relations → roles/workflow → Saudi-government example**.

### 3.1 Must-have for basic NORA alignment

#### M1. NORA metamodel profile (seeded, data-driven)

- **NORA requirement**: Stage 4 (EA Framework/taxonomy) + Stage 5 (reference models). Agencies need artifact types matching BRM/ARM/DRM/TRM out of the box.
- **Module/screen**: `backend/app/services/seed.py` (new optional profile, e.g. `SEED_PROFILE=nora`), Admin → Metamodel. No new UI needed — metamodel is data.
- **Entities/attributes**:
  - `BusinessCapability`: add fields `brmCode` (text), `brmLevel` (single_select: businessArea | lineOfBusiness | businessFunction | subBusinessFunction), `neaAlignment` (text — NEA BRM reference).
  - `Application`: add `armCode` (text), `armCategory` (single_select from NEA ARM), `automationLevel` (single_select: fullyAutomated | partiallyAutomated | manual — NORA Stage 6.3 explicitly requires this), `sharedService` (boolean — national shared-systems flagging).
  - `ITComponent`: add `trmServiceArea` / `trmServiceCategory` (single_select or relation to TechCategory), `trmCode`.
  - `DataObject`: add `drmCode`, `dataClassification` (single_select: topSecret | secret | confidential | public — Saudi NDMO classification levels), `dataOwnerOrg` (via relation).
  - All new option sets carry full `translations` including `ar`.
- **Roles/workflow**: Admin applies the profile; existing `admin.metamodel` permission.
- **Example**: Ministry of Municipal Affairs tags its "Building Permits System" with `armCode=ARM-3.2`, `automationLevel=partiallyAutomated`, `sharedService=false`; its "Permit Issuance" Business Function carries `brmLevel=businessFunction`, `brmCode=BRM-07.3`.

#### M2. GovService card type (Service Catalogue)

- **NORA requirement**: BA artifact #9 "Service Catalogue" — the current and target list of business services. Core to Saudi digital government (services are what Qiyas / DGA measure).
- **Module/screen**: New seeded card type `GovService` (Business Architecture layer); appears automatically in Inventory, Card Detail, reports.
- **Entities/attributes**: `GovService` fields: `serviceCode` (text), `beneficiaryType` (multi_select: citizen | resident | business | government | visitor), `deliveryChannel` (multi_select: portal | mobileApp | serviceCenter | callCenter | kiosk), `serviceMaturity` (single_select: informational | interactive | transactional | proactive), `feeModel` (single_select: free | paid), `slaDays` (number), `monthlyTransactions` (number).
  Relations (one per pair, per metamodel rule): `GovService → BusinessProcess` ("is realized by"), `GovService → Application` ("is delivered by"), `Organization → GovService` ("provides"), `GovService → BusinessCapability` ("supports").
- **Roles/workflow**: standard inventory permissions; service owners as a stakeholder role (`service_owner`) on the type.
- **Example**: "Issue Commercial Registration" service — beneficiary: business; channels: portal + mobile; maturity: transactional; realized by "CR Issuance Process" (BPMN in BPM module); delivered by "Meras Platform".

#### M3. Technology Standard entity (TRM Service Standards)

- **NORA requirement**: TRM artifact "Service Standard" — the list of technology standards in use / targeted; Policy Management (standards mandating adoption).
- **Module/screen**: New seeded card type `TechStandard` (Technical Architecture layer); a new "Standards" report view under Reports.
- **Entities/attributes**: `TechStandard` fields: `standardStatus` (single_select: proposed | emerging | current | declining | retired — a technology-standards lifecycle), `standardBody` (text — e.g. DGA, NCA, W3C), `mandate` (single_select: mandatory | recommended | optional), `reviewDate` (date), `specUrl` (url).
  Relations: `TechStandard → TechCategory` ("categorized under" — places it in TRM Service Area/Category), `ITComponent → TechStandard` ("complies with").
- **Roles/workflow**: `admin.metamodel` to define; approval workflow (M5) applies — a standard is only "current" once the Governance Committee approves it. A calculated field on ITComponent can derive "standards-compliant?" via the calculation engine.
- **Example**: Agency mandates "TLS 1.3" (mandate=mandatory, status=current, body=NCA) and marks "SOAP 1.1" declining; the Standards report lists all ITComponents still on declining standards — feeding transition projects.

#### M4. Architecture state dimension (current / transition / target)

- **NORA requirement**: Stages 6 & 7 — the same artifact set exists twice (current BA/AA/DA/TA and target BA/AA/DA/TA); Stage 8 gap analysis between them.
- **Module/screen**: Backend: new nullable column `architecture_state` on `cards` (enum: `current` (default) | `transition` | `target`) + same on `relations.attributes`; Alembic migration. Frontend: state filter chip in Inventory sidebar, state badge on cards (reuse the LDV "NEW" dashed-border pattern for target items), a state selector on reports (Dependencies, Landscape, Capability Map render current-only by default, target overlay on toggle).
- **Entities/attributes**: `cards.architecture_state`; `successor_id` (nullable self-FK) so a target Application can declare which current Application it replaces — this powers gap analysis.
- **Roles/workflow**: `inventory.edit` to set state; transition `target → current` gated on approval (the "go-live" of a target card is a governance event, emitted to the event bus).
- **Example**: Current "Legacy HR System" (state=current, lifecycle end-of-life 2027) is succeeded by target "Unified HR Platform" (state=target, successor of legacy). The Dependencies report toggles between the 2025 landscape and the 2028 blueprint; the gap report (M6) lists the delta.
- **Why not just lifecycle?** Lifecycle describes *when a real asset lives*; architecture state describes *which blueprint a card belongs to*. A target card may itself have a planned lifecycle. Keeping them orthogonal avoids overloading lifecycle semantics and stays TOGAF-compatible (states ≈ plateaus).

#### M5. Multi-step artifact approval workflow (EA Governance Committee)

- **NORA requirement**: Stage 4.8 "EA artifact management processes" + every stage's "Obtain governance approval". Single-click approve is not enough: NORA's flow is *working team drafts → Chief Architect reviews → EA Governance Committee approves*.
- **Module/screen**: Extend the existing `approval_status` machinery (`cards.py` approval endpoint) with a configurable review chain; Admin → Settings → Governance tab to enable "NORA governance mode" and map roles to steps; Card Detail approval badge grows a stepper.
- **Entities/attributes**: New table `approval_steps` (id, card_id, step_no, required_role_key, status: pending|approved|rejected, actor_user_id, comment, acted_at). `approval_status` gains state `IN_REVIEW`. Config: per card type, an ordered list of role keys (JSONB on `card_types` or app_settings), e.g. `["chief_architect", "ea_governance_committee"]`.
- **Roles/workflow**: Seed roles `chief_architect`, `ea_governance_committee`, `ea_working_team` (M7). Submitting for review notifies the next step's role members (existing notification service); rejection resets to draft with comment; all steps stamped into the events audit trail. The existing "approval breaks on substantive edit" rule stays.
- **Example**: The EA team finishes documenting the target Application Architecture for the "Digital Permits" segment; the working team submits 14 cards for review; the Chief Architect approves 12 and rejects 2 with comments; the Committee chair bulk-approves the 12 from the Inventory grid; the Qiyas evidence pack (A3) later cites the approval timestamps.

#### M6. Gap analysis & transition-project linkage

- **NORA requirement**: Stage 8.1–8.3 — derive transition projects from current/target gap analysis; build the prioritised roadmap.
- **Module/screen**: New report "Gap Analysis" under Reports (`/reports/gap-analysis`): three-column view (current-only cards = retire/replace candidates; changed pairs via `successor_id`; target-only = build/buy). Each gap row gets an "assign to Initiative" action.
- **Entities/attributes**: New relation type `Initiative → *` already exists per pair in most cases; add a generic `closesGap` attribute on the initiative relation, or simpler: a new relation `Initiative → Card` "delivers" is already representable — reuse existing relation types and add a `transitionRole` single_select attribute (introduces | modifies | retires) on the Initiative relation types' `attributes_schema` (consistent with the one-relation-type-per-pair rule).
- **Roles/workflow**: `reports.view` to see; `inventory.edit` + `relations.manage` to assign gaps. Prioritisation happens in PPM (already supports budget/schedule/priority).
- **Example**: Gap report shows "Legacy HR System → Unified HR Platform"; the architect assigns both to Initiative "HR Modernization 1446H" with transitionRole retires/introduces; PPM Gantt becomes the NORA Transition Roadmap; the roadmap report can now be filtered to transition projects only.

#### M7. NORA governance role pack + committee seeding

- **NORA requirement**: Stage 2.1 — EA Governance Committee, EA Working Team, Business-Domain WT, IT WT; Chief Architect.
- **Module/screen**: Seed data only (`seed.py` roles) + docs. Admin → Roles.
- **Entities/attributes**: New app-level roles: `chief_architect` (all inventory + approve step 1), `ea_governance_committee` (approve step 2, reports, read-all), `ea_working_team` (inventory create/edit, no approve), `domain_owner` (scoped stakeholder role per card type: BA/AA/DA/TA owner). Uses existing `roles.permissions` JSONB — no schema change.
- **Roles/workflow**: n/a (this *is* the roles item).
- **Example**: The Deputy Minister for Digital Transformation chairs the committee (role `ea_governance_committee`); the EA consultant vendor staff get `ea_working_team` so they can draft but never approve their own work — clean segregation of duties for audit.

#### M8. Arabic-first delivery of all NORA features

- **NORA requirement**: Implicit — Saudi government users; DGA documents are bilingual.
- **Module/screen**: i18n discipline: every new key lands in `ar` (plus the other 8 locales) in the same PR; new metamodel content (M1–M3) ships `translations.ar` on every type/field/option; docs pages get `.ar.md` variants (new locale suffix for docs if not present).
- **Example**: `GovService` renders as "الخدمة الحكومية", `brmLevel=businessArea` as "مجال الأعمال". RTL already works (AG Grid/Recharts opt-in via `useIsRtl` per existing conventions).

### 3.2 Important enhancements

#### I1. Data Architecture module completion (DRM)

- **NORA requirement**: DA artifacts — Data Classifications, Data Exchanges, Database Portfolio Catalogue, Data Dictionary.
- **Module/screen**: Extend `DataObject` + two new card types; a "Data Landscape" report.
  - `DataObject` gains `dataClassification` (from M1), `piiFlag` (boolean), `retentionPeriod` (text), `authoritativeSource` (boolean).
  - New type `DataExchange` (Application & Data layer, no hierarchy): fields `exchangeMethod` (single_select: api | fileTransfer | messaging | database | manual), `frequency` (single_select: realtime | daily | weekly | monthly | adhoc), `externalParty` (text — e.g. another agency via GSB), `viaGsb` (boolean — Saudi Government Service Bus). Relations: `Application → DataExchange` ("sends/receives", direction attribute), `DataExchange → DataObject` ("carries").
  - New type `Database` — or, cheaper, a new `ITComponent` subtype `Database` + relation `DataObject → ITComponent` ("stored in"). Recommended: **subtype**, avoids type proliferation.
  - Data Dictionary = the DataObject inventory grid with a saved view (name, definition, classification, owner, source) exported to Excel — no new entity needed; ship it as a seeded Bookmark.
- **Roles/workflow**: data steward stakeholder role on DataObject; classification changes above `confidential` could require approval (M5 chain).
- **Example**: "National ID Number" DataObject: classification=secret, PII=true, authoritative source=Absher/NIC, exchanged with the agency via GSB (DataExchange viaGsb=true, method=api, realtime), stored in "Core Registry DB" (ITComponent subtype Database).

#### I2. KPI / Performance Indicator entity (PRM)

- **NORA requirement**: PRM — outcome-focused measurement indicators; Continuous Governance performance management.
- **Module/screen**: New card type `KPI` (Strategy & Transformation layer) + a "Performance" report (scorecard grid: KPI, baseline, target, actual, RAG).
- **Entities/attributes**: `KPI` fields: `unit` (text), `baselineValue` / `targetValue` / `currentValue` (number), `measurementFrequency` (single_select), `direction` (single_select: higherIsBetter | lowerIsBetter), `ragStatus` (calculated via the calculation engine from current vs target). Relations: `Objective → KPI` ("is measured by"), `KPI → GovService` ("measures"), `Initiative → KPI` ("improves").
- **Roles/workflow**: `inventory.edit`; performance manager stakeholder role. Periodic value updates can be driven by the existing Surveys module (data-maintenance surveys targeting KPI cards).
- **Example**: Objective "Raise digital service adoption" measured by KPI "% transactions via digital channels" (baseline 55%, target 92% per DGA benchmarks, current 71%, RAG=amber) — feeding the agency's Qiyas submission.

#### I3. EA Program tracker (NORA 10-stage checklist)

- **NORA requirement**: The methodology itself — stages 1–10 with named deliverables and per-deliverable governance approval; program management.
- **Module/screen**: New page `/nora-program` (or a tab under GRC → Governance): a stage-by-stage checklist seeded from NORA's deliverable tables; each deliverable row links evidence (a card set, a saved report, a diagram, a document/file attachment, a SoAW/ADR) and carries an approval state.
- **Entities/attributes**: New tables `ea_program_stages` (seeded: 10 stages + continuous governance) and `ea_program_deliverables` (id, stage_no, key, title, status: notStarted|inProgress|inReview|approved, evidence JSONB [{kind: card_query|report|diagram|document|soaw|adr, ref}], approved_by, approved_at). Admin-editable so agencies can tailor scope (NORA explicitly allows tailoring).
- **Roles/workflow**: `ea_working_team` updates status/evidence; `ea_governance_committee` approves — reuses M5 semantics. Progress % per stage surfaces on the Dashboard.
- **Example**: Stage 6 row "Current Application Architecture" links: inventory view filtered `type=Application, architecture_state=current`, the Dependencies report saved-report id, and the approval record; DGA liaison sees the agency is 70% through Stage 6.

#### I4. Improvement Opportunity records (Stage 6.6)

- **NORA requirement**: "Summary of Improvement Opportunities" — the approved output of current-architecture analysis, classified by domain, feeding transition projects.
- **Module/screen**: New lightweight entity surfaced as a tab in GRC or on the Gap report; also the landing target for TurboLens findings ("promote to improvement opportunity" from duplicate clusters / modernization assessments — mirrors the existing compliance-finding → risk promotion pattern).
- **Entities/attributes**: Table `improvement_opportunities` (id, title, description, domain: BA|AA|DA|TA, source: manual|turbolens_duplicate|turbolens_modernization|swot, priority, status: proposed|approved|inTransition|realized|rejected, linked cards M:N, initiative_id nullable FK).
- **Roles/workflow**: working team proposes; committee approves (M5); "assign to initiative" closes the loop to the Transition Plan; realized opportunities show on a value-delivered dashboard.
- **Example**: TurboLens flags 3 overlapping document-management systems → promoted to opportunity "Consolidate ECM platforms" (domain=AA, priority=high) → approved → attached to Initiative "Shared Services Wave 2" → realized in 1447H.

#### I5. Policy packs for Saudi compliance (NDMO / NCA ECC / DGA)

- **NORA requirement**: Continuous Governance — Policy Management; alignment with national policies.
- **Module/screen**: GRC → Compliance. The regulation-driven compliance scanner already supports admin-managed regulation catalogues — add seeded packs: **NCA Essential Cybersecurity Controls (ECC)**, **NDMO Data Management & Personal Data Protection standards**, **PDPL** (Saudi Personal Data Protection Law), **DGA Digital Government Policy** checks (e.g. every GovService must have a digital channel; every Application must have an owner and BRM linkage).
- **Entities/attributes**: Rows in `compliance_regulations` + scanner rule extensions keyed on the new NORA fields (e.g. flag DataObjects with classification=secret lacking an owning Organization relation).
- **Roles/workflow**: existing `compliance.view/manage`; findings promote to risks (existing) or improvement opportunities (I4).
- **Example**: Scan reports "12 Applications have no assigned business function (BRM linkage missing — DGA alignment gap)" and "3 secret-classified DataObjects exchanged without GSB" — each becomes a finding with remediation, promotable to the Risk Register.

#### I6. NORA report pack

- **NORA requirement**: The artifact tables in Stages 6/7 are essentially *views* — NORA compliance is largely about producing them on demand.
- **Module/screen**: Reports section, new saved-report templates (seeded `saved_reports`):
  1. **BRM Explorer** — Capability Map report relabelled/filtered by `brmLevel` (Business Area → Sub-Business Function drill-down).
  2. **Service Catalogue** — GovService grid grouped by beneficiary/channel/maturity (Inventory saved view + print stylesheet).
  3. **Application Catalogue (ARM view)** — grouped by armCategory, with automationLevel heat colouring (portfolio report config).
  4. **Data Exchange Map** — Dependencies-report variant filtered to DataExchange edges (reuses LDV renderer).
  5. **TRM Standards Compliance** — TechStandard × ITComponent matrix (Matrix report config).
  6. **Transition Roadmap** — existing Roadmap/PPM Gantt filtered to `architecture_state=target` initiatives.
  7. **Org Chart** — simple tree render of Organization hierarchy (new small component or reuse hierarchy section).
- **Roles/workflow**: `reports.view`; all exportable (existing thumbnail/print/Excel machinery).
- **Example**: For the annual DGA review, the agency exports the seven views as the Current Architecture evidence pack in one afternoon instead of a two-week PowerPoint exercise.

#### I7. SWOT / Environment Analysis (Stage 3)

- **NORA requirement**: Stage 3 deliverables — EA Requirements, Environment Analysis, SWOT.
- **Module/screen**: Extend the SoAW editor pattern (`ea-delivery`): a new document template "Environment Analysis / SWOT" with structured sections (Internal, External, S/W/O/T quadrants as EditableTable), stored alongside SoAW.
- **Entities/attributes**: Reuse `statement_of_architecture_works`-style storage (new `doc_type` discriminator or a sibling table); SWOT entries optionally link cards (a Weakness can reference the Application it concerns).
- **Roles/workflow**: `soaw.create` (or a new `ea_docs.*`); committee approval via M5.
- **Example**: Weakness: "Core licensing system is a 15-year-old Oracle Forms app (links: Legacy Licensing System card)"; Opportunity: "GSB integration now available for MoI data" — both later traceable to improvement opportunities and transition projects.

### 3.3 Advanced / future capabilities

#### A1. Plateau/time-slice landscape views

- **NORA requirement**: Target architecture as a 3–5 year blueprint; transition sequencing.
- **What**: Extend M4 with named plateaus ("2025 Baseline", "2026 Transition", "2028 Target") — table `plateaus` + card membership derived from lifecycle dates + architecture_state; TimelineSlider drives all major reports.
- **Example**: The committee reviews the 2026 transition landscape showing which of the 40 transition projects have landed.

#### A2. Qiyas-style EA maturity self-assessment

- **NORA requirement**: Stage 1.3 and Stage 10 — e-transformation/EA maturity measurement (Qiyas).
- **What**: A maturity module: admin-definable assessment dimensions (per NEA Maturity Model), periodic self-assessment via the existing Surveys engine, results as radar chart + trend (kpi_snapshots pattern), gap-to-next-level recommendations. Optionally exportable in the DGA submission format once DGA publishes one.
- **Example**: The agency scores 2.4/5 on "EA Usage" — the module recommends completing the EA Usage Plan deliverable (I3 links directly to the Stage 9 row).

#### A3. DGA/NEA interchange & national alignment reporting

- **NORA requirement**: NEA federation — agencies align to national models; DGA oversight.
- **What**: An export profile ("NEA Alignment Package") bundling: BRM mapping coverage, shared-service candidates (`sharedService=true` Applications), standards compliance summary, maturity score, program status — as xlsx/zip via the workspace-io machinery. If DGA later publishes an API/schema, add a submission adapter (the migration adapter pattern in reverse).
- **Example**: Quarterly NEA alignment package generated in one click, replacing manual DGA reporting templates.

#### A4. NEA reference-model catalogues (import once published)

- **NORA requirement**: Stage 5 — agencies derive their models from the NEA PRM/BRM/ARM/DRM/TRM.
- **What**: Ship the official NEA taxonomies as importable catalogues, following the existing Capability Catalogue / Process Catalogue wheel pattern (`turbo-ea-capabilities`-style versioned packages). Auto-link agency cards to national codes.
- **Example**: Importing the NEA BRM creates the Business Area/LoB skeleton; the agency maps its existing functions onto it via `catalogueId` matching — exactly how the Macro-capability import works today.

#### A5. Segment architecture workspaces

- **NORA requirement**: NEA Framework "Segment Architecture" — architecture scoped to a business segment.
- **What**: Saved cross-entity scopes ("segments") — a named filter set (capability subtree + its applications/data/tech) applied across inventory, reports, and the program tracker. Cheaper than multi-workspace: a `segments` table + filter chip.
- **Example**: The "Licensing Services" segment shows only the 6 capabilities, 14 applications, and 3 initiatives in that slice, with its own gap report.

#### A6. AI-assisted NORA authoring (TurboLens extension)

- **What**: TurboLens prompts tuned for NORA: generate draft improvement opportunities from current-architecture analysis; draft target-architecture options per NORA Stage 7 wording; Arabic-language AI output support.
- **Example**: "Analyze current DA and propose improvement opportunities" returns candidate records into I4's proposed state — never auto-approved (governance stays human).

---

## 4. Does Turbo EA need new architecture domains?

Turbo EA's four layers map to NORA's domains almost 1:1. Recommendation: **keep four physical layers, add two virtual/report-level views, and split "Application & Data" presentationally.**

| Domain asked about | Recommendation |
|---|---|
| Business architecture | ✅ Exists (layer "Business Architecture"). Add GovService (M2) and BRM fields (M1). No structural change |
| Data architecture | 🟡 Exists inside "Application & Data". **Do not split the stored layer** (metamodel `category` strings drive many views); instead add a **Data Architecture report lens** (I1's Data Landscape + Data Exchange Map) and let NORA-profile installs relabel the layer "Application & Data Architecture". A physical split would churn every layer-keyed feature (LDV lanes, layer colors) for little gain |
| Application architecture | ✅ Exists. ARM fields via M1 |
| Technology architecture | ✅ Exists ("Technical Architecture" → relabel "Technology Architecture" in NORA profile translations). TechStandard (M3) completes TRM |
| Security architecture | 🟡 Don't create a fifth layer. NORA lists security as an *optional* reference model. Model it as: NCA ECC policy pack (I5) + Risk Register (exists) + `securityTier`/`dataClassification` attributes + a Security view (matrix of Applications × classifications × findings). A dedicated layer would fragment cards that are inherently cross-cutting |
| Integration architecture | 🟡 Covered by `Interface` + new `DataExchange` (I1) + the Data Exchange Map report. No new layer |
| Digital services / shared services | ✅ via GovService (M2) + `sharedService` flag on Application (M1) + a Shared Services report (Applications flagged shared, grouped by consuming Organizations) |
| Government interoperability / standards / compliance views | ✅ via TechStandard (M3), TRM compliance matrix (I6.5), GSB flags (I1), and policy packs (I5) — all views/reports, not new domains |

---

## 5. Recommended target information model (TOGAF + NORA, no duplication)

**Core principle: one metamodel, two vocabularies.** Turbo EA's metamodel is data-driven — exploit that instead of forking types.

1. **Single type system, framework-neutral keys.** Keep existing card-type keys (`Application`, `BusinessCapability`, …) as the stable internal vocabulary. Never create parallel NORA types (`ArmApplication` etc.) — that duplicates inventory, breaks the one-relation-type-per-pair rule's assumptions, and splits reports.

2. **NORA as a seed profile, not a fork.** A `nora` metamodel profile (M1) = additional fields, option sets, subtypes, relabelled `translations`, seeded roles, seeded saved reports, and seeded compliance packs. A TOGAF-oriented install simply doesn't apply the profile. Both live in the same codebase and database schema; migration between them is additive.

3. **Framework terminology via `translations`, per install.** NORA labels (Arabic and English) are metamodel *labels*: `BusinessCapability` displays as "Business Function (BRM)" / "الوظيفة الأعمالية" under the profile while the key never changes. This is exactly how the existing label-resolver system (`useTypeLabel` etc.) is designed to work.

4. **Classification codes as attributes, hierarchy as structure.** BRM/ARM/DRM/TRM codes are *fields* (`brmCode`, `armCode`, …) on the existing types, while the tree structure uses the existing `parent_id` hierarchy. National reference models arrive as catalogues (A4) matched by `catalogueId` — the proven Capability Catalogue mechanism.

5. **Architecture state is orthogonal to everything.** One new column (`architecture_state`, M4) + `successor_id` gives NORA current/target and TOGAF baseline/target simultaneously — one mechanism, two framework names. Do not model target architecture as separate cards types, separate workspaces, or tag hacks.

6. **Governance is a workflow layer, not a data fork.** The M5 approval chain, I3 program tracker, and I4 opportunities all *reference* cards; they never copy card data. TOGAF users get the same machinery labelled ADM-style (Phase G compliance reviews); NORA users see committee steps.

7. **Crosswalk documentation.** Ship a TOGAF ↔ NORA ↔ Turbo EA mapping table in the user manual (docs/, all locales) so mixed teams — TOGAF-certified architects working under NORA mandates — can navigate: e.g. TOGAF "Baseline Architecture" = NORA "Current Architecture" = Turbo EA `architecture_state=current`; TOGAF "Architecture Roadmap" = NORA "Transition Plan" = PPM Gantt + Roadmap report; TOGAF "Architecture Board" = NORA "EA Governance Committee" = role `ea_governance_committee`.

### Suggested sequencing

| Phase | Items | Outcome |
|---|---|---|
| 1 (foundation) | M1, M2, M7, M8 | An agency can *capture* its NORA landscape in NORA terms, in Arabic |
| 2 (governance) | M5, M3, M4 | Deliverables become *governable* artifacts; current/target modelling works |
| 3 (methodology) | M6, I3, I4, I6 | The 10-stage journey is trackable end-to-end with evidence and reports |
| 4 (compliance & data) | I1, I2, I5, I7 | DRM/PRM complete; Saudi policy packs live |
| 5 (federation) | A1–A6 | Maturity, DGA reporting, national catalogues, segments, AI assist |

---

*Prepared for the Turbo EA fork maintained at ea.rahimsapp.com. All backlog items follow existing project conventions: data-driven metamodel (no hardcoded types), Alembic migrations for schema changes, permission checks on every mutating endpoint, full i18n (10 locales, Arabic RTL first-class for this initiative), and workspace-transfer coverage for every new table/column.*
