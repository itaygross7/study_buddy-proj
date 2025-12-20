# --- Builder Stage ---
FROM python:3.11-slim-bookworm as builder

# Install system dependencies for Python packages, Tesseract, and WeasyPrint
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    gcc \
    curl \
    tesseract-ocr \
    libpango-1.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for Tailwind CSS build
RUN curl -sL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get update && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (root requirements.txt is still the main one)
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install and build frontend assets (from /ui)
COPY package.json ./package.json
RUN npm install

COPY tailwind.config.js ./tailwind.config.js
COPY ui/templates ./ui/templates
COPY ui/static/css/input.css ./ui/static/css/input.css

# This should generate ui/static/css/styles.css
RUN npm run tailwind:build

# --- Final Stage ---
FROM python:3.11-slim-bookworm

WORKDIR /app

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    tesseract-ocr \
    libpango-1.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    libmagic1 \
    git \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy built static assets
COPY --from=builder /app/ui/static/css/styles.css ./ui/static/css/styles.css

# Copy application code (existing backend)
COPY src ./src
COPY ui ./ui
COPY sb_utils ./sb_utils
COPY services ./services
COPY infra ./infra
COPY app.py .
COPY worker.py .
COPY health_monitor.py .


# Ensure /app is on Python path (so 'import new_backend', 'import src' etc. work)
ENV PYTHONPATH=/app

# Set environment variables
ENV FLASK_APP=app:create_app()
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# Use Gunicorn as the production WSGI server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:create_app()"]
