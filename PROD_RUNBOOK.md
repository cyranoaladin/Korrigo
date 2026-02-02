# Korrigo Production Runbook

## Overview

This document provides the exact commands and procedures for deploying Korrigo to production at `korrigo.labomaths.tn`.

## Prerequisites

- Docker & Docker Compose installed
- Domain DNS configured to point to server
- SSL certificates (Let's Encrypt or similar)
- Environment variables configured

## Required Environment Variables

```bash
# Core Security (REQUIRED)
SECRET_KEY=<64+ character random string>
DJANGO_ENV=production

# Database
POSTGRES_DB=korrigo_prod
POSTGRES_USER=korrigo_user
POSTGRES_PASSWORD=<strong password>

# Domain Configuration
ALLOWED_HOSTS=korrigo.labomaths.tn,localhost
CORS_ALLOWED_ORIGINS=https://korrigo.labomaths.tn
CSRF_TRUSTED_ORIGINS=https://korrigo.labomaths.tn

# SSL (for production with HTTPS)
SSL_ENABLED=True
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true

# Rate Limiting (enabled by default in production)
RATELIMIT_ENABLE=true

# Optional but recommended
METRICS_TOKEN=<64+ character token for /metrics endpoint>
```

## Build & Deploy Commands

### 1. Clone and prepare

```bash
git clone https://github.com/cyranoaladin/Korrigo.git
cd Korrigo
git checkout main
```

### 2. Create .env file

```bash
cp .env.example .env
# Edit .env with production values
nano .env
```

### 3. Build images

```bash
# For local-prod testing
docker compose -f infra/docker/docker-compose.local-prod.yml build --no-cache

# For production (uses pre-built images from GHCR)
export GITHUB_REPOSITORY_OWNER=cyranoaladin
export KORRIGO_SHA=$(git rev-parse --short HEAD)
docker compose -f infra/docker/docker-compose.prod.yml pull
```

### 4. Start services

```bash
# Local-prod
docker compose -f infra/docker/docker-compose.local-prod.yml up -d

# Production
docker compose -f infra/docker/docker-compose.prod.yml up -d
```

### 5. Run migrations

```bash
docker compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py migrate
```

### 6. Create admin user (first time only)

```bash
docker compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py ensure_admin
```

### 7. Collect static files

```bash
docker compose -f infra/docker/docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

## Health Checks

```bash
# Backend health
curl -f http://localhost:8088/api/health/live/

# All containers status
docker compose -f infra/docker/docker-compose.prod.yml ps
```

## Backup Procedure

### Database backup

```bash
docker compose -f infra/docker/docker-compose.prod.yml exec db pg_dump -U korrigo_user korrigo_prod > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Media files backup

```bash
docker compose -f infra/docker/docker-compose.prod.yml exec backend tar -czf /tmp/media_backup.tar.gz /app/media
docker cp $(docker compose -f infra/docker/docker-compose.prod.yml ps -q backend):/tmp/media_backup.tar.gz ./media_backup_$(date +%Y%m%d).tar.gz
```

## Restore Procedure

### Database restore

```bash
docker compose -f infra/docker/docker-compose.prod.yml exec -T db psql -U korrigo_user korrigo_prod < backup.sql
```

## Rollback Procedure

### Quick rollback (previous image)

```bash
# Stop current
docker compose -f infra/docker/docker-compose.prod.yml down

# Deploy previous version
export KORRIGO_SHA=<previous_commit_sha>
docker compose -f infra/docker/docker-compose.prod.yml up -d
```

## Post-Deploy Checklist

- [ ] All containers healthy: `docker compose ps`
- [ ] Health endpoint responds: `curl /api/health/live/`
- [ ] Frontend loads: `curl https://korrigo.labomaths.tn/`
- [ ] Admin login works
- [ ] Teacher login works
- [ ] Student login works (email + lastname)
- [ ] PDF upload works
- [ ] Grading workflow functional
- [ ] Rate limiting active (5 attempts / 15 min)

## Monitoring

### Logs

```bash
# All services
docker compose -f infra/docker/docker-compose.prod.yml logs -f

# Specific service
docker compose -f infra/docker/docker-compose.prod.yml logs -f backend
```

### Metrics

```bash
# If METRICS_TOKEN is set
curl -H "X-Metrics-Token: $METRICS_TOKEN" http://localhost:8088/api/metrics/
```

## Security Notes

1. **Never commit `.env` files** - use `.env.example` as template
2. **Rotate secrets regularly** - especially after personnel changes
3. **Monitor failed login attempts** - check audit logs
4. **Keep images updated** - rebuild regularly for security patches
5. **Backup before any deployment** - always have a rollback path

---

*Last updated: 2026-02-02*
