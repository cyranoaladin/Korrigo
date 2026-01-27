# Inventaire - Configuration de Production

**Date**: 27 janvier 2026  
**Audit**: Production Readiness - Korrigo PMF  
**Phase**: PHASE 1 - INVENTAIRE

---

## Vue d'ensemble

Cette section documente l'inventaire complet de la configuration de production de Korrigo PMF, incluant les paramètres Django, variables d'environnement, configuration Docker, serveurs web, base de données, logging, monitoring, et CI/CD.

---

## 1. Paramètres Django (Production vs Development)

### 1.1 Fichiers de configuration

| Fichier | Usage | Notes |
|---------|-------|-------|
| `backend/core/settings.py` | **Configuration principale** | Paramètres de base, guards de sécurité |
| `backend/core/settings_prod.py` | **Production stricte** | Hérite de settings.py, renforce la sécurité |
| `backend/core/settings_test.py` | **Tests** | Isolation des tests, SQLite temporaire |

### 1.2 Paramètres de sécurité critiques

#### ✅ SECRET_KEY
- **Dev**: Fallback généré automatiquement (`django-insecure-dev-only-xxx`)
- **Prod**: **OBLIGATOIRE via env var**, sinon `ValueError` au démarrage
- **Fichier**: `backend/core/settings.py:8-15`
- **Production guard**: ✅ Fail-fast si absent en production

```python
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if DJANGO_ENV == "production":
        raise ValueError("SECRET_KEY environment variable must be set in production")
    SECRET_KEY = "django-insecure-dev-only-" + "x" * 50
```

#### ✅ DEBUG
- **Dev**: `True` par défaut (via `DEBUG=True` env var)
- **Prod**: **Forcé à False**, erreur si `DEBUG=True` avec `DJANGO_ENV=production`
- **Fichier**: `backend/core/settings.py:17-29`
- **Production guard**: ✅ Fail-fast si DEBUG=True en production

```python
raw_debug = os.environ.get("DEBUG", "True").lower() == "true"
if DJANGO_ENV == "production":
    if raw_debug:
        raise ValueError("CRITICAL: DEBUG must be False in production (DJANGO_ENV=production).")
    DEBUG = False
else:
    DEBUG = raw_debug
```

#### ✅ ALLOWED_HOSTS
- **Dev**: `localhost,127.0.0.1` par défaut
- **Prod**: **Doit être explicite**, erreur si contient `*`
- **Fichier**: `backend/core/settings.py:31-34`
- **Production guard**: ✅ Interdit `*` en production

```python
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
if "*" in ALLOWED_HOSTS and DJANGO_ENV == "production":
    raise ValueError("ALLOWED_HOSTS cannot contain '*' in production")
```

### 1.3 Paramètres SSL/HTTPS

#### SSL_ENABLED (configurable)
- **Prod réelle**: `SSL_ENABLED=True` → force HTTPS redirect, secure cookies, HSTS
- **Prod-like (E2E)**: `SSL_ENABLED=False` → HTTP-only, pas de redirect (pour tests E2E)
- **Fichier**: `backend/core/settings.py:52-72`

| Paramètre | SSL_ENABLED=True | SSL_ENABLED=False |
|-----------|------------------|-------------------|
| `SECURE_SSL_REDIRECT` | ✅ True | ❌ False |
| `SESSION_COOKIE_SECURE` | ✅ True | ❌ False |
| `CSRF_COOKIE_SECURE` | ✅ True | ❌ False |
| `SECURE_HSTS_SECONDS` | ✅ 31536000 (1 an) | ❌ Non défini |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | ✅ True | ❌ Non défini |
| `SECURE_HSTS_PRELOAD` | ✅ True | ❌ Non défini |

#### Headers de sécurité (production)
- **Fichier**: `backend/core/settings.py:73-75`
- ✅ `SECURE_BROWSER_XSS_FILTER = True`
- ✅ `SECURE_CONTENT_TYPE_NOSNIFF = True`
- ✅ `X_FRAME_OPTIONS = 'DENY'`

### 1.4 CORS Configuration

| Environnement | Configuration | Fichier |
|---------------|---------------|---------|
| **Dev** | Origins hardcodés (localhost:5173, 8088, 5174) | `settings.py:219-229` |
| **Prod** | Explicit via `CORS_ALLOWED_ORIGINS` env var, ou same-origin only | `settings.py:230-240` |

**Sécurité**:
- ✅ Production: Origins explicites uniquement
- ✅ Credentials autorisés seulement si origins définis
- ✅ Headers CORS limités (x-csrftoken, authorization, content-type)

### 1.5 Content Security Policy (CSP)

| Environnement | CSP | Fichier |
|---------------|-----|---------|
| **Dev** | Permissif (unsafe-inline, unsafe-eval) | `settings.py:273-284` |
| **Prod** | **Strict** (self only, frame-ancestors none, upgrade-insecure-requests) | `settings.py:257-272` |

**Production CSP**:
- `default-src: 'self'`
- `script-src: 'self', 'unsafe-inline'` (⚠️ à affiner pour retirer unsafe-inline si possible)
- `style-src: 'self', 'unsafe-inline'`
- `img-src: 'self', data:, blob:`
- `frame-ancestors: 'none'`
- `upgrade-insecure-requests: true`

### 1.6 Rate Limiting

- **Activation**: Env var `RATELIMIT_ENABLE` (défaut: `true`)
- **Production guard**: ✅ Fail-fast si désactivé en production (sauf si `E2E_TEST_MODE=true`)
- **Fichier**: `backend/core/settings.py:202-215`
- **Cache**: LocMemCache (dev/test), à remplacer par Redis en production pour multi-workers

```python
RATELIMIT_ENABLE = os.environ.get("RATELIMIT_ENABLE", "true").lower() == "true"
E2E_TEST_MODE = os.environ.get("E2E_TEST_MODE", "false").lower() == "true"

if DJANGO_ENV == "production" and not RATELIMIT_ENABLE and not E2E_TEST_MODE:
    raise ValueError("RATELIMIT_ENABLE cannot be false in production environment (unless E2E_TEST_MODE=true)")
```

---

## 2. Variables d'environnement

### 2.1 Fichier `.env.example`

**Fichier**: `.env.example` (29 lignes)

| Variable | Valeur exemple | Requis en Prod | Notes |
|----------|----------------|----------------|-------|
| `DJANGO_SETTINGS_MODULE` | `core.settings_prod` | ✅ Oui | Utiliser settings_prod en production |
| `SECRET_KEY` | `django-insecure-CHANGE_ME_IN_PROD` | ✅ Oui | Générer avec `get_random_secret_key()` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | ✅ Oui | Domaines explicites |
| `DJANGO_LOG_LEVEL` | `INFO` | ⚠️ Recommandé | INFO ou WARNING en prod |
| `DB_NAME` | `viatique` | ✅ Oui (settings_prod) | PostgreSQL database name |
| `DB_USER` | `viatique_user` | ✅ Oui (settings_prod) | PostgreSQL user |
| `DB_PASSWORD` | `change_this_password_in_prod` | ✅ Oui (settings_prod) | ⚠️ Mot de passe fort obligatoire |
| `DB_HOST` | `127.0.0.1` | ✅ Oui (settings_prod) | PostgreSQL host |
| `DB_PORT` | `5432` | ✅ Oui (settings_prod) | PostgreSQL port |
| `DB_CONN_MAX_AGE` | `60` | ⚠️ Recommandé | Connection pooling (secondes) |
| `SECURE_HSTS_SECONDS` | `0` | ⚠️ Si SSL | Mettre 31536000 si SSL_ENABLED=true |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `false` | ⚠️ Si SSL | Mettre true si SSL_ENABLED=true |
| `SECURE_HSTS_PRELOAD` | `false` | ⚠️ Si SSL | Mettre true si SSL_ENABLED=true |
| `SSL_ENABLED` | `false` | ✅ Oui | **true** en production réelle |
| `E2E_SEED_TOKEN` | `` | ❌ Non | ⚠️ Ne JAMAIS définir en production réelle |
| `CORS_ALLOWED_ORIGINS` | `` | ⚠️ Si CORS | Domaines frontend si séparés |
| `CSRF_TRUSTED_ORIGINS` | `` | ⚠️ Si CORS | Domaines frontend si séparés |

### 2.2 Variables utilisées par settings_prod.py

**Fichier**: `backend/core/settings_prod.py`

```python
def _get_required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} environment variable must be set")
    return value

SECRET_KEY = _get_required_env("SECRET_KEY")
DJANGO_ALLOWED_HOSTS = _get_required_env("DJANGO_ALLOWED_HOSTS")  # via check ligne 21
DB_NAME = _get_required_env("DB_NAME")
DB_USER = _get_required_env("DB_USER")
DB_PASSWORD = _get_required_env("DB_PASSWORD")
DB_HOST = _get_required_env("DB_HOST")
DB_PORT = _get_required_env("DB_PORT")
```

**⚠️ ATTENTION**: settings_prod.py utilise des noms de variables différents (DJANGO_ALLOWED_HOSTS vs ALLOWED_HOSTS dans settings.py). À harmoniser pour éviter confusion.

---

## 3. Configuration Docker

### 3.1 Docker Compose - Environnements disponibles

| Fichier | Usage | Build | Images | Notes |
|---------|-------|-------|--------|-------|
| `infra/docker/docker-compose.yml` | **Dev locale** | Build local | N/A | Développement avec hot-reload |
| `infra/docker/docker-compose.prod.yml` | **Production** | Images pré-build | GHCR (SHA-tagged) | Déploiement CI/CD |
| `infra/docker/docker-compose.local-prod.yml` | **Prod-like local** | Build local | N/A | Test local avec topologie prod |
| `infra/docker/docker-compose.prodlike.yml` | **Prod-like (legacy)** | Build local | N/A | Ancienne version |
| `infra/docker/docker-compose.e2e.yml` | **E2E tests** | Build local | N/A | Tests Playwright |

### 3.2 docker-compose.prod.yml (Production)

**Fichier**: `infra/docker/docker-compose.prod.yml`

#### Services

| Service | Image | Command | Ports | Volumes | Health Check |
|---------|-------|---------|-------|---------|--------------|
| **db** | `postgres:15-alpine` | N/A | - | `postgres_data:/var/lib/postgresql/data` | ✅ pg_isready (5s interval) |
| **redis** | `redis:7-alpine` | N/A | - | - | ✅ redis-cli ping (5s interval) |
| **backend** | `ghcr.io/${OWNER}/korrigo-backend:${SHA}` | `gunicorn` (3 workers, 120s timeout) | expose:8000 | `static_volume`, `media_volume` | ✅ curl /api/health/ (30s interval) |
| **celery** | `ghcr.io/${OWNER}/korrigo-backend:${SHA}` | `celery -A core worker -l info` | - | `media_volume` | ❌ Aucun |
| **nginx** | `ghcr.io/${OWNER}/korrigo-nginx:${SHA}` | N/A | 8088:80 | `static_volume:ro`, `media_volume:ro` | ✅ curl / (30s interval) |

#### Variables d'environnement (backend)

```yaml
DJANGO_ENV: production
DEBUG: "False"
SSL_ENABLED: "${SSL_ENABLED:-False}"  # ⚠️ Devrait être True en prod réelle
SECRET_KEY: "${SECRET_KEY:-prod-secret-key-change-it}"  # ⚠️ Fallback dangereux
ALLOWED_HOSTS: "${ALLOWED_HOSTS:-localhost,127.0.0.1,nginx,backend}"
DATABASE_URL: "postgres://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"
CELERY_BROKER_URL: "redis://redis:6379/0"
CORS_ALLOWED_ORIGINS: "${CORS_ALLOWED_ORIGINS:-http://localhost:8088}"
CSRF_TRUSTED_ORIGINS: "${CSRF_TRUSTED_ORIGINS:-http://localhost:8088}"
```

**⚠️ Risques identifiés**:
1. **Fallback SECRET_KEY** dangereux en production (devrait fail-fast si absent)
2. **SSL_ENABLED** par défaut à False (devrait être True en prod réelle)
3. **Celery**: Pas de health check (impossible de détecter un worker crashé)

#### Volumes persistants

```yaml
volumes:
  postgres_data:      # Base de données PostgreSQL
  static_volume:      # Fichiers statiques Django (collectstatic)
  media_volume:       # Fichiers média (copies PDF, annotations)
```

### 3.3 Backend Dockerfile

**Fichier**: `backend/Dockerfile`

```dockerfile
FROM python:3.9-slim
WORKDIR /app

# System dependencies (OpenCV, PDF processing, health checks)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    curl \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
```

**✅ Bonnes pratiques**:
- Image slim (légère)
- Dépendances système minimales (OpenCV, poppler-utils pour PDF)
- Nettoyage apt cache
- curl inclus pour health checks

### 3.4 Nginx Dockerfile

**Fichier**: `infra/nginx/Dockerfile`

```dockerfile
# Stage 1: Build Frontend (Vue.js)
FROM node:20-alpine as builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:1.25-alpine
RUN rm /etc/nginx/conf.d/default.conf
COPY infra/nginx/nginx.conf /etc/nginx/conf.d/
COPY --from=builder /app/dist /usr/share/nginx/html
RUN mkdir -p /app/staticfiles /app/media
```

**✅ Bonnes pratiques**:
- Multi-stage build (frontend build séparé de l'image finale)
- Image alpine (légère)
- Suppression du default.conf

### 3.5 Entrypoint Script

**Fichier**: `backend/entrypoint.sh`

```bash
#!/bin/bash
set -e

echo "--> Applied database migrations..."
python manage.py migrate

echo "--> Collecting static files..."
python manage.py collectstatic --noinput

if [ "$#" -gt 0 ]; then
    exec "$@"
else
    echo "--> Starting Gunicorn..."
    exec gunicorn core.wsgi:application -c gunicorn_config.py
fi
```

**✅ Bonnes pratiques**:
- Migrations automatiques au démarrage
- Collectstatic automatique
- `set -e` (fail-fast)
- `exec` pour remplacer le shell (signals correctement propagés)

**⚠️ Risques**:
- Migrations au démarrage peuvent être bloquantes si longues (scaling horizontal)
- Pas de rollback automatique si migration échoue après démarrage

---

## 4. Configuration Nginx

**Fichier**: `infra/nginx/nginx.conf`

### 4.1 Configuration générale

```nginx
resolver 127.0.0.11 valid=10s ipv6=off;  # Docker DNS resolver

server {
    listen 80;
    include /etc/nginx/mime.types;
    client_max_body_size 100M;  # Large PDF uploads
    
    # Security Headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

### 4.2 Endpoints

| Location | Upstream | Description | Notes |
|----------|----------|-------------|-------|
| `/static/` | File system (`/app/staticfiles/`) | Fichiers statiques Django | ✅ Servis directement par Nginx |
| `/media/` | File system (`/app/media/`) | Fichiers média (PDF copies) | ✅ Servis directement par Nginx |
| `/api/` | `http://backend:8000` | API Django REST | ✅ Proxy avec headers forwarded |
| `/admin/` | `http://backend:8000` | Django Admin | ✅ Proxy avec headers forwarded |
| `/` | File system (`/usr/share/nginx/html`) | Frontend Vue.js (SPA) | ✅ Fallback à index.html |

### 4.3 Sécurité

**✅ Headers présents**:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

**⚠️ Headers manquants en production réelle** (présents dans DEPLOYMENT_GUIDE.md mais pas dans nginx.conf actuel):
- ❌ `Strict-Transport-Security` (HSTS) - doit être ajouté si SSL
- ❌ Configuration SSL/HTTPS (certificats Let's Encrypt)
- ❌ Redirect HTTP→HTTPS

**Note**: nginx.conf actuel est pour HTTP (dev/local-prod). Production réelle nécessite config SSL séparée.

---

## 5. Base de données et Connexions

### 5.1 PostgreSQL Configuration

#### Development (settings.py)
```python
if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
```

#### Production (settings.py)
```python
else:
    DATABASES = {
        'default': dj_database_url.config(
            default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'),
            conn_max_age=600  # Connection pooling: 10 minutes
        )
    }
```

#### Production strict (settings_prod.py)
```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASSWORD,
        "HOST": DB_HOST,
        "PORT": DB_PORT,
        "CONN_MAX_AGE": int(os.environ.get("DB_CONN_MAX_AGE", "60")),
    }
}
```

### 5.2 Connection Pooling

| Paramètre | Valeur | Description |
|-----------|--------|-------------|
| `CONN_MAX_AGE` (settings.py) | **600** secondes (10 min) | Via dj_database_url |
| `CONN_MAX_AGE` (settings_prod.py) | **60** secondes (1 min) | Via env var |
| `CONN_MAX_AGE` (settings_test.py) | **0** (disabled) | Tests isolés |

**⚠️ Incohérence**: settings.py (600s) vs settings_prod.py (60s). À harmoniser.

### 5.3 Celery / Redis

```python
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
```

- ✅ Redis utilisé pour Celery broker
- ⚠️ Cache Django utilise LocMemCache (non partagé entre workers) → devrait utiliser Redis en production

---

## 6. Logging et Monitoring

### 6.1 Configuration Logging (settings_prod.py)

**Fichier**: `backend/core/settings_prod.py:49-68`

```python
LOG_LEVEL = os.environ.get("DJANGO_LOG_LEVEL", "INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}
```

**✅ Présent dans settings_prod.py**  
**❌ Absent dans settings.py** (pas de config logging en dev/prod via settings.py)

### 6.2 Health Check Endpoints

**Fichier**: `backend/core/views_health.py`

| Endpoint | Permission | Check | Response |
|----------|------------|-------|----------|
| `/api/health/` | AllowAny | Simple ping | `{"status": "ok"}` |
| `/health/` | AllowAny | Simple ping | `{"status": "ok"}` |
| `/readyz/` | AllowAny | **Database check** | `{"status": "ok"}` ou 503 |

```python
@api_view(['GET'])
@permission_classes([AllowAny])
def readyz_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return Response({"status": "ok"})
    except Exception:
        return Response({"detail": "db unavailable"}, status=503)
```

**✅ Bonnes pratiques**:
- Endpoints sans authentification (pour load balancers)
- `/readyz/` vérifie la DB (readiness probe)
- `/health/` simple (liveness probe)

**⚠️ Manques**:
- Pas de check Redis/Celery
- Pas de métriques (Prometheus, statsd)
- Pas d'alerting configuré

### 6.3 Docker Health Checks

| Service | Health Check | Interval | Timeout | Retries | Start Period |
|---------|-------------|----------|---------|---------|--------------|
| **db** | `pg_isready` | 5s | 5s | 5 | - |
| **redis** | `redis-cli ping` | 5s | 5s | 5 | - |
| **backend** | `curl /api/health/` | 30s | 10s | 3 | 30s |
| **nginx** | `curl /` | 30s | 10s | 3 | - |
| **celery** | ❌ Aucun | - | - | - | - |

**⚠️ Celery**: Pas de health check → impossible de détecter worker mort.

---

## 7. Gunicorn Configuration

**Fichier**: `backend/gunicorn_config.py`

```python
import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2
timeout = 120  # 120s pour PDF flattening
forwarded_allow_ips = '*'
```

**Calcul workers**: `(CPU_COUNT * 2) + 1`
- 2 CPU → 5 workers
- 4 CPU → 9 workers

**✅ Bonnes pratiques**:
- Timeout élevé (120s) pour traitements PDF lourds
- Multi-threading (2 threads par worker)

**⚠️ Risques**:
- `forwarded_allow_ips = '*'` → accepte n'importe quel proxy (devrait être limité à Nginx)
- Pas de configuration `access_log` / `error_log`
- Pas de `graceful_timeout` (défaut 30s)

---

## 8. CI/CD

### 8.1 Workflows GitHub Actions

| Fichier | Trigger | Jobs | Déploiement |
|---------|---------|------|-------------|
| `.github/workflows/korrigo-ci.yml` | push/PR (main, develop) | lint → unit → security → integration → packaging → gate | ❌ Non |
| `.github/workflows/deploy.yml` | push (main) + manual | ci → build_and_push → deploy | ✅ Oui (VPS) |

### 8.2 korrigo-ci.yml (Gate de déploiement)

**Jobs**:
1. **lint**: flake8 (backend)
2. **unit**: pytest (tous les tests backend)
3. **security**: pip-audit + bandit
4. **integration**: tests workflow complet (grading, concurrency, PDF validators, full audit)
5. **packaging**: Docker build backend
6. **deployable_gate**: Gate final (tous les jobs doivent passer)

**✅ Bonnes pratiques**:
- Gate de sécurité (pip-audit, bandit)
- Tests d'intégration critiques (concurrency, workflow complet)
- Build Docker pour vérifier la reproductibilité

**⚠️ Manques**:
- Pas de tests frontend (lint, typecheck) dans korrigo-ci.yml
- Pas de tests E2E dans CI

### 8.3 deploy.yml (Déploiement continu)

**Pipeline**:
1. **ci**: Frontend (lint + typecheck + build) + Backend (tests)
2. **build_and_push**: Build Docker images → Push GHCR (SHA + latest)
3. **deploy**: SSH → VPS → Pull images → Migrate → Collectstatic → Up → Health check

**✅ Bonnes pratiques**:
- Images taggées par SHA (traçabilité)
- Migrations avant redémarrage
- Health check post-deploy
- Secrets validation

**⚠️ Risques**:
- Pas de rollback automatique si health check échoue
- Pas de blue/green deployment
- Migrations bloquantes pendant déploiement (downtime potentiel)

---

## 9. Fichiers statiques et média

### 9.1 Configuration Django

```python
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB
```

### 9.2 Stockage

| Type | Path | Servi par | Volume Docker | Notes |
|------|------|-----------|---------------|-------|
| **Static** | `/app/staticfiles` | Nginx | `static_volume` | collectstatic au démarrage |
| **Media** | `/app/media` | Nginx | `media_volume` | Copies PDF, annotations |

**⚠️ Risques**:
- Pas de backup automatique du volume `media_volume` (contient les copies d'examens)
- Pas de stockage S3/object storage (scalabilité limitée)

---

## 10. Checklist de préparation production

### 10.1 Variables d'environnement obligatoires

#### ✅ Obligatoires (Fail-fast si absent)
- [x] `SECRET_KEY` (généré aléatoirement, ≥50 caractères)
- [x] `DJANGO_ENV=production`
- [x] `DEBUG=False`
- [x] `ALLOWED_HOSTS` (domaines explicites, pas de `*`)

#### ✅ Obligatoires si settings_prod.py
- [x] `DJANGO_ALLOWED_HOSTS`
- [x] `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`

#### ⚠️ Fortement recommandées
- [ ] `SSL_ENABLED=true` (production réelle)
- [ ] `CORS_ALLOWED_ORIGINS` (si frontend sur domaine différent)
- [ ] `CSRF_TRUSTED_ORIGINS` (si frontend sur domaine différent)
- [ ] `DJANGO_LOG_LEVEL=INFO` ou `WARNING`
- [ ] `DB_CONN_MAX_AGE=60` ou plus
- [ ] `RATELIMIT_ENABLE=true` (jamais désactiver en prod)

#### ❌ INTERDITES en production
- [x] `E2E_SEED_TOKEN` (ne JAMAIS définir)
- [x] `E2E_TEST_MODE=true` (ne JAMAIS activer)

### 10.2 Configuration Docker

- [x] Images taggées par SHA (pas `latest` en prod)
- [x] Health checks configurés (db, redis, backend, nginx)
- [ ] Health check Celery (manquant)
- [x] Volumes persistants (postgres_data, media_volume, static_volume)
- [ ] Backup automatique des volumes (manquant)
- [x] Restart policy: `unless-stopped`

### 10.3 Configuration Nginx

- [x] Headers de sécurité (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection)
- [ ] SSL/TLS (certificats Let's Encrypt)
- [ ] HSTS header (si SSL)
- [ ] Redirect HTTP→HTTPS (si SSL)
- [x] `client_max_body_size 100M` (upload PDF)

### 10.4 Sécurité

- [x] DEBUG=False en production
- [x] SECRET_KEY aléatoire et sécurisé
- [x] ALLOWED_HOSTS explicite
- [x] Rate limiting activé
- [x] CSP strict en production
- [x] CORS origins explicites
- [x] DRF: Authentication requise par défaut (`IsAuthenticated`)
- [x] Fail-closed security guards (DEBUG, ALLOWED_HOSTS, SECRET_KEY)

### 10.5 Monitoring & Observabilité

- [x] Health check endpoints (/api/health/, /readyz/)
- [x] Logging configuré (settings_prod.py)
- [ ] Métriques (Prometheus, statsd) - **MANQUANT**
- [ ] Alerting (email, Slack, PagerDuty) - **MANQUANT**
- [ ] Distributed tracing (Sentry, Datadog) - **MANQUANT**

### 10.6 CI/CD

- [x] Tests backend (pytest) dans CI
- [x] Tests frontend (lint, typecheck) dans CI
- [x] Security scan (pip-audit, bandit) dans CI
- [ ] Tests E2E dans CI - **MANQUANT**
- [x] Docker build dans CI
- [x] Déploiement automatique (deploy.yml)
- [ ] Rollback automatique - **MANQUANT**

---

## 11. Risques et Gaps Identifiés

### P0 (Blocants)

1. **❌ Fallback SECRET_KEY dangereux** (docker-compose.prod.yml:48)
   - `SECRET_KEY: "${SECRET_KEY:-prod-secret-key-change-it}"`
   - Devrait fail-fast si absent (comme dans settings.py)

2. **❌ SSL_ENABLED=False par défaut en production** (docker-compose.prod.yml:47)
   - Production réelle DOIT avoir SSL_ENABLED=True
   - Cookies non sécurisés, pas de HSTS

3. **❌ Pas de backup automatique media_volume**
   - Contient les copies d'examens (données critiques)
   - Perte = perte des notes et annotations

### P1 (Sérieux)

4. **⚠️ Celery sans health check**
   - Worker mort = tâches bloquées silencieusement
   - Aucune alerte si crash

5. **⚠️ Cache LocMemCache en production** (settings.py:195-200)
   - Non partagé entre workers Gunicorn
   - Rate limiting inefficace en multi-workers
   - Devrait utiliser Redis

6. **⚠️ Incohérence variables d'environnement**
   - settings.py: `ALLOWED_HOSTS` / settings_prod.py: `DJANGO_ALLOWED_HOSTS`
   - Confusion possible, risque de mauvaise config

7. **⚠️ Incohérence CONN_MAX_AGE**
   - settings.py: 600s / settings_prod.py: 60s
   - Quelle valeur en production ?

8. **⚠️ Gunicorn `forwarded_allow_ips = '*'`**
   - Accepte n'importe quel proxy
   - Risque de spoofing X-Forwarded-For

9. **⚠️ Pas de rollback automatique**
   - Si déploiement échoue, reste en état cassé
   - Intervention manuelle requise

10. **⚠️ Migrations bloquantes au démarrage**
    - Downtime si migration longue
    - Pas de stratégie blue/green

### P2 (Améliorations)

11. **📝 Pas de métriques / APM**
    - Pas de Prometheus, statsd, Datadog
    - Observabilité limitée

12. **📝 Pas d'alerting configuré**
    - Pas de notification si service down
    - Détection d'incidents manuelle

13. **📝 CSP unsafe-inline** (settings.py:262)
    - `script-src` et `style-src` autorisent `'unsafe-inline'`
    - Réduit efficacité CSP contre XSS

14. **📝 Pas de tests E2E dans CI**
    - E2E seulement en local
    - Risque de régression non détectée

15. **📝 Pas de stockage S3**
    - Scalabilité limitée (volume Docker local)
    - Pas de CDN pour media files

---

## 12. Commandes de vérification

### Vérifier configuration production

```bash
# 1. Vérifier settings.py guards
cd backend
python -c "import os; os.environ['DJANGO_ENV']='production'; os.environ['DEBUG']='True'; import core.settings" 2>&1 | grep "CRITICAL: DEBUG must be False"

# 2. Vérifier SECRET_KEY obligatoire
python -c "import os; os.environ['DJANGO_ENV']='production'; import core.settings" 2>&1 | grep "SECRET_KEY environment variable must be set"

# 3. Vérifier ALLOWED_HOSTS
python -c "import os; os.environ['DJANGO_ENV']='production'; os.environ['ALLOWED_HOSTS']='*'; import core.settings" 2>&1 | grep "ALLOWED_HOSTS cannot contain"

# 4. Vérifier rate limiting guard
python -c "import os; os.environ['DJANGO_ENV']='production'; os.environ['RATELIMIT_ENABLE']='false'; import core.settings" 2>&1 | grep "RATELIMIT_ENABLE cannot be false"
```

### Vérifier Docker production

```bash
# 1. Vérifier health checks
docker compose -f infra/docker/docker-compose.prod.yml config | grep -A5 healthcheck

# 2. Vérifier variables d'environnement
docker compose -f infra/docker/docker-compose.prod.yml config | grep -E "(SECRET_KEY|DEBUG|SSL_ENABLED|ALLOWED_HOSTS)"

# 3. Vérifier volumes persistants
docker compose -f infra/docker/docker-compose.prod.yml config | grep -A2 "volumes:"
```

### Vérifier health checks en prod

```bash
# 1. Liveness (simple ping)
curl -f http://localhost:8088/api/health/

# 2. Readiness (DB check)
curl -f http://localhost:8088/readyz/

# 3. Vérifier réponse 503 si DB down
docker compose -f infra/docker/docker-compose.prod.yml stop db
curl -i http://localhost:8088/readyz/  # Devrait retourner 503
docker compose -f infra/docker/docker-compose.prod.yml start db
```

---

## Conclusion

### ✅ Points forts

1. **Guards de sécurité robustes** (settings.py)
   - DEBUG forcé à False en production
   - SECRET_KEY obligatoire
   - ALLOWED_HOSTS validé
   - Rate limiting protégé

2. **Health checks complets**
   - Endpoints dédiés (/health/, /readyz/)
   - Docker health checks (db, redis, backend, nginx)
   - Vérification DB dans readiness probe

3. **CI/CD mature**
   - Gate de déploiement (lint, tests, security, integration)
   - Déploiement automatique avec health check
   - Images SHA-tagged (traçabilité)

4. **Configuration Docker solide**
   - Multi-environnements (dev, prod, local-prod, e2e)
   - Volumes persistants
   - Restart policies

### ⚠️ Gaps critiques (P0/P1)

1. **Fallback SECRET_KEY dangereux** (docker-compose.prod.yml)
2. **SSL_ENABLED=False par défaut** en production
3. **Pas de backup automatique** media_volume
4. **Celery sans health check**
5. **Cache LocMemCache** (non partagé entre workers)
6. **Incohérences** variables d'environnement (settings.py vs settings_prod.py)
7. **Pas de rollback automatique**

### 📊 Maturité Production Readiness

| Catégorie | Score | Commentaire |
|-----------|-------|-------------|
| **Sécurité** | 8/10 | Guards robustes, mais SSL par défaut désactivé |
| **Observabilité** | 5/10 | Logs OK, mais pas de métriques/alerting |
| **Résilience** | 6/10 | Health checks OK, mais pas de rollback auto |
| **Scalabilité** | 5/10 | Gunicorn multi-workers, mais cache non partagé |
| **Opérationnalité** | 7/10 | CI/CD mature, mais gaps backup/monitoring |

**Verdict**: Application **QUASI prête pour production**, mais nécessite corrections P0/P1 avant déploiement réel.

---

**Prochaine étape**: Audit P0/P1/P2 (PHASE 2 - AUDIT PAR RISQUE)
