from __future__ import annotations

import json
import logging

from supabase import Client

from app.core.config import Settings
from app.integrations.aws import get_rekognition_client, get_s3_client
from app.integrations.gemini_client import get_gemini_client

logger = logging.getLogger("picvibez.ai")


def _collection_id(settings: Settings, event_id: str) -> str:
    return f"{settings.REKOGNITION_COLLECTION_PREFIX}{event_id.replace('-', '')}"


async def ensure_rekognition_collection(settings: Settings, event_id: str) -> str:
    """Create a Rekognition collection for the event if it doesn't exist."""
    rekog = get_rekognition_client()
    collection_id = _collection_id(settings, event_id)
    try:
        rekog.create_collection(CollectionId=collection_id)
        logger.info("Created Rekognition collection: %s", collection_id)
    except rekog.exceptions.ResourceAlreadyExistsException:
        pass
    return collection_id


async def index_selfie(
    settings: Settings,
    db: Client,
    *,
    user_id: str,
    event_id: str,
    s3_key: str,
) -> str | None:
    """Index a selfie into the event's Rekognition collection.

    Returns the FaceId on success, None on failure.
    """
    rekog = get_rekognition_client()
    collection_id = await ensure_rekognition_collection(settings, event_id)

    try:
        response = rekog.index_faces(
            CollectionId=collection_id,
            Image={"S3Object": {"Bucket": settings.S3_MEDIA_BUCKET, "Name": s3_key}},
            ExternalImageId=user_id,
            MaxFaces=1,
            QualityFilter="AUTO",
            DetectionAttributes=["DEFAULT"],
        )
    except Exception:
        logger.exception("Failed to index selfie for user %s", user_id)
        return None

    face_records = response.get("FaceRecords", [])
    if not face_records:
        logger.warning("No face detected in selfie for user %s", user_id)
        return None

    face_id = face_records[0]["Face"]["FaceId"]
    logger.info("Indexed selfie for user %s -> FaceId %s", user_id, face_id)
    return face_id


async def search_faces_in_photo(
    settings: Settings,
    *,
    event_id: str,
    s3_key: str,
    max_faces: int = 10,
) -> list[dict]:
    """Search for known faces in a photo.

    Returns list of {face_id, external_image_id, confidence, bounding_box}.
    """
    rekog = get_rekognition_client()
    collection_id = _collection_id(settings, event_id)

    try:
        detect_response = rekog.detect_faces(
            Image={"S3Object": {"Bucket": settings.S3_MEDIA_BUCKET, "Name": s3_key}},
            Attributes=["DEFAULT"],
        )
    except Exception:
        logger.exception("Face detection failed for %s", s3_key)
        return []

    results = []
    for face_detail in detect_response.get("FaceDetails", [])[:max_faces]:
        bbox = face_detail["BoundingBox"]
        try:
            search_response = rekog.search_faces_by_image(
                CollectionId=collection_id,
                Image={"S3Object": {"Bucket": settings.S3_MEDIA_BUCKET, "Name": s3_key}},
                MaxFaces=5,
                FaceMatchThreshold=80.0,
            )
            for match in search_response.get("FaceMatches", []):
                results.append({
                    "face_id": match["Face"]["FaceId"],
                    "external_image_id": match["Face"].get("ExternalImageId"),
                    "confidence": match["Similarity"],
                    "bounding_box": {
                        "left": bbox["Left"],
                        "top": bbox["Top"],
                        "width": bbox["Width"],
                        "height": bbox["Height"],
                    },
                })
        except rekog.exceptions.InvalidParameterException:
            continue
        except Exception:
            logger.exception("Face search failed for %s", s3_key)
            continue

    return results


async def generate_semantic_labels(s3_key: str, cdn_url: str) -> list[str]:
    """Use Gemini to generate descriptive tags for a photo."""
    client = get_gemini_client()
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {"text": (
                            "Analyze this event photo and return ONLY a JSON array of "
                            "descriptive English tags (5-15 tags). Include people descriptions, "
                            "activities, setting, mood, colors, and objects. "
                            "Example: [\"bride\", \"groom\", \"dance floor\", \"outdoor\", \"sunset\"]. "
                            "Return ONLY the JSON array, nothing else."
                        )},
                        {"file_data": {"file_uri": cdn_url, "mime_type": "image/jpeg"}},
                    ],
                }
            ],
        )
        text = response.text.strip()
        if text.startswith("["):
            return json.loads(text)
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            return json.loads(text[start : end + 1])
    except Exception:
        logger.exception("Gemini labeling failed for %s", s3_key)

    return []


async def delete_rekognition_collection(settings: Settings, event_id: str) -> None:
    rekog = get_rekognition_client()
    collection_id = _collection_id(settings, event_id)
    try:
        rekog.delete_collection(CollectionId=collection_id)
        logger.info("Deleted Rekognition collection: %s", collection_id)
    except Exception:
        logger.warning("Failed to delete Rekognition collection: %s", collection_id)


async def get_find_me_media(db: Client, event_id: str, user_id: str) -> list[str]:
    """Get media IDs where the user's face was detected."""
    profile = db.table("profiles").select("face_embedding_id").eq("id", user_id).maybe_single().execute()
    if not profile.data or not profile.data.get("face_embedding_id"):
        return []

    face_embedding_id = profile.data["face_embedding_id"]

    clusters = (
        db.table("ai_face_clusters")
        .select("id")
        .eq("event_id", event_id)
        .execute()
    )
    if not clusters.data:
        return []

    cluster_ids = [c["id"] for c in clusters.data]

    person_result = (
        db.table("profiles")
        .select("person_id")
        .eq("id", user_id)
        .maybe_single()
        .execute()
    )
    person_id = person_result.data.get("person_id") if person_result.data else None

    if person_id:
        matched_clusters = (
            db.table("ai_face_clusters")
            .select("id")
            .eq("event_id", event_id)
            .eq("person_id", person_id)
            .execute()
        )
    else:
        matched_clusters = {"data": []}

    if not matched_clusters.data if isinstance(matched_clusters, dict) else not matched_clusters.data:
        return []

    matched_cluster_ids = [c["id"] for c in (matched_clusters.data if hasattr(matched_clusters, 'data') else matched_clusters["data"])]

    faces = (
        db.table("media_faces")
        .select("media_id")
        .in_("cluster_id", matched_cluster_ids)
        .execute()
    )
    return list({f["media_id"] for f in faces.data}) if faces.data else []


async def search_media_by_labels(db: Client, event_id: str, query: str) -> list[str]:
    """Search media by AI-generated labels using JSONB containment."""
    terms = [t.strip().lower() for t in query.split() if t.strip()]
    if not terms:
        return []

    all_media = (
        db.table("media")
        .select("id, ai_labels")
        .eq("event_id", event_id)
        .eq("is_approved", True)
        .not_.is_("ai_labels", "null")
        .execute()
    )

    matched_ids = []
    for row in all_media.data or []:
        labels = row.get("ai_labels", []) or []
        labels_lower = [l.lower() for l in labels]
        if any(term in label for term in terms for label in labels_lower):
            matched_ids.append(row["id"])

    return matched_ids
