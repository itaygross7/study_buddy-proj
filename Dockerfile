# Stage 1: Build Stage
FROM python:3.11-slim-buster as builder

# Install system dependencies required for building Python packages and Tesseract
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libffi-dev \
    gcc \
    tesseract-ocr \
    # WeasyPrint dependencies
    libpango-1.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js and TailwindCSS
RUN curl -sL https://deb.nodesource.com/setup_16.x | bash -
RUN apt-get install -y nodejs
RUN npm install -g tailwindcss

WORKDIR /app

# Install Python dependencies
COPY Pipfile Pipfile.lock ./
RUN pip install pipenv
RUN pipenv install --system --deploy --ignore-pipfile

# Build TailwindCSS
COPY tailwind.config.js .
COPY ui/templates ./ui/templates
RUN tailwindcss -o ./ui/static/css/styles.css --minify

# ---

# Stage 2: Final Stage
FROM python:3.11-slim-buster

WORKDIR /app

# Install runtime dependencies for Tesseract and WeasyPrint
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libpango-1.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy static assets and application code
COPY --from=builder /app/ui/static ./ui/static
COPY src ./src
COPY sb_utils ./sb_utils
COPY app.py .
COPY worker.py .

EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

CMD ["flask", "run", "--host=0.0.0.0"]
