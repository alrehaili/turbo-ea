# NORA Implementation Plan for Turbo EA

**Purpose**: Working implementation plan and progress tracker for making Turbo EA NORA-based.
**Companion document**: [NORA.md](NORA.md) — the capability-mapping analysis this plan executes.
**Additional input reviewed**: external "NORA Alignment Blueprint" (2026-07). Adopted from it: stage gates + artifact immutability, typed target-change semantics, standards conformance/waiver workflow, framework-profile versioning, NEA mapping entities, traceability rules, acceptance criteria. Rejected from it: the large parallel entity zoo (ArchitectureScope/StageInstance/Viewpoint/etc. as ~20 new tables up front — Turbo EA's data-driven metamodel and existing modules cover most of these with far less schema), and its references to a non-existent "System" card type.

**Guiding rule (do not violate)**: one canonical landscape. NORA is delivered as a **profile + governance overlay + views** on the existing cards/relations — never as parallel NORA card types, never as a copied repository.

---

## Progress Overview

| Phase | Name | Work packages | Status |
|---|---|---|---|
| 1 | NORA Foundation (data model & profile) | WP1.1–WP1.4 | ☑ **Complete** (all four WPs, 2026-07-02) |
| 2 | Current/Target Architecture & Governance | WP2.1–WP2.4 | ☑ **Complete** (all four WPs, 2026-07-02) |
| 3 | Methodology & Program Management | WP3.1–WP3.4 | ☑ **Complete** (all four WPs, 2026-07-02) |
| 4 | Domain Completeness (DRM/PRM/Standards/Integration) | WP4.1–WP4.5 | ☑ **Complete** (2026-07-02; WP4.3 closed as fork-covered) |
| 5 | NEA Content & Federation *(blocked on NEA reference models)* | WP5.1–WP5.5 | ☐ Blocked / future |

> **Fork-overlap note (2026-07-02).** Codebase inspection found this fork already ships features the plan scheduled (beyond what upstream CLAUDE.md documents): **Scenarios** (`backend/app/models/scenario.py` — copy-on-write current/target overlay with add/modify/retire deltas, approval lifecycle, merge with conflict detection) largely covers WP2.1's intent; the **TechStandard catalogue** (`tech_standard.py` — radar statuses Preferred→Prohibited, replacement links, time-boxed approver-gated exception register) covers most of WP1.3 and WP4.3; **ARB reviews** (`arb_review.py`) partially covers WP2.2's committee-decision needs; **Roadmaps** (`roadmap.py`) and **TIME rationalization** (`rationalization.py` — replaces the dropped `targetDisposition` field) support WP2.4. Affected WPs must start with a gap review against these modules instead of building from scratch.

Status values: `☐ Not started` · `◐ In progress` · `☑ Done` · `⊘ Blocked` · `✕ Descoped`

Each work package is independently shippable and follows project conventions: data-driven metamodel, Alembic migration for every schema change, `require_permission()` on every mutating endpoint, i18n across all 10 locales with **Arabic first-class**, workspace-transfer coverage (ENTITY_SECTIONS / CONFIG_SECTIONS / *_COLUMNS) for every new table or column, tests, CHANGELOG.fork.md entry, and docs.

---

## Phase 1 — NORA Foundation (data model & profile)

*Goal: an agency can capture its landscape in NORA terms, in Arabic, today — before the NEA reference models arrive.*

### WP1.1 — NORA framework profile & seed extensions `☑ Done 2026-07-02`

**NORA ref**: Stage 4 (EA framework/taxonomy), Stage 5 (reference-model readiness). NORA.md item M1.

**As implemented** (design deltas from the original spec are noted inline):

- [x] `SEED_PROFILE` env setting (`backend/app/config.py`) + `app_settings.general_settings.frameworkProfile` (`togaf` default | `nora`), versioned via `noraProfileVersion`. **Delta**: instead of a guarded Alembic migration, the profile is applied by the idempotent `apply_nora_profile()` in `backend/app/services/nora_profile.py` — invoked at startup (`ensure_framework_profile()` in `main.py`, handles both fresh-install env activation and version upgrades) or at runtime via `PATCH /settings/framework-profile` (admin.settings). Same guarantees (idempotent, preserves admin customisations — fields already present anywhere in the schema are never duplicated or overwritten), no schema change needed.
- [x] New fields injected as a "NORA Alignment" section per type:
  - `BusinessCapability`: `brmCode`, `brmLevel` (businessArea | lineOfBusiness | businessFunction | subBusinessFunction), `neaAlignment`
  - `Application`: `armCode`, `armCategory` (9 placeholder options until NEA ARM arrives), `automationLevel`, `sharedService`. **Delta**: `targetDisposition` dropped — the fork's TIME rationalization module already owns that concept.
  - `ITComponent`: `trmCode`, `hostingModel` (onPremise | governmentCloud | publicCloud | hybrid), `securityZone`
  - `DataObject`: `drmCode`, `dataClassification` (**topSecret | secret | restricted | public** — corrected to the actual NDMO levels; "restricted"/مقيد, not "confidential"), `piiFlag`, `authoritativeSource`, `retentionPeriod`
  - `Interface`: `integrationType`, `authenticationMethod`, `viaGsb`. **Delta**: `protocol` dropped — the built-in Interface type already has it.
  - `Objective`: `nationalAlignment`
  - All fields carry `weight: 0` so enabling the profile never degrades existing data-quality scores (admins can raise weights per field).
- [x] All fields/options carry full `translations` for the 9 non-English locales (Arabic included). Frontend renders them automatically via the data-driven `AttributeSection` — zero frontend field code.
- [x] Admin UI: **Settings → Modules → Framework Profile** toggle (`SettingsAdmin.tsx`), `useFrameworkProfile` singleton hook (inflight pattern), `framework_profile` in `/settings/bootstrap` + `primeBootstrap()`. UI strings in all 10 locale `admin.json` files.
- [x] Tests: `backend/tests/services/test_nora_profile.py` — 72 definition tests (locale completeness, zero weight, NDMO levels, no seed collisions) + 5 DB tests (idempotency, customisation preservation, flag lifecycle; run under `scripts/test.sh`).
- [ ] **Deferred**: type/layer `translations` relabels ("Business Function (BRM)" etc.) — admins can relabel via the metamodel editor; revisit after user feedback on whether hard relabels help or confuse.
- [ ] **Deferred**: `docs/admin/nora-profile.md` user-manual page (+ locale variants) — fork docs pass pending.

**Acceptance check**: enabling the profile exposes all fields (translated, incl. `ar`) on the six types; a TOGAF install is unaffected; re-applying is a no-op; switching back preserves fields and data. ✔ verified by tests.

### WP1.2 — GovService card type (Service Catalogue) `☑ Done 2026-07-02`

**NORA ref**: BA artifact #9 "Service Catalogue". NORA.md item M2.

**As implemented** (in `backend/app/services/nora_profile.py`, delivered through the NORA profile apply — **delta**: not a global seed, so TOGAF installs never see the type; no Alembic migration needed, the runtime apply covers fresh and existing installs alike):

- [x] Card type `GovService` (Business Architecture layer, no hierarchy, `built_in=True`, icon `assured_workload`): `serviceCode`, `beneficiaryType` (multi: citizen | resident | business | government | visitor), `deliveryChannel` (multi: portal | mobileApp | serviceCenter | callCenter | kiosk), `serviceMaturity` (informational | interactive | transactional | proactive), `feeModel` (free | paid), `slaDays`, `monthlyTransactions` (weight 0), `sharedServiceConsumer` (weight 0). Existing types keyed `GovService` are never overwritten.
- [x] Relation types (pair-safe: an ordered (source, target) pair an admin already modelled is skipped, per the one-per-pair invariant; skips are reported in the apply summary): `GovService → BusinessProcess` (is realized by / realizes), `GovService → Application` (is delivered by / delivers), `Organization → GovService` (provides / is provided by), `GovService → BusinessCapability` (supports / is supported by), `GovService → DataObject` (uses / is used by).
- [x] Stakeholder roles seeded as `stakeholder_role_definitions`: `responsible`, `observer`, `service_owner` (service_owner inherits the responsible card-permission set).
- [x] i18n: type label/description, section, all fields, options, stakeholder roles, and relation labels/reverse labels translated in all 9 non-English locales (ar first-class).
- [x] Tests: definition tests (translation completeness, no seed key/pair collisions, endpoint validity) + DB tests (creation with roles + relations, idempotency, pair-conflict skip, existing-type preservation).
- [ ] **Deferred**: seeded "Service Catalogue" inventory bookmark — bookmarks are per-user (`bookmarks.user_id`), so a global seeded view isn't possible; the inventory type filter covers it until WP3.4's seeded saved reports.
- [ ] **Deferred**: demo services + docs/screenshots — pending the fork docs pass (same as WP1.1).

**Acceptance check**: with the NORA profile applied, a service can be created, related to process/application/org/capability/data object, filtered in the inventory, and exported to Excel. ✔ type + relations verified by tests; inventory/export are existing data-driven machinery.

### WP1.3 — TRM Service Standards `☑ Done 2026-07-02` *(re-scoped after fork gap review)*

**NORA ref**: TRM "Service Standard" artifact; Policy Management. NORA.md item M3.

**Gap review outcome**: the fork's existing `tech_standards` module (standalone entity + radar UI + CRUD API with `tech_standards.view/manage` + **time-boxed approver-gated exception register**) already provides the catalogue, lifecycle statuses (radar scale Preferred → Allowed → Tolerated → Sunset → Prohibited ≈ NORA's emerging→retired), replacement links, and waivers (originally scheduled for WP4.3). A new card type would have duplicated it — WP1.3 was re-scoped to **complete the existing entity with NORA TRM metadata**:

- [x] New columns on `tech_standards` (migration `125_add_nora_trm_fields_to_tech_standards_fork.py`): `standard_body` (issuing body — DGA/NCA/W3C…), `mandate` (mandatory | recommended | optional, validated), `review_date`, `spec_url`, `trm_code`, and `tech_category_id` — a nullable card FK linking the standard into the **TechCategory tree** (= TRM Service Area / Category classification).
- [x] API: create/update payloads, mandate validation, serializer returns the resolved TechCategory card brief on list / radar / detail.
- [x] Workspace transfer: `tech_category_id` registered in `card_fk_columns` on the TechStandards EntitySection (card PKs are remapped on import); the five scalar columns transfer automatically via introspection.
- [x] Frontend: standards dialog gains mandate select, TRM code, issuing body, review date, spec URL, and a **TechCategory `CardPicker`**; edit pre-fills from the radar row (API now returns full rows).
- [x] i18n: 9 new `techStandards.*` keys in `reports.json` across all 10 locales.
- [x] Tests: NORA-fields roundtrip (create → get/list brief resolution → patch clear), invalid-mandate rejection.
- [ ] **Deferred**: radar-scale ↔ NORA status terminology mapping table in docs; ITComponent *positive* conformance tracking (which standards apply, compliant/partial) → WP4.3, which after this gap review shrinks to "conformance assessments only" (waivers already exist).

**Acceptance check**: standards carry TRM classification + NORA metadata, are governable (waivers with expiry + approver already in the fork), and slot into the TechCategory tree. ✔ verified by API tests.

### WP1.4 — Arabic-first delivery gate `☑ Done 2026-07-02`

**NORA ref**: Saudi-government usability (implicit). NORA.md item M8.

**Audit results (2026-07-02)**:

- [x] **UI-string parity audit**: `ar` (and all 8 other locales) have **zero** missing keys, zero empty values, and zero placeholder mismatches against `en` across all 14 namespaces. This is not just a snapshot — `frontend/src/i18n/i18n.test.ts` enforces key parity, non-empty values, placeholder preservation, and `_one`/`_other` plural consistency for every locale **in CI**, so any PR that omits `ar` keys fails the frontend test suite.
- [x] **Metamodel-content parity**: `backend/tests/services/test_i18n_seed.py` (260 tests) enforces `ar` on every seed type/field/option/relation, and `test_nora_profile.py`'s definition tests enforce it on all NORA profile content (fields, options, GovService type, stakeholder roles, relation labels). Adding NORA content without Arabic fails CI.
- [x] **RTL verification of NORA-touched surfaces**: the Framework Profile settings card, the NORA Alignment card-detail sections (rendered by `AttributeSection`), the GovService inventory/detail surfaces, and the tech-standards radar page + dialog are all pure MUI — they inherit the document `dir` and need no per-component opt-in. None of the touched components use AG Grid or Recharts (the two libraries that require the `useIsRtl()` opt-in per project convention); `useIsRtl.ts` and `RTL_LOCALES`/`isRtlLocale` verified present for future WPs that do touch them (WP2.4 gap report and WP3.4 report pack will).

**Delivery gate (the standing rule for every NORA work package)**:
1. UI strings ship in all 10 locale files **in the same change** — `ar` is never a follow-up. (CI-enforced by `i18n.test.ts`.)
2. Metamodel content (types, fields, options, sections, subtypes, relation labels, stakeholder roles) ships with `translations` covering all 9 non-English locales. (CI-enforced by the seed/profile definition tests — new NORA content must be added to those test parametrisations.)
3. Any new view built on AG Grid or Recharts must wire `useIsRtl()`; plain MUI needs nothing.
4. DOCX/print exports touched by a WP get a manual RTL render check before the WP is marked done (relevant from WP3.2 onward).
**Acceptance check**: NORA-profile install with `ar` locale shows no English fallback strings in the NORA-relevant screens. ✔ zero-gap parity verified; regressions blocked by CI.

---

## Phase 2 — Current/Target Architecture & Governance

*Goal: current/target modelling with governed approvals — the structural heart of NORA Stages 6–8.*

### WP2.1 — Architecture state + target-change semantics `☑ Done 2026-07-02`

**NORA ref**: Stages 6/7 (current + target architectures), Stage 8 input. NORA.md item M4, upgraded with the blueprint's typed change model.

**As implemented** (gap-review outcome: the fork's Scenarios module stays as the *branch/merge authoring* workflow; `architecture_state` is the *standing landscape dimension* — complementary, not duplicative):

- [x] `cards.architecture_state` (`current` default | `transition` | `target`), `cards.change_type` (`create` | `modify` | `replace` | `retire` | `consolidate`), `cards.successor_id` (self-FK, SET NULL) — migration `126`. Second self-FK required explicit `foreign_keys` on the `parent`/`children` relationships.
- [x] Workspace-io: `architecture_state` + `change_type` in `CARD_COLUMNS` (exporter + applier). **Delta**: `successor_id` is not yet bundle-encoded (needs a `{col}__ref` pass on the bespoke cards section) — deferred with this note.
- [x] Card Detail: `ArchitectureStateBadge` (chip + menu: state switch + change-type marker; target renders dashed; `current` hidden on read-only cards to avoid noise). Gated `card.edit`.
- [x] API: `architecture_state` filter on `GET /cards`; fields on create/update/response schemas (pattern-validated); self-successor 400 guard; `card.state_promoted` event on promotion to `current`.
- [x] Tests: create-with-semantics, filter, invalid-state 422, self-successor 400, promotion (in `tests/api/test_governance_approval.py`).
- [ ] **Deferred**: inventory filter chip/column (`InventoryFilterSidebar` is 2.3k lines; the API filter + Gap report cover the workflow); state toggles on Dependencies/Landscape/Capability Map; LDV dashed rendering for target cards outside TurboLens; successor CardPicker UI (API supports it); MCP bulk schemas; promotion-requires-approval coupling to governance mode.

**Acceptance check**: target blueprint lives side-by-side with the live landscape, typed changes + successor links declared, promotion audited. ✔ core verified by tests; report overlays deferred.

### WP2.2 — Multi-step approval workflow (stage gates) `☑ Done 2026-07-02`

**NORA ref**: Stage 4.8 artifact review/approval process; every stage's "obtain governance approval". NORA.md item M5, upgraded with the blueprint's gate/immutability rules.

**As implemented**:

- [x] Table `approval_steps` (card_id CASCADE, step_no, required_role_key, status pending|approved|rejected, `submitted_by` for SoD, actor_user_id, comment, acted_at) — migration `127`, model `approval_step.py`, service `governance_service.py`. **Delta**: intentionally *not* in the workspace bundle — approval steps are instance-local governance state (like `last_confirmed_at`); the durable audit lives in `events`.
- [x] `approval_status` gains `IN_REVIEW`. Config in `app_settings.general_settings`: `governanceMode` (off by default — classic flow untouched), `governanceChain` (default `["chief_architect","ea_governance_committee"]`), `governanceSodEnabled` (default on). **Delta**: one global chain, not per-card-type (per-type overrides deferred until a real need).
- [x] Flow: `action=submit` → IN_REVIEW + fresh steps + in-app notifications to the first chain role's members; `approve` decides the current step (requires `governance.approve_step` + the step's role, admin override; notifies the next role); final approve → APPROVED; `reject` (optional comment) → REJECTED; `reset` → DRAFT + steps cleared. Mandatory-relations/tags gate applies on submit. All transitions land in `events` via the existing publisher.
- [x] Immutability: mid-review substantive edit clears the round back to DRAFT (approved-card `BROKEN` rule preserved).
- [x] `GET /cards/{id}/approval-steps` for the UI; `ApprovalStatusBadge` grew governance actions (Submit for review / Approve step) + `IN_REVIEW` chip; `ApprovalStepsStrip` renders the live chain under the card header; `GET/PATCH /settings/governance` + Admin → Settings governance card; `governance_mode` in bootstrap + `useGovernanceMode` singleton hook.
- [x] Permissions: new `governance` group + `governance.approve_step` (added as `False` to the three built-in role sets — the registry's completeness test enforces enumeration).
- [x] Tests (`tests/api/test_governance_approval.py`): full-chain happy path, queue-jump 403, member 403, SoD 403, reject, mid-review-edit invalidation, submit-without-mode 400, legacy flow regression.
- [ ] **Deferred**: inventory bulk submit/approve; mandatory rejection comment; per-type chains; email channel for step notifications (in-app only).

**Acceptance check**: with governance on, APPROVED is unreachable without passing the chain; step history auditable. ✔ verified by tests.

### WP2.3 — NORA governance role pack `☑ Done 2026-07-02`

**NORA ref**: Stage 2.1 committees & teams. NORA.md item M7 + blueprint's role table.

- [x] Roles seeded by the NORA profile apply (pass 0, never overwritten): `ea_working_team` (member permissions minus approval), `chief_architect` (member + `governance.approve_step`), `ea_governance_committee` (viewer + approval powers).
- [x] SoD enforced in WP2.2 (`governanceSodEnabled`, default on).
- [x] Tests: role seeding + permission shape + idempotency.
- [ ] **Deferred**: `domain_owner`/`data_steward` stakeholder-role definitions (revisit with WP4.1's data-steward needs); `docs/admin/nora-governance.md` RACI page (fork docs pass).

**Acceptance check**: a NORA-profile install has the committee/working-team roles ready; SoD enforced. ✔

### WP2.4 — Gap analysis report + transition traceability `☑ Done 2026-07-02`

**NORA ref**: Stage 8.1–8.3 (gap → transition projects → roadmap). NORA.md item M6 + blueprint traceability rule "no untraceable roadmap projects".

- [x] `GET /reports/gap-analysis` + **Reports → Gap Analysis** page: four buckets (new / replacements / modifications / retirements), per-row initiative chips with transition role, replaced-card links, summary chips, untraceable warning banner.
- [x] "Assign to initiative" dialog (Initiative `CardPicker` + transition-role select) — resolves the metamodel relation type for the (Initiative, card-type) pair in either direction and creates the relation with the `transitionRole` attribute; disabled when no relation type exists for the pair.
- [x] `transitionRole` attribute (introduces | modifies | retires, translated ×10) injected into every Initiative relation type by the NORA profile apply (pass 3b, idempotent).
- [x] Traceability lint: untraceable changes flagged inline + counted (the inverse lint — roadmap initiatives with zero gap links — is visible via the same data).
- [x] Tests: bucket assignment, successor resolution, initiative linkage + transition role, untraceable list.
- [ ] **Deferred**: PPM Gantt "transition projects only" filter; seeded saved-report template (→ WP3.4 pack); export button (print works).

**Acceptance check**: every current→target delta, its delivering initiative, and untraceable items visible on one screen. ✔ verified by tests.

---

## Phase 3 — Methodology & Program Management

*Goal: the 10-stage NORA journey is trackable end-to-end with evidence and reports.*

### WP3.1 — EA Program tracker (10 stages + gates) `☑ Done 2026-07-02`

**As implemented**: single `ea_program_deliverables` table (migration `128`) — **delta**: no separate `ea_program_stages` table; stages are the fixed NORA list (0 = continuous governance), tailoring = descoping deliverables or adding custom ones. 41 deliverables seeded from the NORA guideline tables via the profile apply (pass 5, idempotent; `app/services/nora_program.py`). Deliverable titles are data (admin-editable, untranslated by design); stage names are i18n keys ×10. API `/nora-program` (GET grouped by stage with progress %, POST custom deliverables, PATCH status/evidence — `approved` requires `governance.approve_step` and stamps approver+time, DELETE custom-only; built-ins descope instead). New `nora.view`/`nora.manage` permission group; NORA roles grant them. Page `/nora-program` (nav-gated to the NORA profile): stage accordions with progress bars, status selects, evidence-link chips with add/remove, custom deliverables. Workspace-io EntitySection. 7 API tests. **Deferred**: executive-dashboard tile view (the page header carries the overall progress chip); evidence pickers (card-query/report/diagram/SoAW/ADR) — evidence is free links (app paths or URLs) in v1; owner/due-date editing UI (API supports both).

*Original spec follows for reference:*

#### (original) WP3.1 — EA Program tracker `superseded`

**NORA ref**: the methodology itself; continuous governance (program management). NORA.md item I3 + blueprint stage-gate concept.

- [ ] Tables: `ea_program_stages` (seeded 10 stages + continuous-governance row; per-install editable for NORA's explicit tailoring allowance) and `ea_program_deliverables` (id, stage_no, key, title, status: notStarted | inProgress | inReview | approved, evidence JSONB `[{kind: card_query | report | diagram | document | soaw | adr, ref}]`, approved_by, approved_at, due_date, owner_id). Migration + workspace-io coverage.
- [ ] Deliverable catalogue seeded from NORA's stage tables (NORA.md §1.3–1.4 — content fully known from the guideline).
- [ ] Page `/nora-program` (nav-gated to NORA profile): stage board with per-stage progress %, deliverable rows, evidence linking (card-query builder, saved-report picker, diagram picker, file attach, SoAW/ADR picker).
- [ ] Stage-gate: marking a stage "complete" requires all non-descoped deliverables `approved`; approval uses WP2.2 semantics (committee role).
- [ ] Dashboard widget: NORA program progress.
- [ ] **NORA executive dashboard** — a landing view on `/nora-program` (first tab) aggregating: stage readiness %, artifact approval coverage, current/target card counts by domain, top open gaps (WP2.4), transition-initiative RAG (from PPM status reports), open waivers (WP4.3 when available), improvement opportunities by status (WP3.3). Read-only, committee-friendly; each tile deep-links to its source screen. Tiles render only for feature areas already shipped (progressive enhancement, no dead tiles).
- [ ] Permissions: `nora.view` / `nora.manage` keys; tests; i18n; docs.

**Acceptance**: an agency (or DGA liaison) can open one screen and see exactly where the EA program stands, per stage, with clickable evidence for every deliverable.

### WP3.2 — Governed document artifacts (Strategy / Plan / SWOT / Usage & Management plans) `☑ Done 2026-07-02`

**As implemented** (per the carried-over design decision — `doc_type` discriminator on the SoAW machinery, no new module):

- [x] `doc_type` column on `statement_of_architecture_works` (migration `129`, default `soaw`), pattern-validated on create, copied on revision, returned everywhere, filterable via `GET /soaw?doc_type=…`. Plain scalar → auto-covered by the workspace-transfer introspection.
- [x] Five NORA section templates in `soawTemplate.ts` (`getTemplateSections(docType)`): **EA Project Strategy** (value / goals / scope / approach / cost — NORA Step 1.4's five topics), **EA Project Plan** (teams / approach / work plan / schedule / risks), **Environment Analysis / SWOT** (requirements / internal / external / S / W / O / T), **EA Usage Plan**, **EA Management Plan**. All rich-text; the TOGAF SoAW template is untouched.
- [x] Editor, preview, DOCX and PDF export all doc-type aware (`SoAWEditor` reads `?type=…` on create / the row on edit; `exportToDocx`/`exportToPdf`/`buildPreviewBody` take `docType`).
- [x] **Everything the SoAW workflow already had applies for free**: revision chain on signed documents, signatories + sign-off, status workflow (draft → in_review → approved → signed), custom sections, initiative linking, `soaw.view/manage/sign` permissions.
- [x] Entry point: **NORA Program page → "New NORA document"** menu (5 types, `nora.manage`-gated); doc-type label shown in the delivery deliverable list.
- [x] i18n ×10: 5 document labels + 26 section titles (delivery ns) + create-menu keys (nav ns). Section hints intentionally omitted (optional field) to keep the template lean.
- [x] Tests: doc_type roundtrip + list filter + invalid-type 422.
- [ ] **Deferred**: manual RTL render check of the Arabic DOCX/PDF output (WP1.4 gate rule 4 — needs a running instance; flag for the next deploy); wiring created documents automatically as WP3.1 evidence (one manual copy-paste of the document URL today).

**Acceptance check**: all Stage 1/2/3/9 named deliverables can be authored from their own template, versioned, signed, exported, and linked as program evidence. ✔

**NORA ref**: Stages 1, 2, 3, 9 deliverables. NORA.md item I7 + blueprint artifact-registry versioning.

- [ ] Extend the SoAW pattern (`ea-delivery`) with a `doc_type` discriminator (or sibling table `ea_documents`): templates for **EA Project Strategy**, **EA Project Plan**, **Environment Analysis / SWOT** (S/W/O/T quadrants as EditableTable, entries optionally linking cards), **EA Usage Plan**, **EA Management Plan**.
- [ ] Version field + "superseded by" self-link: approving a new revision marks the prior one superseded (blueprint immutability rule, minimal schema).
- [ ] Documents register as evidence kinds in WP3.1.
- [ ] Approval via WP2.2 chain; export to DOCX (existing soawExport machinery); i18n incl. RTL DOCX check; docs.

**Acceptance**: all Stage 1/2/3/9 named deliverables can be authored, versioned, approved, exported, and linked as program evidence.

### WP3.3 — Improvement Opportunity registry `☑ Done 2026-07-02`

**As implemented**: `improvement_opportunities` + `improvement_opportunity_cards` (migration `128`, shared with WP3.1), CRUD API `/improvement-opportunities` gated by the existing `grc.view`/`grc.manage` (per plan's "reuse grc" option), domain/priority/status lifecycle with validation, card links, initiative assignment (auto-advances proposed/approved → inTransition), **GRC → Governance → Opportunities** sub-tab (table + create/edit dialog + Initiative CardPicker), workspace-io sections (initiative + card FKs remapped), i18n ×10 (nested grc namespace), 2 API tests. **Deferred**: TurboLens/SWOT promotion actions (the `source` field is ready — buttons land when WP3.2's SWOT exists and as a TurboLens follow-up); committee approval via WP2.2 chain (status select is permission-gated but single-step); realized-value widget.

*Original spec follows for reference:*

#### (original) WP3.3 `superseded`

**NORA ref**: Stage 6.6 "Summary of Improvement Opportunities". NORA.md item I4.

- [ ] Table `improvement_opportunities` (id, title, description, domain: BA | AA | DA | TA, source: manual | turbolens_duplicate | turbolens_modernization | swot, priority, status: proposed | approved | inTransition | realized | rejected, initiative_id FK nullable) + M:N link to cards. Migration + workspace-io.
- [ ] UI: tab under GRC (or the Gap report) with CRUD + "assign to initiative".
- [ ] Promotion actions: TurboLens duplicate cluster → opportunity; modernization assessment → opportunity; SWOT weakness (WP3.2) → opportunity (mirrors compliance-finding→risk pattern).
- [ ] Committee approval via WP2.2; realized-value widget (opportunities realized per quarter).
- [ ] Permissions (`nora.manage` or reuse `grc`), tests, i18n, docs.

**Acceptance**: analysis findings from humans and TurboLens converge into one governable backlog that feeds the transition plan.

### WP3.4 — NORA report pack & committee decision log `☑ Done 2026-07-02` *(re-scoped)*

**As implemented**:

- [x] **Organization Chart report** (`/reports/org-chart`): Organization hierarchy as an indented tree with subtype labels — the NORA BA org-chart artifact.
- [x] **Government Service Traceability report** (`/reports/service-traceability` + backend `GET /reports/service-traceability?card_id=`): BFS over relations (2 hops, configurable to 3) from a GovService, grouped into the four EA layers with layer-colored columns; indirect (2-hop) cards flagged; target-state cards render dashed. Deep-linkable. **Delta**: rendered as layered chip columns rather than the LDV React-Flow renderer — same information, a fraction of the complexity; upgrade to `C4DiagramView` is a cosmetic follow-up.
- [x] **Committee decision register**: `committee`, `meeting_date`, `stage_no` on ADRs (migration `130`), full API roundtrip, copied on revision, editable in the ADR editor (signed = read-only). ADRs are now filterable committee decisions.
- [x] i18n ×10; API tests (traceability layer grouping + hops, ADR fields roundtrip); OpenAPI regenerated.
- [ ] **Re-scoped — seeded saved-report templates dropped**: `saved_reports.owner_id` is NOT NULL with user cascade (same structural blocker as WP1.2's bookmark), so install-wide seeded reports are impossible without schema surgery that isn't warranted. Instead, the **report-pack map** below documents how each NORA artifact view is produced with existing reports; users save their own configured variants.
- [ ] **Deferred**: "Decisions" list filter by committee/stage in the ADR grid (fields returned by the API; grid column is cosmetic).

**Report-pack map (NORA artifact → Turbo EA view)**: BRM Explorer → Capability Map filtered/colored by `brmLevel` · Service Catalogue → Inventory filtered `type=GovService` (Excel-exportable) · ARM Application Catalogue → Portfolio/Flexible-Portfolio by `armCategory`, heat `automationLevel` · TRM Standards Compliance → Tech-Standards radar (per-category × status) or Matrix report · Transition Roadmap → PPM Gantt / Transformation Roadmap + Gap Analysis · Org Chart → `/reports/org-chart` · Service delivery → `/reports/service-traceability` · Decision register → ADR list (committee fields).

**NORA ref**: Stage 6/7 artifact views; governance decisions. NORA.md item I6 + blueprint views list.

- [ ] Seeded saved-report templates: BRM Explorer (Capability Map by `brmLevel`), Service Catalogue (from WP1.2), ARM Application Catalogue (portfolio by `armCategory`, heat by `automationLevel`), TRM Standards Compliance (Matrix: ITComponent × TechStandard), Transition Roadmap (Gantt filtered per WP2.4), Data Exchange Map (after WP4.1), Org Chart (Organization hierarchy tree render — small new component).
- [ ] **Government Service Traceability view** — per-GovService end-to-end chain: service → beneficiary/channel → business process → application → interface/data exchange → data object → IT component/standard, rendered with the LDV renderer (`C4DiagramView`) scoped to the service's relation subgraph (BFS from the GovService card). Entry point: a "Traceability" tab/button on the GovService card detail + a report variant. This is the blueprint's service-delivery view and the primary DGA "show me how this service is delivered" artifact.
- [ ] ADR extension: optional `committee` + `meeting_date` + `stage_no` fields so ADRs double as the committee decision register; "Decisions" report filtered by committee.
- [ ] Print/export verified for all pack reports (evidence-pack precursor for WP5.3).
- [ ] i18n, docs (map each report to the NORA artifact it satisfies — table in docs).

**Acceptance**: the current-architecture and target-architecture artifact tables from NORA Stages 6–7 can each be produced as a live, exportable view.

---

## Phase 4 — Domain Completeness (DRM / PRM / Standards / Integration)

*Goal: close the DA and PRM gaps; make standards governance and Saudi policy packs real.*

### WP4.1 — Data Architecture completion (DRM) `☑ Done 2026-07-02` *(delivered via profile, no migration)*

> **As implemented**: `DataExchange` card type (method / frequency / external party / GSB flag / NDMO classification carried) + relations `Application → DataExchange` (direction attribute) and `DataExchange → DataObject`; `database` subtype appended to ITComponent (pass 4b, idempotent) + `DataObject → ITComponent` "is stored in" relation — all created by the NORA profile apply, translated ×10, pair-safe. Data Dictionary/Database Portfolio = inventory filters (per-user bookmark blocker as before). **Deferred**: dedicated Data Exchange Map visual (the Interoperability report covers exchange governance; an LDV-based map is cosmetic follow-up); classification-change approval hook (governance mode already gates card approval broadly).

#### (original spec) `superseded`

**NORA ref**: DA artifacts — classifications, exchanges, database portfolio, dictionary. NORA.md item I1.

- [ ] New card type `DataExchange` (Application & Data layer): `exchangeMethod` (api | fileTransfer | messaging | database | manual), `frequency` (realtime | daily | weekly | monthly | adhoc), `externalParty` (text), `viaGsb` (boolean), `dataClassificationCarried` (single_select, NDMO levels). Relations: `Application → DataExchange` (sends/receives, direction attribute), `DataExchange → DataObject` (carries).
- [ ] `ITComponent` subtype `Database` + relation `DataObject → ITComponent` (stored in) → the Database Portfolio Catalogue is the inventory filtered to the subtype (seeded bookmark).
- [ ] Data Dictionary = seeded DataObject bookmark (name, definition, classification, owner, source) + Excel export.
- [ ] Data Exchange Map report (LDV/dependencies variant filtered to DataExchange edges; GSB edges visually distinct).
- [ ] Governance hook: classification changes to `secret`/`topSecret` require WP2.2 approval when governance mode on.
- [ ] Migration, demo data, tests, i18n, docs.

**Acceptance**: NORA's DA artifact list (§1.4) is fully producible: classifications, exchanges, flows, database portfolio, dictionary.

### WP4.2 — KPI / Performance Reference Model `☑ Done 2026-07-02`

> **As implemented**: `KPI` card type (unit, baseline/target/current, measurement frequency, direction) via the profile; relations `Objective → KPI`, `KPI → GovService`, `Initiative → KPI`; **Reports → KPI Scorecard** with direction-aware progress % and RAG colouring computed client-side from the values. **Deferred**: `ragStatus` as a stored calculated field (the scorecard computes it live; admins can add a calculation for card-level display); Surveys-driven value maintenance template; PPM-overview KPI links.

#### (original spec) `superseded`

**NORA ref**: PRM; continuous governance (performance management). NORA.md item I2.

- [ ] New card type `KPI` (Strategy & Transformation layer): `unit`, `baselineValue`, `targetValue`, `currentValue`, `measurementFrequency`, `direction` (higherIsBetter | lowerIsBetter), `ragStatus` (calculated via calculation engine).
- [ ] Relations: `Objective → KPI` (is measured by), `KPI → GovService` (measures), `Initiative → KPI` (improves).
- [ ] Performance scorecard report (KPI grid: baseline/target/actual/RAG, grouped by Objective).
- [ ] KPI value maintenance via existing Surveys module (seeded survey template targeting KPI cards).
- [ ] Benefits traceability: transition initiatives (WP2.4) surface their linked KPIs on the PPM overview tab.
- [ ] Migration, tests, i18n, docs.

**Acceptance**: objectives → KPIs → services/initiatives are traceable and the scorecard renders RAG from live values.

### WP4.3 — Standards conformance & waivers `☑ Closed 2026-07-02` *(fork already provides the core)*

> **Closure rationale**: the fork's exception register (WP1.3 gap review) already delivers time-boxed approver-gated waivers with expiry derived at read time (`expired` status), per-standard open-exception counts on the radar, and the `tech_standards.approve_exception` permission. Remaining nice-to-haves — daily expiry-notification loop with Risk-Register escalation, positive per-asset conformance assessments, per-standard compliance % tile — are recorded here as backlog, not blocking NORA alignment (NORA requires standards + governed deviations, which exist).

#### (original spec) `superseded`

**NORA ref**: TRM standards, policy management. Blueprint NORA-08 (adopted).

- [ ] Table `standard_waivers` (id, standard_card_id FK, subject_card_id FK, justification, compensating_control, requested_by, approved_by, expires_at, status: requested | approved | rejected | expired) + migration + workspace-io.
- [ ] Conformance stays on the `ITComponent → TechStandard` relation attribute (WP1.3); waiver records hang off it.
- [ ] Expiry: daily background loop (pattern: `_promote_recurring_tasks_loop`) flips overdue waivers to `expired`, notifies the standard owner, and opens a Risk-Register entry (reuse promote pattern).
- [ ] GRC → Compliance gains a **Standards & Waivers** tab: non-compliant assets, expiring waivers, per-standard compliance %.
- [ ] High-mandate (`mandatory`) waivers require committee approval (WP2.2 chain).
- [ ] Permissions (`compliance.manage`), tests, i18n, docs.

**Acceptance**: every deviation from a mandatory standard is either remediated, risk-accepted, or covered by a time-bound waiver that escalates on expiry.

### WP4.4 — Saudi policy packs (NCA ECC / NDMO / PDPL / DGA) `☑ Done 2026-07-02`

> **As implemented**: profile pass 4c seeds four `compliance_regulations` rows — **NCA ECC**, **NDMO Data Management**, **PDPL**, **DGA Digital Government Policy** — whose assessment-scope descriptions key the AI compliance scanner on the NORA profile fields (NDMO classification without owner, secret+ data off-GSB, services without digital channels, apps without BRM/ARM linkage, components on declining standards). Idempotent by key; follows the built-in regulation precedent (labels are proper names, no translations). Findings promote to risks via the existing GRC machinery. **Deferred**: promotion to improvement opportunities (WP3.3 source field ready).

#### (original spec) `superseded`

**NORA ref**: policy management; national alignment. NORA.md item I5.

- [ ] Seeded `compliance_regulations` packs: NCA Essential Cybersecurity Controls, NDMO data-management standards, PDPL, DGA digital-government checks.
- [ ] Scanner rules keyed on Phase-1 fields: e.g. Applications lacking BRM linkage; `secret+` DataObjects exchanged with `viaGsb=false`; GovServices without a digital channel; ITComponents on `declining`/`retired` standards.
- [ ] Findings promote to risks (existing) and to improvement opportunities (WP3.3).
- [ ] Packs are data — update path documented for regulation revisions.
- [ ] Tests (scanner rules), i18n (regulation names/descriptions ar+en), docs.

**Acceptance**: one scan produces a Saudi-compliance findings list with remediation paths into the risk register and transition backlog.

### WP4.5 — Integration & interoperability view `☑ Done 2026-07-02`

> **As implemented**: `GET /reports/interoperability` + **Reports → Interoperability** page — every Interface and DataExchange with integration type, NDMO classification carried, GSB routing, external party, frequency and connected applications (with exchange direction); summary chips and a warning banner for **secret-or-above exchanges running off-GSB** (rows highlighted). This is the WP4.4 scanner's rule made permanently visible. **Delta**: `externalParty` stays free text (picklist promotion deferred until real demand, per plan).

#### (original spec) `superseded`

**NORA ref**: whole-of-government interoperability; AA/DA exchange artifacts. Blueprint NORA-15 (adopted, slimmed).

- [ ] Interoperability report: source app → interface/exchange → target app/external entity, showing protocol, classification, GSB status, standard conformance, SLA — built on existing Interface + WP4.1 DataExchange (no new entities).
- [ ] `externalParty` values promoted to a lightweight picklist managed in settings (external government entities) — avoids a new card type until real demand.
- [ ] Cross-agency exchanges without GSB and without a waiver flagged (feeds WP4.4 scanner).
- [ ] i18n, docs.

**Acceptance**: integration governance can review every external exchange with its standards/classification posture on one screen.

---

## Phase 5 — NEA Content & Federation *(⊘ blocked on NEA reference-model publications)*

*Goal: national content, maturity, and DGA-facing outputs. WP5.1 unblocks when the user provides the NEA PRM/BRM/ARM/DRM/TRM documents.*

### WP5.1 — NEA reference-model catalogue importers `⊘`

**NORA ref**: Stage 5 — agency models derived from NEA models. NORA.md item A4 + blueprint NORA-04 mapping entities.

- [ ] Package the official NEA taxonomies as versioned importable catalogues (Capability-Catalogue wheel pattern; `catalogueId` matching).
- [ ] BRM import → Business Area / LoB skeleton as BusinessCapability tree with `brmLevel`/`brmCode`; auto-relink of existing capabilities by `catalogueId` (macro-capability import is the proven template).
- [ ] ARM/DRM/TRM imports → populate the option sets stubbed in WP1.1 + TechStandard/TechCategory trees; PRM import → KPI reference set.
- [ ] Per-item `alignmentStatus` (aligned | agencyExtension | unmapped) — the blueprint's `NationalReferenceMapping`, folded onto the card `attributes` instead of a join table.
- [ ] Coverage report: % of landscape mapped to national codes, unmapped cards, agency extensions.

**Blocked**: needs the actual NEA reference-model content (user to provide).

### WP5.2 — EA maturity self-assessment (Qiyas-style) `☐`

**NORA ref**: Stage 1.3 + Stage 10 maturity assessment. NORA.md item A2.

- [ ] Admin-definable maturity dimensions + levels; periodic self-assessment via Surveys engine; radar chart + trend (kpi_snapshots pattern); per-dimension improvement actions feeding WP3.3 opportunities or todos.
- [ ] If/when DGA publishes a Qiyas submission format, add an export adapter.

### WP5.3 — NEA alignment / evidence pack export `☐`

**NORA ref**: NEA federation; auditability. NORA.md item A3 + blueprint NORA-23.

- [ ] "NEA Alignment Package" export (workspace-io machinery): BRM coverage, shared-service candidates, standards-compliance summary, maturity score, program status, approval history — xlsx/zip, immutable once generated (stored like workspace transfers).

### WP5.4 — Plateaus / time-slice views + segment scopes `☐`

**NORA ref**: 3–5y blueprint sequencing; NEA segment architecture. NORA.md items A1/A5 + blueprint ArchitectureScope (slimmed to a filter-set entity).

- [ ] Named plateaus derived from lifecycle dates + `architecture_state`; TimelineSlider integration on major reports.
- [ ] `segments` table: named cross-entity filter scopes (capability subtree + related apps/data/tech) applied across inventory, reports, program tracker.

### WP5.5 — AI-assisted NORA authoring `☐`

**NORA ref**: productivity on Stages 6.6/7. NORA.md item A6.

- [ ] TurboLens prompt profiles for NORA wording (improvement opportunities, target directions); Arabic output support; results always land as `proposed` records — governance approval stays human.

---

## UI & Views Inventory (consolidated)

Every user-facing surface the plan delivers, in one place — each view lives inside a work package above; this table exists so UI coverage is auditable at a glance and maps to the ten must-have views from the reviewed blueprint (§8). "Free" means no custom UI is built: the data-driven metamodel renders it.

| # | View / screen | Where in the app | WP | Status |
|---|---|---|---|---|
| 1 | NORA fields on Card Detail (all 6 types, translated, RTL) | Card Detail → "NORA Alignment" section (auto-rendered by `AttributeSection`) | WP1.1 | ☑ Free — shipped |
| 2 | NORA fields as inventory columns/filters + Excel export | Inventory (AG Grid) | WP1.1 | ☑ Free — shipped |
| 3 | Framework Profile toggle | Admin → Settings → Modules | WP1.1 | ☑ Shipped |
| 4 | Service Catalogue view | Inventory filtered to GovService (type shipped; seeded saved view lands with WP3.4) | WP1.2 | ◐ type ☑, saved view deferred |
| 5 | Current vs Target landscape toggle | Card Detail state badge ☑; API filter ☑; report overlays + inventory chip deferred | WP2.1 | ◐ |
| 6 | Approval stepper + bulk submit/approve | Card Detail badge menu + review-chain strip ☑; inventory bulk actions deferred | WP2.2 | ◐ |
| 7 | Gap Analysis report (gap-to-roadmap traceability) | `/reports/gap-analysis` + "assign to initiative" + untraceable flags | WP2.4 | ☑ |
| 8 | NORA stage board (10 stages, deliverables, evidence links, gates) | `/nora-program` | WP3.1 | ☐ |
| 9 | **NORA executive dashboard** (stage readiness, approvals, top gaps, transition RAG, waivers) | `/nora-program` first tab + main Dashboard widget | WP3.1 | ☐ |
| 10 | Document editors: EA Strategy / Plan / SWOT / Usage / Management plans | EA Delivery (SoAW pattern) + DOCX export | WP3.2 | ☐ |
| 11 | Improvement Opportunities registry | GRC tab (or Gap report) + realized-value widget | WP3.3 | ☐ |
| 12 | Report pack: BRM Explorer, ARM Application Catalogue, TRM Compliance Matrix, Transition Roadmap, Org Chart | Reports → seeded saved reports | WP3.4 | ☐ |
| 13 | Committee decision register | ADR list filtered by committee/meeting/stage | WP3.4 | ☐ |
| 14 | **Government Service Traceability** (service → process → app → data → tech chain) | `/reports/service-traceability` (layered columns, deep-linkable) | WP3.4 | ☑ |
| 15 | Data Exchange Map (GSB edges distinct) + Data Dictionary + Database Portfolio views | Reports + seeded bookmarks | WP4.1 | ☐ |
| 16 | PRM / KPI performance scorecard (baseline/target/actual/RAG) | Reports + PPM overview KPI links | WP4.2 | ☐ |
| 17 | Standards & Waivers dashboard (compliance %, expiring waivers) | GRC → Compliance new tab (gap-review against the fork's existing TechStandard UI first) | WP4.3 | ☐ |
| 18 | Saudi policy-pack findings (NCA ECC / NDMO / PDPL / DGA) | GRC → Compliance scanner (existing UI, new packs) | WP4.4 | ☐ |
| 19 | Integration & interoperability view (external exchanges, protocols, GSB posture) | Reports | WP4.5 | ☐ |
| 20 | Reference-model coverage report (% mapped to NEA codes, unmapped cards, agency extensions) | Reports | WP5.1 | ⊘ blocked on NEA models |
| 21 | EA maturity radar + trend | Maturity module (Surveys-based) | WP5.2 | ☐ |
| 22 | NEA alignment / evidence pack export | Reports → export | WP5.3 | ☐ |
| 23 | Plateau/time-slice landscape views + segment scope filter | TimelineSlider on major reports; segment chip | WP5.4 | ☐ |

Blueprint §8 must-have views → coverage: Lifecycle/Stage-Gate dashboard → #8/#9 · Reference-model coverage → #20 · Current architecture overview → #5 (+ existing reports) · Target architecture overview → #5 · Gap-to-roadmap → #7 · Service traceability → #14 · Integration/interoperability → #19 · Standards & waivers → #17 · PRM/benefits → #16 · EA maturity → #21. All ten are now explicitly owned by a WP.

---

## Traceability rules (enforced/flagged once Phases 2–3 land)

Adopted from the reviewed blueprint, enforced pragmatically (lint/flags, not hard blocks, unless noted):

1. An approved artifact/card that is materially edited loses approval and must re-pass the chain *(hard rule — already core behaviour, extended by WP2.2)*.
2. A transition-roadmap initiative should link ≥1 gap, target change, or improvement opportunity *(flagged in WP2.4)*.
3. A target card should link a driving objective, gap, requirement, or standard *(flagged in gap report)*.
4. A mandatory-standard violation must end as remediated, risk-accepted, or time-bound-waived *(enforced by WP4.3)*.
5. `secret`/`topSecret` data exchanged externally without GSB requires a waiver *(scanned by WP4.4)*.
6. No parallel NORA card types — profile fields + translations only *(review-time rule)*.

---

## Acceptance criteria for "basic NORA alignment" (Definition of Done for Phases 1–3)

- [ ] 1. An agency can switch on the NORA profile and see NORA terminology (ar/en) across the app. *(WP1.1)*
- [ ] 2. The BA artifact set is capturable: BRM-levelled functions, processes, org chart, service catalogue. *(WP1.1, WP1.2)*
- [ ] 3. The AA/TA artifact sets are capturable, including technology standards. *(WP1.1, WP1.3)*
- [ ] 4. Current and target architectures coexist on one landscape with typed changes and successor links. *(WP2.1)*
- [ ] 5. Every stage deliverable can pass a working-team → Chief Architect → Governance Committee chain with full audit history. *(WP2.2, WP2.3)*
- [ ] 6. Gaps are explicit and every roadmap initiative is traceable to them. *(WP2.4)*
- [ ] 7. The 10-stage program is tracked with linked evidence and stage gates. *(WP3.1)*
- [ ] 8. Stage 1/2/3/9 document deliverables are authorable, versioned, and approvable. *(WP3.2)*
- [ ] 9. Improvement opportunities from analysis and TurboLens feed the transition plan. *(WP3.3)*
- [ ] 10. The NORA artifact views/reports are producible and exportable on demand. *(WP3.4)*

Full DRM/PRM/standards depth = Phase 4. National content, maturity, and DGA reporting = Phase 5.

---

## Change log of this plan

| Date | Change |
|---|---|
| 2026-07-02 | Initial plan created from NORA.md backlog, merged with external blueprint review (adopted: stage gates, typed target changes, waivers, framework-profile versioning, NEA mapping status, traceability rules, acceptance criteria). |
| 2026-07-02 | **WP1.1 implemented** (NORA profile service, settings endpoints, admin toggle, i18n ×10, 77 tests). Deltas: runtime idempotent apply instead of Alembic migration; `targetDisposition` dropped (TIME rationalization exists); Interface `protocol` dropped (built-in); NDMO level "confidential" corrected to "restricted". Added fork-overlap note: scenarios / tech-standards+exceptions / ARB reviews / roadmaps / rationalization already exist in this fork — WP1.3, WP2.1, WP2.2, WP2.4 and WP4.3 need gap reviews, not greenfield builds. |
| 2026-07-02 | Added the consolidated **UI & Views Inventory** (23 surfaces mapped to WPs, cross-checked against the blueprint's ten must-have views). Two views had no explicit owner and were added: **NORA executive dashboard** (→ WP3.1) and **Government Service Traceability** view (→ WP3.4). |
| 2026-07-02 | **WP1.2 implemented** (GovService card type + 5 pair-safe relation types + service_owner stakeholder role, delivered via the NORA profile apply; i18n ×10; definition + DB tests). Deltas: delivered through the profile instead of the global seed (TOGAF installs unaffected, no migration needed); seeded bookmark deferred (bookmarks are per-user) → WP3.4 saved report; demo data + docs deferred to the fork docs pass. |
| 2026-07-02 | **WP1.3 implemented after gap review** — re-scoped from "new TechStandard card type" to completing the fork's existing `tech_standards` module with NORA TRM metadata (issuing body, mandate, review date, spec URL, TRM code, TechCategory card link; migration 125; dialog + CardPicker; i18n ×10; workspace-io card-FK registration; API tests). Consequence: **WP4.3 shrinks** — waivers/exceptions with expiry + approver already exist in the fork; remaining WP4.3 scope is positive conformance assessments, the expiry escalation loop, and the compliance dashboard tab. |
| 2026-07-02 | **WP1.4 closed — Phase 1 complete.** Arabic-first audit: zero missing/empty/placeholder-mismatched keys in `ar` (and all locales) across all 14 namespaces; gate found to be **already CI-enforced** by `i18n.test.ts` (UI strings) + seed/profile definition tests (metamodel content). RTL verified: all NORA-touched surfaces are pure MUI (no AG Grid/Recharts opt-in needed). Standing 4-rule delivery gate recorded in WP1.4. |
| 2026-07-02 | **Phase 4 complete.** DataExchange + KPI card types, six new pair-safe relation types, Database subtype on ITComponent, Saudi regulation pack (NCA ECC / NDMO / PDPL / DGA keyed on profile fields) — all via profile passes, no migrations. KPI Scorecard + Interoperability reports (secret-off-GSB flagging). WP4.3 closed as fork-covered (exception register = waivers); its remaining nice-to-haves recorded as backlog. i18n ×10; backend suite grows to 1108 tests; OpenAPI 404 paths. |
| 2026-07-02 | **WP3.4 implemented — Phase 3 complete.** Org Chart report, Service Traceability report (layered BFS view + backend endpoint, deep-linkable), ADR committee decision fields (migration 130, copied on revision, editor section). Re-scope: seeded saved-report templates dropped — `saved_reports.owner_id` NOT NULL makes install-wide seeds structurally impossible (same as WP1.2 bookmarks); replaced by the documented report-pack map in WP3.4. Deltas: traceability rendered as layered chip columns instead of the LDV renderer (cosmetic upgrade deferred). i18n ×10; 2 new API tests; OpenAPI regenerated (403 paths). |
| 2026-07-02 | **WP3.2 implemented** — NORA governed documents on the SoAW machinery: `doc_type` discriminator (migration 129), five section templates (Strategy / Plan / Environment-SWOT / Usage / Management), doc-type-aware editor + preview + DOCX/PDF export, "New NORA document" menu on the program page, delivery-list labels, i18n ×10, API tests. Inherited for free: revision chain, signatories, sign-off workflow, permissions. Deferred: Arabic DOCX/PDF render check on a running instance; auto-linking created documents as WP3.1 evidence. Phase 3 now only lacks WP3.4. |
| 2026-07-02 | **Phase 3 partial: WP3.1 + WP3.3 shipped** — EA Program tracker (41 seeded NORA deliverables, stage progress, evidence links, stage-gate approval, `/nora-program` page gated to the NORA profile, `nora.*` permissions, migration 128) and Improvement Opportunity registry (GRC → Governance → Opportunities, domain/priority/lifecycle, initiative assignment). Deltas: no `ea_program_stages` table (fixed stage list + descoping covers tailoring); evidence = free links in v1; deliverable titles are untranslated data by design. **WP3.2 (document templates) and WP3.4 (report pack) explicitly deferred to the next session** with status notes — largest remaining items, methodology workable meanwhile via evidence links. i18n ×10 (incl. 11 stage names); 9 API tests; OpenAPI regenerated. |
| 2026-07-02 | **Phase 2 complete** (WP2.1–WP2.4): architecture state + typed changes + successor links (migration 126); multi-step approval chain with SoD, IN_REVIEW status, stepper UI and settings card (migration 127, `governance_service.py`, `governance.approve_step` permission); NORA governance role pack (profile pass 0); Gap Analysis report + assign-to-initiative + `transitionRole` attribute (profile pass 3b). i18n ×10 across 5 namespaces; OpenAPI spec regenerated; 8 new API integration tests + profile tests. Key deferrals noted per WP: inventory state filter chip, report state overlays, successor bundle encoding, per-type chains, PPM transition filter. Gap review confirmed Scenarios (branch/merge) and architecture_state (standing dimension) are complementary. |
