FROM python:3.11-slim AS app

# Better logging
ENV PYTHONUNBUFFERED=1

# System dependencies:
# - libmagic*: for python-magic
# - libgobject / libglib / pango / cairo / harfbuzz / fontconfig / gdk-pixbuf: for WeasyPrint/Pango stack
# - libffi-dev: for bcrypt compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    libmagic-dev \
    file \
    libgobject-2.0-0 \
    libglib2.0-0 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    libffi-dev \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files separately for caching
COPY Pipfile Pipfile.lock ./

# Install pipenv + install deps to system
RUN pip install --no-cache-dir pipenv \
    && pipenv install --system --deploy --ignore-pipfile \
    && pip uninstall -y pipenv

# Remove build dependencies to reduce image size
RUN apt-get purge -y gcc libffi-dev && apt-get autoremove -y

# Copy the application last (so code changes don't rebuild deps)
COPY . .

# Create non-root user for security
RUN useradd -m -r appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Run the app
CMD ["python", "app.py"]
