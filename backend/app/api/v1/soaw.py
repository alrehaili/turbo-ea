from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import get_current_user
from app.database import get_db
from app.models.improvement_opportunity import ImprovementOpportunity
from app.models.soaw import SoAW
from app.models.swot_entry import (
    PROMOTABLE_QUADRANTS,
    SWOT_QUADRANTS,
    SwotEntry,
)
from app.models.todo import Todo
from app.models.user import User
from app.services import document_collab, notification_service, soaw_service
from app.services import document_discussion_service as discussion
from app.services import document_history_service as history
from app.services.event_bus import event_bus
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/soaw", tags=["soaw"])

# Which architecture domain a promoted SWOT weakness/threat lands in by
# default. SWOT is strategic, so Business Architecture is the safe default;
# the user re-classifies in the Opportunities registry.
_SWOT_DEFAULT_DOMAIN = "BA"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SoAWCreate(BaseModel):
    name: str
    # "soaw" (TOGAF, default), a NORA governed document type ([FORK] WP3.2),
    # or one of the practice operating-model artifacts ([FORK] WP6.8 — the
    # Establishing EA Practice Guideline's ten artifacts).
    doc_type: str = Field(
        default="soaw",
        pattern=(
            "^(soaw|ea_project_strategy|ea_project_plan|environment_analysis"
            "|ea_usage_plan|ea_management_plan|ea_mandates|ea_services"
            "|ea_org_structure|ea_governance_model|ea_processes"
            "|ea_interaction_model|ea_kpis|ea_vocabulary|ea_operating_model)$"
        ),
    )
    initiative_id: str | None = None
    status: str = "draft"
    document_info: dict | None = None
    version_history: list | None = None
    sections: dict | None = None

    # Unknown keys must fail loudly: silently-ignored extras caused the
    # ADR body/link loss in #800 and masked the SoAW field mismatch in #802.
    model_config = {"extra": "forbid"}


class SoAWUpdate(BaseModel):
    name: str | None = None
    initiative_id: str | None = None
    status: str | None = None
    document_info: dict | None = None
    version_history: list | None = None
    sections: dict | None = None

    model_config = {"extra": "forbid"}


class SignatureRequest(BaseModel):
    user_ids: list[str]
    message: str | None = None


class RejectRequest(BaseModel):
    # The reason, which also opens the rejection thread (and the history row's note).
    comment: str = Field(max_length=4000)


class SignRequest(BaseModel):
    # Optional signing note: a ``sign_note`` comment in the discussion and the
    # note of the ``signature`` timeline row. An absent body signs without one.
    note: str | None = Field(default=None, max_length=2000)

    model_config = {"extra": "forbid"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_dict(s: SoAW, chains: soaw_service.SoAWChains) -> dict:
    return {
        "id": str(s.id),
        "name": s.name,
        "doc_type": s.doc_type or "soaw",
        "initiative_id": str(s.initiative_id) if s.initiative_id else None,
        "status": s.status,
        "document_info": s.document_info or {},
        "version_history": s.version_history or [],
        "sections": s.sections or {},
        "created_by": str(s.created_by) if s.created_by else None,
        "created_via": s.created_via,
        "updated_via": s.updated_via,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        "revision_number": s.revision_number,
        "parent_id": str(s.parent_id) if s.parent_id else None,
        "signatories": s.signatories or [],
        "signed_at": s.signed_at.isoformat() if s.signed_at else None,
        **soaw_service.chain_fields(chains, s.id),
    }


async def _render(db: AsyncSession, payloads: list[dict], user: User) -> list[dict]:
    """The response rows of one request as ``user`` reads them, in one batch."""
    return await document_collab.render_doc(
        db, document_collab.SOAW, payloads, user=user, read_scope=None
    )


async def _detail_fields(db: AsyncSession, s: SoAW) -> dict:
    """What a single-SoAW response adds to a list row: the open-thread count."""
    return {"open_thread_count": await discussion.open_thread_count(db, document_collab.SOAW, s.id)}


async def _respond(db: AsyncSession, s: SoAW, user: User) -> dict:
    """One SoAW with its chain fields (one light chain query)."""
    row = {**_row_to_dict(s, await soaw_service.load_chains(db)), **await _detail_fields(db, s)}
    (rendered,) = await _render(db, [row], user)
    return rendered


async def _detail(db: AsyncSession, s: SoAW, user: User) -> dict:
    """``GET /soaw/{id}``'s reply: the SoAW with its chain fields, its
    revisions and its open-thread count, rendered for ``user``."""
    chains = await soaw_service.load_chains(db)
    (rendered,) = await _render(
        db,
        [
            {
                **_row_to_dict(s, chains),
                "revisions": soaw_service.revisions_payload(chains, s.id),
                **await _detail_fields(db, s),
            }
        ],
        user,
    )
    return rendered


def _refuse(refusal: tuple[int, object] | None) -> None:
    if refusal is not None:
        raise HTTPException(refusal[0], refusal[1])


async def _get_soaw(db: AsyncSession, soaw_id: str) -> SoAW:
    result = await db.execute(select(SoAW).where(SoAW.id == uuid.UUID(soaw_id)))
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Statement of Architecture Work not found")
    return s


# ---------------------------------------------------------------------------
# CRUD Endpoints
# ---------------------------------------------------------------------------


@router.get("")
async def list_soaws(
    initiative_id: str | None = Query(None),
    doc_type: str | None = Query(None, max_length=32),
    include_earlier: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "soaw.view")
    stmt = select(SoAW).order_by(SoAW.updated_at.desc())
    if initiative_id:
        stmt = stmt.where(SoAW.initiative_id == uuid.UUID(initiative_id))
    if doc_type:
        stmt = stmt.where(SoAW.doc_type == doc_type)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    chains = await soaw_service.load_chains(db)
    out = [_row_to_dict(s, chains) for s in rows]
    return await _render(
        db,
        [r for r in out if soaw_service.keep_in_list(r, include_earlier=include_earlier)],
        user,
    )


@router.post("", status_code=201)
async def create_soaw(
    body: SoAWCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "soaw.manage")
    text = await document_collab.before_save(
        db,
        document_collab.SOAW,
        None,
        {"sections": body.sections or {}},
        user=user,
        read_scope=None,
    )
    s = SoAW(
        name=body.name,
        doc_type=body.doc_type,
        initiative_id=uuid.UUID(body.initiative_id) if body.initiative_id else None,
        status=body.status,
        document_info=body.document_info or {},
        version_history=body.version_history or [],
        sections=text["sections"],
        created_by=user.id,
    )
    db.add(s)
    await db.flush()
    await document_collab.on_workflow(db, document_collab.SOAW, s, "created", user=user)
    await db.commit()
    await db.refresh(s)
    return await _respond(db, s, user)


@router.get("/{soaw_id}")
async def get_soaw(
    soaw_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "soaw.view")
    s = await _get_soaw(db, soaw_id)
    return await _detail(db, s, user)


@router.patch("/{soaw_id}")
async def update_soaw(
    soaw_id: str,
    body: SoAWUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "soaw.manage")
    s = await _get_soaw(db, soaw_id)

    # Signed: no edit at all. Status moves with their own endpoint: 400. In
    # review: only the initiative (filing) may change.
    _refuse(soaw_service.update_refusal(s.status, body.status, body.model_fields_set))
    # Whether this save may change content: a draft, or a legacy approved SoAW.
    was_draft = soaw_service.content_editable(s.status)
    # The content before this save touches the row: the first recorded save
    # keeps it as the baseline version.
    before = history.snapshot_of(document_collab.SOAW, s) if was_draft else None

    if body.name is not None:
        s.name = body.name
    if body.initiative_id is not None:
        s.initiative_id = uuid.UUID(body.initiative_id) if body.initiative_id else None
    if body.status is not None:
        s.status = body.status
    if body.document_info is not None:
        s.document_info = body.document_info
    if body.version_history is not None:
        s.version_history = body.version_history
    if body.sections is not None:
        text = await document_collab.before_save(
            db,
            document_collab.SOAW,
            s,
            {"sections": body.sections},
            user=user,
            read_scope=None,
        )
        s.sections = text["sections"]
    await document_collab.after_save(
        db, document_collab.SOAW, s, user=user, was_draft=was_draft, before=before
    )
    await db.commit()
    await db.refresh(s)
    return await _respond(db, s, user)


@router.delete("/{soaw_id}", status_code=204)
async def delete_soaw(
    soaw_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "soaw.manage")
    s = await _get_soaw(db, soaw_id)
    _refuse(soaw_service.delete_refusal(s.status))
    await db.delete(s)
    await db.commit()


# ---------------------------------------------------------------------------
# Signing workflow
# ---------------------------------------------------------------------------


@router.post("/{soaw_id}/request-signatures")
async def request_signatures(
    soaw_id: str,
    body: SignatureRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Request signatures from specified users. Creates todos and notifications."""
    await PermissionService.require_permission(db, user, "soaw.manage")
    s = await _get_soaw(db, soaw_id)

    _refuse(soaw_service.request_refusal(s.status))
    label = soaw_service.soaw_label(s.name, s.revision_number)
    link = soaw_service.soaw_link(s.id)

    # Resolve user names for the signatories list
    signatories = []
    for uid_str in body.user_ids:
        uid = uuid.UUID(uid_str)
        result = await db.execute(select(User).where(User.id == uid))
        u = result.scalar_one_or_none()
        if not u:
            raise HTTPException(404, f"User {uid_str} not found")
        signatories.append(
            {
                "user_id": str(uid),
                "display_name": u.display_name,
                "email": u.email,
                "status": "pending",
                "signed_at": None,
            }
        )

    s.signatories = signatories
    flag_modified(s, "signatories")
    s.status = "in_review"
    await document_collab.on_workflow(
        db, document_collab.SOAW, s, "sent_for_review", user=user, signatories=signatories
    )

    # Create a todo for each signatory
    for sig in signatories:
        todo = Todo(
            card_id=s.initiative_id,
            description=f'Sign SoAW: "{label}"',
            assigned_to=uuid.UUID(sig["user_id"]),
            created_by=user.id,
            link=link,
            is_system=True,
        )
        db.add(todo)

        # Create notification (no actor_id so self-request still notifies)
        await notification_service.create_notification(
            db,
            user_id=uuid.UUID(sig["user_id"]),
            actor_id=user.id,
            notif_type="soaw_sign_requested",
            title="Signature Requested",
            message=f'{user.display_name} requested your signature on "{label}"',
            link=link,
            data={
                "soaw_id": soaw_id,
                "soaw_name": s.name,
                "revision_number": s.revision_number,
            },
        )

    await event_bus.publish(
        "soaw.signatures_requested",
        {
            "id": soaw_id,
            "name": s.name,
            "revision_number": s.revision_number,
            "signatory_count": len(signatories),
        },
        db=db,
        user_id=user.id,
    )
    await db.commit()
    await db.refresh(s)

    return await _respond(db, s, user)


@router.post("/{soaw_id}/sign")
async def sign_soaw(
    soaw_id: str,
    body: SignRequest | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Sign the SoAW as the current user. When all signatories have signed,
    the document status changes to 'signed' and becomes readonly."""
    # Signing is gated by the dedicated `soaw.sign` permission (mirrors
    # `adr.py`'s sign_adr → `adr.sign`); `soaw.manage` holders retain the
    # ability too so the change never removes an existing capability.
    can_sign = await PermissionService.check_permission(
        db, user, "soaw.sign"
    ) or await PermissionService.check_permission(db, user, "soaw.manage")
    if not can_sign:
        raise HTTPException(403, "Insufficient permissions")
    s = await _get_soaw(db, soaw_id)

    if s.status == "signed":
        raise HTTPException(400, "Document is already signed")

    signatories = list(s.signatories or [])
    if not signatories:
        raise HTTPException(400, "No signatures have been requested for this document")

    # Find the current user in the signatories list
    found = False
    for sig in signatories:
        if sig["user_id"] == str(user.id):
            if sig["status"] == "signed":
                raise HTTPException(400, "You have already signed this document")
            sig["status"] = "signed"
            sig["signed_at"] = datetime.now(timezone.utc).isoformat()
            found = True
            break

    if not found:
        raise HTTPException(403, "You are not a signatory of this document")

    label = soaw_service.soaw_label(s.name, s.revision_number)
    # Auto-close the sign-request todo for this user (matched by its link:
    # revisions of one SoAW share a name)
    sign_todos = await db.execute(
        select(Todo).where(
            Todo.assigned_to == user.id,
            Todo.is_system == True,  # noqa: E712
            Todo.status == "open",
            Todo.link == soaw_service.soaw_link(s.id),
        )
    )
    for t in sign_todos.scalars().all():
        t.status = "done"

    s.signatories = signatories
    flag_modified(s, "signatories")
    await document_collab.on_workflow(
        db, document_collab.SOAW, s, "signature", user=user, note=body.note if body else None
    )

    # Check if all signatories have signed
    all_signed = all(sig["status"] == "signed" for sig in signatories)
    if all_signed:
        s.status = "signed"
        s.signed_at = datetime.now(timezone.utc)
        await document_collab.on_workflow(db, document_collab.SOAW, s, "signed", user=user)

        # Notify creator that the document is fully signed
        if s.created_by:
            await notification_service.create_notification(
                db,
                user_id=s.created_by,
                actor_id=user.id,
                notif_type="soaw_signed",
                title="SoAW Fully Signed",
                message=f'All signatories have signed "{label}"',
                link=f"/ea-delivery/soaw/{soaw_id}/preview",
                data={
                    "soaw_id": soaw_id,
                    "soaw_name": s.name,
                    "revision_number": s.revision_number,
                },
            )
    else:
        # Notify creator that an individual signatory has signed
        if s.created_by:
            signed_count = sum(1 for sig in signatories if sig["status"] == "signed")
            await notification_service.create_notification(
                db,
                user_id=s.created_by,
                actor_id=user.id,
                notif_type="soaw_signed",
                title="SoAW Signature Received",
                message=(
                    f'{user.display_name} signed "{label}" ({signed_count}/{len(signatories)})'
                ),
                link=f"/ea-delivery/soaw/{soaw_id}",
                data={
                    "soaw_id": soaw_id,
                    "soaw_name": s.name,
                    "revision_number": s.revision_number,
                },
            )

    await event_bus.publish(
        "soaw.signed",
        {
            "id": soaw_id,
            "name": s.name,
            "revision_number": s.revision_number,
            "signer": user.display_name,
            "all_signed": all_signed,
        },
        db=db,
        user_id=user.id,
    )
    await db.commit()
    await db.refresh(s)

    return await _respond(db, s, user)


@router.post("/{soaw_id}/recall-signatures")
async def recall_signatures(
    soaw_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Recall all pending signature requests. Only the creator or an admin
    can recall. Resets status to draft and clears signatories."""
    await PermissionService.require_permission(db, user, "soaw.manage")
    s = await _get_soaw(db, soaw_id)

    if s.status != "in_review":
        raise HTTPException(400, "Only documents in review can have signatures recalled")
    label = soaw_service.soaw_label(s.name, s.revision_number)

    # Close pending sign-request todos
    sign_todos = await db.execute(
        select(Todo).where(
            Todo.is_system == True,  # noqa: E712
            Todo.status == "open",
            Todo.link == soaw_service.soaw_link(s.id),
        )
    )
    for t in sign_todos.scalars().all():
        t.status = "done"

    # Notify pending signatories that the request was recalled
    for sig in s.signatories or []:
        if sig["status"] == "pending":
            await notification_service.create_notification(
                db,
                user_id=uuid.UUID(sig["user_id"]),
                actor_id=user.id,
                notif_type="soaw_sign_recalled",
                title="Signature Request Recalled",
                message=(f'{user.display_name} recalled the signature request for "{label}"'),
                link=f"/ea-delivery/soaw/{soaw_id}",
                data={
                    "soaw_id": soaw_id,
                    "soaw_name": s.name,
                    "revision_number": s.revision_number,
                },
            )

    s.signatories = []
    flag_modified(s, "signatories")
    s.status = "draft"
    await document_collab.on_workflow(db, document_collab.SOAW, s, "recalled", user=user)

    await event_bus.publish(
        "soaw.signatures_recalled",
        {"id": soaw_id, "name": s.name, "revision_number": s.revision_number},
        db=db,
        user_id=user.id,
    )
    await db.commit()
    await db.refresh(s)

    return await _respond(db, s, user)


@router.post("/{soaw_id}/reject")
async def reject_soaw(
    soaw_id: str,
    body: RejectRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Reject the SoAW as a signatory. Resets to draft (the revision number
    stays: revisions count signed versions), clears all signatories, notifies
    the creator and opens a rejection thread carrying the reason.

    Like signing: a signatory holding ``soaw.sign`` (or ``soaw.manage``)."""
    can_sign = await PermissionService.check_permission(
        db, user, "soaw.sign"
    ) or await PermissionService.check_permission(db, user, "soaw.manage")
    if not can_sign:
        raise HTTPException(403, "Insufficient permissions")
    s = await _get_soaw(db, soaw_id)

    if s.status != "in_review":
        raise HTTPException(400, "Only documents in review can be rejected")

    signatories = list(s.signatories or [])
    if not any(sig["user_id"] == str(user.id) for sig in signatories):
        raise HTTPException(403, "You are not a signatory of this document")
    label = soaw_service.soaw_label(s.name, s.revision_number)

    # Close all pending sign-request todos
    sign_todos = await db.execute(
        select(Todo).where(
            Todo.is_system == True,  # noqa: E712
            Todo.status == "open",
            Todo.link == soaw_service.soaw_link(s.id),
        )
    )
    for t in sign_todos.scalars().all():
        t.status = "done"

    # Notify the creator
    if s.created_by:
        await notification_service.create_notification(
            db,
            user_id=s.created_by,
            actor_id=user.id,
            notif_type="soaw_rejected",
            title="SoAW Rejected",
            message=(f'{user.display_name} rejected "{label}": {body.comment}'),
            link=f"/ea-delivery/soaw/{soaw_id}",
            data={
                "soaw_id": soaw_id,
                "soaw_name": s.name,
                "revision_number": s.revision_number,
                "comment": body.comment,
            },
        )

    # Notify other signatories
    for sig in signatories:
        if sig["user_id"] != str(user.id):
            await notification_service.create_notification(
                db,
                user_id=uuid.UUID(sig["user_id"]),
                actor_id=user.id,
                notif_type="soaw_rejected",
                title="SoAW Rejected",
                message=(f'{user.display_name} rejected "{label}": {body.comment}'),
                link=f"/ea-delivery/soaw/{soaw_id}",
                data={
                    "soaw_id": soaw_id,
                    "soaw_name": s.name,
                    "revision_number": s.revision_number,
                    "comment": body.comment,
                },
            )

    s.signatories = []
    flag_modified(s, "signatories")
    s.status = "draft"
    await document_collab.on_workflow(
        db, document_collab.SOAW, s, "rejected", user=user, note=body.comment
    )

    await event_bus.publish(
        "soaw.rejected",
        {
            "id": soaw_id,
            "name": s.name,
            "revision_number": s.revision_number,
            "rejector": user.display_name,
        },
        db=db,
        user_id=user.id,
    )
    await db.commit()
    await db.refresh(s)

    return await _respond(db, s, user)


@router.post("/{soaw_id}/revise")
async def revise_soaw(
    soaw_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new revision of a signed SoAW. Copies the document content
    into a new draft linked to the same initiative, numbered after the chain's
    highest revision, with parent_id pointing to the original. Refused (409)
    while the chain already has an unsigned revision, and on a signed revision
    that a later signed revision superseded."""
    await PermissionService.require_permission(db, user, "soaw.manage")
    s = await _get_soaw(db, soaw_id)
    chains = await soaw_service.load_chains(db)
    _refuse(soaw_service.revise_refusal(chains, s.id))

    new_revision = await soaw_service.create_revision(db, s, created_by=user.id, chains=chains)
    await db.commit()
    await db.refresh(new_revision)

    return await _respond(db, new_revision, user)


# ---------------------------------------------------------------------------
# Revision history
# ---------------------------------------------------------------------------


@router.get("/{soaw_id}/revisions")
async def list_revisions(
    soaw_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all revisions in the chain for this SoAW, in chain order (fork-safe;
    a dangling parent is a root)."""
    await PermissionService.require_permission(db, user, "soaw.view")
    s = await _get_soaw(db, soaw_id)
    chains = await soaw_service.load_chains(db)
    ids = soaw_service.chain_ids(chains, s.id)
    result = await db.execute(select(SoAW).where(SoAW.id.in_(ids)))
    by_id = {row.id: row for row in result.scalars().all()}
    return await _render(db, [_row_to_dict(by_id[i], chains) for i in ids if i in by_id], user)


# ---------------------------------------------------------------------------
# Structured SWOT entries ([FORK] noraPlan.md WP3.3)
#
# The Environment-Analysis document's four quadrants carry structured,
# promotable rows alongside their rich text. A weakness or threat can be
# promoted into the Improvement-Opportunity registry (mirrors the
# compliance-finding → risk bridge), with an idempotent back-link.
# ---------------------------------------------------------------------------


class SwotEntryCreate(BaseModel):
    quadrant: str = Field(max_length=16)
    text: str = Field(min_length=1, max_length=2000)


def _swot_dict(e: SwotEntry) -> dict:
    return {
        "id": str(e.id),
        "soaw_id": str(e.soaw_id),
        "quadrant": e.quadrant,
        "text": e.text,
        "sort_order": e.sort_order,
        "opportunity_id": str(e.opportunity_id) if e.opportunity_id else None,
        "promotable": e.quadrant in PROMOTABLE_QUADRANTS,
    }


async def _get_swot_entry(db: AsyncSession, entry_id: str) -> SwotEntry:
    e = await db.get(SwotEntry, uuid.UUID(entry_id))
    if e is None:
        raise HTTPException(404, "SWOT entry not found")
    return e


@router.get("/{soaw_id}/swot")
async def list_swot_entries(
    soaw_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "soaw.view")
    await _get_soaw(db, soaw_id)  # 404 if the document is missing
    rows = (
        (
            await db.execute(
                select(SwotEntry)
                .where(SwotEntry.soaw_id == uuid.UUID(soaw_id))
                .order_by(SwotEntry.quadrant, SwotEntry.sort_order, SwotEntry.created_at)
            )
        )
        .scalars()
        .all()
    )
    return [_swot_dict(e) for e in rows]


@router.post("/{soaw_id}/swot", status_code=201)
async def create_swot_entry(
    soaw_id: str,
    body: SwotEntryCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "soaw.manage")
    await _get_soaw(db, soaw_id)
    if body.quadrant not in SWOT_QUADRANTS:
        raise HTTPException(422, f"Invalid quadrant. Expected one of {SWOT_QUADRANTS}")
    e = SwotEntry(
        soaw_id=uuid.UUID(soaw_id),
        quadrant=body.quadrant,
        text=body.text.strip(),
        created_by=user.id,
    )
    db.add(e)
    await db.commit()
    await db.refresh(e)
    return _swot_dict(e)


@router.delete("/swot/{entry_id}", status_code=204)
async def delete_swot_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "soaw.manage")
    e = await _get_swot_entry(db, entry_id)
    await db.delete(e)
    await db.commit()


@router.post("/swot/{entry_id}/promote", status_code=201)
async def promote_swot_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Promote a weakness/threat SWOT entry to an Improvement Opportunity.

    Idempotent — if the entry was already promoted, returns the existing
    opportunity id. Requires both ``soaw.manage`` (the source document) and
    ``grc.manage`` (the opportunity registry), mirroring the compliance →
    risk bridge's dual-permission model."""
    await PermissionService.require_permission(db, user, "soaw.manage")
    await PermissionService.require_permission(db, user, "grc.manage")
    e = await _get_swot_entry(db, entry_id)

    if e.quadrant not in PROMOTABLE_QUADRANTS:
        raise HTTPException(
            400,
            f"Only {' / '.join(PROMOTABLE_QUADRANTS)} entries can be promoted to an opportunity.",
        )

    # Idempotent: an already-promoted entry returns its opportunity.
    if e.opportunity_id is not None:
        existing = await db.get(ImprovementOpportunity, e.opportunity_id)
        if existing is not None:
            return {"opportunity_id": str(existing.id), "created": False}

    title = e.text.strip()
    if len(title) > 300:
        title = title[:297] + "…"
    opp = ImprovementOpportunity(
        title=title,
        description=e.text.strip(),
        domain=_SWOT_DEFAULT_DOMAIN,
        source="swot",
        priority="medium",
        status="proposed",
        created_by=user.id,
    )
    db.add(opp)
    await db.flush()
    e.opportunity_id = opp.id
    await db.commit()
    return {"opportunity_id": str(opp.id), "created": True}
