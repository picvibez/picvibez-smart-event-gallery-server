from __future__ import annotations

from functools import lru_cache
from typing import Any

import boto3

from app.core.config import get_settings


def _session() -> boto3.Session:
    settings = get_settings()
    return boto3.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION,
    )


@lru_cache
def get_s3_client() -> Any:
    return _session().client("s3")


@lru_cache
def get_rekognition_client() -> Any:
    return _session().client("rekognition")


@lru_cache
def get_sqs_client() -> Any:
    return _session().client("sqs")
