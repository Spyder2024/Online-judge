# Code Captain: Authentication & Authorization Specification (Layer 4)

**Product Name:** Code Captain Online Judge  
**Document Version:** 1.0.0  
**Phase:** 4 — Auth & Permissions (Foundation Phase)  
**Status:** Approved Baseline  
**Related Documents:** [docs/system-design.md](system-design.md), [docs/database.md](database.md)

---

## 1. System Roles

Code Captain enforces three explicit system roles in accordance with the principle of least privilege:

| Role | Identifier | Target Audience | Scope of Responsibility |
|---|---|---|---|
| **Student** | `STUDENT` | Casual learners & academy students | Can view public problems, execute sample tests, submit solutions, view personal submissions and bookmark problems. |
| **Contestant** | `CONTESTANT` | Active competitive programmers | Default role. All Student capabilities + live contest registration, contest submissions, leaderboard participation. |
| **Admin** | `ADMIN` | Platform administrators & contest hosts | Full system authority. Problem creation, editing, hidden testcase management, contest scheduling, user management, and telemetry access. |

---

## 2. Resource Permissions Matrix

| Resource | Action | Student | Contestant | Admin | Enforcement Mechanism |
|---|---|:---:|:---:|:---:|---|
| **Public Problems** | Read / Search | **Allow** | **Allow** | **Allow** | Public endpoint |
| **Problem Management** | Create / Edit / Delete | Deny | Deny | **Allow** | `get_current_admin_user` dependency |
| **Hidden Test Cases** | Read / View | Deny | Deny | **Allow** | Excluded from serializer; admin-only |
| **Pre-Flight Run** | Run Sample Cases | **Allow** | **Allow** | **Allow** | Authenticated user session |
| **Code Submissions** | Create | **Allow** | **Allow** | **Allow** | Authenticated user (`get_current_user`) |
| **Submission Details** | Read (Owner) | **Allow** | **Allow** | **Allow** | IDOR Check (`submission.user_id == user.user_id`) |
| **Submission Details** | Read (Other User) | **Deny (403)** | **Deny (403)** | **Allow** | IDOR Check (`user.role == 'Admin'`) |
| **Contests** | View Public List | **Allow** | **Allow** | **Allow** | Public / Authenticated |
| **Contests** | Participate / Submit | Deny | **Allow** | **Allow** | Role check (`role in ('Contestant', 'Admin')`) |
| **Contest Management** | Create / Edit | Deny | Deny | **Allow** | `get_current_admin_user` |
| **User Profile** | Edit (Own) | **Allow** | **Allow** | **Allow** | Token sub matching |
| **User Profile** | Edit (Other User) | **Deny (403)** | **Deny (403)** | **Allow** | Admin override only |
| **Avatar Upload** | Presigned S3 URL | **Allow (own avatar)**| **Allow (own avatar)** | **Allow (all)** | SEC-05 path prefix validation |

---

## 3. Authorization Enforcement in Code

Authorization is enforced at multiple layers:

### A. FastAPI Route Dependencies
```python
@router.post("/problems", response_model=ProblemResponse)
async def create_problem(
    problem_in: ProblemCreate,
    current_admin: User = Depends(get_current_admin_user), # Enforces Admin role
    db: AsyncSession = Depends(get_db)
):
    ...
```

### B. Object-Level Authorization (IDOR Prevention)
Every endpoint accessing a private resource strictly validates record ownership against `current_user.user_id`:
```python
@router.get("/submissions/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Submission).where(Submission.submission_id == submission_id)
    submission = (await db.execute(stmt)).scalar_one_or_none()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Strict IDOR Authorization Guard
    if current_user.role != UserRole.ADMIN and submission.user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this submission"
        )
    return submission
```

---

## 4. Cryptographic Security Standards

1. **Password Hashing (Argon2id + Bcrypt)**:
   - Implemented via `pwdlib` using `Argon2Hasher` with automatic fallback to `BcryptHasher`.
   - Salt generation is cryptographically random and unique per password.
   - Raw passwords and hashes are strictly excluded from all `UserResponse` Pydantic models.
2. **JWT Access & Refresh Tokens**:
   - Access tokens signed with `HS256` using high-entropy `SECRET_KEY` (minimum 32 characters enforced by SEC-08 validator).
   - Access token duration: 1,440 minutes (24 hours).
   - Refresh token duration: 30 days (`type: "refresh"` claim guard).
3. **Login CSRF Defense (Signed OAuth State)**:
   - Google and GitHub OAuth handshakes issue an HMAC-SHA256 signed JWT `state` parameter containing a timestamp and cryptographic nonce, validated on callback (SEC-06).

---

## 5. Layer 4 Verification Checklist

- [x] Unauthenticated requests to protected routes return `401 Unauthorized`, not 500 or empty bodies.
- [x] Unauthorized requests to another user's submissions return `403 Forbidden` (IDOR verified).
- [x] Password hashes are excluded from all API response schemas.
- [x] Signup enforces non-admin role assignment by default (`UserRole.CONTESTANT`).
- [x] Refresh tokens are cryptographically distinct from access tokens (`type: "refresh"` claim).
