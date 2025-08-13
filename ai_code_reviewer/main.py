# ai_code_reviewer/main.py

# --- START: Added Imports ---
import hashlib
import hmac
# Note: We are expanding the import from fastapi
from fastapi import FastAPI, Request, HTTPException, Header
# --- END: Added Imports ---

from .worker import dummy_analysis_task
from .settings import settings

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
    task = dummy_analysis_task.delay(repo_name=repo_name, pr_id=pr_id)
    return {"message": "Analysis has been queued.", "task_id": task.id}

@app.post("/api/webhook", tags=["GitHub"])
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None)
):
    """
    Receives, verifies, and processes webhook events from GitHub.
    """
    # --- This part is the same: signature verification ---
    if not x_hub_signature_256:
        raise HTTPException(status_code=401, detail="X-Hub-Signature-256 header is missing!")

    payload_body = await request.body()
    hash_object = hmac.new(settings.GITHUB_WEBHOOK_SECRET.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()

    if not hmac.compare_digest(expected_signature, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Request signature does not match!")

    # --- This is the new logic: parse the payload and trigger the task ---
    payload_json = await request.json()
    event_type = request.headers.get("X-GitHub-Event")

    if event_type == "pull_request":
        action = payload_json.get("action")
        # We only care about PRs being opened or updated with new commits
        if action in ["opened", "synchronize"]:
            repo_name = payload_json["repository"]["full_name"]
            pr_number = payload_json["number"]

            print(f"✅ Valid PR event received: '{action}' on {repo_name} #{pr_number}")
            print("🚀 Triggering background analysis task...")

            # This is where we call our Celery task with real data!
            dummy_analysis_task.delay(repo_name=repo_name, pr_id=pr_number)

    return {"status": "success"}