from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import Settings
from app.core.dependencies import CurrentUser, get_config, get_current_user, get_db
from app.models.schemas import EventCreate, EventOut, EventUpdate, MessageResponse
from app.services.ai_service import delete_rekognition_collection
from app.services.event_service import (
    create_event,
    delete_event,
    get_event_detail,
    get_user_events,
    is_event_admin,
    update_event,
)

router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
async def create_new_event(
    body: EventCreate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    event = await create_event(
        db,
        user_id=user.id,
        name=body.name,
        event_type=body.event_type,
        start_time=body.start_time.isoformat() if body.start_time else None,
        end_time=body.end_time.isoformat() if body.end_time else None,
        privacy_mode=body.privacy_mode,
    )
    event["member_count"] = 1
    return event


@router.get("", response_model=list[EventOut])
async def list_my_events(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    return await get_user_events(db, user.id)


@router.get("/{event_id}", response_model=EventOut)
async def get_event(
    event_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    from app.services.event_service import is_approved_member

    if not await is_approved_member(db, event_id, user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this event")

    event = await get_event_detail(db, event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.patch("/{event_id}", response_model=EventOut)
async def update_event_settings(
    event_id: str,
    body: EventUpdate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    if not await is_event_admin(db, event_id, user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    return await update_event(db, event_id, updates)


@router.delete("/{event_id}", response_model=MessageResponse)
async def delete_event_endpoint(
    event_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
    settings: Settings = Depends(get_config),
):
    if not await is_event_admin(db, event_id, user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    await delete_rekognition_collection(settings, event_id)
    await delete_event(db, event_id)
    return MessageResponse(message="Event deleted successfully")
