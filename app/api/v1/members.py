from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.models.enums import MemberRole, MemberStatus, PrivacyMode
from app.models.schemas import JoinRequest, MemberOut, MemberUpdate, MessageResponse
from app.services.event_service import (
    is_approved_member,
    is_event_admin,
    join_event,
    resolve_invite_token,
    verify_passcode,
)

router = APIRouter(prefix="/events/{event_id}/members", tags=["members"])


@router.post("", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
async def join_event_endpoint(
    event_id: str,
    body: JoinRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    invite = await resolve_invite_token(db, str(body.token))
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite link")

    event = invite.get("events", {})
    if event["id"] != event_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invite does not match this event")

    privacy = event.get("privacy_mode", PrivacyMode.PUBLIC.value)

    if privacy == PrivacyMode.PASSCODE.value:
        if not body.passcode:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passcode required for this event",
            )
        if not invite.get("passcode_hash") or not verify_passcode(body.passcode, invite["passcode_hash"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid passcode",
            )
        join_status = MemberStatus.APPROVED
    elif privacy == PrivacyMode.APPROVAL.value:
        join_status = MemberStatus.PENDING
    else:
        join_status = MemberStatus.APPROVED

    member = await join_event(
        db,
        event_id=event_id,
        user_id=user.id,
        invite_id=invite["id"],
        status=join_status,
    )
    return member


@router.get("", response_model=list[MemberOut])
async def list_members(
    event_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    if not await is_approved_member(db, event_id, user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member")

    admin = await is_event_admin(db, event_id, user.id)

    query = (
        db.table("event_members")
        .select("*, profiles(display_name, avatar_url)")
        .eq("event_id", event_id)
    )
    if not admin:
        query = query.eq("status", MemberStatus.APPROVED.value)

    result = query.order("role").execute()

    members = []
    for row in result.data:
        profile = row.pop("profiles", None) or {}
        row["display_name"] = profile.get("display_name")
        row["avatar_url"] = profile.get("avatar_url")
        members.append(row)
    return members


@router.patch("/{member_id}", response_model=MemberOut)
async def update_member(
    event_id: str,
    member_id: str,
    body: MemberUpdate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    if not await is_event_admin(db, event_id, user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    result = (
        db.table("event_members")
        .update(updates)
        .eq("event_id", event_id)
        .eq("profile_id", member_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return result.data[0]


@router.delete("/{member_id}", response_model=MessageResponse)
async def remove_member(
    event_id: str,
    member_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    is_self = member_id == user.id
    if not is_self and not await is_event_admin(db, event_id, user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    db.table("event_members").delete().eq("event_id", event_id).eq("profile_id", member_id).execute()
    action = "left" if is_self else "removed"
    return MessageResponse(message=f"Member {action} successfully")
