# Règles de Déploiement Production - Viatique

## Statut : CRITIQUE PRODUCTION

Ces règles garantissent un déploiement sécurisé et stable en production.

---

## 1. Environnements

### 1.1 Séparation Stricte

**OBLIGATOIRE** :
```
Development (Local)
├── DEBUG=True
├── Base de données locale (SQLite/PostgreSQL)
├── Secrets non critiques
└── Logs verbeux

Staging (Pre-production)
├── DEBUG=False
├── Base de données dédiée
├── Secrets de staging
├── Configuration proche production
└── Tests d'intégration

Production
├── DEBUG=False (OBLIGATOIRE)
├── Base de données production
├── Secrets production sécurisés
├── HTTPS obligatoire
└── Monitoring actif
```

**INTERDIT** :
- Utiliser DB production en dev/staging
- Secrets production en dev/staging
- Configuration de dev en production

### 1.2 Variables d'Environnement

**OBLIGATOIRE** :
```bash
# .env.production (JAMAIS versionné)
DEBUG=False
SECRET_KEY=<secret-généré-aléatoirement-min-50-chars>
DATABASE_URL=postgresql://user:password@db:5432/viatique_prod
ALLOWED_HOSTS=viatique.example.com,www.viatique.example.com
CSRF_TRUSTED_ORIGINS=https://viatique.example.com

# Email (si applicable)
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@viatique.example.com
EMAIL_HOST_PASSWORD=<email-password>
EMAIL_USE_TLS=True

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Security
SSL_ENABLED=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

**Règles** :
- Fichier `.env` JAMAIS versionné (dans `.gitignore`)
- Fichier `.env.example` versionné (SANS valeurs)
- Secrets générés aléatoirement (min 50 caractères)
- Rotation des secrets tous les 90 jours

---

## 2. Configuration Django Production

### 2.1 Settings Obligatoires

**OBLIGATOIRE** :
```python
# backend/core/settings.py
import os

# ⚠️ CRITIQUE: Valeurs par défaut INTERDITES en production
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set")

DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
if DEBUG:
    import sys
    if 'runserver' not in sys.argv:  # OK en dev, PAS en prod
        raise ValueError("DEBUG must be False in production")

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    raise ValueError("ALLOWED_HOSTS must be explicitly set")

# HTTPS Obligatoire
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 an
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # Autres headers de sécurité
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
```

**INTERDIT** :
```python
# ❌ JAMAIS en production
SECRET_KEY = 'django-insecure-...'
DEBUG = True
ALLOWED_HOSTS = ['*']
```

### 2.2 Base de Données

**OBLIGATOIRE** :
```python
# PostgreSQL en production (JAMAIS SQLite)
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Validation
if not DATABASES['default']['ENGINE'].startswith('django.db.backends.postgresql'):
    raise ValueError("PostgreSQL required in production")
```

**Raisons** :
- SQLite non adapté à la production (pas de concurrence)
- PostgreSQL robuste, concurrent, performant
- Connection pooling via `conn_max_age`

---

## 3. Architecture Docker Production

### 3.1 Dockerfile Backend Production

**OBLIGATOIRE** :
```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dépendances système
RUN apt-get update && apt-get install -y \
    postgresql-client \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Créer utilisateur non-root
RUN useradd -m -u 1000 django && \
    mkdir -p /app /app/staticfiles /app/media && \
    chown -R django:django /app

WORKDIR /app

# Installer dépendances Python
COPY --chown=django:django requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier code
COPY --chown=django:django . .

# Collecter static files
RUN python manage.py collectstatic --noinput

# Permissions
RUN chmod +x entrypoint.sh

# Utilisateur non-root
USER django

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["gunicorn", "core.wsgi:application", "--config", "gunicorn_config.py"]
```

**Règles** :
- Image slim pour taille réduite
- Utilisateur non-root (sécurité)
- Pas de code en root
- Collectstatic au build
- Entrypoint pour initialisation

### 3.2 Gunicorn Configuration

**OBLIGATOIRE** :
```python
# backend/gunicorn_config.py
import os
import multiprocessing

# Binding
bind = "0.0.0.0:8000"

# Workers
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"  # ou "gevent" pour async
worker_connections = 1000
max_requests = 1000  # Recycle workers
max_requests_jitter = 50
timeout = 30

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"

# Security
limit_request_line = 4094
limit_request_fields = 100
```

### 3.3 Entrypoint Script

**OBLIGATOIRE** :
```bash
#!/bin/bash
# backend/entrypoint.sh

set -e

echo "Waiting for database..."
while ! nc -z $DATABASE_HOST $DATABASE_PORT; do
  sleep 0.1
done
echo "Database ready!"

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting application..."
exec "$@"
```

---

## 4. Nginx Configuration

### 4.1 Nginx Reverse Proxy

**OBLIGATOIRE** :
```nginx
# nginx/nginx.conf
upstream backend {
    server backend:8000;
}

server {
    listen 80;
    server_name viatique.example.com www.viatique.example.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name viatique.example.com www.viatique.example.com;

    # SSL Certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/viatique.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/viatique.example.com/privkey.pem;

    # SSL Configuration (Mozilla Intermediate)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Client body size (uploads)
    client_max_body_size 50M;

    # Frontend (Vue.js)
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Django Admin
    location /admin/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Static files (Django)
    location /static/ {
        alias /app/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Media files (uploads)
    location /media/ {
        alias /app/media/;
        expires 1h;
        add_header Cache-Control "public";

        # Sécurité: empêcher exécution
        location ~* \.(php|py|sh|pl|cgi)$ {
            deny all;
        }
    }
}
```

### 4.2 Rate Limiting

**OBLIGATOIRE** :
```nginx
# Limiter requêtes par IP
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;

server {
    # ...

    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        # ...
    }

    location /api/auth/login/ {
        limit_req zone=login_limit burst=3 nodelay;
        # ...
    }
}
```

---

## 5. Docker Compose Production

### 5.1 Configuration Production

**OBLIGATOIRE** :
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: ${DATABASE_NAME}
      POSTGRES_USER: ${DATABASE_USER}
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD}
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DATABASE_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: always
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    env_file:
      - .env.production
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3

  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A core worker --loglevel=info
    env_file:
      - .env.production
    volumes:
      - media_volume:/app/media
    depends_on:
      - redis
      - db
    restart: always

  celery_beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A core beat --loglevel=info
    env_file:
      - .env.production
    depends_on:
      - redis
    restart: always

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        VITE_API_URL: https://viatique.example.com/api
    restart: always

  nginx:
    build:
      context: ./nginx
      dockerfile: Dockerfile
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - static_volume:/app/staticfiles:ro
      - media_volume:/app/media:ro
      - ./certbot/conf:/etc/letsencrypt:ro
      - ./certbot/www:/var/www/certbot:ro
    depends_on:
      - backend
      - frontend
    restart: always

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

---

## 6. SSL/TLS avec Let's Encrypt

### 6.1 Certbot Configuration

**OBLIGATOIRE** :
```yaml
# docker-compose.prod.yml (ajout)
services:
  certbot:
    image: certbot/certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
```

**Commande Initiale** :
```bash
# Obtenir certificat
docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  -d viatique.example.com \
  -d www.viatique.example.com \
  --email admin@viatique.example.com \
  --agree-tos \
  --no-eff-email
```

---

## 7. Monitoring et Logs

### 7.1 Logging

**OBLIGATOIRE** :
```python
# settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO' if not DEBUG else 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
```

### 7.2 Health Checks

**OBLIGATOIRE** :
```python
# core/views.py
from django.http import JsonResponse
from django.db import connection

def health_check(request):
    """
    Health check endpoint pour monitoring.
    """
    try:
        # Test DB connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        return JsonResponse({
            'status': 'healthy',
            'database': 'connected'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=503)

# urls.py
urlpatterns = [
    path('health/', health_check, name='health_check'),
    # ...
]
```

---

## 8. Backup

### 8.1 Backup Base de Données

**OBLIGATOIRE** :
```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/postgres"
BACKUP_FILE="$BACKUP_DIR/viatique_backup_$DATE.sql"

# Créer répertoire si nécessaire
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker exec viatique_db pg_dump -U postgres viatique_prod > $BACKUP_FILE

# Compression
gzip $BACKUP_FILE

# Rétention: supprimer backups >30 jours
find $BACKUP_DIR -type f -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

### 8.2 Backup Media Files

**OBLIGATOIRE** :
```bash
#!/bin/bash
# backup_media.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR="/backups/media"
MEDIA_DIR="/app/media"

# Backup incrémenta rsync
rsync -av --delete $MEDIA_DIR $BACKUP_DIR/media_$DATE/

echo "Media backup completed: $BACKUP_DIR/media_$DATE/"
```

---

## 9. Procédure de Déploiement

### 9.1 Checklist Pré-Déploiement

**OBLIGATOIRE** :
- [ ] Tests passent (CI/CD)
- [ ] Migrations testées en staging
- [ ] Variables d'environnement production configurées
- [ ] Secrets sécurisés et rotationnés
- [ ] Backup DB récent (<24h)
- [ ] Backup media récent (<24h)
- [ ] Certificat SSL valide et à jour
- [ ] Monitoring configuré
- [ ] Health checks fonctionnels
- [ ] Rollback plan préparé
- [ ] Équipe notifiée

### 9.2 Processus de Déploiement

**OBLIGATOIRE** :
```bash
# 1. Backup
./backup.sh
./backup_media.sh

# 2. Pull dernières images
docker-compose -f docker-compose.prod.yml pull

# 3. Build si nécessaire
docker-compose -f docker-compose.prod.yml build

# 4. Migrations (avec backup auto)
docker-compose -f docker-compose.prod.yml run --rm backend python manage.py migrate

# 5. Collectstatic
docker-compose -f docker-compose.prod.yml run --rm backend python manage.py collectstatic --noinput

# 6. Restart services (rolling restart)
docker-compose -f docker-compose.prod.yml up -d --no-deps --build backend
docker-compose -f docker-compose.prod.yml up -d --no-deps --build celery_worker
docker-compose -f docker-compose.prod.yml up -d --no-deps --build frontend
docker-compose -f docker-compose.prod.yml restart nginx

# 7. Vérifier health
curl https://viatique.example.com/health/

# 8. Vérifier logs
docker-compose -f docker-compose.prod.yml logs -f --tail=100 backend
```

---

## 10. Checklist Production Finale

**Avant mise en production** :
- [ ] DEBUG=False
- [ ] SECRET_KEY sécurisé (>50 chars)
- [ ] ALLOWED_HOSTS explicite
- [ ] PostgreSQL configuré
- [ ] HTTPS activé et forcé
- [ ] Certificat SSL valide
- [ ] CSRF/CORS configurés
- [ ] Rate limiting actif
- [ ] Security headers configurés
- [ ] Permissions DRF strictes (pas AllowAny)
- [ ] Backup automatisé
- [ ] Monitoring actif
- [ ] Health checks fonctionnels
- [ ] Logs centralisés
- [ ] Documentation à jour

---

**Version** : 1.0
**Date** : 2026-01-21
**Statut** : CRITIQUE - Requis pour production
