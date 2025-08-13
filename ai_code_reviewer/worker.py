# ai_code_reviewer/worker.py
import time
import base64
import jwt
import httpx
from celery import Celery
from radon.visitors import ComplexityVisitor

from .settings import settings

# Celery app setup is the same
celery_app = Celery("worker", broker="redis://redis:6379/0", backend="redis://redis:6379/0")

def get_github_installation_token(repo_full_name: str) -> str:
    """Authenticates as the GitHub App to get a temporary token for a specific installation."""
    # Step 1: Decode the private key
    private_key_bytes = base64.b64decode(settings.GITHUB_PRIVATE_KEY_BASE64)

    # Step 2: Create a JSON Web Token (JWT)
    now = int(time.time())
    payload = {
        'iat': now - 60,         # Issued at time
        'exp': now + (10 * 60),  # Expiration time (10 minutes)
        'iss': settings.GITHUB_APP_ID  # Issuer (our app's ID)
    }
    app_jwt = jwt.encode(payload, private_key_bytes, algorithm='RS256')

    # Step 3: Use the JWT to find the installation ID for the repo
    headers = {'Authorization': f'Bearer {app_jwt}', 'Accept': 'application/vnd.github.v3+json'}
    repo_owner, repo_name = repo_full_name.split('/')
    install_url = f'https://api.github.com/repos/{repo_owner}/{repo_name}/installation'
    
    with httpx.Client() as client:
        response = client.get(install_url, headers=headers)
        response.raise_for_status()
        installation_id = response.json()['id']

        # Step 4: Use the installation ID to get a short-lived access token
        token_url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
        response = client.post(token_url, headers=headers)
        response.raise_for_status()
        return response.json()['token']

# The task signature now accepts commit_id
@celery_app.task
def analyze_pull_request(repo_name: str, pr_id: int, commit_id: str):
    """
    Fetches PR files, analyzes them, and posts comments on high-complexity functions.
    """
    print(f"✅ Starting analysis for {repo_name} PR #{pr_id} on commit {commit_id[:7]}")
    try:
        token = get_github_installation_token(repo_name)
        headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github.v3+json'}

        pr_files_url = f'https://api.github.com/repos/{repo_name}/pulls/{pr_id}/files'
        
        with httpx.Client(follow_redirects=True) as client:
            response = client.get(pr_files_url, headers=headers)
            response.raise_for_status()
            files = response.json()

            for file in files:
                filename = file['filename']
                if not filename.endswith('.py'):
                    continue

                print(f"  Analysing file: {filename}")
                
                content_response = client.get(file['raw_url'], headers=headers)
                content_response.raise_for_status()
                code_content = content_response.text

                visitor = ComplexityVisitor.from_code(code_content)
                for function in visitor.functions:
                    if function.complexity > 10:
                        # --- THIS IS THE NEW COMMENTING LOGIC ---
                        comment_body = (
                            f"### Complexity Warning 🤖\n\n"
                            f"Function `'{function.name}'` has a cyclomatic complexity of **{function.complexity}**. "
                            f"Consider refactoring to keep complexity below 10 for better maintainability."
                        )
                        
                        # The API endpoint for posting a review comment
                        comments_url = f"https://api.github.com/repos/{repo_name}/pulls/{pr_id}/comments"
                        
                        comment_payload = {
                            "body": comment_body,
                            "commit_id": commit_id,
                            "path": filename,
                            "line": function.lineno,
                        }
                        
                        print(f"    Posting comment for function '{function.name}' on line {function.lineno}...")
                        comment_response = client.post(comments_url, headers=headers, json=comment_payload)
                        comment_response.raise_for_status()
                        # --- END OF NEW LOGIC ---
        
        print(f"✅ Analysis finished for {repo_name} PR #{pr_id}")

    except Exception as e:
        print(f"❌ Error during analysis for {repo_name} PR #{pr_id}: {e}")