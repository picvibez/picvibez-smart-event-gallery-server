from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import CurrentUser, get_current_user, get_db
from app.models.schemas import (
    FamilyTreeNode,
    MessageResponse,
    PersonCreate,
    PersonOut,
    PersonUpdate,
    RelationshipCreate,
    RelationshipOut,
)
from app.services.family_tree_service import (
    create_person,
    create_relationship,
    delete_relationship,
    get_family_tree,
    get_people_by_admin,
    update_person,
)

router = APIRouter(tags=["family_tree"])


@router.post("/people", response_model=PersonOut, status_code=status.HTTP_201_CREATED)
async def create_person_endpoint(
    body: PersonCreate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    person = await create_person(
        db,
        admin_id=user.id,
        first_name=body.first_name,
        last_name=body.last_name,
        date_of_birth=body.date_of_birth.isoformat() if body.date_of_birth else None,
        face_cluster_id=str(body.face_cluster_id) if body.face_cluster_id else None,
    )
    return person


@router.get("/people", response_model=list[PersonOut])
async def list_my_people(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    return await get_people_by_admin(db, user.id)


@router.patch("/people/{person_id}", response_model=PersonOut)
async def update_person_endpoint(
    person_id: str,
    body: PersonUpdate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    updates = body.model_dump(exclude_unset=True)
    if "date_of_birth" in updates and updates["date_of_birth"]:
        updates["date_of_birth"] = updates["date_of_birth"].isoformat()
    if "face_cluster_id" in updates and updates["face_cluster_id"]:
        updates["face_cluster_id"] = str(updates["face_cluster_id"])

    try:
        return await update_person(db, person_id, user.id, updates)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/relationships", response_model=RelationshipOut, status_code=status.HTTP_201_CREATED)
async def create_relationship_endpoint(
    body: RelationshipCreate,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    try:
        return await create_relationship(
            db,
            admin_id=user.id,
            person_id=str(body.person_id),
            related_person_id=str(body.related_person_id),
            relationship_type=body.relationship_type.value,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/relationships/{relationship_id}", response_model=MessageResponse)
async def delete_relationship_endpoint(
    relationship_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    try:
        await delete_relationship(db, relationship_id, user.id)
        return MessageResponse(message="Relationship deleted")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/people/{person_id}/tree", response_model=list[FamilyTreeNode])
async def get_family_tree_endpoint(
    person_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
):
    person = db.table("people").select("managed_by_admin_id").eq("id", person_id).maybe_single().execute()
    if not person.data or person.data["managed_by_admin_id"] != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your person")

    return await get_family_tree(db, person_id)
