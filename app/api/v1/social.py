from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.models.schemas import CommentCreate, CommentOut, MessageResponse

router = APIRouter(prefix="/media/{media_id}", tags=["social"])


def _assert_media_exists(db, media_id: str) -> dict:
    result = db.table("media").select("event_id").eq("id", media_id).maybe_single().execute()
    if not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
    return result.data


async def _check_member(db, event_id: str, user_id: str) -> None:
    from app.services.event_service import is_approved_member

    if not await is_approved_member(db, event_id, user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an approved member")


@router.post("/like", response_model=MessageResponse)
async def toggle_like(
    media_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    media = _assert_media_exists(db, media_id)
    await _check_member(db, media["event_id"], user.id)

    existing = (
        db.table("media_likes")
        .select("media_id")
        .eq("media_id", media_id)
        .eq("user_id", user.id)
        .maybe_single()
        .execute()
    )

    if existing.data:
        db.table("media_likes").delete().eq("media_id", media_id).eq("user_id", user.id).execute()
        return MessageResponse(message="Like removed")
    else:
        db.table("media_likes").insert({"media_id": media_id, "user_id": user.id}).execute()
        return MessageResponse(message="Liked")


@router.get("/comments", response_model=list[CommentOut])
async def list_comments(
    media_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    media = _assert_media_exists(db, media_id)
    await _check_member(db, media["event_id"], user.id)

    result = (
        db.table("media_comments")
        .select("*, profiles(display_name, avatar_url)")
        .eq("media_id", media_id)
        .order("created_at", desc=False)
        .range(offset, offset + limit - 1)
        .execute()
    )

    comments = []
    for row in result.data:
        profile = row.pop("profiles", None) or {}
        row["display_name"] = profile.get("display_name")
        row["avatar_url"] = profile.get("avatar_url")
        comments.append(row)
    return comments


@router.post("/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
async def add_comment(
    media_id: str,
    body: CommentCreate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    media = _assert_media_exists(db, media_id)
    await _check_member(db, media["event_id"], user.id)

    result = db.table("media_comments").insert({
        "media_id": media_id,
        "user_id": user.id,
        "comment_text": body.comment_text,
    }).execute()
    return result.data[0]


@router.delete("/comments/{comment_id}", response_model=MessageResponse)
async def delete_comment(
    media_id: str,
    comment_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    comment = db.table("media_comments").select("user_id").eq("id", comment_id).maybe_single().execute()
    if not comment.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    if comment.data["user_id"] != user.id:
        media = _assert_media_exists(db, media_id)
        from app.services.event_service import is_event_admin

        if not await is_event_admin(db, media["event_id"], user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only delete your own comments")

    db.table("media_comments").delete().eq("id", comment_id).execute()
    return MessageResponse(message="Comment deleted")
