from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import CurrentUser, get_current_user, get_db, get_optional_user
from app.models.schemas import InviteCreate, InviteOut, InviteResolve, MessageResponse
from app.services.event_service import create_invite, is_event_admin, resolve_invite_token

router = APIRouter(tags=["invites"])


@router.post(
    "/events/{event_id}/invites",
    response_model=InviteOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_event_invite(
    event_id: str,
    body: InviteCreate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    if not await is_event_admin(db, event_id, user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    invite = await create_invite(
        db,
        event_id=event_id,
        invite_type=body.invite_type.value,
        passcode=body.passcode,
    )
    invite["has_passcode"] = bool(invite.get("passcode_hash"))
    invite.pop("passcode_hash", None)
    return invite


@router.get("/events/{event_id}/invites", response_model=list[InviteOut])
async def list_event_invites(
    event_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    if not await is_event_admin(db, event_id, user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    result = (
        db.table("event_invites")
        .select("*")
        .eq("event_id", event_id)
        .order("created_at", desc=True)
        .execute()
    )
    invites = []
    for inv in result.data:
        inv["has_passcode"] = bool(inv.get("passcode_hash"))
        inv.pop("passcode_hash", None)
        invites.append(inv)
    return invites


@router.patch("/invites/{invite_id}", response_model=InviteOut)
async def toggle_invite(
    invite_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    invite = db.table("event_invites").select("*").eq("id", invite_id).maybe_single().execute()
    if not invite.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found")

    if not await is_event_admin(db, invite.data["event_id"], user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    new_active = not invite.data["is_active"]
    result = db.table("event_invites").update({"is_active": new_active}).eq("id", invite_id).execute()
    inv = result.data[0]
    inv["has_passcode"] = bool(inv.get("passcode_hash"))
    inv.pop("passcode_hash", None)
    return inv


@router.get("/join/{token}", response_model=InviteResolve)
async def resolve_token(
    token: str,
    db=Depends(get_db),
):
    """Public endpoint: resolve an invite token to event info and privacy mode."""
    invite = await resolve_invite_token(db, token)
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired invite link")

    event = invite.get("events", {})
    return InviteResolve(
        event_id=event["id"],
        event_name=event["name"],
        privacy_mode=event["privacy_mode"],
        requires_passcode=bool(invite.get("passcode_hash")),
    )
