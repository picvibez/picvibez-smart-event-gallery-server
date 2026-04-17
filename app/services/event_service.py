from __future__ import annotations

import hashlib
import logging
from uuid import UUID, uuid4

import bcrypt
from supabase import Client

from app.models.enums import MemberRole, MemberStatus, PrivacyMode

logger = logging.getLogger("picvibez.events")

DEFAULT_STORAGE_LIMIT = 536_870_912  # 500 MB


async def create_event(
    db: Client,
    *,
    user_id: str,
    name: str,
    event_type: str,
    start_time: str | None,
    end_time: str | None,
    privacy_mode: PrivacyMode,
) -> dict:
    event_data = {
        "name": name,
        "event_type": event_type,
        "privacy_mode": privacy_mode.value,
        "storage_limit_bytes": DEFAULT_STORAGE_LIMIT,
        "current_storage_bytes": 0,
        "is_watermark_enabled": True,
        "created_by": user_id,
    }
    if start_time:
        event_data["start_time"] = start_time
    if end_time:
        event_data["end_time"] = end_time

    result = db.table("events").insert(event_data).execute()
    event = result.data[0]

    db.table("event_members").insert({
        "event_id": event["id"],
        "profile_id": user_id,
        "role": MemberRole.ADMIN.value,
        "status": MemberStatus.APPROVED.value,
    }).execute()

    invite_token = str(uuid4())
    db.table("event_invites").insert({
        "event_id": event["id"],
        "invite_type": "link",
        "token": invite_token,
        "is_active": True,
    }).execute()

    logger.info("Event created: %s by user %s", event["id"], user_id)
    return event


async def get_user_events(db: Client, user_id: str) -> list[dict]:
    result = (
        db.table("event_members")
        .select("event_id, events(*)")
        .eq("profile_id", user_id)
        .eq("status", MemberStatus.APPROVED.value)
        .execute()
    )
    events = []
    for row in result.data:
        event = row.get("events")
        if event:
            count_result = (
                db.table("event_members")
                .select("profile_id", count="exact")
                .eq("event_id", event["id"])
                .eq("status", MemberStatus.APPROVED.value)
                .execute()
            )
            event["member_count"] = count_result.count or 0
            events.append(event)
    return events


async def get_event_detail(db: Client, event_id: str) -> dict | None:
    result = db.table("events").select("*").eq("id", event_id).maybe_single().execute()
    if not result.data:
        return None
    event = result.data
    count_result = (
        db.table("event_members")
        .select("profile_id", count="exact")
        .eq("event_id", event_id)
        .eq("status", MemberStatus.APPROVED.value)
        .execute()
    )
    event["member_count"] = count_result.count or 0
    return event


async def update_event(db: Client, event_id: str, updates: dict) -> dict:
    clean = {k: v for k, v in updates.items() if v is not None}
    result = db.table("events").update(clean).eq("id", event_id).execute()
    return result.data[0]


async def delete_event(db: Client, event_id: str) -> None:
    db.table("media_faces").delete().in_(
        "media_id",
        db.table("media").select("id").eq("event_id", event_id).execute().data
        and [r["id"] for r in db.table("media").select("id").eq("event_id", event_id).execute().data]
        or [],
    ).execute()
    db.table("media_likes").delete().in_(
        "media_id",
        [r["id"] for r in db.table("media").select("id").eq("event_id", event_id).execute().data]
        or ["00000000-0000-0000-0000-000000000000"],
    ).execute()
    db.table("media_comments").delete().in_(
        "media_id",
        [r["id"] for r in db.table("media").select("id").eq("event_id", event_id).execute().data]
        or ["00000000-0000-0000-0000-000000000000"],
    ).execute()
    db.table("ai_face_clusters").delete().eq("event_id", event_id).execute()
    db.table("media").delete().eq("event_id", event_id).execute()
    db.table("event_guests_metadata").delete().eq("event_id", event_id).execute()
    db.table("event_members").delete().eq("event_id", event_id).execute()
    db.table("event_invites").delete().eq("event_id", event_id).execute()
    db.table("transactions").delete().eq("event_id", event_id).execute()
    db.table("events").delete().eq("id", event_id).execute()
    logger.info("Event deleted: %s", event_id)


async def is_event_admin(db: Client, event_id: str, user_id: str) -> bool:
    result = (
        db.table("event_members")
        .select("role")
        .eq("event_id", event_id)
        .eq("profile_id", user_id)
        .eq("status", MemberStatus.APPROVED.value)
        .maybe_single()
        .execute()
    )
    return result.data is not None and result.data.get("role") == MemberRole.ADMIN.value


async def is_approved_member(db: Client, event_id: str, user_id: str) -> bool:
    result = (
        db.table("event_members")
        .select("status")
        .eq("event_id", event_id)
        .eq("profile_id", user_id)
        .eq("status", MemberStatus.APPROVED.value)
        .maybe_single()
        .execute()
    )
    return result.data is not None


# ── Invite helpers ──


def hash_passcode(passcode: str) -> str:
    return bcrypt.hashpw(passcode.encode(), bcrypt.gensalt()).decode()


def verify_passcode(passcode: str, hashed: str) -> bool:
    return bcrypt.checkpw(passcode.encode(), hashed.encode())


async def create_invite(
    db: Client,
    *,
    event_id: str,
    invite_type: str,
    passcode: str | None = None,
) -> dict:
    data: dict = {
        "event_id": event_id,
        "invite_type": invite_type,
        "token": str(uuid4()),
        "is_active": True,
    }
    if passcode:
        data["passcode_hash"] = hash_passcode(passcode)

    result = db.table("event_invites").insert(data).execute()
    return result.data[0]


async def resolve_invite_token(db: Client, token: str) -> dict | None:
    result = (
        db.table("event_invites")
        .select("*, events(id, name, privacy_mode)")
        .eq("token", token)
        .eq("is_active", True)
        .maybe_single()
        .execute()
    )
    return result.data


async def join_event(
    db: Client,
    *,
    event_id: str,
    user_id: str,
    invite_id: str | None = None,
    status: MemberStatus = MemberStatus.APPROVED,
    role: MemberRole = MemberRole.GUEST,
) -> dict:
    existing = (
        db.table("event_members")
        .select("*")
        .eq("event_id", event_id)
        .eq("profile_id", user_id)
        .maybe_single()
        .execute()
    )
    if existing.data:
        return existing.data

    data = {
        "event_id": event_id,
        "profile_id": user_id,
        "role": role.value,
        "status": status.value,
    }
    if invite_id:
        data["joined_via_invite_id"] = invite_id

    result = db.table("event_members").insert(data).execute()

    if invite_id:
        db.rpc("increment_invite_usage", {"invite_id_param": invite_id}).execute()

    logger.info("User %s joined event %s with status %s", user_id, event_id, status.value)
    return result.data[0]
