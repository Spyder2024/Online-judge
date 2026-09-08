from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from structlog import get_logger
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import async_engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_structured_logging
from app.core.redis import close_redis_pool, init_redis_pool

# Initialize structured logging before application setup
setup_structured_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    FastAPI lifespan context manager initializing asynchronous resources
    (Redis connection pool, database connectivity check) on startup and releasing on shutdown.
    """
    logger.info("Starting AI-Enhanced Online Judge Platform backend...", environment=settings.ENVIRONMENT)
    try:
        # Initialize Redis connection pooling
        await init_redis_pool()
        logger.info("Redis async connection pool initialized successfully.")
    except Exception as e:
        logger.warning("Redis pool initialization skipped or failed during startup", error=str(e))

    yield

    logger.info("Shutting down AI-Enhanced Online Judge Platform backend...")
    try:
        await close_redis_pool()
        await async_engine.dispose()
        logger.info("All async connection pools closed cleanly.")
    except Exception as e:
        logger.warning("Resource cleanup exception during shutdown", error=str(e))


def create_application() -> FastAPI:
    """
    Factory function creating and configuring the core FastAPI application instance.
    Sets up CORS, lifespan handlers, global exception handlers, and API routers.
    """
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="1.0.0",
        description="Phase 1 Backend API for AI-Enhanced Online Judge Platform with 13-table schema and pgvector 1536-dim HNSW indexing.",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict in production via environment settings
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register unified global exception handlers
    register_exception_handlers(app)

    from fastapi.responses import Response
    from app.api.v1.websocket import router as ws_router

    # Include v1 API routes & root level WebSocket router
    app.include_router(api_router, prefix=settings.API_V1_STR)
    app.include_router(ws_router)

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return Response(status_code=204)

    @app.get("/health", tags=["Health & Monitoring"])
    @app.get(f"{settings.API_V1_STR}/health", tags=["Health & Monitoring"])
    async def health_check() -> dict[str, str]:
        """
        Liveness and readiness probe endpoint.
        """
        return {"status": "ok", "environment": settings.ENVIRONMENT, "version": "1.0.0"}

    @app.post("/run", include_in_schema=False)
    async def run_code_fallback(payload: dict):
        """
        Compiler Engine fallback endpoint for local development.
        Executes code in isolated subprocess and returns stdout/stderr JSON payload.
        """
        import subprocess, sys, tempfile, os
        lang = payload.get("language", "py")
        code = payload.get("code", "")
        input_data = payload.get("input", "")

        if lang in ["py", "python3"]:
            with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
                f.write(code)
                f_path = f.name
            try:
                proc = subprocess.run(
                    [sys.executable, f_path],
                    input=input_data,
                    text=True,
                    capture_output=True,
                    timeout=5
                )
                return {"output": proc.stdout, "error": proc.stderr}
            except subprocess.TimeoutExpired:
                return {"output": "", "error": "Time Limit Exceeded"}
            except Exception as e:
                return {"output": "", "error": str(e)}
            finally:
                if os.path.exists(f_path):
                    try:
                        os.remove(f_path)
                    except Exception:
                        pass

        return {"output": "", "error": "Unsupported language fallback"}

    # Mount static frontend application UI
    from pathlib import Path
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    
    frontend_path = Path(__file__).parent / "frontend"
    if frontend_path.exists():
        app.mount("/static", StaticFiles(directory=frontend_path), name="static")
        
        @app.get("/", include_in_schema=False)
        async def serve_index():
            return FileResponse(
                frontend_path / "index.html",
                headers={"Cache-Control": "no-cache, no-store, must-revalidate"}
            )

    return app


app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
