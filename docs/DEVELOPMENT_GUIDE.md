# Guide de Développement - Korrigo PMF

> **Version**: 1.2.0  
> **Date**: Janvier 2026  
> **Public**: Développeurs

Guide complet pour configurer l'environnement de développement et contribuer au projet Korrigo PMF.

---

## 📋 Table des Matières

1. [Prérequis](#prérequis)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Commandes Disponibles](#commandes-disponibles)
5. [Structure du Projet](#structure-du-projet)
6. [Standards de Code](#standards-de-code)
7. [Git Workflow](#git-workflow)
8. [Debug et Troubleshooting](#debug-et-troubleshooting)

---

## Prérequis

### Logiciels Requis

| Logiciel | Version Minimale | Installation |
|----------|------------------|--------------|
| **Docker** | 20.10+ | [docs.docker.com](https://docs.docker.com/get-docker/) |
| **Docker Compose** | 2.0+ | Inclus avec Docker Desktop |
| **Git** | 2.30+ | `sudo apt install git` |
| **Make** | 4.0+ | `sudo apt install make` |

### Optionnel (Développement Local)

| Logiciel | Version | Usage |
|----------|---------|-------|
| **Python** | 3.9 | Tests backend hors Docker |
| **Node.js** | 18+ | Tests frontend hors Docker |
| **PostgreSQL Client** | 15+ | Inspection DB |

---

## Installation

### 1. Cloner le Dépôt

```bash
git clone https://github.com/votre-org/viatique__PMF.git
cd viatique__PMF
```

### 2. Configuration Environnement

Copier le fichier d'exemple:
```bash
cp .env.example .env
```

Éditer `.env` avec vos valeurs:
```bash
# Backend
SECRET_KEY=django-insecure-dev-only-xxxxxxxxxxxxxxxxxx
DEBUG=true
DATABASE_URL=postgres://viatique_user:viatique_password@db:5432/viatique
CELERY_BROKER_URL=redis://redis:6379/0

# Redis Cache (login lockout multi-worker)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=1

# Frontend
VITE_API_URL=http://localhost:8088

# Security
SSL_ENABLED=false
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:8088

# Development
DJANGO_AUTO_MIGRATE=true
E2E_TEST_MODE=false
```

### 3. Démarrer les Services

```bash
make up
```

Cette commande:
- Build les images Docker
- Démarre PostgreSQL, Redis, Backend, Celery, Frontend
- Expose les ports: 5173 (frontend), 8088 (backend), 5435 (postgres), 6385 (redis)

### 4. Initialiser la Base de Données

```bash
make migrate
```

### 5. Créer un Super-Utilisateur

```bash
make superuser
```

Entrer les informations:
```
Username: admin
Email: admin@example.com
Password: ********
```

### 6. Vérifier l'Installation

Ouvrir dans le navigateur:
- **Frontend**: http://localhost:5173
- **Backend Admin**: http://localhost:8088/admin
- **API Root**: http://localhost:8088/api/

---

## Configuration

### Variables d'Environnement

#### Backend (`.env`)

| Variable | Défaut (Dev) | Description |
|----------|--------------|-------------|
| `SECRET_KEY` | `django-insecure-dev-only-...` | Clé cryptographique Django |
| `DEBUG` | `true` | Mode debug |
| `DATABASE_URL` | `postgres://...` | URL connexion PostgreSQL |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | URL broker Celery |
| `REDIS_HOST` | `redis` | Hôte Redis pour cache applicatif |
| `REDIS_PORT` | `6379` | Port Redis |
| `REDIS_DB` | `1` | Base Redis (DB 1 = cache, DB 0 = Celery) |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Hôtes autorisés |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173,...` | Origins CORS |
| `SSL_ENABLED` | `false` | Activer SSL/HTTPS |
| `RATELIMIT_ENABLE` | `true` | Activer rate limiting |
| `DJANGO_AUTO_MIGRATE` | `true` | Auto-exécuter migrations au démarrage |
| `E2E_TEST_MODE` | `false` | Activer mode test E2E (désactive rate-limiting) |
| `E2E_SEED_TOKEN` | _(vide)_ | Token pour endpoint `/api/dev/seed/` |

#### Frontend (`.env`)

| Variable | Défaut (Dev) | Description |
|----------|--------------|-------------|
| `VITE_API_URL` | `http://localhost:8088` | URL du backend |

### Configuration Redis Cache

**Contexte**: Le cache Redis est utilisé pour le système de verrouillage de compte (login lockout) multi-worker.

**Architecture**:
- **DB 0**: Broker Celery (`CELERY_BROKER_URL`)
- **DB 1**: Cache applicatif (`REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`)

**Fonctionnalités utilisant le cache**:
1. **Login lockout**: Tentatives de connexion échouées persistées entre workers Gunicorn
2. **TTL automatique**: Clés expirées après 15 minutes (durée du lockout)

**Configuration locale**:
```bash
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=1  # Séparation logique avec Celery
```

**Vérification**:
```bash
# Connexion au cache Redis
docker-compose exec redis redis-cli -n 1

# Lister les clés de lockout
127.0.0.1:6379[1]> KEYS login_attempts:*
```

### Mode Test E2E

**Variables**:
- `E2E_TEST_MODE=true`: Active des comportements de test
- `E2E_SEED_TOKEN=<secret>`: Expose l'endpoint `/api/dev/seed/`

**Comportements activés**:
1. **Rate-limiting désactivé**: Permet tests intensifs sans throttling
2. **Logs verbeux**: Traçabilité complète des opérations
3. **Endpoint de seed**: Population rapide de données de test

**Usage**:
```bash
# 1. Activer mode E2E
export E2E_TEST_MODE=true
export E2E_SEED_TOKEN=my-test-secret

# 2. Initialiser données de test
curl -X POST http://localhost:8088/api/dev/seed/ \
  -H "X-Seed-Token: my-test-secret"

# 3. Lancer tests Playwright
cd frontend
npm run test:e2e
```

**⚠️ Sécurité**: Ne **jamais** activer `E2E_TEST_MODE` en production.

### Configuration Docker Compose

Le projet utilise `infra/docker/docker-compose.yml` pour le développement.

**Services**:
```yaml
services:
  db:         # PostgreSQL 15 (port 5435)
  redis:      # Redis 7 (port 6385)
  backend:    # Django runserver (port 8088)
  celery:     # Celery worker
  frontend:   # Vite dev server (port 5173)
```

**Volumes**:
- `postgres_data`: Données PostgreSQL (persistant)
- `./backend:/app`: Code backend (hot reload)
- `./frontend:/app`: Code frontend (hot reload)

---

## Commandes Disponibles

### Makefile

Le `Makefile` à la racine du projet fournit des raccourcis:

| Commande | Description |
|----------|-------------|
| `make up` | Démarrer tous les services |
| `make down` | Arrêter tous les services |
| `make logs` | Afficher les logs en temps réel |
| `make migrate` | Exécuter les migrations Django |
| `make superuser` | Créer un super-utilisateur |
| `make test` | Lancer les tests backend + E2E |
| `make shell` | Ouvrir un shell Django |
| `make init_pmf` | Initialiser données PMF (users, groups) |

### Docker Compose

Commandes directes:

```bash
# Démarrer services
docker-compose -f infra/docker/docker-compose.yml up -d

# Arrêter services
docker-compose -f infra/docker/docker-compose.yml down

# Voir les logs
docker-compose -f infra/docker/docker-compose.yml logs -f backend

# Exécuter commande dans container
docker-compose -f infra/docker/docker-compose.yml exec backend python manage.py shell

# Rebuild après changement Dockerfile
docker-compose -f infra/docker/docker-compose.yml up --build -d
```

### Backend (Django)

```bash
# Shell Django
docker-compose exec backend python manage.py shell

# Créer migration
docker-compose exec backend python manage.py makemigrations

# Appliquer migrations
docker-compose exec backend python manage.py migrate

# Collecter static files
docker-compose exec backend python manage.py collectstatic --noinput

# Créer super-utilisateur
docker-compose exec backend python manage.py createsuperuser

# Lancer tests
docker-compose exec backend pytest

# Lancer tests avec coverage
docker-compose exec backend pytest --cov=. --cov-report=html
```

### Frontend (Vue.js)

```bash
# Installer dépendances
cd frontend
npm install

# Démarrer dev server (hors Docker)
npm run dev

# Build production
npm run build

# Linter
npm run lint

# Type checking
npm run typecheck

# Tests E2E Playwright
npx playwright test

# Tests E2E avec UI
npx playwright test --ui
```

---

## Structure du Projet

```
viatique__PMF/
├── backend/                    # Backend Django
│   ├── core/                   # Configuration Django
│   │   ├── settings.py         # Settings principal
│   │   ├── urls.py             # URLs racine
│   │   └── wsgi.py             # WSGI application
│   ├── exams/                  # App Examens
│   │   ├── models.py           # Exam, Booklet, Copy
│   │   ├── views.py            # ViewSets DRF
│   │   ├── serializers.py      # Serializers DRF
│   │   ├── permissions.py      # Permissions custom
│   │   ├── validators.py       # Validators PDF
│   │   └── tests/              # Tests unitaires
│   ├── grading/                # App Correction
│   │   ├── models.py           # Annotation, GradingEvent, CopyLock
│   │   ├── views.py            # ViewSets correction
│   │   ├── services.py         # GradingService, AnnotationService
│   │   └── tests/              # Tests unitaires
│   ├── processing/             # Services traitement PDF
│   │   └── services/
│   │       ├── pdf_splitter.py # Découpage A3 → A4
│   │       └── pdf_flattener.py# Génération PDF finaux
│   ├── students/               # App Élèves
│   │   ├── models.py           # Student
│   │   ├── views.py            # Portail élève
│   │   └── management/         # Commandes Django
│   ├── manage.py               # CLI Django
│   ├── requirements.txt        # Dépendances Python
│   └── Dockerfile              # Image Docker backend
│
├── frontend/                   # Frontend Vue.js
│   ├── src/
│   │   ├── main.js             # Entry point
│   │   ├── App.vue             # Composant racine
│   │   ├── router/             # Vue Router
│   │   │   └── index.js        # Routes + guards
│   │   ├── stores/             # Pinia stores
│   │   │   ├── auth.js         # Store authentification
│   │   │   └── exam.js         # Store examens
│   │   ├── services/           # Services API
│   │   │   └── api.js          # Client axios
│   │   ├── components/         # Composants réutilisables
│   │   └── views/              # Vues principales
│   │       ├── admin/          # Vues admin
│   │       ├── student/        # Vues élève
│   │       ├── Login.vue
│   │       ├── AdminDashboard.vue
│   │       └── CorrectorDashboard.vue
│   ├── e2e/                    # Tests E2E Playwright
│   ├── package.json            # Dépendances npm
│   ├── vite.config.js          # Config Vite
│   └── Dockerfile              # Image Docker frontend
│
├── infra/                      # Infrastructure
│   ├── docker/                 # Configurations Docker Compose
│   │   ├── docker-compose.yml  # Développement
│   │   ├── docker-compose.prod.yml # Production
│   │   └── docker-compose.e2e.yml  # Tests E2E
│   └── nginx/                  # Config Nginx (prod)
│
├── docs/                       # Documentation
│   ├── ARCHITECTURE.md
│   ├── DATABASE_SCHEMA.md
│   ├── API_REFERENCE.md
│   ├── DEVELOPMENT_GUIDE.md
│   └── ...
│
├── scripts/                    # Scripts utilitaires
│   ├── release/                # Scripts release
│   └── test_e2e.py             # Script tests E2E
│
├── .env.example                # Template variables env
├── .gitignore                  # Fichiers ignorés Git
├── Makefile                    # Commandes raccourcies
├── README.md                   # Documentation principale
└── CHANGELOG.md                # Historique versions
```

---

## Standards de Code

### Backend (Python)

#### PEP 8

Suivre [PEP 8](https://pep8.org/) pour le style Python:
- Indentation: 4 espaces
- Longueur ligne: 120 caractères max
- Imports: Groupés (stdlib, third-party, local)

#### Django Best Practices

- **Models**: Un fichier `models.py` par app
- **Views**: Utiliser ViewSets DRF pour CRUD
- **Services**: Logique métier dans `services.py`
- **Permissions**: Permissions custom dans `permissions.py`
- **Tests**: Coverage > 80%

#### Exemple

```python
# backend/grading/services.py
from django.db import transaction
from .models import Annotation, GradingEvent

class AnnotationService:
    @staticmethod
    @transaction.atomic
    def add_annotation(copy, payload, user):
        """
        Crée une annotation sur une copie.
        
        Args:
            copy (Copy): Copie à annoter
            payload (dict): Données annotation
            user (User): Utilisateur créateur
            
        Returns:
            Annotation: Annotation créée
            
        Raises:
            ValueError: Si copie pas en statut READY
        """
        if copy.status != Copy.Status.READY:
            raise ValueError(f"Cannot annotate copy in status {copy.status}")
        
        annotation = Annotation.objects.create(
            copy=copy,
            created_by=user,
            **payload
        )
        
        GradingEvent.objects.create(
            copy=copy,
            action=GradingEvent.Action.CREATE_ANN,
            actor=user,
            metadata={'annotation_id': str(annotation.id)}
        )
        
        return annotation
```

### Frontend (Vue.js + TypeScript)

#### ESLint

Configuration dans `frontend/eslint.config.js`:
- Vue.js 3 Composition API
- TypeScript strict
- Prettier integration

#### Vue.js Best Practices

- **Composition API**: Préférer `<script setup>`
- **Stores**: Un store par domaine métier
- **Components**: Composants réutilisables dans `components/`
- **Views**: Vues pages dans `views/`
- **Naming**: PascalCase pour composants, camelCase pour variables

#### Exemple

```vue
<!-- frontend/src/views/admin/CorrectorDesk.vue -->
<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useExamStore } from '@/stores/exam'

const route = useRoute()
const examStore = useExamStore()

const copyId = ref(route.params.copyId)
const annotations = ref([])

onMounted(async () => {
  await examStore.loadCopy(copyId.value)
  annotations.value = await examStore.loadAnnotations(copyId.value)
})

const addAnnotation = async (payload) => {
  const annotation = await examStore.createAnnotation(copyId.value, payload)
  annotations.value.push(annotation)
}
</script>

<template>
  <div class="corrector-desk">
    <h1>Correction Copie {{ copyId }}</h1>
    <!-- ... -->
  </div>
</template>

<style scoped>
.corrector-desk {
  padding: 2rem;
}
</style>
```

---

## Git Workflow

### Branches

| Branche | Description |
|---------|-------------|
| `main` | Production (stable) |
| `develop` | Développement (intégration) |
| `feature/*` | Nouvelles fonctionnalités |
| `bugfix/*` | Corrections bugs |
| `hotfix/*` | Corrections urgentes prod |

### Workflow

```bash
# 1. Créer branche feature
git checkout develop
git pull origin develop
git checkout -b feature/identification-ocr

# 2. Développer et committer
git add .
git commit -m "feat(exams): Add OCR identification for booklets"

# 3. Push et créer PR
git push origin feature/identification-ocr
# Créer Pull Request sur GitHub: feature/identification-ocr → develop

# 4. Après review et merge
git checkout develop
git pull origin develop
git branch -d feature/identification-ocr
```

### Commits Conventionnels

Format: `<type>(<scope>): <description>`

**Types**:
- `feat`: Nouvelle fonctionnalité
- `fix`: Correction bug
- `docs`: Documentation
- `style`: Formatage code
- `refactor`: Refactoring
- `test`: Tests
- `chore`: Maintenance

**Exemples**:
```
feat(grading): Add annotation service layer
fix(exams): Correct PDF validation mime type
docs(api): Update API reference with new endpoints
test(grading): Add unit tests for GradingService
```

---

## Debug et Troubleshooting

### Logs

#### Backend

```bash
# Logs Django
docker-compose logs -f backend

# Logs Celery
docker-compose logs -f celery

# Logs PostgreSQL
docker-compose logs -f db
```

#### Frontend

```bash
# Logs Vite dev server
docker-compose logs -f frontend

# Console navigateur
# Ouvrir DevTools (F12) → Console
```

### Problèmes Courants

#### 1. Port déjà utilisé

**Erreur**:
```
Error starting userland proxy: listen tcp4 0.0.0.0:8088: bind: address already in use
```

**Solution**:
```bash
# Trouver processus utilisant le port
sudo lsof -i :8088

# Tuer le processus
sudo kill -9 <PID>

# Ou changer le port dans docker-compose.yml
```

#### 2. Migrations non appliquées

**Erreur**:
```
django.db.utils.ProgrammingError: relation "exams_exam" does not exist
```

**Solution**:
```bash
make migrate
```

#### 3. Volumes Docker corrompus

**Erreur**:
```
psycopg2.OperationalError: FATAL: database "viatique" does not exist
```

**Solution**:
```bash
# Arrêter services
make down

# Supprimer volumes (⚠️ PERTE DE DONNÉES)
docker volume rm viatique__pmf_postgres_data

# Redémarrer et recréer DB
make up
make migrate
make superuser
```

#### 4. Hot Reload ne fonctionne pas

**Solution**:
```bash
# Backend: Vérifier volume monté
docker-compose exec backend ls -la /app

# Frontend: Vérifier Vite config
# vite.config.js doit avoir:
server: {
  host: '0.0.0.0',
  port: 5173,
  watch: {
    usePolling: true
  }
}
```

### Debugging Backend

#### Django Debug Toolbar

Installer:
```bash
pip install django-debug-toolbar
```

Configurer dans `settings.py`:
```python
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
    INTERNAL_IPS = ['127.0.0.1']
```

#### PDB (Python Debugger)

Ajouter breakpoint dans le code:
```python
import pdb; pdb.set_trace()
```

Attacher au container:
```bash
docker attach viatique__pmf_backend_1
```

### Debugging Frontend

#### Vue DevTools

Installer extension navigateur:
- [Chrome](https://chrome.google.com/webstore/detail/vuejs-devtools/)
- [Firefox](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)

#### Console Logging

```javascript
console.log('Debug:', variable)
console.table(array)
console.trace()
```

---

## Références

- [ARCHITECTURE.md](file:///home/alaeddine/viatique__PMF/docs/ARCHITECTURE.md) - Architecture globale
- [API_REFERENCE.md](file:///home/alaeddine/viatique__PMF/docs/API_REFERENCE.md) - Documentation API
- [TEST_PLAN.md](file:///home/alaeddine/viatique__PMF/docs/quality/TEST_PLAN.md) - Plan de tests
- [DEPLOYMENT_GUIDE.md](file:///home/alaeddine/viatique__PMF/docs/DEPLOYMENT_GUIDE.md) - Guide déploiement

---

**Dernière mise à jour**: 25 janvier 2026  
**Auteur**: Aleddine BEN RHOUMA  
**Licence**: Propriétaire - AEFE/Éducation Nationale
