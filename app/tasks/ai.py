from app.core.celery_app import celery_app

@celery_app.task(bind=True, name="app.tasks.ai.analyze_submission_task")
def analyze_submission_task(self, task_id: str, submission_id: int):
    """
    Placeholder for AI review generation, dispatched to `q_ai_analysis`.
    Will utilize LLM APIs and PGVector lookups.
    """
    pass
