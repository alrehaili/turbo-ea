# Data model and relationships

**Status: design proposal. No schema change has been made.** Every new table below requires an Alembic migration (sequential numbering in `backend/alembic/versions/`, `server_default=sa.func.now()` on timestamps per `test_alembic_timestamp_defaults.py`), a model in `backend/app/models/` registered in `models/__init__.py`, and the **workspace-transfer checklist** (CLAUDE.md: an `EntitySection` in `workspace_io/sections.py`, `card_fk_columns`, `user_fk_columns`, `id_bearing_columns` + `rewrite` for ids inside JSON).

## 1. Principles

1. **Extend, do not duplicate.** KPI definitions stay on `KPI` cards; decisions stay in ADR / ARB / rationalization; initiatives stay as Initiative cards with PPM; risks stay in the risk register.
2. **New structures only where no existing entity can hold the data**: measurement history, financial benefits, decision-action linkage, snapshot facts.
3. **Metamodel additions are data** (seed + guarded migration for existing installs, per CLAUDE.md "Built-in metamodel default changes need a migration too"), never hard-coded card types.

## 2. Existing entities reused [Confirmed]

| Entity | Table / type | Fields used | Used by |
|---|---|---|---|
| KPI card | `cards` type `KPI` (NORA profile) | `unit`, `baselineValue`, `baselineDate`, `targetValue`, `targetValueDate`, `currentValue`, `direction`, `measurementFrequency`, `indicatorLevel`, `calculationFormula`, `dataSource`, `lastMeasuredDate`; relations `relObjectiveToKPI`, `relInitiativeToKPI`, `relKPIToGovService`, `relKPIToBusinessProcess`, `relKPIToOrgUnit`, `relProjectToKPI` | All KPI definitions (FR-09) |
| Objective, Pillar, Vision, Mission | `cards` | `Objective.progress`, `objectiveType`; pillar relations | TR-01, FIN-09 |
| Initiative + PPM | `cards` type `Initiative`; `ppm_status_reports`, `ppm_wbs`, `ppm_budget_lines`, `ppm_cost_lines`, `ppm_dependencies` | `initiativeStatus`, `startDate`, `endDate`, `costBudget`, `costActual`; report health; WBS milestones | TR-02/03/04, FIN-06/07, DEC-04 |
| GovService | `cards` type `GovService` | `serviceStatus`, `automationLevel`, `serviceType` (+ digitalization, see §4.1) | SVC-01 |
| BusinessProcess + BPM | `cards`; `process_flow_versions`, `process_assessments` | `automationLevel`, `maturity`, subtype; assessment scores | SVC-02..05 |
| Capability | `cards` type `BusinessCapability` | `maturity`, `strategicImportance` | TR-06 |
| Maturity | `maturity_assessments`, `maturity_dimension_scores` | `overall_score`, `level`, `target_level`, `approved_at` | TR-05 |
| ARB | `arb_reviews` | `subject_card_id`, `status`, `decided_at`, `created_at`, `reviewer_id` | GOV-01/02/05/07, DEC-02 |
| ADR | `architecture_decisions`, `architecture_decision_cards` | `status`, `signatories`, `committee`, `meeting_date`, `alternatives_considered`, linked cards; signed time from `events` | GOV-01/05/07, benefits link |
| ADM | `adm_workspaces`, `adm_phases` | `initiative_id`, `approved_at`, `status` | GOV-02, DEC-03 |
| Approval steps | `approval_steps` | `status`, `acted_at` | GOV-07/08 |
| Tech standards | `tech_standards`, `tech_standard_exceptions` | `mandate`, exception `status`, `expiry_date` | GOV-03/04 |
| Rationalization | `rationalization_assessments`, `assessment_decisions` | `time_decision`, `successor_id`, `initiative_id`, `annual_cost`, `planned_savings`, `progress` | IMP-01/04, FIN-03, benefits link |
| Improvement opportunities | `improvement_opportunities` (+ `_cards`) | `status`, `initiative_id`, `journey_card_id` | benefits link |
| Risks | `risks`, `risk_cards`, `risk_mitigation_task_occurrences` | levels, status, owner, target date | IMP-08, GOV-06, DEC-01 |
| Todos | `todos` | `card_id`, `assigned_to`, `status`, `link`, `is_system`, due date, `external_*` | Decision actions (§3.3) |
| Tags | `tag_groups`, `tags`, `card_tags` | — | Escalation flag (D-04), ROI scope tag (D-15) |
| Documents / attachments | `documents`, `file_attachments` (card-scoped) | — | Benefit evidence on linked cards |
| Events | `events` | old/new `attributes`, `lifecycle`, `architecture_state` | Realisation dates, ADR signed time, reconstructions |
| Snapshots | `kpi_snapshots` (4 columns) | — | Superseded by `metric_snapshots` (§3.2) |
| Fiscal year | `services/fiscal_year.py`, `services/lifecycle.py` | — | All period logic |

## 3. New structures

### 3.1 KPI card ↔ builder link (metamodel field, no table)

Add a text field **`metricKey`** to the `KPI` card type's `fields_schema` (seed + guarded migration), e.g. `TR-03`. The executive service reads the KPI card whose `metricKey` matches a builder to obtain target, baseline, owner and direction. KPIs without a builder (manual or external) have no `metricKey` match and take values from `kpi_measurements`. *(Alternative: `cards.external_id`; rejected because import and ServiceNow paths own it. D-26.)*

### 3.2 `metric_snapshots` (computed KPI history)

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| metric_key | String(32) | e.g. `TR-03.on_track` |
| period_type | String(8) | `day` / `quarter` / `fy` |
| period_key | String(16) | `2026-10-22`, `FY2027-Q2`, `FY2027` |
| scope_key | String(64) | `all` or `org:<card_id>` (landscape-wide only, see the security note) |
| value | Float, nullable | null = not available |
| numerator / denominator | Float, nullable | for audit and recompute |
| status | String(16) | `ok` / `not_available` / `not_reported` / `insufficient_data` |
| confidence | String(8) | high / medium / low |
| completeness | Float | 0-100 |
| calculation_version | String(16) | builder version |
| captured_at, created_at | timestamptz | server default now() |

Unique `(metric_key, period_type, period_key, scope_key)`. Written by the existing daily loop (`_kpi_snapshot_loop`, `backend/app/main.py:357`), extended with a registry of builders. Quarter and FY rows are **frozen** at period close (NFR-02). The 4 legacy `kpi_snapshots` columns are migrated into rows (D-19).

**Security note**: snapshots are landscape-wide. They are shown only to readers for whom `read_scope.is_unrestricted(mode="module")`, the same rule as `reports.py:255`. Restricted readers see live values without trend.

### 3.2b `kpi_measurements` (manual or external KPI history)

For KPIs measured outside Turbo-EA (satisfaction, transaction volumes, SLA), entered by owners or loaded by an extension connector.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| kpi_card_id | UUID FK → cards (type KPI), cascade | definition, target and owner stay on the card |
| period_key | String(16) | `FY2027-Q2` / `2026-10` |
| value | Float, nullable | null + status = not reported |
| status | String(16) | `reported` / `not_reported` / `estimated` |
| confidence | String(8) | |
| source | String(64) | `manual` / `survey:<id>` / `ext:<key>` |
| evidence_url | Text, nullable | |
| entered_by | UUID FK → users | |
| verified_by / verified_at | nullable | owner verification |
| created_at / updated_at | timestamptz | server default |

Unique `(kpi_card_id, period_key)`. Writing a measurement also updates `KPI.currentValue` and `lastMeasuredDate` through `card_write_service` and publishes a card event (`db=`), so the card's History tab stays truthful (CLAUDE.md `updated_at` invariant). Workspace transfer: a new `EntitySection` with `card_fk_columns=["kpi_card_id"]` and `user_fk_columns=["entered_by", "verified_by"]`.

### 3.3 Decision actions (extend `todos`, D-13)

Add two nullable columns to `todos`: `source_kind` (String(16): `adr` / `arb` / `exception` / `benefit`) and `source_id` (UUID), indexed together. A decision's actions = todos with that source. Rationale: todos already carry assignee, due date, status, notifications, system-todo behaviour, recurrence and the extension bridge. The workspace-transfer section for todos must add `source_id` to `id_bearing_columns` with a rewrite (ADR and ARB rows keep their source UUIDs on import per the transfer conventions, so the remap is identity for those; documented as such).

### 3.4 `benefits` (benefits register)

Field-level specification in `BENEFITS_AND_ROI_SPECIFICATION.md` §3. Summary:

| Group | Columns |
|---|---|
| Identity | id, reference (`B-000001`), title, description, benefit_type (`cost_saving` / `cost_avoidance` / `revenue` / `productivity` / `non_financial`), recurrence (`one_time` / `recurring`), recurring_months |
| Money | currency, baseline_amount, counterfactual_amount, forecast_amount, estimated_amount, validated_amount, realised_amount |
| Period | financial_period_start, financial_period_end (fiscal-year aligned), expected_realisation_date |
| Status | status (`forecast` / `estimated` / `validated` / `realised` / `not_realised` / `withdrawn`), validated_by / validated_at, finance_confirmed_by / finance_confirmed_at, finance_reference |
| Ownership | owner_id (user), verifier_id |
| Links | decision_kind (`adr` / `arb` / `rationalization_decision` / `improvement_opportunity`) + decision_id; initiative_id (card FK); kpi_card_id (card FK, non-financial outcome) |
| Attribution | attribution_method (enum, D-14), attribution_rationale (text), attributable_amount (nullable; set only by the approved method) |
| Audit | created_by, created_at, updated_at |

Child tables:

- **`benefit_cards`** (benefit_id, card_id): affected cards.
- **`benefit_evidence`** (id, benefit_id, kind `implementation` / `baseline` / `validation` / `finance_confirmation`, url *or* file_attachment_id *or* document_id, note, added_by, added_at).

*(Alternative: a `Benefit` card type. Rejected as the default because Finance-only state transitions and typed money arithmetic need column-level control, which card attributes do not give; listed as D-12.)*

### 3.5 Small field additions

| Field | Table | Purpose | Decision |
|---|---|---|---|
| `realized_at` | `improvement_opportunities` | Replace the `updated_at` approximation (`improvement_opportunities.py:149-194`) | — |
| `achieved_at`, `status` | `roadmap_milestones` | TR-02 when not derived from WBS | D-25 |
| `digitalizationLevel` (`digital` / `hybrid` / `manual`) | `GovService` fields_schema | SVC-01 | D-08 |
| `escalation` tag group | tags (data) | DEC-01 | D-04 |
| `initiativeReportStalenessDays` (nullable, **no default**) | `app_settings.general_settings` (no migration) | CR-01 / CR-02 staleness threshold | D-02 (approved) |
| `roiScope` tag group | tags (data) | FIN-06 | D-15 |

## 4. Relationship model for traceability

```
Pillar ─contains─▶ Objective ─is measured by─▶ KPI ◀─improves─ Initiative ─affects─▶ Application / Capability / Process
                      ▲                          ▲                 ▲
                      └──── supports ────────────┼─────────────────┘
                                                 │
ARB review ─subject─▶ Initiative/Card            │ (benefit.kpi_card_id for non-financial outcomes)
ADR ─linked cards─▶ cards ─────────────▶ Benefit ◀── TIME decision (assessment_decisions) ─▶ successor / initiative
      │                                    ▲  ▲
      └─ todos(source_kind=adr) ─ actions  │  └── Improvement opportunity ─▶ initiative
                                           └── benefit_evidence (implementation, validation, finance)
```

### 4.1 Service vs process separation (FR-15/16)

- GovService digitalization is **channel-facing** (how a beneficiary obtains the service): `digitalizationLevel` (D-08). If the profile's multi-select `deliveryChannel` (portal / mobileApp / serviceCenter / callCenter…, defined in `nora_profile.py:4688`) is adopted instead, the derivation is: digital = only digital channels; hybrid = digital + physical; manual = only physical.
- **Definition drift [Confirmed]**: `GovService` is defined in both `backend/app/services/seed.py:4840` and `nora_profile.py:4462`. The live type came from `seed.py` and lacks `deliveryChannel`. One definition must be chosen as canonical (D-08).
- Process automation is **internal**: `BusinessProcess.automationLevel` only. `GovService.automationLevel` is not used for SVC-01.

### 4.2 Organisation filter (FR-02, D-07)

The live metamodel hides `Organization` (NORA profile) but demo relations use it (`relOrgToInitiative` 15 rows, `relOrgToApp` 40), while NORA uses `OrganizationalUnit` (`relKPIToOrgUnit`, `relNora2GovServiceOrganizationalUnit`). The filter takes a configurable organisation card type (setting) and its `parent_id` hierarchy, and maps each KPI population to it through the relation types connecting the population type to the org type (keyed by relation type, never by card-type pair, per CLAUDE.md).

## 5. Data population prerequisites (Phase 0)

Demo and current data hold **0** KPI cards, 0 GovService, 0 maturity assessments, 0 roadmap milestones, 0 improvement opportunities and 0 Pillar → Objective links [Confirmed]. Owners must populate these before the corresponding KPIs leave "Not available". The existing **surveys** module can collect values.
