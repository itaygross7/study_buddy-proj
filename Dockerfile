FROM python:3.11-slim AS app

# Better logging and Python settings
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# =============================================================================
# 1. Runtime System Dependencies
# =============================================================================
# We install these FIRST and keep them.
# Since we list them explicitly here, apt marks them as "manual" automatically.
# We do not include gcc or dev headers here.
RUN set -eux; \
    apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        # Libmagic
        libmagic1 \
        file \
        # WeasyPrint / Pango / Cairo dependencies
        libgobject-2.0-0 \
        libglib2.0-0 \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libpangocairo-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libharfbuzz0b \
        libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# 2. Python Dependencies & Build Tools
# =============================================================================
COPY requirements.txt ./

# This block does 3 things in ONE layer to keep image small:
# A. Installs heavy build dependencies (gcc, headers)
# B. Installs Python packages via pip
# C. Removes the build dependencies immediately
RUN set -eux; \
    # A. Install Build Deps
    apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
        libmagic-dev \
    ; \
    # B. Install Python packages
    # (Includes your SSL fallback logic)
    TRUSTED_HOSTS="--trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org"; \
    if pip install --upgrade pip setuptools wheel; then \
        echo "Pip upgraded successfully"; \
    else \
        pip install $TRUSTED_HOSTS --upgrade pip setuptools wheel; \
    fi; \
    if pip install --no-cache-dir -r requirements.txt; then \
        echo "Deps installed successfully"; \
    else \
        echo "WARNING: SSL fallback triggered"; \
        pip install --no-cache-dir $TRUSTED_HOSTS -r requirements.txt; \
    fi; \
    # C. Cleanup Build Deps
    # We purge the compilers, but the runtime libs (from step 1) stay because
    # they were installed in a previous committed layer.
    apt-get purge -y --auto-remove \
        gcc \
        libffi-dev \
        libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

# =============================================================================
# Application Setup
# =============================================================================
COPY . .

# Create non-root user for security
RUN useradd -m -r appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

CMD ["python", "app.py"]
