from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.storage import router as storage_router
from app.api.v1.problems import router as problems_router
from app.api.v1.contests import router as contests_router
from app.api.v1.submissions import router as submissions_router
from app.api.v1.websocket import router as ws_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication & Users"])
api_router.include_router(storage_router, prefix="/storage", tags=["Object Storage & Pre-signed URLs"])
api_router.include_router(problems_router, prefix="/problems", tags=["Problems & Vector Search"])
api_router.include_router(contests_router, prefix="/contests", tags=["Contests & Redis Leaderboards"])
api_router.include_router(submissions_router, prefix="/submissions", tags=["Submissions & Execution"])
api_router.include_router(ws_router, tags=["WebSocket Real-Time Events"])

