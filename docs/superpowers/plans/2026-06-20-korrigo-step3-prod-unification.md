# Korrigo Step 3 Prod Unification Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare, validate, and document the production configuration cutover without touching active production until explicit human go.

**Architecture:** Keep the Porte 2 source/release intact as the rollback baseline, then create a dedicated Step 3 branch for config and security hardening. Validate on a disposable Docker Compose stack with digest-pinned images, Redis AUTH, GPG-encrypted backups, no overlays, and explicit migrations; stop before production.

**Tech Stack:** Docker Compose, Django 4.2, DRF, Celery/Redis, PostgreSQL, nginx, GPG, Vitest, pytest.

---

## Chunk 1: Checklist And Branch Hygiene

### Task 1: Gate 2 Documentation

**Files:**
- Modify: `ASSAINISSEMENT_KORRIGO.md`

- [ ] Check Porte 2 in the dashboard after human validation.
- [ ] Add Step 6 UI/UX recipe criteria by role.
- [ ] Add Step 7 FE/BE/DB/nginx/routing consistency audit criteria.
- [ ] Add Step 9 CI gates for migration-history parity, PostgreSQL migrations, overlay detection, OCI labels, KORRIGO_SHA, and restore tests.
- [ ] Commit doc-only and push `release/reconcile`.

### Task 2: Step 3 Branch

**Files:**
- None initially.

- [ ] Create `release/prod-unification` from pushed `release/reconcile`.
- [ ] Inventory compose/env/backup/nginx/settings files and record assumptions.

## Chunk 2: Runtime Config Unification

### Task 3: Canonical Compose

**Files:**
- Modify: `infra/docker/docker-compose.prod.yml`
- Modify: `.env.prod.example`
- Test: `backend/core/tests/test_prod_compose_contract.py`

- [ ] Define `infra/docker/docker-compose.prod.yml` as the single canonical production compose with `name: docker` to preserve existing Korrigo container/volume naming.
- [ ] Pin backend and nginx by digest, not floating tags.
- [ ] Remove all overlay and frontend host bind mounts.
- [ ] Require `REDIS_PASSWORD`, `BACKUP_GPG_PASSPHRASE`, `SECRET_KEY`, DB secrets, and metrics token.
- [ ] Set `DJANGO_AUTO_MIGRATE=false`, `SEED_ON_START=false`, no `E2E_SEED_TOKEN`.
- [ ] Add `GUNICORN_WORKERS=4` default in example env.
- [ ] Keep rollback image digests documented.

### Task 4: Disable Runtime Docs In Production

**Files:**
- Modify: `backend/core/urls.py`
- Modify: `backend/core/settings.py` or `backend/core/settings_prod.py`
- Test: new or existing backend URL tests.

- [ ] Add `ENABLE_API_DOCS` setting defaulting to `False` in production and `True` otherwise unless explicitly set.
- [ ] Gate `api/schema/`, `api/docs/`, and `api/redoc/` behind `ENABLE_API_DOCS`.
- [ ] Add tests proving docs are absent in prod settings and present when enabled.

## Chunk 3: Security And Backup Hardening

### Task 5: Redis AUTH

**Files:**
- Modify: canonical compose
- Test: compose contract and staging runtime proof.

- [ ] Run Redis with mandatory `--requirepass`.
- [ ] Pass `REDIS_PASSWORD` to Django/Celery and avoid unauthenticated broker defaults in compose.
- [ ] Healthcheck Redis with auth.

### Task 6: GPG Backups And PII-Safe Logs

**Files:**
- Modify: `scripts/korrigo_backup.sh`
- Add tests under `backend/tests/` or script-level proof.

- [ ] Require GPG passphrase when `REQUIRE_BACKUP_GPG=true`.
- [ ] Encrypt DB dump, media archive, and JSON exports at rest.
- [ ] Redact PII-like emails from backup logs.
- [ ] Prove backup -> encryption -> decryption -> restore on staging without committing data artifacts.

## Chunk 4: Staging Validation And Stop

### Task 7: Full Staging Proofs

**Files:**
- Proofs in `proofs/assainissement_step3_<timestamp>/`
- Modify: `ASSAINISSEMENT_KORRIGO.md`

- [ ] Start disposable staging with canonical compose, digest-pinned images, Redis AUTH, GPG backup config, and zero overlays.
- [ ] Run complete backend tests in a test image from the same source commit, plus frontend vitest.
- [ ] Exercise upload PDF, Celery finalization, concurrent student access, shared-IP student login rate limit, protected media, PDF iframe headers/CSP, and role parcours.
- [ ] Confirm Celery runs reconciled code.
- [ ] Archive all proofs, redact PII, teardown staging.
- [ ] Write runbook and rollback procedure.
- [ ] Leave Porte 3 unchecked and stop before production action.
