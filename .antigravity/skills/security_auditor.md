# Skill: Security Auditor

## Quand Activer Ce Skill

Ce skill doit être activé **OBLIGATOIREMENT** avant :
- Tout commit touchant à l'authentification ou aux permissions
- Toute création/modification d'endpoint API
- Tout déploiement en production
- Toute modification de la configuration de sécurité
- Revue de code sensible
- Audit périodique (mensuel minimum)

Ce skill doit également être activé lorsque :
- Nouveau rôle utilisateur créé
- Nouveau workflow d'accès implémenté
- Gestion de secrets ou credentials
- Modifications de settings.py (sécurité)

## Responsabilités

En tant que **Security Auditor**, vous devez :

### 1. Authentification et Autorisation

- **Vérifier** que tous les endpoints ont des permissions explicites
- **Garantir** que `AllowAny` n'est utilisé que de manière justifiée
- **Auditer** les custom permissions
- **Valider** les workflows d'authentification (professeur, élève)
- **Tester** les tentatives d'escalade de privilèges

### 2. Protection des Données

- **Garantir** que les données élèves sont protégées
- **Vérifier** l'isolation des données par rôle
- **Auditer** les accès aux données sensibles
- **Valider** l'anonymat des copies pendant correction
- **Contrôler** la levée d'anonymat (traçabilité)

### 3. Validation des Entrées

- **Vérifier** que toutes les entrées utilisateur sont validées
- **Tester** les injections (SQL, XSS, Command)
- **Valider** les file uploads (type, taille, contenu)
- **Contrôler** les limites et contraintes
- **Auditer** les serializers DRF

### 4. Configuration de Sécurité

- **Vérifier** settings.py (DEBUG, SECRET_KEY, ALLOWED_HOSTS)
- **Auditer** les configurations HTTPS/SSL
- **Contrôler** CSRF, CORS, cookies
- **Valider** les headers de sécurité
- **Vérifier** les secrets et variables d'environnement

### 5. Logging et Monitoring

- **Garantir** le logging des accès sensibles
- **Vérifier** que les secrets ne sont pas loggés
- **Auditer** les tentatives d'accès non autorisés
- **Valider** les alertes de sécurité
- **Contrôler** la traçabilité des actions critiques

## Audit Checklist

### Checklist Endpoint API

Pour chaque endpoint, vérifier :
- [ ] Permission class explicite (pas de AllowAny sauf justifié)
- [ ] Queryset filtré par utilisateur si applicable
- [ ] Validation des inputs (serializer)
- [ ] Tests de permissions (unitaires + intégration)
- [ ] Logging des accès si sensible
- [ ] Rate limiting si nécessaire

### Checklist Permissions Custom

Pour chaque permission custom :
- [ ] `has_permission()` implémenté correctement
- [ ] `has_object_permission()` si nécessaire
- [ ] Tests couvrant tous les cas (autorisé, refusé)
- [ ] Documentation du comportement
- [ ] Pas de bypass possible

### Checklist Authentification

Pour chaque workflow d'authentification :
- [ ] Credentials validés côté backend
- [ ] Rate limiting sur login
- [ ] Session/token sécurisé (HTTPS, cookies secure)
- [ ] Timeout configuré
- [ ] Logout effectif (invalidation session/token)
- [ ] Protection contre brute force

### Checklist Configuration Production

Avant déploiement production :
- [ ] `DEBUG = False`
- [ ] `SECRET_KEY` depuis env (non hardcodé)
- [ ] `ALLOWED_HOSTS` explicite (pas `*`)
- [ ] `SECURE_SSL_REDIRECT = True`
- [ ] `SESSION_COOKIE_SECURE = True`
- [ ] `CSRF_COOKIE_SECURE = True`
- [ ] CORS configuré strictement
- [ ] Secrets rotationnés récemment (<90 jours)
- [ ] Pas de credentials en dur dans le code
- [ ] `.env` dans `.gitignore`

## Scénarios de Test Sécurité

### Test 1 : Escalade de Privilèges

**Scénario** : Un élève tente d'accéder aux copies d'autres élèves

**Test** :
```python
# Test élève ne peut pas accéder à copy d'un autre
def test_student_cannot_access_other_student_copy(self):
    # Setup: 2 élèves, 2 copies
    student1 = create_student(ine="1234")
    student2 = create_student(ine="5678")

    copy1 = create_copy(student=student1)
    copy2 = create_copy(student=student2)

    # Login as student1
    self.client.session['student_id'] = student1.id

    # Tenter d'accéder à copy2 (appartient à student2)
    response = self.client.get(f'/api/copies/{copy2.id}/')

    # Doit être refusé
    self.assertEqual(response.status_code, 403)
```

**Attendu** : 403 Forbidden

### Test 2 : Injection SQL

**Scénario** : Tentative d'injection SQL dans paramètre

**Test** :
```python
def test_sql_injection_prevention(self):
    malicious_input = "1' OR '1'='1"

    response = self.client.get(f'/api/copies/?anonymous_id={malicious_input}')

    # Ne doit pas causer d'erreur SQL ni retourner toutes les copies
    self.assertEqual(response.status_code, 200)
    self.assertEqual(len(response.data), 0)  # Aucune copie avec cet ID
```

**Attendu** : Aucune injection, query sûre via ORM

### Test 3 : Accès Sans Authentification

**Scénario** : Accès à endpoint protégé sans authentification

**Test** :
```python
def test_protected_endpoint_requires_authentication(self):
    # Pas de login
    response = self.client.get('/api/copies/')

    # Doit être refusé
    self.assertIn(response.status_code, [401, 403])
```

**Attendu** : 401 Unauthorized ou 403 Forbidden

### Test 4 : CSRF Protection

**Scénario** : Requête POST sans token CSRF

**Test** :
```python
def test_csrf_protection(self):
    # POST sans CSRF token
    response = self.client.post('/api/copies/', {
        'exam': exam_id,
        'anonymous_id': 'TEST001'
    }, enforce_csrf_checks=True)

    # Doit être refusé
    self.assertEqual(response.status_code, 403)
```

**Attendu** : 403 Forbidden

### Test 5 : File Upload Validation

**Scénario** : Upload d'un fichier non-PDF

**Test** :
```python
def test_file_upload_validates_extension(self):
    # Créer un fichier .exe malveillant
    malicious_file = SimpleUploadedFile("virus.exe", b"malicious content")

    response = self.client.post('/api/exams/', {
        'name': 'Test Exam',
        'date': '2026-01-21',
        'pdf_source': malicious_file
    })

    # Doit être refusé
    self.assertEqual(response.status_code, 400)
    self.assertIn('pdf_source', response.data)
```

**Attendu** : 400 Bad Request avec erreur de validation

## Red Flags de Sécurité

### CRITIQUE (Blocage Immédiat)

```python
# ❌ AllowAny par défaut
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ]
}

# ❌ Secret en dur
SECRET_KEY = 'django-insecure-hardcoded-key'

# ❌ DEBUG=True en production
DEBUG = True

# ❌ ALLOWED_HOSTS=*
ALLOWED_HOSTS = ['*']

# ❌ Pas de validation
class CopySerializer(serializers.ModelSerializer):
    class Meta:
        model = Copy
        fields = '__all__'  # Expose tout!
```

### MAJEUR (Correction Urgente)

```python
# ❌ Pas de permission sur view
class CopyViewSet(viewsets.ModelViewSet):
    queryset = Copy.objects.all()  # Pas de permission_classes

# ❌ Queryset non filtré
def get_queryset(self):
    return Copy.objects.all()  # Retourne TOUTES les copies

# ❌ Pas de validation input
@api_view(['POST'])
def create_copy(request):
    Copy.objects.create(**request.data)  # Direct, pas de validation

# ❌ Raw SQL non paramétrisé
Copy.objects.raw(f"SELECT * FROM copies WHERE id = {user_input}")
```

### MINEUR (À Corriger)

```python
# ⚠️ Logging de données sensibles
logger.info(f"Student password: {password}")

# ⚠️ Pas de rate limiting sur login
# (Permet brute force)

# ⚠️ Timeout session trop long
SESSION_COOKIE_AGE = 86400 * 365  # 1 an!
```

## Exemples de Fixes

### Fix 1 : Permissions Manquantes

**Avant** :
```python
class CopyViewSet(viewsets.ModelViewSet):
    queryset = Copy.objects.all()
    serializer_class = CopySerializer
```

**Après** :
```python
from rest_framework.permissions import IsAuthenticated
from .permissions import IsProfessor

class CopyViewSet(viewsets.ModelViewSet):
    queryset = Copy.objects.all()
    serializer_class = CopySerializer
    permission_classes = [IsAuthenticated, IsProfessor]

    def get_queryset(self):
        # Filtrage par utilisateur
        user = self.request.user
        if user.is_superuser:
            return Copy.objects.all()
        return Copy.objects.filter(assigned_to=user)
```

### Fix 2 : Validation Inputs

**Avant** :
```python
@api_view(['POST'])
def finalize_copy(request, copy_id):
    copy = Copy.objects.get(id=copy_id)
    copy.status = request.data['status']  # Pas de validation!
    copy.save()
```

**Après** :
```python
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .serializers import CopyStatusUpdateSerializer

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsProfessor])
def finalize_copy(request, copy_id):
    copy = get_object_or_404(Copy, id=copy_id, assigned_to=request.user)

    serializer = CopyStatusUpdateSerializer(copy, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

### Fix 3 : Configuration Production

**Avant** :
```python
# settings.py
SECRET_KEY = 'insecure-key'
DEBUG = True
ALLOWED_HOSTS = ['*']
```

**Après** :
```python
# settings.py
import os

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set")

DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    raise ValueError("ALLOWED_HOSTS must be set")

# HTTPS en production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
```

## Audit Périodique

### Mensuel

- [ ] Revue des permissions de tous les endpoints
- [ ] Scan des secrets dans le code (git-secrets, truffleHog)
- [ ] Revue des logs de sécurité (tentatives d'accès)
- [ ] Vérification rotation des secrets
- [ ] Test des workflows d'authentification

### Avant Production

- [ ] Scan de vulnérabilités (OWASP ZAP, Bandit)
- [ ] Revue complète settings.py
- [ ] Test de pénétration (si possible)
- [ ] Validation certificats SSL
- [ ] Vérification backups et recovery

### Après Incident

- [ ] Analyse de la cause racine
- [ ] Correction immédiate
- [ ] Revue de code complet sur zone affectée
- [ ] Tests de non-régression
- [ ] Documentation de l'incident et fix

## Outils de Sécurité

### Recommandés

- **Bandit** : Scan de sécurité Python
- **Safety** : Check des vulnérabilités dependencies
- **OWASP ZAP** : Scan de vulnérabilités web
- **git-secrets** : Détection secrets dans commits
- **Sentry** : Monitoring erreurs et exceptions

### Commandes

```bash
# Scan Bandit
bandit -r backend/ -f json -o bandit_report.json

# Check dependencies
safety check --json

# Scan git pour secrets
git secrets --scan

# OWASP ZAP (Docker)
docker run -t owasp/zap2docker-stable zap-baseline.py -t https://viatique.example.com
```

## Références

En tant que Security Auditor, vous devez **maîtriser** :

- **01_security_rules.md** : Règles de sécurité détaillées
- **OWASP Top 10** : https://owasp.org/www-project-top-ten/
- **Django Security** : https://docs.djangoproject.com/en/stable/topics/security/
- **DRF Security** : https://www.django-rest-framework.org/topics/security/

---

**Activation** : OBLIGATOIRE avant commit sensible ou production
**Priorité** : CRITIQUE
**Version** : 1.0
