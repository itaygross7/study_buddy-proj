FROM python:3.11-slim AS app

# Better logging and Python settings
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# =============================================================================
# DNS and Network Configuration for Ubuntu 22.04 / Build Environments
# =============================================================================
# Configure DNS fallbacks to prevent resolution issues in various network environments
# This helps with:
# - Corporate proxies
# - Docker build environments with restricted networking
# - Ubuntu 22.04 systemd-resolved quirks
RUN echo "nameserver 8.8.8.8" >> /etc/resolv.conf && \
    echo "nameserver 8.8.4.4" >> /etc/resolv.conf && \
    echo "nameserver 1.1.1.1" >> /etc/resolv.conf

# =============================================================================
# System Dependencies Installation
# =============================================================================
# Install system packages with retry mechanism for network reliability
# - ca-certificates: SSL certificate verification
# - curl: for health checks and debugging
# - libmagic*: for python-magic file type detection
# - libgobject / libglib / pango / cairo / harfbuzz / fontconfig / gdk-pixbuf: for WeasyPrint/Pango stack (PDF generation)
# - libffi-dev + gcc: for bcrypt compilation
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

# Install Python dependencies with retry mechanism
# Using requirements.txt instead of Pipfile for simpler deployment
RUN set -eux; \
    for i in 1 2 3; do \
        pip install --no-cache-dir -r requirements.txt \
        && break || { echo "pip install retry $i failed, waiting..."; sleep 5; }; \
    done

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
