from fastapi import APIRouter, Depends, status
from structlog import get_logger
from app.api.deps import get_current_user
from app.core.config import settings
from app.core.storage import storage_client
from app.models.user import User
from app.schemas.storage import (
    PresignedURLMethod,
    PresignedURLRequest,
    PresignedURLResponse,
)

logger = get_logger(__name__)

router = APIRouter()


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
    Generate a secure pre-signed URL for reading (`GET`) or uploading (`PUT`) binary objects
    such as problem statement PDFs, statement diagrams/images, or large testcase files.
    Ensures zero binary payload processing through PostgreSQL.
    """
    logger.info(
        "Generating pre-signed URL",
        user_id=current_user.user_id,
        object_key=payload.object_key,
        method=payload.method,
    )

    expires_in = payload.expires_in or settings.PRESIGNED_URL_EXPIRE_SECONDS

    if payload.method == PresignedURLMethod.GET:
        url = storage_client.generate_presigned_get_url(
            object_key=payload.object_key,
            expires_in=expires_in,
        )
    else:
        url = storage_client.generate_presigned_put_url(
            object_key=payload.object_key,
            content_type=payload.content_type or "application/pdf",
            expires_in=expires_in,
        )

    return PresignedURLResponse(
        object_key=payload.object_key,
        method=payload.method,
        url=url,
        expires_in=expires_in,
    )
