# D-41 decision package and Batch 3.4 implementation instructions

**Status 2026-10-27: superseded.** D-41 was approved **with changes** the same day; the record is `DECISION_LOG.md` §3.1 (D-41, I-42..I-49), and Batch 3.4 was built from it. Where this proposal differs — decision authors may verify when independent; no file or fingerprint is required; a system reference is evidence for any decision, including one with no linked card; GOV-05 discloses decisions without a deadline and the planning coverage beside the rate — the decision log is the record. Kept for history.

Scope: D-41 settles what D-13 (decision actions) and D-32 (implementation verified independently, approved due date, No Plan) left open — **who verifies implementation, what evidence is required, and where the implementation due date comes from**. GOV-05 (decision implementation rate) is built on the answer.

## 1. Code facts the proposal rests on (main at `481f1238`)

| Fact | Where | Consequence |
|---|---|---|
| A signed ADR is frozen; signing completes when the last signatory signs (`sign_adr`), and the transition is recorded by `governance_transitions.set_adr_status` | `api/v1/adr.py:366`, `:607-657` | A due date added **after** signing is not part of what was signed. To be "approved", it must be fixed before or at signing. |
| ADR signatories are a JSONB list on the record; `adr.sign` is the signing permission | `models/architecture_decision.py:54`; `core/permissions.py` | The approvers of an ADR are known per record. |
| ARB reviews record a decision through `reviewer_id` / `decided_at`; first approve is dated by the transition history | `models/arb_review.py`; I-14, I-17 | The ARB approval moment is reliable only from the history (Batch 3.2). |
| Todos have owner (`assigned_to`), `due_date`, `status` open/done, `link`, no source link and no evidence | `models/todo.py` | D-13's "reuse Todo" needs a source link and evidence columns. |
| Exception remediation already has fingerprinted card evidence (files by SHA-256 + size, document links by URL hash), `evidence_changed`, and an independent-verifier rule | `services/governance_transitions.py:269-500`; I-32, I-36 | The evidence mechanism exists and is approved; GOV-05 reuses it instead of inventing a new evidence table. |
| `governance_transitions` is append-only, typed from / to, no FK on `record_id`, transfers with the workspace | I-14, I-33 | Implementation lifecycle and due-date changes can live there as new instruments / event kinds. |
| Workspace transfer: Todos, ADRs, ARB reviews and transitions are entity sections; module rows keep their UUIDs | `services/workspace_io/sections.py:106, 279, 441, 449` | A todo's `source_id` pointing at an ADR / ARB needs **no** id rewrite (the target keeps the UUID); it is allowlisted with that reason. |

## 2. Proposed D-41 rules (for approval)

### D-41.1 Verifier authority and independence

- New app permission **`governance.verify_implementation`**, held by **no default role** (admins through the wildcard). Granted by admins to the EA Governance Office.
- The verifier must be **independent**. Refused with 403 `self_verification` when the verifier is:
  1. the owner (`assigned_to`) of any action of the decision, or the person who completed any action;
  2. the person who submitted the implementation for verification;
  3. the decision's author — ADR `created_by`; ARB `created_by`.
- ADR signatories and the ARB reviewer **may** verify (approving a decision is not delivering it), unless excluded by 1–3.
- The verifier either **verifies** (with an attestation) or **returns** (with a mandatory note). Both are append-only.

### D-41.2 Implementation evidence

- Every action, to be marked **done**, carries a completion note and **at least one evidence reference** (422 `evidence_required`).
- Evidence reuses the approved exception mechanism (I-32, I-36): **file attachments and documents on a card linked to the decision** (ADR: `architecture_decision_cards`; ARB: `subject_card_id`), cited as `{kind, id, name}` and fingerprinted at completion. A reference outside the decision's linked cards is refused (422 `invalid_evidence_ref`).
- At verification every cited item is re-fingerprinted; any change or removal refuses verification (409 `evidence_changed`; return, re-cite, resubmit).
- Integrity is established through files only: verification needs **at least one unchanged cited file** across the decision's actions (422 `evidence_integrity_unavailable`). Document links are accepted as supporting evidence.
- The verifier attests **what was examined** and **why it demonstrates implementation**, and confirms (422 `attestation_required`). The attestation and confirmed fingerprints are kept on the verification row.
- A decision with **no linked card** cannot cite evidence and so cannot be verified; it is reported as *unscoped decision* (`GOVERNANCE_MEASUREMENT_MODEL.md` §4), never as implemented.

### D-41.3 Implementation due date

- One **implementation due date per decision**, held on the decision:
  - **ADR**: set while the ADR is `draft` / `in_review` (by `adr.manage`) and frozen with the record when it is signed — the signatories approve it with the decision. Basis `approved_with_decision`.
  - **ARB**: set by the person recording the `approved` decision (`arb.manage`), in the same request. Basis `approved_with_decision`.
- **Changes after approval** need `adr.manage` / `arb.manage` and a mandatory reason (422 `due_date_reason_required`), append a `due_date_changed` event (previous and new date, actor, time) and never edit an earlier row — the same pattern as the approved exception expiry changes (I-35). The due date in force for a period is the approved one replaced by each change recorded **before the period's end**.
- **Decisions approved without a due date** (every decision before Batch 3.4, and any later one where none was set) are **not timed**: shown as *no due date*, never overdue, never in the GOV-05 rate. A manager may add one later with a reason; it is then recorded with basis `set_after_decision` and the decision becomes eligible from then on. Nothing is backfilled or derived from action due dates.
- The latest action due date is **not** used as the implementation due date (it would let the plan set its own deadline).

### D-41.4 States and GOV-05

Per decision (signed ADR, or ARB review whose first approval is in the transition history):

| State | Rule |
|---|---|
| **No Plan** | No action exists. Never Implemented (D-32). |
| **In progress** | At least one action open. |
| **Awaiting verification** | All actions done with evidence, submitted, not yet verified. |
| **Implemented** | Independently verified (D-41.1, D-41.2). |
| **Overdue** | Due date in force has passed and not Implemented (shown with the underlying state). |
| **No due date** | Not timed (D-41.3). |
| **Lifecycle not recorded** | ARB approved with no recorded approval transition. Counted, never measured. |

**GOV-05 rate** for a period = decisions **verified on or before their due date in force** ÷ **eligible decisions**, where eligible = due date in force falls in the period and has passed (as of the period end for a closed period; today while it runs), readable by the viewer. Each decision counts once. Reported apart, never in the numerator: implemented late, awaiting verification, in progress, No Plan (all eligible, so in the denominator), and outside the rate: no due date, lifecycle not recorded, unscoped. The earlier "≥ 90 days" window (`GOVERNANCE_MEASUREMENT_MODEL.md` §3.3) is superseded by D-32's "no universal waiting period".

### Open questions for the owner (answer with the approval)

1. **Signatories as verifiers** — allowed as proposed, or excluded too?
2. **File required** — at least one unchanged file per decision (proposed), or per action?
3. **Due-date changes** — any `adr.manage` / `arb.manage` holder with a reason (proposed), or only `governance.verify_implementation`?
4. **Unscoped decisions** — accept that an ADR with no linked card cannot be verified (proposed), or allow evidence attached to the ADR itself (new attachment target, larger change)?

## 3. Batch 3.4 implementation instructions (after approval)

Follow `PHASED_DELIVERY_PLAN.md` conventions: EN + AR only, one focused validation pass, PROGRESS = Completed only after commit authorisation.

### 3.1 Database (one migration, `1172_decision_actions_and_implementation.py`)

- `todos`: `source_kind` (String(16), nullable, `adr` / `arb`), `source_id` (UUID, nullable, no FK), index `ix_todos_source (source_kind, source_id)`; `completion_note` (Text), `evidence_refs` (JSONB `[{kind, id, name, sha256, size?}]`), `completed_by` (user FK, SET NULL), `completed_at` (timestamptz, nullable, **no default** — earlier todos stay NULL).
- `architecture_decisions` and `arb_reviews`: `implementation_due_date` (Date, nullable), `implementation_due_basis` (String(24), nullable).
- `governance_transitions`: reuse; new instruments `adr_implementation` / `arb_implementation` with states `NULL → planned → submitted → verified` and `submitted → planned` (returned); new `event_kind = "due_date_changed"` with `previous_due_date` / `due_date` columns (Date, nullable); `attestation` (JSONB, nullable) on the verify row. No default on any new timestamp; any new `created_at` gets `server_default=sa.func.now()`.
- **Workspace transfer** (mandatory checklist): `completed_by` → `user_fk_columns` of the Todos section; `evidence_refs` and `attestation` → allowlist in `test_workspace_io_id_bearing_columns.py` (they hold attachment / document ids, which keep their UUIDs) — or declare and remap if any card id is stored; `source_id` → allowlist (ADR / ARB keep UUIDs); round-trip assertion in `test_workspace_io_roundtrip.py`.

### 3.2 Backend

- `core/permissions.py`: `governance.verify_implementation` (no default role); mirrored in the frontend permission lists.
- New `services/decision_implementation.py` — the **one** definition of decision state and GOV-05 eligibility: action create / complete / reopen rules, submission, verification and return (independence checks D-41.1, evidence checks reusing the exception fingerprint helpers — lift `_fingerprint` and the re-check out of `governance_transitions.py` into a shared helper rather than copying), due-date set / change with events.
- Actions are todos with `source_kind/source_id`; owner (`assigned_to`) and `due_date` required (422). Create / edit / delete: `adr.manage` / `arb.manage`. Complete: the owner or a manager, with note + evidence. Once a decision is **submitted**, adding, editing or reopening an action returns it to `planned` (transition row). Once **verified**, its actions are frozen (409 `implementation_verified`).
- Routes (new or in `api/v1/adr.py`, `api/v1/arb.py`): `GET/POST /adr/{id}/actions`, `PATCH /adr/{id}/actions/{todo_id}`, `POST /adr/{id}/implementation/submit|verify|return`, `PATCH /adr/{id}/implementation-due-date`; same under `/arb/{id}/…`. Reads need `adr.view` / `arb.view` plus the ARB subject card's `CardReadScope`; evidence and attestation text follow I-33 / I-37 confidentiality (owners, managers, verifiers; others get `*_withheld: true`). Every mutation publishes / audits per `.claude/rules/db-sessions-events-audit.md`.
- ADR signing: `implementation_due_date` editable only while not signed; `sign_adr` stamps basis `approved_with_decision` when present. ARB: accept `implementation_due_date` on the approve request.
- Generic todo endpoints must refuse to edit, complete or delete a todo with a `source_kind` (409 `decision_action`) so the rules cannot be bypassed; the Todos page lists them read-through with a link to the decision.
- `services/executive/governance.py`: GOV-05 tile (rate, eligible, outcome buckets summing to eligible, plus no-due-date / not-recorded / unscoped counts), registered `GOV-05@1` in `services/executive/registry.py`, daily capture under D-19 from ship date, no backfill. Overview governance tile switches to GOV-05 (I-7).
- `python scripts/dump_openapi.py`.

### 3.3 Frontend

- `features/adr/…` preview and ARB detail: **Implementation** panel — due date (with basis and change history), actions list reusing the todo row UI (owner, due, status, evidence chips), complete-with-evidence dialog (card evidence picker reused from the exception remediation dialog), submit / verify (attestation) / return dialogs, state chip. Buttons hidden without permission; the API is the authority.
- ADR editor: due-date field before signing. ARB decision dialog: due-date field on approve.
- `ExecutiveGovernance.tsx` and overview: GOV-05 tile with buckets and Not Available reasons; types in `src/types/index.ts`; keys in `en` and `ar` (`common`, `admin`, `reports` as needed).

### 3.4 Tests

- `tests/services/test_decision_implementation.py`: every state; independence (owner, completer, submitter, author refused; signatory allowed); `evidence_required`, `invalid_evidence_ref`, `evidence_changed`, `evidence_integrity_unavailable`, `attestation_required`; due-date in force across a change before / after period end; no-due-date and lifecycle-not-recorded never in the rate; frozen after verification.
- `tests/api/test_decision_actions_api.py`: success path, 403 without manage / verify permission, 404 for an ARB review on a hidden card, 422 inputs, 409 on the generic todo endpoints.
- **Acceptance** (`GOVERNANCE_MEASUREMENT_MODEL.md` §6, restated): ADR with due date signed → two actions with evidence → both done → submitted → verified by an independent verifier before the due date → counted Implemented in the period the due date falls in; the same flow verified by an action owner is refused.
- Workspace round-trip with wiped inventory; Vitest for the panel and the GOV-05 tile.
- Mutation gate answered on the PR (not run locally).

### 3.5 Docs and release

- `docs/guide/` ADR / ARB pages and `docs/guide/dashboard.md` (+ `.ar.md`); `docs/admin/` permission note; CHANGELOG + VERSION minor bump; `PROGRESS_REPORT.md`, `REQUIREMENTS_TRACEABILITY_MATRIX.md` rows P3-08, P3-09 unblocked; `DECISION_LOG.md` D-41 moved to approved with I-42 onward for the details above.
