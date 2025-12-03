FROM python:3.11-slim AS app

# Better logging and Python settings
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# =============================================================================
# System Dependencies Installation
# =============================================================================
# Install system packages with retry mechanism for network reliability
# - ca-certificates: SSL certificate verification
# - curl: for health checks and debugging
# - libmagic*: for python-magic file type detection
# - libgobject / libglib / pango / cairo / harfbuzz / fontconfig / gdk-pixbuf: for WeasyPrint/Pango stack (PDF generation)
# - libffi-dev + gcc: for bcrypt compilation
#
# Note: DNS configuration is handled at runtime via docker-compose.yml
RUN set -eux; \
    # Update CA certificates first to fix potential SSL issues
    apt-get update && apt-get install -y --no-install-recommends ca-certificates; \
    update-ca-certificates; \
    # Retry mechanism for package installation
    for i in 1 2 3; do \
        apt-get update && apt-get install -y --no-install-recommends \
            curl \
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
        && break || { echo "Retry $i failed, waiting..."; sleep 5; }; \
    done; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# =============================================================================
# Python Dependencies Installation
# =============================================================================
# Copy dependency files separately for Docker layer caching
COPY requirements.txt ./

# Install Python dependencies with retry mechanism and SSL fallback
# Using requirements.txt instead of Pipfile for simpler deployment
RUN set -eux; \
    # Upgrade pip and setuptools first to ensure latest SSL handling
    pip install --upgrade pip setuptools wheel || \
        pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --upgrade pip setuptools wheel; \
    # Try with proper SSL verification first
    if pip install --no-cache-dir -r requirements.txt; then \
        echo "Dependencies installed successfully with SSL verification"; \
    else \
        echo "SSL verification failed, falling back to trusted-host mode"; \
        pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt; \
    fi

# Remove build dependencies to reduce image size
RUN apt-get update && apt-get purge -y gcc libffi-dev && apt-get autoremove -y && apt-get clean && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Application Setup
# =============================================================================
# Copy the application last (so code changes don't rebuild deps)
COPY . .

# Create non-root user for security
RUN useradd -m -r appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Health check for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the app
CMD ["python", "app.py"]
