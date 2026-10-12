# Korrigo production remediation implementation plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development. Steps use checkbox syntax for tracking.

**Goal:** Restore Korrigo production functionality and reconcile its source, runtime and operations without losing existing data.

**Architecture:** Preserve project `docker` and its data volumes. Apply scoped network repair, explicit inference connectivity, secret-free Compose configuration and tested source fixes, with image and configuration rollback.

**Tech Stack:** Django, Celery, PostgreSQL, Redis, Vue, Vite, Docker Compose, Nginx, systemd, iptables.

User approved this scope and production changes on 2026-10-12. Each step is a 2–5 minute unit; builds and full test runs may run longer in the background.

## Chunk 1: Preserve and repair connectivity

- [x] Capture current service/image/volume metadata and configuration in a root-only checkpoint. Copy secret-bearing files directly on the server; print only safe metadata.
- [x] Reproduce outbound IPv4 failure from backend and verify stale bridge references in forwarding rules.
- [x] Add behavioral tests for a scoped, idempotent network repair helper in `scripts/ops/repair_korrigo_egress.py`; prove RED before implementation.
- [x] Implement the minimum bridge lookup and HTTPS/established forwarding rules. Preserve existing rules and avoid a Docker daemon restart.
- [x] Deploy helper with a systemd unit/timer, apply once, prove outbound catalog GET succeeds and existing public/proxied health remains good.
- [x] Establish the intended RAG/Ollama endpoints and validate their authentication and available models without sending student data.

## Chunk 2: Reconcile source and dependencies

- [x] Write a MigrationLoader regression in backend tests; observe missing identification migration failure.
- [x] Restore `backend/identification/migrations/0001_initial.py` and `__init__.py` from `c38a586`; verify migration loader and graph.
- [x] Write OCR regressions for absent/empty/whitespace model and explicit overrides; observe RED.
- [x] Correct model fallback in identification OCR, preserving explicit values and provider-compatible model IDs; verify GREEN.
- [x] Align Pillow security minimum with the deployed September patch and select a compatible Django security update from primary sources; run backend tests.
- [x] Reproduce frontend audit/test/build baseline, update vulnerable dependencies minimally, switch Docker builds to `npm ci`, and run audit/tests/build again.
- [x] Review each task for spec compliance and code quality before integration.

## Chunk 3: Canonical runtime and secrets

- [x] Verify the existing volumes and exact runtime settings through a redacted comparison.
- [x] Update `infra/docker/docker-compose.prod.yml` for configurable pinned images, persistent Beat schedule, explicit inference connectivity and Redis volume retention/durability. Test rendered behavior with synthetic secrets.
- [x] Prepare server environment and secret-free production overrides atomically with root-only permissions.
- [x] Rotate manageable service secrets in a coordinated maintenance window. Preserve backup decryptability and distinguish provider management access from inference access.
- [x] Record exact image digests, Git source, effective Compose files and rollback command in an updated production manifest.
- [x] Deploy tested application images and changed services using `up -d --no-deps`; never use `down -v` or prune.

## Chunk 4: Public access and functional verification

- [x] Check registrar/DNS access and restore authoritative delegation plus the Korrigo record if authority is available.
- [ ] Validate DNS with authoritative and independent recursive resolvers, then validate TLS and ordinary public access.
- [x] Exercise authenticated role endpoints through temporary, controlled test access; preserve accounts and records.
- [x] Test AI inference with a harmless synthetic prompt and OCR fixture, not student data; test configured fallback.
- [x] Run integrity/migration checks, Celery ping, browser desktop/mobile smoke and focused response sampling.
- [x] Update the operational runbook and evidence with exact passing checks and remaining external blockers. Commit only reviewed, verified changes; publish the reviewed branch if appropriate within the user's authorization.

## Chunk 5: Teacher empty-assignment regression discovered by browser verification

- [x] Reproduce the empty type modal and blocked logout without assigning or changing any real exam.
- [x] Add behavioral tests using the real dashboard and selection component; observe two RED cases for successful empty array/paginated responses.
- [x] Emit an empty-list event only after a successful response; hide the selection modal and stop dashboard loading while preserving loading/error/single/multiple-type behavior.
- [x] Verify all six cases, the full 368-test frontend suite, typecheck and build; obtain independent source/test review.
- [x] Build and deploy only the pinned Nginx frontend image, preserving backend images, secrets and data volumes.
- [x] Verify the teacher login/dashboard/reload/route guard/logout in a real browser, then remove only controlled temporary audit accounts.

External authority unavailable: OVH/ATI domain restoration and OpenRouter provider-key rotation remain open. DNS still NXDOMAIN; TLS and HTTP are verified only with explicit resolution. Internal service-secret rotation and historical/new backup decryption are complete.

## Chunk 6: Release validation consistency discovered before publication

- [x] Reproduce the release phase's SQLite/PostgreSQL mismatch and broken skipped-summary detection with focused behavioral regressions, without executing destructive reset/seed phases.
- [x] Use PostgreSQL test settings backed by the isolated CI stack's existing DATABASE_URL; correct the skipped-summary expression, preserving all tests and the zero-skipped policy.
- [x] Run contract regressions and the complete backend suite on local isolated PostgreSQL; independently review the minimal script/test diff.
- [ ] Verify the GitHub push validation run and record its actual outcome separately from live production checks.

## Chunk 7: Complete privacy and fresh-stack validation

- [x] Reproduce the missing privacy secret and empty reference corpus; fail closed for empty markers with a behavioral regression.
- [x] Generate real HMAC references entirely in server memory, keep the pepper in private operations storage, configure its GitHub secret, and verify source/built-assets scans without exporting identities.
- [x] Prove a real reference is detected by an in-memory positive canary; verify that checker output contains neither the identity nor the pepper.
- [x] Reproduce the smoke caller overwriting its pepper and the missing post-build scan; inherit the caller's actual secret and scan the compiled frontend, with targeted RED/GREEN tests.
- [x] Reproduce fresh-stack startup before migrations with fake Docker; start healthy DB/Redis and apply explicit one-shot migrations before the application, preserving all subsequent release checks. Four behavioral cases and fourteen existing backend contracts pass.
- [ ] Review, publish and obtain green checks on the updated PR; merge the tested result and obtain the mandatory manual main release validation.
- [ ] Publish the exact main archive as canonical server source without recreating already-verified application images; verify archive parity, healthy services, main/local/pointer alignment and final evidence.
