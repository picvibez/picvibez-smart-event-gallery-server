from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    InviteType,
    MediaType,
    MemberRole,
    MemberStatus,
    PrivacyMode,
    RelationshipType,
    TransactionType,
    VendorCategory,
)


class _Base(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────── Profiles ────────────────────────────


class ProfileOut(_Base):
    id: UUID
    display_name: str | None = None
    phone_number: str | None = None
    avatar_url: str | None = None
    event_passes: int = 0
    person_id: UUID | None = None
    face_embedding_id: str | None = None
    created_at: datetime | None = None


class ProfileUpdate(BaseModel):
    display_name: str | None = None
    phone_number: str | None = None
    avatar_url: str | None = None


# ──────────────────────────── Events ────────────────────────────


class EventCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    event_type: str = "Wedding"
    start_time: datetime | None = None
    end_time: datetime | None = None
    privacy_mode: PrivacyMode = PrivacyMode.PUBLIC


class EventUpdate(BaseModel):
    name: str | None = None
    event_type: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    privacy_mode: PrivacyMode | None = None
    is_watermark_enabled: bool | None = None
    storage_limit_bytes: int | None = None


class EventOut(_Base):
    id: UUID
    name: str
    event_type: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    privacy_mode: PrivacyMode
    storage_limit_bytes: int
    current_storage_bytes: int = 0
    is_watermark_enabled: bool = True
    created_by: UUID
    created_at: datetime | None = None
    member_count: int | None = None


# ──────────────────────────── Invites ────────────────────────────


class InviteCreate(BaseModel):
    invite_type: InviteType = InviteType.LINK
    passcode: str | None = Field(None, min_length=4, max_length=8)


class InviteOut(_Base):
    id: UUID
    event_id: UUID
    invite_type: InviteType
    token: UUID
    is_active: bool = True
    usage_count: int = 0
    has_passcode: bool = False
    created_at: datetime | None = None


class InviteResolve(_Base):
    event_id: UUID
    event_name: str
    privacy_mode: PrivacyMode
    requires_passcode: bool = False


# ──────────────────────────── Members ────────────────────────────


class JoinRequest(BaseModel):
    token: UUID
    passcode: str | None = None


class MemberOut(_Base):
    event_id: UUID
    profile_id: UUID
    role: MemberRole
    status: MemberStatus
    auto_upload_enabled: bool = False
    display_name: str | None = None
    avatar_url: str | None = None


class MemberUpdate(BaseModel):
    role: MemberRole | None = None
    status: MemberStatus | None = None


# ──────────────────────────── Media ────────────────────────────


class PresignRequest(BaseModel):
    file_name: str
    file_size_bytes: int = Field(..., gt=0, le=104_857_600)  # max 100MB
    media_type: MediaType


class PresignResponse(_Base):
    upload_url: str
    s3_key: str
    cdn_url: str


class MediaConfirm(BaseModel):
    s3_key: str
    file_name: str
    file_size_bytes: int
    media_type: MediaType
    captured_at: datetime | None = None


class MediaOut(_Base):
    id: UUID
    event_id: UUID
    uploader_id: UUID
    cdn_url: str
    thumbnail_url: str | None = None
    file_name: str
    file_size_bytes: int
    media_type: MediaType
    is_approved: bool = True
    ai_labels: list[str] | None = None
    captured_at: datetime | None = None
    created_at: datetime | None = None
    uploader_name: str | None = None
    uploader_avatar: str | None = None
    like_count: int = 0
    comment_count: int = 0
    liked_by_me: bool = False


class MediaListParams(BaseModel):
    cursor: str | None = None
    limit: int = Field(default=30, ge=1, le=100)
    media_type: MediaType | None = None
    uploader_id: UUID | None = None
    cluster_id: UUID | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"


# ──────────────────────────── AI / Smart ────────────────────────


class FaceClusterOut(_Base):
    id: UUID
    event_id: UUID
    representative_image_url: str
    person_id: UUID | None = None
    person_name: str | None = None
    photo_count: int = 0


class ClusterLinkRequest(BaseModel):
    person_id: UUID


class SearchResult(_Base):
    media: list[MediaOut]
    query: str
    total: int


# ──────────────────────────── Family Tree ────────────────────────


class PersonCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str | None = None
    date_of_birth: date | None = None
    face_cluster_id: UUID | None = None


class PersonUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: date | None = None
    face_cluster_id: UUID | None = None


class PersonOut(_Base):
    id: UUID
    first_name: str
    last_name: str | None = None
    date_of_birth: date | None = None
    face_cluster_id: UUID | None = None
    managed_by_admin_id: UUID


class RelationshipCreate(BaseModel):
    person_id: UUID
    related_person_id: UUID
    relationship_type: RelationshipType


class RelationshipOut(_Base):
    id: UUID
    person_id: UUID
    related_person_id: UUID
    relationship_type: RelationshipType


class FamilyTreeNode(_Base):
    id: UUID
    first_name: str
    last_name: str | None = None
    generation: int


# ──────────────────────────── Social ────────────────────────────


class CommentCreate(BaseModel):
    comment_text: str = Field(..., min_length=1, max_length=1000)


class CommentOut(_Base):
    id: UUID
    media_id: UUID
    user_id: UUID
    comment_text: str
    created_at: datetime | None = None
    display_name: str | None = None
    avatar_url: str | None = None


# ──────────────────────────── Admin Secrets ────────────────────


class GuestMetadataUpsert(BaseModel):
    gift_received: str | None = None
    thank_you_sent: bool | None = None
    admin_notes: str | None = None


class GuestMetadataOut(_Base):
    event_id: UUID
    person_id: UUID
    gift_received: str | None = None
    thank_you_sent: bool = False
    admin_notes: str | None = None
    person_name: str | None = None


# ──────────────────────────── Billing ────────────────────────────


class CheckoutRequest(BaseModel):
    event_id: UUID
    type: TransactionType
    storage_gb: int | None = Field(None, ge=1, le=100)


class CheckoutResponse(_Base):
    checkout_url: str
    session_id: str


class TransactionOut(_Base):
    id: UUID
    event_id: UUID
    user_id: UUID
    stripe_payment_id: str
    type: TransactionType
    amount_cents: int
    purchased_bytes: int | None = None
    created_at: datetime | None = None


# ──────────────────────────── Vendors ────────────────────────────


class VendorOut(_Base):
    id: UUID
    name: str
    category: VendorCategory
    description: str | None = None
    rating: float | None = None
    price_range: str | None = None
    contact_url: str | None = None
    image_url: str | None = None
    created_at: datetime | None = None


# ──────────────────────────── Generic ────────────────────────────


class MessageResponse(_Base):
    message: str


class HealthResponse(_Base):
    status: str
    version: str
    environment: str
