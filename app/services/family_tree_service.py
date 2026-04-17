from __future__ import annotations

import logging

from supabase import Client

logger = logging.getLogger("picvibez.family_tree")


async def create_person(
    db: Client,
    *,
    admin_id: str,
    first_name: str,
    last_name: str | None = None,
    date_of_birth: str | None = None,
    face_cluster_id: str | None = None,
) -> dict:
    data = {
        "first_name": first_name,
        "managed_by_admin_id": admin_id,
    }
    if last_name:
        data["last_name"] = last_name
    if date_of_birth:
        data["date_of_birth"] = date_of_birth
    if face_cluster_id:
        data["face_cluster_id"] = face_cluster_id

    result = db.table("people").insert(data).execute()
    return result.data[0]


async def update_person(db: Client, person_id: str, admin_id: str, updates: dict) -> dict:
    clean = {k: v for k, v in updates.items() if v is not None}
    result = (
        db.table("people")
        .update(clean)
        .eq("id", person_id)
        .eq("managed_by_admin_id", admin_id)
        .execute()
    )
    if not result.data:
        raise ValueError("Person not found or not managed by you")
    return result.data[0]


async def create_relationship(
    db: Client,
    *,
    admin_id: str,
    person_id: str,
    related_person_id: str,
    relationship_type: str,
) -> dict:
    person = db.table("people").select("id").eq("id", person_id).eq("managed_by_admin_id", admin_id).maybe_single().execute()
    related = db.table("people").select("id").eq("id", related_person_id).eq("managed_by_admin_id", admin_id).maybe_single().execute()
    if not person.data or not related.data:
        raise ValueError("Both people must be managed by you")

    result = db.table("relationships").insert({
        "person_id": person_id,
        "related_person_id": related_person_id,
        "relationship_type": relationship_type,
    }).execute()
    return result.data[0]


async def delete_relationship(db: Client, relationship_id: str, admin_id: str) -> None:
    rel = db.table("relationships").select("*, people!relationships_person_id_fkey(managed_by_admin_id)").eq("id", relationship_id).maybe_single().execute()
    if not rel.data:
        raise ValueError("Relationship not found")
    db.table("relationships").delete().eq("id", relationship_id).execute()


async def get_family_tree(db: Client, person_id: str) -> list[dict]:
    """Call the recursive CTE RPC function."""
    result = db.rpc("get_family_tree", {"starting_person_id": person_id}).execute()
    return result.data or []


async def get_people_by_admin(db: Client, admin_id: str) -> list[dict]:
    result = db.table("people").select("*").eq("managed_by_admin_id", admin_id).order("first_name").execute()
    return result.data or []
