# Architectural Context & Deviations Analysis

## 1. Detected Technology Stack

- **Backend Framework**: Python FastAPI (v0.111+) with AsyncIO, Pydantic v2, Structlog structured logging.
- **Database**: PostgreSQL with `pgvector` extension for 384/1536-dim vector embeddings, managed via SQLAlchemy 2.0 Async (`asyncpg`). Tested and compatible with Neon.tech / Supabase / AWS RDS.
- **Task Queue & Background Execution**: Celery 5.4 with Redis broker (`q_compile_exec`, `q_ai_analysis`).
- **Cache & Real-Time Event Streaming**: Redis 5.0+ Pub/Sub streaming via WebSocket endpoints (`/ws/submissions/{id}`).
- **Frontend Architecture**: High-performance Single-Page Application (SPA) served directly from `frontend/index.html` via FastAPI static mount and Vercel serverless rewrites.
- **UI Framework & Styling**: Modern Vanilla HTML5/ES6+ with Tailwind CSS (CDN), Custom CSS Variables for semantic design tokens (`--bg-main`, `--bg-surface`, `--amber`, etc.), Lucide Icons, and Chart.js.
- **Code Editor Library**: CodeMirror 5 with VS Code Dark+ theme and syntax highlighting modes for Python (`mode/python`), C++ (`mode/clike`), and Java. Configured with lazy-loading hooks and dynamic Monaco editor compatibility.
- **Deployment Platform**: Vercel Serverless ASGI function (`api/index.py` with `@vercel/python` and root rewrites in `vercel.json`).

---

## 2. Documented Deviations & Rationale

| Spec Requirement | Current / Planned Implementation | Rationale |
| :--- | :--- | :--- |
| **Framework Assumptions (e.g. Next.js / React)** | High-performance vanilla SPA in `frontend/index.html` powered by HTML5 History API (`pushState` / `popstate`) and client-side routing. | The existing codebase is built as a unified FastAPI + SPA architecture. Maintaining and upgrading this architecture preserves 100% route compatibility and lightning-fast zero-build deployment on Vercel. |
| **Dedicated Auth Routes (`/login`, `/signup`)** | Routes `/login` and `/signup` handled via PushState router + dedicated full-page views, with fallback to query parameter `?redirectTo=`. Direct browser hits rewrite cleanly via `main.py` and `vercel.json`. | Allows full bookmarking, direct navigation, and standard OAuth callback redirection while maintaining a single cohesive deployment. |
| **Sandbox Isolation (SYS-03)** | Hybrid architecture: Full Docker container cgroups isolation supported via external compiler microservice (`AlgoU-Online-Compiler-2`). Local/Serverless fallback uses isolated temporary Python subprocess with strict timeouts and pipe caps. | Serverless hosting (Vercel) lacks Docker daemon privileges (`/var/run/docker.sock`). Marking containerized syscall filters (seccomp/nsjail) as partially supported in microservice and gracefully deferred in serverless runtimes. |
| **Editor Choice (PD-04)** | CodeMirror 5 (with VS Code Dark+ styling, bracket matching, line numbers, autocomplete, and lazy chunk loading) with fallback container for Monaco. | Provides immediate 60fps responsiveness, zero bundle overhead, and cross-browser reliability. |
