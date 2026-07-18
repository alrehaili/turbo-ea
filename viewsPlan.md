# NORA Views Implementation Plan (viewsPlan.md)

Tracker for implementing the 67 NORA/DGA EA viewpoints in Turbo EA.
Source analysis: [NORA_DGA_Viewpoints_vs_Turbo_EA.md](NORA_DGA_Viewpoints_vs_Turbo_EA.md) (DGA *The EA Viewpoints Document* v2.0, Dec 2024).

**Progress legend**

| Icon | Meaning |
|---|---|
| ✅ Done | View exists and is reachable at the given link (NORA-preset seeded) |
| 🟢 Available | Engine covers it today, but the NORA preset/saved view is not seeded yet |
| 🟡 Partial | Generic engine can render it after configuration (relation/subtype/preset work needed) |
| ❌ Missing | Requires new building blocks (card types/relations) or a new renderer |

**Overall: 0 / 67 done** · 27 available · 15 partial · 25 missing

**Phase 1 Status: ✅ COMPLETE**
- ViewpointDefinition model & table (migration 154)
- All 67 NORA viewpoints seeded with metadata
- `/api/v1/viewpoints` endpoints + frontend `/view-library` page live

**Phase 2 Status: ✅ COMPLETE**
- Added 7 building block card types (GovService, Beneficiary, BeneficiaryPersona, BeneficiaryJourney, ModelTemplate, Policy, Position)
- Added 9 relation types linking them (GovService→Org/Template/Process/App/Persona/Journey, Beneficiary→Persona, Persona→Journey, Org→Position)
- Unblocked 16 viewpoints (Business 14/14 ✅, Beneficiary 7/8, all matrices now seedable)
- **Ready for testing**: `/view-library` now shows all Business/Beneficiary viewpoints as 🟢 Available

---

## Implementation phases

### Phase 1 — View Library + presets (no schema changes)
1. Add a data-driven **ViewpointDefinition registry** (seeded table or JSON seed) with code, bilingual name, domain, level, type, description, stakeholders, building blocks, and target route.
2. Add **`/view-library`** page (top-level route, not under `/reports`): grid grouped by domain → level → type, each card showing progress badge + "Open view" link (the links in the tables below).
3. Seed saved views/presets for all 🟢 Available rows → flips them to ✅.

### Phase 2 — Business & Beneficiary building blocks
Add `GovService`, `Beneficiary`, `BeneficiaryPersona`, `BeneficiaryJourney` (+ stages/touchpoints), `ModelTemplate`, `Policy`, `Position/Mandate` mapping, and their relation types (seed + migration). Unblocks 16 ❌ rows and several 🟡 rows.

### Phase 3 — Data, infrastructure & security semantics
Add/standardize `DataTerm`, `DataAttribute`, `DataVault`, `Datacenter`, `Location`, `NetworkCircuit`, `SecurityService`, `SecurityFunction`, plus subtypes `Server`, `NetworkDevice`, `Storage`, `PhysicalHost`, `SecuritySoftware`, `SecurityHardware`.

### Phase 4 — Specialized generated diagrams
New renderers: Strategic House, Beneficiary Journey Map, Datacenter Distribution, Network Topology/Circuits, Security Deployment. Reuse the LDV/React-Flow and report-shell infrastructure; one registry, reusable renderers — no 67 hard-coded pages.

---

## Strategic Alignment (0/3)

| Viewpoint | Level · Type | Progress | Link / Route | Next step |
|---|---|---|---|---|
| Strategic Objectives catalog | Conceptual · List | 🟢 Available | `/inventory?type=Objective` | Seed NORA saved view (code, pillar, owner, KPI columns) |
| Objectives/Pillars | Conceptual · Matrix | 🟡 Partial | `/reports/matrix` | Confirm Pillar model + relation, seed matrix preset |
| Strategic House | Conceptual · Diagram | ❌ Missing | `/reports/strategic-house` (planned) | Phase 4 renderer (vision, mission, pillars, objectives, KPIs) |

## Business (0/14)

| Viewpoint | Level · Type | Progress | Link / Route | Next step |
|---|---|---|---|---|
| Service catalog | Conceptual · List | 🟢 Available | `/inventory?type=GovService` | Seed NORA saved view (code, owner, automation) |
| Organizational Structure | Conceptual · Diagram | 🟢 Available | `/inventory?type=Organization` (hierarchy) | Seed NORA org-chart preset |
| Business Value Chain | Conceptual · Diagram | 🟡 Partial | `/value-stream-catalogue` | Value-chain diagram preset (capabilities + services + processes) |
| Business Processes Catalog | Logical · List | 🟢 Available | `/inventory?type=BusinessProcess` | Seed NORA columns (owner, service, capability, automation) |
| Model/Template Catalog | Logical · List | 🟢 Available | `/inventory?type=ModelTemplate` | Seed NORA template catalogue |
| Policy Catalog | Logical · List | 🟡 Partial | `/grc?tab=governance` | Add Policy catalogue or extend GRC regulations |
| Organizational Units/Services | Logical · Matrix | 🟢 Available | `/reports/matrix?source=Organization&target=GovService` | Add relation + seed matrix |
| Business Capabilities/Organizational Units | Logical · Matrix | 🟢 Available | `/reports/matrix` | Seed exact NORA matrix preset |
| Interaction Model (Entity/Org Unit) | Logical · Diagram | 🟡 Partial | `/reports/dependencies` | Org-scoped context/interaction preset |
| Mandates/Positions | Physical · Matrix | 🟢 Available | `/reports/matrix?source=Position&target=Mandate` (after relation) | Add Position type + Mandate relation |
| Services/Models | Physical · Matrix | 🟢 Available | `/reports/matrix?source=GovService&target=ModelTemplate` | Add relation + seed matrix |
| Services/Business Processes | Physical · Matrix | 🟢 Available | `/reports/matrix?source=GovService&target=BusinessProcess` | Add relation + seed matrix |
| Services/Applications | Physical · Matrix | 🟢 Available | `/reports/matrix?source=GovService&target=Application` | Add relation + seed matrix |
| Business Process Diagram | Physical · Diagram | 🟢 Available | `/bpm` → process → flow | Register in View Library, link to card |

## Beneficiary Experience (0/8)

| Viewpoint | Level · Type | Progress | Link / Route | Next step |
|---|---|---|---|---|
| Beneficiary Persona Card | Conceptual · Diagram | 🟢 Available | `/inventory?type=BeneficiaryPersona` | Seed NORA persona card template |
| List of Improvements to Beneficiary Journeys | Logical · List | ❌ Missing | (planned) | Phase 2: JourneyImprovement entity (or extend from initiatives) |
| Beneficiaries/Beneficiary Personas | Logical · Matrix | 🟢 Available | `/reports/matrix?source=Beneficiary&target=BeneficiaryPersona` | Add relation + seed matrix |
| Services/Beneficiary Personas | Logical · Matrix | 🟢 Available | `/reports/matrix?source=GovService&target=BeneficiaryPersona` | Add relation + seed matrix |
| Services/Beneficiary Journeys | Logical · Matrix | 🟢 Available | `/reports/matrix?source=GovService&target=BeneficiaryJourney` | Add relation + seed matrix |
| Beneficiary Personas/Beneficiary Journeys | Logical · Matrix | 🟢 Available | `/reports/matrix?source=BeneficiaryPersona&target=BeneficiaryJourney` | Add relation + seed matrix |
| Beneficiary Journey Map | Logical · Diagram | ❌ Missing | `/reports/journey-map` (planned) | Phase 4 renderer (stages, touchpoints, pain points) |
| Journeys/Experience Improvement Priorities | Physical · Matrix | 🟡 Partial | `/reports/matrix` (planned) | Extend BeneficiaryJourney + priority scoring |

## Data (0/8)

| Viewpoint | Level · Type | Progress | Link / Route | Next step |
|---|---|---|---|---|
| Data Entities Landscape | Conceptual · Diagram | 🟡 Partial | `/reports/dependencies` (DataObject) | Data-architecture lens preset (domains, owners, flows) |
| List of Data Owners | Logical · List | 🟡 Partial | `/inventory?type=DataObject` | Standardize Data Owner/Steward stakeholder roles + saved view |
| Data Entity/Business Capability | Logical · Matrix | 🟡 Partial | `/reports/matrix` | Confirm relation type, seed preset |
| Data Entity/Applications | Logical · Matrix | 🟢 Available | `/reports/matrix` | Seed NORA matrix preset |
| Data Vocabulary | Physical · List | ❌ Missing | `/inventory?type=DataTerm` (planned) | Phase 3: DataTerm/DataVocabulary |
| Data Vaults Catalog | Physical · List | ❌ Missing | `/inventory?type=DataVault` (planned) | Phase 3: DataVault or ITComponent subtype |
| Data Entity/Data Attributes | Physical · Matrix | ❌ Missing | (planned) | Phase 3: DataAttribute |
| Data Entity/Data Vault | Physical · Matrix | ❌ Missing | `/reports/matrix` (planned) | Phase 3, after DataVault |

## Applications (0/14)

| Viewpoint | Level · Type | Progress | Link / Route | Next step |
|---|---|---|---|---|
| Applications Landscape | Conceptual · Diagram | 🟢 Available | `/reports/portfolio` | Seed NORA conceptual preset (current/target, org filter) |
| Applications Catalog | Logical · List | 🟢 Available | `/inventory?type=Application` | Seed NORA columns (ARM fields) |
| Application/Beneficiary | Logical · Matrix | ❌ Missing | `/reports/matrix` (planned) | Phase 2, after Beneficiary |
| Application/Organizational Unit | Logical · Matrix | 🟢 Available | `/reports/matrix` | Seed exact matrix + usage semantics |
| Application/Business Service | Logical · Matrix | ❌ Missing | `/reports/matrix` (planned) | Phase 2, after GovService |
| Application/Business Process | Logical · Matrix | 🟢 Available | `/reports/matrix` | Expose as NORA preset |
| Application/Server | Logical · Matrix | 🟡 Partial | `/reports/matrix` | Phase 3: Server subtype + relation semantics |
| Applications Viewpoint by Organizational Unit | Logical · Diagram | 🟡 Partial | `/reports/portfolio` | Org-scoped landscape preset |
| Landscape of Application Modules | Logical · Diagram | 🟡 Partial | `/inventory?type=Application` (hierarchy) | Standardize module hierarchy + drill-down diagram |
| Integration Landscape | Logical · Diagram | 🟢 Available | `/reports/dependencies` | Seed integration-landscape preset |
| Applications Integration Viewpoint | Logical · Diagram | 🟢 Available | `/reports/dependencies` | Add protocol/direction/frequency overlays |
| Technical Integration Point Register | Physical · List | 🟢 Available | `/inventory?type=Interface` | Seed NORA fields + saved view |
| Application/Security Software | Physical · Matrix | 🟡 Partial | `/reports/matrix` | Phase 3: SecuritySoftware subtype |
| Applications by Development Type / Source Type | Physical · Diagram | 🟡 Partial | `/reports/portfolio` | Add developmentType/sourceType fields + preset |

## Technology (0/12)

| Viewpoint | Level · Type | Progress | Link / Route | Next step |
|---|---|---|---|---|
| Landscape of Datacenter Distribution | Conceptual · Diagram | 🟡 Partial | `/reports/datacenter-map` (planned) | Phase 3 Datacenter/Location + Phase 4 renderer |
| Landscape of Technology Architecture Capabilities | Conceptual · Diagram | 🟡 Partial | `/reports/capability-map` (TechCategory) | Tech reference-model landscape preset |
| Infrastructure Tools Catalog | Logical · List | 🟢 Available | `/inventory?type=ITComponent` | Seed NORA catalogue (subtype + lifecycle) |
| Infrastructure Services Catalog | Logical · List | 🟢 Available | `/inventory?type=ITComponent` (Service/IaaS/PaaS/SaaS) | Seed exact view + provider fields |
| Datacenter/Service Provider | Logical · Matrix | 🟡 Partial | `/reports/matrix` (planned) | Phase 3: Datacenter + relations |
| Datacenter/Application | Logical · Matrix | 🟡 Partial | `/reports/matrix` (planned) | Phase 3: deployment relation |
| Network Architecture Landscape | Logical · Diagram | 🟡 Partial | `/reports/dependencies` | Network topology semantics or preset |
| Physical Host Hardware Catalog | Physical · List | 🟢 Available | `/inventory?type=ITComponent` (Hardware) | Phase 3: PhysicalHost subtype + columns |
| Servers Catalog | Physical · List | 🟢 Available | `/inventory?type=ITComponent` | Phase 3: Server subtype + saved view |
| Network Devices Catalog | Physical · List | 🟢 Available | `/inventory?type=ITComponent` | Phase 3: NetworkDevice subtype + saved view |
| Storage Catalog | Physical · List | 🟢 Available | `/inventory?type=ITComponent` | Phase 3: Storage subtype + saved view |
| Diagram of Network Connectivity Circuits | Physical · Diagram | ❌ Missing | `/reports/network-circuits` (planned) | Phase 3 NetworkCircuit + Phase 4 topology renderer |

## Security (0/8)

| Viewpoint | Level · Type | Progress | Link / Route | Next step |
|---|---|---|---|---|
| Security Service/Service Provider | Conceptual · Matrix | 🟡 Partial | `/reports/matrix` (planned) | Phase 3: SecurityService + provider relation |
| Landscape of Security Architecture Capabilities | Conceptual · Diagram | 🟡 Partial | `/reports/capability-map` (planned lens) | Security capability/reference-model lens |
| Security Hardware Catalog | Logical · List | 🟢 Available | `/inventory?type=ITComponent` (Hardware) | Phase 3 subtype + NORA saved view |
| Security Software Catalog | Logical · List | 🟢 Available | `/inventory?type=ITComponent` (Software) | Phase 3 subtype + NORA saved view |
| Security Services Catalog | Logical · List | 🟡 Partial | `/inventory?type=ITComponent` (Service) | Security-service classification + saved view |
| Security HW/SW Function / Application Locations | Logical · Matrix | ❌ Missing | `/reports/matrix` (planned) | Phase 3: SecurityFunction + Location relations |
| Security HW/SW Functions / Related Applications | Logical · Matrix | 🟡 Partial | `/reports/matrix` | Phase 3: SecurityFunction attributes, then seed |
| Distribution of Security Hardware in Datacenters | Physical · Diagram | ❌ Missing | `/reports/security-deployment` (planned) | Phases 3+4: Datacenter + deployment renderer |

---

## How to update this file

- When a viewpoint's NORA preset ships, change its Progress to **✅ Done** and make the Link a real route (with the saved-report/bookmark id if applicable).
- Update the **Overall** counter and per-domain `(n/total)` headings.
- New routes introduced by Phase 4 renderers replace the "(planned)" placeholders.

## Phase 1 Deliverables (Completed)

### Implemented
1. **ViewpointDefinition model** (`backend/app/models/viewpoint_definition.py`) — governs all 67 viewpoints
   - Columns: code, name_en/ar, domain, level, type, description_en/ar, building_blocks (JSONB), target_route, status, sort_order
   - Indices on code (unique) and domain
2. **Migration 154** — creates `viewpoint_definitions` table
3. **Seed data** (`backend/app/services/seed_viewpoints.py`) — all 67 NORA viewpoints seeded on startup
4. **API** (`backend/app/api/v1/viewpoints.py`)
   - `GET /viewpoints?domain=X&level=Y&status=Z&page=1&page_size=50` — paginated list with filters
   - `GET /viewpoints/{code}` — single viewpoint detail
5. **Frontend** (`frontend/src/features/view-library/ViewLibraryPage.tsx`)
   - Route: `/view-library`
   - Grid grouped by domain → level, filterable
   - Progress badges (✅ Done · 🟢 Available · 🟡 Partial · ❌ Missing)
   - Click card → navigate to target route or alert if missing
   - Bilingual (en/ar), showing building blocks

### How to Test
```bash
# Backend
cd backend && alembic upgrade head
# Restart app — seed runs, migration applied

# Frontend
# Navigate to http://localhost:5173/view-library
# Filter by domain/level, click cards to navigate or see what's missing
```

### What's Left
- **Phase 2**: Add missing building blocks (GovService, Beneficiary, Persona, Journey, ModelTemplate, Policy, etc.)
- **Phase 3**: Add infrastructure/data/security subtypes and standardized relations
- **Phase 4**: Build specialized renderers (Strategic House, Journey Map, Network Topology, Security Deployment, etc.)
