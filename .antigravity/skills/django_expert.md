# Skill: Django Expert

## Quand Activer Ce Skill

Ce skill doit être activé pour :
- Création ou modification de modèles Django
- Création de migrations
- Problèmes avec l'ORM Django
- Configuration Django (settings, middleware, apps)
- Optimisation de queries
- Django Admin customization
- Gestion des transactions
- Signals Django

## Responsabilités

En tant que **Django Expert**, vous devez :

### 1. Modèles et ORM

- **Concevoir** des modèles Django robustes et normalisés
- **Définir** les relations appropriées (FK, M2M, O2O)
- **Utiliser** l'ORM efficacement (éviter N+1, utiliser select_related/prefetch_related)
- **Gérer** les contraintes DB-level (UniqueConstraint, CheckConstraint)
- **Implémenter** les indexes pour performance
- **Respecter** les conventions Django (Meta, __str__, etc.)

### 2. Migrations

- **Créer** des migrations atomiques et réversibles
- **Nommer** les migrations explicitement
- **Gérer** les migrations de données (RunPython)
- **Tester** les migrations avant production
- **Éviter** les migrations destructives non documentées
- **Squasher** les migrations si nécessaire

### 3. QuerySets et Performance

- **Optimiser** les queries avec select_related/prefetch_related
- **Utiliser** annotations et aggregations
- **Implémenter** le caching approprié
- **Lazy loading** vs eager loading selon contexte
- **Éviter** les queries en boucle
- **Monitorer** avec Django Debug Toolbar

### 4. Transactions

- **Utiliser** @transaction.atomic pour opérations critiques
- **Gérer** les rollbacks correctement
- **Éviter** les side effects dans transactions
- **Comprendre** les niveaux d'isolation
- **Tester** les conditions d'erreur

### 5. Django REST Framework

- **Créer** des serializers efficaces et sécurisés
- **Implémenter** des ViewSets/APIViews appropriés
- **Gérer** les permissions granulaires
- **Optimiser** les queries dans ViewSets
- **Utiliser** les features DRF (pagination, filtering, throttling)

## Patterns Django

### Pattern 1 : Service Layer

**Quand** : Logique métier complexe

**Implémentation** :
```python
# app/services.py
class CopyService:
    @staticmethod
    @transaction.atomic
    def lock_copy(copy, user):
        if copy.status != Copy.Status.READY:
            raise ValueError("Copy not ready")

        copy.status = Copy.Status.LOCKED
        copy.locked_by = user
        copy.locked_at = timezone.now()
        copy.save(update_fields=['status', 'locked_by', 'locked_at'])

        logger.info(f"Copy {copy.id} locked by {user}")
        return copy

# app/views.py
class CopyViewSet(viewsets.ModelViewSet):
    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        copy = self.get_object()
        try:
            CopyService.lock_copy(copy, request.user)
            return Response({'success': True})
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
```

### Pattern 2 : QuerySet Methods

**Quand** : Filtres réutilisables

**Implémentation** :
```python
# app/models.py
class CopyQuerySet(models.QuerySet):
    def ready_for_grading(self):
        return self.filter(status=Copy.Status.READY)

    def locked_by_user(self, user):
        return self.filter(status=Copy.Status.LOCKED, locked_by=user)

    def for_exam(self, exam):
        return self.filter(exam=exam)

class Copy(models.Model):
    objects = CopyQuerySet.as_manager()

# Usage
copies = Copy.objects.ready_for_grading().for_exam(exam)
my_locked = Copy.objects.locked_by_user(request.user)
```

### Pattern 3 : Select/Prefetch Related

**Quand** : Éviter N+1 queries

**Implémentation** :
```python
# ❌ Bad - N+1 problem
copies = Copy.objects.all()
for copy in copies:
    print(copy.exam.name)  # Query!
    print(copy.student.name)  # Query!

# ✅ Good - Optimized
copies = Copy.objects.select_related('exam', 'student').all()
for copy in copies:
    print(copy.exam.name)  # No query
    print(copy.student.name)  # No query

# ✅ Good - M2M and reverse FK
copies = Copy.objects.prefetch_related('booklets', 'annotations').all()
for copy in copies:
    for booklet in copy.booklets.all():  # No query
        print(booklet.start_page)
```

## Checklist Modèle Django

Pour chaque nouveau modèle :
- [ ] UUID pour PK si exposé publiquement
- [ ] ForeignKey avec on_delete explicite
- [ ] related_name défini pour toutes les relations
- [ ] verbose_name sur tous les champs
- [ ] Meta class avec verbose_name, verbose_name_plural, ordering
- [ ] __str__() méthode implémentée
- [ ] created_at/updated_at si pertinent
- [ ] Indexes ajoutés pour champs filtrés fréquemment
- [ ] Contraintes DB-level ajoutées (unique, check)

## Checklist Migration

Pour chaque migration :
- [ ] Migration nommée explicitement (--name)
- [ ] Migration revue (fichier généré)
- [ ] Migration testée localement
- [ ] Migration réversible (ou non-réversible documenté)
- [ ] Pas de perte de données (ou acceptée et documentée)
- [ ] Migration de données si nécessaire (RunPython)
- [ ] Performance acceptable (si gros volumes)

## Optimisations Communes

### Problème : Requête Lente

**Diagnostic** :
```python
from django.db import connection
from django.test.utils import override_settings

@override_settings(DEBUG=True)
def test_query_performance():
    copies = Copy.objects.all()
    for copy in copies:
        print(copy.exam.name)

    print(f"Queries: {len(connection.queries)}")
    for query in connection.queries:
        print(query['sql'])
```

**Solution** :
```python
# Ajouter select_related
copies = Copy.objects.select_related('exam').all()
```

### Problème : Trop de Données

**Solution** : Pagination
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50
}
```

### Problème : Queries Complexes

**Solution** : Annotations
```python
from django.db.models import Count, Q

exams = Exam.objects.annotate(
    total_copies=Count('copies'),
    graded_copies=Count('copies', filter=Q(copies__status='GRADED')),
    ready_copies=Count('copies', filter=Q(copies__status='READY'))
)

for exam in exams:
    print(f"{exam.name}: {exam.graded_copies}/{exam.total_copies} graded")
```

## Django Admin Customization

### Custom List Display

```python
# app/admin.py
from django.contrib import admin

@admin.register(Copy)
class CopyAdmin(admin.ModelAdmin):
    list_display = ['anonymous_id', 'exam', 'status', 'created_at', 'is_graded']
    list_filter = ['status', 'exam', 'created_at']
    search_fields = ['anonymous_id', 'exam__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'

    def is_graded(self, obj):
        return obj.status == Copy.Status.GRADED
    is_graded.boolean = True
    is_graded.short_description = 'Graded?'
```

## Signaux Django

**Quand Utiliser** : Side effects décorrélés

**Exemple** :
```python
# app/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Copy)
def copy_post_save(sender, instance, created, **kwargs):
    if created:
        logger.info(f"New copy created: {instance.id}")

    if instance.status == Copy.Status.GRADED:
        # Notifier l'élève (async)
        from .tasks import notify_student_copy_graded
        notify_student_copy_graded.delay(instance.id)

# app/apps.py
class ExamsConfig(AppConfig):
    def ready(self):
        import exams.signals
```

**ATTENTION** : Éviter les signals pour logique critique (préférer services explicites)

## Tests Django

### Test Modèle

```python
from django.test import TestCase

class CopyModelTest(TestCase):
    def test_copy_str_representation(self):
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='TEST001'
        )
        self.assertEqual(str(copy), 'Copie TEST001')

    def test_copy_status_transition(self):
        copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id='TEST001',
            status=Copy.Status.READY
        )
        copy.status = Copy.Status.LOCKED
        copy.save()

        copy.refresh_from_db()
        self.assertEqual(copy.status, Copy.Status.LOCKED)
```

### Test API

```python
from rest_framework.test import APITestCase

class CopyAPITest(APITestCase):
    def test_list_copies_requires_authentication(self):
        response = self.client.get('/api/copies/')
        self.assertEqual(response.status_code, 401)

    def test_professor_can_list_their_copies(self):
        self.client.force_authenticate(user=self.professor)
        response = self.client.get('/api/copies/')
        self.assertEqual(response.status_code, 200)
```

## Références

- Django Documentation : https://docs.djangoproject.com/
- Django ORM Cookbook : https://books.agiliq.com/projects/django-orm-cookbook/
- DRF Documentation : https://www.django-rest-framework.org/
- Two Scoops of Django (livre)

---

**Activation** : Automatique pour code Django
**Priorité** : Haute
**Version** : 1.0
