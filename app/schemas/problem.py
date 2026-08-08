from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.problem import ProblemDifficulty


class TagBase(BaseModel):
    tag_name: str = Field(..., min_length=1, max_length=64)


class TagCreate(TagBase):
    pass


class TagResponse(TagBase):
    tag_id: int

    model_config = ConfigDict(from_attributes=True)


class TestCaseBase(BaseModel):
    input_text: str = Field(..., description="Exact standard input text")
    output_text: str = Field(..., description="Expected standard output text")
    is_hidden: bool = Field(default=True, description="Whether test case is hidden from contestants")


class TestCaseCreate(TestCaseBase):
    pass


class TestCaseResponse(TestCaseBase):
    test_case_id: int
    problem_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProblemBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    statement_text: str = Field(..., description="Markdown problem description and requirements")
    difficulty: ProblemDifficulty = Field(..., description="Problem difficulty rating")
    time_limit: float = Field(..., gt=0.0, description="Execution time limit in seconds")
    memory_limit: int = Field(..., gt=0, description="Memory consumption limit in MB")


class ProblemCreate(ProblemBase):
    tag_names: Optional[List[str]] = Field(default=None, description="List of tag names to link")
    test_cases: Optional[List[TestCaseCreate]] = Field(default=None, description="Initial test cases")
    problem_embedding: Optional[List[float]] = Field(
        default=None, min_length=384, max_length=384, description="384-dimensional vector embedding"
    )


class ProblemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    statement_text: Optional[str] = None
    difficulty: Optional[ProblemDifficulty] = None
    time_limit: Optional[float] = Field(None, gt=0.0)
    memory_limit: Optional[int] = Field(None, gt=0)
    tag_names: Optional[List[str]] = None
    problem_embedding: Optional[List[float]] = Field(None, min_length=384, max_length=384)


class ProblemResponse(ProblemBase):
    problem_id: int
    tags: List[TagResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProblemDetailResponse(ProblemResponse):
    test_cases: List[TestCaseResponse] = []
    problem_embedding: Optional[List[float]] = None


class PaginatedProblemResponse(BaseModel):
    items: List[ProblemResponse]
    total_count: int
    page: int
    limit: int
    total_pages: int

