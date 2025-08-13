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

@celery_app.task
def analyze_pull_request(repo_name: str, pr_id: int):
    """
    Fetches PR files and analyzes them for cyclomatic complexity.
    """
    print(f"✅ Starting analysis for {repo_name} PR #{pr_id}")
    try:
        # Get an installation token to interact with the repository
        token = get_github_installation_token(repo_name)
        headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github.v3+json'}

        # Get the list of files in the pull request
        pr_files_url = f'https://api.github.com/repos/{repo_name}/pulls/{pr_id}/files'
        with httpx.Client() as client:
            response = client.get(pr_files_url, headers=headers)
            response.raise_for_status()
            files = response.json()

            for file in files:
                filename = file['filename']
                if not filename.endswith('.py'):
                    continue # Skip non-python files

                print(f"  Analysing file: {filename}")
                
                # Download the file content
                content_response = client.get(file['raw_url'], headers=headers)
                content_response.raise_for_status()
                code_content = content_response.text

                # Analyze for cyclomatic complexity
                visitor = ComplexityVisitor.from_code(code_content)
                for function in visitor.functions:
                    # We'll just print for now. Later we'll post this as a comment.
                    if function.complexity > 10:
                        print(f"    ❗️ High complexity in function '{function.name}': {function.complexity} (line {function.lineno})")
        
        print(f"✅ Analysis finished for {repo_name} PR #{pr_id}")

    except Exception as e:
        print(f"❌ Error during analysis for {repo_name} PR #{pr_id}: {e}")