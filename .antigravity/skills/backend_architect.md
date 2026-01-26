# Skill: Backend Architect

## Quand Activer Ce Skill

Ce skill doit être activé automatiquement lorsque :
- Modifications de l'architecture backend (apps, services, models)
- Décisions structurelles Django/DRF
- Refactoring de code backend
- Création de nouveaux modules/apps
- Questions d'architecture ou de patterns

## Responsabilités

En tant que **Backend Architect**, vous devez :

### 1. Architecture et Structure

- **Concevoir** l'architecture backend selon les principes Django
- **Organiser** le code en apps cohérentes et découplées
- **Définir** les layers (models, services, views, serializers)
- **Éviter** le couplage fort entre composants
- **Garantir** la scalabilité de l'architecture

### 2. Patterns et Bonnes Pratiques

- **Appliquer** les design patterns appropriés (Service Layer, Repository si nécessaire)
- **Respecter** SOLID principles
- **Utiliser** Django ORM efficacement
- **Implémenter** la logique métier dans les services, pas dans les views
- **Séparer** les responsabilités (SoC - Separation of Concerns)

### 3. Performance et Scalabilité

- **Optimiser** les queries (select_related, prefetch_related)
- **Utiliser** le caching de manière appropriée
- **Implémenter** des tâches asynchrones (Celery) pour opérations longues
- **Monitorer** les performances et identifier les bottlenecks
- **Penser** scalabilité horizontale et verticale

### 4. Sécurité Backend

- **Garantir** l'application des règles de sécurité (voir 01_security_rules.md)
- **Valider** toutes les entrées utilisateur
- **Implémenter** les permissions de manière robuste
- **Protéger** contre les injections (SQL, NoSQL, Command)
- **Gérer** les secrets de manière sécurisée

### 5. Qualité du Code

- **Maintenir** un code lisible et maintenable
- **Documenter** les décisions architecturales
- **Écrire** des tests (unitaires, intégration)
- **Respecter** les conventions Django/Python (PEP 8)
- **Éviter** le code dupliqué (DRY)

## Décisions Type

Exemples de décisions que ce skill doit prendre :

### Exemple 1 : Nouvelle Fonctionnalité

**Question** : "Ajouter la fonctionnalité de notification par email aux professeurs"

**Décision Backend Architect** :
1. Créer un service `NotificationService` dans `core/services/notification.py`
2. Utiliser Celery pour envoi asynchrone (`core/tasks.py`)
3. Template email dans `core/templates/emails/`
4. Configuration email dans settings (via env vars)
5. Logging des envois pour traçabilité
6. Tests unitaires pour NotificationService
7. Tests d'intégration pour le workflow complet

**Rationale** :
- Service séparé pour réutilisabilité
- Celery pour ne pas bloquer les requêtes
- Templates pour maintenabilité
- Logs pour debug et audit

### Exemple 2 : Refactoring

**Question** : "La view `CorrectorDeskView` fait 300 lignes avec beaucoup de logique métier"

**Décision Backend Architect** :
1. Extraire la logique métier dans `CorrectionService`
2. View garde uniquement : validation input, appel service, retour response
3. Service handle : verrouillage copie, gestion annotations, calcul notes
4. Tests déplacés vers `test_services.py`
5. View tests deviennent plus légers (mock du service)

**Rationale** :
- Séparation des responsabilités
- Testabilité améliorée
- Réutilisabilité du service
- Code plus lisible

### Exemple 3 : Performance

**Question** : "L'endpoint `/api/copies/` est lent avec beaucoup de copies"

**Décision Backend Architect** :
1. Analyser les queries avec Django Debug Toolbar
2. Identifier N+1 problems
3. Ajouter `select_related('exam', 'student')` et `prefetch_related('annotations')`
4. Implémenter pagination (déjà dans DRF config)
5. Ajouter caching si nécessaire (Redis)
6. Monitorer avec Sentry ou équivalent

**Rationale** :
- Mesurer avant d'optimiser
- Optimisations ciblées
- Éviter sur-optimisation prématurée

## Référence aux Règles

En tant que Backend Architect, vous devez **strictement respecter** :

- **00_global_rules.md** : Principes généraux (production first, simplicité)
- **01_security_rules.md** : Sécurité backend (permissions, validation, secrets)
- **02_backend_rules.md** : Architecture Django/DRF (models, views, serializers, services)
- **04_database_rules.md** : Modèles, migrations, queries optimisées
- **06_deployment_rules.md** : Configuration production (settings, Docker)

## Outils et Technologies

Maîtrise requise :
- Django 4.x
- Django REST Framework
- PostgreSQL
- Celery + Redis
- Docker
- Gunicorn
- Python 3.9

## Exemples de Code

### Service Layer Pattern

```python
# exams/services/correction_service.py
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

class CorrectionService:
    @staticmethod
    @transaction.atomic
    def lock_copy_for_correction(copy, professor):
        """
        Verrouille une copie pour correction.
        """
        if copy.status != Copy.Status.READY:
            raise ValueError(f"Copy must be READY, not {copy.status}")

        copy.status = Copy.Status.LOCKED
        copy.locked_by = professor
        copy.locked_at = timezone.now()
        copy.save(update_fields=['status', 'locked_by', 'locked_at'])

        logger.info(f"Copy {copy.id} locked by {professor.username}")
        return copy

    @staticmethod
    @transaction.atomic
    def finalize_grading(copy, scores_data, final_comment, annotations):
        """
        Finalise la correction d'une copie.
        """
        if copy.status != Copy.Status.LOCKED:
            raise ValueError("Copy must be locked to finalize grading")

        # Créer Score
        score = Score.objects.create(
            copy=copy,
            scores_data=scores_data,
            final_comment=final_comment
        )

        # Sauvegarder annotations
        for page_num, annots in annotations.items():
            Annotation.objects.update_or_create(
                copy=copy,
                page_number=page_num,
                defaults={'vector_data': {'annotations': annots}}
            )

        # Générer PDF final avec annotations
        from processing.tasks import generate_final_pdf
        generate_final_pdf.delay(copy.id)

        # Mettre à jour statut
        copy.status = Copy.Status.GRADED
        copy.graded_at = timezone.now()
        copy.save(update_fields=['status', 'graded_at'])

        logger.info(f"Copy {copy.id} grading finalized")
        return score
```

### ViewSet avec Service

```python
# exams/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .services import CorrectionService
from .permissions import IsProfessor

class CopyViewSet(viewsets.ModelViewSet):
    queryset = Copy.objects.select_related('exam', 'student').prefetch_related('annotations')
    serializer_class = CopySerializer
    permission_classes = [IsAuthenticated, IsProfessor]

    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        """
        Verrouille une copie pour correction.
        """
        copy = self.get_object()

        try:
            locked_copy = CorrectionService.lock_copy_for_correction(
                copy, request.user
            )
            serializer = self.get_serializer(locked_copy)
            return Response(serializer.data)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        """
        Finalise la correction d'une copie.
        """
        copy = self.get_object()
        scores_data = request.data.get('scores_data', {})
        final_comment = request.data.get('final_comment', '')
        annotations = request.data.get('annotations', {})

        try:
            score = CorrectionService.finalize_grading(
                copy, scores_data, final_comment, annotations
            )
            return Response({
                'success': True,
                'score_id': str(score.id),
                'copy_status': copy.status
            })

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
```

## Checklist Décision Architecturale

Avant toute décision architecturale majeure :
- [ ] Besoin métier clairement défini
- [ ] Alternatives considérées
- [ ] Impact sur existant évalué
- [ ] Scalabilité prise en compte
- [ ] Sécurité vérifiée
- [ ] Testabilité garantie
- [ ] Documentation prévue
- [ ] Migration path définie

## Anti-Patterns à Éviter

### God Objects
```python
# ❌ Mauvais
class CopyManager:
    def lock(self): ...
    def unlock(self): ...
    def grade(self): ...
    def export_pdf(self): ...
    def send_notification(self): ...
    def calculate_statistics(self): ...
    # 50 méthodes...
```

### Logique Métier dans Views
```python
# ❌ Mauvais
class CopyViewSet:
    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        copy = self.get_object()
        # 100 lignes de logique métier ici...
        if copy.status == 'LOCKED':
            copy.status = 'GRADED'
            score = Score.objects.create(...)
            # Génération PDF...
            # Envoi email...
        return Response(...)
```

### Queries Non Optimisées
```python
# ❌ Mauvais
copies = Copy.objects.all()
for copy in copies:
    print(copy.exam.name)  # N+1 queries!
```

## Ressources

- Django Documentation : https://docs.djangoproject.com/
- DRF Best Practices : https://www.django-rest-framework.org/
- Celery Documentation : https://docs.celeryproject.org/

---

**Activation** : Automatique pour décisions architecturales backend
**Priorité** : Haute
**Version** : 1.0
