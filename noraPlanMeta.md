# NORA Content Meta Model — Exact Fidelity Rebuild

**Goal:** Replace the "map NORA onto the tool's generic types" approach with the **exact** NORA
Content Meta Model from *The "EA Content Meta Model" Document (National EA Framework, Dec 2024)* —
every one of the **45 building blocks** across **7 domains** becomes its own independent card type,
with the document's exact attributes and connections.

**Source of truth:** `الحقيبة التوعوية - البنية المؤسسية الوطنية/الدليل الإسترشادي لبناء النموذج العام/The "EA Content Meta Model" Document-Draft.pdf`

## Key decisions (locked)

1. **Fresh start** — no data migration. New installs seed the exact NORA metamodel; existing data on
   generic types is **not** re-typed. (Phase 5 migration is dropped.)
2. **Full card types** — Vision, Mission, KPI, Phase, Step all become first-class card types (not
   settings/fields).
3. **Faithful over convenient** — the tool's built-in modules (BPM, cost/EOL reports, TurboLens) get
   rewired to the NORA-native keys rather than forcing NORA onto generic keys.
4. Overloaded generic types (`Organization`, `Provider`, `ITComponent`, `Interface`, `BusinessContext`)
   are **hidden** (`is_hidden`) when the NORA profile is active — non-destructive, reversible.

---

## Overall progress

**~95%** — Phases 1–4 complete; Phase 5 nearly done (demo cards + tests + CHANGELOG/VERSION landed).
Only the user-manual/`docs/` translation pass remains.

| Phase | Scope | Status | % |
|-------|-------|--------|---|
| 0 | Plan & decisions | ✅ Done | 100% |
| 1 | Author 45 building-block card types (attributes + 9 locales) | ✅ Done | 100% |
| 2 | Author connection catalogue (120 relations) | ✅ Done | 100% |
| 3 | Hide generic tool types when NORA active | ✅ Done | 100% |
| 4 | Rewire tool modules (BPM, reports, TurboLens) to NORA keys | ✅ Done | 100% |
| 5 | Tests + docs + seed-demo alignment | 🟡 In progress | 80% |

**Done so far:**
- **Phase 1F (Technology):** 9 new independent types in
  `backend/app/services/seed_nora_technology.py` — Server, PhysicalHost, NetworkDevice, Storage,
  ContainerizationEngine, InfrastructureService, InfrastructureManagementTool, PeripheralDevice,
  License.
- **Phase 1A (Strategic):** 3 new types in `backend/app/services/seed_nora_strategic.py` — Vision,
  Mission, Project. (KPI already exists via `nora_profile`; reused key `KPI`.)
- **Phase 1B (Business):** 5 new types in `backend/app/services/seed_nora_business.py` —
  OrganizationalUnit, ServiceProvider (split from generic `Organization` / `Provider`, 5.3.2.2.2–3;
  generics to be hidden in Phase 3) plus ProcessesGroup, Role, Activity (5.3.2.2.5/10/7).
- **Phase 1E (Applications):** `seed_nora_applications.py` — ApplicationModule, ApplicationFunction
  (5.3.5.2.2–3).
- **Phase 1C (Beneficiary):** `seed_nora_beneficiary.py` — Phase, Step (5.3.3.2.4–5).
- **Phase 1G (Security split):** `seed_nora_security.py` — SecurityHardware, SecuritySoftware
  (split from combined `SecurityFunction`, 5.3.7). Plus `Product` (5.3.2.2.8) added to
  `seed_nora_business.py` (split from the `BusinessContext` subtype).
- **Phase 2 (Technology relations):** 51 relations in
  `backend/app/services/seed_nora_technology_relations.py` — 5.3.6.3 hosts / manages / uses-license
  / linked-through / owned-by / provided-by backbone, one-per-pair enforced. `ownedBy` / `providedBy`
  now point at the NORA-native `OrganizationalUnit` / `ServiceProvider`.

All appended into `seed.TYPES` (50 types) / `seed.RELATIONS`; `test_i18n_seed.py` +
`test_seed_demo.py` green, `ruff` clean.

Legend: ✅ done · 🟡 in progress · ⬜ not started

---

## Phase 1 — Building-block card types (45)

Each type: `key`, `label`, `icon`, `color`, `category` (domain), `fields_schema` (doc attributes),
`translations` for all 9 non-English locales (incl. Arabic/RTL), `stakeholder_roles`, `sort_order`.
Authored into `NORA_CARD_TYPES` in `backend/app/services/nora_profile.py` (consumed by the activate
button + `SEED_PROFILE=nora`).

Status key: ✅ exists standalone · 🟡 exists but overloaded (must split to native key) · ⬜ to build

### 1A · Strategic Alignment (7)

| # | Building block | Target key | Current | Status |
|---|----------------|-----------|---------|--------|
| 1 | Vision | `Vision` | **built** | ✅ |
| 2 | Mission | `Mission` | **built** | ✅ |
| 3 | Objective | `Objective` | standalone | ✅ |
| 4 | Pillar | `Pillar` | standalone | ✅ |
| 5 | Initiative | `Initiative` | standalone | ✅ |
| 6 | Project | `Project` | **built** (Initiative subtype still present — remove later) | ✅ |
| 7 | Key Performance Indicator | `KPI` | standalone (via `nora_profile`) | ✅ |

### 1B · Business Architecture (12)

| # | Building block | Target key | Current | Status |
|---|----------------|-----------|---------|--------|
| 8 | Business Capability | `BusinessCapability` | standalone | ✅ |
| 9 | Organizational Unit | `OrganizationalUnit` | **built** (generic `Organization` to be hidden in Phase 3) | ✅ |
| 10 | Service Provider | `ServiceProvider` | **built** (generic `Provider` to be hidden in Phase 3) | ✅ |
| 11 | Service | `GovService` | standalone | ✅ |
| 12 | Processes Group | `ProcessesGroup` | **built** | ✅ |
| 13 | Business Process | `BusinessProcess` | standalone | ✅ |
| 14 | Product | `Product` | **built** (split from `BusinessContext` subtype) | ✅ |
| 15 | Position | `Position` | standalone | ✅ |
| 16 | Role | `Role` | **built** | ✅ |
| 17 | Policy | `Policy` | standalone | ✅ |
| 18 | Model/Template | `ModelTemplate` | standalone | ✅ |
| 19 | Activity | `Activity` | **built** | ✅ |

### 1C · Beneficiary Experience (5)

| # | Building block | Target key | Current | Status |
|---|----------------|-----------|---------|--------|
| 20 | Beneficiary | `Beneficiary` | standalone | ✅ |
| 21 | Beneficiary Journey | `BeneficiaryJourney` | standalone | ✅ |
| 22 | Persona | `Persona` | standalone | ✅ |
| 23 | Phase | `Phase` | **built** | ✅ |
| 24 | Step | `Step` | **built** | ✅ |

### 1D · Data Architecture (3)

| # | Building block | Target key | Current | Status |
|---|----------------|-----------|---------|--------|
| 25 | Data Entity | `DataObject` | standalone (reused) | ✅ |
| 26 | Data Vault | `DataVault` | standalone | ✅ |
| 27 | Data Attributes | `DataAttribute` | standalone | ✅ |

### 1E · Applications Architecture (4)

| # | Building block | Target key | Current | Status |
|---|----------------|-----------|---------|--------|
| 28 | Application | `Application` | standalone | ✅ |
| 29 | Application Module | `ApplicationModule` | **built** | ✅ |
| 30 | Application Function | `ApplicationFunction` | **built** | ✅ |
| 31 | Technical Integration Interface | `Interface` | **attrs via `nora_profile`** (5.3.5.2.4) | ✅ |

### 1F · Technology Architecture (11)

| # | Building block | Target key | Current | Status |
|---|----------------|-----------|---------|--------|
| 32 | Data Center | `Datacenter` | **attrs backfilled** (5.3.6.2.1) | ✅ |
| 33 | Physical Host | `PhysicalHost` | **built** | ✅ |
| 34 | Server | `Server` | **built** | ✅ |
| 35 | Containerization Engine | `ContainerizationEngine` | **built** | ✅ |
| 36 | Network Device | `NetworkDevice` | **built** | ✅ |
| 37 | Network Link | `NetworkCircuit` | **attrs backfilled** (5.3.6.2.5) | ✅ |
| 38 | Storage | `Storage` | **built** | ✅ |
| 39 | Infrastructure Service | `InfrastructureService` | **built** | ✅ |
| 40 | Infrastructure Management Tool | `InfrastructureManagementTool` | **built** | ✅ |
| 41 | Peripheral Device | `PeripheralDevice` | **built** | ✅ |
| 42 | License | `License` | **built** | ✅ |

### 1G · Security Architecture (3)

| # | Building block | Target key | Current | Status |
|---|----------------|-----------|---------|--------|
| 43 | Security Hardware | `SecurityHardware` | **built** (split from `SecurityFunction`) | ✅ |
| 44 | Security Software | `SecuritySoftware` | **built** (split from `SecurityFunction`) | ✅ |
| 45 | Security Service | `SecurityService` | standalone | ✅ |

**Phase 1 tally:** 45 ✅ · 0 🟡 · 0 ⬜ = **45 — COMPLETE** ✅

All 45 NORA building blocks are realised as independent card types with the document's attributes and
full 9-locale translations. `Datacenter` / `NetworkCircuit` / `Interface` attribute backfills applied
in-place via `seed_nora_technology_attrs.py` (existing fields preserved).

---

## Phase 2 — Connection catalogue (~120 relations)

Encode the document's connection tables into `relation_types` (one relation type per ordered
`(source, target)` pair; variants as relation attributes). Source sections:

Two modules, both merged **collision-safe** into `seed.RELATIONS` (skip any ordered `(source,target)`
pair already owned by the base seed, the technology backbone, or `nora_profile`):
`seed_nora_technology_relations.py` (§5.3.6.3 backbone, 51) and `seed_nora_domain_relations.py`
(the other six domains, 66 landed). **117 NORA relations total.**

| Doc section | Domain | Status |
|-------------|--------|--------|
| 5.3.1.3 | Strategic Alignment | ✅ (Vision/Mission/Project/Objective/Pillar/Initiative + KPI edges) |
| 5.3.2.3 | Business Architecture | ✅ (OrgUnit/ServiceProvider/GovService/ProcessesGroup/Role/Activity/Product/Position/Policy/ModelTemplate) |
| 5.3.3.3 | Beneficiary Experience | ✅ (Beneficiary/Journey/Persona/Phase/Step) |
| 5.3.4.3 | Data Architecture | ✅ (DataObject/DataVault/DataAttribute + security) |
| 5.3.5.3 | Applications | ✅ (Application/Module/Function/Interface + security) |
| 5.3.6.3 | Technology | ✅ (backbone, 51 relations) |
| 5.3.7.3 | Security | ✅ (secured-through edges for Application/Interface/DataVault/Server) |

KPI relations live in `nora_profile.NORA_RELATION_TYPES` alongside the `KPI` type definition
(6 edges: Objective/Initiative/Project → KPI, and KPI → GovService/BusinessProcess/OrganizationalUnit).

---

## Phase 3 — Hide non-NORA types (fully-NORA picker) ✅

Done in `nora_profile.py` (`NORA_PROFILE_VERSION` 8 → 10). `apply_nora_profile` sets `is_hidden=True`
on **every** non-NORA card type so the inventory / create-card picker shows only the exact 45-block
model; `set_togaf_profile` un-hides them. Non-destructive — only the flag flips; cards/relations are
preserved. Any single type can be un-hidden from the admin metamodel editor.

Hidden set (`NORA_HIDDEN_TYPE_KEYS`, 16 types):
- **Superseded 1:1** — `Organization`→`OrganizationalUnit`, `Provider`→`ServiceProvider`,
  `ITComponent`→the 9 tech types, `SecurityFunction`→`SecurityHardware`/`SecuritySoftware`.
- **No NORA-doc block** — base generics (`Platform`, `BusinessContext`, `TechCategory`, `Location`),
  pre-canonical duplicates (`Journey`→`BeneficiaryJourney`, `BeneficiaryPersona`→`Persona`), and
  fork extensions beyond the doc (`Mandate`, `DataDomain`, `DataProduct`, `DataDictionary`,
  `DataTerm`, `JourneyImprovement`).

**Test debt fixed:** the two pre-existing `test_nora_profile` collision failures (which also failed on
`main`) are resolved — `nora_profile`'s type/relation defs legitimately overlap the base seed for
types the fork promoted (`GovService`, `Pillar`, `Policy`, `Persona`, `BeneficiaryJourney` + 3
GovService relations); the guards now allow-list those and still catch new accidental collisions.

---

## Phase 4 — Module rewiring ✅

Shared source of truth added: `backend/app/services/type_groups.py`
(`NORA_TECH_COMPONENT_TYPE_KEYS`, `INFRASTRUCTURE_TYPE_KEYS` = ITComponent + the 9 NORA tech types,
`EOL_TYPE_KEYS` = Application + infrastructure). Modules import from it instead of hardcoding
`"ITComponent"`, so they work under both the NORA and TOGAF profiles.

| Module | Assumed generic key | Status |
|--------|--------------------|--------|
| Inventory / reports layer colors | layer categories | ✅ no change — colours are category-driven (`LAYER_COLORS`); new types carry the right `category` + colour |
| BPM | `BusinessProcess` | ✅ no change — `BusinessProcess` is NORA-native |
| Cost reports | cost fields | ✅ no change — aggregates cost-typed fields generically; new types carry `capitalCost`/`operatingCost` |
| EOL linking endpoint (`eol.py`) | `["Application","ITComponent"]` | ✅ rewired to `EOL_TYPE_KEYS` |
| EOL report (`reports.py`) | `["Application","ITComponent"]` + `== "ITComponent"` | ✅ rewired to `EOL_TYPE_KEYS` / `INFRASTRUCTURE_TYPE_KEYS`; app-impact flows through the NORA `hosts` relations |
| Compliance scanner | `["Application","ITComponent"]` | ✅ rewired to include NORA tech types |
| Tech landscape report (`reports.py`) | `ITComponent` hierarchy + subtypes | ✅ rewired — fetches `TECH_LANDSCAPE_TYPE_KEYS`; DC roots by `type=="Datacenter"`; containment built from **both** `parent_id` (TOGAF) and the NORA `hosts` relations (`TECH_CONTAINMENT_RELATION_KEYS`); security by type or subtype |
| TurboLens domain split (`turbolens.py`) | `ITComponent` target_type | ✅ rewired — TA/AA split uses `INFRASTRUCTURE_TYPE_KEYS` |
| Maturity indicators (`maturity_indicators.py`) | `ITComponent` count/lifecycle | ✅ rewired — technology-layer count + lifecycle span `INFRASTRUCTURE_TYPE_KEYS` (`_cards_with_lifecycle` now takes a list) |
| Data-flow service (`data_flow_service.py`) | `ITComponent` neighbour type | ✅ rewired — component neighbours matched against `INFRASTRUCTURE_TYPE_KEYS` |
| tech_standards (`tech_standards.py`) | `App → ITComponent → TechCategory` | ➖ N/A under NORA — the chain ends at `TechCategory`/`TechStandard`, which have no NORA-doc equivalent (both hidden); degrades gracefully to empty |

Tests: `test_eol`, `test_reports`, `test_reports_extended`, `test_compliance_scanner`,
`test_technology_landscape`, `test_maturity`, `test_turbolens_ai`, `test_nora_landscape` green;
`ruff` clean; app imports.

---

## Phase 5 — Tests, docs, demo 🟡

- [x] `test_i18n_seed.py` — 9-locale completeness for all new types (green throughout).
- [x] Registry/seed tests for new types + relations (`test_seed_demo`, `test_nora_profile`).
- [x] `seed_demo_nora.py` — sample cards + relations for the new NORA types (23 cards, 18 relations;
      `test_seed_demo_nora` green).
- [x] CHANGELOG `[2.25.0]` + VERSION bump (2.24.0 → 2.25.0).
- [ ] User-manual + `docs/` updates (all 8 locales) — outstanding.

---

## Open items / risks

- **9-locale translation volume** — 23 new types × attributes is a large i18n surface; Arabic (RTL)
  mandatory.
- **`ITComponent` split** — the biggest change; downstream cost/EOL/TurboLens logic keyed to it.
- **One-relation-type-per-pair rule** — some doc connections between the same pair must collapse into
  a single relation type with an attribute discriminator.
- **Fresh-start scope** — existing installs keep old data on generic types; only new installs get the
  exact model. Confirmed acceptable.
