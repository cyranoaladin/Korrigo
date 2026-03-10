# Manuel de Sécurité Technique
# Plateforme Korrigo PMF

> **Version**: 1.1.0  
> **Date**: 10 Mars 2026  
> **Public**: Administrateurs techniques, DSI, RSSI, DPO  
> **Classification**: Usage interne - Sensible  
> **Référence**: SECURITY_PERMISSIONS_INVENTORY.md

---

## 📋 Table des Matières

1. [Introduction](#introduction)
2. [Architecture de Sécurité](#architecture-de-sécurité)
3. [Authentification et Gestion des Identités](#authentification-et-gestion-des-identités)
4. [Contrôle d'Accès et Autorisations](#contrôle-daccès-et-autorisations)
5. [Sécurité des Données](#sécurité-des-données)
6. [Sécurité Réseau](#sécurité-réseau)
7. [Audit et Journalisation](#audit-et-journalisation)
8. [Gestion des Vulnérabilités](#gestion-des-vulnérabilités)
9. [Réponse aux Incidents](#réponse-aux-incidents)
10. [Procédures Opérationnelles](#procédures-opérationnelles)
11. [Conformité et Référentiels](#conformité-et-référentiels)

---

## 1. Introduction

### 1.1 Objet

Ce manuel décrit les mesures de sécurité techniques implémentées dans Korrigo PMF et les procédures opérationnelles associées pour garantir :
- **Confidentialité** : Protection données personnelles élèves
- **Intégrité** : Fiabilité des notes et annotations
- **Disponibilité** : Continuité service pour corrections
- **Traçabilité** : Audit complet des actions

### 1.2 Périmètre

**Systèmes couverts** :
- Application web (Frontend Vue.js + Backend Django)
- Base de données PostgreSQL
- Cache et files d'attente Redis
- Workers Celery (traitement asynchrone)
- Serveur web Nginx (reverse proxy)
- Infrastructure Docker (si applicable)

**Hors périmètre** :
- Sécurité physique des locaux (cf. politique établissement)
- Sécurité des postes de travail utilisateurs (responsabilité DSI)

### 1.3 Responsabilités

| Rôle | Responsabilité Sécurité |
|------|------------------------|
| **Administrateur NSI** | - Appliquer configurations sécurité<br>- Gérer accès et permissions<br>- Surveiller logs sécurité<br>- Exécuter sauvegardes |
| **DSI/RSSI** | - Valider architecture sécurité<br>- Audits périodiques<br>- Gestion incidents majeurs |
| **DPO** | - Conformité RGPD<br>- Validation mesures protection données |
| **Proviseur** | - Approbation politique sécurité<br>- Décisions escalade incidents |

---

## 2. Architecture de Sécurité

### 2.1 Vue d'Ensemble

```
┌─────────────────────────────────────────────────────────────┐
│                       INTERNET                              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTPS (TLS 1.2+)
                         │
                    ┌────▼────┐
                    │  Nginx  │ ← Reverse Proxy + SSL Termination
                    │  WAF    │   Rate Limiting, CSP, HSTS
                    └────┬────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼────┐    ┌────▼────┐    ┌─────▼─────┐
    │ Frontend│    │ Backend │    │  Static   │
    │ Vue.js  │    │ Django  │    │  Files    │
    │ (SPA)   │    │  DRF    │    │ (/media/) │
    └─────────┘    └────┬────┘    └───────────┘
                        │
          ┌─────────────┼─────────────┐
          │             │             │
     ┌────▼────┐   ┌────▼────┐   ┌───▼────┐
     │PostgreSQL│   │  Redis  │   │ Celery │
     │   DB     │   │  Cache  │   │Workers │
     └──────────┘   └─────────┘   └────────┘
```

**Zones de sécurité** :
- **DMZ** : Nginx (exposition publique)
- **Application** : Django + Frontend (réseau interne)
- **Données** : PostgreSQL + Redis (réseau isolé)

---

### 2.2 Modèle de Menaces

**Acteurs malveillants identifiés** :
| Acteur | Motivation | Capacité | Risque |
|--------|-----------|----------|--------|
| **Attaquant externe** | Vol données élèves, défaçage | Moyenne (scripts automatisés) | Moyen |
| **Élève malveillant** | Modification notes, accès copies autres | Faible | Faible |
| **Enseignant malveillant** | Exfiltration données, modification non autorisée | Moyenne | Moyen |
| **Ransomware** | Chiffrement données, rançon | Élevée (automatisé) | Élevé |
| **Insider** (personnel établissement) | Accès non autorisé, sabotage | Élevée | Moyen |

**Vecteurs d'attaque** :
- Brute force authentification
- Injection SQL (ORM Django mitigue)
- XSS (CSP mitigue)
- CSRF (tokens Django mitigent)
- Exfiltration données via API
- Déni de service (DoS)

---

## 3. Authentification et Gestion des Identités

### 3.1 Architecture Multi-Authentification

**Korrigo PMF implémente 2 systèmes d'authentification** :

#### 3.1.1 Authentification Admin/Teacher (Django User)

**Méthode** : Session-based (cookies Django)

**Flux de connexion** :
```python
# backend/core/views.py:LoginView (lines 14-46)
POST /api/login/
{
  "username": "teacher1",
  "password": "password123"
}

# Vérification
user = authenticate(request, username=username, password=password)
if user:
    login(request, user)  # Crée session Django
    return {"user": {"id": user.id, "role": get_user_role(user)}}
```

**Configuration sécurité** :
```python
# backend/core/settings.py
SESSION_COOKIE_SECURE = True  # HTTPS uniquement (si SSL_ENABLED)
SESSION_COOKIE_HTTPONLY = True  # Pas accessible JavaScript
SESSION_COOKIE_SAMESITE = 'Lax'  # Protection CSRF
SESSION_COOKIE_AGE = 1209600  # 2 semaines
SESSION_SAVE_EVERY_REQUEST = False  # Performance
```

**Stockage sessions** : Base de données PostgreSQL (`django_session`)

---

#### 3.1.2 Authentification Student (Email + Password)

**Méthode** : Email + Mot de passe (Django User standard)

**Flux de connexion** :
```python
# backend/students/views.py:StudentLoginView
POST /api/students/login/
{
  "email": "jean.dupont@eleve.lycee.fr",
  "password": "password123"
}

# Vérification
user = authenticate(username=email, password=password)
# + Vérification lien Student
student = Student.objects.get(user=user)

auth_login(request, user) # Session Django standard
request.session['student_id'] = student.id
```

**Sécurité** :
- ✅ **Standard** : Utilise l'infrastructure auth Django éprouvée
- ✅ **Mot de passe** : Haché (PBKDF2)
- ✅ **Rate Limiting** : 30 tentatives / 15 min par IP (adapté aux NAT partagés)
- ✅ **Réponse 429** : Message français clair en cas de dépassement
- ✅ **Changement forcé** : Mot de passe initial (date de naissance JJMMAAAA) doit être changé à la première connexion

---

### 3.2 Rate Limiting (Protection Brute Force)

**Configuration** :
```python
# backend/core/settings.py
RATELIMIT_ENABLE = True  # Obligatoire en production

# backend/core/views.py:LoginView
@method_decorator(ratelimit(key='ip', rate='5/15m', method='POST'), name='dispatch')
class LoginView(APIView):
    # Max 5 tentatives par IP toutes les 15 minutes

# backend/students/views.py:StudentLoginView
@method_decorator(maybe_ratelimit(key='ip', rate='30/15m', method='POST', block=False))
def post(self, request):
    if getattr(request, 'limited', False):
        return Response({'error': '...', 'rate_limited': True}, status=429)
```

**Endpoints protégés** :
- `/api/login/` : 5 tentatives / 15 min (enseignants/admin)
- `/api/students/login/` : 30 tentatives / 15 min par IP (adapté NAT partagé école/opérateur)

> ℹ️ **Note** : Le rate limit élève est plus élevé car les élèves d'une même classe partagent souvent la même IP publique (NAT opérateur mobile, WiFi école). Le endpoint retourne HTTP 429 avec un message français clair au lieu du 403 générique DRF.

**Limitation actuelle** :
- ⚠️ Rate limiting par IP (contournable via VPN)
- ⚠️ Pas de lockout compte après N échecs
- ⚠️ Pas de CAPTCHA

**Amélioration recommandée** :
```python
# Lockout basé username
@ratelimit(key='post:username', rate='10/1h')
```

---

### 3.3 Gestion des Mots de Passe

#### 3.3.1 Politique de Complexité

**Configuration Django** :
```python
# backend/core/settings.py
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 6}},  # ⚠️ FAIBLE
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
```

**Validation actuelle** :
- ✅ Longueur minimum 6 caractères
- ✅ Pas similaire nom utilisateur
- ✅ Pas dans liste mots de passe communs
- ✅ Pas entièrement numérique

**⚠️ AMÉLIORATION REQUISE** :
```python
# Recommandation ANSSI
{
    'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    'OPTIONS': {'min_length': 12}  # Au lieu de 6
}
```

---

#### 3.3.2 Stockage Sécurisé

**Algorithme de hachage** :
```python
# Django par défaut (backend/core/settings.py)
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',  # SHA256 + sel
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.Argon2PasswordHasher',  # Recommandé si argon2 installé
]
```

**Format stocké** (exemple) :
```
pbkdf2_sha256$260000$random_salt$hashed_password
```

**Sécurité** :
- ✅ 260 000 itérations PBKDF2 (résistance brute force)
- ✅ Sel unique par mot de passe
- ✅ Pas de stockage en clair

---

#### 3.3.3 Changement de Mot de Passe

**Endpoint** :
```python
# POST /api/change-password/
{
  "old_password": "ancien",
  "new_password": "nouveau123"
}
```

**Sécurité implémentée** :
```python
# backend/core/views.py
if not user.check_password(old_password):
    return Response({"error": "Invalid old password"}, status=400)

user.set_password(new_password)
user.save()
update_session_auth_hash(request, user)  # ✅ Préserve session
```

**Protection** :
- ✅ Vérification ancien mot de passe
- ✅ Validation nouveau mot de passe (validators)
- ✅ Session maintenue après changement

---

### 3.4 Gestion des Sessions

#### 3.4.1 Configuration Sécurisée

```python
# backend/core/settings.py
SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # DB (traçabilité)
SESSION_COOKIE_SECURE = True  # HTTPS uniquement
SESSION_COOKIE_HTTPONLY = True  # Anti-XSS
SESSION_COOKIE_SAMESITE = 'Lax'  # Anti-CSRF
SESSION_COOKIE_AGE = 1209600  # 2 semaines
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
```

**Expiration** :
- Inactivité : 2 semaines
- Fermeture navigateur : Session conservée
- Changement mot de passe : Session préservée (via `update_session_auth_hash`)

---

#### 3.4.2 Nettoyage Sessions Expirées

**Commande Django** :
```bash
# Exécution quotidienne (cron)
python manage.py clearsessions
```

**Configuration cron** :
```cron
0 2 * * * cd /opt/korrigo && python manage.py clearsessions >> /var/log/korrigo/clearsessions.log 2>&1
```

---

## 4. Contrôle d'Accès et Autorisations

### 4.1 Modèle RBAC (Role-Based Access Control)

**Rôles définis** :
```python
# backend/core/auth.py
class UserRole:
    ADMIN = 'admin'      # Superuser Django
    TEACHER = 'teacher'  # Groupe Django "teacher"
    STUDENT = 'student'  # Session student_id (pas de User)
```

**Mapping rôles → permissions** :
| Rôle | Groupes Django | Attributs | Permissions |
|------|---------------|-----------|-------------|
| **ADMIN** | `admin` (groupe) | `is_superuser=True`<br>`is_staff=True` | - Gestion utilisateurs<br>- Configuration système<br>- Tous endpoints |
| **TEACHER** | `teacher` (groupe) | `is_staff=False` | - Correction copies<br>- Annotations<br>- Consultation exams |
| **STUDENT** | - | Session `student_id` | - Consultation copies personnelles<br>- Téléchargement PDF finaux |

---

### 4.2 Permission Classes DRF

**Hiérarchie implémentée** :
```python
# backend/core/auth.py

# Permission de base
class IsAuthenticated(BasePermission):
    # Django DRF par défaut

# Permissions spécifiques
class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name='admin').exists()

class IsTeacher(BasePermission):
```
    def has_permission(self, request, view):
        return request.user.groups.filter(name='teacher').exists()

class IsStudent(BasePermission):
    def has_permission(self, request, view):
        # Student authentication: Email/Password, Django User + Student Profile, Django Session, SessionAuthentication
        return hasattr(request.user, 'student')

class IsAdminOrTeacher(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return user.is_superuser or user.groups.filter(name__in=['admin', 'teacher']).exists()
```

---

### 4.3 Object-Level Permissions

**Cas d'usage critique : Annotations**

**Permission class** :
```python
# backend/grading/permissions.py
class IsLockedByOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Lecture : Toujours autorisée
        if request.method in SAFE_METHODS:
            return True
        
        # Écriture : Vérifier propriété verrou
        copy = obj.copy if isinstance(obj, Annotation) else obj
        lock = CopyLock.objects.filter(copy=copy).first()
        
        if not lock:
            return False
        
        # Vérifier owner + token
        if lock.owner != request.user:
            return False
        
        lock_token = request.headers.get('X-Lock-Token') or request.data.get('lock_token')
        if lock.token != UUID(lock_token):
            return False
        
        return True
```

**Protection** :
- ✅ Un enseignant ne peut modifier que SES annotations
- ✅ Nécessite verrou actif sur la copie
- ✅ Token de verrou vérifié

---

### 4.4 Queryset Filtering (Security by Obscurity)

**Isolation données élèves** :
```python
# backend/exams/views.py:StudentCopiesListView (lines 349-395)
class StudentCopiesListView(generics.ListAPIView):
    permission_classes = [IsStudent]
    
    def get_queryset(self):
        student_id = self.request.session.get('student_id')
        if student_id:
            # Filtrage strict : SEULEMENT ses copies
            return Copy.objects.filter(
                student=student_id,
                status=Copy.Status.GRADED  # Uniquement copies finalisées
            )
        else:
            # Méthode alternative : User associé
            student = Student.objects.get(user=self.request.user)
            return Copy.objects.filter(student=student, status=Copy.Status.GRADED)
```

**Sécurité** :
- ✅ Isolation complète (élève A ne voit JAMAIS copies élève B)
- ✅ Statut GRADED obligatoire (pas de copies en cours)
- ✅ Pas de bypass possible (queryset filtré avant sérialisation)

---

### 4.5 Endpoint Critique : Téléchargement PDF Final

**Endpoint** : `GET /api/grading/copies/<id>/final-pdf/`

**Permission class** : `AllowAny` ⚠️ **Justification requise**

**Gates de sécurité implémentés dans la vue** :
```python
# backend/grading/views.py:CopyFinalPdfView (lines 160-253)

# Gate 1 : Copie finalisée uniquement
if copy.status != Copy.Status.GRADED:
    return Response({"detail": "Copy not graded yet"}, status=403)

# Gate 2 : Permission basée rôle
if request.user.is_authenticated:
    # Admin/Teacher : Accès complet
    if request.user.is_staff or request.user.is_superuser:
        pass  # Autorisé
    else:
        return Response({"detail": "Forbidden"}, status=403)
else:
    # Student : Vérifier session
    student_id = request.session.get('student_id')
    if not student_id:
        return Response({"detail": "Authentication required"}, status=401)
    
    # Vérifier propriété
    if copy.student_id != student_id:
        return Response({"detail": "Not your copy"}, status=403)

# Gate 3 : Audit trail
GradingEvent.objects.create(
    copy=copy,
    action=GradingEvent.Action.EXPORT,
    actor=request.user if request.user.is_authenticated else None,
    metadata={"student_id": student_id, "ip": request.META.get('REMOTE_ADDR')}
)
```

**Justification `AllowAny`** :
- Système dual (User vs Student session)
- Gates explicites dans vue (documenté)
- Audit complet des téléchargements
- Conformité : Règles de sécurité internes — Accès PDF Final

**Référence** : `SECURITY_PERMISSIONS_INVENTORY.md:186-218`

---

## 5. Sécurité des Données

### 5.1 Chiffrement au Repos

**Base de données PostgreSQL** :
```bash
# Configuration recommandée (transparent data encryption)
# postgresql.conf
ssl = on
ssl_cert_file = '/etc/ssl/certs/server.crt'
ssl_key_file = '/etc/ssl/private/server.key'
```

**Fichiers média** :
- **Localisation** : `/media/` (montage Docker volume ou filesystem)
- **Permissions** : `chmod 750` (rwx r-x ---)
- **Propriétaire** : `korrigo:korrigo` (user applicatif)

**⚠️ Amélioration recommandée** :
```bash
# Chiffrement disque LUKS (Linux)
cryptsetup luksFormat /dev/sdb
cryptsetup luksOpen /dev/sdb korrigo_data
mkfs.ext4 /dev/mapper/korrigo_data
mount /dev/mapper/korrigo_data /opt/korrigo/media
```

---

### 5.2 Chiffrement en Transit

**HTTPS Obligatoire** :
```python
# backend/core/settings.py (production)
if SSL_ENABLED:
    SECURE_SSL_REDIRECT = True  # HTTP → HTTPS redirect
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    
    # HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000  # 1 an
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Cookies sécurisés
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
```

**Configuration Nginx** :
```nginx
# /etc/nginx/sites-available/korrigo
server {
    listen 443 ssl http2;
    server_name korrigo.lycee-exemple.fr;
    
    # Certificat SSL (Let's Encrypt recommandé)
    ssl_certificate /etc/letsencrypt/live/korrigo.lycee-exemple.fr/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/korrigo.lycee-exemple.fr/privkey.pem;
    
    # Protocoles TLS
    ssl_protocols TLSv1.2 TLSv1.3;  # ✅ Pas SSLv3, TLS 1.0/1.1
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers on;
    
    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    
    # Headers sécurité
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

**Test** :
```bash
# Vérifier SSL
curl -I https://korrigo.lycee-exemple.fr
# Attendre: Strict-Transport-Security header

# Test SSL Labs
# https://www.ssllabs.com/ssltest/analyze.html?d=korrigo.lycee-exemple.fr
# Objectif: Grade A+
```

---

### 5.3 Anonymisation des Copies

**Processus** :
1. **Identification** : Secrétariat lie copie ↔ élève
2. **Génération anonymat** : UUID unique
   ```python
   anonymous_id = uuid.uuid4().hex[:8].upper()  # Ex: "A3F7B2E1"
   ```
3. **Masquage nom** : Bandeau blanc sur en-tête PDF (future feature)
4. **Transition statut** : `STAGING` → `READY`

**Garanties** :
- ✅ Anonymat réversible (traçabilité DB)
- ✅ Correcteurs voient uniquement `anonymous_id`
- ✅ Réidentification automatique lors export Pronote

---

### 5.4 Pseudonymisation des Logs

**Recommandation RGPD** :
```python
# Pseudonymiser IP dans logs
import hashlib

def pseudonymize_ip(ip_address):
    salt = settings.SECRET_KEY[:16]
    return hashlib.sha256(f"{ip_address}{salt}".encode()).hexdigest()[:16]

# Usage dans audit
GradingEvent.objects.create(
    copy=copy,
    action='EXPORT',
    metadata={
        "ip_hash": pseudonymize_ip(request.META.get('REMOTE_ADDR')),
        "user_agent": request.META.get('HTTP_USER_AGENT')
    }
)
```

---

### 5.5 Suppression Sécurisée

**Méthode recommandée** :
```python
# backend/core/management/commands/secure_delete.py
import os

def secure_delete_file(file_path):
    """Écrasement 3 passes (DoD 5220.22-M)"""
    if not os.path.exists(file_path):
        return
    
    file_size = os.path.getsize(file_path)
    
    with open(file_path, 'ba+') as f:
        # Passe 1 : Zéros
        f.write(b'\x00' * file_size)
        f.flush()
        
        # Passe 2 : Uns
        f.seek(0)
        f.write(b'\xFF' * file_size)
        f.flush()
        
        # Passe 3 : Random
        f.seek(0)
        f.write(os.urandom(file_size))
        f.flush()
    
    os.remove(file_path)
```

**Usage** :
```python
# Suppression copies expirées
copies = Copy.objects.filter(exam__date__lt=threshold)
for copy in copies:
    if copy.pdf_source:
        secure_delete_file(copy.pdf_source.path)
    if copy.final_pdf:
        secure_delete_file(copy.final_pdf.path)
    copy.delete()
```

---

## 6. Sécurité Réseau

### 6.1 CORS (Cross-Origin Resource Sharing)

**Configuration stricte** :
```python
# backend/core/settings.py

# Développement
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CORS_ALLOW_CREDENTIALS = True

# Production
cors_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "")
if cors_origins:
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(",")]
    CORS_ALLOW_CREDENTIALS = True
else:
    # Same-origin uniquement (Nginx sert frontend + backend)
    CORS_ALLOWED_ORIGINS = []
    CORS_ALLOW_CREDENTIALS = False
```

**Vérification** :
```bash
# Test CORS
curl -H "Origin: https://malicious.com" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS \
     https://korrigo.lycee-exemple.fr/api/exams/

# Réponse attendue : 403 Forbidden (origin non autorisée)
```

---

### 6.2 CSRF Protection

**Configuration Django** :
```python
# backend/core/settings.py
CSRF_COOKIE_SECURE = True  # HTTPS uniquement
CSRF_COOKIE_HTTPONLY = False  # ⚠️ SPA doit lire token
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = [
    "https://korrigo.lycee-exemple.fr",
]

# Exemptions (authentification uniquement)
CSRF_EXEMPT_VIEWS = [
    'core.views.LoginView',  # POST /api/login/
    'students.views.StudentLoginView',  # POST /api/students/login/
]
```

**Flow CSRF** :
```javascript
// Frontend (Vue.js)
// 1. Récupérer token CSRF (cookie)
const csrfToken = document.cookie
  .split('; ')
  .find(row => row.startsWith('csrftoken='))
  ?.split('=')[1];

// 2. Envoyer dans header
axios.post('/api/exams/', data, {
  headers: { 'X-CSRFToken': csrfToken }
});
```

---

### 6.3 Content Security Policy (CSP)

**Configuration** :
```python
# backend/core/settings.py
CONTENT_SECURITY_POLICY = {
    'DIRECTIVES': {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'"],  # ⚠️ Vue.js inline
        'style-src': ["'self'", "'unsafe-inline'"],   # ⚠️ Vue.js inline
        'img-src': ["'self'", "data:", "blob:"],      # PDF.js
        'font-src': ["'self'"],
        'connect-src': ["'self'"],
        'frame-ancestors': ["'none'"],  # Anti-clickjacking
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
    }
}
```

**⚠️ Amélioration recommandée** :
- Remplacer `'unsafe-inline'` par nonces CSP
- Générer nonce dynamique par requête
- Vérifier compatibilité Vite build

**Header généré** :
```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; ...
```

---

### 6.4 Firewall et Segmentation

**Règles iptables recommandées** :
```bash
# Autoriser HTTP/HTTPS uniquement
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# Bloquer accès direct PostgreSQL/Redis (réseau interne uniquement)
iptables -A INPUT -p tcp --dport 5432 -s 172.16.0.0/12 -j ACCEPT  # PostgreSQL
iptables -A INPUT -p tcp --dport 5432 -j DROP
iptables -A INPUT -p tcp --dport 6379 -s 172.16.0.0/12 -j ACCEPT  # Redis
iptables -A INPUT -p tcp --dport 6379 -j DROP

# Bloquer tout le reste
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT
```

**Docker networking** :
```yaml
# docker-compose.yml
services:
  backend:
    networks:
      - frontend_network
      - backend_network
  
  postgres:
    networks:
      - backend_network  # Pas exposé à frontend

networks:
  frontend_network:
    driver: bridge
  backend_network:
    driver: bridge
    internal: true  # Pas d'accès internet
```

---

## 7. Audit et Journalisation

### 7.1 Événements Audités

**Table `GradingEvent`** (traçabilité complète) :
```python
# backend/grading/models.py
class GradingEvent(models.Model):
    class Action(models.TextChoices):
        IMPORT = 'IMPORT', 'Import Copy'
        VALIDATE = 'VALIDATE', 'Validate Copy'
        LOCK = 'LOCK', 'Lock Copy'
        UNLOCK = 'UNLOCK', 'Unlock Copy'
        CREATE_ANN = 'CREATE_ANN', 'Create Annotation'
        UPDATE_ANN = 'UPDATE_ANN', 'Update Annotation'
        DELETE_ANN = 'DELETE_ANN', 'Delete Annotation'
        FINALIZE = 'FINALIZE', 'Finalize Copy'
        EXPORT = 'EXPORT', 'Export PDF'
    
    copy = models.ForeignKey(Copy, on_delete=models.CASCADE)
    action = models.CharField(max_length=20, choices=Action.choices)
    actor = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict)
```

**Événements tracés** :
- ✅ Import copies
- ✅ Identification élève
- ✅ Verrouillage/déverrouillage
- ✅ Création/modification/suppression annotations
- ✅ Finalisation copies
- ✅ Téléchargements PDF
- ✅ Connexions/déconnexions (Django logs)

---

### 7.2 Logs Applicatifs

**Configuration Django Logging** :
```python
# backend/core/settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/korrigo/django.log',
            'maxBytes': 10485760,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'security': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/korrigo/security.log',
            'maxBytes': 10485760,
            'backupCount': 10,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
```

**Logs sécurité Django** (exemples) :
- Tentatives CSRF
- Requêtes suspectes (SQL injection, XSS)
- Échecs authentification
- Permissions refusées

---

### 7.3 Logs Nginx

**Configuration** :
```nginx
# /etc/nginx/nginx.conf
http {
    log_format security '$remote_addr - $remote_user [$time_local] '
                       '"$request" $status $body_bytes_sent '
                       '"$http_referer" "$http_user_agent" '
                       '$request_time $upstream_response_time';
    
    access_log /var/log/nginx/korrigo_access.log security;
    error_log /var/log/nginx/korrigo_error.log warn;
}
```

**Rotation logs** :
```bash
# /etc/logrotate.d/korrigo
/var/log/korrigo/*.log /var/log/nginx/korrigo*.log {
    daily
    rotate 180  # 6 mois (conformité RGPD)
    compress
    delaycompress
    notifempty
    create 0640 korrigo adm
    sharedscripts
    postrotate
        /usr/bin/systemctl reload nginx > /dev/null 2>&1 || true
    endscript
}
```

---

### 7.4 Surveillance et Alertes

**Indicateurs à surveiller** :
| Métrique | Seuil Alerte | Action |
|----------|-------------|--------|
| Tentatives login échouées | > 50 / 15 min | Vérifier attaque brute force |
| Erreurs 500 | > 10 / min | Vérifier logs applicatifs |
| CPU > 90% | > 5 min | Vérifier workers Celery |
| Espace disque < 10% | Immédiat | Purger fichiers temporaires |
| Connexions DB > 80% pool | Immédiat | Vérifier fuites connexions |

**Outils recommandés** :
- **Prometheus + Grafana** : Métriques temps réel
- **Sentry** : Suivi erreurs applicatives
- **Fail2ban** : Bannissement IP après tentatives login

**Configuration Fail2ban** :
```ini
# /etc/fail2ban/jail.d/korrigo.conf
[korrigo-auth]
enabled = true
port = http,https
filter = korrigo-auth
logpath = /var/log/korrigo/django.log
maxretry = 5
findtime = 600
bantime = 3600
```

---

## 8. Gestion des Vulnérabilités

### 8.1 Veille Sécurité

**Sources CVE** :
- Django Security : https://www.djangoproject.com/weblog/
- Python Security : https://python.org/dev/security/
- PostgreSQL Security : https://www.postgresql.org/support/security/
- GitHub Security Advisories : https://github.com/advisories

**Outils automatisés** :
```bash
# Scan dépendances Python
pip install safety
safety check --json > security_report.json

# Scan npm (frontend)
cd frontend
npm audit --json > npm_audit.json
```

**Fréquence** : Hebdomadaire (automatisé via CI/CD)

---

### 8.2 Mises à Jour Sécurité

**Processus** :
1. **Notification CVE** (veille automatisée)
2. **Évaluation criticité** (CVSS score)
   - **Critique (9.0-10.0)** : Patch sous 24h
   - **Élevée (7.0-8.9)** : Patch sous 7 jours
   - **Moyenne (4.0-6.9)** : Patch sous 30 jours
3. **Test environnement staging**
4. **Déploiement production** (fenêtre maintenance)
5. **Vérification post-déploiement**

**Commandes** :
```bash
# Mise à jour Django
pip install --upgrade django==4.2.x

# Mise à jour PostgreSQL (apt)
apt update && apt upgrade postgresql

# Redémarrage services
systemctl restart korrigo-backend
systemctl restart postgresql
```

---

### 8.3 Scan de Vulnérabilités

**OWASP ZAP** (scan automatisé) :
```bash
# Scan basique
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t https://korrigo.lycee-exemple.fr \
  -r zap_report.html

# Scan complet (authentifié)
docker run -t owasp/zap2docker-stable zap-full-scan.py \
  -t https://korrigo.lycee-exemple.fr \
  -z "-config api.addrs.addr.name=.* -config api.addrs.addr.regex=true" \
  -r zap_full_report.html
```

**Fréquence** : Trimestriel + avant mise en production majeure

---

## 9. Réponse aux Incidents

### 9.1 Classification des Incidents

| Niveau | Criticité | Exemples | Temps Réponse |
|--------|-----------|----------|---------------|
| **P0 - Critique** | Violation données, service indisponible | Exfiltration DB, ransomware | < 1 heure |
| **P1 - Élevé** | Vulnérabilité critique, défaçage | SQLi exploité, XSS stocké | < 4 heures |
| **P2 - Moyen** | Accès non autorisé, bug sécurité | Élève accède copie d'autrui | < 24 heures |
| **P3 - Faible** | Anomalie, tentative échouée | Brute force bloqué | < 72 heures |

---

### 9.2 Procédure d'Intervention

**Phase 1 : Détection et Alerte**
```
1. Détection anomalie (logs, alerte utilisateur, scan)
2. Notification Admin NSI + DPO
3. Évaluation criticité (classification P0-P3)
4. Si P0/P1 : Escalade Proviseur + DSI
```

**Phase 2 : Confinement**
```
1. Isoler système affecté (firewall, déconnexion réseau)
2. Préserver preuves (snapshots disque, logs)
3. Bloquer accès comptes compromis
4. Activer mode maintenance si nécessaire
```

**Phase 3 : Éradication**
```
1. Identifier vecteur d'attaque
2. Patcher vulnérabilité
3. Restaurer depuis sauvegarde saine (si compromission)
4. Changer tous mots de passe Admin
```

**Phase 4 : Récupération**
```
1. Restaurer service normal
2. Surveillance accrue (72h)
3. Vérification intégrité données
4. Communication utilisateurs (si nécessaire)
```

**Phase 5 : Post-Mortem**
```
1. Rapport incident (causes, impact, actions)
2. Notification CNIL si violation RGPD (< 72h)
3. Amélioration procédures (leçons apprises)
4. Formation équipe
```

---

### 9.3 Contacts d'Urgence

| Rôle | Contact | Disponibilité |
|------|---------|---------------|
| **Admin NSI (1er niveau)** | admin.nsi@lycee-exemple.fr<br>06 XX XX XX XX | 24/7 (astreinte) |
| **DPO** | dpo@lycee-exemple.fr<br>06 YY YY YY YY | Heures bureau |
| **DSI Académie** | dsi@ac-exemple.fr<br>01 23 45 67 89 | Heures bureau |
| **CNIL (violation)** | https://www.cnil.fr/notifications | 24/7 (formulaire) |
| **CERT-FR (incidents majeurs)** | cert-fr.cossi@ssi.gouv.fr | 24/7 |

---

## 10. Procédures Opérationnelles

### 10.1 Création Utilisateur Admin

**Procédure** :
```bash
# 1. Créer utilisateur Django
python manage.py createsuperuser
# Username: admin.nsi
# Email: admin.nsi@lycee-exemple.fr
# Password: [Mot de passe fort 12+ caractères]

# 2. Ajouter au groupe admin
python manage.py shell
>>> from django.contrib.auth.models import User, Group
>>> user = User.objects.get(username='admin.nsi')
>>> admin_group = Group.objects.get(name='admin')
>>> user.groups.add(admin_group)
>>> user.save()

# 3. Vérifier permissions
>>> user.is_superuser
True
>>> user.groups.filter(name='admin').exists()
True
```

**Traçabilité** :
- Créer ticket changement (numéro, date, responsable)
- Logger dans registre utilisateurs
- Email confirmation au nouvel admin

---

### 10.2 Révocation Accès (Départ Enseignant)

**Procédure** :
```bash
# 1. Désactiver compte (ne pas supprimer pour audit)
python manage.py shell
>>> user = User.objects.get(username='teacher.dupont')
>>> user.is_active = False
>>> user.save()

# 2. Invalider sessions actives
>>> from django.contrib.sessions.models import Session
>>> Session.objects.filter(
...     session_data__contains=f'"_auth_user_id":"{user.id}"'
... ).delete()

# 3. Libérer verrous copies
>>> from grading.models import CopyLock
>>> CopyLock.objects.filter(owner=user).delete()

# 4. Archiver données (si nécessaire)
python manage.py export_user_activity --username teacher.dupont > archive_dupont.json
```

**Délai** : < 24h après notification RH

---

### 10.3 Audit Permissions Trimestriel

**Script d'audit** :
```python
# backend/core/management/commands/audit_permissions.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from datetime import datetime, timedelta

class Command(BaseCommand):
    def handle(self, *args, **options):
        # Utilisateurs inactifs > 90 jours
        threshold = datetime.now() - timedelta(days=90)
        inactive_users = User.objects.filter(
            last_login__lt=threshold,
            is_active=True
        )
        
        print(f"⚠️ {inactive_users.count()} utilisateurs inactifs > 90j :")
        for user in inactive_users:
            print(f"  - {user.username} (dernière connexion: {user.last_login})")
        
        # Superusers
        superusers = User.objects.filter(is_superuser=True)
        print(f"\n🔒 {superusers.count()} superusers :")
        for user in superusers:
            print(f"  - {user.username} ({user.email})")
        
        # Comptes sans email
        no_email = User.objects.filter(email='')
        print(f"\n⚠️ {no_email.count()} comptes sans email :")
        for user in no_email:
            print(f"  - {user.username}")
```

**Exécution** :
```bash
# Trimestre 1, 2, 3, 4
python manage.py audit_permissions > audit_Q1_2026.txt
```

---

### 10.4 Sauvegardes et Restauration

**Stratégie 3-2-1** :
- **3 copies** : Production + Sauvegarde locale + Sauvegarde distante
- **2 supports** : Disque dur + Bande magnétique (ou cloud)
- **1 hors site** : Datacenter secondaire ou cloud

**Script sauvegarde** :
```bash
#!/bin/bash
# /opt/korrigo/scripts/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/korrigo"
DB_NAME="korrigo_db"

# Sauvegarde PostgreSQL
pg_dump -U korrigo -Fc $DB_NAME > "$BACKUP_DIR/db_$DATE.dump"

# Sauvegarde fichiers média
tar -czf "$BACKUP_DIR/media_$DATE.tar.gz" /opt/korrigo/media/

# Chiffrement
gpg --encrypt --recipient admin@lycee-exemple.fr "$BACKUP_DIR/db_$DATE.dump"
gpg --encrypt --recipient admin@lycee-exemple.fr "$BACKUP_DIR/media_$DATE.tar.gz"

# Suppression fichiers non chiffrés
rm "$BACKUP_DIR/db_$DATE.dump"
rm "$BACKUP_DIR/media_$DATE.tar.gz"

# Rétention : 30 jours quotidiens, 6 mois hebdomadaires
find $BACKUP_DIR -name "db_*.dump.gpg" -mtime +30 -delete
```

**Cron** :
```cron
0 2 * * * /opt/korrigo/scripts/backup.sh >> /var/log/korrigo/backup.log 2>&1
```

**Restauration** :
```bash
# Déchiffrer
gpg --decrypt backup/db_20260130_020000.dump.gpg > db.dump

# Restaurer DB
pg_restore -U korrigo -d korrigo_db -c db.dump

# Restaurer média
tar -xzf media_20260130_020000.tar.gz -C /opt/korrigo/
```

**Test restauration** : Trimestriel (environnement staging)

---

## 11. Conformité et Référentiels

### 11.1 Référentiels Applicables

| Référentiel | Niveau | Notes |
|-------------|--------|-------|
| **RGPD** | Obligatoire | Protection données personnelles |
| **RGS (Référentiel Général de Sécurité)** | Recommandé | Sécurité SI publics |
| **PASSI (Prestataire d'Audit de la Sécurité des SI)** | Optionnel | Audit externe |
| **ANSSI Bonnes Pratiques** | Recommandé | Guide sécurité |
| **OWASP Top 10** | Recommandé | Vulnérabilités web |

---

### 11.2 Checklist Conformité OWASP Top 10 (2021)

| Vulnérabilité | Statut | Mesures |
|---------------|--------|---------|
| **A01:2021 - Broken Access Control** | ✅ Mitigué | RBAC, queryset filtering, object permissions |
| **A02:2021 - Cryptographic Failures** | ✅ Mitigué | HTTPS, HSTS, chiffrement DB |
| **A03:2021 - Injection** | ✅ Mitigué | ORM Django (parameterized queries) |
| **A04:2021 - Insecure Design** | ✅ Mitigué | AIPD, threat modeling, security by default |
| **A05:2021 - Security Misconfiguration** | ⚠️ Partiel | DEBUG=False, SECRET_KEY unique, CSP ⚠️ unsafe-inline |
| **A06:2021 - Vulnerable Components** | ✅ Mitigué | `safety check`, `npm audit`, mises à jour régulières |
| **A07:2021 - Authentication Failures** | ⚠️ Partiel | Rate limiting ✅, MDP faible ⚠️ (min 6 car.) |
| **A08:2021 - Software/Data Integrity** | ✅ Mitigué | Audit trail, signatures Git |
| **A09:2021 - Logging Failures** | ✅ Mitigué | GradingEvent, logs Django/Nginx, rétention 6 mois |
| **A10:2021 - SSRF** | ✅ Non applicable | Pas de fetch URL externe |

---

### 11.3 Audit Externe Recommandé

**Fréquence** : Annuel

**Scope** :
- Test intrusion (pentest)
- Revue code sécurité
- Scan vulnérabilités
- Conformité RGPD
- Disaster recovery test

**Prestataire** : Certification PASSI (liste ANSSI)

---

## 12. Annexes

### Annexe A : Ports et Services

| Port | Service | Exposition | Sécurité |
|------|---------|-----------|----------|
| 80 | HTTP | Publique | Redirect → 443 |
| 443 | HTTPS | Publique | TLS 1.2+, HSTS |
| 5432 | PostgreSQL | Interne | Firewall, authentification |
| 6379 | Redis | Interne | Firewall, requirepass |
| 5555 | Celery Flower | Localhost | Admin uniquement |
| 8088 | Gunicorn (backend) | Interne | Nginx reverse proxy |

---

### Annexe B : Variables d'Environnement Sensibles

**Fichier `.env` (ne JAMAIS commit Git)** :
```bash
# Sécurité critique
SECRET_KEY=<généré via `openssl rand -base64 64`>
DEBUG=False
ALLOWED_HOSTS=korrigo.lycee-exemple.fr
DJANGO_ENV=production

# Base de données
DATABASE_URL=postgresql://korrigo:PASSWORD@localhost:5432/korrigo_db

# Redis
REDIS_URL=redis://:PASSWORD@localhost:6379/0

# SSL
SSL_ENABLED=True
CSRF_TRUSTED_ORIGINS=https://korrigo.lycee-exemple.fr

# Rate limiting
RATELIMIT_ENABLE=true
```

**Gestion secrets** :
- Production : Variables d'environnement système (systemd)
- Alternative : Vault (HashiCorp), AWS Secrets Manager

---

### Annexe C : Commandes Utiles

```bash
# Vérifier configuration sécurité Django
python manage.py check --deploy

# Audit permissions
python manage.py audit_permissions

# Purger données expirées
python manage.py purge_expired_data

# Exporter données élève (RGPD)
python manage.py export_student_data --ine 1234567890A

# Test connexion DB chiffrée
psql "sslmode=require host=localhost dbname=korrigo_db user=korrigo"

# Vérifier certificat SSL
openssl s_client -connect korrigo.lycee-exemple.fr:443 -showcerts
```

---

**Document validé par** :
- Admin NSI : _______________
- RSSI Académie : _______________
- DPO : _______________
- Date : 30 Janvier 2026
