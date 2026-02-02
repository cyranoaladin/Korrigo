# Korrigo Production Readiness Checklist (Main-Only Protocol)

## Metadata
- **Date**: 2026-02-02
- **Timestamp**: 2026-02-02_1206
- **Branch**: main (ONLY)
- **Target**: korrigo.labomaths.tn

---

## PRD Validation Table

| PRD | Description | Status | Commit Hash | Proof Directory |
|-----|-------------|--------|-------------|-----------------|
| PRD-01 | Baseline + Checklist Creation | PENDING | - | `.antigravity/proofs/prd/2026-02-02_1206/PRD-01/` |
| PRD-02 | Docker Compose prod config valid | PENDING | - | `.antigravity/proofs/prd/2026-02-02_1206/PRD-02/` |
| PRD-03 | Docker Compose local-prod config valid | PENDING | - | `.antigravity/proofs/prd/2026-02-02_1206/PRD-03/` |
| PRD-04 | Build images (no-cache) | PENDING | - | `.antigravity/proofs/prd/2026-02-02_1206/PRD-04/` |
| PRD-05 | Boot stack + all services healthy | PENDING | - | `.antigravity/proofs/prd/2026-02-02_1206/PRD-05/` |
| PRD-06 | Migrations applied | PENDING | - | `.antigravity/proofs/prd/2026-02-02_1206/PRD-06/` |
| PRD-07 | Collectstatic + nginx config | PENDING | - | `.antigravity/proofs/prd/2026-02-02_1206/PRD-07/` |
| PRD-08 | Seed deterministic + idempotent | PENDING | - | `.antigravity/proofs/prd/2026-02-02_1206/PRD-08/` |
| PRD-09 | Backend tests 100% pass | PENDING | - | `.antigravity/proofs/prd/2026-02-02_1206/PRD-09/` |
| PRD-10 | Frontend build prod | PENDING | - | `.antigravity/proofs/prd/2026-02-02_1206/PRD-10/` |
| PRD-11 | Frontend lint/typecheck | PENDING | - | `.antigravity/proofs/prd/2026-02-02_1206/PRD-11/` |
| PRD-12 | E2E tests 100% pass | PENDING | - | `.antigravity/proofs/prd/2026-02-02_1206/PRD-12/` |
| PRD-13 | Auth/Lockout TTL runtime validation | PENDING | - | `.antigravity/proofs/prd/2026-02-02_1206/PRD-13/` |
| PRD-14 | Workflow métier complet (scan A3 réel) | PENDING | - | `.antigravity/proofs/prd/2026-02-02_1206/PRD-14/` |
| PRD-15 | Restart resilience | PENDING | - | `.antigravity/proofs/prd/2026-02-02_1206/PRD-15/` |
| PRD-16 | Security headers nginx (curl -I) | PENDING | - | `.antigravity/proofs/prd/2026-02-02_1206/PRD-16/` |
| PRD-17 | Observability + no PII in logs | PENDING | - | `.antigravity/proofs/prd/2026-02-02_1206/PRD-17/` |
| PRD-18 | Runbook + Risk Register finalized | PENDING | - | `.antigravity/proofs/prd/2026-02-02_1206/PRD-18/` |
| PRD-19 | Gate final (fresh clone rebuild) | PENDING | - | `.antigravity/proofs/prd/2026-02-02_1206/PRD-19/` |

---

## PRD Details

### PRD-01: Baseline + Checklist Creation
- [ ] Git clean working directory
- [ ] Create safety tag
- [ ] Create this checklist file
- [ ] Create proof directory structure

### PRD-02: Docker Compose prod config
- [ ] `docker compose -f infra/docker/docker-compose.prod.yml config` validates
- [ ] No hardcoded secrets
- [ ] All required env vars documented

### PRD-03: Docker Compose local-prod config
- [ ] `docker compose -f infra/docker/docker-compose.local-prod.yml config` validates
- [ ] Services: db, redis, backend, celery, nginx

### PRD-04: Build images
- [ ] `docker compose build --no-cache` succeeds
- [ ] All images built without errors

### PRD-05: Boot stack
- [ ] All containers start
- [ ] Health checks pass (db, redis, backend healthy)
- [ ] `docker compose ps` shows all services UP

### PRD-06: Migrations
- [ ] `python manage.py migrate` succeeds
- [ ] No pending migrations

### PRD-07: Static files + nginx
- [ ] `python manage.py collectstatic` succeeds
- [ ] nginx serves static files
- [ ] nginx config syntax valid

### PRD-08: Seed
- [ ] Seed script runs without errors
- [ ] Seed is idempotent (run twice, same result)
- [ ] DB counts verified

### PRD-09: Backend tests
- [ ] `pytest` 100% pass
- [ ] No skipped critical tests
- [ ] Coverage acceptable

### PRD-10: Frontend build
- [ ] `npm run build` succeeds
- [ ] No build errors

### PRD-11: Frontend lint
- [ ] `npm run lint` passes
- [ ] `npm run typecheck` passes (if applicable)

### PRD-12: E2E tests
- [ ] Playwright tests 100% pass
- [ ] All critical flows covered

### PRD-13: Auth/Lockout TTL
- [ ] Rate limiting configured (5/15m for login)
- [ ] Lockout TTL verified in runtime
- [ ] No default admin password in production mode

### PRD-14: Workflow métier complet (SCAN A3 RÉEL)
- [ ] Import PDF scan A3 recto-verso
- [ ] A3 → A4 split with correct page order (1-4, 2-3 → 1-2-3-4)
- [ ] Header detection works
- [ ] Student identification (manual or OCR-assisted)
- [ ] Copy status transitions: STAGING → READY → LOCKED → GRADED
- [ ] Annotations/autosave functional
- [ ] Final PDF generation
- [ ] Student login and copy consultation

### PRD-15: Restart resilience
- [ ] `docker compose down && up` preserves data
- [ ] All services recover healthy

### PRD-16: Security headers
- [ ] `curl -I` shows X-Frame-Options: DENY
- [ ] X-Content-Type-Options: nosniff
- [ ] X-XSS-Protection: 1; mode=block
- [ ] Referrer-Policy present
- [ ] CSP header present

### PRD-17: Observability + no PII
- [ ] Logs in JSON format
- [ ] No PII (emails, names) in logs
- [ ] Health endpoints respond
- [ ] Metrics endpoint secured (METRICS_TOKEN)

### PRD-18: Runbook + Risk Register
- [ ] PROD_RUNBOOK.md complete
- [ ] RISK_REGISTER.md complete
- [ ] All env vars documented
- [ ] Backup/restore procedures documented

### PRD-19: Gate final
- [ ] Fresh clone from GitHub
- [ ] Build from scratch
- [ ] All tests pass
- [ ] Workflow métier verified
- [ ] GO/NO-GO decision documented

---

## Non-Negotiable Rules

1. **Main-only protocol**: No branches, no PRs
2. **Atomic commits**: One PRD = one commit
3. **Proof required**: Every claim must have a proof file
4. **No PII in logs**: Verified before declaring PASS
5. **No default passwords**: Production mode requires strong ADMIN_PASSWORD
6. **PRD-19 must PASS**: Cannot declare prod-ready until fresh rebuild succeeds

---

## Proof Directory Structure

```
.antigravity/proofs/prd/2026-02-02_1206/
├── PRD-01/
│   ├── commands.sh
│   ├── output.log
│   └── notes.md
├── PRD-02/
│   └── ...
└── PRD-19/
    └── ...
```

---

*Last updated: 2026-02-02 12:06 UTC+01:00*
