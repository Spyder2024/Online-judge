import enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class PresignedURLMethod(str, enum.Enum):
    GET = "GET"
    PUT = "PUT"


class PresignedURLRequest(BaseModel):
    object_key: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="Path or key inside S3/MinIO bucket (e.g., 'problems/101/statement.pdf')",
    )
    method: PresignedURLMethod = Field(
        ..., description="GET for downloading object, PUT for uploading directly to bucket"
    )
    content_type: Optional[str] = Field(
        default="application/pdf",
        description="MIME type required when method is PUT (e.g., 'application/pdf', 'image/png')",
    )
    expires_in: Optional[int] = Field(
        default=None,
        gt=0,
        le=86400,
        description="Optional custom URL expiration time in seconds (max 24 hours)",
    )


class PresignedURLResponse(BaseModel):
    object_key: str
    method: PresignedURLMethod
    url: str = Field(..., description="Secure pre-signed URL generated from storage client")
    expires_in: int = Field(..., description="Expiration time in seconds")

    model_config = ConfigDict(from_attributes=True)
