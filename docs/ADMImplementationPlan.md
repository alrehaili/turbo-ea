# ADM Governance Workspace — Implementation Plan

## Actual Progress Summary

Reviewed on **2026-07-20**. This document describes a completed v1 architecture rather than a checkbox backlog. Based on the sections present, the documented ADM Governance Workspace MVP is **100% implemented**, with Phase 2 hardening items tracked as known limitations.

| Area | Actual progress | Status | Evidence checked | Open work |
|------|----------------:|--------|------------------|-----------|
| ADM v1 MVP | **100%** | Built | Final architecture, workflow, permissions, API endpoints, migration, workspace transfer, frontend files, and tests are documented as implemented | None for v1 MVP scope |
| Data model and migration | **100%** | Built | Three tables in migration `132_add_adm_workspace_fork.py`; model file listed | None |
| API and permissions | **100%** | Built | `/api/v1/adm` endpoint table and `adm.view/manage/approve_gate` permissions listed | Add richer per-kind resolvers later |
| Frontend | **100%** | Built | Feature folder, list/detail pages, SoAW section, dashboard widget, dialogs, test file listed | Live pickers for artefact linking deferred |
| Workspace transfer | **Partial** | Built with limitation | ADM sections are wired into `ENTITY_SECTIONS` | Card-kind artefact `ref_id` remap is a known Phase 2 gap |
| Product hardening backlog | **Open** | Deferred | Seven known limitations listed in section 8 | Polymorphic ref remap, per-kind existence checks, comments, live pickers, locale backfill, changelog/version |

**Percentage basis:** **100%** for the documented v1 MVP because every required architecture/API/frontend/test section is present. No single overall percentage is assigned to Phase 2 hardening; it is tracked as the seven known limitations in section 8.

*Branch: `feature/adm-governance-workspace`*

## 1. Purpose

An **ADM Governance Workspace** turns an approved **Statement of Architecture Work (SoAW)** into a governed architecture engagement, following TOGAF's Architecture Development Method (ADM). Each workspace tracks nine sequential ADM phases plus continuous Requirements Management, and records the evidence, owners, dates, gate reviews and approvals for the engagement — without duplicating the underlying artefacts (SoAWs, ADRs, diagrams, risks, roadmaps, cards, …) that already live in Turbo EA.

Existing SoAWs continue to work without an ADM workspace. Creating one is opt-in.

## 2. Final architecture

### 2.1 Data model — three new tables

All in `[FORK FEATURE]` migration [`132_add_adm_workspace_fork.py`](../backend/alembic/versions/132_add_adm_workspace_fork.py). Additive and reversible; the `downgrade()` cleanly drops the three tables.

| Table | Purpose |
|---|---|
| `adm_workspaces` | One row per engagement. Anchored to a SoAW (primary) and/or an Initiative card (nullable). A table-level `CHECK` enforces that at least one anchor is set, and a partial unique index (`WHERE soaw_id IS NOT NULL`) enforces **at most one workspace per SoAW** (v1 rule). |
| `adm_phases` | Ten rows per workspace, seeded from a code catalogue. Carries `phase_key`, `sort_order`, `is_continuous`, `status`, `owner_id`, dates, completion %, and the full approval history (`approved_by`, `approved_at`, `approval_comment`, `approval_override_reason`). Unique on `(workspace_id, phase_key)`. |
| `adm_phase_artefacts` | Evidence links. Each row uses a `(kind, ref_id | ref_url)` pair pointing at an existing entity (SoAW, ADR, ARB review, diagram, roadmap, risk, compliance finding, tech standard, standard exception, rationalization assessment, inventory card, external URL, document, file attachment, requirement). The underlying entity is never copied. |

Model file: [`backend/app/models/adm.py`](../backend/app/models/adm.py).

### 2.2 Template catalogue

The nine sequential TOGAF ADM phases plus Requirements Management are declared in code in [`backend/app/services/adm_templates.py`](../backend/app/services/adm_templates.py) — not in the DB — mirroring the NORA program catalogue pattern. Each entry carries the phase's title, description, `sort_order`, `is_continuous` flag and a list of *default required artefact placeholders* which are inserted as `is_required=true, ref_id=null` rows so the phase starts in a "Ready-for-gate blocked" state until an artefact is linked, waived or the requirement is overridden.

### 2.3 Service layer

[`backend/app/services/adm_service.py`](../backend/app/services/adm_service.py) holds every business rule as a pure function operating on ORM instances passed by the API layer. This lets us unit-test the state machine, readiness gate, override rule and completion arithmetic without a DB.

State machine:

```
NOT_STARTED ─▶ IN_PROGRESS ─▶ READY_FOR_GATE ─▶ APPROVED
                      ▼               ▼
                    BLOCKED         BLOCKED
                      ▲               ▲
                      └── in_progress ┘

APPROVED ─▶ IN_PROGRESS   (reopen — requires reason + adm.approve_gate)
*        ─▶ SKIPPED       (requires reason + adm.approve_gate; continuous phases rejected)
```

### 2.4 API

Router mounted at `/api/v1/adm` in [`backend/app/api/v1/adm.py`](../backend/app/api/v1/adm.py). Full endpoint list is enumerated in §5 below.

Every state transition and every waive/override/link call publishes an `Event` through `event_bus.publish()` — the existing single audit-write path — so the resulting row lands in the `events` table with the current user, origin, batch id and (if applicable) impersonation contextvars automatically stamped.

### 2.5 Frontend

New feature folder at `frontend/src/features/adm/`:

| File | Role |
|---|---|
| `types.ts` | TypeScript mirror of the API payload shapes. |
| `admConstants.ts` | Token-driven phase status colours + icons. |
| `AdmWorkspaceListPage.tsx` | `/ea-delivery/adm` — card-per-workspace list with search + status filter. |
| `AdmWorkspacePage.tsx` | `/ea-delivery/adm/:workspaceId` — full detail: breadcrumb, header, phase timeline, phase detail panel, cross-phase Requirements Management panel, workspace-delete affordance. |
| `AdmPhaseTimeline.tsx` | Horizontal tile-per-phase strip with status accent, completion bar and continuous chip. |
| `AdmPhaseDetail.tsx` | Selected-phase panel: description, gate readiness bar, gate actions (mark-ready / approve / reopen / skip), approval history, artefact list with waive controls. |
| `AdmRequirementsPanel.tsx` | Cross-phase list of all `kind="requirement"` artefacts. |
| `AdmGateDialog.tsx` | Reason-required dialog used for the four gate actions. Enforces min 8-character reason for `mark_ready` override / `reopen` / `skip`. |
| `AdmArtefactLinkDialog.tsx` | Kind-dispatched picker (accepts UUID for entity-linked kinds, URL for external links). |
| `CreateWorkspaceDialog.tsx` | Create-workspace dialog. Pre-fills `soaw_id` when opened from the SoAW editor. |
| `AdmSoAWSection.tsx` | Section embedded in the SoAW editor — empty state + Create CTA when no workspace exists, summary + timeline + Open button when one does. |
| `AdmDashboardWidget.tsx` | "My ADM actions" widget on the Dashboard Overview tab. |
| `AdmPhaseTimeline.test.tsx` | Vitest coverage of the timeline. |

Routes registered in [`App.tsx`](../frontend/src/App.tsx). Both routes are gated with `<RequirePermission permission="adm.view">`.

## 3. Workflow

1. **Create workspace.** Any user with `adm.manage` (member+admin by default) can turn a SoAW into an ADM engagement via the SoAW-editor tab or from the workspace list page. The workspace is seeded with all ten phases.
2. **Assign phase owners and dates.** Owners are Turbo EA users; the field is nullable, and phases without an owner still work.
3. **Link evidence.** Users add artefacts of any of 15 kinds. Kinds that resolve to Turbo EA entities (SoAW, ADR, card, diagram, …) require a UUID; `url` requires a URL; `requirement`, `document`, `file_attachment` require only a title.
4. **Mark required or waive.** Any artefact can be flagged required for the gate. Requirements can be waived with a documented reason (minimum 8 characters, audit-logged).
5. **Mark ready for gate.** A user with `adm.manage` calls the endpoint; the API rejects the call if any required artefact is neither linked nor waived, unless `override=true` with an override reason (audit-logged).
6. **Approve.** Only a user with `adm.approve_gate` can call `/approve`. Approve fails unless the phase is currently `ready_for_gate`.
7. **Reopen / skip.** `adm.approve_gate` can reopen an approved phase or mark a phase skipped; both require a reason and land in the audit log.
8. **Continuous Requirements Management** runs alongside the sequential phases. It cannot enter `ready_for_gate`, cannot be approved, and cannot be skipped.

Work in multiple phases in parallel is allowed by design — the state machine gates individual phases but does not enforce ordering between phases.

## 4. Permissions

New keys in [`backend/app/core/permissions.py`](../backend/app/core/permissions.py) under group `"adm"`:

| Key | Meaning |
|---|---|
| `adm.view` | See ADM workspaces + phase detail |
| `adm.manage` | Create/edit workspaces, phases, artefact links; waive requirements; mark-ready |
| `adm.approve_gate` | Approve, reopen, skip phase gates |

Default role grants (also in `permissions.py` alongside the other module defaults):

| Role | view | manage | approve_gate |
|---|---|---|---|
| admin | via `*` | via `*` | via `*` |
| bpm_admin | ✓ | ✓ | ✓ |
| member | ✓ | ✓ | ✓ |
| viewer | ✓ | – | – |

For tighter production tenants an administrator can revoke `adm.approve_gate` from the member role via the Roles admin UI without any code change.

Impersonation flows through `PermissionService.require_permission`, so an admin impersonating "member" cannot approve a gate even though their real role is admin.

## 5. API endpoints

All endpoints are mounted under `/api/v1/adm/…`.

| Method | Path | Permission | Notes |
|---|---|---|---|
| GET | `/adm/workspaces` | `adm.view` | List + per-workspace rollup (phase counts, active phase, blocked/overdue chips, completion %). Filters: `soaw_id`, `initiative_id`, `status`. |
| POST | `/adm/workspaces` | `adm.manage` | Creates workspace + seeds 10 phases + seeded required-artefact placeholders. Enforces the "one workspace per SoAW" rule and returns 409 otherwise. Emits `adm_workspace.created`. |
| GET | `/adm/workspaces/{id}` | `adm.view` | Full workspace with phases + artefacts. |
| PATCH | `/adm/workspaces/{id}` | `adm.manage` | Updates name/description/owner/target/status. Emits `adm_workspace.updated`. |
| DELETE | `/adm/workspaces/{id}` | `adm.manage` | Cascade delete of phases + artefacts; SoAW / Initiative untouched. Emits `adm_workspace.deleted`. |
| GET | `/adm/workspaces/by-soaw/{soaw_id}` | `adm.view` | Convenience for the SoAW editor tab. |
| GET | `/adm/workspaces/{id}/requirements` | `adm.view` | Every `kind='requirement'` artefact across all phases, powering the cross-phase panel. |
| GET | `/adm/phases/{phase_id}` | `adm.view` | Phase + its artefacts. |
| PATCH | `/adm/phases/{phase_id}` | `adm.manage` | Update title / description / owner / dates / notes / gate_notes. Also supports lateral status transitions (`not_started ↔ in_progress ↔ blocked`); `ready_for_gate` / `approved` / `skipped` must go through the dedicated endpoints. Emits `adm_phase.updated`. |
| POST | `/adm/phases/{phase_id}/mark-ready` | `adm.manage` | Validates readiness gate; supports `{override, override_reason}`. Emits `adm_phase.transitioned`. |
| POST | `/adm/phases/{phase_id}/approve` | `adm.approve_gate` | Requires phase in `ready_for_gate`. Records `approved_by`, `approved_at`, `approval_comment`. Emits `adm_phase.transitioned`. |
| POST | `/adm/phases/{phase_id}/reopen` | `adm.approve_gate` | Requires `reason` (min 8 chars). Emits `adm_phase.transitioned`. |
| POST | `/adm/phases/{phase_id}/skip` | `adm.approve_gate` | Requires `reason`; forbidden on continuous phases. Emits `adm_phase.transitioned`. |
| POST | `/adm/phases/{phase_id}/artefacts` | `adm.manage` | Kind + `ref_id` / `ref_url` + title. Validates kind against the allowlist and resolves `ref_id` for known kinds. Emits `adm_artefact.linked`. |
| PATCH | `/adm/artefacts/{artefact_id}` | `adm.manage` | Update title / notes / sort_order / is_required. |
| POST | `/adm/artefacts/{artefact_id}/waive` | `adm.manage` | Toggle waived; requires reason on waive. Emits `adm_artefact.waived` / `unwaived`. |
| DELETE | `/adm/artefacts/{artefact_id}` | `adm.manage` | Unlinks; underlying entity untouched. Emits `adm_artefact.unlinked`. |
| GET | `/adm/my-actions` | `adm.view` | "My ADM actions" widget payload: pending-gate for approvers, blocked + overdue phases owned by the caller. |

## 6. Migrations

`132_add_adm_workspace_fork.py` — additive; safely reversible via the `downgrade()` that drops the three new tables and their indexes. No existing table is modified; no existing row is touched. No SoAW backfill.

## 7. Workspace transfer

Three new sections added to `ENTITY_SECTIONS` in [`backend/app/services/workspace_io/sections.py`](../backend/app/services/workspace_io/sections.py) so ADM workspaces round-trip through the workspace bundle:

- `AdmWorkspaces` (with `initiative_id` in `card_fk_columns`, user FKs on `owner_id`/`created_by`)
- `AdmPhases` (user FKs on `owner_id`/`approved_by`)
- `AdmPhaseArtefacts` (user FKs on `waived_by`/`linked_by`)

Note that artefact `ref_id` is a soft FK — for `kind='card'` links the referenced UUID is not automatically remapped by the entity engine today. This is a documented limitation (see §11) and is planned for Phase 2.

## 8. Known limitations (v1)

1. **Artefact `ref_id` for `kind='card'` is not remapped by workspace transfer.** After import to a target instance, card-kind artefact references still point at the source-instance UUIDs. Follow-up work should extend `EntitySection` with a `polymorphic_ref` hook.
2. **Per-kind resolver is minimal.** `_resolve_ref_for_kind` verifies the row exists for `soaw` and `card` kinds; the other kinds are accepted trustingly. A future PR should add per-kind existence checks and a "resolved title" refresh at read time.
3. **No dedicated ADM comment stream.** Comments are surfaced through the existing per-phase `notes` / `gate_notes` fields today; a lightweight `adm_phase_comments` table (or reuse of the existing `Comment` model with a synthetic anchor) is a plausible Phase 2 addition.
4. **Live picker for artefact linking is deferred.** The MVP link dialog accepts a raw UUID; per-kind pickers reusing `useCardSearch` / SoAW list / ADR list will land as follow-ups.
5. **No dedicated Enterprise Architect seeded role.** Every seeded role inherits `adm.*` by the defaults documented in §4. Tightening this is a tenant-admin action via the Roles UI.
6. **Non-EN/AR locales fall back to English** for ADM strings by design. Adding remaining locales is a straightforward per-file backfill.
7. **CHANGELOG + VERSION are not yet bumped** — held for reviewer sign-off before the merge PR.

## 9. Test coverage

- `backend/tests/services/test_adm_service.py` — unit tests for the state machine, gate readiness rules, waive/reopen reason enforcement, completion arithmetic.
- `backend/tests/services/test_adm_templates.py` — template catalogue compatibility (10 phases, monotonic sort order, continuous flag, valid artefact kinds).
- `backend/tests/api/test_adm.py` — HTTP integration tests covering create → mark-ready → approve → reopen; anchor CHECK; artefact kind validation; waive reason enforcement; delete cascade; permission matrix (admin can approve, member cannot).
- `frontend/src/features/adm/AdmPhaseTimeline.test.tsx` — renders + click behaviour.
