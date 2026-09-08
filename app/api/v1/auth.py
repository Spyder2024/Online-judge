from datetime import timedelta
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from structlog import get_logger
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AuthenticationError, DuplicateResourceError
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserResponse

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def signup(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Register a new user with secure password hashing (Argon2 via pwdlib).
    Checks for existing username collisions asynchronously.
    """
    logger.info("Registering new user", username=user_in.username, role=user_in.role)
    result = await db.execute(select(User).where(User.username == user_in.username))
    existing_user = result.scalar_one_or_none()
    if existing_user is not None:
        raise DuplicateResourceError("User", "username", user_in.username)

    hashed_pw = get_password_hash(user_in.password)
    new_user = User(
        username=user_in.username,
        password_hash=hashed_pw,
        role=user_in.role or "Contestant",
        rating=1200,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    logger.info("User registered successfully", user_id=new_user.user_id)
    return UserResponse.model_validate(new_user)


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Authenticate credentials and obtain JWT access token",
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    OAuth2 compatible login route using form data (username & password).
    Returns a JWT Bearer access token valid for configured expiration duration.
    """
    logger.info("Authenticating login attempt", username=form_data.username)
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.password_hash):
        logger.warning("Authentication failed", username=form_data.username)
        raise AuthenticationError("Incorrect username or password")

    access_token = create_access_token(
        subject=user.user_id,
        role=user.role.value,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    logger.info("Login successful", user_id=user.user_id)
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/login-json",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="JSON login endpoint for API clients",
)
async def login_json(
    credentials: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> Token:
    """
    JSON payload compatible login route for SPA and REST clients.
    """
    logger.info("Authenticating JSON login attempt", username=credentials.username)
    result = await db.execute(select(User).where(User.username == credentials.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(credentials.password, user.password_hash):
        logger.warning("JSON authentication failed", username=credentials.username)
        raise AuthenticationError("Incorrect username or password")

    access_token = create_access_token(
        subject=user.user_id,
        role=user.role.value,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
)
async def read_current_user(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Retrieve profile details of the currently authenticated user.
    """
    return UserResponse.model_validate(current_user)
