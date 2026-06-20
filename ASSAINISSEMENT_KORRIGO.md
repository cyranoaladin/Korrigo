# Assainissement Korrigo — Checklist d'exécution (pilotage Codex)

> Périmètre : dépôt local + production `korrigo.labomaths.tn` (`root@88.99.254.59`)
> Référence factuelle : `AUDIT_COMPLET_KORRIGO_2026-06-20.md`
> Objet : rendre la prod saine, sans surcouches, doublons, caches, orphelins, zombies, code mort ni incohérences — avec un comportement stable et robuste.
> Convention : `- [ ]` à cocher ; une **Porte de sortie** doit être franchie avant de passer à l'étape suivante.

## Comment utiliser ce document

1. Codex traite **une étape à la fois**, dans l'ordre.
2. Chaque tâche se fait en deux temps : **inventaire lecture seule** (preuve d'état) → **exécution réversible** (preuve avant/après).
3. Codex **s'arrête à chaque Porte de sortie** et attend une validation humaine explicite avant de la franchir.
4. Les preuves (chemins, IDs, checksums, rapports) sont consignées dans le **Journal des preuves** en fin de document.

---

## Règles permanentes (revérifier à chaque session)

- [ ] Sauvegarde complète point-in-time (dump + média) disponible et datée de moins de 24 h
- [ ] Aucune opération destructive sans restauration testée préalablement
- [ ] Périmètre **strictement Korrigo** : images `…/korrigo-*`, volumes `docker_*` / `korrigo_*` du projet uniquement
- [ ] Aucun objet d'un autre projet du serveur n'est touché (réseaux, volumes, conteneurs, vhosts)
- [ ] Tout changement de code passe par une branche dédiée puis une validation en staging
- [ ] **Aucun élagage d'image ou de volume avant la validation de l'Étape 2** (les anciennes images sont le seul rollback)
- [ ] Aucune suppression de données de moins d'un an

---

## Tableau de bord (portes franchies)

- [x] **Porte 1** — Point de référence établi
- [x] **Porte 2** — Release réconciliée reconstructible validée *(gate central)*
- [ ] **Porte 3** — Prod basculée sans overlay, configuration unifiée
- [ ] **Porte 4** — Élagage Docker effectué (rollback préservé)
- [ ] **Porte 5** — Orphelins / zombies / scratch supprimés
- [ ] **Porte 6** — Orphelins de données traités
- [ ] **Porte 7** — Dépôt assaini (code mort, fichiers obsolètes, doublons)
- [ ] **Porte 8** — Robustesse runtime en place
- [ ] **Porte 9** — Garde-fous CI anti-rechute actifs

---

## Étape 1 — Point de référence et inventaire
**Mode : lecture seule.** *(réf. §18, §19, §21, §22)*

- [x] Sauvegarde complète (dump + média) confirmée
- [x] Restauration testée dans une pile jetable, health applicatif `OK`
- [x] Inventaire des images Korrigo : IDs, tailles, ancienneté (réf. §18.4 — ~74 images, ~15,2 Gio de cache)
- [x] Inventaire des volumes + références par conteneur (réf. §22.3, §17.2)
- [x] Inventaire des conteneurs : états, uptime (réf. §18.5)
- [x] Liste des montages `overlay/` du compose actif (réf. §19.2)
- [x] Comparaison `django_migrations` (DB) vs fichiers de migration de l'image (réf. §19.4 — écart `exams 0039–0042`)
- [x] `df -h` capturé (réf. §10.1 — disque à 83 %)
- [x] Rapport d'état de référence horodaté archivé

> **Porte de sortie 1** — [x] Backup restaurable **prouvé** + rapport d'état complet archivé.

---

## Étape 2 — Release réconciliée reconstructible *(gate central)*
**Mode : branche dédiée + staging.** *(réf. §19.3, §19.5)*

- [x] Branche `release/reconcile` créée depuis l'état courant
- [x] Overlays **DIFFERS** repliés dans le code source canonique :
  - [x] `exams/views.py`
  - [x] `exams/urls.py`
  - [x] `exams/permissions.py`
  - [x] `core/views.py`
  - [x] `core/settings_prod.py`
  - [x] `backend/bilan/permissions.py`
  - [x] `gunicorn_config.py`
  - [x] `students/serializers.py`
  - [x] `core/views_platform.py`
- [x] Overlays **MISSING_IN_IMAGE** intégrés à la source :
  - [x] `exams/views_direction.py`
  - [x] `exams/views_jury_report.py`
  - [x] `bilan/services/orchestrator_eam.py`
  - [x] `bilan/services/rag_retriever_premiere.py`
  - [x] migrations `bilan 0002`, `exams 0021_merge`
- [x] Doublons de chemins tranchés (`backend/bilan/…` vs `bilan/…`, `backend/exams/…` vs `exams/…`) : canonique = fichier réellement monté, décision documentée
- [x] **Cas critique arbitré explicitement** : `eam_orchestrator.py` (94 597 vs 29 798 octets) — divergence majeure, ne pas dédupliquer à l'aveugle
- [x] Overlays **IDENTICAL** confirmés inutiles et retirés du chemin runtime après tests
- [x] Migrations `exams 0039 → 0042` tracées dans Git et présentes dans l'image
- [x] Migrations fantômes `grading 0013_alter_annotation_type` et `0020_alter_annotation_type` réintroduites dans le graphe canonique
- [x] `0042` réconciliée sur **clone** de la DB (migration réelle ou fake documentée)
- [x] Images rebuild avec labels OCI : `revision`, `source`, `version`, `created`
- [x] Images publiées sous **tag Git + digest** (tag ad hoc interdit)
- [x] Staging : `manage.py check` `OK`
- [x] Staging : `showmigrations --plan` cohérent avec la DB
- [x] Staging : tests permissions / média / migrations / peer-review `OK`
- [x] Staging : health + Celery + tests unitaires backend/frontend `OK`
- [ ] Staging : parcours UI complet admin / correcteur / élève / direction `OK` *(reporté à la recette ; non exercé en Étape 2)*

> **Porte de sortie 2** — [ ] `docker image inspect` remonte au commit ; `showmigrations` reflète la DB ; **aucun overlay nécessaire** au fonctionnement ; staging entièrement vert.
> ⚠️ **Ne franchir aucune étape d'élagage tant que cette porte n'est pas validée.**

---

## Étape 3 — Bascule prod et unification de la configuration
**Mode : exécution prod, rollback conservé.** *(réf. §10.4, §11.5, §21.2)*

- [ ] Bascule prod sur l'image réconciliée **par digest** (pas un tag flottant) — en attente du `go` explicite
- [x] Montages `overlay/` retirés du compose canonique et validés en staging (`overlay_mount_count=0`)
- [x] **Compose unique** : `infra/docker/docker-compose.prod.yml` canonique ; pas de compose racine concurrent dans la branche
- [x] Redis protégé par mot de passe ; backend/celery/celery-beat configurés avec `REDIS_PASSWORD`
- [x] Chiffrement GPG des backups activé (`BACKUP_GPG_PASSPHRASE`) ; cycle backup → déchiffrement → restore jetable prouvé
- [x] `SEED_ON_START=false`, `E2E_SEED_TOKEN` retiré du runtime prod, docs d'API désactivées en prod (`ENABLE_API_DOCS=false`)
- [x] `KORRIGO_SHA` = tag Git `korrigo-step3-20260620-1958681`, image labels OCI `revision=1958681b082402e06d0f463e685d8a9895c460c5`
- [x] Nom des dumps corrigé (`.dump.gpg`, pas `.sql.gz` trompeur) ; image backend contient `pg_dump/pg_restore` 15 et `gpg`
- [x] Entrypoint durci : base vide sans migration = arrêt explicite ; migrations uniquement par one-shot ; `/app/backups` préparé pour Celery
- [x] Rate-limit login élève validé : 10 échecs / 15 min par identifiant tenté ; 11e tentative `429` ; IP partagée non pénalisée sous seuil
- [x] Redis rate-limit : risque d'éviction `allkeys-lru` accepté et documenté (`volume attendu << 256 Mo`) ; alerte mémoire Redis à traiter en Étape 8
- [x] Nginx `/api/students/login/` conservé comme garde-fou anti-flood haut (`30r/s`, `burst=60`), non comme limite métier ; la limite métier reste par identifiant côté Django
- [x] `DEFAULT_PASSWORD` absent du runtime backend/celery/celery-beat ; login élève par mot de passe date de naissance validé
- [x] `_TRIVIAL_PASSWORDS` documenté comme garde-fou du secret d'import/seed one-shot, pas comme exigence runtime permanente
- [x] Runbook v2 durci avant `go` prod : rollback par base recréée, plan de migration contrôlé, migrations one-shot via `--entrypoint python`, média résolu par `docker volume inspect`, gel applicatif avant dump
- [x] Hypothèses infra levées en lecture seule : projet Compose `docker`, répertoire `/var/www/labomaths/korrigo`, DB `docker-db-1`, volume média `docker_media_volume`, PostgreSQL `korrigo_user/korrigo_db`, StorageBox `u554481@u554481.your-storagebox.de:23`, disque `170G` libre
- [x] Runbook v3 durci contre les pièges Compose : pas de `up -d` global, DB protégée par garde ID, Redis recréé explicitement pour AUTH puis gardé stable, aucun `--remove-orphans`
- [x] Backup média : intégrité `.tar.gz.gpg` vérifiée par `gpg -d | tar -tzf -` sans extraction ; nettoyage `/tmp/korrigo_extract` dans le conteneur backend après chiffrement
- [x] Rollback : contrôle post-restore exige contrainte `check_copy_status_valid` revenue à `LOCKED/GRADED` et défaut `pdf_regeneration_pending` absent
- [ ] Pré-requis prod à corriger pendant la bascule : `.env` confirmé en `664` au lieu de `600`; exécuter `chmod 600 .env` avant démarrage de la pile unifiée
- [x] Alias silencieux `n_copies_graded` supprimé : statut métier canonique = `FINALIZED`
- [x] Sweep logs RGPD : backend/celery/entrypoint/nginx sans email, secret ni identifiant de probe en clair
- [x] Staging : redémarrage backend/celery/celery-beat/nginx + health + parcours HTTP par rôle `OK`
- [x] Anciennes images conservées (rollback) ; aucun prune image/volume effectué
- [ ] Prod : backup frais, migrations explicites, déploiement par digest, health, parcours et logs — en attente du `go`

**Runbook M v3 de bascule prévu (ne pas exécuter sans `go`)**

Variables confirmées en lecture seule :
- hôte : `root@88.99.254.59`
- répertoire : `/var/www/labomaths/korrigo`
- compose cible : `/var/www/labomaths/korrigo/infra/docker/docker-compose.prod.yml`
- projet Compose : `docker`
- DB : conteneur `docker-db-1`, user `korrigo_user`, base `korrigo_db`, volume `docker_postgres_data`
- média : volume `docker_media_volume`, mountpoint confirmé `/var/lib/docker/volumes/docker_media_volume/_data`, `8528` fichiers, `14G`
- StorageBox : clé `/root/.ssh/storagebox_ed25519` en `600`, cible `u554481@u554481.your-storagebox.de:23/backups/korrigo_backups`
- disque : `/` et `/var/lib/docker` sur `/dev/md2`, `170G` libres, `81%` utilisés ; seuil bloquant avant pull : moins de `15G` libres ou plus de `90%` utilisés
- anomalie à corriger pendant la bascule : `.env` actuellement en `664`, attendu `600`
- comportement Compose attendu : un `$COMPOSE up -d` global est interdit ; aucun `--remove-orphans` ; DB non recréée et vérifiée par ID ; Redis recréé explicitement une seule fois pour activer `requirepass` ; backend/celery/celery-beat/nginx recréés par changement d'image/digest et retrait overlays

Préparation après `go`, avant gel applicatif :

```bash
ssh root@88.99.254.59
set -euo pipefail
cd /var/www/labomaths/korrigo
export TS="$(date -u +%Y%m%d_%H%M%S)"
export COMPOSE="docker compose --env-file /var/www/labomaths/korrigo/.env -f /var/www/labomaths/korrigo/infra/docker/docker-compose.prod.yml -p docker"
export BACKEND_NEW="ghcr.io/cyranoaladin/korrigo-backend@sha256:aafe75e7e4bc475f066ed57cc4b16dc816ea3497c70f3e8e954c5ba496929e1e"
export NGINX_NEW="ghcr.io/cyranoaladin/korrigo-nginx@sha256:5c4dda163f3ce4a4ff7e4a2b321adafb398cc3cdaa4461d708de89dabae0f61a"
export BACKEND_ROLLBACK="ghcr.io/cyranoaladin/korrigo-backend@sha256:a6b750e56dd976153d62bec16128ebf4d8a1efc6a68fb24fc86c11d46b5657c8"
export NGINX_ROLLBACK="ghcr.io/cyranoaladin/korrigo-nginx@sha256:09401293f50173ce8483df7ea7897ba880e6d3b79450955f9eb70c0fd8ebf7fd"
export DB_ID_BEFORE="$(docker inspect -f '{{.Id}}' docker-db-1)"
export REDIS_ID_BEFORE="$(docker inspect -f '{{.Id}}' docker-redis-1)"
test -f infra/docker/docker-compose.prod.yml
test -f .env
df -h / /var/lib/docker
docker system df
test "$(df -BG /var/lib/docker | awk 'NR==2 {gsub(\"G\",\"\",$4); print ($4 >= 15)}')" = "1"
test "$(df -P /var/lib/docker | awk 'NR==2 {gsub(\"%\",\"\",$5); print ($5 < 90)}')" = "1"
chmod 600 .env
test "$(stat -c %a .env)" = "600"
git status --short --untracked-files=no
test -z "$(git status --porcelain --untracked-files=no)"
git fetch origin release/prod-unification --tags
git switch release/prod-unification
git pull --ff-only origin release/prod-unification
git rev-parse HEAD
git tag --points-at 1958681b082402e06d0f463e685d8a9895c460c5 | grep -x 'korrigo-step3-20260620-1958681'
test "$(docker inspect -f '{{.Id}}' docker-db-1)" = "$DB_ID_BEFORE"
test "$(docker inspect -f '{{.Id}}' docker-redis-1)" = "$REDIS_ID_BEFORE"
grep -E '^(DJANGO_AUTO_MIGRATE|SEED_ON_START|ENABLE_API_DOCS|GUNICORN_WORKERS|REQUIRE_BACKUP_GPG|STUDENT_LOGIN_RATE_LIMIT_ATTEMPTS|STUDENT_LOGIN_RATE_LIMIT_WINDOW)=' .env
test "$(grep -E '^DJANGO_AUTO_MIGRATE=' .env | cut -d= -f2)" = "false"
test "$(grep -E '^SEED_ON_START=' .env | cut -d= -f2)" = "false"
test "$(grep -E '^ENABLE_API_DOCS=' .env | cut -d= -f2)" = "false"
test "$(grep -E '^REQUIRE_BACKUP_GPG=' .env | cut -d= -f2)" = "true"
test -n "$(grep -E '^REDIS_PASSWORD=' .env | cut -d= -f2-)"
test -n "$(grep -E '^BACKUP_GPG_PASSPHRASE=' .env | cut -d= -f2-)"
$COMPOSE config | grep -E 'image:|DJANGO_AUTO_MIGRATE|SEED_ON_START|ENABLE_API_DOCS'
$COMPOSE config --no-interpolate --services | sort | diff -u <(printf "backend\ncelery\ncelery-beat\ndb\nnginx\nredis\n") -
$COMPOSE config --no-interpolate --format json > "/tmp/korrigo_target_compose_${TS}.json"
python3 - "/tmp/korrigo_target_compose_${TS}.json" <<'PY'
import json, sys
cfg = json.load(open(sys.argv[1]))
db = cfg["services"]["db"]
redis = cfg["services"]["redis"]
assert db["image"] == "postgres:15-alpine", db
assert db["ports"][0]["published"] == "5432", db
assert db["ports"][0]["host_ip"] == "127.0.0.1", db
assert db["volumes"][0]["source"] == "postgres_data", db
assert db["volumes"][0]["target"] == "/var/lib/postgresql/data", db
assert redis["image"] == "redis:7-alpine", redis
assert "--requirepass" in redis["command"], redis
assert "REDIS_PASSWORD" in redis["environment"], redis
PY
```

Gel applicatif avant dump de référence :

```bash
# Coupe les écritures externes et asynchrones, tout en gardant backend/db/redis
# disponibles pour l'export JSON interne. Backend n'est pas publié sur l'hôte ;
# nginx arrêté = plus d'ingress HTTP public ; celery/beat arrêtés = plus de tâches
# asynchrones qui modifient copies/bilans/backups pendant le dump.
$COMPOSE stop nginx celery-beat celery
$COMPOSE ps
curl -fsS http://127.0.0.1:8088/ && exit 1 || true
```

Backup complet chiffré après gel, avec média résolu dynamiquement :

```bash
set -a; . ./.env; set +a
export LOCAL_TMP="/tmp/korrigo_predeploy_${TS}"
export MEDIA_VOLUME="docker_media_volume"
export MEDIA_MOUNT="$(docker volume inspect "$MEDIA_VOLUME" --format '{{.Mountpoint}}')"
mkdir -p "$LOCAL_TMP"
test -d "$MEDIA_MOUNT"
MEDIA_FILE_COUNT="$(find "$MEDIA_MOUNT" -type f | wc -l)"
test "$MEDIA_FILE_COUNT" -gt 0
MEDIA_ARCHIVE_FILE_COUNT="$(find "$MEDIA_MOUNT" -type f ! -path "$MEDIA_MOUNT/tmp/*" ! -path "$MEDIA_MOUNT/.cache/*" | wc -l)"
test "$MEDIA_ARCHIVE_FILE_COUNT" -gt 0
docker exec docker-db-1 pg_dump -U korrigo_user -Fc korrigo_db > "$LOCAL_TMP/db_${TS}.dump"
gpg --batch --yes --pinentry-mode loopback --passphrase-fd 3 --symmetric --cipher-algo AES256 -o "$LOCAL_TMP/db_${TS}.dump.gpg" "$LOCAL_TMP/db_${TS}.dump" 3<<<"$BACKUP_GPG_PASSPHRASE"
shred -u "$LOCAL_TMP/db_${TS}.dump"
docker exec -i docker-backend-1 sh -lc 'cat > /app/extract_correction_data.py' < scripts/extract_correction_data.py
if ! docker exec docker-backend-1 python manage.py shell -c 'exec(open("/app/extract_correction_data.py").read())' > "$LOCAL_TMP/extract_${TS}.log" 2>&1; then
  sed -E 's/[[:alnum:]_.%+-]+@[[:alnum:].-]+\.[[:alpha:]]{2,}/<redacted-email>/g' "$LOCAL_TMP/extract_${TS}.log" >&2 || true
  shred -u "$LOCAL_TMP/extract_${TS}.log"
  exit 1
fi
shred -u "$LOCAL_TMP/extract_${TS}.log"
for f in copies_data.json pages_manifest.json exams_bareme.json summary.json; do
  docker exec docker-backend-1 sh -lc "cat /tmp/korrigo_extract/${f}" > "$LOCAL_TMP/${f}"
  gpg --batch --yes --pinentry-mode loopback --passphrase-fd 3 --symmetric --cipher-algo AES256 -o "$LOCAL_TMP/${f}.gpg" "$LOCAL_TMP/${f}" 3<<<"$BACKUP_GPG_PASSPHRASE"
  shred -u "$LOCAL_TMP/${f}"
done
tar -czf "$LOCAL_TMP/media_${TS}.tar.gz" -C "$MEDIA_MOUNT" --exclude="./tmp" --exclude="./.cache" .
test "$(stat -c %s "$LOCAL_TMP/media_${TS}.tar.gz")" -gt 1048576
gpg --batch --yes --pinentry-mode loopback --passphrase-fd 3 --symmetric --cipher-algo AES256 -o "$LOCAL_TMP/media_${TS}.tar.gz.gpg" "$LOCAL_TMP/media_${TS}.tar.gz" 3<<<"$BACKUP_GPG_PASSPHRASE"
shred -u "$LOCAL_TMP/media_${TS}.tar.gz"
sha256sum "$LOCAL_TMP"/*.gpg > "$LOCAL_TMP/SHA256SUMS"
rsync -az --timeout=120 -e "ssh -p 23 -i /root/.ssh/storagebox_ed25519 -o IdentitiesOnly=yes -o StrictHostKeyChecking=no" "$LOCAL_TMP/" u554481@u554481.your-storagebox.de:backups/korrigo_backups/${TS}_predeploy/
ssh -p 23 -i /root/.ssh/storagebox_ed25519 -o IdentitiesOnly=yes -o StrictHostKeyChecking=no u554481@u554481.your-storagebox.de "cd backups/korrigo_backups/${TS}_predeploy && sha256sum -c SHA256SUMS"
MEDIA_TAR_COUNT="$(gpg --batch --yes --pinentry-mode loopback --passphrase-fd 3 -d "$LOCAL_TMP/media_${TS}.tar.gz.gpg" 3<<<"$BACKUP_GPG_PASSPHRASE" | tar -tzf - | grep -v '/$' | wc -l)"
test "$MEDIA_TAR_COUNT" -eq "$MEDIA_ARCHIVE_FILE_COUNT"
docker exec docker-backend-1 sh -lc 'rm -rf /tmp/korrigo_extract && test ! -e /tmp/korrigo_extract'
docker exec docker-backend-1 sh -lc 'find /tmp -path "/tmp/korrigo_extract/*.json" -o -name "copies_data.json"' | tee "/tmp/korrigo_backend_tmp_json_${TS}.txt"
test ! -s "/tmp/korrigo_backend_tmp_json_${TS}.txt"
```

Test rapide de restaurabilité du dump :

```bash
docker network create "korrigo_restore_${TS}"
docker run -d --name "korrigo_restore_db_${TS}" --network "korrigo_restore_${TS}" -e POSTGRES_USER=korrigo_user -e POSTGRES_PASSWORD=restore -e POSTGRES_DB=korrigo_db postgres:15-alpine
until docker exec "korrigo_restore_db_${TS}" pg_isready -U korrigo_user -d korrigo_db; do sleep 2; done
gpg --batch --yes --pinentry-mode loopback --passphrase-fd 3 -d "$LOCAL_TMP/db_${TS}.dump.gpg" 3<<<"$BACKUP_GPG_PASSPHRASE" | docker exec -i "korrigo_restore_db_${TS}" pg_restore -U korrigo_user -d korrigo_db --no-owner
docker exec "korrigo_restore_db_${TS}" psql -U korrigo_user -d korrigo_db -Atc "select count(*) from django_migrations;"
docker rm -f "korrigo_restore_db_${TS}"
docker network rm "korrigo_restore_${TS}"
```

Déploiement image et migrations explicites. Important : les migrations one-shot contournent l'entrypoint fail-fast avec `--entrypoint python`; l'entrypoint reste actif uniquement pour les services longs.

```bash
$COMPOSE pull backend celery celery-beat nginx
test "$(docker inspect -f '{{.Id}}' docker-db-1)" = "$DB_ID_BEFORE"
$COMPOSE stop backend
test "$(docker inspect -f '{{.Id}}' docker-db-1)" = "$DB_ID_BEFORE"
$COMPOSE up -d --no-deps --force-recreate redis
export REDIS_ID_AFTER_AUTH="$(docker inspect -f '{{.Id}}' docker-redis-1)"
test "$REDIS_ID_AFTER_AUTH" != "$REDIS_ID_BEFORE"
test "$(docker inspect -f '{{.Id}}' docker-db-1)" = "$DB_ID_BEFORE"
$COMPOSE exec -T redis sh -lc 'redis-cli -a "$REDIS_PASSWORD" ping'
$COMPOSE run --rm --no-deps --entrypoint python backend manage.py migrate --plan | tee "/tmp/korrigo_migrate_plan_${TS}.txt"
awk '!/^(Planned operations:|exams\\.0042_copy_pdf_regeneration_pending_db_default|    Raw Python operation|exams\\.0043_reconcile_copy_status_constraint|    Alter field status on copy|    Remove constraint check_copy_status_valid from model copy|    Create constraint check_copy_status_valid on model copy|grading\\.0028_reconcile_peer_review_status_constraint|$)/ {count++} END {exit count}' "/tmp/korrigo_migrate_plan_${TS}.txt"
grep -x 'exams.0042_copy_pdf_regeneration_pending_db_default' "/tmp/korrigo_migrate_plan_${TS}.txt"
grep -x 'exams.0043_reconcile_copy_status_constraint' "/tmp/korrigo_migrate_plan_${TS}.txt"
grep -x 'grading.0028_reconcile_peer_review_status_constraint' "/tmp/korrigo_migrate_plan_${TS}.txt"
$COMPOSE run --rm --no-deps --entrypoint python backend manage.py migrate exams 0042 --noinput
$COMPOSE run --rm --no-deps --entrypoint python backend manage.py migrate exams 0043 --noinput
$COMPOSE run --rm --no-deps --entrypoint python backend manage.py migrate grading 0028 --noinput
$COMPOSE run --rm --no-deps --entrypoint python backend manage.py migrate --check --noinput
$COMPOSE run --rm --no-deps --entrypoint python backend manage.py showmigrations exams grading | grep -E '\\[X\\] 0042|\\[X\\] 0043|\\[X\\] 0028'
docker exec docker-db-1 psql -U korrigo_user -d korrigo_db -Atc "select column_default from information_schema.columns where table_schema='public' and table_name='exams_copy' and column_name='pdf_regeneration_pending';" | grep -x 'false'
docker exec docker-db-1 psql -U korrigo_user -d korrigo_db -Atc "select pg_get_constraintdef(oid) from pg_constraint where conrelid='public.exams_copy'::regclass and conname='check_copy_status_valid';" | grep FINALIZED
docker exec docker-db-1 psql -U korrigo_user -d korrigo_db -Atc "select pg_get_constraintdef(oid) from pg_constraint where conrelid='public.grading_peerreviewcorrection'::regclass and conname='check_peer_review_status_valid';" | grep FINALIZED
$COMPOSE up -d --no-deps backend
until [ "$(docker inspect -f '{{.State.Health.Status}}' docker-backend-1)" = "healthy" ]; do sleep 5; done
$COMPOSE up -d --no-deps celery celery-beat nginx
test "$(docker inspect -f '{{.Id}}' docker-db-1)" = "$DB_ID_BEFORE"
test "$(docker inspect -f '{{.Id}}' docker-redis-1)" = "$REDIS_ID_AFTER_AUTH"
$COMPOSE ps
```

Vérifications succès :

```bash
curl -fsS https://korrigo.labomaths.tn/api/health/
$COMPOSE exec -T redis sh -lc 'redis-cli -a "$REDIS_PASSWORD" ping'
$COMPOSE exec -T redis sh -lc 'redis-cli -a "$REDIS_PASSWORD" info stats | grep evicted_keys'
$COMPOSE exec -T backend sh -lc '! env | grep -q "^DEFAULT_PASSWORD="'
for c in docker-backend-1 docker-celery-1 docker-celery-beat-1 docker-nginx-1; do docker inspect "$c" --format '{{range .Mounts}}{{println .Source "->" .Destination}}{{end}}'; done | grep -i overlay && exit 1 || true
$COMPOSE exec -T celery celery -A core inspect ping
$COMPOSE logs --since 15m backend celery celery-beat nginx | grep -Ei '[[:alnum:]_.%+-]+@[[:alnum:].-]+\.[[:alpha:]]{2,}|DEFAULT_PASSWORD|BACKUP_GPG_PASSPHRASE|REDIS_PASSWORD' && exit 1 || true
```

Critères de succès chiffrés : backup distant et restore test `OK`; plan de migrations limité strictement à `exams.0042`, `exams.0043`, `grading.0028`; `migrate --check` code `0`; health `{"status":"healthy","database":"connected"}` ; conteneurs Korrigo `healthy` ; `overlay_mount_count=0` ; `DEFAULT_PASSWORD` absent ; Redis AUTH `PONG` ; Celery `ping` OK ; login élève 10 échecs non limités puis 11e `429` ; IP partagée distincte sans `429` sous seuil ; backup planifié `.dump.gpg` ; `runtime_log_email_count=0`, `runtime_log_secret_count=0`.

Critères d'échec déclenchant rollback : backup frais ou restaurabilité échoué ; plan de migration contenant une migration inattendue ; migration explicite échouée ou verrou long ; health non vert après correction simple ; Redis AUTH cassé ; Celery ne consomme pas `async_finalize_copy` ; médias protégés exposés ou inaccessibles ; logs contenant PII/secret ; régression bloquante d'un parcours rôle.

**Rollback M v2, schéma-conscient**

Le rollback DB ne restaure jamais par-dessus une base déjà migrée. Il recrée `korrigo_db`, puis restaure le dump pré-bascule, afin d'éviter un schéma hybride où des contraintes postérieures au dump subsisteraient.

```bash
$COMPOSE stop nginx celery-beat celery backend
test "$(docker inspect -f '{{.Id}}' docker-db-1)" = "$DB_ID_BEFORE"
cat >/tmp/korrigo-rollback-port2.yml <<'YAML'
services:
  backend:
    image: ghcr.io/cyranoaladin/korrigo-backend@sha256:a6b750e56dd976153d62bec16128ebf4d8a1efc6a68fb24fc86c11d46b5657c8
  celery:
    image: ghcr.io/cyranoaladin/korrigo-backend@sha256:a6b750e56dd976153d62bec16128ebf4d8a1efc6a68fb24fc86c11d46b5657c8
  celery-beat:
    image: ghcr.io/cyranoaladin/korrigo-backend@sha256:a6b750e56dd976153d62bec16128ebf4d8a1efc6a68fb24fc86c11d46b5657c8
  nginx:
    image: ghcr.io/cyranoaladin/korrigo-nginx@sha256:09401293f50173ce8483df7ea7897ba880e6d3b79450955f9eb70c0fd8ebf7fd
YAML
docker exec docker-db-1 psql -U korrigo_user -d postgres -v ON_ERROR_STOP=1 -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='korrigo_db' AND pid <> pg_backend_pid();"
docker exec docker-db-1 psql -U korrigo_user -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE korrigo_db;"
docker exec docker-db-1 psql -U korrigo_user -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE korrigo_db OWNER korrigo_user;"
gpg --batch --yes --pinentry-mode loopback --passphrase-fd 3 -d "$LOCAL_TMP/db_${TS}.dump.gpg" 3<<<"$BACKUP_GPG_PASSPHRASE" | docker exec -i docker-db-1 pg_restore -U korrigo_user -d korrigo_db --no-owner
docker exec docker-db-1 psql -U korrigo_user -d korrigo_db -Atc "select coalesce(column_default,'<NULL>') from information_schema.columns where table_schema='public' and table_name='exams_copy' and column_name='pdf_regeneration_pending';" | grep -x '<NULL>'
docker exec docker-db-1 psql -U korrigo_user -d korrigo_db -Atc "select pg_get_constraintdef(oid) from pg_constraint where conrelid='public.exams_copy'::regclass and conname='check_copy_status_valid';" | grep LOCKED
docker exec docker-db-1 psql -U korrigo_user -d korrigo_db -Atc "select pg_get_constraintdef(oid) from pg_constraint where conrelid='public.exams_copy'::regclass and conname='check_copy_status_valid';" | grep GRADED
$COMPOSE -f /tmp/korrigo-rollback-port2.yml up -d backend celery celery-beat nginx
curl -fsS https://korrigo.labomaths.tn/api/health/
```

Si des écritures média ont eu lieu après réouverture du trafic et avant décision rollback, restaurer aussi le média depuis `media_${TS}.tar.gz.gpg` vers le mountpoint dynamique :

```bash
MEDIA_MOUNT="$(docker volume inspect docker_media_volume --format '{{.Mountpoint}}')"
test -d "$MEDIA_MOUNT"
MEDIA_ROLLBACK_HOLD="/tmp/korrigo_media_hold_${TS}"
mkdir -p "$MEDIA_ROLLBACK_HOLD"
find "$MEDIA_MOUNT" -mindepth 1 -maxdepth 1 -exec mv -t "$MEDIA_ROLLBACK_HOLD" {} +
gpg --batch --yes --pinentry-mode loopback --passphrase-fd 3 -d "$LOCAL_TMP/media_${TS}.tar.gz.gpg" 3<<<"$BACKUP_GPG_PASSPHRASE" | tar -xzf - -C "$MEDIA_MOUNT"
```

Post-bascule immédiat si succès : surveiller disque hôte (`df -h / /var/lib/docker`, actuellement `170G` libres), premier backup chiffré planifié, logs, Celery ; fusionner `release/prod-unification` vers `main` seulement après validation prod pour que `main = prod`; nettoyage branches `wip/*` reporté à une étape ultérieure.

> **Porte de sortie 3** — [ ] Prod sans overlay, configuration unifiée, health vert, rollback encore possible.

---

## Étape 4 — Élagage Docker (images, cache)
**Mode : exécution, après validation finale. Périmètre Korrigo strict.** *(réf. §18.4, §10.1)*

- [ ] Validation de stabilité prod confirmée (durée/critère défini)
- [ ] Images Korrigo anciennes supprimées (conserver l'**active + 3 dernières releases**)
- [ ] Images dangling + cache de build élagués (ciblés Korrigo)
- [ ] (Optionnel) Backend allégé : build multi-stage, base slim, `.dockerignore` (image actuelle ~5,98 Go)
- [ ] Espace récupéré rapporté
- [ ] Aucune image d'un autre projet touchée

> **Porte de sortie 4** — [ ] Empreinte d'images réduite, disque sous le seuil d'alerte, rollback (3 dernières releases) préservé.

---

## Étape 5 — Volumes orphelins, conteneurs zombies, scratch
**Mode : inventaire puis suppression confirmée.** *(réf. §17.2, §22.3)*

- [ ] Inventaire des volumes Korrigo non référencés (candidats `*_local`, `korrigo_*`, `docker_seed_data_v2` si seed off)
- [ ] Confirmation : aucun conteneur ne référence ces volumes
- [ ] Conteneurs `exited`/`dead` Korrigo listés
- [ ] Répertoires scratch résiduels listés (`/tmp/korrigo-restore-*`)
- [ ] Dossiers `fallback_*` au-delà de la rétention listés
- [ ] Suppression des **seuls** orphelins confirmés
- [ ] Volumes vivants intacts (`docker_postgres_data`, `docker_media_volume`)

> **Porte de sortie 5** — [ ] Plus aucun orphelin/zombie Korrigo ; volumes vivants intacts.

---

## Étape 6 — Orphelins au niveau données
**Mode : inventaire puis suppression validée.** *(réf. §21.5)*

- [ ] Recette UI/UX par profil admin / correcteur / élève / direction : parcours complets, états vides, états d'erreur, cohérence visuelle, responsive, accessibilité clavier de base
- [ ] Médias orphelins (fichiers non référencés par un `FileField`) — rapport
- [ ] Lignes orphelines (copies/annotations/scores/`OCRResult`/sessions expirées) — rapport
- [ ] État de la purge de rétention (`purge_old_exam_data`) vérifié ; reste-t-il des données > 1 an ?
- [ ] Suppression validée explicitement, sauvegarde préalable, **jamais < 1 an**

> **Porte de sortie 6** — [ ] Rapport produit ; suppressions validées et tracées ; rétention effectivement appliquée.

---

## Étape 7 — Assainissement du dépôt
**Mode : branche dédiée, tests verts.** *(réf. §3.1, §3.2, §12, §19.3)*

- [ ] Données hors-code sorties du suivi Git (archivées ou supprimées) : `docs_exam/`, `DS_NSI_Premiere_Algo/`, `copies_EAM_2026/`, `scan_*`, `PATCHES/`, `overlay/_archived_*`, `*.before_individual_upload_fix_*`, `stat_BB_MATHS_2026.md`
- [ ] `.gitignore` et `.dockerignore` ajoutés (médias, scans, venv, caches, artefacts de build)
- [ ] `docs/` (normatif) vs `documentation/` (archive) clarifiés ; `docs/INDEX.md` rafraîchi (chiffres périmés)
- [ ] Code mort détecté : `ruff` (imports inutilisés), `vulture` (Python mort), `ts-prune`/`knip` (exports TS), `depcheck` (dépendances)
- [ ] Routes/vues Django non câblées, commandes de management inutilisées, composants/routes Vue morts identifiés
- [ ] **Audit de cohérence FE ↔ BE ↔ DB ↔ nginx ↔ routage** :
  - [ ] Chaque appel API front correspond à une route DRF réelle, versionnée et autorisée
  - [ ] Chaque route Vue correspond à un composant réel et à un guard cohérent
  - [ ] Chaque URL Django correspond à une vue réelle et testée
  - [ ] Chaque `location` nginx cible un upstream réel ou un répertoire explicitement monté
  - [ ] Permissions DRF, guards front, menus et profils utilisateur alignés
  - [ ] Zéro route, composant, endpoint ou service mort non documenté
- [ ] Cibles connues à trancher : `bilan/services/orchestrator_eam.py` (`BilanOrchestratorEAM` dormant), commande one-shot `create_peer_review_produit_scalaire_g6.py` (examen codé en dur)
- [ ] Sweep hardcoding : IDs, noms d'examens, groupes/classes, chemins, seuils, tokens et valeurs métier en dur remplacés par config/env ou fixtures explicites
- [ ] Suppression du code mort confirmé, suite de tests verte
- [ ] Worktree stabilisé (commits propres ou stash documenté)

> **Porte de sortie 7** — [ ] Dépôt sans données ni code mort ; tests verts ; worktree propre.

---

## Étape 8 — Robustesse et stabilité du runtime
**Mode : exécution.**

- [ ] Healthchecks avec `start_period` adapté sur tous les services
- [ ] `restart: unless-stopped`
- [ ] Limites de ressources (`mem_limit`, `cpus`) par conteneur (hôte partagé)
- [ ] Rotation des logs (`json-file` `max-size`/`max-file` ou journald)
- [ ] Format de log Nginx enrichi (`$request_time`, `$request_length`, `$body_bytes_sent`, `$request_id`) + rétention
- [ ] Alertes : disque (>80/90 %), échec de backup, expiration certificat, conteneur non `healthy`
- [ ] Alerte mémoire Redis : surveiller `used_memory`, `maxmemory`, `evicted_keys`; le rate-limit élève partage Redis `allkeys-lru` et peut être affaibli si évictions non nulles
- [ ] `.env` en permissions `600`, secrets hors dépôt
- [ ] Déploiement idempotent par digest
- [ ] Runbook d'exploitation rédigé

> **Porte de sortie 8** — [ ] Services résilients, supervisés ; déploiement reproductible et documenté.

---

## Étape 9 — Garde-fous CI (anti-rechute)
**Mode : intégration continue.**

- [ ] CI échoue si le compose contient un montage `overlay/`
- [ ] CI échoue si `KORRIGO_SHA` n'est pas relié à un commit/tag
- [ ] Gates `ruff` / `vulture` sur le code mort
- [ ] Contrôle de cohérence d'historique migrations (`django_migrations` vs fichiers, dans les deux sens, toutes apps — `migrate --check` ne suffit pas)
- [ ] Job PostgreSQL obligatoire pour migrations et contraintes PG-only (les migrations PG-only sont skippées sous SQLite)
- [ ] Détection bloquante de tout montage `overlay/` ou bind source dans une release/staging/prod candidate
- [ ] Exigence des labels OCI sur les images publiées
- [ ] Vérification `KORRIGO_SHA` / label OCI `revision` / tag Git / digest GHCR résolvent vers le même commit
- [ ] Test de restauration automatisé périodique : backup complet → restore pile jetable → health → parité fichiers référencés

> **Porte de sortie 9** — [ ] Dérive structurellement empêchée ; CI verte.

---

## Journal des preuves

| Date | Étape | Artefact / preuve | Emplacement |
|---|---|---|---|
| 2026-06-20T12:10Z | 1 | Rapport synthèse Étape 1 ; backup complet StorageBox `20260620_133001`, health restore `OK`, `file_refs=1793 missing=0` | `proofs/assainissement_step1_20260620T115755Z/step1_summary_20260620T115755Z.md` |
| 2026-06-20T12:10Z | 1 | Inventaire prod lecture seule : `df -h` (`/` 81 %), 76 tags / 74 images Korrigo uniques, volumes, conteneurs, overlays, migrations | `proofs/assainissement_step1_20260620T115755Z/prod_reference_inventory_20260620T115755Z.txt` |
| 2026-06-20T12:10Z | 1 | Listing backup StorageBox confirmé : `db_20260620_133001.dump` + `media_20260620_133001.tar.gz` + exports JSON | `proofs/assainissement_step1_20260620T115755Z/prod_backup_listing_20260620T115755Z.txt` |
| 2026-06-20T12:10Z | 1 | Rapport distant de restauration jetable ; projet `korrigo-restore-step1-20260620t115755z`, conteneurs démontés, scratch conservé | `proofs/assainissement_step1_20260620T115755Z/restore_report_20260620T115755Z.remote.txt` |
| 2026-06-20T12:10Z | 1 | Checksums SHA-256 des preuves locales | `proofs/assainissement_step1_20260620T115755Z/SHA256SUMS.txt` |
| 2026-06-20T12:10Z | 1 | Backup restauré : `db_20260620_133001.dump` SHA-256 `8270e4a9ea0c4fd2d28a46f12fedf0d383fddbf1f7910588013607aa656bca61` ; `media_20260620_133001.tar.gz` SHA-256 `c4d0ac373a0d68271367dca460f8a469d9ecca54d36e7164c2989a96b7deed80` | StorageBox `backups/korrigo_backups/20260620_133001` ; copie scratch `/tmp/korrigo-restore-step1-20260620t115755z` |
| 2026-06-20T13:10Z | A | Source StorageBox confirmée intacte par streaming SHA-256 sans nouvelle copie locale : les 6 checksums de `20260620_133001` correspondent au journal Étape 1 | `proofs/assainissement_step2_20260620T131006Z/storagebox_checksum_confirm_20260620T131006Z.txt` |
| 2026-06-20T13:39Z | A | Scratch distant non chiffré `/tmp/korrigo-restore-step1-20260620t115755z` effacé par `shred -u -n 1 -z` puis `rm -rf`; `df /` avant `740G used / 143G free / 84%`, après `726G used / 156G free / 83%`; conteneurs/réseaux restore `0` | `proofs/assainissement_step2_20260620T131006Z/scratch_cleanup_20260620T131006Z.txt` |
| 2026-06-20T13:40Z | A | Nettoyage confidentialité local : ancien dossier non suivi `proofs/RC_2026-02-20` supprimé (`312` fichiers, dont `209` PDF et `36` JSON, `723M`) ; preuves conservées expurgées | `proofs/assainissement_step2_20260620T131006Z/local_pii_artifacts_cleanup_20260620T131006Z.txt` |
| 2026-06-20T13:40Z | A | Sweep PII : preuves conservées `email_count=0`, `pdf_count=0`, `dump_count=0`; `/var/log/korrigo_backup.log` `email_count=0`; scratch Étape 1 absent | `proofs/assainissement_step2_20260620T131006Z/pii_sweep_20260620T131006Z.txt` |
| 2026-06-20T13:43Z | B | Worktree sale sauvegardé sans perte sur `wip/worktree-20260620`, commit snapshot `41765243f558b5466d71edfe25c6117acc16717f`; classification ajoutée commit `67091ab8b041d43610c6b227de5f6c00e109bd35` | `docs/technical/WORKTREE_CLASSIFICATION_2026-06-20.md` |
| 2026-06-20T14:45Z | C | Migrations `exams 0039-0042` localisées; `0039-0041` appliquées DB mais absentes image; `0042` non appliquée; décision `0042` réelle/idempotente + `0043` de contrainte live | `docs/technical/MIGRATIONS_EXAMS_0039_0042_DECISION_2026-06-20.md` |
| 2026-06-20T15:19Z | 2 | Clone technique StorageBox restauré sans données métier (schéma + `django_migrations`), migré par image réconciliée; base vide migrée; diff schéma normalisé vide (`SCHEMA_DIFF=EMPTY`) | `proofs/assainissement_step2_20260620T131006Z/final_image_schema_parity_korrigo-reconcile-20260620-0ae7e48.txt` |
| 2026-06-20T15:23Z | 2 | Images candidates finales construites localement avec labels OCI vers commit `0ae7e48b8a57f360d39d400a0f499a074f3f3587`; backend `sha256:b5d5c2dda686...`, nginx `sha256:3ef0898b4936...` | `proofs/assainissement_step2_20260620T131006Z/candidate_layered_build_retry_korrigo-reconcile-20260620-0ae7e48.txt` |
| 2026-06-20T15:26Z | 2 | Staging sans overlay : `overlay_mount_count=0`, health nginx `/api/health/` `{"status":"healthy","database":"connected"}`, Celery ping `OK`, tâches requises enregistrées | `proofs/assainissement_step2_20260620T131006Z/final_staging_health_celery_no_overlay_korrigo-reconcile-20260620-0ae7e48.txt` ; `proofs/assainissement_step2_20260620T131006Z/final_overlay_mount_count_korrigo-reconcile-20260620-0ae7e48.txt` |
| 2026-06-20T15:27Z | 2 | Tests image finale sans montage source : `63 passed, 1 skipped`; `manage.py check` et `makemigrations --check` OK; parcours admin/correcteur/élève/direction couverts par tests ciblés | `proofs/assainissement_step2_20260620T131006Z/final_image_targeted_tests_korrigo-reconcile-20260620-0ae7e48.txt` |
| 2026-06-20T15:27Z | 2 | Tâches Celery exécutées en smoke non destructif : finalisation/import/document-set retournent erreurs contrôlées sur IDs inexistants; imports orchestrateurs bilan OK; `scheduled_backup` non exécutée pour éviter dump | `proofs/assainissement_step2_20260620T131006Z/final_celery_task_execution_korrigo-reconcile-20260620-0ae7e48.txt` |
| 2026-06-20T15:34Z | 2 | Images publiées GHCR sous tag Git `korrigo-reconcile-20260620-0ae7e48`: backend digest `sha256:ddc001873087119e8cbd5a9f65641953617b3a49083916ddf0bd63ced3621531`; nginx digest `sha256:3dbd207cbe68610e4425faed9718b3c8cc8187ba7b8aac8e48f4dcfb659393ea` | `proofs/assainissement_step2_20260620T131006Z/publish_ghcr_korrigo-reconcile-20260620-0ae7e48.txt` |
| 2026-06-20T17:20Z | 2 | Image `0ae7e48` déclarée caduque : comparaison exhaustive `django_migrations` vs fichiers image a trouvé deux migrations `grading` appliquées sans fichier (`0013_alter_annotation_type`, `0020_alter_annotation_type`). Correctif source commit `7306c5afa1987b2edd6aa416f8284ea633fe988f` | `docs/technical/STEP2_RELEASE_RECONCILE_CLOSURE_2026-06-20.md` ; `proofs/assainissement_step2_20260620T131006Z/clean_migration_history_parity_korrigo-reconcile-20260620-7306c5a.txt` |
| 2026-06-20T17:22Z | 2 | Build Dockerfile complet propre backend prod + backend test séparé + nginx, sans approche `FROM ... + COPY`; labels OCI vers commit `7306c5afa1987b2edd6aa416f8284ea633fe988f`; backend prod local `sha256:65f42be93e18...`, nginx local `sha256:822bf4c519c...` | `proofs/assainissement_step2_20260620T131006Z/full_clean_build_korrigo-reconcile-20260620-7306c5a.log` |
| 2026-06-20T17:23Z | 2 | Image prod propre sans dépendances dev : `pytest_spec None`, `pip show pytest` absent; image test non publiée utilisée pour tests | `proofs/assainissement_step2_20260620T131006Z/clean_prod_no_dev_deps_korrigo-reconcile-20260620-7306c5a.txt` |
| 2026-06-20T17:23Z | 2 | Tests backend ciblés dans image test du même commit : `manage.py check` OK, `makemigrations --check` OK, `63 passed, 1 skipped` | `proofs/assainissement_step2_20260620T131006Z/clean_test_image_backend_tests_korrigo-reconcile-20260620-7306c5a.txt` |
| 2026-06-20T17:23Z | 2 | Tests unitaires frontend `vitest` : `21 passed`, `197 passed`, incluant `AdminPasswordReset.test.ts`; parcours UI complet reporté à la recette | `proofs/assainissement_step2_20260620T131006Z/frontend_vitest_korrigo-reconcile-20260620-7306c5a.txt` |
| 2026-06-20T17:23Z | 2 | Parité historique migrations sur toutes les apps : `APPLIED_WITHOUT_FILE_COUNT=0`; seuls fichiers en attente avant réconciliation = `exams.0042`, `exams.0043`, `grading.0028` | `proofs/assainissement_step2_20260620T131006Z/clean_migration_history_parity_korrigo-reconcile-20260620-7306c5a.txt` |
| 2026-06-20T17:24Z | 2 | Parité schéma : clone technique StorageBox migré + base vide migrée depuis zéro; aucun plan en attente; hashes identiques; `SCHEMA_DIFF=EMPTY` | `proofs/assainissement_step2_20260620T131006Z/clean_schema_parity_korrigo-reconcile-20260620-7306c5a.txt` |
| 2026-06-20T17:25Z | 2 | Staging jetable sans overlay : image finale `7306c5a` sur backend/celery/celery-beat/nginx; `bind_mount_count=0`, `overlay_mount_count=0`, health `{\"status\":\"healthy\",\"database\":\"connected\"}`, tâches Celery enregistrées | `proofs/assainissement_step2_20260620T131006Z/clean_staging_health_celery_no_overlay_korrigo-reconcile-20260620-7306c5a.txt` |
| 2026-06-20T17:26Z | 2 | Tâches Celery non destructives exécutées via worker final : finalisation PDF, import PDF, document-set retournent erreurs contrôlées sur IDs inexistants; imports `EamBilanOrchestrator`, `BilanOrchestratorEAM`, `RAGRetrieverPremiere` OK | `proofs/assainissement_step2_20260620T131006Z/clean_celery_task_execution_korrigo-reconcile-20260620-7306c5a.txt` |
| 2026-06-20T17:30Z | 2 | Images prod propres publiées GHCR sous tag Git `korrigo-reconcile-20260620-7306c5a`; backend digest `sha256:a6b750e56dd976153d62bec16128ebf4d8a1efc6a68fb24fc86c11d46b5657c8`; nginx digest `sha256:09401293f50173ce8483df7ea7897ba880e6d3b79450955f9eb70c0fd8ebf7fd`; image test dev non publiée | `proofs/assainissement_step2_20260620T131006Z/publish_ghcr_clean_korrigo-reconcile-20260620-7306c5a.txt` |
| 2026-06-20T17:32Z | I | Sweep confidentialité final : preuves conservées `proof_data_artifact_count=0`, `proof_email_file_count=0`; image dev non publiée; `seed_e2e.py` exclu du contexte Docker volontairement (script dev, non runtime) | `proofs/assainissement_step2_20260620T131006Z/final_pii_sweep_clean_korrigo-reconcile-20260620-7306c5a.txt` |
| 2026-06-20T17:33Z | 2 | Pile staging jetable démontée : `korrigo-reconcile-p2` containers/volumes/networks restants `0`; aucun prune image/volume effectué | `proofs/assainissement_step2_20260620T131006Z/teardown_staging_clean_korrigo-reconcile-20260620-7306c5a.txt` |
| 2026-06-20T17:51Z | 2/3 | Validation humaine Porte 2 accordée ; Porte 2 cochée. Critères de sortie enrichis avant Étape 3 : recette UI/UX par profil, audit cohérence FE/BE/DB/nginx/routage, cibles code mort connues, sweep hardcoding, CI migrations PostgreSQL/overlay/OCI/KORRIGO_SHA/restore | `ASSAINISSEMENT_KORRIGO.md` |
| 2026-06-20T18:43Z | 3 | Build final Étape 3 depuis Dockerfiles committés ; image backend prod sans pytest ; client PostgreSQL 15 et GPG présents ; labels OCI vers `e81958e66c15c665185418ad372362d9ae4eddc1` | `proofs/20260620_step3/build_step3_e81958e.log` ; `proofs/20260620_step3/backend_runtime_versions_e81958e.txt` ; `proofs/20260620_step3/image_inspect_labels_e81958e.txt` |
| 2026-06-20T18:44Z | 3 | Images GHCR finales publiées sous tag Git `korrigo-step3-20260620-e81958e` : backend digest `sha256:1abd594998f7109a93f46b059f1d2657e517d8945f57e0bd12f664d5cae51f10`, nginx digest `sha256:63cd6627cd1a45d1b44d9bd4c7c4db77f6e07dee4400d6c2fcc8f631d9fff451` | `proofs/20260620_step3/push_backend_e81958e.log` ; `proofs/20260620_step3/push_nginx_e81958e.log` |
| 2026-06-20T18:44Z | 3 | Tests backend complets dans image test du même commit : `980 passed, 1 skipped, 3 deselected`; vitest frontend : `334 passed` | `proofs/20260620_step3/backend_full_pytest_e81958e.txt` ; `proofs/20260620_step3/frontend_vitest_e81958e.txt` |
| 2026-06-20T18:45Z | 3 | Staging jetable `korrigo_step3` démarrée avec compose unifié, images par digest, Redis auth, `DJANGO_AUTO_MIGRATE=false`, zéro overlay, health `{"status":"healthy","database":"connected"}` | `proofs/20260620_step3/staging_compose_gpg_final_redacted.txt` ; `proofs/20260620_step3/staging_gpg_ps.txt` ; `proofs/20260620_step3/staging_gpg_health.json` ; `proofs/20260620_step3/staging_final_mounts.txt` |
| 2026-06-20T18:46Z | 3 | Backup GPG runtime prouvé : `scheduled_backup` produit seulement `.dump.gpg`; SHA-256 `dab4b32a5ee7bc24e3d633fb3fb94b5c749eb076b57fa2ab747763d9451930a7`; déchiffrement et restore DB jetable `RESTORE_PROBE_OK`, `django_migrations=113`, `exams_copy=3` | `proofs/20260620_step3/staging_gpg_backup_task_result.txt` ; `proofs/20260620_step3/staging_gpg_backup_restore_probe.txt` |
| 2026-06-20T18:46Z | 3 | Parcours HTTP staging via nginx : admin, correcteur, élève, direction `200`; upload PDF `201`; médias directs bloqués (`/media` `404`), médias protégés et PDF final `200` avec headers iframe/CSP ; 35 logins élèves depuis IP partagée sans `429` | `proofs/20260620_step3/http_runtime_checks_redacted.txt` ; `proofs/20260620_step3/staging_upload_pdf_probe_redacted.txt` |
| 2026-06-20T18:46Z | 3 | Celery final : worker avec `DJANGO_SETTINGS_MODULE=core.settings_prod`, Redis/GPG env présents, code réconcilié (`analytics_has_graded=False`), tâche broker `update_copy_status_metrics` exécutée avec résultat | `proofs/20260620_step3/staging_final_celery_env_redacted.txt` ; `proofs/20260620_step3/staging_final_celery_reconciled_code.txt` ; `proofs/20260620_step3/staging_celery_task_probe.txt` |
| 2026-06-20T18:47Z | 3 | Sweep confidentialité preuves Étape 3 : aucun email, secret Redis/GPG/Postgres/metrics/secret key non expurgé détecté ; aucun dump/media téléchargé dans le dépôt ; preuves sous `proofs/` ignorées par Git | `proofs/20260620_step3/` ; `.gitignore` |
| 2026-06-20T18:49Z | 3 | Pile staging jetable démontée : conteneurs/volumes/réseaux `korrigo_step3_*` restants `0`; aucun prune image/volume effectué | `proofs/20260620_step3/staging_final_teardown.txt` |
| 2026-06-20T18:58Z | 3 | Celery finalisation PDF complète via broker sur pile jetable et image prod propre : `async_finalize_copy` retourne `status=success`, copie `FINALIZED`, score `18.0`, PDF final généré (`53672` octets) | `proofs/20260620_step3/staging_async_finalize_copy_probe.txt` |
| 2026-06-20T18:59Z | 3 | Sweep final après remontée jetable : conteneurs/volumes/réseaux `korrigo_step3_*` restants `0`; scan PII/secrets des preuves Étape 3 sans résultat; prod non touchée; aucun prune effectué | `proofs/20260620_step3/final_hygiene_sweep.txt` |
| 2026-06-20T19:46Z | J/K/L | Correctifs runtime finaux sur `release/prod-unification` : entrypoint fail-fast, redaction échec notification Celery, préparation `/app/backups` pour Celery, suppression alias `n_copies_graded`, `DEFAULT_PASSWORD` hors runtime | commits `afa9323410534b6e20b5479d4adc125f9589f54b`, `ead834eb790dd651d1d1be9d71d26992a61c8171` |
| 2026-06-20T19:47Z | J/K/L | Build complet depuis Dockerfiles committés au tag Git `korrigo-step3-20260620-ead834e`; labels OCI vers `ead834eb790dd651d1d1be9d71d26992a61c8171`; image prod sans `pytest`, clients `pg_dump/pg_restore` 15 et GPG présents | `proofs/20260620_step3_jkl/build_korrigo-step3-20260620-ead834e.log`; `proofs/20260620_step3_jkl/image_runtime_labels_korrigo-step3-20260620-ead834e.txt` |
| 2026-06-20T19:48Z | J/K/L | Images GHCR finales publiées : backend `sha256:332866d285ce4d831a5e605aa7793cba003efc7a96b81059ef5ca5d480bb09d7`, nginx `sha256:81bce3acc1388bbb4e4208b88c6ab921aea9f123186b9adff46da7149bb36616`; tag Git poussé | `proofs/20260620_step3_jkl/push_backend_korrigo-step3-20260620-ead834e.log`; `proofs/20260620_step3_jkl/push_nginx_korrigo-step3-20260620-ead834e.log` |
| 2026-06-20T19:48Z | J/K/L | Tests finaux : backend complet `989 passed, 1 skipped, 3 deselected`; frontend `vitest` `334 passed` | `proofs/20260620_step3_jkl/backend_full_pytest_korrigo-step3-20260620-ead834e.txt`; `proofs/20260620_step3_jkl/frontend_vitest_korrigo-step3-20260620-ead834e.txt` |
| 2026-06-20T19:49Z | J | Staging final `ead834e` : base vide refusée explicitement (`EMPTY_DB_ENTRYPOINT_RC=1`), migration one-shot `OK`, health `{"status":"healthy","database":"connected"}`, `bind_mount_count=0`, `overlay_mount_count=0`, `DEFAULT_PASSWORD` absent, Redis `NOAUTH` sans mot de passe | `proofs/20260620_step3_jkl/staging_final_core_ead834e.txt` |
| 2026-06-20T19:49Z | K | Backup GPG final via Celery : `/app/backups` writable par `korrigo`, `scheduled_backup` produit uniquement `.dump.gpg` (`26036` octets sur DB staging), logs sans secret | `proofs/20260620_step3_jkl/staging_final_core_ead834e.txt` |
| 2026-06-20T19:50Z | J/L | Rate-limit final : 10 échecs par identifiant non limités, 11e `429`; 10 identifiants distincts depuis IP partagée sans `429`; Celery `async_finalize_copy` finalise une copie avec PDF (`48554` octets); `analytics_has_n_copies_graded=False`, redaction notification active | `proofs/20260620_step3_jkl/staging_final_app_flows_ead834e.txt` |
| 2026-06-20T19:51Z | K | Sweep confidentialité final : logs backend/celery/entrypoint/nginx `email_count=0`, `secret_count=0`, `probe_identifier_count=0`; preuves conservées `proof_email_file_count=0`, `proof_secret_file_count=0`; aucun dump/media dans le dépôt | `proofs/20260620_step3_jkl/final_pii_logs_sweep_ead834e.txt` |
| 2026-06-20T19:51Z | 3 | Pile staging jetable `korrigo_step3_jkl` démontée : conteneurs/volumes/réseaux restants `0`; aucun prune image/volume effectué ; prod active non touchée | `proofs/20260620_step3_jkl/final_staging_teardown_ead834e.txt` |
| 2026-06-20T20:04Z | N | Angles morts verrouillés sur `1958681b082402e06d0f463e685d8a9895c460c5` : Redis `allkeys-lru` accepté avec alerte mémoire Étape 8 ; nginx login conservé comme garde-fou anti-flood haut ; `_TRIVIAL_PASSWORDS` documenté comme garde-fou one-shot import/seed | `infra/nginx/nginx.conf`; `backend/core/settings_prod.py`; `backend/core/tests/test_nginx_contract.py` |
| 2026-06-20T20:05Z | N | Build complet final `korrigo-step3-20260620-1958681`; images GHCR publiées : backend `sha256:aafe75e7e4bc475f066ed57cc4b16dc816ea3497c70f3e8e954c5ba496929e1e`, nginx `sha256:5c4dda163f3ce4a4ff7e4a2b321adafb398cc3cdaa4461d708de89dabae0f61a`; image prod sans `pytest` | `proofs/20260620_step3_n/build_korrigo-step3-20260620-1958681.log`; `proofs/20260620_step3_n/push_backend_korrigo-step3-20260620-1958681.log`; `proofs/20260620_step3_n/push_nginx_korrigo-step3-20260620-1958681.log`; `proofs/20260620_step3_n/image_runtime_labels_korrigo-step3-20260620-1958681.txt` |
| 2026-06-20T20:05Z | N | Tests finaux après N : backend complet `990 passed, 1 skipped, 3 deselected`; frontend `vitest` `334 passed` | `proofs/20260620_step3_n/backend_full_pytest_korrigo-step3-20260620-1958681.txt`; `proofs/20260620_step3_n/frontend_vitest_korrigo-step3-20260620-1958681.txt` |
| 2026-06-20T20:06Z | N | Staging final combiné : health OK ; Redis `maxmemory-policy=allkeys-lru`, `maxmemory=268435456`, `evicted_keys=0`; 60 identifiants distincts depuis même IP → `401` sans `429/503`; même identifiant → 11e `429` | `proofs/20260620_step3_n/staging_n_rate_limit_combined_1958681.txt` |
| 2026-06-20T20:07Z | N | Sweep final N : preuves `proof_email_file_count=0`, `proof_secret_file_count=0`; pile `korrigo_step3_n` démontée, conteneurs/volumes/réseaux restants `0`; aucun prune ; prod non touchée | `proofs/20260620_step3_n/final_pii_sweep_1958681.txt`; `proofs/20260620_step3_n/final_staging_teardown_1958681.txt` |
| 2026-06-20T20:21Z | O.6 | Inventaire prod lecture seule : projet Compose `docker`, chemin `/var/www/labomaths/korrigo`, DB `docker-db-1`, media `docker_media_volume` (`8528` fichiers, `14G`), PostgreSQL `korrigo_user/korrigo_db`, StorageBox confirmé, disque `170G` libre ; `.env` constaté `664` donc correction `600` exigée dans runbook | `proofs/20260620_step3_o/prod_readonly_inventory_20260620T201959Z.txt` |
| 2026-06-20T20:28Z | O.1/O.2/O.3 | Preuve staging jetable : plan pré-bascule strictement limité à `exams.0042`, `exams.0043`, `grading.0028` (`unexpected_line_count=0`) ; entrypoint service refuse la base non à jour (`rc=1`) ; one-shot `--entrypoint python` applique les migrations ; rollback par DB recréée supprime les lignes postérieures et le défaut DB, ancienne contrainte restaurée | `proofs/20260620_step3_o/rollback_recreated_db_and_entrypoint_1958681.txt` |
| 2026-06-20T20:30Z | O | Runbook M v2 corrigé : gel applicatif avant dump, backup complet chiffré avec média résolu par `docker volume inspect`, plan de migration vérifié avant application, migrations one-shot sans entrypoint, rollback schéma-conscient par `DROP DATABASE`/`CREATE DATABASE`, aucune action prod en écriture réalisée | `ASSAINISSEMENT_KORRIGO.md` |
| 2026-06-20T20:39Z | P.1/P.2 | Compose prod lecture seule : services racine et infra identiques en noms donc pas de `--remove-orphans`; DB actuelle et cible partagent image/port/volume mais healthcheck diffère, donc runbook protège DB par ID et évite tout `up` DB ; Redis actuel sans AUTH, cible avec `--requirepass`, donc recréation Redis explicite et isolée requise | `proofs/20260620_step3_p/prod_compose_reprise_readonly_20260620T203848Z.txt` |
| 2026-06-20T20:40Z | P.3/P.4 | Preuve locale : archive média `.tar.gz.gpg` déchiffrable/listable sans extraction (`media_file_count=2`, `tar_list_file_count=2`) ; nettoyage `/tmp/korrigo_extract` dans conteneur backend laisse `after=0` JSON | `proofs/20260620_step3_p/media_integrity_and_json_cleanup_1958681.txt` |
| 2026-06-20T20:42Z | P.5 | Runbook M v3 : contrôle post-rollback exige défaut `pdf_regeneration_pending` absent (`<NULL>`) et contrainte `check_copy_status_valid` contenant `LOCKED` et `GRADED`; aucune écriture prod réalisée | `ASSAINISSEMENT_KORRIGO.md` |
