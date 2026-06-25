# Porte 6L — Observation courte post-déploiement pages publiques

**Date** : 2026-06-24
**Opérateur** : Claude Code
**Branche** : `hotfix/lot0-rgpd-deploy-clean`
**HEAD** : `2dfa7e2904d59646ff862f9d26808444777dba1d`

## Contexte

- Porte 6K a déployé nginx `korrigo-nginx:korrigo-direct-81b85c5` (pages durcies)
- Porte 6K-VERIFY a confirmé le déploiement avec faux positifs bundle documentés
- Cette porte vérifie la stabilité post-déploiement et prouve l'automaticité du backup

## 1. Préflight production

| Service | Image | Status |
|---------|-------|--------|
| nginx | `korrigo-nginx:korrigo-direct-81b85c5` | healthy (25 min) |
| backend | `korrigo-backend:korrigo-direct-c38a586` | healthy (7h) |
| celery | `korrigo-backend:korrigo-direct-c38a586` | healthy (7h) |
| celery-beat | `korrigo-backend:korrigo-direct-c38a586` | healthy (7h) |
| db | `postgres:15-alpine` | healthy (5 weeks) |
| redis | `redis:7-alpine` | healthy (3 days) |
| Health API | `{"status":"healthy","database":"connected"}` | OK |
| Disk | 198G available | OK |

## 2. Preuve backup automatique `20260624T161702Z`

### Mécanisme de planification

Cron fichier `/etc/cron.d/korrigo_backup_encrypted_v2` :
- `17 */6 * * * root korrigo_backup_encrypted_v2.sh --run` → backup à `:17` toutes les 6h
- `47 */6 * * * root korrigo_sync_storagebox_v2.sh --run` → sync à `:47` toutes les 6h

### Pattern de backups observé

| Timestamp | Heure CEST | Cycle cron | Type |
|-----------|------------|------------|------|
| `20260623T101702Z` | 12:17:02 | `*/6` à 12h | auto |
| `20260623T161702Z` | 18:17:02 | `*/6` à 18h | auto |
| `20260623T221701Z` | 00:17:01 | `*/6` à 0h | auto |
| `20260624T041702Z` | 06:17:02 | `*/6` à 6h | auto |
| `20260624T101701Z` | 12:17:01 | `*/6` à 12h | auto |
| `20260624T124211Z` | 14:42:11 | hors-cycle | **manuel (6G)** |
| `20260624T161702Z` | 18:17:02 | `*/6` à 18h | **auto** |

Le backup `20260624T161702Z` correspond exactement au cycle cron `*/6` à 18h17 CEST (16:17 UTC).
Le backup manuel 6G `20260624T124211Z` est clairement hors-cycle (14:42 CEST).

**Conclusion** : `20260624T161702Z` est un backup automatique planifié.

### Checksums

```
db.sql.gz.gpg: OK
media_inventory.txt.gpg: OK
manifest.json: OK
```

### Log backup

- `KORRIGO_BACKUP_V2 status=PASS` pour chaque cycle
- `EMAIL_COUNT=0`, `SECRET_WORD_COUNT=0`, `ERROR_LIKE_COUNT=0`

## 3. StorageBox dry-run

```
WOULD_TRANSFER_COUNT=0
DELETE_COUNT=0
ERROR_WORD_COUNT=0
```

Sync log : `EMAIL_COUNT=0`, `SECRET_WORD_COUNT=0`, `ERROR_LIKE_COUNT=0`

## 4. Logs applicatifs post-déploiement nginx

Fenêtre : depuis `2026-06-24T18:58:00Z` (juste après le deploy nginx)

| Service | Email | student_email | anonymous_id | Errors | Warnings |
|---------|-------|---------------|--------------|--------|----------|
| backend | 0 | 0 | 0 | 0 | 0 |
| celery | 0 | 0 | 0 | 0 | 2 |
| celery-beat | 0 | 0 | 0 | 0 | 0 |
| nginx | 0 | 0 | 0 | 0 | 0 |

Les 2 warnings celery sont les scans d'intégrité périodiques :
- `Integrity scan completed: scanned=733 issues=0 repaired=0`
- Comportement normal et sain.

## 5. Playwright production réel

Chromium headless contre `https://korrigo.labomaths.tn`, ~25 minutes après le déploiement :

| Route | Status | H1 | Text len | Email | Forbidden | Console | Network | Failed | CTA `/admin/login` |
|-------|--------|----|----------|-------|-----------|---------|---------|--------|--------------------|
| `/korrigo` | 200 | 1 | 2521 | 0 | 0 | 0 | 0 | 0 | 1 |
| `/korrigo/guide-enseignant` | 200 | 1 | 1583 | 0 | 0 | 0 | 0 | 0 | 1 |
| `/korrigo/guide-eleve` | 200 | 1 | 1346 | 0 | 0 | 0 | 0 | 0 | 1 |
| `/korrigo/direction` | 200 | 1 | 1684 | 0 | 0 | 0 | 0 | 0 | 1 |

Forbidden patterns testés (toutes 0) :
`guide-enseignanthttps`, `Lorem`, `TODO`, `fake`, `dummy`, `anonymous_id`,
`platform-stats`, `OCR`, `LLM`, `intelligence artificielle`.

## 6. Nginx et assets

- Nginx Docker health : `healthy`
- Root `/` : HTTP 200
- Health API `/api/health/` : HTTP 200
- Asset JS `index-DNCo1fxr.js` : HTTP 200

## Verdict

**`POST_PAGES_DEPLOY_OBSERVATION_DONE`**

## Confirmations

- Aucun GitHub
- Aucun push
- Aucun build Docker
- Aucun déploiement nouveau
- Aucun restart
- Aucun SQL
- Aucune migration
- Aucun `docker compose down`
- Aucun `down -v`
- Aucun prune
- Aucun cleanup Docker
- Aucun backup manuel
- Aucun sync manuel
- Aucune PII visible
- Aucun `.env` / secret / pepper affiché

## Prochaine étape

Porte 6I — cleanup Docker strict, uniquement si tout reste propre.
