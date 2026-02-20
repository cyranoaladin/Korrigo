# 🚀 Staging Deployment & Smoke Test

**Status**: Ready for deployment
**Version**: v1.0.0-rc1 → v1.0.0
**Date**: 2026-01-29

---

## Overview

This directory contains **production-ready scripts** for deploying to staging and validating the complete workflow.

### Scripts

1. **`deploy_staging_safe.sh`** - Safe staging deployment with auto-rollback
2. **`smoke_staging.sh`** - Complete E2E smoke test (9 steps)
3. **`release_gate_oneshot.sh`** - Full Release Gate validation (existing)

---

## 1. Deploy Staging (Safe)

### Features

✅ **Automatic Rollback**: If services unhealthy → auto-rollback + logs
✅ **METRICS_TOKEN Generation**: Auto-generates if not set (64 chars)
✅ **Health Checks**: Waits up to 90s for all services healthy
✅ **Comprehensive Logging**: All steps logged to `/tmp/staging_deploy_<timestamp>/`

### Prerequisites

- Docker Compose installed
- `infra/docker/docker-compose.staging.yml` exists
- Git repository with tag `v1.0.0-rc1`

### Usage

```bash
# Basic usage (auto-generates METRICS_TOKEN)
BASE_URL=https://staging.example.com TAG=v1.0.0-rc1 ./scripts/deploy_staging_safe.sh

# With explicit METRICS_TOKEN
BASE_URL=https://staging.example.com \
  TAG=v1.0.0-rc1 \
  METRICS_TOKEN=$(openssl rand -hex 32) \
  ./scripts/deploy_staging_safe.sh
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TAG` | `v1.0.0-rc1` | Git tag to deploy |
| `BASE_URL` | `https://staging.example.com` | Staging URL |
| `METRICS_TOKEN` | Auto-generated | /metrics endpoint security token (64+ chars) |
| `COMPOSE` | `infra/docker/docker-compose.staging.yml` | Docker Compose file |

### Output

**Success**:
```
[HH:MM:SS] === STAGING DEPLOY START (v1.0.0-rc1) ===
[HH:MM:SS] Checked out <commit_sha>
[HH:MM:SS] METRICS_TOKEN set (length=64)
[HH:MM:SS] Building images
[HH:MM:SS] Starting stack
[HH:MM:SS] Waiting services healthy (timeout 90s)
[HH:MM:SS] ✅ Stack up & stable
[HH:MM:SS] BASE_URL=https://staging.example.com
[HH:MM:SS] ✅ Health endpoint OK
[HH:MM:SS] === STAGING DEPLOY DONE ===
[HH:MM:SS] Next: run smoke script (scripts/smoke_staging.sh) using same BASE_URL
[HH:MM:SS] Artifacts: /tmp/staging_deploy_<timestamp>
```

**Failure (auto-rollback)**:
```
[HH:MM:SS] ❌ Unhealthy services detected
[HH:MM:SS] Rolling back (down)
```

### Artifacts

All logs saved to: `/tmp/staging_deploy_<timestamp>/`
- `deploy.log` - Main deployment log
- `git_fetch.log` - Git fetch output
- `git_checkout.log` - Git checkout output
- `build.log` - Docker build logs (full)
- `up.log` - Docker Compose up logs
- `ps_final.log` - Final services status
- `health_api.log` - Health endpoint response
- `rollback_down.log` - Rollback logs (if failed)

---

## 2. Smoke Test Staging

### Features

✅ **Complete Workflow**: 9-step E2E validation (login → lock → annotate → finalize → PDF)
✅ **Session-Based Auth**: Uses cookies (Django session), not JWT tokens
✅ **Exact Endpoints**: Matches backend code (no placeholders)
✅ **Fail Fast**: Exits on first error with detailed logs
✅ **Comprehensive Logging**: All API calls + responses logged

### Prerequisites

- Staging deployed and running
- Test user credentials (professor role)
- At least one exam with READY copies (pages > 0)

### Usage

```bash
# Basic usage
BASE_URL=https://staging.example.com \
  SMOKE_USER=prof1 \
  SMOKE_PASS=changeme \
  ./scripts/smoke_staging.sh
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_URL` | `https://staging.example.com` | Staging URL |
| `SMOKE_USER` | `prof1` | Professor username |
| `SMOKE_PASS` | `changeme` | Professor password |

### Workflow Steps

| Step | Action | Validation |
|------|--------|------------|
| 1 | **Login** | Session cookie + CSRF token received |
| 2 | **Get Exam ID** | At least one exam exists |
| 3 | **List READY Copies** | At least one copy with status=READY and pages > 0 |
| 4 | **Lock Copy** | HTTP 201, lock token received |
| 5 | **POST Annotation** | HTTP 201, annotation created |
| 6 | **GET Annotations** | HTTP 200, count > 0 |
| 7 | **Finalize** | HTTP 200, status=GRADED |
| 8 | **Verify PDF** | HTTP 200, PDF accessible |
| 9 | **Unlock** | HTTP 204 or auto-unlocked (best effort) |

### API Endpoints Used

**Authentication** (Session-based):
```bash
POST /api/login/
  Body: {"username": "prof1", "password": "changeme"}
  Returns: {"message": "Login successful"} + session cookie
```

**Workflow**:
```bash
GET  /api/exams/
  Returns: {"results": [{"id": "<exam_id>", ...}]}

GET  /api/exams/<exam_id>/copies/
  Filter: .results[] | select(.status=="READY")
  Returns: copies with booklets + pages_images

POST /api/grading/copies/<copy_id>/lock/
  Headers: X-CSRFToken
  Returns: {"token": "<lock_token>", ...}
  HTTP: 201

POST /api/grading/copies/<copy_id>/annotations/
  Headers: X-CSRFToken, X-Lock-Token
  Body: {"page_index": 0, "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.1, "type": "COMMENT", "content": "staging-smoke-test"}
  HTTP: 201

POST /api/grading/copies/<copy_id>/finalize/
  Headers: X-CSRFToken, X-Lock-Token
  Returns: {"status": "GRADED"}
  HTTP: 200

GET  /api/grading/copies/<copy_id>/final-pdf/
  Returns: PDF file
  HTTP: 200

DELETE /api/grading/copies/<copy_id>/lock/release/
  Headers: X-CSRFToken, X-Lock-Token
  HTTP: 204
```

### Output

**Success**:
```
[HH:MM:SS] === STAGING SMOKE START ===
[HH:MM:SS] BASE_URL=https://staging.example.com
[HH:MM:SS] 1) Login
[HH:MM:SS] ✅ Logged in (session cookie set)
[HH:MM:SS] 2) Get exam ID
[HH:MM:SS] ✅ Exam ID: <exam_id>
[HH:MM:SS] 3) List READY copies
[HH:MM:SS] ✅ Found READY copy: <copy_id>
[HH:MM:SS] ✅ Copy has 2 pages
[HH:MM:SS] 4) Lock copy
[HH:MM:SS] ✅ Locked (HTTP 201, token: abcd1234...)
[HH:MM:SS] 5) POST annotation
[HH:MM:SS] ✅ Annotation created (HTTP 201)
[HH:MM:SS] 6) GET annotations
[HH:MM:SS] ✅ Annotations found: 1
[HH:MM:SS] 7) Finalize copy
[HH:MM:SS] ✅ Finalize OK (HTTP 200)
[HH:MM:SS] 8) Verify final PDF
[HH:MM:SS] ✅ PDF accessible: https://staging.example.com/api/grading/copies/<copy_id>/final-pdf/
[HH:MM:SS] 9) Unlock (best effort)
[HH:MM:SS] ⚠️  Unlock not needed (HTTP 404) - likely auto-unlocked by finalize
[HH:MM:SS] === STAGING SMOKE SUCCESS ===
[HH:MM:SS] Artifacts: /tmp/staging_smoke_<timestamp>

Summary:
  ✅ Login successful
  ✅ Exam found: <exam_id>
  ✅ READY copy found with pages > 0
  ✅ Lock acquired
  ✅ Annotation created
  ✅ Annotations retrieved (1)
  ✅ Copy finalized (status: GRADED)
  ✅ PDF accessible
```

**Failure**:
```
[HH:MM:SS] ❌ <Error description>
<Relevant log content>
```

### Artifacts

All logs saved to: `/tmp/staging_smoke_<timestamp>/`
- `smoke.log` - Main smoke test log
- `login.json` - Login response
- `exams.json` - Exams list
- `copies.json` - Copies list
- `lock.txt` - Lock response
- `annotation_post.txt` - Annotation creation response
- `annotations_get.json` - Annotations GET response
- `finalize.txt` - Finalize response
- `pdf_head.txt` - PDF HEAD response
- `unlock.txt` - Unlock response
- `cookies.txt` - Session cookies

---

## 3. Troubleshooting

### Deploy Script

**Issue**: Services unhealthy after 90s
```bash
# Check logs
cat /tmp/staging_deploy_<timestamp>/logs_full.log

# Common causes:
# - Database not ready (wait longer or check DB config)
# - Missing environment variables
# - Port conflicts
```

**Issue**: Health endpoint unreachable
```bash
# Check Nginx/backend logs
docker compose -f infra/docker/docker-compose.staging.yml logs nginx backend

# Verify BASE_URL
curl -I https://staging.example.com/api/health/
```

### Smoke Script

**Issue**: Login failed
```bash
# Check credentials
cat /tmp/staging_smoke_<timestamp>/login.json

# Verify user exists
docker compose exec backend python manage.py shell -c "
from django.contrib.auth.models import User
print(User.objects.filter(username='prof1').exists())
"
```

**Issue**: No READY copies
```bash
# Check exam/copies status
cat /tmp/staging_smoke_<timestamp>/copies.json

# Seed data if needed
docker compose exec backend python manage.py seed_e2e_data
```

**Issue**: Lock failed (409 Conflict)
```bash
# Copy already locked, check status
curl -b cookies.txt https://staging.example.com/api/grading/copies/<copy_id>/lock/status/

# Force unlock (admin only)
docker compose exec backend python manage.py shell -c "
from grading.models import CopyLock
CopyLock.objects.all().delete()
"
```

**Issue**: Annotation POST failed (403 Forbidden)
```bash
# Missing lock token
cat /tmp/staging_smoke_<timestamp>/annotation_post.txt

# Verify X-Lock-Token header is set
grep "X-Lock-Token" /tmp/staging_smoke_<timestamp>/smoke.log
```

---

## 4. Complete Workflow Example

```bash
# Step 1: Deploy staging
BASE_URL=https://staging.korrigo.example.com \
  TAG=v1.0.0-rc1 \
  METRICS_TOKEN=$(openssl rand -hex 32) \
  ./scripts/deploy_staging_safe.sh

# Wait for completion (~2-3 minutes)
# Check output: ✅ STAGING DEPLOY DONE

# Step 2: Run smoke test
BASE_URL=https://staging.korrigo.example.com \
  SMOKE_USER=prof1 \
  SMOKE_PASS=secure_password_123 \
  ./scripts/smoke_staging.sh

# Wait for completion (~30 seconds)
# Check output: ✅ STAGING SMOKE SUCCESS

# Step 3: Review artifacts
ls -la /tmp/staging_deploy_*/
ls -la /tmp/staging_smoke_*/

# Step 4: If all green → proceed to v1.0.0 tag
```

---

## 5. Integration with Production Checklist

These scripts correspond to **items 1 and 6** of `PRODUCTION_CHECKLIST.md`:

| Item | Script | Duration |
|------|--------|----------|
| 1. Staging Deploy | `deploy_staging_safe.sh` | 30 min |
| 6. Smoke Staging | `smoke_staging.sh` | 15 min |

**After smoke test passes**: Fill `RELEASE_NOTES_v1.0.0.md` template and tag `v1.0.0`.

---

## 6. Success Criteria

**Deploy Script**:
- ✅ All services healthy (5/5)
- ✅ Health endpoint returns 200
- ✅ No critical errors in logs

**Smoke Test**:
- ✅ All 9 steps pass
- ✅ HTTP status codes correct (201, 200, 204)
- ✅ Annotation count > 0
- ✅ Copy status = GRADED
- ✅ PDF accessible

**Overall**:
- ✅ No manual intervention required
- ✅ Artifacts available for debugging
- ✅ Ready for production deployment

---

## 7. Links

- **Production Checklist**: `../PRODUCTION_CHECKLIST.md`
- **Release Notes Template**: `../RELEASE_NOTES_v1.0.0.md`
- **Release Gate Integrity**: `../.github/RELEASE_GATE_INTEGRITY.md`
- **CI Workflow**: `../.github/workflows/release-gate.yml`

---

**Questions?** See `PRODUCTION_CHECKLIST.md` section "Rollback Plan" if issues arise.

**Ready to deploy?** Run scripts in order: deploy → smoke → tag v1.0.0 🚀
