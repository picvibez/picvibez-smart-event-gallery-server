from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_db
from app.models.enums import VendorCategory
from app.models.schemas import VendorOut

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.get("", response_model=list[VendorOut])
async def list_vendors(
    db=Depends(get_db),
    q: str | None = Query(None, max_length=200),
    category: VendorCategory | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    query = db.table("vendors").select("*")

    if q:
        query = query.ilike("name", f"%{q}%")
    if category:
        query = query.eq("category", category.value)

    result = (
        query
        .order("rating", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data


@router.get("/{vendor_id}", response_model=VendorOut)
async def get_vendor(
    vendor_id: str,
    db=Depends(get_db),
):
    result = db.table("vendors").select("*").eq("id", vendor_id).maybe_single().execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return result.data
