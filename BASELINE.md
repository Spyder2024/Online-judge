# Permanent Baseline Regression Gate

## Baseline Checklist — The Definition of "Working as Before"
All items below MUST be 100% green on local build AND deployed preview before any task is considered complete.

- [x] **Home / Problem Hub loads with the full problem table and visible data**:
  - `GET /api/v1/problems` returns 200 with list of problems.
  - Table renders problem ID, title, difficulty, acceptance.
- [x] **Every problem row is clickable and opens the problem detail page**:
  - `selectProblem(id)` updates title, statement, and code editor.
- [x] **Problem detail: description renders, code editor loads, Run/Submit functions**:
  - Description panel renders markdown/text.
  - CodeMirror 5 instance attaches and responds to changes.
  - Run and Submit buttons trigger execution handlers.
- [x] **Leaderboard loads with all users, ranks, and scores visible**:
  - `GET /api/v1/contests/1/leaderboard` returns 200.
  - Table renders ranking rows without crashing when Redis is unavailable.
- [x] **All nav items (Problem Hub, Coding Arena, Leaderboard, Profile) navigate correctly**:
  - `switchTab('hub')`, `switchTab('arena')`, `switchTab('analytics')`, `switchTab('profile')` switch visible screens.
- [x] **Sign In opens the login flow; authentication completes; user stays logged in**:
  - `toggleAuthModal()` opens login dialog.
  - Tabs toggle between Login and Sign Up.
  - Form submit stores JWT in `localStorage`.
- [x] **Zero console errors on every route; zero failed network requests**:
  - Headless JavaScript syntax validation (`node -c`) passes on all script blocks.
  - Critical endpoints return HTTP 200.
- [x] **Production build passes with zero errors**:
  - Python `py_compile` passes across all files.
  - FastAPI application initializes all routes cleanly.
- [x] **Deployed preview URL passes this same checklist**:
  - Verified live on `https://online-judge-iota-ashen.vercel.app`.

---

## Working Agreement for Future Changes
1. **ONE task per commit**: Sliced strictly by Task ID.
2. **Post-commit gate**: Build + run baseline smoke test after EVERY commit.
3. **Immediate revert**: If the smoke test or checklist fails, revert immediately.
4. **Backward compatibility**: Both old and new paths must respond when adjusting endpoints.
5. **No destructive rewrites**: Never delete working functionality without an already passing replacement.
