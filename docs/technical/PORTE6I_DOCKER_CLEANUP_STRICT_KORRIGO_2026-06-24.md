# Porte 6I — Nettoyage Docker strict Korrigo

**Date** : 2026-06-24
**Opérateur** : Claude Code
**Branche** : `hotfix/lot0-rgpd-deploy-clean`
**HEAD** : `09af251815c08267944ac2f0f5b7ae05a6476d33`

## Contexte

- Porte 6L validée : `POST_PAGES_DEPLOY_OBSERVATION_DONE`
- Cleanup Docker autorisé uniquement dans le périmètre Korrigo
- Objectif : supprimer les images GHCR obsolètes remplacées par les images direct-deploy

## 1. Préflight

| Check | Résultat |
|-------|----------|
| Health API | `{"status":"healthy","database":"connected"}` |
| nginx | `korrigo-nginx:korrigo-direct-81b85c5` healthy (2h) |
| backend/celery/celery-beat | `korrigo-backend:korrigo-direct-c38a586` healthy (8h) |
| DB | `postgres:15-alpine` healthy (5 weeks) |
| Redis | `redis:7-alpine` healthy (3 days) |
| Disk | 198G available |
| Backup latest | `20260624T161702Z` checksums OK |
| StorageBox | `WOULD_TRANSFER=0`, `DELETE=0`, `ERROR=0` |

## 2. Inventaire images Korrigo

### Images protégées (6)

| Image | ID | Raison |
|-------|----|--------|
| `korrigo-nginx:korrigo-direct-81b85c5` | `6d0c8c7dd0b1` | Active (nginx running) |
| `korrigo-backend:korrigo-direct-c38a586` | `7011ded2c047` | Active (backend/celery/celery-beat) |
| `korrigo-backend:korrigo-direct-f793f0c` | `c5da5a111002` | Rollback |
| `korrigo-backend:korrigo-lot0g-direct-1fc58d1` | `6f08c27d903f` | Rollback |
| `korrigo-nginx:korrigo-direct-f793f0c` | `5e9c7675264f` | Rollback |
| `korrigo-nginx:korrigo-lot0g-direct-1fc58d1` | `528a98863479` | Rollback |

### Candidats supprimés (2)

| Image | ID | Taille | Raison |
|-------|----|--------|--------|
| `ghcr.io/cyranoaladin/korrigo-nginx` | `5c4dda163f3c` | 88.7MB | GHCR obsolète, remplacée par direct-deploy |
| `ghcr.io/cyranoaladin/korrigo-backend` | `aafe75e7e4bc` | 1.31GB | GHCR obsolète, remplacée par direct-deploy |

### Validation déterministe

- `CANDIDATE_COUNT=2`
- `CANDIDATE_VALIDATION_BAD_COUNT=0`
- Aucun candidat n'est une image de base (postgres, redis, nginx)
- Aucun candidat n'est utilisé par un conteneur running
- Aucun candidat n'est dans la liste protégée
- Suppression par image ID explicite uniquement

## 3. Volumes protégés

| Volume | Statut avant | Statut après |
|--------|-------------|--------------|
| `docker_postgres_data` | PRESENT | PRESENT |
| `docker_media_volume` | PRESENT | PRESENT |
| `docker_backup_volume` | PRESENT | PRESENT |

## 4. Post-cleanup

| Check | Avant | Après |
|-------|-------|-------|
| Disk used | 685G | 684G |
| Disk avail | 198G | 198G |
| Health API | OK | OK |
| Images protégées | 7/7 | 7/7 |
| Volumes protégés | 3/3 | 3/3 |
| Korrigo images | 8 | 6 |
| GHCR images | 2 | 0 |
| Services healthy | 6/6 | 6/6 |

### Playwright production smoke post-cleanup

| Route | Status | H1 | Email | Forbidden | Console | Network |
|-------|--------|----|-------|-----------|---------|---------|
| `/korrigo` | 200 | 1 | 0 | 0 | 0 | 0 |
| `/korrigo/guide-enseignant` | 200 | 1 | 0 | 0 | 0 | 0 |
| `/korrigo/guide-eleve` | 200 | 1 | 0 | 0 | 0 | 0 |
| `/korrigo/direction` | 200 | 1 | 0 | 0 | 0 | 0 |

## Verdict

**`DOCKER_CLEANUP_DONE`**

## Confirmations

- Aucun GitHub
- Aucun push
- Aucun build Docker
- Aucun déploiement
- Aucun restart
- Aucun `docker compose down`
- Aucun `down -v`
- Aucun `docker system prune`
- Aucun `docker volume prune`
- Aucun `docker network prune`
- Aucune suppression de volume
- Aucune suppression de réseau
- Aucune suppression de backup
- Aucune suppression DB/Redis
- Aucune suppression de conteneur running
- Aucune suppression d'image non-Korrigo
- Aucune suppression d'image active
- Aucune suppression d'image rollback
- Aucune migration
- Aucun SQL
- Aucune PII
