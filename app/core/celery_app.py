from celery import Celery
from app.core.config import settings

# Initialize Celery app backed by Redis
celery_app = Celery(
    "online_judge_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Explicit routing to strict queues
celery_app.conf.task_routes = {
    "app.tasks.execution.evaluate_submission_task": {"queue": "q_compile_exec"},
    "app.tasks.ai.analyze_submission_task": {"queue": "q_ai_analysis"},
}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)
