# ai_code_reviewer/main.py

from fastapi import FastAPI
import uuid

# Create an instance of the FastAPI class
app = FastAPI(
    title="AI Code Review Assistant",
    description="An intelligent system that automatically detects bugs and suggests improvements.",
    version="0.1.0",
)

@app.get("/health", tags=["Status"])
async def health_check():
    """
    Endpoint to check if the service is running.
    """
    return {"status": "ok"}

@app.post("/analyze", tags=["Analysis"])
async def analyze_repository(repo_name: str, pr_id: int):
    """
    Triggers a background analysis task for a given repository and pull request.
    """
    # Use .delay() to send the task to the Celery queue and return immediately
    # Dummy module to simulate Celery tasks
    class DummyTask:
        def __init__(self, name):
            self.name = name
        
        def delay(self, **kwargs):
            self.id = str(uuid.uuid4())
            print(f"Task {self.name} started with parameters: {kwargs}")
            return self

    # Create a dummy task
    dummy_analysis_task = DummyTask("analyze_repository")

    # Queue the task
    task = dummy_analysis_task.delay(repo_name=repo_name, pr_id=pr_id)
    # Return the ID of the task that was created
    return {"message": "Analysis has been queued.", "task_id": task.id}