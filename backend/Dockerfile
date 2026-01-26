FROM python:3.9-slim

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

ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
