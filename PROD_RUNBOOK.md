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

---

## Batch A3 Scans Processing

### Overview

Korrigo supports processing batch A3 scans containing multiple student copies scanned recto-verso. The system automatically:
1. Detects A3 format (aspect ratio > 1.2)
2. Splits each A3 page into 2 A4 pages
3. Reorders pages correctly (P1, P2, P3, P4 per sheet)
4. Segments copies by student using OCR + CSV whitelist
5. Creates one Copy per student with all their pages

### Format Requirements

| Requirement | Value |
|-------------|-------|
| Page format | A3 landscape (2 A4 pages side-by-side) |
| Pages per sheet | 2 A3 = 4 A4 (one student sheet) |
| Page order in A3 | A3#1: P1(right), P4(left) / A3#2: P2(left), P3(right) |
| Total A3 pages | Must be even (pairs of recto/verso) |
| A4 pages per student | Multiple of 4 |

### Page Reconstruction Rule

```
A3 Page #1 (recto):  [P4 | P1]  (P1 is on the right, P4 on the left)
A3 Page #2 (verso):  [P2 | P3]  (P2 is on the left, P3 on the right)

Final order: P1, P2, P3, P4
```

### CSV Whitelist Format

The CSV file must contain student information for OCR matching:

```csv
Élèves,Né(e) le,Adresse E-mail,Classe
ABID YOUCEF,01/02/2008,youcef.abid-e@ert.tn,T.01
BEN JEMAA SADRI,21/09/2008,sadri.benjemaa-e@ert.tn,T.01
```

Required columns:
- `Élèves`: Full name (format "LASTNAME FIRSTNAME")
- `Né(e) le`: Date of birth (dd/mm/yyyy)
- `Adresse E-mail`: Student email

### API Usage

```bash
# Upload batch A3 with CSV
curl -X POST /api/exams/upload/ \
  -F "name=Exam Name" \
  -F "pdf_source=@batch_scan.pdf" \
  -F "students_csv=@students.csv" \
  -F "batch_mode=true"
```

### Response

```json
{
  "id": "uuid",
  "name": "Exam Name",
  "copies_created": 28,
  "ready_count": 25,
  "needs_review_count": 3,
  "message": "28 copies created (25 ready, 3 need review)"
}
```

### Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `needs_review=true` | OCR couldn't match student | Manual identification in UI |
| Page count not multiple of 4 | Incomplete scan | Re-scan missing pages |
| Wrong page order | Incorrect scan orientation | Check scanner settings |
| No students matched | CSV format issue | Verify CSV encoding (UTF-8) |

### Invariants (Non-negotiable)

1. **Zero page loss**: Every A3 page produces exactly 2 A4 pages
2. **Zero student mixing**: Each Copy contains only one student's pages
3. **Correct order**: Pages always in order P1, P2, P3, P4 per sheet
4. **Multiple of 4**: Each student Copy has pages as multiple of 4

