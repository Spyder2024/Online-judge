# Project: Code Captain Online Judge

## What this product does
Code Captain is a recruiter-grade competitive programming and technical interview prep SaaS platform. Candidates practice algorithmic challenges with isolated multi-language code execution, real-time WebSocket test streaming, automated AI code review, and live contest leaderboards.

## Stack (do not change without asking)
- **Frontend**: Single-Page Application (`frontend/index.html`) using Tailwind CSS, CodeMirror 5 (with VS Code Dark+ theme), Lucide Icons, and KaTeX math rendering.
- **Backend**: Python 3.12 + FastAPI (modular monolith) with async route handlers and Pydantic v2 validation.
- **Database**: Neon PostgreSQL (serverless with PgBouncer connection pooling) + `pgvector` for semantic problem search; ORM: SQLAlchemy 2.0 (async).
- **Cache & Real-time**: Upstash Redis (serverless) for sorted-set leaderboards, rate limiting, and pub/sub streaming.
- **Judge Sandbox**: Isolated Docker container (`compiler-engine/Dockerfile`) running under non-root unprivileged user `sandbox` with CPU and memory quotas.
- **Hosting**: Vercel Serverless (FastAPI via ASGI bridge) + GitHub automated deployment.

## Rules
- **Never commit secrets**: All secrets must reside in environment variables and be documented in `.env.example`.
- **API security standards**: Every new endpoint requires Pydantic input validation, authentication verification, object-level authorization (IDOR check), and standardized JSON error envelopes.
- **Database integrity**: Every schema modification must be tracked via an Alembic migration. Never mutate production databases manually.
- **Verification floor**: Run `python scripts/smoke_test.py` before marking any task as complete. All 8 critical-path tests must remain green.
- **Minimal dependencies**: Ask before adding any new third-party Python or JavaScript library.
- **Design consistency**: Maintain the dark gold/slate design system (`#0B0F14`, `#1A2233`, `#E6C38A`, `#94A3B8`). Never introduce hardcoded white cards or low-contrast elements.

## Commands
- **Dev Server**: `uvicorn backend.main:app --reload --port 8000`
- **Smoke Tests**: `python scripts/smoke_test.py`
- **Unit Tests**: `pytest tests/`
- **Lint / Syntax Check**: `python -m py_compile backend/main.py && node --check frontend/index.html`
- **Migrations**: `alembic upgrade head`

## Architecture Decisions
- System Design Document: [docs/system-design.md](docs/system-design.md)
- Architecture Decision Records: [docs/decisions/](docs/decisions/)
