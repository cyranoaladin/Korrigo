# Porte 5A - Compose canonical reconciliation - 2026-06-23

## Contexte

La Porte 4 est terminee : production healthy, environ 48G recuperes, images
Korrigo obsoletes supprimees, volumes et services data preserves.

Dette traitee par cette porte : le runtime Lot 0-G etait maintenu par un
override persistant, tandis que le compose canonique referenceait encore les
images GHCR de rollback. Une commande Compose sans override aurait donc pu
revenir aux anciennes images applicatives.

Runtime attendu :

- backend/celery/celery-beat : `korrigo-backend:korrigo-lot0g-direct-1fc58d1`;
- nginx : `korrigo-nginx:korrigo-lot0g-direct-1fc58d1`.

## Preflight

Preflight local :

- branche : `hotfix/lot0-rgpd-deploy-clean`;
- HEAD initial : `57f79b105e0d790477a35584e2826a9dd37bce94`;
- worktree propre.

Preflight production :

- host : `korrigo`;
- disque : `/dev/md2 929G 682G 201G 78% /`;
- services Korrigo healthy avec l'override Lot 0-G;
- health public : `{"status":"healthy","database":"connected"}`.

Garde backup/sync avant modification :

```text
LATEST_ENCRYPTED_BACKUP=20260623T161702Z
db.sql.gz.gpg: OK
media_inventory.txt.gpg: OK
manifest.json: OK
WOULD_TRANSFER_COUNT=0
DELETE_COUNT=0
ERROR_WORD_COUNT=0
```

Audit serveur :

`/var/www/labomaths/korrigo_release/ops/porte5a_compose_reconcile_20260623T183518Z`

## Diff Compose

Fichier modifie sur le serveur :

`/var/www/labomaths/korrigo_release/infra/docker/docker-compose.prod.yml`

Avant modification, le compose canonique referenceait :

- backend/celery/celery-beat : `ghcr.io/cyranoaladin/korrigo-backend@sha256:aafe75e7e4bc475f066ed57cc4b16dc816ea3497c70f3e8e954c5ba496929e1e`;
- nginx : `ghcr.io/cyranoaladin/korrigo-nginx@sha256:5c4dda163f3ce4a4ff7e4a2b321adafb398cc3cdaa4461d708de89dabae0f61a`;
- db : `postgres:15-alpine`;
- redis : `redis:7-alpine`.

Modification appliquee :

- `backend.image` -> `korrigo-backend:korrigo-lot0g-direct-1fc58d1`;
- `celery.image` -> `korrigo-backend:korrigo-lot0g-direct-1fc58d1`;
- `celery-beat.image` -> `korrigo-backend:korrigo-lot0g-direct-1fc58d1`;
- `nginx.image` -> `korrigo-nginx:korrigo-lot0g-direct-1fc58d1`.

Non modifies :

- `db`;
- `redis`;
- volumes;
- reseaux;
- ports;
- healthchecks;
- commandes;
- variables d'environnement;
- policies de restart;
- chemins applicatifs.

Controle diff :

```text
APP_IMAGE_DIFF_LINES=8
FORBIDDEN_DIFF_SECRET_COUNT=0
```

## Validation

`docker compose config --quiet` sans override : PASS.

Images effectives canonique apres modification :

```text
image: korrigo-backend:korrigo-lot0g-direct-1fc58d1
image: korrigo-backend:korrigo-lot0g-direct-1fc58d1
image: korrigo-backend:korrigo-lot0g-direct-1fc58d1
image: postgres:15-alpine
image: korrigo-nginx:korrigo-lot0g-direct-1fc58d1
image: redis:7-alpine
```

Comparaison canonique vs canonique + override :

```text
CANONICAL_MATCHES_OVERRIDE_IMAGES=YES
CANONICAL_OVERRIDE_DIFF_SIZE=0
```

Conteneurs actuels :

```text
docker-backend-1 IMAGE=korrigo-backend:korrigo-lot0g-direct-1fc58d1 ID=7b0f74171847...
docker-celery-1 IMAGE=korrigo-backend:korrigo-lot0g-direct-1fc58d1 ID=97f234d57fa9...
docker-celery-beat-1 IMAGE=korrigo-backend:korrigo-lot0g-direct-1fc58d1 ID=c24c1e709bd8...
docker-nginx-1 IMAGE=korrigo-nginx:korrigo-lot0g-direct-1fc58d1 ID=37aa1f0ab071...
docker-redis-1 ID=8a8bf2b8e8cc
docker-db-1 ID=54202b9d02f8
```

Aucun `docker compose up` n'a ete lance : les conteneurs etaient deja coherents
avec le compose canonique modifie.

## Runbook

Runbook serveur mis a jour :

`/var/www/labomaths/korrigo_release/ops/lot0g/README_LOT0G_RUNTIME.md`

Ajout : depuis Porte 5A, le compose canonique reference directement les images
runtime Lot 0-G. L'override reste archive a :

`/var/www/labomaths/korrigo_release/ops/lot0g/docker-compose.lot0g.override.yml`

Les commandes de statut routinieres peuvent utiliser le compose canonique seul.
L'override peut encore servir de verification supplementaire.

## Sante finale

Verification finale sans override :

```text
docker-backend-1       korrigo-backend:korrigo-lot0g-direct-1fc58d1   Up healthy
docker-celery-1        korrigo-backend:korrigo-lot0g-direct-1fc58d1   Up healthy
docker-celery-beat-1   korrigo-backend:korrigo-lot0g-direct-1fc58d1   Up healthy
docker-db-1            postgres:15-alpine                            Up healthy
docker-nginx-1         korrigo-nginx:korrigo-lot0g-direct-1fc58d1     Up healthy
docker-redis-1         redis:7-alpine                                Up healthy
```

Health public final :

```json
{"status":"healthy","database":"connected"}
```

## Confirmations

- Aucun push GitHub.
- Aucune PR.
- Aucun GHCR.
- Aucun workflow GitHub.
- Aucun build Docker.
- Aucun `docker compose up`.
- Aucun redemarrage applicatif.
- Aucun `docker compose down`.
- Aucun `down -v`.
- Aucun prune.
- Aucun volume supprime.
- Aucun backup supprime.
- Aucune migration.
- Aucun secret, `.env` ou PII affiche.

## Risques residuels

- Le compose serveur est reconcilie, mais le depot distant/GitHub reste non
  aligne avec la production.
- La modification compose canonique n'est pas poussee vers GitHub.
- Le gate anti-PII doit encore passer en HMAC/pepper.
- Les emails hors bundle doivent encore etre classes.
- `BilanBacBlanc.vue` reste une dette structurelle.
- Le build cache Docker reste massif et non traite car non attribuable
  strictement a Korrigo.

## Prochaine etape recommandee

1. Porte 5B : HMAC/pepper anti-PII et classification des emails hors bundle.
2. Strategie Git/main prive : realigner l'historique et integrer les changements
   serveur de maniere auditable.
