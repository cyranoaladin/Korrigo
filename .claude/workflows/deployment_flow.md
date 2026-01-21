# Workflow: Déploiement Production

## Vue d'Ensemble

Workflow de déploiement sécurisé en production.

---

## Workflow Déploiement

```
1. Pre-Deployment Checks
   ├─ Tests passent (CI/CD)
   ├─ Security audit
   ├─ Migrations testées staging
   └─ Backup DB/media
   ↓
2. Configuration Production
   ├─ Variables environnement
   ├─ Secrets sécurisés
   └─ SSL/HTTPS configuré
   ↓
3. Build Images Docker
   ↓
4. Database Migrations
   ↓
5. Collectstatic
   ↓
6. Deploy Services (Rolling Restart)
   ↓
7. Health Checks
   ↓
8. Monitoring Actif
   ↓
9. Rollback si Erreur
```

---

## 1. Pre-Deployment Checklist

```bash
# Tests
./run_tests.sh  # Tous les tests passent

# Security Scan
bandit -r backend/
safety check

# Staging validation
# Tester migrations en staging
docker-compose -f docker-compose.staging.yml run backend python manage.py migrate

# Backup
./backup_production.sh
```

**Checklist** :
- [ ] Tous les tests passent
- [ ] Scan sécurité sans vulnérabilité critique
- [ ] Migrations testées en staging
- [ ] Backup DB récent (<24h)
- [ ] Backup media récent (<24h)
- [ ] Équipe notifiée

---

## 2. Configuration Production

**Variables Environnement** :
```bash
# .env.production
DEBUG=False
SECRET_KEY=<generated-50-chars-minimum>
DATABASE_URL=postgresql://user:password@db:5432/viatique_prod
ALLOWED_HOSTS=viatique.example.com,www.viatique.example.com
CSRF_TRUSTED_ORIGINS=https://viatique.example.com

# SSL
SSL_ENABLED=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Email (if applicable)
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@viatique.example.com
EMAIL_HOST_PASSWORD=<email-password>

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
```

**Validation** :
```python
# settings.py - Validation obligatoire
if not os.environ.get('SECRET_KEY'):
    raise ValueError("SECRET_KEY must be set")

if not os.environ.get('ALLOWED_HOSTS'):
    raise ValueError("ALLOWED_HOSTS must be set")

if DEBUG:
    raise ValueError("DEBUG must be False in production")
```

---

## 3. Build Images

```bash
# Pull dernières images de base
docker-compose -f docker-compose.prod.yml pull

# Build images
docker-compose -f docker-compose.prod.yml build --no-cache

# Tag images (optionnel, si registry)
docker tag viatique_backend:latest registry.example.com/viatique_backend:v1.2.0
docker push registry.example.com/viatique_backend:v1.2.0
```

---

## 4. Database Migrations

```bash
# Avec backup automatique avant migration
docker-compose -f docker-compose.prod.yml run --rm backend python manage.py migrate

# Vérifier migrations
docker-compose -f docker-compose.prod.yml run --rm backend python manage.py showmigrations
```

---

## 5. Collectstatic

```bash
docker-compose -f docker-compose.prod.yml run --rm backend python manage.py collectstatic --noinput
```

---

## 6. Deploy Services

```bash
# Rolling restart (pas de downtime)

# 1. Backend workers
docker-compose -f docker-compose.prod.yml up -d --no-deps --build backend

# 2. Celery workers
docker-compose -f docker-compose.prod.yml up -d --no-deps --build celery_worker
docker-compose -f docker-compose.prod.yml up -d --no-deps --build celery_beat

# 3. Frontend
docker-compose -f docker-compose.prod.yml up -d --no-deps --build frontend

# 4. Nginx (reload config sans restart si possible)
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
# ou restart si nécessaire
docker-compose -f docker-compose.prod.yml restart nginx
```

---

## 7. Health Checks

```bash
# Check health endpoint
curl -f https://viatique.example.com/health/ || exit 1

# Check services
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs --tail=100 backend
docker-compose -f docker-compose.prod.yml logs --tail=100 celery_worker
```

**Health Endpoint** :
```python
# core/views.py
def health_check(request):
    try:
        # Test DB
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # Test Redis (Celery)
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        redis_conn.ping()

        return JsonResponse({
            'status': 'healthy',
            'database': 'connected',
            'redis': 'connected'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=503)
```

---

## 8. Monitoring

**Logs** :
```bash
# Tail logs en temps réel
docker-compose -f docker-compose.prod.yml logs -f backend celery_worker

# Surveiller erreurs
docker-compose -f docker-compose.prod.yml logs | grep -i error
```

**Métriques** :
- CPU/Memory usage
- Requests/second
- Error rate (5xx)
- Response time

**Alertes** (Sentry, Grafana, etc.) :
- Erreurs 500
- Downtime services
- DB queries lentes
- Disk space low

---

## 9. Rollback

**Si Problème Détecté** :
```bash
# 1. Revert code
git checkout <previous-stable-tag>

# 2. Rebuild et redeploy
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# 3. Rollback migrations (si nécessaire)
docker-compose -f docker-compose.prod.yml run --rm backend python manage.py migrate <app> <previous_migration>

# 4. Restore DB (si critique)
docker exec -i viatique_db psql -U postgres viatique_prod < backup_20260121_020000.sql

# 5. Vérifier health
curl https://viatique.example.com/health/
```

---

## 10. Post-Deployment

**Checklist** :
- [ ] Health checks OK
- [ ] Logs sans erreurs critiques
- [ ] Smoke tests manuels OK
  - [ ] Login professeur
  - [ ] Accès copie
  - [ ] Annotation fonctionne
  - [ ] Login élève
  - [ ] Visualisation copie élève
- [ ] Métriques normales (CPU, mem, requests)
- [ ] Backup automatique configuré
- [ ] Équipe notifiée (succès)

---

## Script Déploiement Complet

```bash
#!/bin/bash
# deploy.sh

set -e  # Exit on error

echo "=== Viatique Production Deployment ==="

# 1. Backup
echo "1. Backup..."
./backup.sh

# 2. Pull code
echo "2. Pulling latest code..."
git pull origin main

# 3. Build images
echo "3. Building images..."
docker-compose -f docker-compose.prod.yml build

# 4. Migrations
echo "4. Running migrations..."
docker-compose -f docker-compose.prod.yml run --rm backend python manage.py migrate

# 5. Collectstatic
echo "5. Collecting static files..."
docker-compose -f docker-compose.prod.yml run --rm backend python manage.py collectstatic --noinput

# 6. Deploy services
echo "6. Deploying services..."
docker-compose -f docker-compose.prod.yml up -d --no-deps backend celery_worker celery_beat frontend
docker-compose -f docker-compose.prod.yml restart nginx

# 7. Health check
echo "7. Health check..."
sleep 5
curl -f https://viatique.example.com/health/ || {
    echo "Health check failed! Rolling back..."
    # Rollback logic
    exit 1
}

echo "=== Deployment successful ==="
```

---

**Version** : 1.0
**Date** : 2026-01-21
