import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_access_token
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency validating the Bearer JWT token and loading the current async user profile from PostgreSQL.
    """
    try:
        payload = decode_access_token(token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise AuthenticationError("Could not validate credentials: sub claim missing")
        user_id = int(user_id_str)
    except (jwt.PyJWTError, ValueError) as e:
        raise AuthenticationError(f"Invalid authentication token: {e}")

    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthenticationError("User associated with token no longer exists")
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    FastAPI dependency enforcing Admin role restrictions on sensitive endpoints.
    """
    if current_user.role != UserRole.ADMIN:
        raise PermissionDeniedError("Admin role required to access this resource")
    return current_user
