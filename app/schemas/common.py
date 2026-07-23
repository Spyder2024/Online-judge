from typing import Generic, List, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response schema wrapper.
    Uses Pydantic v2 strict serialization schema.
    """
    items: List[T]
    total: int = Field(..., description="Total number of items matching query")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of available pages")

    model_config = ConfigDict(from_attributes=True)
