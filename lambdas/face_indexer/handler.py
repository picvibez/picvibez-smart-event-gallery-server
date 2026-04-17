"""Lambda: Detect faces with Rekognition and generate semantic labels with Gemini.

Triggered by SQS messages from S3 PutObject events.
Creates/updates ai_face_clusters and media_faces rows in Supabase.
Updates media.ai_labels with Gemini-generated tags.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
rekognition = boto3.client("rekognition")

BUCKET = os.environ["S3_MEDIA_BUCKET"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
CLOUDFRONT_DOMAIN = os.environ.get("CLOUDFRONT_DOMAIN", "")
COLLECTION_PREFIX = os.environ.get("REKOGNITION_COLLECTION_PREFIX", "picvibez_event_")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


def _supabase_request(path: str, method: str = "GET", data: dict | None = None) -> list | dict:
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("apikey", SUPABASE_SERVICE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_SERVICE_KEY}")
    req.add_header("Content-Type", "application/json")
    if method in ("POST", "PATCH"):
        req.add_header("Prefer", "return=representation")
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def _collection_id(event_id: str) -> str:
    return f"{COLLECTION_PREFIX}{event_id.replace('-', '')}"


def _ensure_collection(event_id: str) -> str:
    cid = _collection_id(event_id)
    try:
        rekognition.create_collection(CollectionId=cid)
    except rekognition.exceptions.ResourceAlreadyExistsException:
        pass
    return cid


def _process_faces(event_id: str, s3_key: str, media_id: str) -> None:
    collection_id = _ensure_collection(event_id)

    try:
        search_resp = rekognition.search_faces_by_image(
            CollectionId=collection_id,
            Image={"S3Object": {"Bucket": BUCKET, "Name": s3_key}},
            MaxFaces=10,
            FaceMatchThreshold=80.0,
        )
    except (rekognition.exceptions.InvalidParameterException, Exception) as e:
        logger.info("No indexable face in %s: %s", s3_key, e)
        return

    searched_face_bbox = search_resp.get("SearchedFaceBoundingBox", {})

    for match in search_resp.get("FaceMatches", []):
        face = match["Face"]
        face_id = face["FaceId"]
        confidence = match["Similarity"]
        bbox = face.get("BoundingBox", searched_face_bbox)

        existing = _supabase_request(
            f"ai_face_clusters?id=eq.{face_id}&event_id=eq.{event_id}&select=id"
        )
        if not existing:
            cdn_url = f"https://{CLOUDFRONT_DOMAIN}/{s3_key}" if CLOUDFRONT_DOMAIN else ""
            _supabase_request("ai_face_clusters", "POST", {
                "id": face_id,
                "event_id": event_id,
                "representative_image_url": cdn_url,
            })

        _supabase_request("media_faces", "POST", {
            "media_id": media_id,
            "cluster_id": face_id,
            "bounding_box": {
                "left": bbox.get("Left", 0),
                "top": bbox.get("Top", 0),
                "width": bbox.get("Width", 0),
                "height": bbox.get("Height", 0),
            },
            "confidence": confidence,
        })

    logger.info("Processed %d face matches for %s", len(search_resp.get("FaceMatches", [])), s3_key)


def _generate_labels(s3_key: str, media_id: str) -> None:
    if not GEMINI_API_KEY:
        return

    from google import genai

    client = genai.Client(api_key=GEMINI_API_KEY)
    cdn_url = f"https://{CLOUDFRONT_DOMAIN}/{s3_key}" if CLOUDFRONT_DOMAIN else f"https://{BUCKET}.s3.amazonaws.com/{s3_key}"

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[{
                "role": "user",
                "parts": [
                    {"text": (
                        "Analyze this event photo. Return ONLY a JSON array of 5-15 "
                        "descriptive English tags. Include: people descriptions, activities, "
                        "setting, mood, colors, objects. Example: [\"bride\",\"dance\",\"outdoor\"]. "
                        "Return ONLY the JSON array."
                    )},
                    {"file_data": {"file_uri": cdn_url, "mime_type": "image/jpeg"}},
                ],
            }],
        )
        text = response.text.strip()
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            labels = json.loads(text[start : end + 1])
        else:
            labels = []
    except Exception:
        logger.exception("Gemini labeling failed for %s", s3_key)
        labels = []

    if labels:
        _supabase_request(
            f"media?id=eq.{media_id}",
            "PATCH",
            {"ai_labels": labels},
        )
        logger.info("Generated %d labels for %s", len(labels), s3_key)


def handler(event, context):
    for record in event.get("Records", []):
        body = json.loads(record.get("body", "{}"))

        for s3_record in body.get("Records", []):
            key = s3_record["s3"]["object"]["key"]

            if "/thumbs/" in key or "/watermarked/" in key:
                continue
            if not any(key.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp")):
                continue

            parts = key.split("/")
            if len(parts) < 3 or parts[0] != "events":
                continue

            event_id = parts[1]

            media_rows = _supabase_request(f"media?s3_key=eq.{key}&select=id")
            if not media_rows:
                logger.warning("No media row found for s3_key=%s", key)
                continue

            media_id = media_rows[0]["id"]

            logger.info("AI processing: event=%s media=%s key=%s", event_id, media_id, key)

            try:
                _process_faces(event_id, key, media_id)
            except Exception:
                logger.exception("Face processing failed for %s", key)

            try:
                _generate_labels(key, media_id)
            except Exception:
                logger.exception("Label generation failed for %s", key)

    return {"statusCode": 200}
