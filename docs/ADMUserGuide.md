# ADM Governance Workspace — User Guide

An **ADM Governance Workspace** turns an approved **Statement of Architecture Work (SoAW)** into a governed architecture engagement following the TOGAF Architecture Development Method (ADM).

You can use it to:

- Sequence and gate the ten TOGAF ADM phases,
- Attach evidence from existing Turbo EA records — SoAWs, ADRs, diagrams, risks, roadmaps, standards, rationalization assessments, inventory cards or plain URLs,
- Track owners, dates, blocked/overdue work, and gate approvals,
- Keep Requirements Management visible across every phase.

Existing SoAWs continue to work with or without an ADM workspace. Creating one is opt-in.

## 1. Getting there

There are three entry points:

- **Left navigation → Reports → ADM Governance** — the workspace list / dashboard.
- **From a SoAW** — a new "ADM Workspace" section on the SoAW editor lets you create a workspace with one click.
- **Dashboard widget** — the "My ADM actions" widget on the main dashboard surfaces phases awaiting gate approval, blocked phases you own, and overdue phases you own.

## 2. Creating a workspace

From the ADM Governance list page click **New workspace**, or open a SoAW and click **Create ADM workspace** in the ADM section.

You must anchor the workspace to at least one of:

- a **SoAW** — the primary anchor,
- an **Initiative card** (Turbo EA card of type `Initiative`) — useful when you are governing an engagement before a full SoAW exists.

A SoAW can carry at most one ADM workspace (v1 constraint). Attempts to create a second one for the same SoAW are rejected with a clear message.

New workspaces are seeded with the ten standard TOGAF ADM phases:

| # | Phase |
|---|---|
| 0 | Preliminary |
| 1 | Phase A — Architecture Vision |
| 2 | Phase B — Business Architecture |
| 3 | Phase C — Information Systems Architecture |
| 4 | Phase D — Technology Architecture |
| 5 | Phase E — Opportunities and Solutions |
| 6 | Phase F — Migration Planning |
| 7 | Phase G — Implementation Governance |
| 8 | Phase H — Architecture Change Management |
| 9 | Requirements Management (continuous) |

Requirements Management runs alongside every other phase — it never enters "Ready for gate" and cannot be approved or skipped.

## 3. Working a phase

Click a phase tile in the timeline to open its detail panel. Each phase has:

- **Status** — Not started · In progress · Blocked · Ready for gate · Approved · Skipped.
- **Owner** — a Turbo EA user; optional.
- **Planned start / end dates** — optional; drives the overdue indicator.
- **Description and notes** — free-text.
- **Artefact checklist** — evidence links, each of which points at an existing Turbo EA entity or a URL.
- **Gate readiness** — a progress bar (linked + waived vs total required).
- **Approval history** — approved_by, approved_at, comment, override reason (if any).

### 3.1 Linking artefacts

Click **Add artefact** to link evidence. Pick a kind:

| Kind | What you provide |
|---|---|
| SoAW, ADR, ARB review, diagram, roadmap, risk, compliance finding, tech standard, standard exception, rationalization assessment, inventory card | A title plus the UUID of the target entity |
| URL | A title plus a URL |
| Document, file attachment, requirement | A title (and optional notes) |

Tick **Mark as required for the gate** to make the artefact count against the phase's readiness gate. Un-required artefacts are informational only.

### 3.2 Waiving a requirement

If a required artefact is not applicable, click the **Waive requirement** icon on its row and record a reason (minimum 8 characters). Waived requirements are treated as satisfied for gate readiness. You can un-waive at any time.

Waive and un-waive actions land in the audit log with your user id, timestamp and reason.

### 3.3 Mark ready for gate

When all required artefacts are linked or waived, click **Mark ready for gate**. The phase status becomes `Ready for gate` and shows up on approvers' dashboards.

If required artefacts remain unlinked and unwaived, you can still mark the phase ready — but only by ticking **Override the readiness check with a documented reason** and providing a reason (min 8 characters). The override reason is stored on the phase and stamped into the audit event.

### 3.4 Approve

Users with the `adm.approve_gate` permission see the **Approve phase** button when the phase is Ready for gate. An optional comment is recorded on the approval history. Approving stamps `approved_by`, `approved_at`, and the audit event.

### 3.5 Reopen / skip

`adm.approve_gate` holders can also:

- **Reopen** an approved phase — requires a reason; approval history is preserved but the phase returns to In progress.
- **Skip** a phase — requires a reason; not permitted on Requirements Management.

## 4. Requirements Management

The Requirements Management panel below the phase detail lists every artefact of kind `requirement` across every phase of the workspace. Click the chip on the right of any row to jump to the phase that owns it.

Requirements Management is continuous by design; the state machine will not accept `ready_for_gate`, `approved` or `skipped` for it.

## 5. Roles you need

The following permissions gate ADM actions:

- **`adm.view`** — see workspaces and phase detail. Granted by default to viewer, member, bpm_admin, admin.
- **`adm.manage`** — create/edit workspaces, phases, artefact links; waive requirements; mark-ready. Granted by default to member, bpm_admin, admin.
- **`adm.approve_gate`** — approve, reopen, skip phase gates. Granted by default to member, bpm_admin, admin.

If your tenant requires that only architecture leads approve gates, an administrator can revoke `adm.approve_gate` from the member role via **Admin → Roles**.

## 6. Audit

Every gate action, every waive / un-waive, every workspace / phase / artefact write emits an entry into Turbo EA's central events log. The audit page (Admin → Events) filters by `event_type` prefixed with `adm_`.

Events include `from`, `to`, `actor`, and (when applicable) the reason or override reason.

## 7. Deleting a workspace

Only users with `adm.manage` can delete a workspace, and only from the workspace detail page (bottom-right "Delete workspace" button). Deletion cascades to phases and artefact links. **The underlying SoAW, ADRs, diagrams, risks and cards are never deleted.**
