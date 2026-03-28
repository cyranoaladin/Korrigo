# Guide de Développement — Korrigo v2

> **Version** : 3.0
> **Date** : 2026-03-28
> **Public** : Développeurs

---

## Environnement de développement

### Prérequis
- Python 3.11 (backend)
- Node.js 20+ (frontend)
- Docker + Docker Compose v2
- PostgreSQL client (optionnel, pour accès direct)

### Setup initial
Voir [QUICKSTART.md](../QUICKSTART.md).

### IDE recommandé : VSCode
Extensions utiles :
- Python + Pylance
- Volar (Vue Language Features)
- ESLint
- TailwindCSS IntelliSense
- Django (snippets)
- GitLens

---

## Structure du projet

```
korrigo_v2_improved/
├── backend/
│   ├── core/              # Auth, settings, middleware, audit RGPD
│   │   ├── auth.py        # UserRole enum (ADMIN/TEACHER/STUDENT)
│   │   ├── settings.py    # Settings dev
│   │   ├── settings_prod.py # Settings production (rejette SECRET_KEY insecure)
│   │   ├── settings_test.py # Settings test (SQLite, Celery eager)
│   │   └── models.py      # GlobalSettings, AuditLog, UserProfile
│   ├── exams/
│   │   ├── models.py      # Exam, ExamType, Booklet, Copy, ExamPDF, ExamDocumentSet
│   │   ├── views.py       # ViewSets + upload views
│   │   ├── serializers.py
│   │   ├── migrations/    # 0001–0028
│   │   ├── tasks.py       # Celery : process_document_set
│   │   └── management/commands/
│   │       ├── import_dnb_copies.py
│   │       ├── import_dnb_students.py
│   │       ├── identify_dnb_copies.py
│   │       ├── create_exam_types.py
│   │       └── export_pronote.py
│   ├── grading/
│   │   ├── models.py      # Annotation, GradingEvent, Score, CopyLock, DraftState, ...
│   │   ├── services.py    # GradingService, AnnotationService, LockConflictError
│   │   ├── views.py
│   │   ├── views_lock.py  # Lock/unlock/heartbeat endpoints
│   │   ├── tasks.py       # async_finalize_copy, generate_questionnaire_bilan_task
│   │   └── tests/         # 60+ modules de tests
│   ├── students/
│   │   ├── models.py      # Student
│   │   └── management/commands/
│   │       ├── import_dnb_students.py (dans exams/management)
│   │       └── provision_student_users.py
│   ├── identification/
│   │   ├── models.py      # OCRResult
│   │   └── services.py    # OCRService (GPT-4o-mini + Tesseract)
│   ├── processing/
│   │   └── services/
│   │       ├── pdf_splitter.py    # Découpage PDF batch
│   │       └── pdf_flattener.py   # Aplatissement annotations sur PDF
│   ├── conftest.py        # Fixtures pytest (api_client, admin_user, teacher_user)
│   └── pytest.ini         # Config pytest (DJANGO_SETTINGS_MODULE=core.settings_test)
└── frontend/
    ├── src/
    │   ├── router/index.js    # 27+ routes Vue Router
    │   ├── stores/auth.js     # Pinia auth store
    │   ├── stores/examStore.js# Pinia exam/copies store
    │   ├── views/admin/       # AdminDashboard, CorrectorDesk, ImportCopies, ...
    │   ├── views/teacher/     # CorrectorDashboard, MyStudents, ...
    │   ├── views/student/     # LoginStudent, ResultView, ...
    │   └── components/        # PDFViewer, CanvasLayer, GradingSidebar, ...
    └── e2e/                   # Tests Playwright
```

---

## Conventions de code

### Backend (Python/Django)
- **Langue** : code en anglais, commentaires/UI en français
- **Style** : PEP 8, lint via `ruff check backend/`
- **Pattern services** : la logique métier va dans les classes `*Service`, jamais dans les vues
- **Transactions** : tout write DB dans `@transaction.atomic`
- **Audit** : chaque changement d'état → `GradingEvent.objects.create()`
- **Pas de migration destructive** : uniquement `AddField` avec `null=True`, jamais `RemoveField` sur données importantes

### Frontend (Vue 3)
- **Composition API** uniquement : `<script setup>`, jamais Options API
- **Pas d'appels API directs** dans les templates : utiliser stores Pinia ou composables
- **TailwindCSS** uniquement : pas de CSS custom sauf cas justifiés
- **Props down, events up** : pas de mutation de props
- **Lint** : `cd frontend && npm run lint`

### Règle CRITIQUE — Machine à états Copy
- **Ne jamais** : `copy.status = 'IN_PROGRESS'` directement en dehors du service
- **Toujours** passer par `AnnotationService.add_annotation()` (READY→IN_PROGRESS)
- **Toujours** passer par `GradingService.finalize_copy()` (→FINALIZED)
- **Toujours** passer par l'endpoint admin reopen (FINALIZED→READY)

---

## Tests

### Configuration (`pytest.ini`)
```ini
[pytest]
DJANGO_SETTINGS_MODULE = core.settings_test
addopts = --verbose --strict-markers --tb=short -m "not postgres and not slow"

markers =
    unit: Tests rapides sans DB
    api: Tests d'intégration avec APIClient + DB
    postgres: Nécessite PostgreSQL réel
    slow: Tests lents (génération PDF, etc.)
    smoke: Tests critiques de production
```

### Lancer les tests

```bash
# Suite normale (hors postgres + slow) — rapide
docker exec docker-backend-1 python -m pytest -q

# Avec couverture
docker exec docker-backend-1 python -m pytest --cov=. --cov-report=html

# Test de concurrence PostgreSQL (nécessite vraie DB Postgres)
docker exec docker-backend-1 python -m pytest -m postgres \
  grading/tests/test_concurrency_postgres.py -v

# Un test spécifique
docker exec docker-backend-1 python -m pytest \
  grading/tests/test_multi_exam_isolation.py::test_corrector_bac_sees_only_bac_copies -v

# Tests frontend E2E
cd frontend && npm run test:e2e
```

### Fixtures disponibles (`conftest.py`)

| Fixture | Description |
|---------|-------------|
| `api_client` | DRF `APIClient` non authentifié |
| `admin_user` | Superuser + groupe ADMIN |
| `teacher_user` | `is_staff=True` + groupe TEACHER |

### Écrire un test API standard
```python
@pytest.mark.django_db
def test_create_annotation(teacher_user, api_client):
    from exams.models import Exam, Copy, Booklet
    from datetime import date

    exam = Exam.objects.create(name="Test", date=date.today())
    booklet = Booklet.objects.create(exam=exam, start_page=0, end_page=0,
                                     pages_images=["p0.png"])
    copy = Copy.objects.create(exam=exam, anonymous_id="T-001",
                               assigned_corrector=teacher_user)
    copy.booklets.add(booklet)

    api_client.force_authenticate(user=teacher_user)
    resp = api_client.post(f"/api/grading/copies/{copy.id}/annotations/", {
        "page_index": 0, "x": 0.1, "y": 0.1, "w": 0.2, "h": 0.1,
        "type": "COMMENT", "content": "Test"
    }, format="json")
    assert resp.status_code == 201
    copy.refresh_from_db()
    assert copy.status == "IN_PROGRESS"  # Transition automatique
```

---

## Commandes de gestion

### Référence complète

| App | Commande | Description |
|-----|---------|-------------|
| core | `ensure_admin` | Crée le superuser initial (admin/admin123) |
| exams | `create_exam_types` | Initialise les types d'examens |
| exams | `import_dnb_copies` | Ingestion des PDFs A4 DNB |
| exams | `import_dnb_students --file X.csv` | Import élèves depuis CSV |
| exams | `identify_dnb_copies [--exam DNB_2026] [--min-score 0.65]` | Auto-link copies→élèves |
| exams | `export_pronote --exam DNB_2026` | Export CSV Pronote |
| exams | `seed_initial_exams` | Données de démo |
| grading | `recover_stuck_copies` | Libère les copies bloquées (`finalizing_at` non-null) |
| grading | `inject_bilan_html` | Injecte les bilans HTML en DB |
| students | `provision_student_users` | Crée les Users Django pour les Students existants |
| students | `reset_student_passwords` | Reset passwords élèves en lot |

### Ajouter une commande de gestion
```python
# backend/monapp/management/commands/ma_commande.py
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Description de la commande"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        if options["dry_run"]:
            self.stdout.write("Mode dry-run")
```

---

## Ajouter un endpoint API

1. **Modèle** (si nouveau) : `backend/monapp/models.py` + migration
2. **Serializer** : `backend/monapp/serializers.py`
3. **Vue** :
   ```python
   # backend/monapp/views.py
   class MonEndpointView(APIView):
       permission_classes = [IsAuthenticated]

       def post(self, request, copy_id):
           copy = get_object_or_404(Copy, id=copy_id, assigned_corrector=request.user)
           # ... logique dans le service ...
           return Response(data, status=201)
   ```
4. **URL** : `backend/monapp/urls.py`
5. **Test** : `backend/monapp/tests/test_mon_endpoint.py`
6. **Documentation** : `docs/technical/API_REFERENCE.md`

---

## Debug

### Backend en mode interactif
```bash
docker exec -it docker-backend-1 python manage.py shell
```

### Inspecter la DB directement
```bash
docker exec -it docker-db-1 psql -U korrigo
```

### Logs structurés
```bash
docker logs docker-backend-1 --tail 100 -f
# Format JSON en production, lisible en dev
```

### Celery task manquante
```bash
docker logs docker-celery-1 --tail 50
# Vérifier la queue
docker exec docker-redis-1 redis-cli LLEN celery
```

### Copy bloquée (finalizing_at non-null)
```bash
docker exec docker-backend-1 python manage.py shell -c "
from exams.models import Copy
stuck = Copy.objects.filter(finalizing_at__isnull=False)
print(f'{stuck.count()} copies bloquées')
stuck.update(finalizing_at=None)
print('Libérées')
"
```

### Migrations hors-sync
```bash
docker exec docker-backend-1 python manage.py showmigrations
docker exec docker-backend-1 python manage.py migrate --check
```

---

## Variables d'environnement (settings_test.py)

Tests utilisent `core.settings_test` :
- DB : SQLite (en mémoire) sauf `@pytest.mark.postgres` (utilise vraie PostgreSQL)
- `CELERY_TASK_ALWAYS_EAGER = True` : tâches exécutées en synchrone
- `RATELIMIT_ENABLE = False`
- Pas de vraie intégration OpenAI (mocker dans les tests)
