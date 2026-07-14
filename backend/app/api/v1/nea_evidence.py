"""NEA alignment / evidence-pack export API ([FORK] — noraPlan.md WP5.3).

Generate an immutable multi-sheet ``.xlsx`` snapshot of the agency's NORA
posture, list past packs, download, and delete. Generation is synchronous
(read-only aggregation) — the workbook is written to disk and the row flipped
to ``ready``. Gated by the existing ``nora`` permissions.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.nea_evidence import NeaEvidencePack
from app.models.user import User
from app.services.nea_evidence import build_evidence_pack
from app.services.permission_service import PermissionService

log = logging.getLogger(__name__)

router = APIRouter(prefix="/nea-evidence-packs", tags=["nea-evidence"])

_PACK_DIR = Path("data/nea_evidence_packs")
_XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class PackCreate(BaseModel):
    title: str | None = Field(default=None, max_length=300)


def _pack_dict(p: NeaEvidencePack, names: dict | None = None) -> dict:
    names = names or {}
    return {
        "id": str(p.id),
        "title": p.title,
        "status": p.status,
        "filename": p.filename,
        "file_size": p.file_size,
        "summary": p.summary or {},
        "error_message": p.error_message,
        "generated_by": str(p.generated_by) if p.generated_by else None,
        "generated_by_display_name": names.get(p.generated_by),
        "generated_at": p.generated_at.isoformat() if p.generated_at else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


async def _get_pack(db: AsyncSession, pid: uuid.UUID) -> NeaEvidencePack:
    row = (
        await db.execute(select(NeaEvidencePack).where(NeaEvidencePack.id == pid))
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Evidence pack not found")
    return row


@router.get("")
async def list_packs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "nora.view")
    rows = list(
        (await db.execute(select(NeaEvidencePack).order_by(NeaEvidencePack.created_at.desc())))
        .scalars()
        .all()
    )
    ids = {p.generated_by for p in rows if p.generated_by}
    names: dict = {}
    if ids:
        res = await db.execute(select(User.id, User.display_name).where(User.id.in_(ids)))
        names = dict(res.all())
    return [_pack_dict(p, names) for p in rows]


@router.post("", status_code=201)
async def generate_pack(
    body: PackCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "nora.manage")
    ts = datetime.now(timezone.utc)
    title = body.title or f"NEA evidence pack {ts.strftime('%Y-%m-%d %H:%M')}"
    pack = NeaEvidencePack(title=title, status="generating", generated_by=user.id)
    db.add(pack)
    await db.flush()

    try:
        data, summary = await build_evidence_pack(db)
        _PACK_DIR.mkdir(parents=True, exist_ok=True)
        path = _PACK_DIR / f"{pack.id}.xlsx"
        path.write_bytes(data)
        pack.status = "ready"
        pack.summary = summary
        pack.file_size = len(data)
        pack.storage_path = str(path)
        pack.filename = f"nea_evidence_{ts.strftime('%Y-%m-%d_%H%M')}.xlsx"
        pack.generated_at = ts
    except Exception as e:  # noqa: BLE001
        log.exception("NEA evidence pack generation failed")
        pack.status = "failed"
        pack.error_message = str(e)[:2000]

    await db.commit()
    await db.refresh(pack)
    return _pack_dict(pack)


@router.get("/{pack_id}")
async def get_pack(
    pack_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "nora.view")
    return _pack_dict(await _get_pack(db, pack_id))


@router.get("/{pack_id}/download")
async def download_pack(
    pack_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "nora.view")
    pack = await _get_pack(db, pack_id)
    if pack.status != "ready" or not pack.storage_path:
        raise HTTPException(409, "Pack is not ready for download")
    path = Path(pack.storage_path)
    if not path.exists():
        raise HTTPException(404, "Pack file missing on disk")
    return StreamingResponse(
        iter([path.read_bytes()]),
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{pack.filename}"'},
    )


@router.delete("/{pack_id}", status_code=204)
async def delete_pack(
    pack_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await PermissionService.require_permission(db, user, "nora.manage")
    pack = await _get_pack(db, pack_id)
    if pack.storage_path:
        Path(pack.storage_path).unlink(missing_ok=True)
    await db.delete(pack)
    await db.commit()
