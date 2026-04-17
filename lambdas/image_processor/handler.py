"""Lambda: Generate thumbnails and watermarked versions of uploaded media.

Triggered by SQS messages from S3 PutObject events.
Writes thumbnail to S3 and updates the media row in Supabase.
"""
from __future__ import annotations

import io
import json
import logging
import os

import boto3
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

BUCKET = os.environ["S3_MEDIA_BUCKET"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

THUMB_MAX_SIZE = (400, 400)
WATERMARK_TEXT = "PicVibez"


def _generate_thumbnail(image_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_bytes))
    img.thumbnail(THUMB_MAX_SIZE, Image.Resampling.LANCZOS)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=80)
    return buf.getvalue()


def _apply_watermark(image_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", max(20, img.width // 20))
    except (OSError, IOError):
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = img.width - text_w - 20
    y = img.height - text_h - 20

    draw.text((x, y), WATERMARK_TEXT, fill=(255, 255, 255, 100), font=font)

    watermarked = Image.alpha_composite(img, overlay).convert("RGB")
    buf = io.BytesIO()
    watermarked.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _update_supabase(media_s3_key: str, thumbnail_key: str) -> None:
    import urllib.request

    url = f"{SUPABASE_URL}/rest/v1/media?s3_key=eq.{media_s3_key}"
    data = json.dumps({"thumbnail_key": thumbnail_key}).encode()
    req = urllib.request.Request(url, data=data, method="PATCH")
    req.add_header("apikey", SUPABASE_SERVICE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_SERVICE_KEY}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Prefer", "return=minimal")
    urllib.request.urlopen(req)


def handler(event, context):
    for record in event.get("Records", []):
        body = json.loads(record.get("body", "{}"))

        for s3_record in body.get("Records", []):
            bucket = s3_record["s3"]["bucket"]["name"]
            key = s3_record["s3"]["object"]["key"]

            if "/thumbs/" in key or "/watermarked/" in key:
                continue

            if not any(key.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")):
                logger.info("Skipping non-image: %s", key)
                continue

            logger.info("Processing: s3://%s/%s", bucket, key)

            response = s3.get_object(Bucket=bucket, Key=key)
            original_bytes = response["Body"].read()

            thumb_key = key.replace("/originals/", "/thumbs/").rsplit(".", 1)[0] + ".webp"
            thumb_bytes = _generate_thumbnail(original_bytes)
            s3.put_object(
                Bucket=bucket,
                Key=thumb_key,
                Body=thumb_bytes,
                ContentType="image/webp",
            )
            logger.info("Thumbnail saved: %s", thumb_key)

            try:
                event_id = key.split("/")[1]
                event_data = _get_event_watermark_setting(event_id)
                if event_data:
                    wm_key = key.replace("/originals/", "/watermarked/")
                    wm_bytes = _apply_watermark(original_bytes)
                    s3.put_object(
                        Bucket=bucket,
                        Key=wm_key,
                        Body=wm_bytes,
                        ContentType="image/jpeg",
                    )
                    logger.info("Watermarked saved: %s", wm_key)
            except Exception:
                logger.exception("Watermark failed for %s", key)

            try:
                _update_supabase(key, thumb_key)
            except Exception:
                logger.exception("Supabase update failed for %s", key)

    return {"statusCode": 200}


def _get_event_watermark_setting(event_id: str) -> bool:
    import urllib.request

    url = f"{SUPABASE_URL}/rest/v1/events?id=eq.{event_id}&select=is_watermark_enabled"
    req = urllib.request.Request(url)
    req.add_header("apikey", SUPABASE_SERVICE_KEY)
    req.add_header("Authorization", f"Bearer {SUPABASE_SERVICE_KEY}")
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read())
    return data[0]["is_watermark_enabled"] if data else False
