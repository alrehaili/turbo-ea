# ADM Governance Workspace — Manual Test Checklist

Run the checklist below on a fresh instance after `docker compose up -d` (or an equivalent local dev run). No demo seed is required — the tests exercise create + drive-through paths using the built-in template.

## 0. Backend + frontend up

- [ ] `docker compose up -d` completes without errors.
- [ ] The web UI loads at `http://localhost:8920/` (or your `HOST_PORT`).
- [ ] Register or log in as an existing admin.

## 1. Migration

- [ ] Backend logs on startup show `Running upgrade 131 -> 132, add ADM Governance Workspace tables` (or equivalent Alembic line).
- [ ] `psql` (or your DB tool) shows the three new tables: `adm_workspaces`, `adm_phases`, `adm_phase_artefacts`.
- [ ] The `statement_of_architecture_works` table has **no** new columns and the same row count as before.

## 2. Nav discoverability

- [ ] Log in as an admin. Reports → **ADM Governance** appears in the nav dropdown.
- [ ] Log out and log in as a `viewer`. Reports → **ADM Governance** still appears (viewer has `adm.view` by default).
- [ ] Log in as a role that has `adm.view=false` (e.g. a custom role you create with the Admin → Roles UI). The **ADM Governance** entry is hidden.

## 3. Create a workspace from a SoAW

- [ ] Open Reports → EA Delivery → any existing SoAW in the list, or create a new SoAW.
- [ ] The **ADM Workspace** section shows the empty state with a **Create ADM workspace** button.
- [ ] Click the button. The dialog opens with the SoAW pre-filled. Name is required.
- [ ] Confirm. The dialog closes and the SoAW page reloads showing a summary + phase timeline strip.
- [ ] The **Open ADM workspace** button navigates to `/ea-delivery/adm/{id}`.

## 4. Create a workspace from the list page

- [ ] Reports → ADM Governance → click **New workspace**.
- [ ] Try to submit without either a SoAW UUID or an Initiative UUID — the API rejects with 422 and a clear message.
- [ ] Provide a SoAW UUID. The workspace is created and the browser navigates to its detail page.

## 5. Workspace list page

- [ ] The workspace you just created is listed.
- [ ] Search by name filters the list live.
- [ ] The status filter offers All / Active / Draft / On hold / Completed / Archived and filters correctly.
- [ ] Each card shows completion % (0% initially), status chip, active-phase chip and any blocked / overdue chips.
- [ ] Clicking a card opens the detail page.

## 6. Phase timeline

- [ ] Ten phase tiles are visible: Preliminary, Phase A through H, and Requirements Management as a separate chip below the strip.
- [ ] Every non-continuous tile shows status "Not started" and 0/N artefacts.
- [ ] Requirements Management chip labels as "Requirements Management · 1" (one placeholder from the template).
- [ ] Clicking any tile / chip loads its detail panel underneath.

## 7. Phase detail — status transitions

- [ ] Open Phase A. Status is Not started. Change the status dropdown / click the status pill to move to In progress (via PATCH). Timeline reflects it.
- [ ] Attempt to move directly to Approved: rejected (422 in the network tab; UI shows the API error).
- [ ] From In progress, add a URL artefact via **Add artefact** with a valid URL. It appears in the artefact list with a green check.

## 8. Gate readiness

- [ ] Phase A ships with two required artefact placeholders. Their rows show a red "unlinked" icon.
- [ ] Click **Mark ready for gate** without linking anything. The dialog shows the outstanding-artefact warning and offers the override switch.
- [ ] Try submitting with the override switch off. The submit button is disabled until you tick override + enter a reason ≥ 8 chars.
- [ ] Tick override, enter a reason ("Board deferred until Q3"). Submit. The phase becomes Ready for gate; the approval history block shows the override reason.

## 9. Approve

- [ ] Still logged in as admin, click **Approve phase**. Enter an optional comment. Submit.
- [ ] The phase becomes Approved. The tile shows the green check icon. Approval history shows date + comment.
- [ ] Log out and log in as a user with `adm.manage` but **not** `adm.approve_gate` (create a custom role via Admin → Roles).
- [ ] Open the same phase. The **Approve** button is disabled. The **Mark ready for gate** button is available. The API call is blocked with 403 if attempted directly.

## 10. Reopen

- [ ] Log in as admin. Open the Approved phase. Click **Reopen**. Reason is required (min 8 chars).
- [ ] After submit the phase returns to In progress; the previous approval history line is preserved and a new "reopened: reason…" appended.

## 11. Skip

- [ ] Move Phase B to In progress. Click **Skip phase**. Reason required. Submit.
- [ ] Phase B tile shows Skipped, greyed.
- [ ] Attempt to skip Requirements Management: 422 (continuous phases cannot be skipped).

## 12. Waive an artefact requirement

- [ ] Open Phase C. Click the waive icon on one of the required placeholders. Enter a reason. Submit.
- [ ] The row now shows the "waived" indicator and the completion bar advances.
- [ ] Click the un-waive icon to reverse. Completion % updates.

## 13. Requirements Management panel

- [ ] Below the phase detail, the Requirements Management panel shows the seeded requirement placeholder.
- [ ] Click **Add artefact** on the Requirements Management chip / phase. Add a `requirement` kind artefact with a title.
- [ ] Refresh. The new requirement appears in the cross-phase panel with a "Requirements Management" chip on the right.
- [ ] Clicking the chip navigates to that phase's detail.

## 14. Dashboard widget

- [ ] Go to `/` (Dashboard).
- [ ] The **My ADM actions** card shows non-zero rows if you own any blocked / overdue phases and, as an approver, any phases sitting in Ready-for-gate.
- [ ] Clicking any chip in the widget deep-links into the correct workspace + phase.

## 15. Delete

- [ ] From the workspace detail, click **Delete workspace**. Confirm. The list page reloads without the workspace.
- [ ] The linked SoAW is still visible and unchanged.
- [ ] Recreate the workspace from the same SoAW to confirm the "one workspace per SoAW" rule releases after delete.

## 16. Audit trail

- [ ] Admin → Events (or your instance's audit log page). Filter or search for `adm_`.
- [ ] Every action from the previous steps has a corresponding event with a JSONB payload including `from` / `to` / `actor` / `reason` (where applicable).
- [ ] Impersonation-driven events (Admin → View as role, then run any ADM action) carry both `impersonator_user_id` and `impersonated_role` in the event payload.

## 17. RTL + Arabic

- [ ] Switch language to Arabic (Admin → Settings → Languages or the user menu).
- [ ] Reports → ADM Governance still opens with the Arabic label ("حوكمة ADM").
- [ ] Phase timeline reads right-to-left; icons flip appropriately; the gate dialog labels are Arabic.

## 18. Backwards compatibility

- [ ] Existing SoAWs without an ADM workspace are unaffected — they still load, edit, and sign as before.
- [ ] The Alembic downgrade to 131 runs cleanly (`alembic downgrade 131`), removes the three new tables, and lets the app boot at revision 131 again (dev-only sanity check).
