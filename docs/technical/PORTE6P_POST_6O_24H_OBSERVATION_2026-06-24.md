# Porte 6P — Observation post-6O, verrou 24h

**Date** : 2026-06-24
**Opérateur** : Claude Code
**Branche** : `hotfix/lot0-rgpd-deploy-clean`

## Timing

- Déploiement 6O : `2026-06-24T21:34:35Z`
- Contrôle 6P : `2026-06-24T22:01:25Z`
- Temps écoulé : ~27 minutes
- Seuil 24h : `2026-06-25T21:34:35Z`

## Production

| Service | Image | Status |
|---------|-------|--------|
| nginx | `korrigo-nginx:korrigo-direct-ac5487c` | healthy (26 min) |
| backend | `korrigo-backend:korrigo-direct-c38a586` | healthy (10h) |
| celery | `korrigo-backend:korrigo-direct-c38a586` | healthy (10h) |
| celery-beat | `korrigo-backend:korrigo-direct-c38a586` | healthy (10h) |
| db | `postgres:15-alpine` | healthy (5 weeks) |
| redis | `redis:7-alpine` | healthy (3 days) |
| Health API | OK | |

## Logs (depuis 6O)

| Service | Email | Secret | Error | Warning |
|---------|-------|--------|-------|---------|
| backend | 0 | 0 | 0 | 2 |
| celery | 0 | 0 | 0 | 2 |
| celery-beat | 0 | 0 | 0 | 0 |
| nginx | 0 | 2* | 0 | 0 |

\* Nginx SECRET=2 : faux positifs — mot "Password" dans le nom d'asset `PasswordResetDialog-*.js`.
Backend/celery warnings : integrity scans `scanned=733 issues=0` (normal).
Nginx 404 pour ancien chunk stale (PasswordResetDialog-DMd8MV94.js) : comportement attendu après
redéploiement, le client a chargé le nouveau chunk ensuite.

## Playwright production (12/12 PASS)

| Category | Route | Redirect | Result |
|----------|-------|----------|--------|
| public | `/korrigo` | — | H1=1 ✅ |
| public | `/korrigo/guide-enseignant` | — | H1=1 ✅ |
| public | `/korrigo/guide-eleve` | — | H1=1 ✅ |
| public | `/korrigo/direction` | — | H1=1 ✅ |
| login | `/teacher/login` | — | Form=1 ✅ |
| login | `/student/login` | — | Form=1 ✅ |
| login | `/admin/login` | — | Form=1 ✅ |
| guard | `/corrector-dashboard` | → `/teacher/login` | ✅ |
| guard | `/student/dashboard` | → `/student/login` | ✅ |
| guard | `/admin/dashboard` | → `/admin/login` | ✅ |
| guard | `/direction/dashboard` | → `/admin/login` | ✅ |
| admin | `/admin` | → `/admin/login` | ✅ |

0 emails, 0 forbidden, 0 console errors, 0 network errors.

## Backup/StorageBox

- Latest : `20260624T161702Z` checksums OK
- StorageBox : `WOULD_TRANSFER=0`, `DELETE=0`, `ERROR=0`

## Verdict

**`WAIT_24H_OBSERVATION_AFTER_6O`**

Raison : seulement ~27 minutes écoulées depuis le déploiement 6O.
Seuil 24h : `2026-06-25T21:34:35Z`.

## Confirmations

- Aucun build
- Aucun déploiement
- Aucun restart
- Aucun SQL
- Aucune migration
- Aucun down/prune
- Aucune suppression
- Aucune PII visible
