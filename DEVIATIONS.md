# Architecture & Specification Deviations

## 1. Stack Detection & Confirmation
- **Prompt Presupposition**: React, TypeScript, Monaco Editor, Framer Motion, Tailwind build pipeline.
- **Actual Repository Architecture**:
  - Backend: FastAPI (Python 3.12 / uv) on Vercel Serverless Functions.
  - Database: PostgreSQL (Neon / asyncpg) + pgvector + SQLAlchemy 2.0.
  - Caching & Queue: Redis + Celery worker (`q_compile_exec`).
  - Frontend: Single-page application in `frontend/index.html` using Tailwind CSS CDN, Lucide Icons, and CodeMirror 5.

## 2. Adaptation Strategy
- **No Heavy Build Tooling**: Rather than introducing an unconfigured Node/Webpack/Vite React build step that would break the existing Vercel deployment pipeline (`@vercel/static` + `@vercel/python`), all requested SaaS design enhancements, CSS design tokens, dual theme support (Dark/Light with black + gold aesthetic), 40/60 draggable split layout, stats cards, and micro-interactions are implemented directly in `frontend/index.html` with pure CSS custom properties and standard JavaScript.
- **Editor**: CodeMirror 5 with VS Code / Monaco Dark+ styling and mode switching (Python, C++, Java), font size controls, and fullscreen toggle.
