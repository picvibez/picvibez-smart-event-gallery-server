from __future__ import annotations

import logging
from uuid import uuid4

from supabase import Client

from app.core.config import Settings
from app.integrations.aws import get_s3_client
from app.models.enums import MemberStatus

logger = logging.getLogger("picvibez.media")


async def check_storage_quota(
    db: Client, event_id: str, file_size_bytes: int
) -> tuple[bool, int, int]:
    """Returns (allowed, current_bytes, limit_bytes)."""
    result = (
        db.table("events")
        .select("current_storage_bytes, storage_limit_bytes")
        .eq("id", event_id)
        .single()
        .execute()
    )
    event = result.data
    current = event["current_storage_bytes"] or 0
    limit = event["storage_limit_bytes"] or 0
    return (current + file_size_bytes) <= limit, current, limit


async def generate_presigned_upload(
    settings: Settings,
    *,
    event_id: str,
    file_name: str,
    media_type: str,
) -> tuple[str, str, str]:
    """Generate a presigned PUT URL for direct S3 upload.

    Returns (upload_url, s3_key, cdn_url).
    """
    s3 = get_s3_client()
    ext = file_name.rsplit(".", 1)[-1] if "." in file_name else "bin"
    s3_key = f"events/{event_id}/originals/{uuid4()}.{ext}"

    content_type = f"{media_type}/{ext}" if ext in ("jpg", "jpeg", "png", "webp", "gif", "mp4", "mov") else "application/octet-stream"

    upload_url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.S3_MEDIA_BUCKET,
            "Key": s3_key,
            "ContentType": content_type,
        },
        ExpiresIn=300,
    )

    cdn_url = f"https://{settings.CLOUDFRONT_DOMAIN}/{s3_key}" if settings.CLOUDFRONT_DOMAIN else upload_url.split("?")[0]

    return upload_url, s3_key, cdn_url


async def confirm_upload(
    db: Client,
    *,
    event_id: str,
    uploader_id: str,
    s3_key: str,
    file_name: str,
    file_size_bytes: int,
    media_type: str,
    captured_at: str | None = None,
    cdn_url: str = "",
) -> dict:
    data = {
        "event_id": event_id,
        "uploader_id": uploader_id,
        "s3_key": s3_key,
        "cdn_url": cdn_url,
        "file_name": file_name,
        "file_size_bytes": file_size_bytes,
        "media_type": media_type,
        "is_approved": True,
    }
    if captured_at:
        data["captured_at"] = captured_at

    result = db.table("media").insert(data).execute()
    media = result.data[0]
    logger.info("Media confirmed: %s for event %s (%d bytes)", media["id"], event_id, file_size_bytes)
    return media


async def list_media(
    db: Client,
    *,
    event_id: str,
    user_id: str,
    cursor: str | None = None,
    limit: int = 30,
    media_type: str | None = None,
    uploader_id: str | None = None,
    cluster_id: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    is_admin: bool = False,
) -> list[dict]:
    query = db.table("media").select(
        "*, profiles!media_uploader_id_fkey(display_name, avatar_url)"
    ).eq("event_id", event_id)

    if not is_admin:
        query = query.eq("is_approved", True)

    if media_type:
        query = query.eq("media_type", media_type)
    if uploader_id:
        query = query.eq("uploader_id", uploader_id)

    if cluster_id:
        face_result = (
            db.table("media_faces")
            .select("media_id")
            .eq("cluster_id", cluster_id)
            .execute()
        )
        media_ids = [r["media_id"] for r in face_result.data] if face_result.data else []
        if not media_ids:
            return []
        query = query.in_("id", media_ids)

    desc = sort_order == "desc"
    query = query.order(sort_by, desc=desc)

    if cursor:
        if desc:
            query = query.lt(sort_by, cursor)
        else:
            query = query.gt(sort_by, cursor)

    query = query.limit(limit)
    result = query.execute()

    media_list = []
    for row in result.data:
        profile = row.pop("profiles", None) or {}
        row["uploader_name"] = profile.get("display_name")
        row["uploader_avatar"] = profile.get("avatar_url")
        row["thumbnail_url"] = (
            row.get("cdn_url", "").replace("/originals/", "/thumbs/").rsplit(".", 1)[0] + ".webp"
            if row.get("thumbnail_key")
            else None
        )
        media_list.append(row)

    return media_list


async def approve_media(db: Client, media_id: str) -> dict:
    result = db.table("media").update({"is_approved": True}).eq("id", media_id).execute()
    return result.data[0]


async def delete_media(db: Client, settings: Settings, media_id: str) -> None:
    media_result = db.table("media").select("s3_key, thumbnail_key, event_id").eq("id", media_id).single().execute()
    media = media_result.data

    s3 = get_s3_client()
    keys_to_delete = [{"Key": media["s3_key"]}]
    if media.get("thumbnail_key"):
        keys_to_delete.append({"Key": media["thumbnail_key"]})

    s3.delete_objects(
        Bucket=settings.S3_MEDIA_BUCKET,
        Delete={"Objects": keys_to_delete},
    )

    db.table("media_faces").delete().eq("media_id", media_id).execute()
    db.table("media_likes").delete().eq("media_id", media_id).execute()
    db.table("media_comments").delete().eq("media_id", media_id).execute()
    db.table("media").delete().eq("id", media_id).execute()

    logger.info("Media deleted: %s from event %s", media_id, media["event_id"])
