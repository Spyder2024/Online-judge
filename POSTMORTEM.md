# Phase R2: Postmortem Analysis

## Incident Summary
On 2026-09-08, following commit `1e1e967` ("feat(platform): upgrade Code Captain to professional production grade (Phases 0-7)"), Code Captain suffered a critical production outage:
- Home page problem list was completely empty.
- Navigation links and action buttons were completely unresponsive.
- Sign In button did not open the authentication modal.
- Global leaderboard displayed zero content.

---

## 1. Breakdown of Symptoms & Root Causes

### Symptom 1: Home page content missing / blank, all buttons unresponsive
- **Root Cause**: A fatal JavaScript `SyntaxError: Identifier 'FALLBACK_PROBLEMS' has already been declared` in `frontend/index.html`.
- **Mechanism**: The variable `FALLBACK_PROBLEMS` was declared as a `const` twice in the same global script scope (lines 1715 and 1760). In JavaScript, a syntax error during script compilation halts the entire `<script>` block before a single statement is executed.
- **Specific Spec Task**: Phase 1 (`PH-06`) / Global SPA runtime insertion.
- **Why It Broke User Actions**: None of the client-side functions (`fetchProblems`, `navigateTo`, `toggleAuthModal`, `selectProblem`, `switchTab`) were registered. Inline event handlers (`onclick="toggleAuthModal()"`) threw `Uncaught ReferenceError`.

### Symptom 2: Leaderboard page empty
- **Root Cause**: In tandem with the client script syntax error, the backend `/api/v1/contests/1/leaderboard` endpoint threw unhandled 500 exceptions when Redis was unreachable in the serverless environment.
- **Specific Spec Task**: Phase 3 (`LB-02`) and Phase 6 (`SYS-02`).
- **Why It Broke**: The endpoint relied directly on an active Redis connection without a fallback try/catch block, causing unhandled server crashes when Redis was down.

### Symptom 3: Database 500 errors on Neon PostgreSQL
- **Root Cause**: Neon database connection strings include `?sslmode=require&channel_binding=require`. The `asyncpg` driver in SQLAlchemy does not accept `sslmode` or `channel_binding` keyword arguments, throwing `TypeError: connect() got an unexpected keyword argument 'sslmode'`.
- **Specific Spec Task**: Initial project deployment config.

---

## 2. Process Failures & Missing Guardrails

1. **Monolithic Multi-Phase Commit**:
   - Committing Phases 0 through 7 (+2553 lines across 13 files) in a single git commit made it impossible to isolate which change caused breakage.
   - *Guardrail to Prevent*: **Atomic Per-Task Commits**. Each task ID must be committed, built, and verified in isolation.

2. **Absence of Headless Syntax Validation Before Commit**:
   - `frontend/index.html` contains embedded `<script>` blocks. While Python files were compiled using `py_compile`, the JavaScript script blocks were not validated with Node (`node -c`).
   - *Guardrail to Prevent*: **Pre-commit script syntax gate** (`node -c`).

3. **Breaking API Contracts without Backward Compatibility**:
   - Renaming endpoints or changing expectations without aliases broke existing integrations.
   - *Guardrail to Prevent*: **Never rename without an alias**. Both old and new routes must respond (`/health` and `/api/v1/health`).

4. **Lack of Automated Smoke Testing**:
   - The deployment was declared successful based purely on HTTP 200 on `/`, without checking whether the frontend scripts actually parsed and ran without runtime errors.
   - *Guardrail to Prevent*: **Automated Smoke Test Suite** that executes in a headless browser or checks all API responses and JS parsing.
