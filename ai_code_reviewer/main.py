# ai_code_reviewer/main.py

# 1. Standard library imports
import hashlib
import hmac

# 2. Third-party imports
from fastapi import FastAPI, Request, HTTPException, Header

# 3. Local application imports
from .worker import analyze_pull_request
from .settings import settings

app = FastAPI(
    title="Kodo.ai",
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
    Manually triggers a background analysis task for a given repository and PR.
    This is useful for debugging.
    """
    # FIXED: This now correctly calls our real analysis task.
    task = analyze_pull_request.delay(repo_name=repo_name, pr_id=pr_id)
    return {"message": "Analysis has been queued.", "task_id": task.id}

@app.post("/api/webhook", tags=["GitHub"])
async def github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None)
):
    """
    Receives, verifies, and processes webhook events from GitHub.
    """
    # --- Signature verification ---
    if not x_hub_signature_256:
        raise HTTPException(status_code=401, detail="X-Hub-Signature-256 header is missing!")

    payload_body = await request.body()
    hash_object = hmac.new(settings.GITHUB_WEBHOOK_SECRET.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()

    if not hmac.compare_digest(expected_signature, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Request signature does not match!")

    # --- Parse payload and trigger task ---
    payload_json = await request.json()
    event_type = request.headers.get("X-GitHub-Event")

    if event_type == "pull_request":
        action = payload_json.get("action")
        # We only care about PRs being opened or updated with new commits
        if action in ["opened", "synchronize"]:
            repo_name = payload_json["repository"]["full_name"]
            pr_number = payload_json["number"]
            # Get the specific commit SHA for the PR's head
            commit_id = payload_json["pull_request"]["head"]["sha"]

            print(f"✅ Valid PR event received: '{action}' on {repo_name} #{pr_number}")
            print("🚀 Triggering background analysis task...")

            # Pass the new commit_id to the task
            analyze_pull_request.delay(
                repo_name=repo_name,
                pr_id=pr_number,
                commit_id=commit_id
            )

    return {"status": "success"}