# Porte 6M — Audit global production Korrigo

**Date** : 2026-06-24
**Opérateur** : Claude Code
**Branche** : `hotfix/lot0-rgpd-deploy-clean`
**HEAD** : `c36f8b0bd25bf2ee708edf9a22f6aee3c1e8f814`

## 1. Runtime production

| Service | Image | Status |
|---------|-------|--------|
| nginx | `korrigo-nginx:korrigo-direct-81b85c5` | healthy (2h) |
| backend | `korrigo-backend:korrigo-direct-c38a586` | healthy (9h) |
| celery | `korrigo-backend:korrigo-direct-c38a586` | healthy (9h) |
| celery-beat | `korrigo-backend:korrigo-direct-c38a586` | healthy (9h) |
| db | `postgres:15-alpine` | healthy (5 weeks) |
| redis | `redis:7-alpine` | healthy (3 days) |

- Health API : `{"status":"healthy","database":"connected"}`
- Compose config : `VALID`
- Disk : 684G used / 198G available

## 2. Backend/Django/API

| Check | Result |
|-------|--------|
| `manage.py check` | 0 issues |
| Unapplied migrations | 0 |
| Copy integrity RC | 0 |
| `EMAIL_COUNT` | 0 |
| `STUDENT_EMAIL_KEY_COUNT` | 0 |
| `ANONYMOUS_ID_KEY_COUNT` | 0 |
| `FINALIZED_WITHOUT_FINAL_PDF` | 0 |
| `ISSUES_ZERO_COUNT` | 1 (≥1) |
| `AT_SIGN_COUNT` | 0 |

## 3. DB invariants

| Metric | Value |
|--------|-------|
| Users | 771 |
| Exams | 8 |
| Copies | 733 |
| Finalized | 731 |
| Finalized with final_pdf | 731 |
| Finalized without final_pdf | 0 |

Aucune donnée nominative affichée.

## 4. Nginx/assets/headers

- `nginx -t` : syntax OK, test successful
- Assets : JS + CSS all 200
- Source maps : none (not exposed)
- Security headers :
  - `X-Frame-Options: DENY`
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `CSP: default-src 'self'; frame-ancestors 'none'`
  - `HSTS: max-age=31536000; includeSubDomains; preload`
  - `Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()`
- HTML cache : `no-cache, no-store, must-revalidate`

## 5. Public routes

| Route | HTTP |
|-------|------|
| `/` | 200 |
| `/api/health/` | 200 |
| `/api/csrf/` | 200 |
| `/korrigo` | 200 |
| `/korrigo/guide-enseignant` | 200 |
| `/korrigo/guide-eleve` | 200 |
| `/korrigo/direction` | 200 |
| `/teacher/login` | 200 |
| `/student/login` | 200 |
| `/admin/login` | 200 |

10/10 routes : aucun 500.

## 6. Playwright production (Chromium headless)

### Pages publiques (4/4)

| Route | Status | H1 | Email | Forbidden | Console | Network | Failed |
|-------|--------|----|-------|-----------|---------|---------|--------|
| `/korrigo` | 200 | 1 | 0 | 0 | 0 | 0 | 0 |
| `/korrigo/guide-enseignant` | 200 | 1 | 0 | 0 | 0 | 0 | 0 |
| `/korrigo/guide-eleve` | 200 | 1 | 0 | 0 | 0 | 0 | 0 |
| `/korrigo/direction` | 200 | 1 | 0 | 0 | 0 | 0 | 0 |

### Pages login (3/3)

| Route | Status | Form | Email | Forbidden | Console | Network |
|-------|--------|------|-------|-----------|---------|---------|
| `/teacher/login` | 200 | 1 | 0 | 0 | 0 | 0 |
| `/student/login` | 200 | 1 | 0 | 0 | 0 | 0 |
| `/admin/login` | 200 | 1 | 0 | 0 | 0 | 0 |

### Route guards (5/5)

| Route | Behavior | Comment |
|-------|----------|---------|
| `/teacher/dashboard` | Redirect → `/` | Guard OK |
| `/student/dashboard` | Redirect → `/` | Guard OK |
| `/admin/dashboard` | Redirect → `/` | Guard OK |
| `/admin` | 404 | Django admin route (not SPA), trailing slash needed |
| `/direction` | 200 + H1 | Page publique direction |

Aucun écran blanc, aucun 500, aucune PII visible.

### Profils authentifiés

```
AUTHENTICATED_PRODUCTION_PROFILE_FLOW_NOT_TESTED_WITH_REAL_LOGIN=YES
REASON=no approved production test account
```

Flows authentifiés couverts par le pipeline E2E local officiel (PASS).

## 7. Frontend hardcoding scan

- `FRONTEND_GLOBAL_SCAN_LINE_COUNT=16`
- `FRONTEND_PUBLIC_SCOPE_RISK_COUNT=0`
- 15 matches dans les fichiers de tests (garde-fous)
- 1 match dans `ResultView.vue` : texte UI légitime "Aucune intelligence artificielle"

## 8. RGPD

### Logs (depuis 2026-06-24T18:50:00Z)

| Service | Email | student_email | anonymous_id | Secret | Error | Warning |
|---------|-------|---------------|--------------|--------|-------|---------|
| backend | 0 | 0 | 0 | 0 | 0 | 4 |
| celery | 0 | 0 | 0 | 0 | 0 | 9 |
| celery-beat | 0 | 0 | 0 | 0 | 0 | 0 |
| nginx | 0 | 0 | 0 | 0 | 0 | 0 |

Warnings : tous des integrity scans `issues=0` (comportement normal).

### Backup permissions

- `/var/backups/korrigo` : `700 root root`
- Tous les répertoires backup : `700 root root`
- Non accessibles au monde.

### Bundle

- `BUNDLE_EMAIL_COUNT=0`
- `BUNDLE_HTML_VISIBLE_RISK_COUNT=0`
- `BUNDLE_UNKNOWN_FINDING_COUNT=0`
- Faux positifs documentés : 22 JS code tokens + 4 third-party tokens (Porte 6K-VERIFY)

## 9. Backups/StorageBox

- Latest backup : `20260624T161702Z` (automatique, cron `*/6` à 18h17 CEST)
- Checksums : `db.sql.gz.gpg: OK`, `media_inventory.txt.gpg: OK`, `manifest.json: OK`
- StorageBox dry-run : `WOULD_TRANSFER=0`, `DELETE=0`, `ERROR=0`

## 10. Docker/compose

- Compose canonical : nginx `81b85c5`, backend `c38a586` ×3
- 6 Korrigo images (2 active + 4 rollback)
- 0 GHCR obsolète (cleaned in 6I)
- 3 protected volumes intact
- Inventory script deployed on server

## 11. Pipeline local officiel

- `LOCAL_RELEASE_CHECK_STATUS=PASS`
- `E2E_STATUS=PASS_EXISTING_PLAYWRIGHT_OR_CYPRESS`

## 12. Dettes restantes

| Debt | Status | Blocker |
|------|--------|---------|
| HMAC réel admin | pepper/input non fournis | Non-bloquant (gate synthétique PASS) |
| Compte test production | non disponible | Flows auth couverts par E2E local |

## Verdict

**`GLOBAL_PRODUCTION_AUDIT_READY_FOR_24H_OBSERVATION`**

## Confirmations

- Aucun GitHub
- Aucun push
- Aucun build Docker
- Aucun déploiement
- Aucun restart
- Aucun SQL d'écriture
- Aucune migration
- Aucun `docker compose down`
- Aucun `down -v`
- Aucun prune
- Aucun cleanup Docker
- Aucune suppression
- Aucun backup/sync manuel
- Aucune PII visible
- Aucun secret affiché
