# Guide de Déploiement Production — Korrigo v2

> **Version** : 3.0
> **Date** : 2026-03-28
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
ALLOWED_HOSTS=korrigo.labomaths.tn,korrigo.nexusreussite.academy

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
curl http://localhost:8000/api/health/
# → {"status": "ok", "db": "ok", "redis": "ok"}

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

### Base de données
```bash
ssh root@88.99.254.59 "
docker exec docker-db-1 pg_dump -U korrigo korrigo \
  > /tmp/korrigo_$(date +%Y%m%d_%H%M).sql
"
# Rapatrier localement
scp root@88.99.254.59:/tmp/korrigo_*.sql ./backups/
```

### Fichiers media (copies, PDFs)
```bash
rsync -av --progress \
  root@88.99.254.59:/var/www/labomaths/korrigo/backend/media/ \
  ./backups/media_$(date +%Y%m%d)/
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

### Copy bloquée (`finalizing_at` non-null)
```bash
docker exec docker-backend-1 python manage.py recover_stuck_copies
# OU
docker exec docker-backend-1 python manage.py shell -c "
from exams.models import Copy
n = Copy.objects.filter(finalizing_at__isnull=False).update(finalizing_at=None)
print(f'{n} copies libérées')
"
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
