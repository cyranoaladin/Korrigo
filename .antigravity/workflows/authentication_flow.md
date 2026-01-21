# Workflow: Authentification

## Vue d'Ensemble

Ce workflow décrit les processus d'authentification pour les trois types d'utilisateurs : **Administrateurs**, **Professeurs**, et **Élèves**.

---

## 1. Authentification Administrateur

### Objectif
Accès au Django Admin pour gestion complète du système.

### Prérequis
- Compte Django User avec `is_staff=True` et `is_superuser=True`
- Credentials (username/password)

### Étapes

```
1. Utilisateur accède à /admin/
   ↓
2. Django affiche formulaire login
   ↓
3. Utilisateur saisit username + password
   ↓
4. Django valide credentials
   ├─ Valid → Créer session + redirect /admin/
   └─ Invalid → Message erreur + retry (rate limited)
   ↓
5. Admin accède à Django Admin complet
```

### Validation
- [ ] Credentials validés via Django auth backend
- [ ] Session créée et sécurisée (HTTPS, secure cookie)
- [ ] Timeout session configuré (4h)
- [ ] Rate limiting sur login (5 tentatives/15min)

### Code Référence
```python
# Django Admin login (built-in)
# Configuration dans settings.py

SESSION_COOKIE_AGE = 14400  # 4 heures
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True
```

---

## 2. Authentification Professeur

### Objectif
Accès à l'interface de correction et gestion des examens/copies.

### Prérequis
- Compte Django User avec `is_staff=True`, `is_superuser=False`
- Credentials (username/password)

### Étapes

```
1. Professeur accède à /login
   ↓
2. Frontend affiche formulaire login
   ↓
3. Professeur saisit username + password
   ↓
4. Frontend envoie POST /api/auth/login/ (avec CSRF token)
   ↓
5. Backend valide credentials
   ├─ Valid → Créer session Django + JWT (optionnel)
   └─ Invalid → 401 Unauthorized
   ↓
6. Frontend stocke token/session
   ↓
7. Frontend redirect /dashboard
   ↓
8. Professeur accède à interface correction
```

### Validation
- [ ] Credentials validés
- [ ] Session/JWT créé et sécurisé
- [ ] CSRF token présent dans requête
- [ ] Rate limiting actif
- [ ] Permissions vérifiées (IsAuthenticated, IsProfessor)

### Code Référence

**Backend** :
```python
# core/views.py
from django.contrib.auth import authenticate, login
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

@api_view(['POST'])
@permission_classes([AllowAny])  # Seule exception
def professor_login(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)

    if user and user.is_staff and not user.is_superuser:
        login(request, user)
        return Response({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'role': 'professor'
            }
        })

    return Response({'error': 'Invalid credentials'}, status=401)
```

**Frontend** :
```javascript
// services/authService.js
export default {
  async login(username, password) {
    const response = await api.post('/auth/login/', {
      username,
      password
    })
    return response.data
  }
}
```

---

## 3. Authentification Élève

### Objectif
Accès en lecture seule à SES copies corrigées uniquement.

### Prérequis
- Compte Student en base (INE enregistré)
- Code d'accès fourni par établissement

### Spécificités
- **PAS de Django User** (session personnalisée)
- **Accès limité** dans le temps (4h)
- **Lecture seule** uniquement
- **Copies GRADED** uniquement

### Étapes

```
1. Élève accède à /student/login
   ↓
2. Frontend affiche formulaire (INE + code d'accès)
   ↓
3. Élève saisit INE + code d'accès
   ↓
4. Frontend envoie POST /api/students/login/
   ↓
5. Backend valide INE + code
   ├─ Valid → Créer session custom avec student_id
   └─ Invalid → 401 Unauthorized
   ↓
6. Frontend stocke session
   ↓
7. Frontend redirect /student/access
   ↓
8. Élève voit liste de SES copies (status=GRADED)
   ↓
9. Élève peut consulter PDF final avec annotations
```

### Validation
- [ ] INE valide et existe en base
- [ ] Code d'accès correct
- [ ] Session créée avec `student_id` uniquement
- [ ] Timeout court (4h maximum)
- [ ] Permissions strictes (IsStudent, IsOwnerStudent)
- [ ] Pas d'accès API autres que consultation copies

### Code Référence

**Backend** :
```python
# students/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import Student

@api_view(['POST'])
@permission_classes([AllowAny])
def student_login(request):
    ine = request.data.get('ine')
    access_code = request.data.get('access_code')

    try:
        student = Student.objects.get(ine=ine)

        # Vérifier code d'accès
        if not check_access_code(student, access_code):
            return Response({'error': 'Invalid credentials'}, status=401)

        # Créer session personnalisée (PAS de Django User)
        request.session['student_id'] = student.id
        request.session.set_expiry(14400)  # 4 heures

        return Response({
            'success': True,
            'student': {
                'id': student.id,
                'first_name': student.first_name,
                'last_name': student.last_name
            }
        })

    except Student.DoesNotExist:
        return Response({'error': 'Invalid credentials'}, status=401)

def check_access_code(student, code):
    """
    Vérifie le code d'accès de l'élève.
    Peut être : hash(INE + secret), code temporaire envoyé par email, etc.
    """
    # Implémentation selon politique établissement
    expected_code = generate_access_code(student.ine)
    return code == expected_code
```

**Permissions Custom** :
```python
# exams/permissions.py
from rest_framework import permissions

class IsStudent(permissions.BasePermission):
    """
    Permission élève : session avec student_id.
    """
    def has_permission(self, request, view):
        return request.session.get('student_id') is not None

class IsOwnerStudent(permissions.BasePermission):
    """
    Permission objet : élève propriétaire uniquement.
    """
    def has_object_permission(self, request, view, obj):
        student_id = request.session.get('student_id')
        if not student_id:
            return False

        # obj = Copy
        if hasattr(obj, 'student'):
            return obj.student and obj.student.id == student_id

        return False
```

**ViewSet Élève** :
```python
# exams/views.py
from rest_framework import viewsets
from .permissions import IsStudent, IsOwnerStudent

class StudentCopyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet lecture seule pour élèves.
    """
    serializer_class = CopyStudentSerializer
    permission_classes = [IsStudent, IsOwnerStudent]

    def get_queryset(self):
        # Filtrer par élève et status GRADED uniquement
        student_id = self.request.session.get('student_id')
        return Copy.objects.filter(
            student_id=student_id,
            status=Copy.Status.GRADED
        ).select_related('exam')
```

---

## 4. Logout

### Professeur Logout
```
1. Utilisateur clique "Logout"
   ↓
2. Frontend envoie POST /api/auth/logout/
   ↓
3. Backend invalide session/JWT
   ↓
4. Frontend supprime token local
   ↓
5. Redirect /login
```

### Élève Logout
```
1. Élève clique "Logout"
   ↓
2. Frontend envoie POST /api/students/logout/
   ↓
3. Backend supprime session (student_id)
   ↓
4. Redirect /student/login
```

---

## 5. Sécurité

### Obligatoire
- HTTPS en production
- Cookies sécurisés (`SESSION_COOKIE_SECURE=True`)
- CSRF protection activée
- Rate limiting sur login
- Logging tentatives d'accès (succès/échec)
- Timeout sessions configuré
- Pas de secrets en dur

### Interdit
- Stocker passwords en clair
- Sessions sans expiration
- Login sans rate limiting
- Credentials dans URLs/logs

---

## 6. Diagramme Récapitulatif

```
┌─────────────┐
│ Admin       │ → Django User (superuser) → Django Admin
├─────────────┤
│ Professeur  │ → Django User (staff) → Session Django/JWT → Interface Correction
├─────────────┤
│ Élève       │ → Student (NO Django User) → Session custom (student_id) → Lecture Copies
└─────────────┘
```

---

**Version** : 1.0
**Date** : 2026-01-21
**Statut** : Obligatoire
