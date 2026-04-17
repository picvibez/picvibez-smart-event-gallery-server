from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.models.schemas import GuestMetadataOut, GuestMetadataUpsert
from app.services.event_service import is_event_admin

router = APIRouter(prefix="/events/{event_id}/guests", tags=["admin_secrets"])


@router.get("", response_model=list[GuestMetadataOut])
async def list_guest_metadata(
    event_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    if not await is_event_admin(db, event_id, user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    result = (
        db.table("event_guests_metadata")
        .select("*, people(first_name, last_name)")
        .eq("event_id", event_id)
        .execute()
    )

    items = []
    for row in result.data:
        person = row.pop("people", None) or {}
        row["person_name"] = f"{person.get('first_name', '')} {person.get('last_name', '')}".strip() or None
        items.append(row)
    return items


@router.put("/{person_id}", response_model=GuestMetadataOut)
async def upsert_guest_metadata(
    event_id: str,
    person_id: str,
    body: GuestMetadataUpsert,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    if not await is_event_admin(db, event_id, user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    data = body.model_dump(exclude_unset=True)
    data["event_id"] = event_id
    data["person_id"] = person_id

    result = (
        db.table("event_guests_metadata")
        .upsert(data, on_conflict="event_id,person_id")
        .execute()
    )
    return result.data[0]
