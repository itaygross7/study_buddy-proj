# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install poetry and dependencies
RUN pip install pipenv
COPY Pipfile Pipfile.lock /app/
RUN pipenv install --system --deploy --ignore-pipfile

# Stage 2: Runner
FROM python:3.11-slim

WORKDIR /app

# Copy virtual env from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin


# Copy the application code
COPY ./src /app/src

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
