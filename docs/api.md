# Code Captain: API Conventions & Contracts Specification (Layer 5)

**Product Name:** Code Captain Online Judge  
**Document Version:** 1.0.0  
**Phase:** 5 — APIs & Backend Logic (Foundation Phase)  
**Status:** Approved Baseline  
**Related Documents:** [docs/system-design.md](system-design.md), [docs/architecture.md](architecture.md), [docs/auth.md](auth.md)

---

## 1. URL Structure & Naming Conventions

All API routes follow predictable RESTful conventions:
* **Base URL:** `/api/v1`
* **Resource Pluralization:** Always use plural nouns for collections (e.g. `/problems`, `/submissions`, `/contests`).
* **Sub-resources:** Express hierarchical relationships cleanly:
  * `GET /api/v1/problems/{id}/hints`
  * `GET /api/v1/contests/{id}/leaderboard`
* **Actions / Verbs:** Use HTTP methods (`GET`, `POST`, `PUT`, `DELETE`). For non-CRUD operations, use suffix verbs:
  * `POST /api/v1/auth/login-json`
  * `POST /api/v1/auth/refresh`
  * `GET /api/v1/problems/search`

---

## 2. Standard Response & Error Envelopes

### A. Success Format
Success responses return either the resource representation directly or a collection with pagination metadata:

#### Single Resource:
```json
{
  "problem_id": 1,
  "title": "Two Sum",
  "difficulty": "Easy",
  "time_limit": 1.0,
  "memory_limit": 256
}
```

#### Paginated List:
```json
{
  "total": 524,
  "skip": 0,
  "limit": 50,
  "items": [ ... ]
}
```

---

### B. Standard Error Envelope
All error responses (4xx and 5xx) strictly follow the universal error envelope:

```json
{
  "error": {
    "code": "ERROR_CODE_STRING",
    "message": "Human-readable explanation of what went wrong.",
    "details": {}
  }
}
```

#### Error Code Catalog:
| HTTP Status | Error Code | Example Scenario |
|---|---|---|
| `400 Bad Request` | `BAD_REQUEST` | Malformed parameters or syntax error. |
| `401 Unauthorized` | `AUTHENTICATION_FAILED` | Missing, expired, or invalid JWT Bearer token. |
| `403 Forbidden` | `PERMISSION_DENIED` | Non-admin attempting problem creation or user attempting to view another's submission (IDOR). |
| `404 Not Found` | `RESOURCE_NOT_FOUND` | Problem ID or submission ID does not exist. |
| `409 Conflict` | `DUPLICATE_RESOURCE` | Attempting to signup with an already registered username. |
| `422 Unprocessable Entity`| `VALIDATION_ERROR` | Request payload fails Pydantic validation (returns `{"errors": [...]}`). |
| `429 Too Many Requests` | `RATE_LIMIT_EXCEEDED` | Exceeded 5 login attempts/min or 10 submissions/min. |
| `500 Internal Error` | `INTERNAL_SERVER_ERROR` | Unhandled server exception (stack trace logged internally, sanitized for client). |

---

## 3. Input Validation Standards (Pydantic v2)

1. **Zero Raw Dicts:** No route handler may consume raw untyped dictionaries or `request.json()`. All input bodies must be explicitly typed Pydantic models extending `BaseModel`.
2. **String Sanitization:** All user strings (titles, code, bio) must define explicit `min_length` and `max_length` constraints to prevent buffer memory bloat.
3. **Strict Enums:** State and category fields (e.g. `ProblemDifficulty`, `LanguageEnum`, `UserRole`) must use Python `Enum` bindings. Invalid enum values are rejected with `422 Unprocessable Entity`.

---

## 4. Idempotency Standard for Mutating Endpoints

To prevent duplicate code submissions or duplicate contest penalties caused by network jitter or rapid double-clicks:
1. Mutating endpoints (`POST /api/v1/submissions`) support the optional `Idempotency-Key: <UUID>` header.
2. The server creates a Redis cache key: `idempotency:{user_id}:{idempotency_key}` with a **120-second TTL**.
3. If a request is received with an existing idempotency key within 120 seconds, the server skips evaluation and returns the previously created submission record directly with `X-Cache: HIT`.

---

## 5. Pagination Standards

* **Simple Collections (`GET /api/v1/problems`):**
  * Uses limit-and-offset pagination via query parameters: `skip: int = 0` (default 0), `limit: int = 50` (max 100).
  * Returns `total`, `skip`, `limit`, and `items`.
* **High-Volume Historical Feeds (`GET /api/v1/submissions`):**
  * Supports cursor-based filtering via `before_id: Optional[int]` or `created_before: Optional[datetime]` to prevent expensive `OFFSET` query degradation on large tables.

---

## 6. Layer 5 Verification Checklist

- [x] Every endpoint has an explicit Pydantic input validation schema.
- [x] Error responses across all endpoints share the exact same JSON error envelope (`{"error": {"code", "message", "details"}}`).
- [x] Mutating endpoints support `Idempotency-Key` to safely prevent duplicate submissions.
- [x] List endpoints have bounds enforced (`limit <= 100`); unbounded list queries are forbidden.
- [x] Route handlers delegate business logic to services/helpers; no raw SQL queries in route handlers.
