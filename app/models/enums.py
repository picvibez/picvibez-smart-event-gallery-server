from enum import StrEnum


class PrivacyMode(StrEnum):
    PUBLIC = "public"
    APPROVAL = "approval"
    PASSCODE = "passcode"


class MemberRole(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


class MemberStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    BANNED = "banned"


class InviteType(StrEnum):
    LINK = "link"
    QR = "qr"
    NFC = "nfc"


class MediaType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"


class RelationshipType(StrEnum):
    PARENT = "parent"
    CHILD = "child"
    SPOUSE = "spouse"
    SIBLING = "sibling"


class TransactionType(StrEnum):
    BASE_PLAN = "base_plan"
    STORAGE_ADDON = "storage_addon"


class VendorCategory(StrEnum):
    PHOTOGRAPHY = "photography"
    DECOR = "decor"
    DJ = "dj"
    CATERING = "catering"
