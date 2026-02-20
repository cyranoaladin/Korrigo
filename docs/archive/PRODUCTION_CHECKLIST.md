# 🚀 Production Checklist - Korrigo

**Version**: v1.0.0-rc1 → v1.0.0
**Date**: 2026-01-29
**Objectif**: Déployer Release Candidate en production avec sécurité et résilience.

---

## Les 7 Items qui Comptent Vraiment

### ✅ 1. Staging Deploy de v1.0.0-rc1

**Objectif**: Valider RC1 dans un environnement identique à la production.

**Actions**:
```bash
# Checkout tag RC1
git checkout v1.0.0-rc1

# Deploy sur staging avec config prod-like
docker compose -f infra/docker/docker-compose.staging.yml up -d --build

# Vérifier services
docker compose -f infra/docker/docker-compose.staging.yml ps
```

**Variables d'environnement** (identiques à prod) :
```bash
DJANGO_ENV=production
DEBUG=False
SECRET_KEY=<staging-secret-64-chars>
ALLOWED_HOSTS=staging.korrigo.example.com
CSRF_TRUSTED_ORIGINS=https://staging.korrigo.example.com
DATABASE_URL=postgresql://user:password@db:5432/korrigo_staging
METRICS_TOKEN=<staging-token-64-chars>
SSL_ENABLED=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

**Vérification**:
- [ ] 5/5 services healthy (backend, celery, db, redis, nginx)
- [ ] Migrations appliquées sans erreur
- [ ] Seed fonctionne (copies avec pages > 0)
- [ ] HTTPS actif et certificat valide
- [ ] /metrics endpoint sécurisé (si METRICS_TOKEN set)

**Durée estimée**: 30 min

---

### ✅ 2. METRICS_TOKEN : Secret Fort

**Objectif**: Sécuriser l'endpoint `/metrics` (exposition de métriques sensibles).

**Règle**:
- ❌ **Jamais de default** (`METRICS_TOKEN=""` = endpoint PUBLIC, warning logged)
- ✅ **Toujours en prod** : Token fort, 64+ caractères, aléatoire

**Génération**:
```bash
# Générer token sécurisé (64 chars)
openssl rand -hex 32

# Ou via Python
python -c "import secrets; print(secrets.token_hex(32))"
```

**Configuration**:
```bash
# .env.production (JAMAIS versionné)
METRICS_TOKEN=a1b2c3d4e5f6...  # 64+ chars
```

**Vérification**:
```bash
# Sans token → 401
curl https://korrigo.example.com/metrics/
# → {"error": "Unauthorized"}

# Avec token → 200
curl -H "X-Metrics-Token: $METRICS_TOKEN" https://korrigo.example.com/metrics/
# → {"status": "ok", "db_connections": 3, ...}
```

**Durée estimée**: 5 min

---

### ✅ 3. TLS : HTTPS + Headers Sécurité

**Objectif**: Chiffrer toutes les communications et protéger contre attaques courantes.

**Certificat SSL** (Let's Encrypt recommandé) :
```bash
# Avec Certbot (Docker)
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  -d korrigo.example.com \
  -d www.korrigo.example.com \
  --email admin@korrigo.example.com \
  --agree-tos

# Nginx reload après obtention certificat
docker compose -f docker-compose.prod.yml restart nginx
```

**Headers Nginx** (déjà dans `nginx.conf`, vérifier) :
```nginx
# HSTS (1 an)
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;

# XSS Protection
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header X-XSS-Protection "1; mode=block" always;
```

**Vérification**:
```bash
# Test HTTPS
curl -I https://korrigo.example.com/ | grep -i "strict-transport-security"
# → Strict-Transport-Security: max-age=31536000; includeSubDomains; preload

# Test redirect HTTP → HTTPS
curl -I http://korrigo.example.com/ | grep -i "location"
# → Location: https://korrigo.example.com/

# SSL Labs test (optionnel mais recommandé)
# https://www.ssllabs.com/ssltest/analyze.html?d=korrigo.example.com
# → Grade A ou A+ attendu
```

**Durée estimée**: 20 min (certificat) + 5 min (vérif headers)

---

### ✅ 4. Backups DB : Quotidien + Rotation + Test Restore

**Objectif**: Protéger contre perte de données (corruption, erreur humaine, ransomware).

**Script Backup** (`scripts/backup_db.sh`) :
```bash
#!/bin/bash
set -euo pipefail

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/postgres"
BACKUP_FILE="$BACKUP_DIR/korrigo_backup_$DATE.sql"

# Créer répertoire
mkdir -p $BACKUP_DIR

# Backup PostgreSQL (via Docker)
docker exec korrigo_db pg_dump -U postgres korrigo_prod > $BACKUP_FILE

# Compression
gzip $BACKUP_FILE

# Rétention: supprimer backups >30 jours
find $BACKUP_DIR -type f -name "*.sql.gz" -mtime +30 -delete

echo "✅ Backup completed: $BACKUP_FILE.gz"
```

**Cron Job** (backup quotidien à 2h du matin) :
```cron
0 2 * * * /path/to/scripts/backup_db.sh >> /var/log/backup.log 2>&1
```

**Test Restore** (à faire AVANT production, puis mensuellement) :
```bash
# Restore sur DB de test
gunzip -c /backups/postgres/korrigo_backup_20260129_020000.sql.gz \
  | docker exec -i korrigo_test_db psql -U postgres korrigo_test

# Vérifier intégrité
docker exec korrigo_test_db psql -U postgres korrigo_test -c "SELECT COUNT(*) FROM exams_copy;"
# → Doit retourner nombre de copies attendu
```

**Vérification**:
- [ ] Script backup fonctionne (test manuel)
- [ ] Cron job configuré et actif
- [ ] Backups créés quotidiennement (vérifier logs)
- [ ] Rétention 30 jours appliquée (vérifier `ls $BACKUP_DIR`)
- [ ] Test restore réussi sur DB test

**Durée estimée**: 30 min (setup) + 15 min/mois (test restore)

---

### ✅ 5. Monitoring : Logs + Alerting

**Objectif**: Détecter et réagir rapidement aux incidents (erreurs 500, pannes, attaques).

**Minimum viable** :
1. **Logs centralisés** (Docker logs → fichier ou service externe)
2. **Alerting sur erreurs critiques** (emails ou Slack)

**Option 1 : Sentry (recommandé, gratuit jusqu'à 5k events/mois)** :
```python
# backend/core/settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

if not DEBUG:
    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        integrations=[DjangoIntegration()],
        traces_sample_rate=0.1,  # 10% des requêtes tracées
        send_default_pii=False,  # RGPD: ne pas envoyer données perso
    )
```

**Configuration**:
```bash
# .env.production
SENTRY_DSN=https://xxx@sentry.io/yyy
```

**Option 2 : Email alerts (simple, pas de dépendance externe)** :
```python
# settings.py
if not DEBUG:
    LOGGING = {
        'handlers': {
            'mail_admins': {
                'level': 'ERROR',
                'class': 'django.utils.log.AdminEmailHandler',
            }
        },
        'loggers': {
            'django': {
                'handlers': ['mail_admins'],
                'level': 'ERROR',
            }
        }
    }

    ADMINS = [('Admin', 'admin@korrigo.example.com')]
    EMAIL_HOST = 'smtp.example.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = 'noreply@korrigo.example.com'
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASSWORD')
```

**Vérification**:
- [ ] Monitoring configuré (Sentry DSN ou email SMTP)
- [ ] Test d'alerte fonctionnel (déclencher une erreur 500 volontairement)
- [ ] Alertes reçues dans les 5 minutes
- [ ] Logs accessibles et lisibles

**Durée estimée**: 20 min (Sentry) ou 30 min (email)

---

### ✅ 6. Smoke Staging : Workflow Complet

**Objectif**: Valider manuellement le workflow critique en staging AVANT production.

**Scénario de test** (E2E réel, pas automatisé) :

#### A) Login Professeur
```bash
# Via UI ou curl
curl -X POST https://staging.korrigo.example.com/api/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username": "prof1", "password": "prof_password"}'
# → HTTP 200 + session cookie
```

#### B) Lister Copies READY
```bash
curl -b cookies.txt https://staging.korrigo.example.com/api/copies/?status=READY
# → HTTP 200 + liste copies avec pages > 0
```

#### C) Lock Copie
```bash
curl -b cookies.txt -X POST \
  https://staging.korrigo.example.com/api/grading/copies/{copy_id}/lock/ \
  -H 'X-CSRFToken: {csrf}'
# → HTTP 201 + lock_token
```

#### D) Annoter
```bash
curl -b cookies.txt -X POST \
  https://staging.korrigo.example.com/api/grading/copies/{copy_id}/annotations/ \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFToken: {csrf}' \
  -H 'X-Lock-Token: {lock_token}' \
  -d '{"page_index": 0, "x": 0.1, "y": 0.2, "w": 0.3, "h": 0.05, "type": "COMMENT", "content": "Test"}'
# → HTTP 201
```

#### E) Finaliser
```bash
curl -b cookies.txt -X POST \
  https://staging.korrigo.example.com/api/grading/copies/{copy_id}/finalize/ \
  -H 'Content-Type: application/json' \
  -H 'X-CSRFToken: {csrf}' \
  -d '{"scores": {"Q1": 5, "Q2": 3}, "comment": "Bien"}'
# → HTTP 200 + status=GRADED
```

#### F) Récupérer PDF Final
```bash
curl -b cookies.txt \
  https://staging.korrigo.example.com/api/grading/copies/{copy_id}/pdf/ \
  -o final_copy.pdf
# → HTTP 200 + PDF téléchargé

# Vérifier PDF
file final_copy.pdf
# → PDF document, version 1.x

# Ouvrir et vérifier visuellement annotations aplaties
```

**Checklist Smoke** :
- [ ] Login prof réussit
- [ ] Liste copies READY (pages > 0)
- [ ] Lock copie fonctionne (HTTP 201)
- [ ] Annotation créée (HTTP 201)
- [ ] Finalisation fonctionne (status → GRADED)
- [ ] PDF final téléchargé et annotations visibles
- [ ] Unlock automatique après finalize

**Durée estimée**: 15 min

---

### ✅ 7. Tag v1.0.0 + Release Notes Prod

**Objectif**: Figer la version production et documenter les changements.

**Après validation staging** :
```bash
# Checkout main
git checkout main

# Tag v1.0.0 (remove RC)
git tag -a v1.0.0 -m "Production Release v1.0.0

✅ Validated in staging
✅ Release Gate: 205 passed, 0 failed, 0 skipped
✅ E2E: 3/3 runs with annotations
✅ Smoke test: Full workflow validated

Changes since v1.0.0-rc1:
- (list any hotfixes or changes made during staging)

Production Ready:
- HTTPS with Let's Encrypt
- METRICS_TOKEN secured
- Daily backups configured
- Monitoring active (Sentry/email)
- Smoke test passed

See RELEASE_GATE_REPORT_v1.0.0-rc1.md for full validation details."

# Push tag
git push origin v1.0.0

# Create GitHub Release (production)
gh release create v1.0.0 \
  --title "v1.0.0 - Production Release 🚀" \
  --notes-file RELEASE_NOTES_v1.0.0.md
```

**Release Notes** (`RELEASE_NOTES_v1.0.0.md`) :
```markdown
# Release v1.0.0 - Production

**Release Date**: 2026-01-29
**Status**: Production Ready 🚀

## Summary

First production release of Korrigo, validated through comprehensive Release Gate process.

## Key Features

- ✅ Exam PDF ingestion and split
- ✅ Booklet detection and validation
- ✅ Copy creation with anonymization
- ✅ Grading workflow with locking
- ✅ Vector annotations (bounding box)
- ✅ PDF export with flattened annotations
- ✅ Student access to graded copies
- ✅ Audit trail and logging

## Validation

- **Release Gate**: 205 tests passed, 0 failed, 0 skipped
- **E2E**: 3/3 runs with annotations (POST 201, GET 200)
- **Seed**: All copies with pages > 0
- **Smoke Test**: Full workflow validated in staging
- **Security**: HTTPS, CSRF, CORS, permissions enforced

## Production Setup

- HTTPS with Let's Encrypt
- METRICS_TOKEN secured (64+ chars)
- Daily backups with 30-day retention
- Monitoring active (Sentry or email alerts)
- Zero-tolerance CI validation

## Known Limitations

- XFAIL policy not yet defined (placeholder in CI)
- METRICS_TOKEN warning if not set (operator's choice)

## Upgrade from RC1

No breaking changes. Direct deployment possible.

## Support

- Documentation: `docs/` directory
- Issues: https://github.com/cyranoaladin/Korrigo/issues
- Release Gate Report: RELEASE_GATE_REPORT_v1.0.0-rc1.md
```

**Vérification**:
- [ ] Tag v1.0.0 créé et pushed
- [ ] GitHub Release créée (production, pas pre-release)
- [ ] Release notes claires et complètes
- [ ] Artifacts CI attachés (optionnel)

**Durée estimée**: 10 min

---

## Résumé Timeline

| Item | Durée Estimée | Critique |
|------|---------------|----------|
| 1. Staging Deploy | 30 min | ⚠️ Critique |
| 2. METRICS_TOKEN | 5 min | ⚠️ Critique |
| 3. TLS + Headers | 25 min | ⚠️ Critique |
| 4. Backups | 30 min | ⚠️ Critique |
| 5. Monitoring | 20-30 min | ⚠️ Critique |
| 6. Smoke Staging | 15 min | ⚠️ Critique |
| 7. Tag v1.0.0 | 10 min | ✅ Final |
| **TOTAL** | **~2h30** | - |

---

## Rollback Plan

**En cas de problème en production** :

### Rollback Immédiat (< 5 min)
```bash
# 1. Revert to previous stable version
git checkout v0.9.x  # ou tag stable précédent

# 2. Rebuild and restart
docker compose -f docker-compose.prod.yml up -d --build

# 3. Verify services
docker compose -f docker-compose.prod.yml ps
curl https://korrigo.example.com/api/health/
```

### Rollback avec Restore DB (< 15 min)
```bash
# 1. Stop services
docker compose -f docker-compose.prod.yml down

# 2. Restore last backup
gunzip -c /backups/postgres/korrigo_backup_YYYYMMDD_HHMMSS.sql.gz \
  | docker exec -i korrigo_db psql -U postgres korrigo_prod

# 3. Restart with old version
git checkout v0.9.x
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Post-Production

**Première semaine** :
- [ ] Monitoring quotidien (erreurs, performance)
- [ ] Vérifier backups quotidiens créés
- [ ] Test restore hebdomadaire
- [ ] Collecter feedback utilisateurs
- [ ] Préparer hotfixes si nécessaire

**Maintenance continue** :
- [ ] Test restore mensuel
- [ ] Rotation secrets tous les 90 jours
- [ ] Mise à jour dépendances (security patches)
- [ ] Review logs mensuel (audit trail)

---

**Checklist Complète** : Cocher les 7 items avant tag v1.0.0.

**Contact Support** : admin@korrigo.example.com
**Escalation** : Shark (responsable technique)
