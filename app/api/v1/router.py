from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.storage import router as storage_router
from app.api.v1.problems import router as problems_router
from app.api.v1.contests import router as contests_router
from app.api.v1.submissions import router as submissions_router
from app.api.v1.ai import router as ai_router
from app.api.v1.websocket import router as ws_router
from app.api.v1.profiles import router as profiles_router  # Module 2
from app.api.v1.oauth import router as oauth_router          # Module 3

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication & Users"])
api_router.include_router(storage_router, prefix="/storage", tags=["Object Storage & Pre-signed URLs"])
api_router.include_router(problems_router, prefix="/problems", tags=["Problems & Vector Search"])
api_router.include_router(contests_router, prefix="/contests", tags=["Contests & Redis Leaderboards"])
api_router.include_router(submissions_router, prefix="/submissions", tags=["Submissions & Execution"])
api_router.include_router(ai_router, prefix="/ai", tags=["Agentic AI Workflows & Reviews"])
api_router.include_router(ws_router, tags=["WebSocket Real-Time Events"])
api_router.include_router(profiles_router, prefix="/profiles", tags=["User Profiles & Bookmarks"])  # Module 2
api_router.include_router(profiles_router, prefix="/users", tags=["Users Management & Profiles"])   # Directive 2
api_router.include_router(oauth_router, prefix="/oauth", tags=["OAuth2 Social Login"])               # Module 3
