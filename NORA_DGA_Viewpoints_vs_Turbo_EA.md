# NORA/DGA EA Viewpoints vs Turbo EA

**Review basis:** DGA *The EA Viewpoints Document*, Version 2.0 (December 2024), compared with the public `main` branch of `alrehaili/turbo-ea` as reviewed on 18 July 2026.

## Executive assessment

- **67** core NORA viewpoints identified.
- **20 Strong:** the current metamodel and report capability provide a close technical match.
- **22 Configurable:** the generic Inventory, Matrix, report or diagram engine can support the viewpoint, but a NORA preset, standardized relations, or dedicated UX is needed.
- **25 Gap:** first-class building blocks or a structured/dynamic visualization are missing.

> These numbers assess technical readiness, not official DGA compliance. Even most “Strong” items still need to be registered, named, classified and governed as NORA viewpoints.

## Domain summary

| Domain | Strong | Configurable | Gap | Total |
|---|---:|---:|---:|---:|
| Strategic Alignment | 0 | 2 | 1 | 3 |
| Business | 4 | 3 | 7 | 14 |
| Beneficiary Experience | 0 | 0 | 8 | 8 |
| Data | 1 | 3 | 4 | 8 |
| Applications | 7 | 5 | 2 | 14 |
| Technology | 6 | 5 | 1 | 12 |
| Security | 2 | 4 | 2 | 8 |
| **Total** | **20** | **22** | **25** | **67** |

## Detailed crosswalk

### Strategic Alignment

| Level | Type | NORA viewpoint | Status | Turbo EA today | Required action |
|---|---|---|---|---|---|
| Conceptual | List | Strategic Objectives catalog | **Configurable** | Objective cards, Inventory, strategy/KPI reporting | Seed a NORA saved list with objective code, pillar, owner, KPI and current/target filters. |
| Conceptual | Matrix | Objectives/Pillars | **Configurable** | Generic Matrix report and strategy relationships | Seed a fixed Objectives × Pillars matrix and validate a first-class Pillar model/relation. |
| Conceptual | Diagram | Strategic House | **Gap** | Can be drawn manually in DrawIO; no generated Strategic House | Build a dynamic Strategic House template using vision, mission, pillars, objectives and KPIs. |

### Business

| Level | Type | NORA viewpoint | Status | Turbo EA today | Required action |
|---|---|---|---|---|---|
| Conceptual | List | Service catalog | **Gap** | No first-class government service entity in the current baseline | Add GovService and seed the Service Catalogue view. |
| Conceptual | Diagram | Organizational Structure | **Strong** | Organization hierarchy and organization-chart reporting | Add the NORA name, conceptual classification and executive preset. |
| Conceptual | Diagram | Business Value Chain | **Configurable** | Value-stream catalogue and diagrams exist, but no exact generated value-chain view | Create a value-chain/value-stream diagram preset with capabilities, services and processes. |
| Logical | List | Business Processes Catalog | **Strong** | BusinessProcess inventory, process catalogue and BPM module | Seed a NORA process catalogue with process owner, service, capability, automation and status. |
| Logical | List | Model/Template Catalog | **Gap** | No dedicated Model/Template building block | Add ModelTemplate type and relationships to services and processes. |
| Logical | List | Policy Catalog | **Configurable** | GRC regulations and principles exist, but not a business-policy catalogue | Define Policy as a governed catalogue or extend the GRC catalogue with business-policy classification. |
| Logical | Matrix | Organizational Units/Services | **Gap** | Matrix engine exists, but GovService is missing | Add GovService and Organization → Service relation, then seed the matrix. |
| Logical | Matrix | Business Capabilities/Organizational Units | **Strong** | BusinessCapability and Organization with Matrix/Capability Map support | Seed the exact NORA matrix and add owner/accountability overlays. |
| Logical | Diagram | Interaction Model for the Entity / Organizational Unit | **Configurable** | Dependency/diagram tools can represent it, but no dedicated interaction model | Build a generated context/interaction view for one organization unit. |
| Physical | Matrix | Mandates/Positions | **Gap** | No first-class mandate and position mapping | Add Mandate and Position/Role concepts or formally map them to existing organization/stakeholder structures. |
| Physical | Matrix | Services/Models | **Gap** | GovService and ModelTemplate are missing | Implement after the two building blocks are added. |
| Physical | Matrix | Services/Business Processes | **Gap** | Process exists, but GovService is missing | Add Service → Process relation and a traceability matrix. |
| Physical | Matrix | Services/Applications | **Gap** | Application exists, but GovService is missing | Add Service → Application relation and a service traceability preset. |
| Physical | Diagram | Business Process Diagram | **Strong** | Full BPMN 2.0 editor/viewer with versioning and approvals | Expose it in the NORA View Library and link the diagram to its BusinessProcess card. |

### Beneficiary Experience

| Level | Type | NORA viewpoint | Status | Turbo EA today | Required action |
|---|---|---|---|---|---|
| Conceptual | Diagram | Beneficiary Persona Card | **Gap** | No first-class beneficiary/persona model | Add Beneficiary and BeneficiaryPersona types plus a persona-card template. |
| Logical | List | List of Improvements to Beneficiary Journeys | **Gap** | No journey improvement entity/workflow | Add JourneyImprovement or reuse a governed ImprovementOpportunity linked to journeys. |
| Logical | Matrix | Beneficiaries/Beneficiary Personas | **Gap** | Beneficiary and persona types are missing | Add types and relations, then seed the matrix. |
| Logical | Matrix | Services/Beneficiary Personas | **Gap** | GovService and persona types are missing | Implement after service and persona models. |
| Logical | Matrix | Services/Beneficiary Journeys | **Gap** | GovService and journey types are missing | Add BeneficiaryJourney and Service → Journey relation. |
| Logical | Matrix | Beneficiary Personas/Beneficiary Journeys | **Gap** | Persona and journey types are missing | Add relation and matrix preset. |
| Logical | Diagram | Beneficiary Journey Map | **Gap** | Can only be drawn manually; no structured journey model | Build a structured journey-map view with stages, touchpoints, pain points and channels. |
| Physical | Matrix | Beneficiary Journeys/Beneficiary Experience Improvement Priorities | **Gap** | Journey and improvement-priority models are missing | Add priority/scoring fields and a matrix or ranked heatmap. |

### Data

| Level | Type | NORA viewpoint | Status | Turbo EA today | Required action |
|---|---|---|---|---|---|
| Conceptual | Diagram | Data Entities Landscape | **Configurable** | DataObject, dependency/data-flow reports and diagrams exist | Create a Data Architecture lens showing domains/entities, ownership, applications and flows. |
| Logical | List | List of Data Owners | **Configurable** | Stakeholders/organizations can represent owners, but no NORA owner preset | Standardize Data Owner and Data Steward roles and seed a completeness-oriented list. |
| Logical | Matrix | Data Entity/Business Capability | **Configurable** | Matrix engine and relevant card types exist; relation conventions need confirmation | Seed the relation type and matrix preset. |
| Logical | Matrix | Data Entity/Applications | **Strong** | DataObject/Application relationships can be shown by Matrix and dependency reports | Seed the exact NORA matrix with CRUD/usage semantics if available. |
| Physical | List | Data Vocabulary | **Gap** | No data dictionary/vocabulary catalogue | Add DataTerm/DataVocabulary or integrate with OpenMetadata and expose a governed catalogue. |
| Physical | List | Data Vaults Catalog | **Gap** | No first-class data-vault/storage-location catalogue | Add DataVault/DataStore or a formal ITComponent subtype with data-specific fields. |
| Physical | Matrix | Data Entity/Data Attributes | **Gap** | Card fields are not equivalent to first-class data attributes | Add DataAttribute or integrate metadata assets and expose entity-attribute mappings. |
| Physical | Matrix | Data Entity/Data Vault | **Gap** | DataVault model is missing | Implement after the storage/vault building block is added. |

### Applications

| Level | Type | NORA viewpoint | Status | Turbo EA today | Required action |
|---|---|---|---|---|---|
| Conceptual | Diagram | Applications Landscape | **Strong** | Portfolio, dependency, reference-model and diagram reports provide application landscapes | Create an exact NORA conceptual preset with current/target and organization filters. |
| Logical | List | Applications Catalog | **Strong** | Inventory with filters, saved views and Excel import/export | Seed the NORA application catalogue with ARM fields and required columns. |
| Logical | Matrix | Application/Beneficiary | **Gap** | Beneficiary model is missing | Implement after Beneficiary/Persona building blocks. |
| Logical | Matrix | Application/Organizational Unit | **Strong** | Application and Organization relations plus Matrix reporting | Seed the exact matrix and ownership/usage semantics. |
| Logical | Matrix | Application/Business Service | **Gap** | First-class GovService is missing | Implement after GovService. |
| Logical | Matrix | Application/Business Process | **Strong** | BPM reports, process-application matrix and generic Matrix support | Expose as a NORA preset. |
| Logical | Matrix | Application/Server | **Configurable** | Application–ITComponent relations can approximate servers | Standardize Server subtype and relation semantics, then seed the matrix. |
| Logical | Diagram | Applications Viewpoint by Organizational Unit | **Configurable** | Portfolio can filter by organization; no exact generated organizational application landscape | Build an organization-scoped application landscape preset. |
| Logical | Diagram | Landscape of Application Modules | **Configurable** | Application hierarchy/subtypes can model modules; no exact module landscape | Standardize module/component hierarchy and create a drill-down diagram. |
| Logical | Diagram | Integration Landscape | **Strong** | Interoperability, dependency, data-flow and integration-status reports exist | Create the NORA integration landscape preset and map Interface/DataExchange semantics. |
| Logical | Diagram | Applications Integration Viewpoint | **Strong** | Dependency and integration reports cover application-to-application relationships | Add protocol, direction, frequency and criticality overlays. |
| Physical | List | Technical Integration Point Register | **Strong** | Interface inventory is a close match | Seed required NORA fields and an integration-point saved view. |
| Physical | Matrix | Application/Security Software | **Configurable** | ITComponent relations and Matrix report exist, but security-software classification is not formalized | Standardize Security Software subtype and relation type. |
| Physical | Diagram | Applications Viewpoint by Development Type Showing the Source Type | **Configurable** | Portfolio reporting can group/filter on configured fields; no NORA preset | Add/standardize developmentType and sourceType fields and seed the visual. |

### Technology

| Level | Type | NORA viewpoint | Status | Turbo EA today | Required action |
|---|---|---|---|---|---|
| Conceptual | Diagram | Landscape of Datacenter Distribution | **Configurable** | IT components and diagrams exist; no dedicated datacenter-distribution view | Add/standardize Datacenter and Location models and generate a distribution view. |
| Conceptual | Diagram | Landscape of Technology Architecture Capabilities | **Configurable** | Reference models, TechCategory and technology reporting provide a foundation | Create a technology-capability/reference-model landscape preset. |
| Logical | List | Infrastructure Tools Catalog | **Strong** | ITComponent inventory can filter tools/software/platforms | Seed the NORA catalogue with subtype and lifecycle fields. |
| Logical | List | Infrastructure Services Catalog | **Strong** | ITComponent Service/IaaS/PaaS/SaaS-style subtypes support a service catalogue | Seed the exact view and ownership/provider fields. |
| Logical | Matrix | Datacenter/Service Provider | **Configurable** | Generic Matrix and Organization/provider modeling can support it; datacenter conventions need work | Standardize Datacenter and ServiceProvider types/relations. |
| Logical | Matrix | Datacenter/Application | **Configurable** | Application–ITComponent/deployment relations can support it | Standardize Datacenter deployment relation and seed the matrix. |
| Logical | Diagram | Network Architecture Landscape | **Configurable** | Dependency graphs and DrawIO exist; no network-specific generated view | Add network topology semantics and a dedicated renderer or preset. |
| Physical | List | Physical Host Hardware Catalog | **Strong** | ITComponent Hardware inventory and EOL tracking | Seed a Physical Host subtype and NORA columns. |
| Physical | List | Servers Catalog | **Strong** | ITComponent inventory can represent servers | Standardize Server subtype and seed the catalogue. |
| Physical | List | Network Devices Catalog | **Strong** | ITComponent inventory can represent network devices | Standardize NetworkDevice subtype and seed the catalogue. |
| Physical | List | Storage Catalog | **Strong** | ITComponent inventory can represent storage | Standardize Storage subtype and seed the catalogue. |
| Physical | Diagram | Diagram of Network Connectivity Circuits | **Gap** | DrawIO can draw it manually; no structured circuit model or generated topology | Add NetworkCircuit/Link with endpoints, bandwidth, provider and redundancy; build topology view. |

### Security

| Level | Type | NORA viewpoint | Status | Turbo EA today | Required action |
|---|---|---|---|---|---|
| Conceptual | Matrix | Security Service/Service Provider | **Configurable** | GRC, Organization/provider and ITComponent foundations exist, but SecurityService is not first-class | Add SecurityService subtype/type and provider relation, then seed the matrix. |
| Conceptual | Diagram | Landscape of Security Architecture Capabilities | **Configurable** | GRC/risk/compliance reporting is strong, but it is not a security-capability architecture view | Add security capabilities or a security reference-model lens and create the diagram. |
| Logical | List | Security Hardware Catalog | **Strong** | ITComponent Hardware can be classified and filtered as security hardware | Standardize subtype and NORA saved view. |
| Logical | List | Security Software Catalog | **Strong** | ITComponent Software can be classified and filtered as security software | Standardize subtype and NORA saved view. |
| Logical | List | Security Services Catalog | **Configurable** | Can be modeled using ITComponent Service, but no explicit security-service catalogue | Add classification and seed the catalogue. |
| Logical | Matrix | Security Hardware and Software Function/Application Locations | **Gap** | Security Function and Application Location are not first-class, consistently related concepts | Add SecurityFunction and Location/deployment relationships. |
| Logical | Matrix | Security Hardware and Software Functions/Related Applications | **Configurable** | Application–ITComponent relations exist, but security-function semantics are missing | Add SecurityFunction or function attributes and seed the matrix. |
| Physical | Diagram | Distribution of Security Hardware in Datacenters | **Gap** | No structured datacenter/security deployment view | Implement after Datacenter, security subtype and deployment relationships are standardized. |

## The main structural gap

Turbo EA already has the three rendering mechanisms NORA expects:

- **List:** Inventory and saved views.
- **Matrix:** Matrix cross-reference report.
- **Diagram:** BPMN, DrawIO, dependency graphs, capability/process/organization and other reports.

However, it does not yet have a first-class **NORA Viewpoint Registry** that records and governs:

- viewpoint code and bilingual name;
- domain, type and conceptual/logical/physical level;
- description, benefits and target stakeholders;
- relevant building blocks and relation types;
- methodology phases/steps;
- route or saved-report configuration;
- current/target architecture state;
- owner, approval status, version and last review date.

Therefore, the application has a strong reporting engine, but not yet the complete NORA viewpoint product layer.

## Recommended implementation sequence

### Phase 1 — NORA View Library without major schema changes

1. Add a data-driven `ViewpointDefinition` registry.
2. Seed all 67 NORA definitions and their bilingual metadata.
3. Add `/reports/view-library` grouped by domain, type and level.
4. Map the 20 Strong and 22 Configurable viewpoints to existing Inventory, Matrix, BPM and report configurations.
5. Add executive and detailed variants and current/target filters.

### Phase 2 — Missing business and beneficiary building blocks

Add `GovService`, `Beneficiary`, `BeneficiaryPersona`, `BeneficiaryJourney`, journey stages/touchpoints and governed improvement opportunities. This closes the largest functional gap.

### Phase 3 — Data, infrastructure and security semantics

Add or standardize `DataVocabulary/DataTerm`, `DataAttribute`, `DataVault/DataStore`, `Datacenter`, `Location`, `NetworkCircuit`, `SecurityService`, `SecurityFunction`, and their relations.

### Phase 4 — Generated specialized diagrams

Implement dynamic Strategic House, journey map, datacenter distribution, network topology/circuits, and security deployment views. Keep DrawIO for free-form architecture, but do not treat manually maintained drawings as the only implementation of a NORA viewpoint.

## Recommended product principle

Do **not** build 67 unrelated hard-coded pages. Use one viewpoint registry and reusable renderers:

- List renderer
- Matrix renderer
- Hierarchy/landscape renderer
- Network/dependency renderer
- Journey renderer
- Strategic-house renderer
- BPMN/DrawIO link renderer

This fits Turbo EA’s data-driven metamodel and saved-report architecture and keeps NORA alignment configurable for each Saudi government entity.

## Sources

- Digital Government Authority, *The EA Viewpoints Document*, Version 2.0, December 2024.
- https://github.com/alrehaili/turbo-ea
- https://github.com/alrehaili/turbo-ea/blob/main/ViewPlan.md
- https://github.com/alrehaili/turbo-ea/blob/main/NORA.md