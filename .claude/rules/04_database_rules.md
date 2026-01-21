# Règles Base de Données et Migrations - Viatique

## Statut : OBLIGATOIRE

Ces règles garantissent l'intégrité des données et la cohérence des modèles/migrations.

---

## 1. Principes Fondamentaux

### 1.1 Intégrité des Données

**OBLIGATOIRE** :
- Cohérence modèles ↔ base de données via migrations
- Constraints de base de données respectés
- Transactions pour opérations multi-tables
- Pas de perte de données lors de migrations

**INTERDIT** :
- Modifier un modèle sans migration
- Supprimer des données sans backup
- Migrations non testées en production
- Incohérences modèles/DB

---

## 2. Modèles Django

### 2.1 Conventions de Nommage

**OBLIGATOIRE** :
```python
# ✅ Bon exemple - Nommage cohérent
class Copy(models.Model):
    # Singular pour model name
    # snake_case pour champs
    anonymous_id = models.CharField(...)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Plural pour verbose_name_plural
        verbose_name = "Copie"
        verbose_name_plural = "Copies"
        # Table name auto: exams_copy
        db_table = 'exams_copy'  # Explicite si nécessaire
```

**Conventions** :
- **Model** : Singular, PascalCase (`Copy`, `Exam`, `Student`)
- **Champs** : snake_case (`anonymous_id`, `created_at`)
- **Relations** : snake_case, descriptives (`assigned_to`, `locked_by`)
- **Tables** : app_modelname (auto) ou explicite via `db_table`

### 2.2 Identifiants

**OBLIGATOIRE pour IDs Exposés** :
```python
import uuid

class Copy(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
```

**Raisons** :
- Pas d'énumération possible (sécurité)
- IDs uniques même entre bases
- Pas de collision lors de merges

**EXCEPTION** :
- Auto-increment OK pour tables internes jamais exposées
- Performance critique nécessitant int

### 2.3 Champs Obligatoires

**Traçabilité** :
```python
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class Copy(BaseModel):
    # Hérite created_at, updated_at
    ...
```

**OBLIGATOIRE pour Modèles Importants** :
- `created_at` : Timestamp de création
- `updated_at` : Timestamp de dernière modification
- `created_by` / `updated_by` si audit nécessaire

---

## 3. Relations

### 3.1 ForeignKey

**OBLIGATOIRE** :
```python
class Copy(models.Model):
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,     # ✅ Explicite
        related_name='copies',         # ✅ Toujours nommer
        verbose_name="Examen",
        db_index=True                  # ✅ Index pour perfs
    )

    student = models.ForeignKey(
        'students.Student',            # ✅ String si autre app
        on_delete=models.SET_NULL,
        null=True,                     # ✅ Cohérent avec SET_NULL
        blank=True,
        related_name='copies'
    )
```

**Règles on_delete** :
- `CASCADE` : Suppression en cascade (exam → copies)
- `SET_NULL` : Null si parent supprimé (student → copies, optionnel)
- `PROTECT` : Empêcher suppression si enfants existent
- `SET_DEFAULT` : Valeur par défaut (rare)
- **JAMAIS** : `on_delete` omis (erreur Python)

**related_name** :
- Toujours explicite
- Plural si OneToMany (`exam.copies`)
- Éviter `+` (désactive reverse relation)

### 3.2 ManyToManyField

**OBLIGATOIRE** :
```python
class Copy(models.Model):
    booklets = models.ManyToManyField(
        Booklet,
        related_name='assigned_copy',  # ✅ Singular (une copy par booklet)
        verbose_name="Fascicules composants",
        blank=True                      # ✅ M2M souvent optionnel
    )
```

**Avec Table Intermédiaire Custom** :
```python
class CopyBooklet(models.Model):
    copy = models.ForeignKey(Copy, on_delete=models.CASCADE)
    booklet = models.ForeignKey(Booklet, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()  # Ordre des booklets
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['copy', 'booklet']]
        ordering = ['order']

class Copy(models.Model):
    booklets = models.ManyToManyField(
        Booklet,
        through='CopyBooklet',
        related_name='assigned_copy'
    )
```

**Quand Utiliser `through`** :
- Besoin de champs supplémentaires (order, date, metadata)
- Contraintes spécifiques
- Audit trail

---

## 4. Indexes et Performance

### 4.1 Indexes

**OBLIGATOIRE** :
```python
class Copy(models.Model):
    anonymous_id = models.CharField(
        max_length=50,
        unique=True,        # ✅ Crée un index unique
        db_index=True       # ✅ Redondant ici mais explicite
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        db_index=True       # ✅ Filtrage fréquent
    )

    class Meta:
        indexes = [
            # ✅ Index composite pour queries fréquentes
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['exam', 'status']),
        ]
```

**Quand Indexer** :
- Champs utilisés dans `filter()`, `get()`, `exclude()`
- Champs de ForeignKey (auto si `db_index=True`)
- Champs utilisés dans `order_by()`
- Champs uniques (index automatique)

**ATTENTION** :
- Trop d'indexes ralentit les writes
- Indexes composites pour queries spécifiques
- Analyser les queries lentes (EXPLAIN)

### 4.2 Contraintes

**OBLIGATOIRE** :
```python
class Copy(models.Model):
    class Meta:
        constraints = [
            # ✅ Contrainte unique composée
            models.UniqueConstraint(
                fields=['exam', 'anonymous_id'],
                name='unique_anonymous_id_per_exam'
            ),
            # ✅ Check constraint
            models.CheckConstraint(
                check=models.Q(status__in=['STAGING', 'READY', 'LOCKED', 'GRADED']),
                name='valid_status'
            )
        ]
```

**Types de Contraintes** :
- `UniqueConstraint` : Unicité (simple ou composée)
- `CheckConstraint` : Validation DB-level
- `Index` : Performance

---

## 5. Migrations

### 5.1 Création de Migration

**OBLIGATOIRE** :
```bash
# ✅ Bon - Nom explicite
python manage.py makemigrations --name add_student_to_copy exams

# ✅ Bon - Vérifier la migration générée
cat backend/exams/migrations/0003_add_student_to_copy.py

# ✅ Bon - Tester localement
python manage.py migrate

# ❌ Mauvais - Nom auto seulement
python manage.py makemigrations
```

**Workflow** :
1. Modifier le modèle
2. Créer migration avec nom explicite
3. Vérifier le fichier généré
4. Tester en local
5. Commit avec modèle + migration

### 5.2 Règles de Migration

**INTERDIT ABSOLUMENT** :
```python
# ❌ JAMAIS éditer une migration déjà appliquée en production
# Si erreur: créer une nouvelle migration corrective

# ❌ JAMAIS supprimer des migrations existantes
# Si nécessaire: squash migrations (Django command)

# ❌ JAMAIS modifier les dépendances manuellement sans comprendre
dependencies = [
    ('exams', '0002_previous_migration'),  # Doit être cohérent
]
```

**OBLIGATOIRE** :
- Migrations séquentielles (dependencies respectées)
- Une migration par changement logique
- Migrations réversibles quand possible
- Backup avant migration en production

### 5.3 Migrations de Données

**OBLIGATOIRE** :
```python
# ✅ Bon exemple - Migration de données
from django.db import migrations

def populate_anonymous_ids(apps, schema_editor):
    """
    Génère des anonymous_id pour copies existantes.
    """
    Copy = apps.get_model('exams', 'Copy')
    for copy in Copy.objects.filter(anonymous_id__isnull=True):
        copy.anonymous_id = f"ANON-{copy.id}"
        copy.save(update_fields=['anonymous_id'])

def reverse_populate(apps, schema_editor):
    """
    Reverse: remettre à None (si nécessaire).
    """
    Copy = apps.get_model('exams', 'Copy')
    Copy.objects.all().update(anonymous_id=None)

class Migration(migrations.Migration):
    dependencies = [
        ('exams', '0002_add_anonymous_id_field'),
    ]

    operations = [
        migrations.RunPython(
            populate_anonymous_ids,
            reverse_populate
        ),
    ]
```

**Règles** :
- Utiliser `apps.get_model()` (pas d'import direct)
- Fonction forward et reverse
- Batch processing pour gros volumes
- Logging des opérations

### 5.4 Migrations Destructives

**OBLIGATOIRE** :
```python
# ⚠️ Migration destructive (perte de données)
class Migration(migrations.Migration):
    operations = [
        # ⚠️ ATTENTION: Suppression de colonne
        migrations.RemoveField(
            model_name='copy',
            name='old_field',
        ),
    ]

# 📝 DOCUMENTER dans le commit message:
# "Migration destructive: supprime old_field (plus utilisé depuis v2.0)"
# "Backup effectué avant migration"
```

**Process pour Migrations Destructives** :
1. **Backup DB complet**
2. **Documentation explicite**
3. **Validation en staging**
4. **Fenêtre de maintenance si critique**
5. **Rollback plan préparé**

---

## 6. Requêtes Optimisées

### 6.1 N+1 Problem

**INTERDIT** :
```python
# ❌ N+1 queries problem
copies = Copy.objects.all()
for copy in copies:
    print(copy.exam.name)        # Query par itération!
    print(copy.student.name)     # Query par itération!
    for booklet in copy.booklets.all():  # Query par itération!
        print(booklet.start_page)
```

**OBLIGATOIRE** :
```python
# ✅ Bon - select_related pour ForeignKey (JOIN)
copies = Copy.objects.select_related('exam', 'student').all()

# ✅ Bon - prefetch_related pour ManyToMany/Reverse FK
copies = Copy.objects.prefetch_related('booklets', 'annotations').all()

# ✅ Bon - Combinaison
copies = Copy.objects.select_related('exam', 'student') \
                     .prefetch_related('booklets', 'annotations') \
                     .all()

for copy in copies:
    print(copy.exam.name)        # Pas de query
    print(copy.student.name)     # Pas de query
    for booklet in copy.booklets.all():  # Pas de query
        print(booklet.start_page)
```

**Règle Mnémotechnique** :
- `select_related` : ForeignKey, OneToOne (JOIN SQL)
- `prefetch_related` : ManyToMany, Reverse FK (2 queries)

### 6.2 Queries Complexes

**OBLIGATOIRE** :
```python
from django.db.models import Q, Count, Prefetch

# ✅ Bon - Q objects pour OR
copies = Copy.objects.filter(
    Q(status='READY') | Q(status='LOCKED'),
    exam=exam
)

# ✅ Bon - Annotations
exams = Exam.objects.annotate(
    copies_count=Count('copies'),
    graded_count=Count('copies', filter=Q(copies__status='GRADED'))
)

# ✅ Bon - Prefetch custom
booklets_prefetch = Prefetch(
    'booklets',
    queryset=Booklet.objects.order_by('start_page')
)
copies = Copy.objects.prefetch_related(booklets_prefetch)
```

### 6.3 Bulk Operations

**OBLIGATOIRE pour Volumes Importants** :
```python
# ✅ Bon - bulk_create
copies = [
    Copy(exam=exam, anonymous_id=f"ANON-{i}")
    for i in range(1000)
]
Copy.objects.bulk_create(copies, batch_size=100)

# ✅ Bon - bulk_update
for copy in copies:
    copy.status = 'READY'
Copy.objects.bulk_update(copies, ['status'], batch_size=100)

# ❌ Mauvais - Loop avec save()
for i in range(1000):
    Copy.objects.create(...)  # 1000 queries!
```

---

## 7. Transactions

### 7.1 Atomicité

**OBLIGATOIRE pour Opérations Critiques** :
```python
from django.db import transaction

@transaction.atomic
def create_copies_from_booklets(exam, booklets_mapping):
    """
    Crée des copies à partir de booklets.
    Si erreur: rollback complet.
    """
    copies = []
    for anonymous_id, booklet_ids in booklets_mapping.items():
        booklets = Booklet.objects.filter(id__in=booklet_ids)

        copy = Copy.objects.create(
            exam=exam,
            anonymous_id=anonymous_id,
            status=Copy.Status.READY
        )

        copy.booklets.set(booklets)
        copies.append(copy)

    return copies
```

**Règles** :
- Decorator `@transaction.atomic` sur fonction
- Rollback automatique si exception
- Commit uniquement si succès complet

**ATTENTION** :
```python
# ⚠️ Transaction avec side effects
@transaction.atomic
def process_copy(copy):
    copy.status = 'GRADED'
    copy.save()

    # ⚠️ Si cette partie échoue, DB rollback mais email envoyé!
    send_email_notification(copy)  # Side effect non transactionnel

# ✅ Meilleur: Side effects APRÈS transaction
@transaction.atomic
def process_copy_db(copy):
    copy.status = 'GRADED'
    copy.save()

def process_copy(copy):
    process_copy_db(copy)
    send_email_notification(copy)  # Après commit DB
```

---

## 8. Schéma de Base de Données

### 8.1 Structure Actuelle Viatique

**Tables Principales** :
```
exams_exam
├── id (UUID, PK)
├── name (VARCHAR)
├── date (DATE)
├── pdf_source (FILE)
├── grading_structure (JSON)
├── is_processed (BOOLEAN)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

exams_booklet
├── id (UUID, PK)
├── exam_id (UUID, FK → exams_exam)
├── start_page (INTEGER)
├── end_page (INTEGER)
├── header_image (FILE)
├── student_name_guess (VARCHAR)
├── pages_images (JSON)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

exams_copy
├── id (UUID, PK)
├── exam_id (UUID, FK → exams_exam)
├── student_id (UUID, FK → students_student, NULL)
├── anonymous_id (VARCHAR, UNIQUE)
├── final_pdf (FILE)
├── status (VARCHAR)
├── is_identified (BOOLEAN)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

exams_copy_booklets (M2M)
├── id (INTEGER, PK)
├── copy_id (UUID, FK → exams_copy)
└── booklet_id (UUID, FK → exams_booklet)

students_student
├── id (INTEGER, PK)
├── ine (VARCHAR, UNIQUE)
├── first_name (VARCHAR)
├── last_name (VARCHAR)
├── class_name (VARCHAR)
└── email (VARCHAR, NULL)

grading_annotation
├── id (UUID, PK)
├── copy_id (UUID, FK → exams_copy)
├── page_number (INTEGER)
├── vector_data (JSON)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)

grading_score
├── id (UUID, PK)
├── copy_id (UUID, FK → exams_copy)
├── scores_data (JSON)
├── final_comment (TEXT)
├── created_at (TIMESTAMP)
└── updated_at (TIMESTAMP)
```

**Indexes Recommandés** :
```python
# exams_copy
indexes = [
    models.Index(fields=['status', '-created_at']),
    models.Index(fields=['exam', 'status']),
    models.Index(fields=['anonymous_id']),  # unique déjà indexé
]

# grading_annotation
indexes = [
    models.Index(fields=['copy', 'page_number']),
]

# students_student
# ine déjà indexé (unique)
```

---

## 9. Backup et Recovery

### 9.1 Backup Obligatoire

**OBLIGATOIRE avant** :
- Migration destructive
- Mise en production majeure
- Maintenance de base de données

**Commandes** :
```bash
# Backup PostgreSQL
pg_dump -U postgres -h localhost viatique_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore
psql -U postgres -h localhost viatique_db < backup_20260121_143000.sql

# Backup avec Docker
docker exec viatique_db pg_dump -U postgres viatique_db > backup.sql
```

**Automatisation** :
- Backup quotidien automatisé
- Rétention 30 jours minimum
- Test de restore régulier

---

## 10. Checklist Base de Données

Avant tout changement de modèle :
- [ ] Modèle modifié avec conventions respectées
- [ ] Migration créée avec nom explicite
- [ ] Migration testée localement
- [ ] Pas de perte de données (ou documentée)
- [ ] Indexes ajoutés si nécessaire
- [ ] Relations avec on_delete explicite
- [ ] UUIDs pour IDs exposés
- [ ] Contraintes de validation ajoutées

Avant migration production :
- [ ] Backup complet effectué
- [ ] Migration testée en staging
- [ ] Downtime estimé (si applicable)
- [ ] Rollback plan préparé
- [ ] Équipe notifiée

---

**Version** : 1.0
**Date** : 2026-01-21
**Statut** : Obligatoire
