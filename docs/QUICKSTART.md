# Guide de Démarrage Rapide — Korrigo v2

> **Objectif** : Environnement local opérationnel en < 15 minutes
> **Public** : Développeurs, Administrateurs
> **Prérequis** : Docker 24+, Docker Compose v2, Node.js 20+, Git

---

## 1. Cloner le dépôt

```bash
git clone <url-repo> korrigo_v2_improved
cd korrigo_v2_improved
```

---

## 2. Configurer l'environnement

```bash
cp infra/docker/.env.example infra/docker/.env
```

Éditer `infra/docker/.env` — valeurs minimales obligatoires :

```env
# OBLIGATOIRE — doit faire 50+ caractères, PAS django-insecure-
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")

DJANGO_SETTINGS_MODULE=core.settings
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=korrigo
DB_USER=korrigo
DB_PASSWORD=korrigo_dev
DB_HOST=db
DB_PORT=5432
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Optionnel — pour l'OCR GPT-4o-mini
OPENAI_API_KEY=sk-...

# Optionnel — pour les bilans LLM
OLLAMA_URL=http://ollama:11434
```

---

## 3. Démarrer les services

```bash
docker compose -f infra/docker/docker-compose.yml up -d
```

Services lancés : `backend` (Django), `db` (PostgreSQL 15), `redis`, `celery`, `celery-beat`, `nginx`.

Vérifier que tout est up :
```bash
docker compose -f infra/docker/docker-compose.yml ps
```

---

## 4. Initialiser la base de données

```bash
# Migrations
docker exec docker-backend-1 python manage.py migrate

# Admin initial (admin / admin123)
docker exec docker-backend-1 python manage.py ensure_admin

# Types d'examens
docker exec docker-backend-1 python manage.py create_exam_types
```

> ⚠️ Changer le mot de passe admin immédiatement après la première connexion.

---

## 5. Frontend (développement)

```bash
cd frontend
npm install
npm run dev
```

Frontend disponible sur **http://localhost:5173** (proxy `/api` → backend:8000).

---

## 6. Vérifier l'installation

```bash
# Health check
curl http://localhost:8000/api/health/
# → {"status": "ok", "db": "ok", "redis": "ok"}

# Swagger UI
open http://localhost:8000/api/schema/swagger-ui/

# Admin Django
open http://localhost:8000/admin/
# Login: admin / admin123
```

---

## 7. Créer un enseignant

```bash
docker exec docker-backend-1 python manage.py shell -c "
from django.contrib.auth.models import User, Group
from core.auth import UserRole
u = User.objects.create_user('prof@ecole.tn', password='pass1234', is_staff=True)
g, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
u.groups.add(g)
print('Enseignant créé:', u.username)
"
```

---

## 8. Importer des élèves (optionnel)

Préparer un CSV `troisieme.csv` :
```csv
Nom;Prenom;Date_Naissance;Mail;Classe
AKROUT;RAHMA;22/07/2011;rahma.akrout-e@ert.tn;3.1
```

```bash
# Copier le CSV dans le conteneur
docker cp troisieme.csv docker-backend-1:/app/scan_DNB_maths/troisieme.csv

# Import (dry-run d'abord)
docker exec docker-backend-1 python manage.py import_dnb_students --dry-run
docker exec docker-backend-1 python manage.py import_dnb_students
```

---

## 9. Lancer les tests

```bash
# Suite complète (hors postgres + slow)
docker exec docker-backend-1 python -m pytest -q \
  --ignore=grading/tests/test_concurrency_postgres.py

# Test de concurrence (nécessite PostgreSQL)
docker exec docker-backend-1 python -m pytest -m postgres \
  grading/tests/test_concurrency_postgres.py -v

# Tests E2E (Playwright)
cd frontend && npm run test:e2e
```

---

## URLs de référence

| URL | Description |
|-----|-------------|
| http://localhost:8000/api/ | API REST |
| http://localhost:8000/api/health/ | Health check |
| http://localhost:8000/api/schema/swagger-ui/ | Documentation API interactive |
| http://localhost:8000/admin/ | Interface admin Django |
| http://localhost:5173 | Frontend Vue (mode dev) |
| http://localhost | Frontend (via Nginx, mode prod) |

---

## Structure du projet

```
korrigo_v2_improved/
├── backend/           # Django 4.2 (Python 3.11)
│   ├── core/          # Auth, settings, audit, middleware
│   ├── exams/         # Exam, Booklet, Copy + pipeline ingestion
│   ├── grading/       # Annotation, Score, Lock, Finalization
│   ├── students/      # Student model + auth élève
│   ├── identification/# OCR (GPT-4o-mini + Tesseract)
│   └── processing/    # PDFSplitter, PDFFlattener
├── frontend/          # Vue 3.4 + Vite 5 + TailwindCSS 4
│   ├── src/views/     # 27 vues (admin, teacher, student)
│   ├── src/components/# 28 composants
│   └── src/stores/    # Pinia (auth, examStore)
├── infra/docker/      # Docker Compose + .env
└── docs/              # Documentation complète (ce dossier)
```

---

## Dépannage rapide

| Problème | Solution |
|----------|---------|
| `SECRET_KEY looks like a placeholder` | Générer une vraie clé 50+ chars dans `.env` |
| Backend ne démarre pas | `docker logs docker-backend-1 --tail 50` |
| Migrations manquantes | `docker exec docker-backend-1 python manage.py migrate` |
| Celery ne traite pas les tâches | `docker logs docker-celery-1 --tail 50` |
| Copy bloquée avec `finalizing_at` | `Copy.objects.filter(finalizing_at__isnull=False).update(finalizing_at=None)` via shell |
