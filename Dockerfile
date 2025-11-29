# --- Builder Stage ---
FROM python:3.11-slim-buster as builder

# Install system dependencies for Python packages, Tesseract, and WeasyPrint
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    gcc \
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
COPY package.json package-lock.json ./
RUN npm install
COPY tailwind.config.js .
COPY ui/templates ./ui/templates
COPY ui/static/css/input.css ./ui/static/css/input.css
RUN npm run tailwind:build

# --- Final Stage ---
FROM python:3.11-slim-buster

WORKDIR /app

# Install only runtime system dependencies
RUN apt-get update && apt-get install -y \
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
COPY sb_utils ./sb_utils
COPY ui/templates ./ui/templates
COPY app.py .
COPY worker.py .

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# Run the Flask application
CMD ["flask", "run", "--host=0.0.0.0"]
