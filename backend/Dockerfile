FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for OpenCV, PDF processing, and OCR
# PRD-19: Added deps for EasyOCR (libgomp1) and PaddleOCR (libSM, libXext, libXrender)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libfontconfig1 \
    poppler-utils \
    curl \
    libmagic1 \
    tesseract-ocr \
    tesseract-ocr-fra \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=600 -r requirements.txt

COPY . .
RUN chmod +x entrypoint.sh

# Ensure logs directory exists with proper permissions
# P0-OP-01 fix: Logging directory must exist for RotatingFileHandler
RUN mkdir -p /app/logs && chmod 755 /app/logs

# PRD-19: Create OCR cache directory with proper permissions
RUN mkdir -p /app/.cache && chmod 755 /app/.cache

ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["gunicorn", "core.wsgi:application", "-c", "gunicorn_config.py"]
