from fastapi import APIRouter

from app.api.v1.admin_secrets import router as admin_secrets_router
from app.api.v1.auth import router as auth_router
from app.api.v1.billing import router as billing_router
from app.api.v1.events import router as events_router
from app.api.v1.family_tree import router as family_tree_router
from app.api.v1.invites import router as invites_router
from app.api.v1.media import router as media_router
from app.api.v1.members import router as members_router
from app.api.v1.smart import router as smart_router
from app.api.v1.social import router as social_router
from app.api.v1.users import router as users_router
from app.api.v1.vendors import router as vendors_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(events_router)
api_router.include_router(invites_router)
api_router.include_router(members_router)
api_router.include_router(media_router)
api_router.include_router(smart_router)
api_router.include_router(social_router)
api_router.include_router(family_tree_router)
api_router.include_router(admin_secrets_router)
api_router.include_router(billing_router)
api_router.include_router(vendors_router)
