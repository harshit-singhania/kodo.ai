# ai_code_reviewer/worker.py
import time
import base64
import jwt
import httpx
import tempfile
import os
import subprocess
import json
from celery import Celery
from radon.visitors import ComplexityVisitor
# We no longer need to import from flake8's internal API
# from flake8.api import legacy as flake8_legacy

from .settings import settings

celery_app = Celery("worker", broker="redis://redis:6379/0", backend="redis://redis:6379/0")

# --- get_github_installation_token is unchanged ---
def get_github_installation_token(repo_full_name: str) -> str:
    # (This function is unchanged)
    private_key_bytes = base64.b64decode(settings.GITHUB_PRIVATE_KEY_BASE64)
    now = int(time.time())
    payload = {'iat': now - 60, 'exp': now + (10 * 60), 'iss': settings.GITHUB_APP_ID}
    app_jwt = jwt.encode(payload, private_key_bytes, algorithm='RS256')
    headers = {'Authorization': f'Bearer {app_jwt}', 'Accept': 'application/vnd.github.v3+json'}
    repo_owner, repo_name = repo_full_name.split('/')
    install_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/installation'
    with httpx.Client() as client:
        response = client.get(install_url, headers=headers)
        response.raise_for_status()
        installation_id = response.json()['id']
        token_url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
        response = client.post(token_url, headers=headers)
        response.raise_for_status()
        return response.json()['token']

# --- run_complexity_analysis is unchanged ---
def run_complexity_analysis(code_content: str) -> list:
    # (This function is unchanged)
    issues = []
    visitor = ComplexityVisitor.from_code(code_content)
    for function in visitor.functions:
        if function.complexity > 10:
            issues.append({"line": function.lineno, "message": f"High Complexity: Function `{function.name}` has a complexity of **{function.complexity}**. (Threshold > 10)"})
    return issues

# --- run_security_analysis using subprocess is unchanged ---
def run_security_analysis(code_content: str, filename: str) -> list:
    # (This function is unchanged)
    issues = []
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.py', delete=False) as temp_file:
        temp_file.write(code_content)
        temp_file_path = temp_file.name
    try:
        command = ["/app/.venv/bin/bandit", "-f", "json", temp_file_path]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.stdout:
            report = json.loads(result.stdout)
            for issue in report["results"]:
                issues.append({"line": issue["line_number"], "message": f"Security Issue ({issue['test_id']}): **{issue['issue_text']}** (Severity: {issue['issue_severity']}, Confidence: {issue['issue_confidence']})"})
    finally:
        os.remove(temp_file_path)
    return issues

# --- **FINAL CORRECTED** LINTING FUNCTION USING SUBPROCESS ---
def run_linting_analysis(code_content: str, filename: str) -> list:
    issues = []
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.py', delete=False) as temp_file:
        temp_file.write(code_content)
        temp_file_path = temp_file.name
    
    try:
        # We provide the full path to flake8 and run it as a subprocess
        command = ["/app/.venv/bin/flake8", temp_file_path]
        result = subprocess.run(command, capture_output=True, text=True)
        
        # Flake8 prints one issue per line to stdout
        if result.stdout:
            for line in result.stdout.strip().splitlines():
                # Line format is typically: path:line:col: code message
                parts = line.split(':')
                if len(parts) >= 4:
                    line_number = int(parts[1])
                    # Re-join the rest of the message in case it contains colons
                    error_message = ':'.join(parts[3:]).strip()
                    error_code = parts[2].strip()
                    issues.append({
                        "line": line_number,
                        "message": f"Linter ({error_code}): {error_message}"
                    })
    finally:
        os.remove(temp_file_path)
        
    return issues

# --- The main task is unchanged ---
@celery_app.task
def analyze_pull_request(repo_name: str, pr_id: int, commit_id: str):
    """
    The main task that orchestrates all analysis and posts a single review.
    """
    print(f"✅ Starting all analyses for {repo_name} PR #{pr_id}")
    try:
        token = get_github_installation_token(repo_name)
        headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github.v3+json'}
        pr_files_url = f'https://api.github.com/repos/{repo_name}/pulls/{pr_id}/files'
        
        comments_for_review = []
        total_issues = 0

        with httpx.Client(follow_redirects=True) as client:
            # First, get the list of files
            response = client.get(pr_files_url, headers=headers)
            response.raise_for_status()
            files = response.json()

            # Then, loop through and analyze each file
            for file in files:
                filename = file['filename']
                if not filename.endswith('.py'):
                    continue
                print(f"  Analysing file: {filename}")
                content_response = client.get(file['raw_url'], headers=headers)
                content_response.raise_for_status()
                code_content = content_response.text
                
                all_issues = []
                all_issues.extend(run_complexity_analysis(code_content))
                all_issues.extend(run_security_analysis(code_content, filename))
                all_issues.extend(run_linting_analysis(code_content, filename))
                
                if not all_issues:
                    continue
                    
                for issue in all_issues:
                    total_issues += 1
                    comments_for_review.append({"path": filename, "line": issue["line"], "body": issue["message"]})

            # --- MOVED THIS BLOCK ---
            # Now, post the review while the client is still open
            if total_issues > 0:
                review_url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_id}/reviews"
                review_body = (
                    f"### Kodo.ai Analysis Complete 🤖\n\n"
                    f"I found **{total_issues}** potential issue(s) in this pull request. "
                    f"Please see the comments on the specific lines for details."
                )
                review_payload = {
                    "commit_id": commit_id,
                    "body": review_body,
                    "event": "COMMENT",
                    "comments": comments_for_review
                }
                
                print(f"Posting a review with {len(comments_for_review)} comments...")
                review_response = client.post(review_url, headers=headers, json=review_payload)
                review_response.raise_for_status()
        
        print(f"✅ Analysis finished for {repo_name} PR #{pr_id}")

    except Exception as e:
        print(f"❌ Error during analysis for {repo_name} PR #{pr_id}: {e}")
