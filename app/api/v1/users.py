from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.models.schemas import ProfileOut, ProfileUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=ProfileOut)
async def get_my_profile(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    result = db.table("profiles").select("*").eq("id", user.id).maybe_single().execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return result.data


@router.patch("/me", response_model=ProfileOut)
async def update_my_profile(
    body: ProfileUpdate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    result = db.table("profiles").update(updates).eq("id", user.id).execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return result.data[0]
