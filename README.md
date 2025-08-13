# Kodo.ai: AI-Powered Code Review Assistant

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com)
[![License: CC BY-NC-SA 4.0](https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png)](https://creativecommons.org/licenses/by-nc-sa/4.0/)


An intelligent code review system that automatically analyzes pull requests, detects potential issues like high code complexity, and posts feedback directly on GitHub as a PR comment.

## ✨ Core Features (Current)

- **GitHub Integration**: Listens to `pull_request` webhooks (`opened` and `synchronize` events).
- **Secure Authentication**: Uses a GitHub App with a private key and short-lived tokens to securely interact with the GitHub API.
- **Asynchronous Analysis**: Leverages Celery and Redis to run code analysis in the background without blocking the web server.
- **Static Code Analysis**: Performs static analysis on Python files to calculate cyclomatic complexity using `radon`.
- **Automated PR Commenting**: Automatically posts a warning comment on the specific line of a function if its complexity exceeds a defined threshold (currently >10).
- **Containerized Environment**: Fully containerized with Docker and Docker Compose for easy and consistent local development.

## 🏛️ Architecture Overview

The system is built with a modern Python backend and operates in an event-driven manner.

**Technology Stack:**
- **Backend**: Python, FastAPI, Celery
- **Message Broker**: Redis
- **Analysis Engine**: `radon`
- **Infrastructure**: Docker, Docker Compose
- **Integrations**: GitHub Apps & Webhooks

**Workflow:**
1.  A developer opens or updates a Pull Request on GitHub.
2.  GitHub sends a `pull_request` webhook to our service.
3.  An **ngrok** tunnel forwards the webhook to the local **FastAPI** `api` container.
4.  The API validates the webhook signature, parses the payload, and pushes an analysis job to **Redis**.
5.  A **Celery `worker`** picks up the job from the Redis queue.
6.  The worker authenticates with the GitHub API, fetches the PR files, and runs the complexity analysis.
7.  If an issue is found, the worker uses the GitHub API to post a comment back on the Pull Request.

## 🚀 Getting Started: Local Development Setup

Follow these steps to get the project running on your local machine.

## 🚀 Installation Options

Pick one of the following setups.

### Option A — Docker (recommended; no local Python needed)
- Prerequisites: Docker Desktop, ngrok, Git
- Steps:
  1. Clone:
     ```bash
     git clone https://github.com/harshit-singhania/kodo.ai.git
     cd ai-code-reviewer
     ```
  2. Create environment file:
     ```bash
     cp .env.example .env
     ```
     Fill values in `.env` (see “Configure Environment Variables” below).
  3. Launch:
     ```bash
     docker compose up --build
     ```
  4. Start ngrok:
     ```bash
     ngrok http 8000
     ```
  5. Set your GitHub App webhook URL to: https://<ngrok-forwarding-url>/api/webhook

### Option B — Linux (native dev)
- Prerequisites: Python 3.10+, Git, ngrok
- Steps:
  1. Install Poetry:
     ```bash
     python3 -m pip install --user pipx || true
     pipx install poetry || python3 -m pip install --user poetry
     ```
  2. Clone and install deps:
     ```bash
     git clone https://github.com/harshit-singhania/kodo.ai.git
     cd ai-code-reviewer
     poetry install
     ```
  3. Create `.env` and fill values (see “Configure Environment Variables” below).
  4. Recommended run method: use Docker Compose (Option A) to run services consistently.

### Option C — macOS (native dev)
- Prerequisites: Python 3.10+, Git, ngrok, Homebrew (optional)
- Steps:
  1. Install Python (via Homebrew, optional):
     ```bash
     brew install python
     ```
  2. Install Poetry:
     ```bash
     pipx install poetry || pip3 install --user poetry
     ```
  3. Clone and install deps:
     ```bash
     git clone https://github.com/harshit-singhania/kodo.ai.git
     cd ai-code-reviewer
     poetry install
     ```
  4. Create `.env` and fill values (see “Configure Environment Variables” below).
  5. Recommended run method: use Docker Compose (Option A).

### Option D — Windows (native dev)
- Prerequisites: Python 3.10+ (Add to PATH), Git, ngrok
- Steps (PowerShell):
  1. Install Poetry:
     ```powershell
     pipx install poetry; if ($LASTEXITCODE) { py -m pip install --user poetry }
     ```
  2. Clone and install deps:
     ```powershell
     git clone https://github.com/harshit-singhania/kodo.ai.git
     cd ai-code-reviewer
     poetry install
     ```
  3. Create `.env` and fill values (see “Configure Environment Variables” below).
  4. Recommended run method: use Docker Compose (Option A).

Note:
- Native runs for API + worker require Redis and matching broker URLs. The Docker option handles this automatically and is the supported path for running the full stack.

### 3\. Set Up the GitHub App

The application requires a GitHub App for authentication and integration.

  - Go to your GitHub **Settings -\> Developer settings -\> GitHub Apps** and create a new app.
  - **Permissions Required**:
      - `Pull requests`: **Read & write**
      - `Contents`: **Read-only**
  - **Subscribe to events**:
      - `Pull request`
  - **Generate a private key** for the app and download the `.pem` file. Move it to the project's root directory and rename it `github-private-key.pem`.
  - **Add the key to your `.gitignore`** to ensure it's never committed\!
    ```bash
    echo "github-private-key.pem" >> .gitignore
    ```

### 4\. Configure Environment Variables

Create a `.env` file for your secrets. We provide an example file to make this easy.

1.  Copy the example file:

    ```bash
    cp .env.example .env
    ```

2.  Fill in your details in the newly created `.env` file.


3.  To generate the `GITHUB_PRIVATE_KEY_BASE64` value, run this command in your terminal:

    ```bash
    # On macOS
    cat github-private-key.pem | base64 | pbcopy

    # On Linux
    cat github-private-key.pem | base64 -w 0
    ```

    On Windows (PowerShell):

    ```powershell
    # Copies base64 to clipboard
    [Convert]::ToBase64String([IO.File]::ReadAllBytes("github-private-key.pem")) | Set-Clipboard

    # If Set-Clipboard isn't available, write to a file instead:
    [Convert]::ToBase64String([IO.File]::ReadAllBytes("github-private-key.pem")) > key.b64
    ```

### 5\. Run the Application

1.  **Start ngrok**: Open a new terminal window and run the following to expose your local port 8000.

    ```bash
    ngrok http 8000
    ```

    Copy the `https://...` forwarding URL it gives you.

    Windows notes:
    - Run commands in Windows Terminal (PowerShell). If using WSL, run everything inside your Linux distro shell.
    - After installing Docker Desktop, sign in and start it once before running `docker compose up`.


2.  **Update Webhook URL**: Go to your GitHub App's settings, and paste the ngrok forwarding URL into the "Webhook URL" field. Add `/api/webhook` to the end.

3.  **Launch Docker Containers**: In your main project terminal, run:

    ```bash
    docker compose up --build
    ```

### 6\. Test the Workflow

Create a Pull Request in a repository where you have installed the GitHub App. The PR should include a Python file with a complex function to trigger a comment.

## 🛠️ Future Work & Roadmap

  - [ ] Add more static analysis rules (e.g., security linting with `bandit`).
  - [ ] Integrate ML models (CodeBERT/CodeT5) for advanced bug detection.
  - [ ] Implement a system for suggesting code fixes.
  - [ ] Build a React dashboard to view historical analysis data and trends.
  - [ ] Support more programming languages.

## 📄 License

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License**.

<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" /></a>

This means you are free to use, share, and adapt this software for **non-commercial purposes** as long as you give appropriate credit and distribute any modifications under the same license.

For commercial use, please contact me to arrange a separate commercial license.
