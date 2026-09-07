# Upgrade Progress Tracking Checklist

## Phase 0 — Trust & Branding Fixes (P0)
- [x] **BR-01**: Brand unification: Replace all user-facing occurrences of "CodeJudge" with "Code Captain".
- [x] **LB-01**: Remove implementation leaks: Delete "ZSET Score" column and "Powered by Redis ZSET" subtitle.
- [x] **ST-01**: Real system status: Wire "System Operational" badge to `GET /api/v1/health` with real DB ping, queue depth, worker status, tooltip, and `/status` route.
- [x] **AUTH-01**: Auth as routes: Replace login modal with `/login` and `/signup` routes with `?redirectTo=` support.

## Phase 1 — Problem Hub (List Page)
- [x] **PH-01**: Status column: Add Solved (✓) / Attempted (●) / blank column for authenticated user.
- [x] **PH-02**: Difficulty badges: Color-coded with distinct icon/shape for Easy, Medium, Hard (WCAG 1.4.1).
- [x] **PH-03**: Tag chips: Clickable chips toggling active tag filter.
- [x] **PH-04**: Number & numeric formatting: "1" instead of "#1.", 1 decimal on acceptance, tabular-nums mono font.
- [x] **PH-05**: Search UX: 300ms debounce, `/` shortcut, clear (×) button, designed empty state.
- [x] **PH-06**: URL-synced filters & server-side search: `?search=&difficulty=&tag=&status=&sort=&page=`, browser back/forward support.
- [x] **PH-07**: Table interactions: Full-row hover, cursor: pointer, sticky table header, skeleton loaders.
- [x] **PH-08**: Sortable columns: Click-to-sort with visible indicator and `aria-sort`.

## Phase 2 — Problem Detail / Workspace
- [x] **PD-01**: Resizable split view: Draggable divider between description and editor, collapsible panel.
- [x] **PD-02**: Console panel: Output panel with custom stdin input field, stdout, stderr, exit code, line-mapped compile errors.
- [x] **PD-03**: Run vs Submit: Two distinct actions (Run = sample tests, Submit = full hidden test suite) with inline results.
- [x] **PD-04**: Code editor: Line numbers, bracket matching, autocomplete, error squiggles, font size controls, Cmd/Ctrl+Enter Run, Cmd+Shift+Enter Submit.
- [x] **PD-05**: Language selector: Proper dropdown with per-language time limit multipliers.
- [x] **PD-06**: Metadata bar: Structured bar above description with difficulty badge, time limit clock, memory limit.
- [x] **PD-07**: Tabs: Description | Submissions | Discussion | Editorial with empty states.
- [x] **PD-08**: Copy & navigation: Copy buttons on example I/O, breadcrumbs "Problem Hub / 1. Two Sum", page title.
- [x] **PD-09**: Submission history: Verdict badge, language, runtime, memory, relative timestamp.

## Phase 3 — Leaderboard
- [x] **LB-02**: Truly live: Auto-refreshing updates (every 5s or SSE/WS) with "Updated Xs ago · auto-refreshing" microcopy.
- [x] **LB-03**: Visual identity: Avatars (DiceBear / initials), rank-delta arrows ▲/▼, crown/medal styling for top 3.
- [x] **LB-04**: Tie-breaking: Score DESC → earliest achievement ASC with tooltip on Rank header.
- [x] **LB-05**: You-highlight: Highlight logged-in user row with "You" chip and sticky positioning.
- [x] **LB-06**: Time periods & persistence: All-time / Weekly tabs, no "pts" suffix in cells.

## Phase 4 — Auth Hardening
- [x] **AUTH-02**: Login form quality: Email or username login, password visibility toggle, inline errors, loading spinner, Enter to submit, autofocus.
- [x] **AUTH-03**: Security: Generic error messages ("Invalid credentials"), rate-limit lockout warning, forgot password flow.
- [x] **AUTH-04**: OAuth: Brand-styled Google and GitHub OAuth buttons with account merge strategy.
- [x] **AUTH-05**: Form conventions: Sentence-case labels, consistent input styling, terms/privacy links.

## Phase 5 — Global Chrome & Design System
- [x] **GC-01**: Design tokens: CSS variables for color, spacing (8px grid), radius, shadow, typography. Layered dark palette (#0d1117 family).
- [x] **GC-02**: Navigation: Active-state indicator pill on all routes; avatar dropdown (Profile / Settings / Sign out) post-login; single "Sign In" button pre-login.
- [x] **GC-03**: Footer: Terms, Privacy, Status, About, version on all views.
- [x] **GC-04**: Typography: Inter UI font, JetBrains Mono for code + tabular numbers, `font-display: swap`.

## Phase 6 — Backend / System Design
- [x] **SYS-01**: Verdict taxonomy: AC / WA / TLE / MLE / RE / CE / PE / SE with colored badge + icon.
- [x] **SYS-02**: Async judge pipeline: Idempotent submission queuing, backoff, fault handling.
- [x] **SYS-03**: Sandbox isolation: Docker container cgroups isolation via microservice, safe fallback documented.
- [x] **SYS-04**: Real-time verdict push: WebSocket channel `/ws/submissions/:id` with live state progression.
- [x] **SYS-05**: Testcase model: Sample vs hidden testcases with per-language multipliers.
- [x] **SYS-06**: Rate limiting: Submission rate limiting.
- [x] **SYS-07**: Data model: Indexes and foreign key integrity.
- [x] **SYS-08**: Server-side search: Postgres FTS / query matching on problems.
- [x] **SYS-09**: Observability: Health endpoint with DB ping, Redis status, queue depth.
- [x] **SYS-10**: API discipline: Namespace `/api/v1/…`, OpenAPI documentation.

## Phase 7 — Polish: A11y, Mobile, SEO, States
- [x] **UX-01**: Toasts: Toast notification system (`aria-live="polite"`).
- [x] **UX-02**: Error surfaces: Designed 404 / 500 / offline views.
- [x] **UX-03**: Focus rings: Visible 2px focus ring with offset on all interactive elements.
- [x] **UX-04**: Shortcuts: `/` focuses search; Cmd/Ctrl+K opens command palette.
- [x] **UX-05**: Data formatting: Relative timestamps (`timeAgo()`) with absolute date hover tooltips.
- [x] **UX-06**: Mobile responsiveness: Responsive tables collapsing to cards at <768px (tested at 375px).
- [x] **UX-07**: SEO / meta: Route-specific `<title>`, meta description, OpenGraph tags, favicon.
- [x] **UX-08**: Motion & performance: Respect `prefers-reduced-motion`, smooth transitions.
- [x] **UX-09**: Micro-polish: Custom themed scrollbars, scroll shadows, skeleton loaders.
