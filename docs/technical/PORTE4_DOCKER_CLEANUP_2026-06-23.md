# Porte 4 Docker cleanup - 2026-06-23

## Contexte

La Porte 4 a ete executee apres le GO Lot 0-M. La chaine backup/sync v2 etait
verte avant toute suppression :

- dernier backup chiffre verifie : `20260623T161702Z`;
- checksums locaux : OK;
- sync StorageBox dry-run : `WOULD_TRANSFER_COUNT=0`, `DELETE_COUNT=0`,
  `ERROR_WORD_COUNT=0`;
- production healthy : `{"status":"healthy","database":"connected"}`.

Objectif : recuperer de l'espace Docker en supprimant uniquement les artefacts
Korrigo obsoletes, sans toucher aux donnees, aux volumes, aux reseaux, aux
conteneurs vivants, aux images runtime/rollback, ni aux projets non-Korrigo.

## Preflight

Audit serveur :

- host : `korrigo`;
- audit dir : `/var/www/labomaths/korrigo_release/ops/porte4_docker_cleanup_20260623T172427Z`;
- services Korrigo : 6 services healthy via compose avec l'override Lot 0-G;
- health public : OK.

Disque avant :

```text
/dev/md2        929G  730G  153G  83% /
```

Docker avant :

```text
Images          110       19        573.1GB   501.1GB (87%)
Containers      24        24        22.29MB   0B (0%)
Local Volumes   72        18        25.86GB   744.1MB (2%)
Build Cache     1487      0         518.8GB   466.8GB
```

## Ressources protegees

Les ressources suivantes ont ete explicitement preservees :

- images runtime Lot 0-G :
  - `korrigo-backend:korrigo-lot0g-direct-1fc58d1`;
  - `korrigo-nginx:korrigo-lot0g-direct-1fc58d1`;
- images rollback pre-Lot0G :
  - backend digest `sha256:aafe75e7e4bc475f066ed57cc4b16dc816ea3497c70f3e8e954c5ba496929e1e`;
  - nginx digest `sha256:5c4dda163f3ce4a4ff7e4a2b321adafb398cc3cdaa4461d708de89dabae0f61a`;
- images data services :
  - `postgres:15-alpine`;
  - `redis:7-alpine`;
- conteneurs vivants, dont `docker-db-1` et `docker-redis-1`;
- volumes proteges :
  - `docker_postgres_data`;
  - `docker_media_volume`;
  - `docker_backup_volume`;
- backups chiffres v2 et backups legacy;
- reseaux Docker.

IDs data services apres nettoyage :

```text
docker-redis-1 8a8bf2b8e8cc redis:7-alpine Up 2 days (healthy)
docker-db-1 54202b9d02f8 postgres:15-alpine Up 5 weeks (healthy)
```

## Inventaire

Inventaires complets conserves dans l'audit dir :

- `docker_system_df_before.txt`;
- `docker_system_df_verbose_before.txt`;
- `docker_ps_all_before.txt`;
- `docker_images_before.txt`;
- `docker_volumes_before.txt`;
- `docker_networks_before.txt`;
- `docker_builder_du_before.txt`;
- `docker_builder_du_verbose_before.txt`.

Candidats identifies :

- conteneurs Korrigo arretes : `0`;
- references images Korrigo obsoletes : `76`;
- IDs images uniques Korrigo obsoletes : `74`;
- build cache : inventorie, non supprime, car non attribuable de maniere fiable
  a Korrigo uniquement;
- `/tmp/korrigo-lot0g-images` : conserve, taille observee `315M`.

## Plan execute

```text
PLAN_DELETE_STOPPED_KORRIGO_CONTAINERS=0
PLAN_DELETE_KORRIGO_IMAGE_REFS=76
PLAN_DELETE_KORRIGO_UNIQUE_IMAGE_IDS=74
PLAN_BUILDER_PRUNE_UNTIL_24H=NO_NON_KORRIGO_CACHE_NOT_ATTRIBUTABLE
PLAN_DELETE_TMP_LOT0G_IMAGES=NO_KEEP_RECENT_ARTIFACTS
PLAN_DELETE_VOLUMES=NO
PLAN_DELETE_NETWORKS=NO
PLAN_TOUCH_DB_REDIS=NO
PLAN_TOUCH_NON_KORRIGO=NO
```

## Actions executees

- Suppression de conteneurs arretes Korrigo : aucune, car aucun candidat.
- Suppression d'images : `docker rmi` sur les 76 references Korrigo candidates,
  sans `--force`.
- Images effectivement supprimees : 74 IDs.
- Build cache : aucun prune execute.
- Volumes : aucun volume supprime.
- Networks : aucun network supprime.
- Artefacts `/tmp/korrigo-lot0g-images` : conserves.

Fichier de log Docker :

- `/var/www/labomaths/korrigo_release/ops/porte4_docker_cleanup_20260623T172427Z/docker_rmi_korrigo_images.log`

## Post-cleanup

Production apres nettoyage :

- 6 services Korrigo healthy;
- health public OK;
- DB/Redis non recrees;
- volumes proteges presents;
- images runtime et rollback presentes.

Disque apres :

```text
/dev/md2        929G  682G  201G  78% /
```

Docker apres :

```text
Images          36        19        519.4GB   503GB (96%)
Containers      24        24        22.29MB   0B (0%)
Local Volumes   72        18        25.86GB   744.1MB (2%)
Build Cache     1487      0         518.8GB   474GB
```

Espace disque recupere sur `/` : environ `48G` selon `df`.

Compteurs :

```text
REMOVED_IMAGE_REF_COUNT=76
DELETED_IMAGE_ID_COUNT=74
VOLUME_COUNT_BEFORE=73
VOLUME_COUNT_AFTER=73
KORRIGO_CANDIDATES_REMAINING_AFTER=0
```

## Incidents

Deux erreurs non destructives de scripting ont ete rencontrees pendant
l'inventaire :

- un quoting `awk` sous `set -u`;
- une expression Python de synthese mal quotee.

Elles ont ete corrigees avant toute suppression. Aucun effet sur Docker, les
services, les volumes ou les backups.

## Confirmations

- Aucun `docker system prune`.
- Aucun `docker volume prune`.
- Aucun `docker network prune`.
- Aucun `docker compose down`.
- Aucun `down -v`.
- Aucun volume supprime.
- Aucun reseau supprime.
- Aucun conteneur vivant supprime.
- Aucun conteneur DB/Redis supprime ou recree.
- Aucun projet non-Korrigo touche.
- Aucun backup supprime.
- Aucun secret, `.env` ou PII affiche.
- Aucun GitHub/GHCR/workflow utilise.

## Risques residuels

- Le build cache Docker reste massif, mais n'a pas ete prune car non
  strictement attribuable a Korrigo.
- Le compose canonique doit encore etre reconcilie avec l'etat runtime Lot 0-G.
- `main` Git reste non alignee avec la production.
- Le gate anti-PII doit encore passer en HMAC/pepper.
- Les backups legacy restent conserves, avec permissions durcies.
- La retention StorageBox longue duree reste a finaliser.
- `BilanBacBlanc.vue` reste une dette fonctionnelle/architecture.
