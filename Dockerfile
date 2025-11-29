FROM python:3.11-slim AS app

# Better logging
ENV PYTHONUNBUFFERED=1

# System dependencies:
# - libmagic*: for python-magic
# - libgobject / libglib / pango / cairo / harfbuzz / fontconfig / gdk-pixbuf: for WeasyPrint/Pango stack
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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files separately for caching
COPY Pipfile Pipfile.lock ./

# Install pipenv + install deps to system
RUN pip install --no-cache-dir pipenv \
    && pipenv install --system --deploy --ignore-pipfile \
    && pip uninstall -y pipenv

# Copy the application last (so code changes don't rebuild deps)
COPY . .

# Run the app
CMD ["python", "app.py"]
