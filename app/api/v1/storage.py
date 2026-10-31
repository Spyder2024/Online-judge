from fastapi import APIRouter, Depends, HTTPException, status
from structlog import get_logger
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.storage import storage_client
from app.models.user import User, UserRole
from app.schemas.storage import (
    PresignedURLMethod,
    PresignedURLRequest,
    PresignedURLResponse,
)

logger = get_logger(__name__)

router = APIRouter()

ALLOWED_AVATAR_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}


@router.post(
    "/presigned-url",
    response_model=PresignedURLResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate pre-signed URL for S3/MinIO binary object access",
)
async def generate_presigned_url(
    payload: PresignedURLRequest,
    current_user: User = Depends(get_current_user),
) -> PresignedURLResponse:
    """
    Generate a secure pre-signed URL for reading (GET) or uploading (PUT) binary objects.
    Enforces role-based path validation, directory traversal prevention, and MIME filtering.
    """
    object_key = payload.object_key.strip()

    # Prevent directory traversal and invalid paths
    if ".." in object_key or object_key.startswith("/") or object_key.startswith("\\"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid object key: path traversal detected",
        )

    # Restrict PUT operations: only Admins can upload problem/system assets
    if payload.method == PresignedURLMethod.PUT:
        if current_user.role != UserRole.ADMIN:
            allowed_avatar_prefix = f"avatars/{current_user.user_id}/"
            if not object_key.startswith(allowed_avatar_prefix):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Non-admin users may only upload personal avatars under their assigned prefix",
                )
            content_type = payload.content_type or "image/png"
            if content_type.lower() not in ALLOWED_AVATAR_CONTENT_TYPES:
                allowed_types_str = ", ".join(sorted(ALLOWED_AVATAR_CONTENT_TYPES))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid avatar content type. Allowed types: {allowed_types_str}",
                )

    # Restrict GET operations: sensitive test cases can only be downloaded by Admin
    if payload.method == PresignedURLMethod.GET:
        if object_key.startswith("testcases/") and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin role required to download private testcase files",
            )

    logger.info(
        "Generating pre-signed URL",
        user_id=current_user.user_id,
        object_key=object_key,
        method=payload.method,
    )

    expires_in = payload.expires_in or settings.PRESIGNED_URL_EXPIRE_SECONDS

    if payload.method == PresignedURLMethod.GET:
        url = storage_client.generate_presigned_get_url(
            object_key=object_key,
            expires_in=expires_in,
        )
    else:
        url = storage_client.generate_presigned_put_url(
            object_key=object_key,
            content_type=payload.content_type or "application/pdf",
            expires_in=expires_in,
        )

    return PresignedURLResponse(
        object_key=object_key,
        method=payload.method,
        url=url,
        expires_in=expires_in,
    )
