# Korrigo production remediation implementation plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development. Steps use checkbox syntax for tracking.

**Goal:** Restore Korrigo production functionality and reconcile its source, runtime and operations without losing existing data.

**Architecture:** Preserve project `docker` and its data volumes. Apply scoped network repair, explicit inference connectivity, secret-free Compose configuration and tested source fixes, with image and configuration rollback.

**Tech Stack:** Django, Celery, PostgreSQL, Redis, Vue, Vite, Docker Compose, Nginx, systemd, iptables.

User approved this scope and production changes on 2026-10-12. Each step is a 2–5 minute unit; builds and full test runs may run longer in the background.

## Chunk 1: Preserve and repair connectivity

- [ ] Capture current service/image/volume metadata and configuration in a root-only checkpoint. Copy secret-bearing files directly on the server; print only safe metadata.
- [ ] Reproduce outbound IPv4 failure from backend and verify stale bridge references in forwarding rules.
- [ ] Add behavioral tests for a scoped, idempotent network repair helper in `scripts/ops/repair_korrigo_egress.py`; prove RED before implementation.
- [ ] Implement the minimum bridge lookup and HTTPS/established forwarding rules. Preserve existing rules and avoid a Docker daemon restart.
- [ ] Deploy helper with a systemd unit/timer, apply once, prove outbound catalog GET succeeds and existing public/proxied health remains good.
- [ ] Establish the intended RAG/Ollama endpoints and validate their authentication and available models without sending student data.

## Chunk 2: Reconcile source and dependencies

- [ ] Write a MigrationLoader regression in backend tests; observe missing identification migration failure.
- [ ] Restore `backend/identification/migrations/0001_initial.py` and `__init__.py` from `c38a586`; verify migration loader and graph.
- [ ] Write OCR regressions for absent/empty/whitespace model and explicit overrides; observe RED.
- [ ] Correct model fallback in identification OCR, preserving explicit values and provider-compatible model IDs; verify GREEN.
- [ ] Align Pillow security minimum with the deployed September patch and select a compatible Django security update from primary sources; run backend tests.
- [ ] Reproduce frontend audit/test/build baseline, update vulnerable dependencies minimally, switch Docker builds to `npm ci`, and run audit/tests/build again.
- [ ] Review each task for spec compliance and code quality before integration.

## Chunk 3: Canonical runtime and secrets

- [ ] Verify the existing volumes and exact runtime settings through a redacted comparison.
- [ ] Update `infra/docker/docker-compose.prod.yml` for configurable pinned images, persistent Beat schedule, explicit inference connectivity and Redis volume retention/durability. Test rendered behavior with synthetic secrets.
- [ ] Prepare server environment and secret-free production overrides atomically with root-only permissions.
- [ ] Rotate manageable service secrets in a coordinated maintenance window. Preserve backup decryptability and distinguish provider management access from inference access.
- [ ] Record exact image digests, Git source, effective Compose files and rollback command in an updated production manifest.
- [ ] Deploy tested application images and changed services using `up -d --no-deps`; never use `down -v` or prune.

## Chunk 4: Public access and functional verification

- [ ] Check registrar/DNS access and restore authoritative delegation plus the Korrigo record if authority is available.
- [ ] Validate DNS with authoritative and independent recursive resolvers, then validate TLS and ordinary public access.
- [ ] Exercise authenticated role endpoints through temporary, controlled test access; preserve accounts and records.
- [ ] Test AI inference with a harmless synthetic prompt and OCR fixture, not student data; test configured fallback.
- [ ] Run integrity/migration checks, Celery ping, browser desktop/mobile smoke and focused response sampling.
- [ ] Update the operational runbook and evidence with exact passing checks and remaining external blockers. Commit only reviewed, verified changes; publish the reviewed branch if appropriate within the user's authorization.
