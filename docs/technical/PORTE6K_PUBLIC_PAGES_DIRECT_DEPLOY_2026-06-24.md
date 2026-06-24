# Porte 6K — Déploiement direct des pages publiques durcies

**Date** : 2026-06-24
**Opérateur** : Claude Code
**Branche** : `hotfix/lot0-rgpd-deploy-clean`
**Commit source pages** : `81b85c524cd5043e3a207f5548e26e71c6050c99`

## Pré-requis validés

### Porte 6H-C — Observation post-réparation (clôturée 2026-06-24T18:52Z)

| Check | Résultat |
|-------|----------|
| Heure UTC | `18:52:25Z` > seuil `18:50:00Z` |
| Health backend | `{"status":"healthy","database":"connected"}` |
| Images backend/celery/celery-beat | `korrigo-backend:korrigo-direct-c38a586` |
| Image nginx (avant déploiement) | `korrigo-nginx:korrigo-direct-f793f0c` |
| Disk | 198G available |
| Backup automatique | `20260624T161702Z` > manual `20260624T124211Z` |
| Checksums backup | `db.sql.gz.gpg: OK`, `media_inventory.txt.gpg: OK`, `manifest.json: OK` |
| StorageBox dry-run | `WOULD_TRANSFER_COUNT=0`, `DELETE_COUNT=0`, `ERROR_WORD_COUNT=0` |
| `GLOBAL_AUDIT_RC` | `0` |
| `EMAIL_COUNT` | `0` |
| `STUDENT_EMAIL_KEY_COUNT` | `0` |
| `ANONYMOUS_ID_KEY_COUNT` | `0` |
| `FINALIZED_WITHOUT_FINAL_PDF_COUNT` | `0` |
| `ISSUES_ZERO_COUNT` | `1` (≥1) |
| `AT_SIGN_COUNT` | `0` |
| Logs applicatifs (backend, celery, celery-beat, nginx) | Aucune erreur |
| Logs backup/sync | 0 erreurs, 0 emails, 0 secrets |

**Verdict 6H-C** : `POST_REPAIR_24H_OBSERVATION_DONE`

## Déploiement pages publiques

### Pipeline local pré-déploiement

- Audit dir : `/tmp/korrigo_porte6k_predeploy_release_check_20260624T185350Z`
- `LOCAL_RELEASE_CHECK_STATUS=PASS`
- `E2E_STATUS=PASS_EXISTING_PLAYWRIGHT_OR_CYPRESS`

### Build nginx

- Image : `korrigo-nginx:korrigo-direct-81b85c5`
- SHA : `81b85c524cd5043e3a207f5548e26e71c6050c99`
- Labels OCI :
  - `org.opencontainers.image.revision=81b85c524cd5043e3a207f5548e26e71c6050c99`
  - `org.opencontainers.image.source=direct-local-korrigo-porte6k-pages`
  - `org.opencontainers.image.version=korrigo-direct-81b85c5`

### Scan PII image nginx

- `PII_GATE_STATUS=PASS`
- `IMAGE_NGINX_EMAIL_COUNT=0`
- `IMAGE_NGINX_ANONYMOUS_ID_COUNT=22` (faux positifs : références JS applicatives `anonymous_id` dans composants Vue)
- `IMAGE_NGINX_PLACEHOLDER_COUNT=4` (faux positifs : mot-clé `todo` du parser markdown/marked.js)

### Transfert et chargement

- Export : `korrigo-nginx-korrigo-direct-81b85c5.tar.gz` (21M)
- SHA256SUMS : OK local et serveur
- `docker load` : OK
- Labels serveur vérifiées : OK

### Déploiement

- Commande : `docker compose ... up -d --no-deps nginx`
- Override temporaire : `docker-compose.porte6k.override.yml`
- Compose config : `--quiet` validé

### Services après déploiement

| Service | Image | Statut | Modifié |
|---------|-------|--------|---------|
| nginx | `korrigo-nginx:korrigo-direct-81b85c5` | healthy | OUI |
| backend | `korrigo-backend:korrigo-direct-c38a586` | healthy (7h) | NON |
| celery | `korrigo-backend:korrigo-direct-c38a586` | healthy (7h) | NON |
| celery-beat | `korrigo-backend:korrigo-direct-c38a586` | healthy (7h) | NON |
| db | `postgres:15-alpine` | healthy (5 weeks) | NON |
| redis | `redis:7-alpine` | healthy (3 days) | NON |

### Audit pages production

| Page | Status HTTP | SPA shell | Assets JS | Emails | Typos |
|------|-------------|-----------|-----------|--------|-------|
| `/korrigo` | 200 | OK | 200 | 0 | 0 |
| `/korrigo/guide-enseignant` | 200 | OK | 200 | 0 | 0 |
| `/korrigo/guide-eleve` | 200 | OK | 200 | 0 | 0 |
| `/korrigo/direction` | 200 | OK | 200 | 0 | 0 |

- `/admin/login` : accessible (200)
- Health API : `{"status":"healthy","database":"connected"}`

### Réconciliation compose

- Serveur : `infra/docker/docker-compose.prod.yml` — nginx image mise à jour
- Local : `infra/docker/docker-compose.prod.yml` — nginx image alignée
- Local : `scripts/release/local_release_check.sh` — expected image nginx alignée
- Diff : strictement image-only (une ligne par fichier)

## Confirmations

- Aucun GitHub
- Aucun push
- Aucun backend rebuild
- Aucun DB/Redis touché
- Aucune migration
- Aucun `docker compose down`
- Aucun `down -v`
- Aucun prune
- Aucun cleanup Docker
- Aucune PII affichée
- Aucun hardcoding dispersé
- Aucun `.env` / secret / pepper affiché
