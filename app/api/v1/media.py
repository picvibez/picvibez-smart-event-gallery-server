from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.config import Settings
from app.core.dependencies import CurrentUser, get_config, get_current_user, get_db
from app.models.enums import MediaType
from app.models.schemas import (
    MediaConfirm,
    MediaOut,
    MessageResponse,
    PresignRequest,
    PresignResponse,
)
from app.services.event_service import is_approved_member, is_event_admin
from app.services.media_service import (
    approve_media,
    check_storage_quota,
    confirm_upload,
    delete_media,
    generate_presigned_upload,
    list_media,
)

router = APIRouter(tags=["media"])


@router.post(
    "/events/{event_id}/media/presign",
    response_model=PresignResponse,
)
async def get_presigned_url(
    event_id: str,
    body: PresignRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
    settings: Settings = Depends(get_config),
):
    if not await is_approved_member(db, event_id, user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an approved member")

    allowed, current, limit = await check_storage_quota(db, event_id, body.file_size_bytes)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Storage quota exceeded. Used {current:,} of {limit:,} bytes.",
        )

    upload_url, s3_key, cdn_url = await generate_presigned_upload(
        settings,
        event_id=event_id,
        file_name=body.file_name,
        media_type=body.media_type.value,
    )

    return PresignResponse(upload_url=upload_url, s3_key=s3_key, cdn_url=cdn_url)


@router.post(
    "/events/{event_id}/media/confirm",
    response_model=MediaOut,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_media_upload(
    event_id: str,
    body: MediaConfirm,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
    settings: Settings = Depends(get_config),
):
    if not await is_approved_member(db, event_id, user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an approved member")

    cdn_url = f"https://{settings.CLOUDFRONT_DOMAIN}/{body.s3_key}" if settings.CLOUDFRONT_DOMAIN else ""

    media = await confirm_upload(
        db,
        event_id=event_id,
        uploader_id=user.id,
        s3_key=body.s3_key,
        file_name=body.file_name,
        file_size_bytes=body.file_size_bytes,
        media_type=body.media_type.value,
        captured_at=body.captured_at.isoformat() if body.captured_at else None,
        cdn_url=cdn_url,
    )
    return media


@router.get("/events/{event_id}/media", response_model=list[MediaOut])
async def list_event_media(
    event_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
    cursor: str | None = Query(None),
    limit: int = Query(30, ge=1, le=100),
    media_type: MediaType | None = Query(None),
    uploader_id: str | None = Query(None),
    cluster_id: str | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
):
    if not await is_approved_member(db, event_id, user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an approved member")

    admin = await is_event_admin(db, event_id, user.id)

    return await list_media(
        db,
        event_id=event_id,
        user_id=user.id,
        cursor=cursor,
        limit=limit,
        media_type=media_type.value if media_type else None,
        uploader_id=uploader_id,
        cluster_id=cluster_id,
        sort_by=sort_by,
        sort_order=sort_order,
        is_admin=admin,
    )


@router.patch("/media/{media_id}/approve", response_model=MediaOut)
async def approve_media_endpoint(
    media_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    media_result = db.table("media").select("event_id").eq("id", media_id).maybe_single().execute()
    if not media_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    if not await is_event_admin(db, media_result.data["event_id"], user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    return await approve_media(db, media_id)


@router.delete("/media/{media_id}", response_model=MessageResponse)
async def delete_media_endpoint(
    media_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
    settings: Settings = Depends(get_config),
):
    media_result = db.table("media").select("event_id, uploader_id").eq("id", media_id).maybe_single().execute()
    if not media_result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    event_id = media_result.data["event_id"]
    is_uploader = media_result.data["uploader_id"] == user.id
    admin = await is_event_admin(db, event_id, user.id)

    if not is_uploader and not admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the uploader or admin can delete")

    await delete_media(db, settings, media_id)
    return MessageResponse(message="Media deleted successfully")
