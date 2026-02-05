# 🎨 AUDIT COMPLET - Frontend + Infrastructure + Tests + Monitoring

**Date** : 2026-02-05
**Scope** : Tâches 4-7 (Vue.js, Docker/Nginx/Celery, Tests E2E, Monitoring)

---

## 4️⃣ AUDIT FRONTEND VUE.JS

### ✅ Points Positifs
- **Architecture** : Vue 3 + Vite + Pinia (moderne et performant)
- **Router Guards** : Présents dans `router/index.js` (lignes 109-159)
- **API Layer** : Centralisé dans `services/api.js` avec interceptors
- **CSRF Protection** : Implémentée (api.js:14-35)
- **Credentials** : `withCredentials: true` correctement configuré

### ⚠️ Problèmes Identifiés

#### 1. XSS Potentiel - v-html non trouvé (✅ Bon)
**Status** : ✅ Aucun usage de `v-html` détecté
**Conclusion** : Pas de risque XSS immédiat

#### 2. Validation Formulaires - Incomplète
**Fichiers** : Login.vue, CorrectorDashboard.vue
**Problème** : Validation côté client basique
**Recommandation** :
```vue
<!-- Ajouter validation avec Vee-Validate ou Zod -->
<script setup>
import { useForm } from 'vee-validate'
import * as yup from 'yup'

const schema = yup.object({
  username: yup.string().required('Requis').min(3),
  password: yup.string().required('Requis').min(8)
})

const { errors, handleSubmit } = useForm({ validationSchema: schema })
</script>
```

#### 3. Gestion d'Erreurs - Basique
**Fichiers** : CorrectorDashboard.vue:23-26
**Problème** : `console.error()` uniquement, pas de notification utilisateur
**Recommandation** :
```javascript
import { useToast } from 'vue-toastification'

const toast = useToast()

catch (err) {
  console.error("Failed to fetch copies", err)
  toast.error("Échec du chargement des copies")
}
```

#### 4. Performance - Bundle Size
**Problème** : Pas de lazy loading pour les routes
**Recommandation** :
```javascript
// router/index.js
const routes = [
  {
    path: '/admin-dashboard',
    component: () => import('../views/AdminDashboard.vue')  // Lazy load
  }
]
```

#### 5. Sécurité - Password Visibility Toggle
**Fichier** : Login.vue:88-143
**Status** : ✅ Correctement implémenté avec bouton toggle

### 📊 Score Frontend : 🟢 **85/100**

**Résumé** :
- Sécurité : ✅ Bon (CSRF, credentials)
- Performance : 🟡 Moyen (lazy loading manquant)
- UX : ✅ Bon (password toggle, loading states)
- Tests : ❌ Absents

---

## 5️⃣ AUDIT DOCKER/NGINX/CELERY

### Docker Compose

**Fichier analysé** : `infra/docker/docker-compose.prod.yml`

#### ✅ Points Positifs
- Health checks présents sur tous les services
- Volumes persistants (postgres_data, media_volume)
- Restart policy : `unless-stopped`
- Networks correctement configurés

#### ⚠️ Problèmes Identifiés

##### 1. Gunicorn Workers - Sous-dimensionné
**Ligne 33** : `--workers 3`
**Problème** : Formule recommandée = (2 × CPU) + 1
**Recommandation** :
```yaml
command: gunicorn core.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers $((2 * $(nproc) + 1)) \
  --worker-class=gthread \
  --threads=2 \
  --timeout 120 \
  --max-requests 1000 \
  --max-requests-jitter 50
```

##### 2. Gunicorn Timeout - Trop court pour OCR
**Ligne 33** : `--timeout 120`
**Problème** : OCR peut prendre 5-10 minutes
**Recommandation** : Utiliser Celery pour OCR (déjà prévu)

##### 3. Celery - Pas de workers spécialisés
**Fichier** : docker-compose.prod.yml:62-78
**Problème** : Un seul worker pour toutes les tâches
**Recommandation** :
```yaml
celery-default:
  image: ghcr.io/${GITHUB_REPOSITORY_OWNER}/korrigo-backend:${KORRIGO_SHA:-latest}
  command: celery -A core worker -l info -Q default -c 4

celery-ocr:
  image: ghcr.io/${GITHUB_REPOSITORY_OWNER}/korrigo-backend:${KORRIGO_SHA:-latest}
  command: celery -A core worker -l info -Q ocr -c 2

celery-pdf:
  image: ghcr.io/${GITHUB_REPOSITORY_OWNER}/korrigo-backend:${KORRIGO_SHA:-latest}
  command: celery -A core worker -l info -Q pdf -c 2
```

### Nginx Configuration

**Fichier analysé** : `frontend/Dockerfile` (ligne 24-49)

#### ✅ Points Positifs
- `client_max_body_size 1G` présent
- Timeouts étendus (3600s)
- Headers X-Forwarded correctement configurés

#### ⚠️ Problèmes Identifiés

##### 1. Compression Gzip - Manquante
**Recommandation** :
```nginx
server {
    listen 80;
    server_name localhost;

    # AJOUTER :
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    gzip_min_length 1000;

    # Cache pour les assets statiques
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

##### 2. Rate Limiting - Manquant au niveau Nginx
**Recommandation** :
```nginx
# Ajouter avant server {}
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

server {
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://backend:8000;
    }
}
```

### Celery Configuration

**Fichier analysé** : `backend/core/settings.py:365-392`

#### ✅ Points Positifs
- Queues dédiées configurées (import, finalize, maintenance)
- Rate limiting sur tâches lourdes
- `CELERY_WORKER_PREFETCH_MULTIPLIER = 1` (évite blocking)

#### ⚠️ Problèmes Identifiés

##### 1. Pas de retry automatique
**Recommandation** :
```python
# backend/grading/tasks.py
@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    retry_backoff=True
)
def async_import_pdf(self, copy_id):
    ...
```

##### 2. Monitoring Celery - Flower absent
**Recommandation** :
```yaml
# docker-compose.prod.yml
flower:
  image: ghcr.io/${GITHUB_REPOSITORY_OWNER}/korrigo-backend:${KORRIGO_SHA:-latest}
  command: celery -A core flower --port=5555
  ports:
    - "5555:5555"
  environment:
    FLOWER_BASIC_AUTH: "admin:${FLOWER_PASSWORD}"
```

### 📊 Score Infrastructure : 🟡 **78/100**

**Résumé** :
- Docker : ✅ Bon (health checks, volumes)
- Nginx : 🟡 Moyen (compression manquante)
- Celery : ✅ Bon (queues dédiées)
- Monitoring : ❌ Flower absent

---

## 6️⃣ TESTS E2E AUTOMATISÉS

### Status Actuel
- **Tests unitaires** : ❌ Absents
- **Tests d'intégration** : ❌ Absents
- **Tests E2E** : ❌ Absents
- **Coverage** : 0%

### 🎯 Suite de Tests Recommandée

#### Tests Unitaires (pytest)
```python
# tests/unit/test_models.py
import pytest
from exams.models import Exam, Copy

@pytest.mark.django_db
class TestCopyModel:
    def test_copy_creation(self):
        exam = Exam.objects.create(name='Test Exam')
        copy = Copy.objects.create(
            exam=exam,
            anonymous_id='C001',
            status=Copy.Status.STAGING
        )
        assert copy.anonymous_id == 'C001'
        assert copy.status == Copy.Status.STAGING

    def test_copy_status_transitions(self):
        copy = Copy.objects.create(...)
        copy.status = Copy.Status.READY
        copy.save()
        assert copy.status == Copy.Status.READY
```

#### Tests d'Intégration (pytest + Django TestCase)
```python
# tests/integration/test_api_auth.py
import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User

@pytest.mark.django_db
class TestAuthenticationFlow:
    def test_login_logout_flow(self):
        client = APIClient()
        user = User.objects.create_user('teacher', 'test@test.com', 'pass123')

        # Login
        response = client.post('/api/login/', {
            'username': 'teacher',
            'password': 'pass123'
        })
        assert response.status_code == 200

        # Access protected endpoint
        response = client.get('/api/me/')
        assert response.status_code == 200

        # Logout
        response = client.post('/api/logout/')
        assert response.status_code == 200

        # Access protected endpoint after logout
        response = client.get('/api/me/')
        assert response.status_code == 403
```

#### Tests E2E (Playwright)
```javascript
// tests/e2e/test_grading_workflow.spec.ts
import { test, expect } from '@playwright/test'

test('full grading workflow', async ({ page }) => {
  // Login as teacher
  await page.goto('https://korrigo.labomaths.tn/teacher/login')
  await page.fill('[data-testid="login.username"]', 'teacher')
  await page.fill('[data-testid="login.password"]', 'password')
  await page.click('[data-testid="login.submit"]')

  // Wait for redirect to dashboard
  await expect(page).toHaveURL('/corrector-dashboard')

  // Click on first copy
  await page.click('.copy-card:first-child')

  // Wait for PDF to load
  await expect(page.locator('.pdf-viewer')).toBeVisible()

  // Add annotation
  await page.click('.annotation-tool')
  await page.click('.pdf-viewer', { position: { x: 100, y: 100 } })
  await page.fill('.annotation-comment', 'Bonne réponse')

  // Finalize copy
  await page.click('button:has-text("Finaliser")')
  await expect(page.locator('.success-message')).toBeVisible()
})
```

### 📋 Plan d'Implémentation Tests

#### Phase 1 : Setup (1 jour)
```bash
# Backend tests
pip install pytest pytest-django pytest-cov faker

# Frontend tests
npm install --save-dev @playwright/test vitest @vue/test-utils

# Configuration
# pytest.ini, playwright.config.ts, vitest.config.ts
```

#### Phase 2 : Tests Critiques (1 semaine)
```bash
# Tests sécurité
tests/test_security_critical.py (5 tests)

# Tests authentification
tests/test_auth.py (10 tests)

# Tests permissions
tests/test_permissions.py (15 tests)
```

#### Phase 3 : Tests Fonctionnels (2 semaines)
```bash
# Tests endpoints
tests/test_exams_api.py (20 tests)
tests/test_grading_api.py (30 tests)
tests/test_identification_api.py (15 tests)

# Tests frontend
frontend/tests/unit/Login.spec.ts (5 tests)
frontend/tests/unit/CorrectorDashboard.spec.ts (10 tests)
```

#### Phase 4 : Tests E2E (1 semaine)
```bash
# Scénarios complets
tests/e2e/test_full_workflow.spec.ts (5 scénarios)
tests/e2e/test_student_portal.spec.ts (3 scénarios)
```

### 📊 Score Tests : 🔴 **0/100** → Cible **90/100**

---

## 7️⃣ MONITORING (LOGS, ALERTES, MÉTRIQUES)

### Status Actuel
- **Logs structurés** : ✅ Partiellement (JSON formatter présent)
- **Error tracking** : ❌ Absent (pas de Sentry)
- **Métriques** : ✅ Prometheus endpoint présent (/metrics)
- **Dashboard** : ❌ Absent (pas de Grafana)
- **Alertes** : ❌ Absentes

### 🔧 Configuration Recommandée

#### 1. Sentry (Error Tracking)
```python
# backend/core/settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

if not DEBUG:
    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment=DJANGO_ENV,
        release=os.environ.get('KORRIGO_SHA', 'unknown'),
    )
```

#### 2. Structured Logging (JSON)
```python
# backend/core/logging.py (déjà présent, ligne 293)
# ✅ Déjà configuré correctement
import json
import logging

class ViatiqueJSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'funcName': record.funcName,
        }

        # Ajouter contexte request si disponible
        if hasattr(record, 'request_id'):
            log_data['request_id'] = record.request_id
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id

        return json.dumps(log_data)
```

#### 3. Prometheus Metrics
```python
# backend/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Métriques HTTP
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Métriques Celery
celery_task_duration_seconds = Histogram(
    'celery_task_duration_seconds',
    'Celery task duration',
    ['task_name']
)

# Métriques Business
copies_processed_total = Counter(
    'copies_processed_total',
    'Total copies processed',
    ['status']
)

active_users_gauge = Gauge(
    'active_users',
    'Number of active users'
)
```

#### 4. Grafana Dashboard
```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:10.4.6
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
    ports:
      - "3000:3000"
    depends_on:
      - prometheus

  node_exporter:
    image: prom/node-exporter:latest
    ports:
      - "9100:9100"

volumes:
  prometheus_data:
  grafana_data:
```

#### 5. Alertes (Alertmanager)
```yaml
# alertmanager.yml
global:
  resolve_timeout: 5m

route:
  receiver: 'email'
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h

receivers:
  - name: 'email'
    email_configs:
      - to: 'admin@labomaths.tn'
        from: 'alertmanager@labomaths.tn'
        smarthost: 'smtp.example.com:587'
        auth_username: 'alerts@labomaths.tn'
        auth_password: '${SMTP_PASSWORD}'

# Règles d'alerte
groups:
  - name: korrigo_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} req/s"

      - alert: SlowEndpoint
        expr: http_request_duration_seconds{quantile="0.95"} > 2
        for: 10m
        annotations:
          summary: "Slow endpoint detected"
          description: "95th percentile latency is {{ $value }}s"

      - alert: CeleryQueueBacklog
        expr: celery_queue_length > 1000
        for: 15m
        annotations:
          summary: "Celery queue backlog"
          description: "Queue length is {{ $value }}"
```

### 📊 Score Monitoring : 🟡 **40/100** → Cible **95/100**

**Résumé** :
- Logs : ✅ JSON formatter présent
- Métriques : ✅ Prometheus endpoint
- Dashboard : ❌ Grafana absent
- Alertes : ❌ Absentes
- Error Tracking : ❌ Sentry absent

---

## 📊 SCORES FINAUX

| Audit | Score Actuel | Score Cible | Gap |
|-------|--------------|-------------|-----|
| 1. Sécurité | 75/100 | 92/100 | +17 |
| 2. Endpoints | 80/100 | 95/100 | +15 |
| 3. Performances | 45/100 | 90/100 | +45 |
| 4. Frontend | 85/100 | 95/100 | +10 |
| 5. Infrastructure | 78/100 | 90/100 | +12 |
| 6. Tests | 0/100 | 90/100 | +90 |
| 7. Monitoring | 40/100 | 95/100 | +55 |
| **GLOBAL** | **58/100** | **92/100** | **+34** |

---

## 🚀 ROADMAP DE MISE EN PRODUCTION

### Semaine 1 : Correctifs Critiques
- [ ] Corriger vulnérabilités sécurité P0
- [ ] Ajouter index DB manquants
- [ ] Corriger N+1 queries
- [ ] Déployer en staging

### Semaine 2 : Performances
- [ ] Implémenter Celery async tasks
- [ ] Ajouter pagination
- [ ] Cache Redis
- [ ] Tests de charge

### Semaine 3 : Tests
- [ ] Suite tests unitaires (50+)
- [ ] Tests d'intégration (30+)
- [ ] Tests E2E (10+)
- [ ] CI/CD pipeline

### Semaine 4 : Monitoring
- [ ] Sentry configuration
- [ ] Grafana dashboards
- [ ] Alerting rules
- [ ] Documentation opérationnelle

### Semaine 5 : Validation & Déploiement
- [ ] Review complète
- [ ] Tests en préproduction
- [ ] Backup & rollback plan
- [ ] Déploiement production

---

**Audit complet réalisé par** : Claude Code (Anthropic)
**Date** : 2026-02-05
**Version** : 1.0
