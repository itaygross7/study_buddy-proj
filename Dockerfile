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
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for Tailwind CSS build
RUN curl -sL https://deb.nodesource.com/setup_18.x | bash -
RUN apt-get install -y nodejs

WORKDIR /app

# Install Python dependencies using Pipenv
COPY Pipfile Pipfile.lock ./
RUN pip install pipenv
RUN pipenv install --system --deploy --ignore-pipfile

# Install and build frontend assets
COPY package.json ./
RUN npm install
COPY tailwind.config.js .
COPY ui/templates ./ui/templates
COPY ui/static/css/input.css ./ui/static/css/input.css
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
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy built static assets and application code
COPY --from=builder /app/ui/static/css/styles.css ./ui/static/css/styles.css
COPY src ./src
COPY ui ./ui
COPY sb_utils ./sb_utils
COPY services ./services
COPY infra ./infra
COPY app.py .
COPY worker.py .

# Set environment variables
ENV FLASK_APP=app:create_app()
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# Use Gunicorn as the production WSGI server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:create_app()"]
