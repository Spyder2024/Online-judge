from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.storage import router as storage_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication & Users"])
api_router.include_router(storage_router, prefix="/storage", tags=["Object Storage & Pre-signed URLs"])
