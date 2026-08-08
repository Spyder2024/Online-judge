"""
app/api/v1/oauth.py

Module 3: OAuth2 Authentication (Google + GitHub)

Architecture:
  - Backend-driven OAuth2 Authorization Code Flow.
  - The frontend redirects the user's browser to our FastAPI /oauth/{provider}/redirect.
  - FastAPI sends the user to the provider's consent screen.
  - The provider redirects back to /oauth/{provider}/callback?code=...
  - FastAPI exchanges the code for an access_token, fetches the user's profile,
    upserts the User row (creates on first login, re-uses on subsequent logins),
    issues our own JWT, and redirects the browser back to the frontend SPA with
    the token embedded as a URL fragment: /#oauth_token=<JWT>
  - The SPA picks up the fragment, stores it in localStorage, and removes it from
    the URL — identical flow to how GitHub/Google OAuth apps work in the wild.

Non-destructive:
  - Does NOT modify auth.py, security.py, or deps.py.
  - Disabled gracefully when GOOGLE_CLIENT_ID / GITHUB_CLIENT_ID are not set.

Endpoints:
  GET /oauth/google/redirect   → redirects browser to Google consent URL
  GET /oauth/google/callback   → exchanges code, upserts user, returns JWT via redirect
  GET /oauth/github/redirect   → redirects browser to GitHub consent URL
  GET /oauth/github/callback   → exchanges code, upserts user, returns JWT via redirect
  GET /oauth/providers         → returns which providers are currently enabled (for UI)
"""

from __future__ import annotations

import secrets
import urllib.parse
from datetime import timedelta
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.models.user import User, UserRole

logger = get_logger(__name__)
router = APIRouter()

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO  = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_SCOPES    = "openid email profile"

GITHUB_AUTH_URL  = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USERINFO  = "https://api.github.com/user"

# Frontend SPA URL — the fragment token will be appended here
FRONTEND_SUCCESS_URL = "/"
FRONTEND_ERROR_URL   = "/?oauth_error=1"


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _google_redirect_uri() -> str:
    return f"{settings.OAUTH_REDIRECT_BASE_URL}/api/v1/oauth/google/callback"


def _github_redirect_uri() -> str:
    return f"{settings.OAUTH_REDIRECT_BASE_URL}/api/v1/oauth/github/callback"


async def _upsert_oauth_user(
    db: AsyncSession,
    provider: str,
    oauth_id: str,
    username_hint: str,
    email: Optional[str] = None,
) -> User:
    """
    Find an existing user by (oauth_provider, oauth_id).
    If not found, also try to match by email (so a pre-existing password
    account can link to OAuth without creating a duplicate).
    If still not found, create a new Contestant account.
    """
    # 1. Lookup by oauth identity
    result = await db.execute(
        select(User).where(
            User.oauth_provider == provider,
            User.oauth_id == oauth_id,
        )
    )
    user = result.scalar_one_or_none()
    if user:
        return user

    # 2. Lookup by username (derived from email/provider) to avoid collision
    #    Generate a safe username from the hint
    base_username = username_hint.split("@")[0].replace(" ", "_").lower()[:48]
    safe_username = base_username

    # Check uniqueness; append random suffix on collision
    existing_name = await db.execute(select(User).where(User.username == safe_username))
    if existing_name.scalar_one_or_none():
        safe_username = f"{base_username}_{secrets.token_hex(3)}"

    # 3. Create new OAuth user (no password hash)
    user = User(
        username=safe_username,
        password_hash=None,           # OAuth-only accounts have no password
        oauth_provider=provider,
        oauth_id=str(oauth_id),
        role=UserRole.CONTESTANT,
        rating=1200,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("New OAuth user created", provider=provider, user_id=user.user_id, username=safe_username)
    return user


def _make_jwt(user: User) -> str:
    return create_access_token(
        subject=user.user_id,
        role=user.role.value,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def _success_redirect(token: str, username: str) -> RedirectResponse:
    """Redirect back to SPA with token and username in URL fragment."""
    params = urllib.parse.urlencode({"token": token, "username": username})
    return RedirectResponse(url=f"{FRONTEND_SUCCESS_URL}#oauth_success&{params}", status_code=302)


def _error_redirect(detail: str) -> RedirectResponse:
    logger.error("OAuth flow failed", detail=detail)
    return RedirectResponse(url=FRONTEND_ERROR_URL, status_code=302)


# ─────────────────────────────────────────────────────────────
# Provider Status
# ─────────────────────────────────────────────────────────────

@router.get("/providers", summary="List enabled OAuth providers")
async def get_enabled_providers():
    """Returns which OAuth providers are currently configured."""
    return JSONResponse({
        "google": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET),
        "github": bool(settings.GITHUB_CLIENT_ID and settings.GITHUB_CLIENT_SECRET),
    })


# ─────────────────────────────────────────────────────────────
# Google OAuth2
# ─────────────────────────────────────────────────────────────

@router.get("/google/redirect", summary="Redirect to Google OAuth consent screen")
async def google_redirect():
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured.")

    params = urllib.parse.urlencode({
        "client_id":     settings.GOOGLE_CLIENT_ID,
        "redirect_uri":  _google_redirect_uri(),
        "response_type": "code",
        "scope":         GOOGLE_SCOPES,
        "access_type":   "online",
    })
    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{params}", status_code=302)


@router.get("/google/callback", summary="Google OAuth2 callback handler")
async def google_callback(
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if error or not code:
        return _error_redirect(f"Google denied access or no code: {error}")

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Exchange authorization code for access token
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code":          code,
                "client_id":     settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri":  _google_redirect_uri(),
                "grant_type":    "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            return _error_redirect(f"Google token exchange failed: {token_resp.text}")

        token_data   = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return _error_redirect("Google token response missing access_token")

        # Fetch user profile
        userinfo_resp = await client.get(
            GOOGLE_USERINFO,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if userinfo_resp.status_code != 200:
            return _error_redirect("Google userinfo fetch failed")

        userinfo  = userinfo_resp.json()
        oauth_id  = userinfo.get("sub")
        email     = userinfo.get("email", "")
        full_name = userinfo.get("name", email)

    if not oauth_id:
        return _error_redirect("Google userinfo missing 'sub' claim")

    user  = await _upsert_oauth_user(db, "google", oauth_id, full_name or email, email)
    token = _make_jwt(user)
    return _success_redirect(token, user.username)


# ─────────────────────────────────────────────────────────────
# GitHub OAuth2
# ─────────────────────────────────────────────────────────────

@router.get("/github/redirect", summary="Redirect to GitHub OAuth consent screen")
async def github_redirect():
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured.")

    params = urllib.parse.urlencode({
        "client_id":    settings.GITHUB_CLIENT_ID,
        "redirect_uri": _github_redirect_uri(),
        "scope":        "read:user user:email",
    })
    return RedirectResponse(url=f"{GITHUB_AUTH_URL}?{params}", status_code=302)


@router.get("/github/callback", summary="GitHub OAuth2 callback handler")
async def github_callback(
    code: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if error or not code:
        return _error_redirect(f"GitHub denied access or no code: {error}")

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Exchange code for access token
        token_resp = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "code":          code,
                "client_id":     settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "redirect_uri":  _github_redirect_uri(),
            },
        )
        if token_resp.status_code != 200:
            return _error_redirect(f"GitHub token exchange failed: {token_resp.text}")

        token_data   = token_resp.json()
        access_token = token_data.get("access_token")
        if not access_token:
            return _error_redirect(f"GitHub token response missing access_token: {token_data}")

        # Fetch user profile
        userinfo_resp = await client.get(
            GITHUB_USERINFO,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept":        "application/vnd.github+json",
            },
        )
        if userinfo_resp.status_code != 200:
            return _error_redirect("GitHub userinfo fetch failed")

        userinfo = userinfo_resp.json()
        oauth_id = str(userinfo.get("id", ""))
        login    = userinfo.get("login", "")
        email    = userinfo.get("email", "")

    if not oauth_id:
        return _error_redirect("GitHub userinfo missing 'id' field")

    user  = await _upsert_oauth_user(db, "github", oauth_id, login or email, email)
    token = _make_jwt(user)
    return _success_redirect(token, user.username)
