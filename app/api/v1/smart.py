from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.models.schemas import ClusterLinkRequest, FaceClusterOut, MediaOut, SearchResult
from app.services.ai_service import get_find_me_media, search_media_by_labels
from app.services.event_service import is_approved_member, is_event_admin
from app.services.media_service import list_media

router = APIRouter(tags=["smart"])


@router.get("/events/{event_id}/find-me", response_model=list[MediaOut])
async def find_me(
    event_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    """Return all photos where the current user's face was detected."""
    if not await is_approved_member(db, event_id, user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an approved member")

    media_ids = await get_find_me_media(db, event_id, user.id)
    if not media_ids:
        return []

    result = (
        db.table("media")
        .select("*, profiles!media_uploader_id_fkey(display_name, avatar_url)")
        .in_("id", media_ids)
        .eq("is_approved", True)
        .order("created_at", desc=True)
        .execute()
    )

    items = []
    for row in result.data:
        profile = row.pop("profiles", None) or {}
        row["uploader_name"] = profile.get("display_name")
        row["uploader_avatar"] = profile.get("avatar_url")
        items.append(row)
    return items


@router.get("/events/{event_id}/search", response_model=SearchResult)
async def semantic_search(
    event_id: str,
    q: str = Query(..., min_length=1, max_length=200),
    user: Annotated[CurrentUser, Depends(get_current_user)] = None,
    db=Depends(get_db),
):
    if not await is_approved_member(db, event_id, user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an approved member")

    media_ids = await search_media_by_labels(db, event_id, q)
    if not media_ids:
        return SearchResult(media=[], query=q, total=0)

    result = (
        db.table("media")
        .select("*, profiles!media_uploader_id_fkey(display_name, avatar_url)")
        .in_("id", media_ids)
        .order("created_at", desc=True)
        .execute()
    )

    items = []
    for row in result.data:
        profile = row.pop("profiles", None) or {}
        row["uploader_name"] = profile.get("display_name")
        row["uploader_avatar"] = profile.get("avatar_url")
        items.append(row)

    return SearchResult(media=items, query=q, total=len(items))


@router.get("/events/{event_id}/faces", response_model=list[FaceClusterOut])
async def list_face_clusters(
    event_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    if not await is_approved_member(db, event_id, user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not an approved member")

    clusters = (
        db.table("ai_face_clusters")
        .select("*, people(first_name, last_name)")
        .eq("event_id", event_id)
        .execute()
    )

    result = []
    for c in clusters.data:
        person = c.pop("people", None) or {}
        c["person_name"] = f"{person.get('first_name', '')} {person.get('last_name', '')}".strip() or None

        face_count = (
            db.table("media_faces")
            .select("id", count="exact")
            .eq("cluster_id", c["id"])
            .execute()
        )
        c["photo_count"] = face_count.count or 0
        result.append(c)

    return result


@router.patch("/faces/{cluster_id}", response_model=FaceClusterOut)
async def link_cluster_to_person(
    cluster_id: str,
    body: ClusterLinkRequest,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    """Link a face cluster to a person node (admin only)."""
    cluster = db.table("ai_face_clusters").select("event_id").eq("id", cluster_id).maybe_single().execute()
    if not cluster.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found")

    if not await is_event_admin(db, cluster.data["event_id"], user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    result = (
        db.table("ai_face_clusters")
        .update({"person_id": str(body.person_id)})
        .eq("id", cluster_id)
        .execute()
    )
    updated = result.data[0]
    updated["photo_count"] = 0
    return updated
