# LOT 11 — Sortie du Pattern Overlay

## Contexte

Le déploiement actuel utilise un **pattern overlay** : 59 fichiers backend sont montés individuellement via des volumes Docker depuis `/var/www/labomaths/korrigo/overlay/` vers le conteneur. Cela contourne le `COPY . .` du Dockerfile et permet des hotfixes rapides sans rebuild d'image.

**Problèmes du pattern overlay** :
- 59 lignes de volume mounts dans `docker-compose.prod.yml` (backend + celery)
- Risque de divergence entre repo et serveur (détecté le 20/02/2026 : 42 fichiers différents)
- Pas de versionning des fichiers déployés (pas de tag Docker)
- Impossible de rollback proprement
- Les fichiers overlay ne sont pas dans le build cache Docker

## Plan de Migration

### Phase 1 : Vérification pré-migration

```bash
# 1. Vérifier que TOUS les fichiers overlay sont identiques au repo local
ssh root@88.99.254.59 'find /var/www/labomaths/korrigo/overlay/ -type f -name "*.py"' | sort > /tmp/server_files.txt
# Comparer avec le repo local (md5sum)

# 2. Backup complet
ssh root@88.99.254.59 'cd /var/www/labomaths/korrigo && ./scripts/korrigo_backup.sh'

# 3. Snapshot Docker volumes
ssh root@88.99.254.59 'docker volume ls'
```

### Phase 2 : Rebuild de l'image Docker

```bash
# Sur la machine locale
cd /home/alaeddine/Bureau/viatique__PMF

# 1. Tag le commit actuel
git tag -a v1.0-post-audit -m "Post data-integrity audit (LOT 1-11)"
git push origin v1.0-post-audit

# 2. Build l'image backend
docker build -t korrigo-backend:v1.0 ./backend

# 3. Build l'image frontend (si nécessaire)
cd frontend && npx vite build
# SCP dist/ vers serveur + docker cp vers nginx container

# 4. Push l'image vers le registry (ou save/load)
docker save korrigo-backend:v1.0 | gzip > korrigo-backend-v1.0.tar.gz
scp korrigo-backend-v1.0.tar.gz root@88.99.254.59:/var/www/labomaths/korrigo/
```

### Phase 3 : Nouveau docker-compose.prod.yml

Remplacer les 59 overlay mounts par un simple `build:` ou `image:` :

```yaml
services:
  web:
    image: korrigo-backend:v1.0
    # OU build: ./backend
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    volumes:
      # Seulement les volumes de données persistantes
      - media_data:/app/media
      - logs_data:/app/logs
    # ... (env, ports, etc.)

  celery:
    image: korrigo-backend:v1.0
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - media_data:/app/media
      - logs_data:/app/logs
    command: celery -A core worker -l info

  celery-beat:
    image: korrigo-backend:v1.0
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    command: celery -A core beat -l info
```

### Phase 4 : Déploiement

```bash
# Sur le serveur
cd /var/www/labomaths/korrigo

# 1. Charger la nouvelle image
docker load < korrigo-backend-v1.0.tar.gz

# 2. Arrêter les services
docker compose -f docker-compose.prod.yml down

# 3. Remplacer docker-compose.prod.yml (sans overlays)
cp docker-compose.prod.yml docker-compose.prod.yml.overlay-backup
# Déployer le nouveau fichier

# 4. Relancer
docker compose -f docker-compose.prod.yml up -d

# 5. Générer la migration LOT 8 (contraintes DB)
docker compose exec web python manage.py makemigrations grading exams --name lot8_constraints_indexes
docker compose exec web python manage.py migrate

# 6. Vérification
docker compose exec web python manage.py check --deploy
curl -s https://korrigo.labomaths.tn/api/health/ | jq .
```

### Phase 5 : Cleanup

```bash
# Supprimer l'ancien overlay
rm -rf /var/www/labomaths/korrigo/overlay/

# Supprimer le backup docker-compose
# (garder 7 jours pour rollback)
```

## Checklist de Validation Post-Migration

- [ ] `GET /api/health/` → 200
- [ ] `GET /api/copies/` → 209 copies (admin)
- [ ] `GET /api/exams/stats-report/` → données complètes
- [ ] Login correcteur → voit ses copies assignées
- [ ] Login élève → voit son bulletin
- [ ] Celery Beat actif (vérifier `cleanup_expired_locks` et `purge_old_audit_logs`)
- [ ] Vérifier les fichiers media accessibles via `ProtectedMediaView`
- [ ] Vérifier 0 erreur dans `docker compose logs web --tail=50`

## Rollback

En cas de problème :
```bash
# Restaurer l'ancien docker-compose avec overlays
cp docker-compose.prod.yml.overlay-backup docker-compose.prod.yml
docker compose -f docker-compose.prod.yml up -d
```

## Migrations DB à Appliquer

Les LOTs 1-11 ont introduit des changements de modèle nécessitant des migrations :

| Migration | Description | Risque |
|---|---|---|
| `grading.lot8_constraints_indexes` | `UniqueConstraint` sur `Score.copy` | **Vérifier absence de doublons avant** : `SELECT copy_id, COUNT(*) FROM grading_score GROUP BY copy_id HAVING COUNT(*) > 1` |
| `exams.lot8_constraints_indexes` | 3 index sur `Copy` (status, exam+status, corrector+status) | Faible (ajout d'index) |

**Important** : Toujours exécuter les requêtes de vérification de doublons AVANT `migrate`.
