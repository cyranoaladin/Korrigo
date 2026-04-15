# Guide de Déploiement Production — Korrigo v2

> **Version** : 3.1
> **Date** : 2026-04-03
> **Public** : DevOps, Administrateurs Système
> **Serveur** : 88.99.254.59 — korrigo.labomaths.tn

---

## Architecture de production

```
Internet ──HTTPS──→ Nginx (443/80)
                        │
              ┌─────────┼─────────────┐
              │         │             │
         /static/    /api/       /media/
                        │
                 Gunicorn :8000
                 (docker-backend-1)
                        │
         ┌──────────────┼──────────────┐
         │              │              │
    PostgreSQL 15    Redis 7      Celery Workers
    (docker-db-1)  (docker-redis-1) (docker-celery-1)
                                       │
                              Celery Beat (scheduler)
                              (docker-celery-beat-1)
```

---

## Accès au serveur

```bash
ssh root@88.99.254.59
```

Chemin de déploiement : `/var/www/labomaths/korrigo/`

---

## Fichier d'environnement

**Localisation** : `/var/www/labomaths/korrigo/infra/docker/.env`

```env
# Django
DJANGO_SETTINGS_MODULE=core.settings_prod
SECRET_KEY=<clé 50+ chars — PAS django-insecure->
DEBUG=False
ALLOWED_HOSTS=korrigo.labomaths.tn,korrigo.nexusreussite.academy  # alias DNS Korrigo, pas une autre application

# Base de données
DB_NAME=korrigo
DB_USER=korrigo
DB_PASSWORD=<mot de passe fort>
DB_HOST=db
DB_PORT=5432

# Redis / Celery
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# OCR (GPT-4o-mini)
OPENAI_API_KEY=sk-...

# LLM bilans
OLLAMA_URL=http://ollama:11434

# Sécurité web
CORS_ALLOWED_ORIGINS=https://korrigo.labomaths.tn
CSRF_TRUSTED_ORIGINS=https://korrigo.labomaths.tn
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True

# Métriques Prometheus
METRICS_TOKEN=<token aléatoire>

# Image Docker
KORRIGO_SHA=<hash du dernier build>
```

> ⚠️ `SECRET_KEY` ne doit **jamais** commencer par `django-insecure-` (rejeté par `settings_prod.py`).
> Générer : `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`

---

## Conteneurs (état actuel)

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

| Conteneur | Rôle | Port exposé |
|-----------|------|-------------|
| docker-nginx-1 | Reverse proxy + TLS | 80, 443 |
| docker-backend-1 | Django + Gunicorn | 8000 (interne) |
| docker-db-1 | PostgreSQL 15 | 5432 (interne) |
| docker-redis-1 | Redis 7 | 6379 (interne) |
| docker-celery-1 | Celery Worker | — |
| docker-celery-beat-1 | Celery Beat | — |

---

## Procédure de déploiement standard

### 1. Pousser le code (depuis la machine dev)
```bash
git push origin main
```

### 2. Sur le serveur — Pull + migrations
```bash
ssh root@88.99.254.59
cd /var/www/labomaths/korrigo
git pull origin main

# Appliquer les nouvelles migrations
docker exec docker-backend-1 python manage.py migrate

# Vérifier
docker exec docker-backend-1 python manage.py showmigrations | grep '\[ \]'
```

### 3. Redémarrer les services backend
```bash
docker restart docker-backend-1 docker-celery-1 docker-celery-beat-1
```

### 4. Vérifier la santé
```bash
curl -fsS https://korrigo.labomaths.tn/api/health/
# → {"status":"healthy","database":"connected"}

docker ps  # Tous les conteneurs doivent être Up
```

---

## Déploiement frontend uniquement

```bash
# Sur la machine dev
cd frontend
npm run build
# Output dans dist/

# Synchroniser vers le serveur
rsync -av --progress dist/ root@88.99.254.59:/var/www/labomaths/korrigo/frontend/dist/

# Nginx relit les fichiers statiques (pas de restart nécessaire)
# Si config Nginx changée :
ssh root@88.99.254.59 "docker restart docker-nginx-1"
```

---

## Upload de copies volumineux (exemple : 1.3 GB DNB)

```bash
# 1. Rsync des fichiers vers le serveur
rsync -av --progress scan_DNB_maths/Copies_DNB_BLANC_2026/ \
  root@88.99.254.59:/tmp/copies_dnb/

# 2. Copier dans le conteneur
ssh root@88.99.254.59 \
  "docker cp /tmp/copies_dnb docker-backend-1:/app/scan_DNB_maths/Copies_DNB_BLANC_2026"

# 3. Import
ssh root@88.99.254.59 \
  "docker exec docker-backend-1 python manage.py import_dnb_copies"

# 4. Nettoyer le /tmp
ssh root@88.99.254.59 "rm -rf /tmp/copies_dnb"
```

---

## Sauvegarde

### Système automatisé actuel

Le backup de production est orchestré par [`scripts/korrigo_backup.sh`](/home/alaeddine/Bureau/KORRIGO/korrigo_v2_improved/scripts/korrigo_backup.sh) avec ce flux :
- toutes les 30 minutes
- dump PostgreSQL complet
- export JSON des corrections
- archive du volume Docker `media_volume`
- envoi vers Hetzner StorageBox `u554481.your-storagebox.de:23`
- stockage distant sous `backups/korrigo_backups/<timestamp>/`
- rétention distante de 24 heures
- suppression locale après synchronisation
- conservation locale d’au plus 2 dossiers `fallback_*` en cas d’échec réseau

### Contrôles opérationnels

```bash
tail -50 /var/log/korrigo_backup.log
crontab -l | grep korrigo_backup
ssh -i /root/.ssh/storagebox_ed25519 -p 23 u554481@u554481.your-storagebox.de \
  "ls backups/korrigo_backups/ | tail -5"
```

---

## Monitoring

### Logs en temps réel
```bash
# Backend (Django)
docker logs docker-backend-1 --tail 100 -f

# Celery worker
docker logs docker-celery-1 --tail 50

# Nginx
docker logs docker-nginx-1 --tail 50
```

### Métriques Prometheus
```bash
curl -H "Authorization: Bearer $METRICS_TOKEN" \
  https://korrigo.labomaths.tn/metrics
```

### Connexions DB actives
```bash
docker exec docker-db-1 psql -U korrigo -c \
  "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"
```

---

## Dépannage courant

### 502 Bad Gateway
```bash
# Backend down
docker logs docker-backend-1 --tail 20
docker restart docker-backend-1
```

### `SECRET_KEY looks like a placeholder` (celery-beat crash)
```bash
# Vérifier .env
grep SECRET_KEY /var/www/labomaths/korrigo/infra/docker/.env
# Si django-insecure- → régénérer
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
# Mettre à jour .env puis :
docker restart docker-celery-beat-1
```

### Migrations échouées
```bash
docker exec docker-backend-1 python manage.py showmigrations
docker exec docker-backend-1 python manage.py migrate --run-syncdb
# Si conflit : identifier la migration bloquante
docker exec docker-backend-1 python manage.py migrate --fake exams 0027
```

### Copie abandonnée `IN_PROGRESS`
```bash
docker exec docker-backend-1 python manage.py recover_stuck_copies
```

### Celery queue bloquée
```bash
# Vider la queue (DANGER : perd les tâches en attente)
docker exec docker-redis-1 redis-cli FLUSHDB
docker restart docker-celery-1
```

### Restaurer un backup DB
```bash
docker exec -i docker-db-1 psql -U korrigo korrigo < backup_20260328.sql
```

---

## Release Gate CI

Le workflow `.github/workflows/release-gate.yml` valide chaque déploiement avec une tolérance zéro :

| Check | Critère |
|-------|---------|
| pytest | 0 failed, 0 skipped |
| E2E | 3/3 runs passed, annotations POST 201 |
| Seed | All READY copies have pages > 0 |

Un échec bloque le merge. Vérifier les logs de la CI avant tout déploiement manuel.
