# Stage 1: The builder stage
# We use this stage to install dependencies
FROM python:3.10-slim as builder

# Set the working directory
WORKDIR /app

# Install poetry
RUN pip install poetry

# Configure poetry to create the virtual env in the project's root
RUN poetry config virtualenvs.in-project true

# Copy only the files needed to install dependencies
# This leverages Docker's layer caching. The next step will only run
# if these files change.
COPY pyproject.toml poetry.lock ./

# Install dependencies, excluding development ones, without installing the root project
RUN poetry install --without dev --no-root

# Stage 2: The final production stage
# We copy the installed dependencies from the builder stage
FROM python:3.10-slim

# Set the working directory
WORKDIR /app

# Copy the virtual environment with all the dependencies from the builder stage
COPY --from=builder /app/.venv ./.venv

# Copy the application source code
COPY ./ai_code_reviewer /app/ai_code_reviewer

# The command to run when the container starts
# We use 0.0.0.0 to make it accessible from outside the container
CMD ["/app/.venv/bin/uvicorn", "ai_code_reviewer.main:app", "--host", "0.0.0.0", "--port", "80"]