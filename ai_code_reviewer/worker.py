# ai_code_reviewer/worker.py
import time
from celery import Celery

# Define the Celery application.
# The broker URL points to the redis service we will create in docker-compose.
celery_app = Celery(
    "worker",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0"
)

# This is a placeholder for our future analysis logic.
# For now, it just pretends to do work by sleeping.
@celery_app.task
def dummy_analysis_task(repo_name: str, pr_id: int):
    """
    A dummy task that simulates a code analysis.
    """
    print(f"Starting analysis for {repo_name}, PR #{pr_id}...")
    # Simulate a long-running task
    time.sleep(10)
    result = {"repo": repo_name, "pr_id": pr_id, "status": "complete", "issues_found": 5}
    print(f"Analysis complete for {repo_name}, PR #{pr_id}.")
    return result