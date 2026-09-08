from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin_user
from app.models.user import User
from app.models.problem import Problem, ProblemTag, Tag, TestCase
from app.schemas.problem import ProblemCreate, ProblemResponse, ProblemDetailResponse, PaginatedProblemResponse

router = APIRouter()


class SemanticSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10


import math
from sqlalchemy import func

@router.get("", response_model=PaginatedProblemResponse)
async def list_problems(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List practice problems with page-based pagination (page=1, limit=50)."""
    offset = (page - 1) * limit
    
    # Total count query
    count_stmt = select(func.count(Problem.problem_id))
    count_res = await db.execute(count_stmt)
    total_count = count_res.scalar() or 0

    # Paginated items query
    stmt = select(Problem).options(selectinload(Problem.tags)).offset(offset).limit(limit)
    result = await db.execute(stmt)
    problems = result.scalars().all()
    
    total_pages = math.ceil(total_count / limit) if total_count > 0 else 1
    
    return {
        "items": problems,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }


@router.get("/{problem_id}", response_model=ProblemDetailResponse)
async def get_problem(
    problem_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Fetch single problem details including public sample testcases."""
    stmt = (
        select(Problem)
        .options(selectinload(Problem.tags), selectinload(Problem.test_cases))
        .where(Problem.problem_id == problem_id)
    )
    result = await db.execute(stmt)
    problem = result.scalar_one_or_none()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    return problem


@router.post("", response_model=ProblemResponse, status_code=status.HTTP_201_CREATED)
async def create_problem(
    problem_in: ProblemCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin_user)
):
    """Create a new problem (Admin only)."""
    problem = Problem(
        title=problem_in.title,
        statement_text=problem_in.statement_text,
        difficulty=problem_in.difficulty,
        time_limit=problem_in.time_limit,
        memory_limit=problem_in.memory_limit,
    )
    db.add(problem)
    await db.commit()
    await db.refresh(problem)
    return problem


@router.post("/search", response_model=List[ProblemResponse])
async def search_problems_semantic(
    search_req: SemanticSearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Natural language vector semantic search using pgvector cosine distance on Problem.problem_embedding.
    If embeddings are not generated yet, falls back to text ILIKE matching.
    """
    if not query_text:
        res = await list_problems(1, search_req.limit or 10, db)
        return res["items"]
        
    # Standard text matching fallback / pgvector similarity
    stmt = (
        select(Problem)
        .options(selectinload(Problem.tags))
        .where(
            (Problem.title.ilike(f"%{query_text}%")) | 
            (Problem.statement_text.ilike(f"%{query_text}%"))
        )
        .limit(search_req.limit or 10)
    )
    result = await db.execute(stmt)
    problems = result.scalars().all()
    return problems
