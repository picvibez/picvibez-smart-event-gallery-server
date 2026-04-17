from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.core.config import Settings
from app.core.dependencies import CurrentUser, get_config, get_current_user, get_db
from app.integrations.aws import get_s3_client
from app.models.schemas import MessageResponse, ProfileOut
from app.services.ai_service import ensure_rekognition_collection, index_selfie

logger = logging.getLogger("picvibez.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/selfie", response_model=ProfileOut)
async def upload_selfie(
    file: UploadFile,
    event_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    db=Depends(get_db),
    settings: Settings = Depends(get_config),
):
    """Upload a reference selfie for facial recognition.

    The selfie is stored in S3, indexed in AWS Rekognition, and the
    resulting FaceId is saved to the user's profile.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image",
        )

    contents = await file.read()
    if len(contents) > 10_000_000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selfie must be under 10MB",
        )

    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "jpg"
    s3_key = f"selfies/{user.id}/{event_id}.{ext}"

    s3 = get_s3_client()
    s3.put_object(
        Bucket=settings.S3_MEDIA_BUCKET,
        Key=s3_key,
        Body=contents,
        ContentType=file.content_type or "image/jpeg",
    )

    face_id = await index_selfie(
        settings,
        db,
        user_id=user.id,
        event_id=event_id,
        s3_key=s3_key,
    )

    if not face_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No face detected in the selfie. Please try again with a clear face photo.",
        )

    db.table("profiles").update({"face_embedding_id": face_id}).eq("id", user.id).execute()

    result = db.table("profiles").select("*").eq("id", user.id).single().execute()
    return result.data
