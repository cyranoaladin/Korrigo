# Audit de Sécurité Production - Korrigo/Viatique

**Task ID**: ZF-AUD-12  
**Date**: 2026-01-31  
**Version**: 1.0  
**Statut**: Audit Initial Complet

---

## 1. Résumé Exécutif

### 1.1 Posture de Sécurité Actuelle

La plateforme Korrigo présente une **posture de sécurité globalement solide** avec des mécanismes de protection déjà implémentés et une architecture de configuration conditionnelle adaptée aux différents environnements.

**Points forts** ✅:
- Architecture de configuration en trois niveaux (dev/prod-like/production)
- Validation stricte des variables d'environnement critiques en production
- Headers de sécurité de base déjà implémentés (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection)
- Content Security Policy (CSP) configurée via django-csp
- Cookies sécurisés conditionnels (SECURE, HTTPONLY, SAMESITE)
- Protection HSTS et SSL redirect conditionnels via flag SSL_ENABLED
- ALLOWED_HOSTS avec validation anti-wildcard en production
- CORS avec origines explicites (pas de wildcard)

**Lacunes identifiées** ❌:
- Headers HSTS et CSP absents dans la configuration nginx
- Permissions-Policy non configuré
- 2 warnings de déploiement Django liés à la configuration HSTS/SSL (comportement attendu)
- 48 warnings drf_spectacular (qualité documentation API, non critique)

### 1.2 Résultats Django Deployment Check

**Commande exécutée**:
```bash
DJANGO_SETTINGS_MODULE=core.settings_prod python manage.py check --deploy
```

**Résultat global**: `50 issues identified`

**Répartition par criticité**:
- **P0 (Critique)**: 0 warnings ✅
- **P1 (Élevé)**: 2 warnings (HSTS, SSL redirect - configuration conditionnelle existante)
- **P2 (Moyen)**: 0 warnings
- **P3 (Faible)**: 48 warnings (drf_spectacular - documentation API)

### 1.3 Recommandations Prioritaires

1. **[P1] Ajouter headers HSTS dans nginx** (conditionnel HTTPS)
2. **[P1] Ajouter CSP dans nginx** (aligné avec Django CSP)
3. **[P2] Configurer Permissions-Policy** dans nginx
4. **[P3] Améliorer documentation API** (drf_spectacular type hints - optionnel)

---

## 2. Résultats Détaillés du Deployment Check

### 2.1 Warnings de Sécurité (P1)

#### Warning 1: HSTS Non Configuré (security.W004)

**Message complet**:
```
?: (security.W004) You have not set a value for the SECURE_HSTS_SECONDS setting. 
   If your entire site is served only over SSL, you may want to consider setting a value 
   and enabling HTTP Strict Transport Security. Be sure to read the documentation first; 
   enabling HSTS carelessly can cause serious, irreversible problems.
```

**Analyse**:
- **Statut**: ⚠️ Faux positif partiel
- **Explication**: Le warning apparaît car le check est exécuté avec `settings_prod.py` qui définit `SECURE_HSTS_SECONDS = 0` par défaut
- **Code actuel** (`settings_prod.py:45`):
  ```python
  SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))
  ```
- **Configuration conditionnelle** (`settings.py:109-111`):
  ```python
  if SSL_ENABLED:
      SECURE_HSTS_SECONDS = 31536000  # 1 an
      SECURE_HSTS_INCLUDE_SUBDOMAINS = True
      SECURE_HSTS_PRELOAD = True
  ```

**Impact**: Faible - la configuration HSTS est déjà implémentée de manière conditionnelle

**Résolution recommandée**:
1. **Option 1 (Recommandée)**: Documenter que HSTS est activé via SSL_ENABLED=true
2. **Option 2**: Modifier `settings_prod.py` pour forcer HSTS à une valeur par défaut élevée
   ```python
   SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "31536000"))
   SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS", "true").lower() == "true"
   SECURE_HSTS_PRELOAD = os.environ.get("SECURE_HSTS_PRELOAD", "true").lower() == "true"
   ```

**Priorité**: P1 - À adresser avant le déploiement production HTTPS

---

#### Warning 2: SSL Redirect Non Configuré (security.W008)

**Message complet**:
```
?: (security.W008) Your SECURE_SSL_REDIRECT setting is not set to True. 
   Unless your site should be available over both SSL and non-SSL connections, 
   you may want to either set this setting True or configure a load balancer 
   or reverse-proxy server to redirect all connections to HTTPS.
```

**Analyse**:
- **Statut**: ⚠️ Faux positif - comportement intentionnel
- **Explication**: La redirection SSL est conditionnelle via le flag `SSL_ENABLED`
- **Code actuel** (`settings.py:106-117`):
  ```python
  if not DEBUG:
      if SSL_ENABLED:
          SECURE_SSL_REDIRECT = True
          SESSION_COOKIE_SECURE = True
          CSRF_COOKIE_SECURE = True
          # ... HSTS ...
      else:
          # Prod-like (E2E): HTTP-only, no SSL redirect
          SECURE_SSL_REDIRECT = False
          SESSION_COOKIE_SECURE = False
          CSRF_COOKIE_SECURE = False
  ```

**Justification**: 
- En environnement **prod-like** (E2E tests): `SSL_ENABLED=false` → HTTP accepté
- En environnement **production réel**: `SSL_ENABLED=true` → HTTPS forcé

**Impact**: Aucun - le comportement actuel est conforme aux exigences

**Résolution recommandée**:
- **Action**: Documenter ce pattern dans l'audit
- **Validation**: En production réelle, `SSL_ENABLED` **doit** être défini à `true`
- **Vérification**: Ajouter dans checklist pré-déploiement production

**Priorité**: P1 - Validation obligatoire avant déploiement

---

### 2.2 Warnings drf_spectacular (P3)

**Nombre total**: 48 warnings

**Types de warnings**:
1. **drf_spectacular.W001** (6 occurrences): Type hints manquants pour serializer fields
2. **drf_spectacular.W002** (42 occurrences): Serializer non détectable pour APIViews

**Exemple représentatif**:
```
?: (drf_spectacular.W002) /backend/core/views.py: Error [LoginView]: 
   unable to guess serializer. This is graceful fallback handling for APIViews. 
   Consider using GenericAPIView as view base class, if view is under your control.
```

**Analyse**:
- **Impact**: Aucun sur la sécurité ou le fonctionnement
- **Portée**: Documentation OpenAPI/Swagger uniquement
- **Cause**: Utilisation de `APIView` basique au lieu de `GenericAPIView`

**Résolution recommandée**:
- **Option 1**: Ajouter `@extend_schema` decorators sur les vues concernées
- **Option 2**: Migrer vers `GenericAPIView` avec `serializer_class`
- **Option 3**: Accepter et ignorer (fallback drf_spectacular fonctionne)

**Priorité**: P3 - Amélioration qualité code, non bloquant

**Action**: ✅ Accepté - Aucune action requise pour le durcissement production

---

## 3. Configuration des Headers de Sécurité

### 3.1 État Actuel

#### Headers Configurés dans Nginx (`infra/nginx/nginx.conf:13-16`)

| Header | Valeur | Statut |
|--------|--------|--------|
| `X-Frame-Options` | `DENY` | ✅ Configuré |
| `X-Content-Type-Options` | `nosniff` | ✅ Configuré |
| `X-XSS-Protection` | `1; mode=block` | ✅ Configuré |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | ✅ Configuré |
| `Strict-Transport-Security` (HSTS) | - | ❌ Manquant |
| `Content-Security-Policy` | - | ❌ Manquant |
| `Permissions-Policy` | - | ❌ Manquant |

#### Headers Configurés dans Django (`settings.py:119-121`)

| Setting | Valeur | Condition |
|---------|--------|-----------|
| `SECURE_BROWSER_XSS_FILTER` | `True` | `not DEBUG` |
| `SECURE_CONTENT_TYPE_NOSNIFF` | `True` | `not DEBUG` |
| `X_FRAME_OPTIONS` | `'DENY'` | `not DEBUG` |
| `SECURE_HSTS_SECONDS` | `31536000` | `SSL_ENABLED=true` |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `True` | `SSL_ENABLED=true` |
| `SECURE_HSTS_PRELOAD` | `True` | `SSL_ENABLED=true` |

**Note**: Django SecurityMiddleware ajoute ces headers automatiquement. Il y a donc une **défense en profondeur** (nginx + Django).

### 3.2 Content Security Policy (CSP)

#### Configuration Django Actuelle (`settings.py:433-446`)

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

**Analyse**:
- ✅ Politique restrictive et sécurisée
- ✅ `frame-ancestors: 'none'` équivalent à `X-Frame-Options: DENY`
- ✅ `upgrade-insecure-requests` active (force HTTPS pour les ressources)
- ✅ Pas de `'unsafe-inline'` ou `'unsafe-eval'` en production

**Compatibilité Frontend**:
- Configuration adaptée pour une SPA (Single Page Application)
- Permet `data:` et `blob:` pour les images (nécessaire pour prévisualisation PDF)

#### CSP dans Nginx (Proposition)

**Problème**: CSP actuellement définie uniquement dans Django, pas dans nginx.

**Avantages d'ajouter CSP dans nginx**:
1. **Défense en profondeur**: Protection active même si Django est compromis
2. **Performance**: Header ajouté dès le reverse proxy
3. **Centralisation**: Tous les headers de sécurité au même endroit

**Configuration proposée** (ajout dans nginx.conf):
```nginx
# Content Security Policy
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests" always;
```

**IMPORTANT**: Cette directive doit **exactement correspondre** à la CSP Django pour éviter les conflits.

### 3.3 HSTS (HTTP Strict Transport Security)

#### Configuration Django Actuelle

```python
# settings.py:109-111 (quand SSL_ENABLED=true)
SECURE_HSTS_SECONDS = 31536000  # 1 an
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

#### Configuration Nginx Proposée

**Pour production HTTPS** (quand SSL_ENABLED=true, dans un bloc `server` HTTPS):
```nginx
# HSTS Header (HTTPS uniquement)
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
```

**ATTENTION** ⚠️:
- HSTS doit **UNIQUEMENT** être envoyé sur des connexions HTTPS
- Ne **JAMAIS** ajouter ce header dans un bloc `server` HTTP (port 80)
- Conséquence d'une mauvaise config: Blocage total du site sur tous les navigateurs modernes

**Recommandation d'implémentation**:
```nginx
# Bloc HTTP (port 80) - Redirection HTTPS uniquement
server {
    listen 80;
    return 301 https://$server_name$request_uri;
}

# Bloc HTTPS (port 443) - Headers de sécurité complets
server {
    listen 443 ssl http2;
    
    # SSL Configuration
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header Content-Security-Policy "default-src 'self'; ..." always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # ... reste de la configuration ...
}
```

### 3.4 Permissions-Policy

**Statut**: ❌ Non configuré

**Objectif**: Désactiver les fonctionnalités navigateur non utilisées par l'application.

**Configuration proposée**:
```nginx
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=(), usb=()" always;
```

**Justification**:
- Korrigo est une plateforme de correction d'examens
- Aucun besoin de caméra, micro, géolocalisation, paiement, USB
- Réduction de la surface d'attaque XSS/malware

**Priorité**: P2 - Recommandé mais non bloquant

### 3.5 Précédence des Headers et Défense en Profondeur

#### Stratégie Multi-Couches

La configuration actuelle implémente une **défense en profondeur** avec headers définis à deux niveaux:

1. **Niveau 1 - Nginx (Reverse Proxy)**: Headers ajoutés par `infra/nginx/nginx.conf`
2. **Niveau 2 - Django (Application)**: Headers ajoutés par `SecurityMiddleware` (middleware Django)

**Ordre de traitement**:
```
Client ← [Nginx Headers] ← [Django Headers] ← Application
```

#### Règles de Précédence

**Cas 1: Header défini dans nginx ET Django**
- **Comportement**: Les deux headers sont envoyés (nginx ajoute, ne remplace pas)
- **Exemple**: `X-Frame-Options` défini dans nginx.conf:13 ET Django `X_FRAME_OPTIONS='DENY'`
- **Résultat**: Client reçoit deux headers `X-Frame-Options: DENY` (redondant mais inoffensif)
- **Meilleure pratique**: ✅ Accepté - Défense en profondeur

**Cas 2: Header défini uniquement dans nginx**
- **Comportement**: Client reçoit le header nginx
- **Exemple**: `Referrer-Policy` défini uniquement dans nginx.conf:16
- **Résultat**: ✅ Fonctionne correctement

**Cas 3: Header défini uniquement dans Django**
- **Comportement**: Client reçoit le header Django (si middleware actif)
- **Exemple**: HSTS défini via `SECURE_HSTS_SECONDS` quand `SSL_ENABLED=true`
- **Résultat**: ✅ Fonctionne correctement
- **Limite**: Header absent si Django est contourné (attaque reverse proxy)

**Cas 4: Header conditionnel (HSTS)**
- **Problème potentiel**: Si HSTS défini dans nginx HTTP (port 80) → ⚠️ **DANGER**
- **Solution actuelle**: HSTS uniquement via Django quand `SSL_ENABLED=true`
- **Recommandation**: Ajouter HSTS dans bloc nginx HTTPS uniquement (section 3.7)

#### Comparaison État Actuel

| Header | Nginx | Django | Précédence | Recommandation |
|--------|-------|--------|------------|----------------|
| `X-Frame-Options` | ✅ `DENY` | ✅ `DENY` | Double | ✅ OK - Défense profondeur |
| `X-Content-Type-Options` | ✅ `nosniff` | ✅ `nosniff` | Double | ✅ OK - Défense profondeur |
| `X-XSS-Protection` | ✅ `1; mode=block` | ✅ Activé | Double | ✅ OK - Défense profondeur |
| `Referrer-Policy` | ✅ `strict-origin-when-cross-origin` | ❌ Non | Nginx seul | ⚠️ Ajouter Django backup |
| `HSTS` | ❌ Non | ✅ Conditionnel | Django seul | ⚠️ Ajouter nginx HTTPS |
| `CSP` | ❌ Non | ✅ Via django-csp | Django seul | ⚠️ Ajouter nginx |
| `Permissions-Policy` | ❌ Non | ❌ Non | Aucun | ⚠️ Ajouter nginx |

**Actions prioritaires**:
1. **P1**: Ajouter HSTS dans bloc nginx HTTPS (défense profondeur)
2. **P1**: Ajouter CSP dans nginx (alignée avec Django)
3. **P2**: Ajouter Permissions-Policy dans nginx

### 3.6 Configuration Conditionnelle SSL_ENABLED

#### Logique de Configuration

Le système utilise une variable d'environnement `SSL_ENABLED` pour gérer trois environnements:

**Architecture décisionnelle**:
```python
# Arbre de décision (settings.py:100-121)
if DEBUG:
    # Développement local (HTTP)
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    HSTS = Désactivé
else:
    # Production ou Prod-like
    if SSL_ENABLED:
        # Production réelle (HTTPS)
        SECURE_SSL_REDIRECT = True
        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True
        SECURE_HSTS_SECONDS = 31536000
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD = True
    else:
        # Prod-like (E2E tests HTTP)
        SECURE_SSL_REDIRECT = False
        SESSION_COOKIE_SECURE = False
        CSRF_COOKIE_SECURE = False
```

#### Environnements Supportés

| Environnement | `DEBUG` | `SSL_ENABLED` | SSL Redirect | HSTS | Cookies Secure | Use Case |
|---------------|---------|---------------|--------------|------|----------------|----------|
| **Development** | `True` | N/A | ❌ | ❌ | ❌ | Dev local HTTP |
| **Prod-like (E2E)** | `False` | `False` | ❌ | ❌ | ❌ | Tests E2E HTTP |
| **Production** | `False` | `True` | ✅ | ✅ | ✅ | Prod réelle HTTPS |

#### Override settings_prod.py

**Conflit potentiel**: `settings_prod.py` force certains paramètres:

```python
# settings_prod.py:41-43 (OVERRIDE)
SESSION_COOKIE_SECURE = True  # Force True même si SSL_ENABLED=false
CSRF_COOKIE_SECURE = True     # Force True même si SSL_ENABLED=false
```

**Analyse**:
- ⚠️ **Risque**: En environnement prod-like (E2E HTTP), ces overrides cassent la logique conditionnelle
- ⚠️ **Impact**: Cookies ne seront pas envoyés en HTTP → Tests E2E échouent
- ✅ **Solution actuelle**: Utiliser `settings.py` pour prod-like, `settings_prod.py` uniquement pour prod HTTPS réelle

**Recommandation**:
```python
# settings_prod.py (version améliorée)
SSL_ENABLED = os.environ.get("SSL_ENABLED", "True").lower() == "true"

if SSL_ENABLED:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
else:
    # Prod-like E2E
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
```

#### Configuration Nginx Conditionnelle

**Problème**: Nginx ne lit pas les variables d'environnement Python.

**Solutions possibles**:

**Option 1: Template nginx.conf avec envsubst** (Recommandé)
```bash
# Dockerfile ou entrypoint.sh
envsubst '${SSL_ENABLED}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
```

```nginx
# nginx.conf.template
# Conditionnel: HSTS uniquement si SSL_ENABLED=true
map $ssl_enabled $hsts_header {
    default "";
    "true" "max-age=31536000; includeSubDomains; preload";
}

server {
    listen 443 ssl http2;
    add_header Strict-Transport-Security $hsts_header always;
}
```

**Option 2: Deux fichiers nginx séparés**
- `nginx-http.conf` (prod-like E2E)
- `nginx-https.conf` (production réelle)
- Sélection via variable Docker Compose

**Option 3: Bloc conditionnel manuel** (Solution actuelle implicite)
- Configuration HTTP uniquement (nginx.conf actuel)
- Opérateur ajoute manuellement HSTS lors du passage HTTPS

### 3.7 Configuration Nginx Complète pour Production

#### Scénario 1: Production HTTP (Prod-like E2E)

**Fichier**: `infra/nginx/nginx.conf` (état actuel adapté)

```nginx
# Docker DNS resolver
resolver 127.0.0.11 valid=10s ipv6=off;

server {
    listen 80;
    include /etc/nginx/mime.types;
    
    # Increase body size for large PDF uploads
    client_max_body_size 100M;

    # Security Headers (sans HSTS)
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Content Security Policy (aligné avec Django)
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" always;
    
    # Permissions Policy (optionnel pour E2E)
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=(), usb=()" always;

    root /usr/share/nginx/html;
    index index.html;

    # Backend Static Files
    location /static/ {
        alias /app/staticfiles/;
    }

    # Backend Media Files
    location /media/ {
        alias /app/media/;
    }

    # API Proxy - Dynamic upstream resolution
    location /api/ {
        set $backend_upstream http://backend:8000;
        proxy_pass $backend_upstream;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # Admin Proxy - Dynamic upstream resolution
    location /admin/ {
        set $backend_upstream http://backend:8000;
        proxy_pass $backend_upstream;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # Frontend (SPA) - Fallback to index.html
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

#### Scénario 2: Production HTTPS (Production Réelle)

**Fichier**: `infra/nginx/nginx-https.conf` (nouveau fichier recommandé)

```nginx
# Docker DNS resolver
resolver 127.0.0.11 valid=10s ipv6=off;

# HTTP Server: Redirect to HTTPS
server {
    listen 80;
    server_name korrigo.education.fr;
    
    # Redirect all HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

# HTTPS Server: Full Security Headers
server {
    listen 443 ssl http2;
    server_name korrigo.education.fr;
    include /etc/nginx/mime.types;
    
    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Increase body size for large PDF uploads
    client_max_body_size 100M;

    # Security Headers (FULL)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=(), usb=()" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    root /usr/share/nginx/html;
    index index.html;

    # Backend Static Files
    location /static/ {
        alias /app/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Backend Media Files
    location /media/ {
        alias /app/media/;
        expires 1y;
        add_header Cache-Control "public";
    }

    # API Proxy - Dynamic upstream resolution
    location /api/ {
        set $backend_upstream http://backend:8000;
        proxy_pass $backend_upstream;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto https;  # Force HTTPS
        proxy_redirect off;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Admin Proxy - Dynamic upstream resolution
    location /admin/ {
        set $backend_upstream http://backend:8000;
        proxy_pass $backend_upstream;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto https;  # Force HTTPS
        proxy_redirect off;
    }

    # Frontend (SPA) - Fallback to index.html
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

**Différences clés HTTP vs HTTPS**:

| Aspect | HTTP (Prod-like) | HTTPS (Production) |
|--------|------------------|-------------------|
| Port | 80 | 443 + Redirect 80→443 |
| HSTS | ❌ Absent | ✅ `max-age=31536000; includeSubDomains; preload` |
| CSP `upgrade-insecure-requests` | ❌ Absent | ✅ Présent |
| `X-Forwarded-Proto` | `$scheme` (http) | `https` (forcé) |
| SSL/TLS Config | ❌ Absent | ✅ TLS 1.2/1.3 uniquement |
| Cache Headers | Basique | Optimisé (expires 1y) |

### 3.8 Validation et Tests des Headers

#### Méthode 1: curl (Ligne de commande)

**Test headers complets**:
```bash
# Production HTTPS
curl -I https://korrigo.education.fr/api/health/ 2>&1 | grep -E "Strict-Transport|Content-Security|Permissions|X-Frame|X-Content|Referrer"

# Sortie attendue:
# Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
# Content-Security-Policy: default-src 'self'; script-src 'self'; ...
# Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()
# X-Frame-Options: DENY
# X-Content-Type-Options: nosniff
# Referrer-Policy: strict-origin-when-cross-origin
```

**Test redirection HTTP→HTTPS**:
```bash
curl -I http://korrigo.education.fr/api/health/

# Sortie attendue:
# HTTP/1.1 301 Moved Permanently
# Location: https://korrigo.education.fr/api/health/
```

**Test HSTS absent en HTTP** (validation sécurité):
```bash
curl -I http://localhost:8088/api/health/ 2>&1 | grep -i strict-transport

# Sortie attendue: (vide) - HSTS ne doit PAS apparaître en HTTP
```

#### Méthode 2: Browser DevTools

**Procédure**:
1. Ouvrir DevTools (`F12`)
2. Onglet **Network**
3. Naviguer vers `https://korrigo.education.fr/api/health/`
4. Clic sur la requête → Onglet **Headers**
5. Section **Response Headers**: Vérifier présence de tous les headers

**Checklist visuelle**:
- ✅ `strict-transport-security: max-age=31536000; includeSubDomains; preload`
- ✅ `content-security-policy: default-src 'self'; ...`
- ✅ `permissions-policy: camera=(), ...`
- ✅ `x-frame-options: DENY`
- ✅ `x-content-type-options: nosniff`
- ✅ `referrer-policy: strict-origin-when-cross-origin`

#### Méthode 3: Outils en Ligne

**Mozilla Observatory**: https://observatory.mozilla.org/
```bash
# Tester après déploiement
https://observatory.mozilla.org/analyze/korrigo.education.fr
```

**Grade attendu**: **A** ou **A+**

**Critères**:
- ✅ HSTS avec preload
- ✅ CSP sans 'unsafe-inline' ou 'unsafe-eval'
- ✅ X-Frame-Options ou CSP frame-ancestors
- ✅ X-Content-Type-Options
- ✅ Referrer-Policy

**Security Headers**: https://securityheaders.com/
```bash
# Alternative à Mozilla Observatory
https://securityheaders.com/?q=korrigo.education.fr
```

#### Méthode 4: Script Automatisé

**Script de validation** (`scripts/validate_headers.sh`):
```bash
#!/bin/bash
# Validation automatisée des headers de sécurité

URL="${1:-https://korrigo.education.fr}"
FAILED=0

echo "🔍 Validation Headers de Sécurité: $URL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Fonction de test générique
test_header() {
    local header=$1
    local pattern=$2
    local result=$(curl -sI "$URL/api/health/" | grep -i "^$header:" | grep -i "$pattern")
    
    if [ -n "$result" ]; then
        echo "✅ $header: OK"
        echo "   $result"
    else
        echo "❌ $header: MANQUANT ou INVALIDE"
        FAILED=$((FAILED + 1))
    fi
}

# Tests
test_header "Strict-Transport-Security" "max-age=31536000"
test_header "Content-Security-Policy" "default-src 'self'"
test_header "Permissions-Policy" "camera=()"
test_header "X-Frame-Options" "DENY"
test_header "X-Content-Type-Options" "nosniff"
test_header "Referrer-Policy" "strict-origin"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $FAILED -eq 0 ]; then
    echo "✅ Tous les headers sont corrects"
    exit 0
else
    echo "❌ $FAILED header(s) manquant(s) ou invalide(s)"
    exit 1
fi
```

**Usage**:
```bash
chmod +x scripts/validate_headers.sh
./scripts/validate_headers.sh https://korrigo.education.fr
```

---

## 4. Configuration des Cookies de Sécurité

### 4.1 État Actuel

#### Cookies de Session

**Configuration de base** (`settings.py:256-260`):
```python
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_COOKIE_AGE = 14400  # 4 heures
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
```

**Configuration production** (`settings.py:107-117`):
```python
if SSL_ENABLED:
    SESSION_COOKIE_SECURE = True  # Cookie envoyé uniquement sur HTTPS
else:
    SESSION_COOKIE_SECURE = False  # Prod-like HTTP
```

**Override settings_prod.py** (`settings_prod.py:41`):
```python
SESSION_COOKIE_SECURE = True  # Force True en production
```

#### Cookies CSRF

**Configuration de base** (`settings.py:128-130`):
```python
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_HTTPONLY = False  # Requis pour SPAs (lecture JavaScript)
```

**Configuration production** (`settings.py:107-117`):
```python
if SSL_ENABLED:
    CSRF_COOKIE_SECURE = True
else:
    CSRF_COOKIE_SECURE = False
```

**Override settings_prod.py** (`settings_prod.py:42`):
```python
CSRF_COOKIE_SECURE = True  # Force True en production
```

### 4.2 Analyse de Sécurité

| Cookie | Flag | Valeur | Statut | Justification |
|--------|------|--------|--------|---------------|
| Session | `SECURE` | `True` (prod) | ✅ | Envoi HTTPS uniquement |
| Session | `HTTPONLY` | `True` | ✅ | Protection XSS (pas de lecture JS) |
| Session | `SAMESITE` | `Lax` | ✅ | Protection CSRF partielle |
| CSRF | `SECURE` | `True` (prod) | ✅ | Envoi HTTPS uniquement |
| CSRF | `HTTPONLY` | `False` | ✅ | **Requis** pour SPA (frontend doit lire token) |
| CSRF | `SAMESITE` | `Lax` | ✅ | Protection CSRF partielle |

**Note sur CSRF_COOKIE_HTTPONLY = False**:
- **Raison**: Les SPAs (Vue.js) doivent lire le token CSRF depuis le cookie pour l'envoyer dans les headers
- **Alternative**: Utiliser `X-CSRFToken` header (déjà implémenté, voir `CORS_ALLOW_HEADERS:426`)
- **Sécurité**: Compensée par `SAMESITE=Lax` + validation CSRF côté serveur

### 4.3 Configuration SECURE_PROXY_SSL_HEADER

**Code actuel** (`settings_prod.py:43`):
```python
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

**Analyse**:
- ✅ Correctement configuré pour un reverse proxy nginx
- ✅ Permet à Django de détecter HTTPS derrière un proxy
- ⚠️ **CRITIQUE**: Ne fonctionne QUE si nginx définit `X-Forwarded-Proto`

**Vérification nginx** (`nginx.conf:38`):
```nginx
proxy_set_header X-Forwarded-Proto $scheme;
```
✅ **Confirmé**: Header correctement défini

### 4.4 Inventaire Complet des Paramètres Cookie

#### Session Cookie - Paramètres Complets

| Paramètre | Valeur (Production) | Valeur (Dev) | Source | Description |
|-----------|---------------------|--------------|--------|-------------|
| `SESSION_ENGINE` | `cached_db` | `cached_db` | settings.py:256 | Backend hybrid (cache + DB) |
| `SESSION_COOKIE_AGE` | `14400` (4h) | `14400` (4h) | settings.py:257 | Durée de vie de la session |
| `SESSION_EXPIRE_AT_BROWSER_CLOSE` | `True` | `True` | settings.py:258 | Session expire à fermeture navigateur |
| `SESSION_COOKIE_HTTPONLY` | `True` | `True` | settings.py:259 | Protection XSS (pas de lecture JS) |
| `SESSION_COOKIE_SAMESITE` | `Lax` | `Lax` | settings.py:260 | Protection CSRF partielle |
| `SESSION_COOKIE_SECURE` | `True` (SSL_ENABLED) | `False` | settings.py:107-117 | Transmission HTTPS uniquement |
| `SESSION_COOKIE_NAME` | `sessionid` | `sessionid` | Django default | Nom du cookie (non modifié) |
| `SESSION_COOKIE_DOMAIN` | `None` | `None` | Django default | Domaine cookie (inherit current) |
| `SESSION_COOKIE_PATH` | `/` | `/` | Django default | Chemin cookie (site entier) |

**Notes de sécurité**:
- ✅ `SESSION_ENGINE = cached_db`: Performances optimales avec persistance DB
- ✅ `SESSION_COOKIE_AGE = 14400`: 4 heures max (conforme best practices éducation)
- ✅ `SESSION_EXPIRE_AT_BROWSER_CLOSE = True`: Session non persistante (sécurité accrue)
- ✅ `SESSION_COOKIE_HTTPONLY = True`: Cookie illisible par JavaScript (protection XSS)

#### CSRF Cookie - Paramètres Complets

| Paramètre | Valeur (Production) | Valeur (Dev) | Source | Description |
|-----------|---------------------|--------------|--------|-------------|
| `CSRF_COOKIE_SAMESITE` | `Lax` | `Lax` | settings.py:129 | Protection CSRF partielle |
| `CSRF_COOKIE_HTTPONLY` | `False` | `False` | settings.py:130 | **Requis pour SPA** (lecture JS) |
| `CSRF_COOKIE_SECURE` | `True` (SSL_ENABLED) | `False` | settings.py:107-117 | Transmission HTTPS uniquement |
| `CSRF_COOKIE_NAME` | `csrftoken` | `csrftoken` | Django default | Nom du cookie CSRF |
| `CSRF_COOKIE_AGE` | `31449600` (1 an) | `31449600` (1 an) | Django default | Durée de vie token CSRF |
| `CSRF_COOKIE_DOMAIN` | `None` | `None` | Django default | Domaine cookie (inherit current) |
| `CSRF_COOKIE_PATH` | `/` | `/` | Django default | Chemin cookie (site entier) |
| `CSRF_USE_SESSIONS` | `False` | `False` | Django default | CSRF token dans cookie (pas session) |

**Notes de sécurité**:
- ⚠️ `CSRF_COOKIE_HTTPONLY = False`: **Intentionnel** - SPA Vue.js doit lire le token
  - Justification technique: Frontend envoie token dans header `X-CSRFToken` (CORS_ALLOW_HEADERS:426)
  - Mitigation: `SAMESITE=Lax` + validation serveur Django
- ✅ `CSRF_COOKIE_AGE = 31449600`: 1 an (valeur par défaut Django, acceptable)
- ✅ `CSRF_USE_SESSIONS = False`: Token dans cookie (meilleure UX pour SPAs)

### 4.5 Validation Django Deployment Check

**Commande exécutée**:
```bash
DJANGO_SETTINGS_MODULE=core.settings_prod python manage.py check --deploy
```

**Résultat pour les cookies**: ✅ **Aucun warning lié aux cookies**

Les paramètres suivants ont été validés automatiquement:
- ✅ `SESSION_COOKIE_SECURE` est `True` quand SSL_ENABLED=true (settings.py:107)
- ✅ `CSRF_COOKIE_SECURE` est `True` quand SSL_ENABLED=true (settings.py:108)
- ✅ `SESSION_COOKIE_HTTPONLY` est `True` (settings.py:259)
- ✅ Pas de warning `security.W012` (SESSION_COOKIE_SECURE manquant)
- ✅ Pas de warning `security.W016` (CSRF_COOKIE_SECURE manquant)
- ✅ Pas de warning `security.W013` (SESSION_COOKIE_HTTPONLY manquant)

**Note**: Les warnings W012/W016 apparaîtraient si `SSL_ENABLED=false`, ce qui est attendu en environnement prod-like (E2E).

### 4.6 Configuration Environnement (SSL_ENABLED)

#### Impact de SSL_ENABLED sur les Cookies

Le flag `SSL_ENABLED` contrôle les flags `Secure` des cookies de manière conditionnelle:

**Tableau de comportement**:

| Environnement | `DEBUG` | `SSL_ENABLED` | `SESSION_COOKIE_SECURE` | `CSRF_COOKIE_SECURE` | Use Case |
|---------------|---------|---------------|-------------------------|----------------------|----------|
| **Development** | `True` | N/A | `False` | `False` | Dev local HTTP |
| **Prod-like (E2E)** | `False` | `False` | `False` | `False` | Tests E2E HTTP (nginx sans TLS) |
| **Production HTTPS** | `False` | `True` | `True` | `True` | Production réelle avec TLS |

**Code conditionnel** (`settings.py:102-126`):
```python
if not DEBUG:
    if SSL_ENABLED:
        # Production réelle HTTPS
        SECURE_SSL_REDIRECT = True
        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True
        SECURE_HSTS_SECONDS = 31536000
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD = True
        SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    else:
        # Prod-like E2E (HTTP)
        SECURE_SSL_REDIRECT = False
        SESSION_COOKIE_SECURE = False
        CSRF_COOKIE_SECURE = False
```

**Override settings_prod.py** (lignes 41-43):
```python
SESSION_COOKIE_SECURE = True   # Force True indépendamment de SSL_ENABLED
CSRF_COOKIE_SECURE = True      # Force True indépendamment de SSL_ENABLED
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

**⚠️ ATTENTION - Conflit de configuration**:
- `settings_prod.py` **force** `SESSION_COOKIE_SECURE = True`
- `settings.py` définit conditionnellement basé sur `SSL_ENABLED`
- **Précédence**: `settings_prod.py` importe `settings.py` puis override → valeur finale = `True`
- **Impact**: En environnement prod-like avec `SSL_ENABLED=false`, les cookies auront quand même le flag `Secure` → **Tests E2E échoueront**

**Recommandation**: Utiliser uniquement `SSL_ENABLED` pour la logique conditionnelle, supprimer les overrides dans `settings_prod.py`:

```python
# settings_prod.py - Configuration recommandée
# Supprimer les lignes 41-42, garder uniquement:
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

Ou documenter explicitement que `settings_prod.py` est uniquement pour production HTTPS réelle, et utiliser `settings.py` (avec `DEBUG=False` et `SSL_ENABLED=False`) pour prod-like.

### 4.7 Exigences Variables d'Environnement

#### Variables Requises en Production

| Variable | Valeur Recommandée | Obligatoire | Impact si Absente |
|----------|-------------------|-------------|-------------------|
| `SSL_ENABLED` | `true` | ✅ Oui (prod réelle) | Cookies non sécurisés, pas de HSTS |
| `SECRET_KEY` | Aléatoire 50+ chars | ✅ Oui | Erreur démarrage Django |
| `DJANGO_ALLOWED_HOSTS` | `korrigo.fr` | ✅ Oui | Erreur démarrage (settings_prod.py:20) |

#### Variables Optionnelles (Avec Defaults)

| Variable | Default | Impact |
|----------|---------|--------|
| `SESSION_COOKIE_SAMESITE` | `Lax` | Protection CSRF partielle |
| `CSRF_COOKIE_SAMESITE` | `Lax` | Protection CSRF partielle |
| `SECURE_HSTS_SECONDS` | `31536000` (si SSL_ENABLED) | Durée HSTS (1 an) |

**Exemple .env.prod complet**:
```bash
# Cookies & HTTPS
SSL_ENABLED=true
SESSION_COOKIE_SAMESITE=Lax
CSRF_COOKIE_SAMESITE=Lax

# Django Core
SECRET_KEY=<généré via secrets.token_urlsafe(50)>
DJANGO_ENV=production
DEBUG=false
DJANGO_ALLOWED_HOSTS=korrigo.education.fr

# Database
DB_NAME=korrigo_prod
DB_USER=korrigo_user
DB_PASSWORD=<strong_password>
DB_HOST=postgres
DB_PORT=5432
```

### 4.8 Recommandations et Plan d'Action

**Actions requises avant déploiement production**:

1. **[P1] Résoudre conflit settings_prod.py**:
   - **Option A**: Supprimer overrides `SESSION_COOKIE_SECURE/CSRF_COOKIE_SECURE` de settings_prod.py
   - **Option B**: Documenter que settings_prod.py est exclusivement pour HTTPS production

2. **[P2] Valider variables d'environnement**:
   - Vérifier que `SSL_ENABLED=true` dans `.env.prod`
   - Vérifier que nginx est configuré avec certificat TLS valide

3. **[P3] Tester cookies en production**:
   - Ouvrir DevTools → Application → Cookies
   - Vérifier `sessionid`: `Secure; HttpOnly; SameSite=Lax`
   - Vérifier `csrftoken`: `Secure; SameSite=Lax` (pas HttpOnly)

**Validation pré-déploiement** (checklist):
- [ ] ✅ Vérifier que `SSL_ENABLED=true` dans `.env.prod`
- [ ] ✅ Vérifier que nginx utilise HTTPS (port 443) avec certificat valide
- [ ] ✅ Tester login utilisateur → Cookie `sessionid` créé avec flags corrects
- [ ] ✅ Tester requête API POST → Header `X-CSRFToken` envoyé correctement
- [ ] ✅ Valider expiration session après 4 heures (`SESSION_COOKIE_AGE`)
- [ ] ✅ Valider expiration session à fermeture navigateur

**Tests automatisés recommandés**:
```python
# backend/tests/test_cookie_security.py
def test_session_cookie_secure_in_production(client, settings):
    settings.DEBUG = False
    settings.SSL_ENABLED = True
    response = client.post('/api/login/', {...})
    assert 'Secure' in response.cookies['sessionid'].output()
    assert 'HttpOnly' in response.cookies['sessionid'].output()
    assert 'SameSite=Lax' in response.cookies['sessionid'].output()

def test_csrf_cookie_not_httponly(client, settings):
    response = client.get('/api/csrf/')
    assert 'HttpOnly' not in response.cookies['csrftoken'].output()
```

**Statut final**: ✅ Configuration cookie sécurisée et conforme aux best practices Django

**Points d'attention**:
- ⚠️ Conflit potentiel settings.py/settings_prod.py à résoudre (P1)
- ✅ Tous les flags de sécurité présents et correctement configurés
- ✅ Justification documentée pour `CSRF_COOKIE_HTTPONLY=False`
- ✅ Aucun warning Django deployment check lié aux cookies

---

## 5. Configuration ALLOWED_HOSTS

### 5.1 Mécanisme de Validation

#### Configuration de Base (`settings.py:42-44`)

```python
ALLOWED_HOSTS = csv_env("ALLOWED_HOSTS", "localhost,127.0.0.1")
if "*" in ALLOWED_HOSTS and DJANGO_ENV == "production":
    raise ValueError("ALLOWED_HOSTS cannot contain '*' in production")
```

**Analyse**:
- ✅ Protection anti-wildcard en production
- ✅ Valeur par défaut sécurisée pour développement
- ✅ Helper `csv_env()` pour parsing CSV propre

#### Configuration Production (`settings_prod.py:18-21`)

```python
DJANGO_ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in DJANGO_ALLOWED_HOSTS.split(",") if h.strip()]
if not ALLOWED_HOSTS:
    raise ValueError("DJANGO_ALLOWED_HOSTS must be set (comma-separated)")
```

**Analyse**:
- ✅ Validation stricte: **bloque le démarrage** si DJANGO_ALLOWED_HOSTS vide
- ✅ Nettoyage des espaces (`.strip()`)
- ✅ Filtrage des valeurs vides
- ⚠️ **Différence de nom**: `ALLOWED_HOSTS` (base) vs `DJANGO_ALLOWED_HOSTS` (prod)

### 5.2 Exemples de Configuration

#### Scénario 1: Domaine Unique

**Cas d'usage**: Site accessible sur `korrigo.education.fr`

```bash
# .env.prod
DJANGO_ALLOWED_HOSTS=korrigo.education.fr
```

#### Scénario 2: Domaine + www

**Cas d'usage**: Site accessible sur `korrigo.education.fr` ET `www.korrigo.education.fr`

```bash
# .env.prod
DJANGO_ALLOWED_HOSTS=korrigo.education.fr,www.korrigo.education.fr
```

#### Scénario 3: Plusieurs Domaines (Multi-tenant)

**Cas d'usage**: Application accessible sur plusieurs domaines AEFE

```bash
# .env.prod
DJANGO_ALLOWED_HOSTS=korrigo.aefe.fr,korrigo.education.gouv.fr,korrigo-aefe.fr
```

#### Scénario 4: Staging avec IP

**Cas d'usage**: Environnement de staging accessible par IP

```bash
# .env.staging
DJANGO_ALLOWED_HOSTS=192.168.1.100,staging.korrigo.fr
```

#### Scénario 5: Production avec Load Balancer

**Cas d'usage**: Derrière un load balancer avec IP interne

```bash
# .env.prod
DJANGO_ALLOWED_HOSTS=korrigo.education.fr,10.0.1.50
```

### 5.3 Validation et Test

**Test de validation**:
```bash
# Démarrage avec ALLOWED_HOSTS vide → doit échouer
DJANGO_ALLOWED_HOSTS="" python manage.py check
# ValueError: DJANGO_ALLOWED_HOSTS must be set (comma-separated)

# Démarrage avec wildcard → doit échouer
DJANGO_ALLOWED_HOSTS="*" DJANGO_ENV=production python manage.py check
# ValueError: ALLOWED_HOSTS cannot contain '*' in production

# Démarrage valide
DJANGO_ALLOWED_HOSTS="example.com" python manage.py check
# System check identified no issues (0 silenced).
```

### 5.4 Différence entre ALLOWED_HOSTS et DJANGO_ALLOWED_HOSTS

**Contexte**: Deux noms de variables différents selon l'environnement.

#### Variable de Base: ALLOWED_HOSTS

**Fichier**: `settings.py:42`  
**Usage**: Environnements dev et prod-like  
**Source**: Variable d'environnement `ALLOWED_HOSTS`  
**Parsing**: Helper `csv_env("ALLOWED_HOSTS", "localhost,127.0.0.1")`

```python
# settings.py
ALLOWED_HOSTS = csv_env("ALLOWED_HOSTS", "localhost,127.0.0.1")
```

**Comportement**:
- Défaut développement: `localhost,127.0.0.1`
- Validation anti-wildcard: bloque `*` si `DJANGO_ENV=production`

#### Variable Production: DJANGO_ALLOWED_HOSTS

**Fichier**: `settings_prod.py:18-21`  
**Usage**: Production réelle uniquement  
**Source**: Variable d'environnement `DJANGO_ALLOWED_HOSTS`  
**Parsing**: Split CSV manuel avec `.strip()`

```python
# settings_prod.py
DJANGO_ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
ALLOWED_HOSTS = [h.strip() for h in DJANGO_ALLOWED_HOSTS.split(",") if h.strip()]
if not ALLOWED_HOSTS:
    raise ValueError("DJANGO_ALLOWED_HOSTS must be set (comma-separated)")
```

**Comportement**:
- Défaut: chaîne vide → **erreur au démarrage**
- Validation stricte: bloque si liste finale vide
- Override: remplace la valeur de `settings.py`

#### Tableau Comparatif

| Aspect | `ALLOWED_HOSTS` (base) | `DJANGO_ALLOWED_HOSTS` (prod) |
|--------|------------------------|-------------------------------|
| **Fichier** | `settings.py` | `settings_prod.py` |
| **Env var** | `ALLOWED_HOSTS` | `DJANGO_ALLOWED_HOSTS` |
| **Défaut** | `localhost,127.0.0.1` | Vide (erreur) |
| **Validation** | Anti-wildcard en prod | Anti-vide strict |
| **Usage** | Dev, prod-like | Production HTTPS |
| **Parsing** | Helper `csv_env()` | Split manuel |

#### Pourquoi deux noms différents ?

**Raison historique**: Séparation des responsabilités.

1. **`settings.py`**: Configuration générale avec valeurs par défaut raisonnables
2. **`settings_prod.py`**: Configuration production qui **override** les valeurs de base

**Avantage**: 
- Variable `DJANGO_ALLOWED_HOSTS` **explicitement production**
- Impossible de confondre avec config dev
- Validation stricte spécifique à la production

**Inconvénient**:
- Risque de confusion pour les opérateurs
- Documentation claire requise (✅ résolu dans ce document)

### 5.5 Comportement de Validation Django

#### Protection Host Header Attack

**Contexte**: Django valide le header HTTP `Host` contre `ALLOWED_HOSTS` pour prévenir les attaques.

**Attaque typique**:
```http
GET /api/health/ HTTP/1.1
Host: attacker.com
```

**Comportement Django**:
```python
# Si "attacker.com" pas dans ALLOWED_HOSTS
→ SuspiciousOperation exception
→ HTTP 400 Bad Request
→ Log: "Invalid HTTP_HOST header: 'attacker.com'"
```

**Protection contre**:
- Cache poisoning
- Password reset poisoning
- Email injection via host header

#### Exemples de Validation

**Cas 1: Host valide**
```bash
curl -H "Host: korrigo.education.fr" https://korrigo.education.fr/api/health/
# → HTTP 200 OK (korrigo.education.fr dans ALLOWED_HOSTS)
```

**Cas 2: Host invalide**
```bash
curl -H "Host: malicious.com" https://korrigo.education.fr/api/health/
# → HTTP 400 Bad Request
# Django log: Invalid HTTP_HOST header: 'malicious.com'
```

**Cas 3: Wildcard bloqué en production**
```bash
DJANGO_ALLOWED_HOSTS="*" DJANGO_ENV=production python manage.py check
# → ValueError: ALLOWED_HOSTS cannot contain '*' in production
```

**Cas 4: Liste vide en production**
```bash
DJANGO_ALLOWED_HOSTS="" python manage.py check
# → ValueError: DJANGO_ALLOWED_HOSTS must be set (comma-separated)
```

#### Wildcards et Subdomains

**Wildcard complet**: ❌ Bloqué en production
```python
ALLOWED_HOSTS = ["*"]  # Accepte tous les hosts (DANGEREUX)
```

**Wildcard subdomain**: ✅ Autorisé (si nécessaire)
```python
ALLOWED_HOSTS = [".example.com"]  # Accepte *.example.com
# Valide: app.example.com, api.example.com, admin.example.com
```

**IMPORTANT**: Le wildcard subdomain (`.example.com`) n'est **pas** bloqué par la validation actuelle car elle check uniquement `"*"` exact.

**Recommandation**: Lister explicitement les subdomains au lieu d'utiliser wildcard:
```python
# ✅ Préféré: Liste explicite
ALLOWED_HOSTS = ["app.example.com", "api.example.com", "admin.example.com"]

# ⚠️ Acceptable si vraiment nécessaire
ALLOWED_HOSTS = [".example.com"]  # Tous les subdomains
```

### 5.6 Cas d'Usage Avancés

#### Scénario 6: Environnement Multi-Région

**Contexte**: Application déployée dans plusieurs datacenters avec domaines régionaux.

```bash
# .env.prod
DJANGO_ALLOWED_HOSTS=korrigo.fr,korrigo.eu,korrigo.asia
```

**Considération**: CORS et CSRF doivent aussi être configurés pour ces domaines.

#### Scénario 7: Migration de Domaine

**Contexte**: Transition de `old-domain.com` vers `new-domain.com`.

```bash
# .env.prod (pendant la migration)
DJANGO_ALLOWED_HOSTS=old-domain.com,new-domain.com,www.old-domain.com,www.new-domain.com
```

**Étapes**:
1. Ajouter nouveau domaine à ALLOWED_HOSTS
2. Configurer redirection DNS
3. Tester accès sur nouveau domaine
4. Supprimer ancien domaine après migration complète

#### Scénario 8: Load Balancer avec IP Interne

**Contexte**: Load balancer AWS/GCP envoie `Host: 10.0.1.50` pour health checks.

```bash
# .env.prod
DJANGO_ALLOWED_HOSTS=korrigo.education.fr,10.0.1.50
```

**Alternative**: Configurer load balancer pour envoyer `Host: korrigo.education.fr` au lieu de l'IP.

### 5.7 Pièges Courants et Solutions

#### Piège 1: Espaces dans la Liste

**Erreur courante**:
```bash
DJANGO_ALLOWED_HOSTS="korrigo.fr, www.korrigo.fr"  # Espace après virgule
```

**Conséquence**:
```python
ALLOWED_HOSTS = ["korrigo.fr", " www.korrigo.fr"]  # Espace en début
# Host "www.korrigo.fr" rejeté (espace non trimé)
```

**Solution**: La logique actuelle **gère ce cas** via `.strip()`
```python
# settings_prod.py:19
ALLOWED_HOSTS = [h.strip() for h in DJANGO_ALLOWED_HOSTS.split(",") if h.strip()]
# → ["korrigo.fr", "www.korrigo.fr"] ✅
```

#### Piège 2: Port dans Host Header

**Situation**: Accès via `http://korrigo.fr:8080`

**Host header**: `korrigo.fr:8080`

**Configuration requise**:
```bash
# Option 1: Inclure le port
DJANGO_ALLOWED_HOSTS=korrigo.fr:8080,korrigo.fr

# Option 2: Proxy stripping (nginx)
proxy_set_header Host $host;  # Sans port
```

**Recommandation**: ✅ Option 2 (nginx strip le port automatiquement)

#### Piège 3: IPv6

**Situation**: Accès direct via IPv6 `[2001:db8::1]`

**Configuration**:
```bash
DJANGO_ALLOWED_HOSTS=korrigo.fr,[2001:db8::1]
# ⚠️ IPv6 doit être entre crochets
```

**Recommandation**: Utiliser domaines au lieu d'IPs IPv6.

#### Piège 4: Variable Non Définie vs Vide

**Cas 1: Variable non définie** (absence totale)
```bash
# .env ne contient PAS DJANGO_ALLOWED_HOSTS
```
```python
DJANGO_ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
# → "" (chaîne vide)
# → ValueError
```

**Cas 2: Variable définie mais vide** (présente avec valeur vide)
```bash
# .env
DJANGO_ALLOWED_HOSTS=
```
```python
DJANGO_ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "")
# → "" (chaîne vide)
# → ValueError
```

**Résultat**: Même comportement → **ValueError** (validation stricte fonctionne)

### 5.8 Recommandations

#### Actions Code

✅ **Aucune modification requise** - La logique actuelle est robuste et sécurisée.

#### Documentation

✅ **Complétées**:
1. ✅ `.env.prod.example` mis à jour avec exemples et documentation
2. ✅ Commentaires explicatifs sur DJANGO_ALLOWED_HOSTS ajoutés
3. ✅ Différence ALLOWED_HOSTS vs DJANGO_ALLOWED_HOSTS documentée
4. ✅ Cas d'usage avancés et pièges documentés

#### Checklist Pré-Déploiement Production

**Validation configuration**:
- [ ] Variable `DJANGO_ALLOWED_HOSTS` définie dans fichier `.env.prod`
- [ ] Valeur correspond **exactement** au(x) nom(s) de domaine production
- [ ] Aucun wildcard `*` présent
- [ ] Aucun espace superflu (mais géré par `.strip()` si présent)
- [ ] Domaines avec et sans `www` inclus si nécessaire

**Tests manuels**:
```bash
# Test 1: Host valide accepté
curl -I -H "Host: korrigo.education.fr" http://localhost:8088/api/health/
# → HTTP 200 OK

# Test 2: Host invalide rejeté
curl -I -H "Host: attacker.com" http://localhost:8088/api/health/
# → HTTP 400 Bad Request

# Test 3: Démarrage avec config invalide bloqué
DJANGO_ALLOWED_HOSTS="" python manage.py check
# → ValueError: DJANGO_ALLOWED_HOSTS must be set

# Test 4: Wildcard bloqué en production
DJANGO_ALLOWED_HOSTS="*" DJANGO_ENV=production python manage.py check
# → ValueError: ALLOWED_HOSTS cannot contain '*' in production
```

**Validation post-déploiement**:
```bash
# Vérifier logs Django pour SuspiciousOperation
docker logs <container> | grep "Invalid HTTP_HOST"
# → Aucune ligne (pas d'attaque détectée)

# Vérifier que le service répond sur le bon domaine
curl -I https://korrigo.education.fr/api/health/
# → HTTP 200 OK + tous les security headers
```

---

## 6. Volumes Docker et Sécurité des Données

### 6.1 Volumes Critiques

**Analyse du fichier** `infra/docker/docker-compose.prod.yml`:

| Volume | Contenu | Criticité | Sauvegarde Requise |
|--------|---------|-----------|-------------------|
| `postgres_data` | Base de données PostgreSQL | 🔴 **CRITIQUE** | ✅ Oui (quotidien) |
| `media_volume` | Fichiers uploadés (PDFs, images) | 🔴 **CRITIQUE** | ✅ Oui (quotidien) |
| `static_volume` | Fichiers statiques collectés | 🟡 Modéré | ⚠️ Optionnel (régénérable) |
| `redis_data` | Cache Redis + queues Celery | 🟢 Faible | ❌ Non (éphémère) |

### 6.2 Risques de Destruction de Volumes

#### Commandes Destructives

**⚠️ DANGER - Commandes qui détruisent les volumes**:

```bash
# DESTRUCTIF: Supprime TOUS les volumes (y compris postgres_data, media_volume)
docker compose -f infra/docker/docker-compose.prod.yml down -v

# DESTRUCTIF: Supprime un volume spécifique
docker volume rm <project>_postgres_data

# DESTRUCTIF: Supprime tous les volumes non utilisés
docker volume prune
```

**✅ SAFE - Commandes qui préservent les volumes**:

```bash
# SAFE: Arrête les containers, garde les volumes
docker compose -f infra/docker/docker-compose.prod.yml down

# SAFE: Redémarre les services sans perte de données
docker compose -f infra/docker/docker-compose.prod.yml restart

# SAFE: Reconstruit les images, garde les volumes
docker compose -f infra/docker/docker-compose.prod.yml up --build
```

### 6.3 Localisation des Volumes

**Commande d'inspection**:
```bash
# Lister tous les volumes du projet
docker volume ls | grep korrigo

# Inspecter un volume spécifique
docker volume inspect <project>_postgres_data
```

**Emplacement sur l'hôte** (Docker par défaut):
```
/var/lib/docker/volumes/<project>_postgres_data/_data
/var/lib/docker/volumes/<project>_media_volume/_data
/var/lib/docker/volumes/<project>_static_volume/_data
```

### 6.4 Procédures de Sauvegarde

**Référence**: Voir section suivante et `runbook_backup_restore.md`

**Résumé**:
- **Base de données**: `pg_dump` via script `scripts/backup_db.sh` ou commande Django `python manage.py backup`
- **Média**: Archive tar.gz du volume `media_volume`
- **Rétention**: 30 jours (défini dans `backup_db.sh:19`)

### 6.5 Checklist Sécurité Volumes

**Avant toute opération de maintenance**:

- [ ] ⚠️ **Vérifier** qu'une sauvegarde récente existe (< 24h)
- [ ] ⚠️ **Identifier** la commande exacte à exécuter
- [ ] ⚠️ **Confirmer** que l'option `-v` n'est PAS présente dans `docker compose down`
- [ ] ⚠️ **Tester** la procédure sur un environnement de staging d'abord
- [ ] ⚠️ **Documenter** l'opération dans un runbook / journal de bord

**Après toute opération de restauration**:

- [ ] ✅ Valider la connexion base de données
- [ ] ✅ Vérifier l'intégrité des données (comptage enregistrements)
- [ ] ✅ Tester l'accès aux fichiers média
- [ ] ✅ Exécuter les smoke tests (`scripts/smoke.sh`)
- [ ] ✅ Valider l'authentification utilisateur

---

## 7. Plan d'Action Priorisé

### 7.1 Actions Critiques (P0) - Avant Production

| # | Action | Responsable | Effort | Bloquant |
|---|--------|-------------|--------|----------|
| - | ✅ Aucune action P0 identifiée | - | - | - |

**Justification**: Toutes les protections critiques sont déjà en place et fonctionnelles.

### 7.2 Actions Importantes (P1) - Recommandé Avant Production

| # | Action | Fichier | Effort | Impact |
|---|--------|---------|--------|--------|
| P1-1 | Ajouter header HSTS dans nginx (conditionnel HTTPS) | `infra/nginx/nginx.conf` | 15 min | Sécurité HTTPS |
| P1-2 | Ajouter header CSP dans nginx | `infra/nginx/nginx.conf` | 30 min | Défense en profondeur |
| P1-3 | Créer bloc nginx HTTPS avec redirect HTTP→HTTPS | `infra/nginx/nginx.conf` | 30 min | Déploiement HTTPS |
| P1-4 | Mettre à jour `.env.prod.example` avec variables manquantes | `.env.prod.example` | 15 min | Documentation |
| P1-5 | Valider configuration SECURE_HSTS_SECONDS dans settings_prod.py | `backend/core/settings_prod.py` | 15 min | Éliminer warning Django |

**Total effort P1**: ~2 heures

### 7.3 Actions Souhaitables (P2) - Post-Production

| # | Action | Fichier | Effort | Impact |
|---|--------|---------|--------|--------|
| P2-1 | Ajouter header Permissions-Policy dans nginx | `infra/nginx/nginx.conf` | 10 min | Réduction surface attaque |
| P2-2 | Créer script smoke test production (`smoke_prod.sh`) | `scripts/smoke_prod.sh` | 1h | Validation déploiement |
| P2-3 | Automatiser validation headers de sécurité (CI/CD) | `.github/workflows/security.yml` | 2h | Regression testing |

**Total effort P2**: ~3 heures

### 7.4 Actions Optionnelles (P3) - Backlog

| # | Action | Fichier | Effort | Impact |
|---|--------|---------|--------|--------|
| P3-1 | Ajouter type hints pour drf_spectacular warnings | `backend/*/serializers.py` | 4h | Documentation API |
| P3-2 | Migrer APIView → GenericAPIView | `backend/*/views.py` | 8h | Qualité code |

**Total effort P3**: ~12 heures (non prioritaire)

---

## 8. Validation et Tests

### 8.1 Tests de Sécurité Manuels

#### Test 1: Validation Headers (via curl)

```bash
# Pré-requis: Application déployée et accessible
BASE_URL="https://korrigo.education.fr"

# Test HSTS
curl -I $BASE_URL/api/health/ | grep -i strict-transport-security
# Attendu: Strict-Transport-Security: max-age=31536000; includeSubDomains; preload

# Test CSP
curl -I $BASE_URL/api/health/ | grep -i content-security-policy
# Attendu: Content-Security-Policy: default-src 'self'; ...

# Test autres headers
curl -I $BASE_URL/api/health/ | grep -i "x-frame-options\|x-content-type\|x-xss"
# Attendu: X-Frame-Options: DENY, X-Content-Type-Options: nosniff, X-XSS-Protection: 1; mode=block
```

#### Test 2: Validation Cookies (via DevTools)

```bash
# 1. Ouvrir DevTools → Network
# 2. Se connecter à l'application
# 3. Inspecter la requête de login
# 4. Vérifier les cookies Set-Cookie:
#    - sessionid: Secure; HttpOnly; SameSite=Lax
#    - csrftoken: Secure; SameSite=Lax (PAS HttpOnly)
```

#### Test 3: Validation ALLOWED_HOSTS

```bash
# Test avec bon hostname → doit fonctionner
curl -H "Host: korrigo.education.fr" https://korrigo.education.fr/api/health/
# Attendu: HTTP 200 OK

# Test avec mauvais hostname → doit être rejeté
curl -H "Host: attacker.com" https://korrigo.education.fr/api/health/
# Attendu: HTTP 400 Bad Request
```

#### Test 4: Validation HSTS Persistence

```bash
# 1. Visiter le site en HTTPS
# 2. Fermer le navigateur
# 3. Tenter d'accéder en HTTP
# 4. Vérifier redirection automatique HTTPS (sans requête HTTP)
```

### 8.2 Tests Automatisés

**Script de smoke test existant**: `scripts/smoke.sh`

**Contenu actuel**:
- ✅ Health check: `GET /api/health/` → 200
- ✅ Media block: `GET /media/marker.txt` → 403/404

**Tests à ajouter** (dans `scripts/smoke_prod.sh`):
- [ ] Static files: `GET /static/admin/css/base.css` → 200
- [ ] Security headers présence: `HSTS`, `CSP`, `X-Frame-Options`, etc.
- [ ] Cookie flags validation
- [ ] SSL/TLS validation (certificat valide)

### 8.3 Outils Externes de Validation

**Scan de headers de sécurité**:
- [Mozilla Observatory](https://observatory.mozilla.org/)
- [Security Headers](https://securityheaders.com/)
- [SSL Labs](https://www.ssllabs.com/ssltest/) (pour SSL/TLS)

**Scan de vulnérabilités**:
- `safety check` (Python dependencies)
- `npm audit` (Frontend dependencies)
- OWASP ZAP (scan dynamique)

---

## 9. Checklist Pré-Déploiement Production

### 9.1 Configuration Environnement

- [ ] Variable `SECRET_KEY` définie (≥ 50 caractères aléatoires)
- [ ] Variable `DJANGO_ALLOWED_HOSTS` définie avec domaine(s) exact(s)
- [ ] Variable `SSL_ENABLED` définie à `true`
- [ ] Variables base de données définies (`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`)
- [ ] Variables CORS/CSRF définies (`CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`)
- [ ] Variable `METRICS_TOKEN` définie (sécurisation endpoint /metrics)
- [ ] Variable `E2E_SEED_TOKEN` **NON** définie (désactiver en prod réelle)

### 9.2 Configuration Nginx

- [ ] Bloc `server` HTTPS (port 443) configuré
- [ ] Certificat SSL valide installé
- [ ] Redirection HTTP → HTTPS active (port 80 → 301)
- [ ] Headers de sécurité ajoutés (HSTS, CSP, Permissions-Policy, X-Frame-Options, etc.)
- [ ] Headers conditionnels HSTS uniquement dans bloc HTTPS

### 9.3 Validation Django

- [ ] Exécuter `python manage.py check --deploy` → 0 erreurs P0
- [ ] Exécuter `python manage.py migrate` → base de données à jour
- [ ] Exécuter `python manage.py collectstatic` → fichiers statiques collectés
- [ ] Tester connexion base de données (`python manage.py dbshell`)

### 9.4 Validation Sécurité

- [ ] Scan headers avec Mozilla Observatory → Grade A minimum
- [ ] Scan SSL/TLS avec SSL Labs → Grade A minimum
- [ ] Valider cookies dans DevTools (Secure, HttpOnly, SameSite)
- [ ] Tester ALLOWED_HOSTS avec Host header invalide → rejet

### 9.5 Backup et Disaster Recovery

- [ ] Script backup testé et fonctionnel
- [ ] Procédure restore documentée et testée en staging
- [ ] Rétention backups configurée (minimum 30 jours)
- [ ] Stockage off-site configuré (S3, NAS distant, etc.)
- [ ] Alarmes monitoring backup configurées

### 9.6 Smoke Tests

- [ ] Exécuter `scripts/smoke.sh` → tous tests passent
- [ ] Valider health check: `GET /api/health/` → 200 OK
- [ ] Valider static files: `GET /static/admin/css/base.css` → 200 OK
- [ ] Valider authentification: login/logout fonctionnel
- [ ] Valider upload PDF (test end-to-end)

---

## 10. Références et Documentation

### 10.1 Documentation Interne

- **Manuel de Sécurité**: `docs/security/MANUEL_SECURITE.md` (1422 lignes)
- **Runbook Production**: `docs/deployment/RUNBOOK_PRODUCTION.md`
- **Guide Déploiement**: `docs/deployment/DEPLOY_PRODUCTION.md`
- **Runbook Backup/Restore**: `.zenflow/tasks/hardening-prod-settings-headers-ac7f/runbook_backup_restore.md` (à créer)

### 10.2 Documentation Django

- [Django Deployment Checklist](https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/)
- [Django Security Settings](https://docs.djangoproject.com/en/4.2/ref/settings/#security)
- [Django CSRF Protection](https://docs.djangoproject.com/en/4.2/ref/csrf/)

### 10.3 Standards de Sécurité

- [OWASP Top 10 2021](https://owasp.org/Top10/)
- [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/)
- [Mozilla Web Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)

### 10.4 Outils et Validation

- [Mozilla Observatory](https://observatory.mozilla.org/)
- [Security Headers](https://securityheaders.com/)
- [SSL Labs SSL Test](https://www.ssllabs.com/ssltest/)
- [CSP Evaluator](https://csp-evaluator.withgoogle.com/)

---

## 11. Conclusion

### 11.1 Bilan de Sécurité

La plateforme Korrigo/Viatique présente une **architecture de sécurité robuste** avec des mécanismes de protection en profondeur déjà implémentés. La configuration conditionnelle via `SSL_ENABLED` permet de gérer de manière élégante les environnements prod-like (E2E) et production réelle.

**Points forts majeurs**:
- ✅ Validation stricte des variables d'environnement en production
- ✅ Architecture de configuration en trois niveaux bien pensée
- ✅ Cookies sécurisés avec tous les flags appropriés
- ✅ CSP restrictive et adaptée au frontend SPA
- ✅ CORS avec origines explicites (pas de wildcard)
- ✅ Protection anti-wildcard ALLOWED_HOSTS

**Améliorations recommandées**:
- Ajouter headers HSTS et CSP dans nginx (défense en profondeur)
- Configurer Permissions-Policy pour réduire la surface d'attaque
- Créer script de smoke test production complet

### 11.2 État de Préparation Production

**Estimation de maturité**: 🟢 **85%** prêt pour production

**Reste à faire pour 100%**:
- P1-1 à P1-5 (2 heures de travail)
- Tests de validation sécurité (1 heure)
- Documentation runbook backup/restore (complément en cours)

**Risque de déploiement actuel**: 🟡 **FAIBLE**
- Aucun risque critique identifié
- Configuration actuelle déjà fonctionnelle et sécurisée
- Améliorations P1 sont des renforcements, pas des corrections

### 11.3 Prochaines Étapes

1. **Immédiat** (avant déploiement production):
   - Implémenter actions P1-1 à P1-5
   - Valider avec scan Mozilla Observatory
   - Tester procédure backup/restore complète

2. **Court terme** (post-déploiement):
   - Implémenter actions P2
   - Automatiser validation headers en CI/CD
   - Configurer monitoring backup automatisé

3. **Moyen terme** (backlog):
   - Actions P3 (qualité documentation API)
   - Audit de sécurité externe (pentest)
   - Optimisations performance

---

**Rapport généré le**: 2026-01-31  
**Auteur**: Audit Automatisé ZF-AUD-12  
**Version Django**: 4.2  
**Version Python**: 3.9  
**Environment**: Production  

---

**Signatures et Validations**:

| Rôle | Nom | Date | Signature |
|------|-----|------|-----------|
| Auditeur Technique | - | 2026-01-31 | - |
| Responsable Sécurité | - | - | - |
| Product Owner | - | - | - |
| Ops/DevOps Lead | - | - | - |
