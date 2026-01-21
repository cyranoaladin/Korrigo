# Règles Backend - Django/DRF - Viatique

## Statut : OBLIGATOIRE

Ces règles définissent l'architecture backend et les pratiques obligatoires pour Django/Django REST Framework.

---

## 1. Architecture Django

### 1.1 Structure des Apps

**Structure Obligatoire** :
```
backend/
├── core/              # Configuration centrale
├── exams/             # Gestion examens, copies, booklets
├── grading/           # Annotations, scores
├── processing/        # Traitement PDF, services
└── students/          # Gestion élèves
```

**Règles** :
- Une app = un domaine métier cohérent
- Pas de dépendances circulaires entre apps
- Imports explicites, pas de `import *`
- Apps découplées via signals ou services si nécessaire

### 1.2 Organisation Interne d'une App

**Structure Standard** :
```
app_name/
├── __init__.py
├── models.py           # Modèles Django
├── serializers.py      # DRF Serializers
├── views.py            # Views/ViewSets
├── urls.py             # URL routing
├── permissions.py      # Permissions custom
├── services.py         # Logique métier (si complexe)
├── tasks.py            # Celery tasks
├── tests/              # Tests
│   ├── test_models.py
│   ├── test_views.py
│   └── test_services.py
└── migrations/         # Migrations Django
```

**INTERDIT** :
- Fichiers monolithiques (>500 lignes)
- Logique métier dans views
- Modèles "god objects"

---

## 2. Modèles Django

### 2.1 Règles de Définition

**OBLIGATOIRE** :
```python
# ✅ Bon exemple
from django.db import models
import uuid

class Copy(models.Model):
    # UUIDs pour IDs publics
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Champs obligatoires avec verbose_name
    anonymous_id = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Identifiant Anonyme"
    )

    # Choices avec TextChoices
    class Status(models.TextChoices):
        STAGING = 'STAGING', "En attente"
        READY = 'READY', "Prêt à corriger"
        LOCKED = 'LOCKED', "Verrouillé"
        GRADED = 'GRADED', "Corrigé"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.STAGING
    )

    # Traçabilité
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Copie"
        verbose_name_plural = "Copies"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"Copie {self.anonymous_id}"
```

**Règles Obligatoires** :
- UUIDs pour toute PK exposée publiquement
- `verbose_name` sur tous les champs
- `help_text` sur champs non évidents
- `created_at` / `updated_at` sur modèles importants
- Meta class avec `verbose_name`, `verbose_name_plural`, `ordering`
- Méthode `__str__()` explicite

**INTERDIT** :
- IDs auto-incrémentaux exposés (énumération possible)
- Champs sans `verbose_name`
- Models sans `__str__()`
- Pas de `Meta` class

### 2.2 Relations

**OBLIGATOIRE** :
```python
# ✅ Bon exemple - ForeignKey
class Copy(models.Model):
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,  # Explicite
        related_name='copies',     # Toujours nommer
        verbose_name="Examen"
    )

    student = models.ForeignKey(
        'students.Student',        # String reference si autre app
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='copies',
        verbose_name="Élève identifié"
    )
```

**Règles** :
- `on_delete` toujours explicite
- `related_name` toujours défini
- `CASCADE` uniquement si suppression en cascade voulue
- `SET_NULL` avec `null=True` si relation optionnelle
- `PROTECT` pour empêcher suppression accidentelle

**INTERDIT** :
```python
exam = models.ForeignKey(Exam)  # ❌ on_delete manquant
student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='+')  # ❌ + interdit
```

### 2.3 Méthodes de Modèle

**OBLIGATOIRE** :
- Pas de logique métier complexe dans les modèles
- Méthodes utilitaires simples uniquement
- Pas d'accès réseau ou I/O dans les modèles

**Bon Usage** :
```python
# ✅ OK - Méthode utilitaire simple
class Copy(models.Model):
    def is_correctable(self):
        return self.status == self.Status.READY

    def can_be_viewed_by_student(self):
        return self.status == self.Status.GRADED and self.is_identified
```

**INTERDIT** :
```python
# ❌ Logique métier complexe dans le modèle
class Copy(models.Model):
    def lock_and_assign(self, professor):
        # Logique complexe → doit être dans un service
        if self.status != self.Status.READY:
            raise ValueError("Cannot lock")
        self.status = self.Status.LOCKED
        self.assigned_to = professor
        self.save()
        # Envoyer email, logger, etc. → NON
```

---

## 3. Migrations

### 3.1 Règles de Migration

**OBLIGATOIRE** :
- Migration pour **chaque** modification de modèle
- Nom de migration explicite : `python manage.py makemigrations --name add_student_to_copy`
- Revue de la migration générée avant commit
- Migration testée localement avant merge

**INTERDIT** :
- Modifier un modèle sans créer de migration
- Éditer une migration déjà appliquée en production
- Supprimer des migrations existantes
- Migrations avec perte de données non documentée

### 3.2 Migrations Réversibles

**OBLIGATOIRE** :
```python
# ✅ Bon exemple - Migration réversible
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('exams', '0002_previous_migration'),
    ]

    operations = [
        migrations.AddField(
            model_name='copy',
            name='is_identified',
            field=models.BooleanField(default=False),
        ),
        # Réversible automatiquement via RemoveField
    ]
```

**Pour Migrations Complexes** :
```python
# ✅ Bon exemple - Migration de données
from django.db import migrations

def populate_anonymous_ids(apps, schema_editor):
    Copy = apps.get_model('exams', 'Copy')
    for copy in Copy.objects.filter(anonymous_id__isnull=True):
        copy.anonymous_id = generate_anonymous_id()
        copy.save()

def reverse_populate(apps, schema_editor):
    # Si nécessaire
    pass

class Migration(migrations.Migration):
    dependencies = [...]

    operations = [
        migrations.RunPython(populate_anonymous_ids, reverse_populate),
    ]
```

### 3.3 Checklist Migration

Avant de commit une migration :
- [ ] Migration nommée explicitement
- [ ] Modèles et migration cohérents
- [ ] Migration testée localement
- [ ] Pas de perte de données (ou documentée et acceptée)
- [ ] Réversible si possible
- [ ] Performance acceptable (si migration de données volumineuses)

---

## 4. Django REST Framework

### 4.1 Serializers

**OBLIGATOIRE** :
```python
# ✅ Bon exemple
from rest_framework import serializers

class CopySerializer(serializers.ModelSerializer):
    # Champs en lecture seule
    exam_name = serializers.CharField(source='exam.name', read_only=True)

    class Meta:
        model = Copy
        fields = ['id', 'anonymous_id', 'status', 'exam_name', 'created_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_status(self, value):
        # Validation custom
        if self.instance and self.instance.status == Copy.Status.LOCKED:
            if value != Copy.Status.LOCKED and not self.context.get('force_unlock'):
                raise serializers.ValidationError("Cannot change status of locked copy")
        return value

    def validate(self, data):
        # Validation globale
        return data
```

**Règles** :
- Serializer par modèle (au minimum un par usage : list, detail, create)
- `read_only_fields` explicites
- Validation dans serializer, pas dans views
- Pas de logique métier dans serializers (uniquement validation)

**INTERDIT** :
```python
# ❌ Exposer tous les champs sans contrôle
class CopySerializer(serializers.ModelSerializer):
    class Meta:
        model = Copy
        fields = '__all__'  # ❌ Dangereux

# ❌ Logique métier dans serializer
def create(self, validated_data):
    copy = Copy.objects.create(**validated_data)
    send_email_notification(copy)  # ❌ Logique métier
    return copy
```

### 4.2 ViewSets et Views

**OBLIGATOIRE** :
```python
# ✅ Bon exemple
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

class CopyViewSet(viewsets.ModelViewSet):
    queryset = Copy.objects.all()
    serializer_class = CopySerializer
    permission_classes = [permissions.IsAuthenticated, IsProfessor]

    def get_queryset(self):
        # Filtrage par utilisateur
        user = self.request.user
        if user.is_superuser:
            return Copy.objects.all()
        return Copy.objects.filter(assigned_to=user)

    def get_serializer_class(self):
        # Serializer différent selon action
        if self.action == 'list':
            return CopyListSerializer
        return CopyDetailSerializer

    @action(detail=True, methods=['post'], permission_classes=[IsProfessor])
    def lock(self, request, pk=None):
        copy = self.get_object()
        # Déléguer à un service
        result = CopyService.lock_copy(copy, request.user)
        return Response(result)
```

**Règles** :
- Permissions explicites sur le ViewSet
- `get_queryset()` pour filtrage par utilisateur
- Pas de logique métier dans les views (déléguer à services)
- Actions custom via `@action` decorator

**INTERDIT** :
```python
# ❌ Logique métier dans view
def lock(self, request, pk=None):
    copy = self.get_object()
    copy.status = Copy.Status.LOCKED
    copy.locked_by = request.user
    copy.locked_at = timezone.now()
    copy.save()
    # Envoyer email, logger, etc.
    return Response(...)
```

### 4.3 Permissions

**OBLIGATOIRE** :
```python
# ✅ Bon exemple
from rest_framework import permissions

class IsProfessor(permissions.BasePermission):
    """
    Permission pour professeurs uniquement.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff

class IsCopyOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission objet : propriétaire peut modifier, autres lecture seule.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.assigned_to == request.user
```

**Règles** :
- Permission class par rôle
- `has_permission()` pour permissions générales
- `has_object_permission()` pour permissions objet
- Messages d'erreur clairs mais pas trop détaillés

---

## 5. Services Layer

### 5.1 Quand Utiliser un Service

**OBLIGATOIRE pour** :
- Logique métier complexe (>20 lignes)
- Opérations multi-modèles
- Opérations transactionnelles
- Appels externes (API, file system)

**Structure** :
```python
# exams/services.py
from django.db import transaction

class CopyService:
    @staticmethod
    @transaction.atomic
    def lock_copy(copy, professor):
        """
        Verrouille une copie pour correction.
        """
        if copy.status != Copy.Status.READY:
            raise ValueError("Copy is not ready to be locked")

        copy.status = Copy.Status.LOCKED
        copy.locked_by = professor
        copy.locked_at = timezone.now()
        copy.save()

        # Logging
        logger.info(f"Copy {copy.id} locked by {professor.username}")

        return {
            'success': True,
            'copy_id': str(copy.id),
            'locked_at': copy.locked_at
        }

    @staticmethod
    @transaction.atomic
    def finalize_grading(copy, scores_data, final_comment):
        """
        Finalise la correction d'une copie.
        """
        # Vérifications
        if copy.status != Copy.Status.LOCKED:
            raise ValueError("Copy must be locked to finalize grading")

        # Créer Score
        score = Score.objects.create(
            copy=copy,
            scores_data=scores_data,
            final_comment=final_comment
        )

        # Mettre à jour statut
        copy.status = Copy.Status.GRADED
        copy.graded_at = timezone.now()
        copy.save()

        # Export PDF avec annotations (via service)
        PDFExportService.generate_final_pdf(copy)

        return score
```

**Règles** :
- Méthodes statiques ou de classe
- Transactions atomiques pour opérations critiques
- Logging des opérations importantes
- Retour de dictionnaires structurés
- Exceptions explicites

---

## 6. Transactions et Atomicité

### 6.1 Transactions Atomiques

**OBLIGATOIRE pour** :
- Modifications multi-modèles
- Opérations critiques (lock, grading, finalization)
- Cohérence de données garantie

**Code de Référence** :
```python
from django.db import transaction

@transaction.atomic
def create_copies_from_booklets(exam, booklets_mapping):
    """
    Crée des copies à partir de booklets validés.
    """
    copies = []
    for anonymous_id, booklet_ids in booklets_mapping.items():
        # Récupérer booklets
        booklets = Booklet.objects.filter(id__in=booklet_ids, exam=exam)

        # Créer PDF final
        final_pdf = merge_booklets_to_pdf(booklets)

        # Créer copie
        copy = Copy.objects.create(
            exam=exam,
            anonymous_id=anonymous_id,
            final_pdf=final_pdf,
            status=Copy.Status.READY
        )

        # Associer booklets
        copy.booklets.set(booklets)

        copies.append(copy)

    return copies
```

**Règles** :
- Decorator `@transaction.atomic` sur fonction/méthode
- Si erreur, rollback automatique
- Pas de commits partiels

**INTERDIT** :
```python
# ❌ Pas de transaction
def create_copies_from_booklets(exam, booklets_mapping):
    for anonymous_id, booklet_ids in booklets_mapping.items():
        copy = Copy.objects.create(...)  # Si erreur ici, copies précédentes restent
        copy.booklets.set(booklets)       # Incohérence possible
```

---

## 7. Queries et Performance

### 7.1 Optimisation Queries

**OBLIGATOIRE** :
```python
# ✅ Bon - select_related pour ForeignKey
copies = Copy.objects.select_related('exam', 'student').all()

# ✅ Bon - prefetch_related pour ManyToMany/Reverse FK
copies = Copy.objects.prefetch_related('booklets', 'annotations').all()

# ✅ Bon - Combinaison
copies = Copy.objects.select_related('exam').prefetch_related('annotations').all()
```

**INTERDIT** :
```python
# ❌ N+1 query problem
copies = Copy.objects.all()
for copy in copies:
    print(copy.exam.name)  # Query par itération!
```

### 7.2 Pagination

**OBLIGATOIRE** :
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50
}
```

---

## 8. Celery Tasks

### 8.1 Tâches Asynchrones

**OBLIGATOIRE pour** :
- Traitement PDF (split, merge, export)
- Envoi d'emails
- Opérations longues (>5 secondes)

**Code de Référence** :
```python
# processing/tasks.py
from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_exam_pdf(self, exam_id):
    """
    Traite le PDF d'un examen (split en booklets).
    """
    try:
        exam = Exam.objects.get(id=exam_id)

        # Traitement
        booklets = PDFSplitter.split_exam(exam)

        # Mise à jour
        exam.is_processed = True
        exam.save()

        logger.info(f"Exam {exam_id} processed: {len(booklets)} booklets created")
        return {'success': True, 'booklets_count': len(booklets)}

    except Exception as exc:
        logger.error(f"Error processing exam {exam_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)  # Retry après 60s
```

**Règles** :
- Décorateur `@shared_task`
- Bind pour accès à self (retry)
- Logging des erreurs
- Retry policy configurée
- Pas de dépendance request dans task

---

## 9. Tests

### 9.1 Tests Obligatoires

**OBLIGATOIRE** :
- Tests unitaires pour models (méthodes custom)
- Tests pour services (logique métier)
- Tests pour permissions
- Tests pour serializers (validation)
- Tests d'intégration pour endpoints critiques

**Structure** :
```python
# exams/tests/test_services.py
from django.test import TestCase
from exams.models import Copy, Exam
from exams.services import CopyService

class CopyServiceTest(TestCase):
    def setUp(self):
        self.exam = Exam.objects.create(name="Test Exam")
        self.copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id="TEST001",
            status=Copy.Status.READY
        )

    def test_lock_copy_success(self):
        user = User.objects.create(username="prof1", is_staff=True)
        result = CopyService.lock_copy(self.copy, user)

        self.copy.refresh_from_db()
        self.assertEqual(self.copy.status, Copy.Status.LOCKED)
        self.assertEqual(self.copy.locked_by, user)
        self.assertTrue(result['success'])

    def test_lock_copy_invalid_status(self):
        self.copy.status = Copy.Status.LOCKED
        self.copy.save()

        with self.assertRaises(ValueError):
            CopyService.lock_copy(self.copy, user)
```

---

## 10. Checklist Backend

Avant tout commit backend :
- [ ] Permissions explicites sur tous les endpoints
- [ ] Migrations créées pour changements de modèles
- [ ] Logique métier dans services, pas dans views
- [ ] Transactions atomiques pour opérations critiques
- [ ] Queries optimisées (select_related / prefetch_related)
- [ ] Tests passent
- [ ] Logging approprié
- [ ] Validation des entrées

---

**Version** : 1.0
**Date** : 2026-01-21
**Statut** : Obligatoire
