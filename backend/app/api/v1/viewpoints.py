"""EA Viewpoints (NORA) API endpoints.

GET /viewpoints — list all 67 NORA/DGA viewpoints with metadata.
GET /viewpoints/:code — get single viewpoint details.

No auth required for public discovery.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.viewpoint_definition import ViewpointDefinition
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/viewpoints", tags=["viewpoints"])


class ViewpointResponse:
    """ViewpointDefinition response model."""

    code: str
    name_en: str
    name_ar: str
    domain: str
    level: str
    type: str
    description_en: str | None
    description_ar: str | None
    building_blocks: list | None
    target_route: str | None
    status: str
    sort_order: int


@router.get("", response_model=PaginatedResponse)
async def list_viewpoints(
    domain: str | None = None,
    level: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List all NORA viewpoints, optionally filtered by domain/level/status.

    Returns paginated list with pagination metadata.
    """
    query = select(ViewpointDefinition)

    if domain:
        query = query.where(ViewpointDefinition.domain == domain)
    if level:
        query = query.where(ViewpointDefinition.level == level)
    if status:
        query = query.where(ViewpointDefinition.status == status)

    query = query.order_by(ViewpointDefinition.sort_order)

    # Paginate
    offset = (page - 1) * page_size
    total = (await db.execute(select(ViewpointDefinition))).scalars().all()
    total_count = len(total)

    result = await db.execute(query.offset(offset).limit(page_size))
    items = result.scalars().all()

    return {
        "data": [
            {
                "code": vp.code,
                "name_en": vp.name_en,
                "name_ar": vp.name_ar,
                "domain": vp.domain,
                "level": vp.level,
                "type": vp.type,
                "description_en": vp.description_en,
                "description_ar": vp.description_ar,
                "building_blocks": vp.building_blocks,
                "target_route": vp.target_route,
                "status": vp.status,
                "sort_order": vp.sort_order,
            }
            for vp in items
        ],
        "page": page,
        "page_size": page_size,
        "total": total_count,
    }


@router.get("/{code}", response_model=dict)
async def get_viewpoint(code: str, db: AsyncSession = Depends(get_db)):
    """Get a single viewpoint by code."""
    result = await db.execute(
        select(ViewpointDefinition).where(ViewpointDefinition.code == code)
    )
    vp = result.scalars().first()

    if not vp:
        raise HTTPException(status_code=404, detail=f"Viewpoint {code} not found")

    return {
        "code": vp.code,
        "name_en": vp.name_en,
        "name_ar": vp.name_ar,
        "domain": vp.domain,
        "level": vp.level,
        "type": vp.type,
        "description_en": vp.description_en,
        "description_ar": vp.description_ar,
        "building_blocks": vp.building_blocks,
        "target_route": vp.target_route,
        "status": vp.status,
        "sort_order": vp.sort_order,
    }
