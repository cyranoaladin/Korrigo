# v1.0.0 — Production Release

## Summary

Graduation from **v1.0.0-rc1** to **v1.0.0** after full Release Gate validation in production-like environment and staging smoke test.

Core workflow validated: **PDF ingestion → booklet splitting → copy creation → grading with annotations → PDF export**.

## Release Gate Evidence (Zero-Tolerance)

| Metric | Result | Status |
|--------|--------|--------|
| **CI Run** | #<CI_RUN_ID> (main) | ✅ SUCCESS |
| **Pytest** | 205 passed, 0 failed, 0 skipped | ✅ PASS |
| **E2E** | 3/3 runs with annotations (POST 201, GET 200) | ✅ PASS |
| **Seed** | All READY copies have pages > 0 | ✅ PASS |
| **Staging Smoke** | Full workflow validated | ✅ PASS |
| **Zero-Tolerance** | Strict patterns (no false positives) | ✅ ENFORCED |

## What's Included

### Core Features
- **Exam Management**: PDF upload, automatic booklet detection, manual validation
- **Copy Creation**: Merge booklets with proper page structure, anonymous ID generation
- **Grading Workflow**: Copy locking (10min TTL), vector annotations (normalized coordinates)
- **Annotations**: Bounding box format, optimistic locking, conflict resolution
- **PDF Export**: Flattened annotations, final PDF generation per copy
- **Student Access**: GRADED copies only, per-student isolation (no enumeration)

### Quality & Validation
- **Release Gate Automation**: One-shot script with 8 validation phases (0→H)
- **CI Integration**: GitHub Actions workflow with zero-tolerance criteria
- **Test Coverage**: 205 tests (unit + integration), 0 failures, 0 skipped
- **E2E Validation**: Complete annotation workflow (lock → annotate → finalize → PDF)
- **Seed Robustness**: Idempotent, validates `pages_images` not empty

### Documentation
- Production Checklist: 7 operational items (staging → METRICS_TOKEN → TLS → backups → monitoring → smoke → v1.0.0)
- Release Gate Integrity: Discipline rules to prevent silent regressions
- Release Gate Report: Full validation evidence (v1.0.0-rc1)
- Deployment Scripts: Safe staging deploy + smoke test

## Breaking Changes

None. This is the first production release.

## Deployment Notes

### Required Environment Variables

**Critical (Must Set)**:
```bash
SECRET_KEY=<strong-random-key-64-chars>
ALLOWED_HOSTS=korrigo.example.com
DATABASE_URL=postgresql://user:password@db:5432/korrigo_prod
METRICS_TOKEN=<strong-random-token-64-chars>  # Secures /metrics endpoint
```

**Optional**:
```bash
DEBUG=False  # Default: False (safe)
SSL_ENABLED=True  # Enable HTTPS redirect + HSTS
CORS_ALLOWED_ORIGINS=https://korrigo.example.com
CELERY_BROKER_URL=redis://redis:6379/0
```

### TLS/HTTPS

**Let's Encrypt Recommended**:
```bash
# Obtain certificate
docker compose run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  -d korrigo.example.com \
  --email admin@korrigo.example.com \
  --agree-tos

# Nginx will auto-reload on cert renewal
```

**HSTS**: Enabled in production with 1-year max-age.

### Backups

**Daily Automated Backups Required**:
```bash
# Configure cron job
0 2 * * * /path/to/scripts/backup_db.sh >> /var/log/backup.log 2>&1
```

**Test Restore**: Monthly validation recommended.

### Monitoring

**Minimum Viable**: Sentry or email alerts for errors 500+.

**Sentry Setup** (recommended):
```bash
SENTRY_DSN=https://xxx@sentry.io/yyy
```

## Known Limitations

1. **XFAIL Policy**: Not yet defined (placeholder in CI, commented out)
   - Decision needed: Warning / Blocker / Ignored

2. **METRICS_TOKEN**: If not set, `/metrics` endpoint is public (warning logged)
   - Operator's choice: acceptable for internal staging, must set for production

3. **Backend Log "Errors"**: 2 benign "error" lines in logs (migration names contain "error")
   - `auth.0007_alter_validators_add_error_messages`
   - `exams.0013_copy_grading_error_tracking`
   - These are not actual errors, just migration naming

## Rollback Plan

**If Issues Detected in Production**:

### Quick Rollback (< 5 min)
```bash
# 1. Revert to previous stable version
git checkout <PREVIOUS_TAG>

# 2. Rebuild and restart
docker compose -f docker-compose.prod.yml up -d --build

# 3. Verify
curl https://korrigo.example.com/api/health/
```

### Rollback with DB Restore (< 15 min)
```bash
# 1. Stop services
docker compose -f docker-compose.prod.yml down

# 2. Restore last backup
gunzip -c /backups/postgres/korrigo_backup_<DATE>.sql.gz \
  | docker exec -i korrigo_db psql -U postgres korrigo_prod

# 3. Restart with old version
git checkout <PREVIOUS_TAG>
docker compose -f docker-compose.prod.yml up -d --build
```

## Upgrade Path (from RC1)

No breaking changes. Direct deployment possible.

```bash
# From v1.0.0-rc1 to v1.0.0
git checkout v1.0.0
docker compose -f docker-compose.prod.yml up -d --build
```

Database migrations are forward-compatible. No data migration required.

## Changes Since v1.0.0-rc1

| Commit | Description |
|--------|-------------|
| `<COMMIT_SHA>` | docs: Production Checklist + Release Gate Integrity rules |
| `<COMMIT_SHA>` | docs: Add deliverables summary v1.0.0-rc1 → v1.0.0 |
| `<COMMIT_SHA>` | scripts: Add safe staging deploy + smoke test |
| `<COMMIT_SHA>` | docs: Release notes v1.0.0 template |

## Security Audit

| Item | Status | Notes |
|------|--------|-------|
| DEBUG=False | ✅ Enforced | Validated in settings.py |
| SECRET_KEY | ✅ Validated | No dangerous defaults in production |
| ALLOWED_HOSTS | ✅ Explicit | Must be set, no wildcards allowed |
| HTTPS | ✅ Enforced | SSL_ENABLED=True → HSTS 1 year |
| CSRF/CORS | ✅ Configured | Strict origins, SameSite=Lax |
| Permissions | ✅ Explicit | No AllowAny on sensitive endpoints |
| Rate Limiting | ✅ Active | Login: 5/15min, API: 100/min |
| Audit Trail | ✅ Implemented | All critical actions logged |
| Backups | ⚠️ Required | Must configure before production |

## Performance Baseline

| Metric | Value | Target |
|--------|-------|--------|
| **CI Duration** | 5m4s | < 10min |
| **Pytest** | 8.70s (205 tests) | < 15s |
| **E2E (3 runs)** | ~15s | < 30s |
| **Seed** | ~3s | < 5s |
| **Docker Build** | ~90s (no cache) | < 2min |
| **Service Boot** | ~30s (5 services) | < 1min |

## Links

- **Release Gate Report**: `RELEASE_GATE_REPORT_v1.0.0-rc1.md`
- **Production Checklist**: `PRODUCTION_CHECKLIST.md`
- **Integrity Rules**: `.github/RELEASE_GATE_INTEGRITY.md`
- **CI Run (main)**: https://github.com/cyranoaladin/Korrigo/actions/runs/<CI_RUN_ID>
- **Artifacts**: https://github.com/cyranoaladin/Korrigo/actions/runs/<CI_RUN_ID>#artifacts
- **GitHub Release**: https://github.com/cyranoaladin/Korrigo/releases/tag/v1.0.0

## Post-Production Checklist

**First Week**:
- [ ] Monitor errors daily (Sentry/logs)
- [ ] Verify backups created daily
- [ ] Test restore once
- [ ] Collect user feedback
- [ ] Prepare hotfixes if needed

**Ongoing Maintenance**:
- [ ] Test restore monthly
- [ ] Rotate secrets every 90 days
- [ ] Update dependencies (security patches)
- [ ] Review audit logs monthly

## Support

- **Technical Contact**: [Admin Email]
- **Documentation**: `docs/` directory + `PRODUCTION_CHECKLIST.md`
- **Issues**: https://github.com/cyranoaladin/Korrigo/issues
- **Escalation**: [Technical Lead]

---

**Release Date**: <YYYY-MM-DD>
**Released By**: Shark (Release Manager)
**Status**: ✅ **Production Ready**

**Validated**: Zero-tolerance criteria met (205 passed, 0 failed, 0 skipped, E2E 3/3, staging smoke passed)
