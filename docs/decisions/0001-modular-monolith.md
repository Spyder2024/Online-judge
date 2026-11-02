# ADR 0001: Modular Monolith Architecture over Microservices

**Date:** 2026-11-02  
**Status:** Accepted  
**Deciders:** Lead Architect & Core Engineering Team  

---

## Context

When architecting a competitive programming and technical interview SaaS platform, the primary architectural decision is choosing between a **microservices topology** (separate services for Auth, Catalog, Submissions, Leaderboards, AI) and a **modular monolith** (a single unified codebase with cleanly segregated domain modules).

Modern developer discourse frequently pushes microservices early. However, early-stage SaaS platforms face substantial risks with microservices:
1. High operational overhead (multiple deployments, service discovery, cross-service network latency).
2. Distributed transaction complexity (lack of ACID transactions across services).
3. Slower developer velocity and complex local setup.
4. Unnecessary infrastructure and cloud costs.

## Decision

We chose a **Python 3.12 + FastAPI Async Modular Monolith** with clean domain boundaries and an out-of-process Dockerized compiler execution worker.

### Module Structure
```
app/
├── api/v1/         # Route handlers & HTTP controllers
├── core/           # Cross-cutting concerns: Config, DB connection, Redis, Security
├── models/         # SQLAlchemy ORM entity definitions
├── schemas/        # Pydantic v2 validation contracts
├── services/       # Core business logic (Leaderboard, Sandbox client, AI)
└── tasks/          # Asynchronous worker jobs
```

### Module Boundary Rules
1. **No Circular Imports**: Submissions depends on Problems and Users, but Problems never imports Submissions.
2. **Schema-Guarded Communication**: Internal service methods pass validated Pydantic models, not raw dictionaries or untyped request objects.
3. **Dedicated Worker for Sandbox Execution**: Untrusted code execution is strictly decoupled from the monolith web process. Web processes only enqueue tasks; execution happens in isolated runner containers.

## Consequences

### Positive
* **Rapid Velocity**: Single codebase, unified linting, straightforward debugging, single Git repository.
* **ACID Transactions**: Relational guarantees across problems, test cases, and submissions without distributed 2PC (two-phase commit) overhead.
* **Cost Efficiency**: Runs effortlessly on serverless infrastructure (Vercel ASGI) and serverless databases (Neon).
* **Clear Migration Path**: If a single module (e.g. the Judge Orchestrator) experiences extreme load, its clean boundaries allow extracting it into a standalone microservice with minimal refactoring.

### Negative / Trade-Offs
* Single deployable unit: A bug in route configuration can affect the entire API (mitigated by automated critical-path smoke tests in CI).
* Scaling must happen as a whole unit, except for the isolated compiler worker which scales horizontally independently.
