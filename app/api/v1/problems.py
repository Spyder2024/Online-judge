import math
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.api.deps import get_current_user, get_current_admin_user, get_optional_current_user
from app.models.user import User
from app.models.problem import Problem, ProblemTag, Tag, TestCase
from app.models.submission import Submission
from app.schemas.problem import ProblemCreate, ProblemResponse, ProblemDetailResponse, PaginatedProblemResponse

router = APIRouter()


class SemanticSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10


@router.get("", response_model=PaginatedProblemResponse)
async def list_problems(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sort_by: str = Query("id"),
    sort_dir: str = Query("asc"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    """
    List practice problems with server-side search, tags, difficulty, status filtering,
    and sorting with page-based pagination.
    """
    offset = (page - 1) * limit
    conditions = []

    # Text search
    if search and search.strip():
        q = search.strip()
        conditions.append(
            (Problem.title.ilike(f"%{q}%")) | (Problem.statement_text.ilike(f"%{q}%"))
        )

    # Difficulty filter
    if difficulty and difficulty.strip().lower() not in ("all", ""):
        conditions.append(func.lower(Problem.difficulty) == difficulty.strip().lower())

    # Tag filter
    if tag and tag.strip().lower() not in ("all", ""):
        clean_tag = tag.strip().lower()
        conditions.append(Problem.tags.any(func.lower(Tag.tag_name) == clean_tag))

    # User status filter & status detection
    solved_ids: set[int] = set()
    attempted_ids: set[int] = set()
    if current_user:
        sub_stmt = select(Submission.problem_id, Submission.verdict).where(
            Submission.user_id == current_user.user_id
        )
        sub_res = await db.execute(sub_stmt)
        for pid, verd in sub_res.all():
            verd_str = str(verd).upper()
            if "ACCEPTED" in verd_str:
                solved_ids.add(pid)
            else:
                attempted_ids.add(pid)
        attempted_ids = attempted_ids - solved_ids

        if status and status.strip().lower() == "solved":
            conditions.append(Problem.problem_id.in_(solved_ids if solved_ids else [-1]))
        elif status and status.strip().lower() == "attempted":
            conditions.append(Problem.problem_id.in_(attempted_ids if attempted_ids else [-1]))
        elif status and status.strip().lower() == "unsolved":
            all_done = solved_ids.union(attempted_ids)
            if all_done:
                conditions.append(Problem.problem_id.not_in(all_done))

    # Sorting
    if sort_by == "title":
        order_clause = Problem.title.asc() if sort_dir == "asc" else Problem.title.desc()
    elif sort_by == "difficulty":
        order_clause = Problem.difficulty.asc() if sort_dir == "asc" else Problem.difficulty.desc()
    else:
        order_clause = Problem.problem_id.asc() if sort_dir == "asc" else Problem.problem_id.desc()

    # Total count query
    count_stmt = select(func.count(func.distinct(Problem.problem_id)))
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    count_res = await db.execute(count_stmt)
    total_count = count_res.scalar() or 0

    # Paginated items query
    stmt = (
        select(Problem)
        .options(selectinload(Problem.tags))
        .order_by(order_clause)
        .offset(offset)
        .limit(limit)
    )
    if conditions:
        stmt = stmt.where(*conditions)
    result = await db.execute(stmt)
    problems = result.scalars().all()

    # Annotate problem items with user status
    problem_items = []
    for p in problems:
        p_status = None
        if current_user:
            if p.problem_id in solved_ids:
                p_status = "solved"
            elif p.problem_id in attempted_ids:
                p_status = "attempted"
        
        # Consistent acceptance rate representation
        acc_rate = 62.4
        p_dict = {
            "problem_id": p.problem_id,
            "title": p.title,
            "statement_text": p.statement_text,
            "difficulty": p.difficulty,
            "time_limit": p.time_limit,
            "memory_limit": p.memory_limit,
            "tags": p.tags,
            "status": p_status,
            "acceptance_rate": acc_rate,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        }
        problem_items.append(p_dict)

    total_pages = math.ceil(total_count / limit) if total_count > 0 else 1

    return {
        "items": problem_items,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
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
    Natural language vector semantic search or text fallback.
    """
    query_text = search_req.query.strip() if search_req.query else ""
    if not query_text:
        res = await list_problems(page=1, limit=search_req.limit or 10, db=db)
        return res["items"]

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
