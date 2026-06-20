FROM python:3.11-slim-bookworm

WORKDIR /app

ARG INSTALL_DEV_REQUIREMENTS=false

# Install system dependencies for OpenCV and PDF processing
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    curl \
    libmagic1 \
    gnupg \
    tesseract-ocr \
    tesseract-ocr-fra \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$INSTALL_DEV_REQUIREMENTS" = "true" ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

COPY . .
RUN chmod +x entrypoint.sh

# Security: Create non-root user for runtime
RUN groupadd -r korrigo && useradd -r -g korrigo -d /app -s /sbin/nologin korrigo

# Ensure logs directory exists with proper permissions
# P0-OP-01 fix: Logging directory must exist for RotatingFileHandler
RUN mkdir -p /app/logs && chown -R korrigo:korrigo /app

ARG OCI_REVISION=unknown
ARG OCI_SOURCE=unknown
ARG OCI_VERSION=dev
ARG OCI_CREATED=unknown

LABEL org.opencontainers.image.revision="${OCI_REVISION}" \
      org.opencontainers.image.source="${OCI_SOURCE}" \
      org.opencontainers.image.version="${OCI_VERSION}" \
      org.opencontainers.image.created="${OCI_CREATED}"

# Note: Container starts as root so entrypoint.sh can fix volume permissions,
# then drops to korrigo user before running gunicorn.
ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
