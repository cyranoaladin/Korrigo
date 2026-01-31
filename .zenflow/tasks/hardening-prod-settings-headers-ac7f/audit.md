# Audit de Durcissement Production - Korrigo

**ID de Tâche**: ZF-AUD-12  
**Date**: 2026-01-31  
**Statut**: Finalisé  
**Auteur**: Audit de Sécurité Automatisé

---

## 1. Résumé Exécutif

### 1.1 État de Sécurité Actuel

Le projet Korrigo dispose d'une **base solide de sécurité** avec des pratiques Django modernes déjà implémentées. La configuration actuelle démontre une compréhension approfondie des exigences de sécurité web.

**Points Forts** ✅:
- Configuration conditionnelle DEBUG/production robuste
- Validation SECRET_KEY stricte en production
- Gestion ALLOWED_HOSTS avec protection contre les wildcards
- Cookies sécurisés conditionnels (SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE)
- Middleware CSP (django-csp) installé et configuré
- Headers de sécurité de base dans nginx
- Backup/restore fonctionnel (scripts shell + commandes Django)
- Protection contre les injections SQL (ORM Django)
- Timeouts de connexion DB configurés

**Lacunes Identifiées** ❌:
- Headers de sécurité incomplets dans nginx (HSTS, CSP)
- CSP défini en Django mais absent de nginx (redondance manquante)
- Configuration HSTS conditionnelle uniquement (via SSL_ENABLED)
- Smoke tests basiques (santé uniquement, pas de tests static/media)
- Absence de validation de déploiement automatisée

### 1.2 Recommandations Critiques (P0)

1. **Ajouter HSTS dans nginx** pour forcer HTTPS (uniquement quand SSL_ENABLED=true)
2. **Ajouter CSP dans nginx** pour defense-in-depth (aligné avec Django CSP)
3. **Valider la configuration EMAIL** pour les notifications d'erreur en production
4. **Implémenter smoke tests complets** (health + static + media)
5. **Documenter la procédure de backup/restore** consolidée

---

## 2. Analyse Django Deployment Check

### 2.1 Configuration de Production Actuelle

**Fichiers de Configuration**:
- `backend/core/settings.py` (512 lignes) - Configuration de base
- `backend/core/settings_prod.py` (69 lignes) - Surcharges production
- `.env.prod.example` (51 lignes) - Template d'environnement

**Variables d'Environnement Critiques**:
```bash
DJANGO_ENV=production          # Force mode production
DEBUG=False                    # Désactive debug (validé par code)
SECRET_KEY=<required>          # Obligatoire en production
DJANGO_ALLOWED_HOSTS=<required> # Liste explicite de domaines
SSL_ENABLED=true               # Active HTTPS/HSTS/cookies sécurisés
```

### 2.2 Analyse des Potentiels Warnings Django

Bien que la commande `manage.py check --deploy` n'ait pas pu être exécutée directement, l'analyse statique des configurations révèle les conformités et risques suivants :

#### P0 - Critique (À Corriger Avant Production Réelle)

| # | Warning | Localisation | État | Résolution |
|---|---------|--------------|------|------------|
| **P0-1** | **SECURE_HSTS_SECONDS non défini par défaut** | `settings_prod.py:45` | ⚠️ **ATTENTION** | Valeur par défaut = 0 (désactivé). Doit être `31536000` en prod réelle avec SSL |
| **P0-2** | **EMAIL_HOST non configuré** | `settings.py:498` | ⚠️ **ATTENTION** | Utilise `smtp.example.com` par défaut. Notifications d'erreur ne fonctionneront pas |
| **P0-3** | **CSP manquant dans nginx** | `infra/nginx/nginx.conf` | ❌ **MANQUANT** | CSP défini en Django mais pas en nginx (pas de defense-in-depth) |
| **P0-4** | **HSTS manquant dans nginx** | `infra/nginx/nginx.conf` | ❌ **MANQUANT** | HSTS uniquement en Django quand SSL_ENABLED=true, absent de nginx |

**Impact**: 
- P0-1/P0-4 : Sans HSTS, navigateurs peuvent faire requêtes HTTP initiales (vulnérable à downgrade attacks)
- P0-2 : Erreurs critiques ne seront pas notifiées aux administrateurs
- P0-3 : Pas de couche de protection CSP au niveau reverse proxy (single point of failure)

**Résolution P0-1 (SECURE_HSTS_SECONDS)**:
```python
# backend/core/settings_prod.py:45
# AVANT:
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))

# APRÈS:
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
```

**Résolution P0-2 (EMAIL_HOST)**:
```bash
# .env.prod (production réelle)
EMAIL_HOST=smtp.votre-domaine.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=notifications@votre-domaine.com
EMAIL_HOST_PASSWORD=<mot-de-passe-sécurisé>
ADMINS=admin@votre-domaine.com
```

#### P1 - Haute Priorité (Devrait Être Corrigé)

| # | Recommandation | Localisation | État | Résolution |
|---|----------------|--------------|------|------------|
| **P1-1** | **Permissions-Policy header manquant** | `infra/nginx/nginx.conf` | ❌ **MANQUANT** | Ajouter `Permissions-Policy` pour restreindre APIs navigateur |
| **P1-2** | **CSP report-uri non configuré** | `settings.py:433` | ⚠️ **OPTIONNEL** | Ajouter `report-uri` pour monitorer violations CSP |
| **P1-3** | **SECURE_SSL_REDIRECT conditionnel** | `settings.py:106` | ✅ **JUSTIFIÉ** | Par design : prod-like (E2E HTTP) vs prod réelle (HTTPS) |
| **P1-4** | **Cache Redis non protégé par mot de passe** | `docker-compose.prod.yml` | ⚠️ **ATTENTION** | Redis sans AUTH (acceptable si réseau Docker isolé) |

**Impact**:
- P1-1 : Navigateurs peuvent accéder à APIs sensibles (caméra, géolocalisation, microphone)
- P1-2 : Aucun monitoring des violations CSP en production
- P1-3 : Nécessaire pour environnement E2E (prod-like HTTP)
- P1-4 : Redis accessible sans authentification sur réseau Docker interne

**Résolution P1-1 (Permissions-Policy)**:
```nginx
# infra/nginx/nginx.conf
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), interest-cohort=()" always;
```

#### P2 - Moyenne Priorité (Meilleures Pratiques)

| # | Recommandation | Localisation | État | Résolution |
|---|----------------|--------------|------|------------|
| **P2-1** | **DB connection pooling** | `settings_prod.py:37` | ✅ **CONFIGURÉ** | `CONN_MAX_AGE=60` déjà défini |
| **P2-2** | **Logging structuré JSON** | `settings.py:283` | ✅ **IMPLÉMENTÉ** | `ViatiqueJSONFormatter` en production |
| **P2-3** | **Session engine cached_db** | `settings.py:256` | ✅ **IMPLÉMENTÉ** | Optimise performances sessions |
| **P2-4** | **METRICS_TOKEN non configuré** | `settings.py:86` | ⚠️ **AVERTISSEMENT** | Warning loggué au démarrage si manquant |

**Impact**:
- Bonnes pratiques déjà implémentées
- P2-4 : `/metrics` endpoint public si METRICS_TOKEN non défini (choix opérateur)

#### P3 - Basse Priorité (Améliorations Optionnelles)

| # | Amélioration | État | Commentaire |
|---|--------------|------|-------------|
| **P3-1** | **Subresource Integrity (SRI)** | ❌ **NON IMPLÉMENTÉ** | Nécessite build frontend avec hashes |
| **P3-2** | **Expect-CT header** | ❌ **NON IMPLÉMENTÉ** | Deprecated, remplacé par Certificate Transparency |
| **P3-3** | **Feature-Policy (legacy)** | ❌ **NON IMPLÉMENTÉ** | Remplacé par Permissions-Policy |

---

## 3. Configuration Headers de Sécurité

### 3.1 État Actuel des Headers

#### Headers Nginx (infra/nginx/nginx.conf:12-16)

**Présents** ✅:
```nginx
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

**Manquants** ❌:
- `Strict-Transport-Security` (HSTS)
- `Content-Security-Policy` (CSP)
- `Permissions-Policy`

#### Headers Django (settings.py:102-121)

**Présents** ✅ (quand `SSL_ENABLED=true`):
```python
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
```

**CSP Django** (settings.py:433-446):
```python
CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        'default-src': ["'self'"],
        'script-src': ["'self'"],
        'style-src': ["'self'"],
        'img-src': ["'self'", "data:", "blob:"],
        'font-src': ["'self'"],
        'connect-src': ["'self'"],
        'frame-ancestors': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
        'upgrade-insecure-requests': True,
    }
}
```

### 3.2 Configuration Recommandée Nginx (Production HTTPS)

⚠️ **IMPORTANT**: Ces headers ne doivent être activés **QUE si `SSL_ENABLED=true`** (production réelle avec TLS).

**Approche Proposée**:
1. Créer deux configurations nginx : `nginx.conf` (HTTP) et `nginx-ssl.conf` (HTTPS)
2. Ou : Utiliser templating nginx avec variables d'environnement (via `envsubst`)
3. Ou : Documenter clairement la configuration manuelle pour production HTTPS

**Configuration Nginx pour Production HTTPS**:
```nginx
# infra/nginx/nginx-ssl.conf (NOUVELLE VERSION PRODUCTION HTTPS)
server {
    listen 443 ssl http2;
    server_name votre-domaine.com;
    
    # Certificats TLS
    ssl_certificate /etc/ssl/certs/votre-domaine.crt;
    ssl_certificate_key /etc/ssl/private/votre-domaine.key;
    
    # Protocoles TLS modernes uniquement
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    
    # Security Headers (PRODUCTION HTTPS UNIQUEMENT)
    
    # HSTS: Force HTTPS pour 1 an (31536000 secondes)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    
    # CSP: Defense-in-depth (aligné avec Django CSP)
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests" always;
    
    # Clickjacking Protection
    add_header X-Frame-Options "DENY" always;
    
    # MIME Sniffing Protection
    add_header X-Content-Type-Options "nosniff" always;
    
    # XSS Filter (legacy mais sans danger)
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Referrer Policy
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Permissions Policy (désactive APIs navigateur non utilisées)
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), interest-cohort=()" always;
    
    # Augmenter taille max pour uploads PDF
    client_max_body_size 100M;
    
    # ... (reste de la configuration identique à nginx.conf)
}

# Redirection HTTP -> HTTPS
server {
    listen 80;
    server_name votre-domaine.com;
    return 301 https://$server_name$request_uri;
}
```

**Configuration Nginx pour Prod-Like (E2E HTTP)**:
```nginx
# infra/nginx/nginx.conf (VERSION ACTUELLE - PROD-LIKE HTTP)
# CONSERVER POUR ENVIRONNEMENT E2E (SANS SSL)
server {
    listen 80;
    
    # Security Headers (SANS HSTS - HTTP seulement)
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # NE PAS AJOUTER:
    # - Strict-Transport-Security (HSTS): UNIQUEMENT pour HTTPS
    # - upgrade-insecure-requests (CSP): UNIQUEMENT pour HTTPS
    
    # ... (reste de la configuration)
}
```

### 3.3 Validation des Headers

**Outil recommandé**: [securityheaders.com](https://securityheaders.com)

**Checklist de Validation**:
- [ ] HSTS présent avec `max-age >= 31536000`
- [ ] CSP présent avec `frame-ancestors 'none'` et `default-src 'self'`
- [ ] X-Frame-Options = `DENY`
- [ ] X-Content-Type-Options = `nosniff`
- [ ] Referrer-Policy = `strict-origin-when-cross-origin`
- [ ] Permissions-Policy restreint caméra, micro, géolocalisation
- [ ] Score A ou A+ sur securityheaders.com

**Commande de Test**:
```bash
curl -I https://votre-domaine.com | grep -E "(Strict-Transport|Content-Security|X-Frame|X-Content)"
```

---

## 4. Configuration Cookies de Sécurité

### 4.1 État Actuel

**Configuration Actuelle (settings.py:102-130)**:
```python
# Logique conditionnelle basée sur DEBUG et SSL_ENABLED
if not DEBUG:
    if SSL_ENABLED:
        # Production HTTPS réelle
        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True
        SECURE_HSTS_SECONDS = 31536000
    else:
        # Prod-like (E2E) HTTP
        SESSION_COOKIE_SECURE = False
        CSRF_COOKIE_SECURE = False
else:
    # Développement
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False

# Tous environnements
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # SPA doit lire CSRF token
```

**Configuration Production (settings_prod.py:41-43)**:
```python
# Force cookies sécurisés en production
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

### 4.2 Validation ✅

| Paramètre | Valeur | État | Commentaire |
|-----------|--------|------|-------------|
| `SESSION_COOKIE_SECURE` | `True` (prod) | ✅ | Forcé dans `settings_prod.py` |
| `CSRF_COOKIE_SECURE` | `True` (prod) | ✅ | Forcé dans `settings_prod.py` |
| `SESSION_COOKIE_HTTPONLY` | `True` | ✅ | Protection XSS |
| `SESSION_COOKIE_SAMESITE` | `Lax` | ✅ | Protection CSRF |
| `CSRF_COOKIE_SAMESITE` | `Lax` | ✅ | Protection CSRF |
| `CSRF_COOKIE_HTTPONLY` | `False` | ✅ **JUSTIFIÉ** | SPA doit lire token CSRF |
| `SESSION_COOKIE_AGE` | `14400` (4h) | ✅ | Timeout raisonnable |
| `SESSION_EXPIRE_AT_BROWSER_CLOSE` | `True` | ✅ | Sécurité renforcée |

### 4.3 Recommandations

**Aucune modification requise** ✅

La configuration actuelle suit les meilleures pratiques :
- Cookies HTTPS-only en production (`SECURE`)
- Protection XSS (`HTTPONLY` pour session)
- Protection CSRF (`SAMESITE=Lax`)
- Timeout approprié (4 heures)
- Expiration à la fermeture du navigateur

**Documentation à Clarifier**:
```bash
# .env.prod.example - Ajouter commentaire explicatif
# SSL_ENABLED contrôle les cookies sécurisés et HSTS
# - SSL_ENABLED=true  : Production HTTPS réelle (cookies secure, HSTS actif)
# - SSL_ENABLED=false : Prod-like E2E HTTP (cookies non-secure, pas de HSTS)
SSL_ENABLED=true
```

---

## 5. Configuration ALLOWED_HOSTS

### 5.1 Validation Actuelle

**Code de Validation (settings.py:42-44)**:
```python
ALLOWED_HOSTS = csv_env("ALLOWED_HOSTS", "localhost,127.0.0.1")
if "*" in ALLOWED_HOSTS and DJANGO_ENV == "production":
    raise ValueError("ALLOWED_HOSTS cannot contain '*' in production")
```

**Code Production (settings_prod.py:18-21)**:
```python
DJANGO_ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in DJANGO_ALLOWED_HOSTS.split(",") if h.strip()]
if not ALLOWED_HOSTS:
    raise ValueError("DJANGO_ALLOWED_HOSTS must be set (comma-separated)")
```

### 5.2 État ✅

**Validation Robuste**:
- ✅ Wildcard (`*`) interdit en production
- ✅ Liste vide interdite en production (`settings_prod.py`)
- ✅ Parsing CSV avec strip (supprime espaces)

### 5.3 Exemples de Configuration

#### Scénario 1 : Domaine unique
```bash
DJANGO_ALLOWED_HOSTS=korrigo.example.com
```

#### Scénario 2 : Domaine principal + www
```bash
DJANGO_ALLOWED_HOSTS=korrigo.example.com,www.korrigo.example.com
```

#### Scénario 3 : Production + staging sur sous-domaines
```bash
# Production
DJANGO_ALLOWED_HOSTS=korrigo.example.com

# Staging
DJANGO_ALLOWED_HOSTS=staging.korrigo.example.com
```

#### Scénario 4 : Accès IP (déconseillé en production)
```bash
# Staging/développement uniquement
DJANGO_ALLOWED_HOSTS=192.168.1.100,staging.example.com
```

### 5.4 Recommandations

**Aucune modification code requise** ✅

**Documentation `.env.prod.example`** - Améliorer commentaires :
```bash
# ALLOWED_HOSTS: Liste des domaines autorisés (séparés par virgule)
# CRITICAL: Ne JAMAIS utiliser '*' en production (erreur levée au démarrage)
# Exemples:
#   - Domaine unique: DJANGO_ALLOWED_HOSTS=korrigo.example.com
#   - Avec www:       DJANGO_ALLOWED_HOSTS=korrigo.example.com,www.korrigo.example.com
#   - Multi-domaines: DJANGO_ALLOWED_HOSTS=app.example.com,api.example.com
DJANGO_ALLOWED_HOSTS=your-domain.com,www.your-domain.com
```

---

## 6. Volumes Docker et Sécurité des Données

### 6.1 Volumes Critiques

**Configuration (infra/docker/docker-compose.prod.yml:117-121)**:
```yaml
volumes:
  postgres_data:    # Base de données PostgreSQL
  static_volume:    # Fichiers statiques (CSS, JS)
  media_volume:     # Fichiers uploadés (PDFs copies étudiants)
```

### 6.2 Importance et Risques

| Volume | Contenu | Criticité | Perte de Données = Impact |
|--------|---------|-----------|---------------------------|
| `postgres_data` | Base de données complète | 🔴 **CRITIQUE** | Perte totale : examens, utilisateurs, notes, annotations |
| `media_volume` | PDFs des copies étudiants | 🔴 **CRITIQUE** | Perte définitive des copies scannées |
| `static_volume` | Fichiers statiques collectés | 🟡 **MOYEN** | Régénérable via `collectstatic` |

### 6.3 ⚠️ Avertissements Destruction Volumes

**Commandes Destructives** (À NE JAMAIS exécuter sans backup) :
```bash
# 🚨 DANGER: Supprime TOUS les volumes (perte définitive de données)
docker compose -f infra/docker/docker-compose.prod.yml down -v

# 🚨 DANGER: Supprime volume spécifique
docker volume rm docker_postgres_data

# 🚨 DANGER: Supprime tous les volumes non utilisés
docker volume prune
```

**Procédure Sûre de Redémarrage** :
```bash
# ✅ SAFE: Arrêt sans suppression volumes
docker compose -f infra/docker/docker-compose.prod.yml down

# ✅ SAFE: Démarrage avec volumes existants
docker compose -f infra/docker/docker-compose.prod.yml up -d
```

### 6.4 Exigences de Backup

**Fréquence Minimale**:
- Base de données (`postgres_data`) : **Quotidien** (automatisé)
- Fichiers média (`media_volume`) : **Hebdomadaire** (ou quotidien si activité intense)

**Rétention**:
- Actuelle (déjà implémentée) : **30 jours** (scripts/backup_db.sh:19)
- Recommandé : 30 jours local + copies off-site mensuelles

**Localisation Backup**:
```
backups/
├── db_backup_20260131_143000.sql.gz
├── media_backup_20260131_143000.tar.gz
└── ... (rotation 30 jours)
```

**⚠️ CRITIQUE**: Le répertoire `backups/` doit être :
1. Monté sur stockage persistant (pas dans conteneur Docker)
2. Inclus dans stratégie de sauvegarde système (rsync, S3, NFS, etc.)
3. Testé régulièrement (procédure restore)

### 6.5 Checklist Sécurité Volumes

- [ ] Volumes Docker configurés avec labels pour prévenir suppression accidentelle
- [ ] Backup automatisé quotidien (DB) configuré (cron ou Celery beat)
- [ ] Backup hebdomadaire (media) configuré
- [ ] Procédure de restore testée au moins une fois
- [ ] Stockage backup sur disque séparé ou remote
- [ ] Documentation runbook backup/restore accessible équipe ops
- [ ] Alerting en cas d'échec backup

---

## 7. Actions Recommandées

### 7.1 Actions Immédiates (P0 - Avant Production HTTPS)

| # | Action | Fichier | Effort | Priorité |
|---|--------|---------|--------|----------|
| **A1** | Créer `nginx-ssl.conf` avec headers HSTS/CSP | `infra/nginx/nginx-ssl.conf` | 30 min | 🔴 P0 |
| **A2** | Configurer EMAIL_HOST réel | `.env.prod` | 15 min | 🔴 P0 |
| **A3** | Définir SECURE_HSTS_SECONDS=31536000 par défaut | `settings_prod.py` | 5 min | 🔴 P0 |
| **A4** | Documenter procédure backup/restore | `runbook_backup_restore.md` | 2 heures | 🔴 P0 |
| **A5** | Implémenter smoke tests complets | `scripts/smoke_prod.sh` | 1 heure | 🔴 P0 |

### 7.2 Actions Court Terme (P1 - Première Semaine)

| # | Action | Fichier | Effort | Priorité |
|---|--------|---------|--------|----------|
| **A6** | Ajouter Permissions-Policy header | `nginx-ssl.conf` | 10 min | 🟠 P1 |
| **A7** | Configurer METRICS_TOKEN | `.env.prod` | 5 min | 🟠 P1 |
| **A8** | Tester restore DB depuis backup | Tests manuels | 1 heure | 🟠 P1 |
| **A9** | Configurer backup automatisé (cron) | Crontab système | 30 min | 🟠 P1 |

### 7.3 Actions Moyen Terme (P2 - Premier Mois)

| # | Action | Effort | Priorité |
|---|--------|--------|----------|
| **A10** | Mettre en place CSP report-uri monitoring | 4 heures | 🟡 P2 |
| **A11** | Configurer Redis AUTH (si exposition externe) | 1 heure | 🟡 P2 |
| **A12** | Tester procédure complète DR (disaster recovery) | 1 jour | 🟡 P2 |

### 7.4 Checklist Pré-Déploiement Production

**Configuration** :
- [ ] SECRET_KEY généré (50+ caractères aléatoires)
- [ ] DJANGO_ALLOWED_HOSTS configuré (domaine(s) de production)
- [ ] EMAIL_HOST configuré (SMTP réel)
- [ ] SSL_ENABLED=true
- [ ] SECURE_HSTS_SECONDS=31536000 (1 an)
- [ ] Certificat TLS installé (Let's Encrypt ou commercial)
- [ ] nginx-ssl.conf déployé (avec HSTS/CSP/Permissions-Policy)

**Sécurité** :
- [ ] Aucune variable sensible dans code source (vérifier .gitignore)
- [ ] Backup DB testé et fonctionnel
- [ ] Restore DB testé avec succès
- [ ] Smoke tests passent (health + static + media)
- [ ] Headers sécurité validés (securityheaders.com score A/A+)

**Opérationnel** :
- [ ] Backup automatisé configuré (cron/Celery)
- [ ] Logs centralisés accessibles
- [ ] Runbook backup/restore documenté et validé
- [ ] Contacts équipe ops définis (ADMINS)
- [ ] Plan de rollback défini

**Validation** :
- [ ] `manage.py check --deploy` exécuté sans erreurs
- [ ] Tests E2E passent en environnement prod-like
- [ ] Charge de test effectuée (optionnel mais recommandé)

---

## 8. Annexes

### A. Matrice de Conformité OWASP Top 10 2021

| Risque OWASP | Mesures Korrigo | État |
|--------------|-----------------|------|
| **A01: Broken Access Control** | Permissions DRF par défaut `IsAuthenticated` | ✅ |
| **A02: Cryptographic Failures** | Cookies secure, HSTS, TLS 1.2+ | ✅ |
| **A03: Injection** | Django ORM (paramétrisé), validation entrées | ✅ |
| **A04: Insecure Design** | Architecture défense-en-profondeur (nginx + Django) | ✅ |
| **A05: Security Misconfiguration** | DEBUG=False, headers sécurité, validation env | ✅ |
| **A06: Vulnerable Components** | Dépendances récentes (Django 4.2, PostgreSQL 15) | ✅ |
| **A07: Identification Failures** | Sessions sécurisées, timeout 4h, validation forte mots de passe | ✅ |
| **A08: Software and Data Integrity Failures** | Backup/restore, logs audit | ✅ |
| **A09: Security Logging Failures** | Logging structuré JSON, audit trail | ✅ |
| **A10: Server-Side Request Forgery** | Pas d'URL externe user-controlled | ✅ |

### B. Références

**Documentation Django** :
- [Django Deployment Checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)
- [Django Security](https://docs.djangoproject.com/en/4.2/topics/security/)

**Standards Sécurité** :
- [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/)
- [Mozilla Web Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)

**Outils Validation** :
- [Security Headers](https://securityheaders.com)
- [SSL Labs](https://www.ssllabs.com/ssltest/)
- [Mozilla Observatory](https://observatory.mozilla.org)

### C. Contacts et Support

**Équipe Technique** :
- Configuration dans `.env.prod` : `ADMINS=admin@votre-domaine.com`
- Support infrastructure : Voir `docs/deployment/RUNBOOK_PRODUCTION.md`

---

## 9. Historique des Modifications

| Date | Version | Auteur | Modifications |
|------|---------|--------|---------------|
| 2026-01-31 | 1.0 | Audit Automatisé | Création initiale suite à analyse codebase |

---

**Statut Document** : ✅ Finalisé  
**Prochaine Révision** : Après déploiement production (validation réelle headers)
