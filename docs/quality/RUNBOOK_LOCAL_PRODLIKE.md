# Runbook: Local Prod-Like Environment

This runbook details how to spin up and verify the application in a production-like environment using Docker Compose and Nginx.

## Prerequisites
- Docker & Docker Compose installed.
- Valid `backend/Dockerfile` and `frontend/Dockerfile`.

## 1. Start Environment
```bash
docker compose -f docker-compose.prodlike.yml up -d --build
```

## 2. Initialization
Run migrations and collect static files:
```bash
docker compose -f docker-compose.prodlike.yml exec backend python manage.py migrate
docker compose -f docker-compose.prodlike.yml exec backend python manage.py collectstatic --noinput
docker compose -f docker-compose.prodlike.yml exec backend python manage.py createsuperuser --noinput --username admin --email admin@example.com
```

## 3. Verification Steps

### A. Health Check
```bash
curl -I http://localhost:8080/api/health/
# Expected: 200 OK
```

### B. Media Gate Check
1.  **Direct Access Blocked**:
    ```bash
    curl -I http://localhost:8080/media/test.txt
    # Expected: 403 Forbidden
    ```
2.  **Protected Access**:
    Must be tested via application logic (Login -> Import -> View).

### C. Import Flow
Login to frontend at `http://localhost:8080`, import a PDF as Teacher.

## 4. Teardown
```bash
docker compose -f docker-compose.prodlike.yml down -v
```
