FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for OpenCV and PDF processing
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    curl \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x entrypoint.sh

# Ensure logs directory exists with proper permissions
# P0-OP-01 fix: Logging directory must exist for RotatingFileHandler
RUN mkdir -p /app/logs && chmod 777 /app/logs

ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
