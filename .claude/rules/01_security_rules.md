# Règles de Sécurité - Viatique

## Statut : CRITIQUE - NON NÉGOCIABLE

Ces règles de sécurité sont **absolument obligatoires**. Toute violation est considérée comme une **faille de sécurité critique**.

---

## 1. Authentification et Autorisation

### 1.1 Django REST Framework - Permissions

**INTERDIT ABSOLUMENT** :
```python
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # ❌ JAMAIS EN DÉFAUT
    ]
}
```

**OBLIGATOIRE** :
```python
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',  # ✅ MINIMUM
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        # OU 'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}
```

**Règles** :
- Permissions explicites sur **chaque ViewSet/APIView**
- `AllowAny` uniquement si absolument nécessaire et documenté
- Jamais `AllowAny` sur endpoints manipulant des données élèves/copies/notes

### 1.2 Permissions Custom Strictes

**Modèle de Permissions Viatique** :

```python
# ✅ Bon exemple
class CopyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsProfessor]  # Explicite

    def get_queryset(self):
        # Filtrage par utilisateur
        if self.request.user.is_staff:
            return Copy.objects.all()
        return Copy.objects.filter(assigned_to=self.request.user)
```

**Classes de Permissions Obligatoires** :
- `IsProfessor` : Accès professeur uniquement
- `IsAdmin` : Accès administrateur
- `IsStudent` : Accès élève (via session custom)
- `IsOwnerStudent` : Élève propriétaire uniquement

**INTERDIT** :
- Permissions au niveau view sans permission class
- Vérifications de permissions dans la logique métier
- Bypass de permissions via query parameters

---

## 2. Séparation Stricte des Rôles

### 2.1 Trois Rôles Distincts

#### Administrateur
- **Accès** : Django Admin complet
- **Permissions** : Superuser
- **Authentification** : Django User avec `is_staff=True`, `is_superuser=True`

#### Professeur
- **Accès** : API de correction, gestion des examens et copies
- **Permissions** : Django User avec `is_staff=True`, `is_superuser=False`
- **Authentification** : Session Django ou JWT
- **Restrictions** :
  - Ne peut voir que ses copies assignées (sauf si coordinateur)
  - Ne peut pas accéder au Django Admin (sauf permissions spécifiques)
  - Ne peut pas voir les données d'identification avant anonymat levé

#### Élève
- **Accès** : Consultation uniquement de SES copies corrigées
- **Permissions** : Session personnalisée (pas de Django User)
- **Authentification** : Via `student_id` en session
- **Restrictions STRICTES** :
  - **Lecture seule** sur ses propres copies avec `status=GRADED`
  - **Aucun accès** aux copies d'autres élèves
  - **Aucun accès** aux copies non corrigées
  - **Aucune modification** possible
  - **Aucun accès** au Django Admin

### 2.2 Authentification Élève

**Workflow Obligatoire** :
1. Élève s'authentifie via INE + code fourni par établissement
2. Backend vérifie INE et code
3. Session créée avec `student_id` (pas de Django User)
4. Token/session limitée dans le temps (4h max)

**Code de Référence** :
```python
# ✅ Bon exemple
class StudentLoginView(APIView):
    permission_classes = [AllowAny]  # Seule exception justifiée

    def post(self, request):
        ine = request.data.get('ine')
        access_code = request.data.get('access_code')

        # Vérifier INE et code
        student = Student.objects.filter(ine=ine).first()
        if not student or not check_access_code(student, access_code):
            return Response({"error": "Invalid credentials"}, status=401)

        # Créer session élève (pas de User Django)
        request.session['student_id'] = student.id
        request.session.set_expiry(14400)  # 4h

        return Response({"success": True})
```

**INTERDIT pour Élèves** :
- Utiliser Django User/Authentication backend
- Donner accès au système de permissions Django
- Permettre l'accès API sans session validée
- Exposer des endpoints non filtrés par `student_id`

---

## 3. Protection des Données Élèves

### 3.1 Accès aux Données

**OBLIGATOIRE** :
- Toute donnée élève nécessite authentification valide
- Filtrage strict par élève propriétaire
- Pas d'énumération possible (pas d'IDs séquentiels exposés)
- UUIDs pour tous les identifiants publics

**INTERDIT** :
- Exposer des listes non filtrées
- Permettre l'accès via IDs prévisibles
- Fuites de données via messages d'erreur détaillés
- Logs contenant des données personnelles

### 3.2 Anonymat des Copies

**Règles** :
- Anonymat maintenu jusqu'à publication des résultats
- `anonymous_id` unique et non devinable
- Nom/prénom élève jamais exposé aux correcteurs avant levée d'anonymat
- Traçabilité de la levée d'anonymat (qui, quand, pourquoi)

**Code de Référence** :
```python
# ✅ Bon exemple - Serializer Anonyme
class CopyCorrectorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Copy
        fields = ['id', 'anonymous_id', 'final_pdf', 'status']
        # ❌ PAS de 'student', 'student_name', etc.
```

---

## 4. Configuration de Sécurité Django

### 4.1 Settings Production

**OBLIGATOIRE** :
```python
# settings.py
SECRET_KEY = os.environ.get('SECRET_KEY')  # Jamais de valeur par défaut en prod
if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set in production")

DEBUG = False  # Toujours False en production

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    raise ValueError("ALLOWED_HOSTS must be set in production")

# HTTPS Obligatoire en Production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Autres Headers de Sécurité
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
```

**INTERDIT en Production** :
```python
SECRET_KEY = 'django-insecure-...'  # ❌
DEBUG = True  # ❌
ALLOWED_HOSTS = ['*']  # ❌
```

### 4.2 CSRF et CORS

**CSRF** :
```python
CSRF_COOKIE_SAMESITE = 'Strict'  # ou 'Lax' si nécessaire
CSRF_COOKIE_HTTPONLY = False  # False pour accès JS si SPA
CSRF_TRUSTED_ORIGINS = ['https://viatique.example.com']  # Explicite
```

**CORS** :
```python
# En production, même origine (Nginx sert tout)
# Si cross-origin nécessaire :
CORS_ALLOWED_ORIGINS = [
    'https://viatique.example.com',
]
CORS_ALLOW_CREDENTIALS = True
```

**INTERDIT** :
```python
CORS_ALLOW_ALL_ORIGINS = True  # ❌ Jamais
CORS_ORIGIN_ALLOW_ALL = True  # ❌ Jamais
```

---

## 5. Gestion des Secrets

### 5.1 Variables d'Environnement

**OBLIGATOIRE** :
- Tous les secrets dans variables d'environnement
- Fichier `.env` dans `.gitignore`
- Fichier `.env.example` versionné (SANS valeurs réelles)

**Secrets à Protéger** :
- `SECRET_KEY` (Django)
- `DATABASE_URL` (connexion DB)
- Clés API externes (si applicable)
- Tokens d'accès services tiers
- Credentials SMTP/email

**Code de Référence** :
```python
# ✅ Bon exemple
import os
from pathlib import Path

SECRET_KEY = os.environ.get('SECRET_KEY')
DATABASE_URL = os.environ.get('DATABASE_URL')

# ❌ Mauvais exemple
SECRET_KEY = 'hardcoded-secret-key'  # JAMAIS
```

### 5.2 Rotation des Secrets

**OBLIGATOIRE** :
- Rotation de `SECRET_KEY` tous les 90 jours en production
- Rotation des tokens d'accès selon politique de sécurité
- Procédure de rotation documentée

---

## 6. Validation des Entrées

### 6.1 Validation Côté Backend

**OBLIGATOIRE** :
- Validation de **toutes** les entrées utilisateur
- Sanitization des données avant stockage
- Type checking strict
- Length limits respectés

**INTERDIT** :
- Faire confiance aux validations frontend
- Accepter des données non validées
- Injections (SQL, NoSQL, Command, XSS)

**Code de Référence** :
```python
# ✅ Bon exemple
class CopyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Copy
        fields = ['anonymous_id', 'status']
        read_only_fields = ['id', 'exam', 'final_pdf']  # Protection

    def validate_status(self, value):
        # Validation stricte des transitions d'état
        allowed_transitions = {
            'STAGING': ['READY'],
            'READY': ['LOCKED'],
            'LOCKED': ['GRADED', 'READY'],  # Unlock possible
        }
        current_status = self.instance.status if self.instance else None
        if current_status and value not in allowed_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f"Invalid transition from {current_status} to {value}"
            )
        return value
```

### 6.2 Injections SQL

**OBLIGATOIRE** :
- Utiliser l'ORM Django (jamais de raw SQL si évitable)
- Si raw SQL nécessaire : parameterized queries

**INTERDIT** :
```python
# ❌ DANGER - SQL Injection
Copy.objects.raw(f"SELECT * FROM copies WHERE id = {user_input}")

# ✅ Bon - Parameterized
Copy.objects.raw("SELECT * FROM copies WHERE id = %s", [user_input])

# ✅ Meilleur - ORM
Copy.objects.filter(id=user_input)
```

---

## 7. Logs et Monitoring

### 7.1 Logging Sécurisé

**OBLIGATOIRE** :
- Logger toutes les tentatives d'authentification (succès/échec)
- Logger les accès aux données sensibles
- Logger les modifications de permissions
- Logs structurés (JSON) pour parsing

**INTERDIT** :
- Logger des secrets (passwords, tokens, keys)
- Logger des données personnelles complètes (INE partiel OK)
- Logs verbeux en production

**Code de Référence** :
```python
# ✅ Bon exemple
import logging
logger = logging.getLogger(__name__)

def student_login(request, ine, access_code):
    student = authenticate_student(ine, access_code)
    if student:
        logger.info(f"Student login success: INE={ine[:4]}***")  # Partiel
        return success_response
    else:
        logger.warning(f"Student login failed: INE={ine[:4]}***")
        return error_response
```

### 7.2 Monitoring des Anomalies

**OBLIGATOIRE** :
- Détection de tentatives de brute force
- Alerte sur accès interdits répétés
- Monitoring des erreurs 403/401
- Rate limiting sur endpoints sensibles

### 7.3 Audit Trail et Traçabilité

**OBLIGATOIRE pour Conformité Légale** :

Les actions suivantes **doivent** être tracées et conservées :

#### Traçabilité Authentification
- [ ] Tentatives de login (succès/échec) avec timestamp, IP, user agent
- [ ] Création/suppression de comptes utilisateur
- [ ] Changements de permissions/rôles
- [ ] Logout (volontaire ou timeout)

#### Traçabilité Accès Données Sensibles
- [ ] Accès élève à ses copies (qui, quand, quelle copie)
- [ ] Consultation de données élèves par admin/prof
- [ ] Export de données (notes Pronote, etc.)
- [ ] Levée d'anonymat (qui, quand, quelle copie, raison)

#### Traçabilité Workflow Métier
- [ ] Verrouillage copie (qui, quand)
- [ ] Déverrouillage copie (qui, quand, raison)
- [ ] Finalisation correction (qui, quand)
- [ ] Modifications post-correction (si exceptionnelles)

#### Implémentation

```python
# models.py - Traçabilité intégrée
class AuditLog(models.Model):
    """
    Table d'audit centralisée pour actions critiques.
    """
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    student_id = models.IntegerField(null=True)  # Si session élève
    action = models.CharField(max_length=100, db_index=True)
    resource_type = models.CharField(max_length=50)
    resource_id = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    metadata = models.JSONField(default=dict)  # Données contextuelles

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['resource_type', 'resource_id']),
        ]

# utils/audit.py - Helper d'audit
import logging
from django.utils import timezone

audit_logger = logging.getLogger('audit')

def log_audit(request, action, resource_type, resource_id, metadata=None):
    """
    Log une action pour audit trail.
    """
    user = getattr(request, 'user', None)
    student_id = request.session.get('student_id')

    AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        student_id=student_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        metadata=metadata or {}
    )

    # Log structuré pour monitoring externe
    audit_logger.info(
        "audit",
        extra={
            'action': action,
            'resource': f"{resource_type}:{resource_id}",
            'user': user.username if user and user.is_authenticated else 'anonymous',
            'student_id': student_id,
            'ip': get_client_ip(request)
        }
    )

# Usage dans views
@api_view(['POST'])
@permission_classes([IsStudent, IsOwnerStudent])
def download_copy_pdf(request, copy_id):
    copy = get_object_or_404(Copy, id=copy_id)

    # Audit trail
    log_audit(
        request,
        action='copy.download',
        resource_type='Copy',
        resource_id=copy.id,
        metadata={'copy_anonymous_id': copy.anonymous_id}
    )

    return FileResponse(copy.final_pdf.open('rb'))
```

#### Rétention et Conformité

**OBLIGATOIRE** :
- Rétention logs audit : **minimum 12 mois** (légal RGPD/CNIL)
- Logs stockés de manière immuable (append-only)
- Accès logs audit réservé admin/DPO
- Export audit trail possible pour contrôle
- Anonymisation logs après période légale (si données perso)

**RGPD/CNIL** :
- Logs contenant données perso = données personnelles
- Droit d'accès élève aux logs le concernant
- Pas de logs excessifs (proportionnalité)
- Documentation finalités traitement

#### Alertes Basées sur Audit

```python
# Exemples d'alertes automatiques
def check_suspicious_activity():
    # Alerte si accès élève depuis IPs multiples en <1h
    recent_logs = AuditLog.objects.filter(
        action='student.login',
        student_id=student_id,
        timestamp__gte=timezone.now() - timedelta(hours=1)
    )
    unique_ips = recent_logs.values('ip_address').distinct().count()
    if unique_ips > 3:
        send_security_alert(f"Multiple IPs for student {student_id}")

    # Alerte si tentatives unlock répétées
    unlock_attempts = AuditLog.objects.filter(
        action='copy.unlock',
        user=user,
        timestamp__gte=timezone.now() - timedelta(minutes=5)
    ).count()
    if unlock_attempts > 5:
        send_security_alert(f"Suspicious unlock attempts by {user}")
```

#### Requêtes Audit Utiles

```python
# Qui a accédé à la copie X ?
AuditLog.objects.filter(
    resource_type='Copy',
    resource_id=copy_id,
    action__in=['copy.view', 'copy.download']
).select_related('user')

# Actions d'un élève spécifique
AuditLog.objects.filter(student_id=student_id).order_by('-timestamp')

# Levées d'anonymat du jour
AuditLog.objects.filter(
    action='copy.deanonymize',
    timestamp__date=timezone.now().date()
)

# Tentatives d'accès refusées
AuditLog.objects.filter(
    action__endswith='.denied',
    timestamp__gte=timezone.now() - timedelta(days=7)
)
```

---

## 8. Sécurité des Fichiers

### 8.1 Upload de Fichiers

**OBLIGATOIRE** :
- Validation du type MIME
- Limite de taille stricte
- Scan antivirus si possible
- Stockage hors du webroot

**INTERDIT** :
- Exécution de fichiers uploadés
- Servir directement les uploads (utiliser X-Sendfile ou équivalent)
- Faire confiance aux extensions de fichier

**Code de Référence** :
```python
# ✅ Bon exemple
from django.core.validators import FileExtensionValidator

class Exam(models.Model):
    pdf_source = models.FileField(
        upload_to='exams/source/',
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf']),
            validate_file_size,  # Custom validator
        ]
    )
```

### 8.2 Accès aux Fichiers

**OBLIGATOIRE** :
- Permissions vérifiées avant envoi de fichier
- URLs signées pour accès temporaire
- Pas d'énumération de fichiers possible

**Code de Référence** :
```python
# ✅ Bon exemple - Protected file serving
@api_view(['GET'])
@permission_classes([IsStudent, IsOwnerStudent])
def download_copy_pdf(request, copy_id):
    copy = get_object_or_404(Copy, id=copy_id)

    # Vérification permission
    if not request.user.has_perm('view_copy', copy):
        return Response(status=403)

    # Vérification statut
    if copy.status != Copy.Status.GRADED:
        return Response({"error": "Copy not yet graded"}, status=403)

    # Serving sécurisé
    response = FileResponse(copy.final_pdf.open('rb'))
    response['Content-Disposition'] = f'attachment; filename="{copy.anonymous_id}.pdf"'
    return response
```

---

## 9. Rate Limiting

**OBLIGATOIRE** :
- Rate limiting sur login endpoints (5 tentatives / 15min)
- Rate limiting sur API publique (100 req/min par IP)
- Throttling pour utilisateurs authentifiés (1000 req/min)

**Configuration DRF** :
```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/min',
        'user': '1000/min',
        'login': '5/15min',  # Custom throttle
    }
}
```

---

## 10. Checklist de Sécurité Avant Production

Avant tout déploiement en production, vérifier :

- [ ] `DEBUG = False`
- [ ] `SECRET_KEY` depuis variable d'environnement
- [ ] `ALLOWED_HOSTS` configuré explicitement
- [ ] HTTPS activé et forcé
- [ ] Cookies sécurisés (`SESSION_COOKIE_SECURE=True`)
- [ ] CSRF activé et configuré
- [ ] CORS configuré strictement (pas de `*`)
- [ ] Permissions explicites sur tous les endpoints
- [ ] Pas de `AllowAny` sur endpoints sensibles
- [ ] Validation des entrées partout
- [ ] Rate limiting activé
- [ ] Logs de sécurité configurés
- [ ] Monitoring et alertes actifs
- [ ] Backup et recovery plan en place
- [ ] Scan de sécurité effectué (OWASP ZAP ou équivalent)

---

## Conséquences des Violations

**CRITIQUE** :
- `AllowAny` par défaut → Blocage immédiat
- Secret en dur → Rotation immédiate + audit
- Fuite de données élèves → Incident de sécurité majeur
- Pas d'authentification sur endpoint sensible → Rollback

**Action Immédiate** :
1. Rollback du code problématique
2. Audit de sécurité complet
3. Notification de l'incident si données exposées
4. Correction et test avant redéploiement

---

**Version** : 1.0
**Date** : 2026-01-21
**Statut** : CRITIQUE - Violation = Incident de Sécurité
