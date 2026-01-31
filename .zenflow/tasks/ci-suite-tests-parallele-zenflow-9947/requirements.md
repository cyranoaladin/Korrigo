# Product Requirements Document: CI + Suite Tests Parallèle (Zenflow)

## 1. Contexte et Objectifs

### 1.1 Contexte
Le projet Korrigo dispose d'une suite de tests comprenant:
- **Backend**: ~44 fichiers de tests Python (pytest + Django TestCase)
- **Frontend**: Tests E2E Playwright (actuellement séquentiels, workers=1)
- **CI**: Pipeline GitHub Actions avec jobs séquentiels

**Problématique actuelle:**
- Les tests s'exécutent séquentiellement, ralentissant le feedback CI
- Pas d'isolation entre workers → risque de flaky tests
- Les tâches Zenflow peuvent s'exécuter en parallèle et se marcher dessus
- Configuration non optimisée pour l'exécution parallèle

### 1.2 Objectif Principal
**Livrer une batterie de tests exécutable en parallèle, sans flakes ni conflits, avec isolation complète entre workers.**

### 1.3 Contraintes
- ✅ Les tâches Zenflow doivent pouvoir s'exécuter en parallèle sans conflit
- ✅ 0 flaky tests sur 5 runs consécutifs (critère de succès)
- ✅ Compatibilité avec l'infrastructure Docker existante
- ✅ Pas de régression sur les tests existants

## 2. État des Lieux Technique

### 2.1 Backend (Pytest)

**Configuration actuelle:**
- Framework: pytest 8.0 + pytest-django 4.8
- Settings test: `core.settings_test.py`
- Markers définis: `unit`, `api`, `e2e`, `postgres`, `smoke`
- **Isolation partielle existante:**
  - DB suffix: `test_viatique_{DB_SUFFIX}` (basé sur `PYTEST_XDIST_WORKER` ou `CI_NODE_INDEX`)
  - Media temp dir: `tempfile.mkdtemp(prefix="korrigo_test_media_")` (autouse fixture)
- **Manque:**
  - `pytest-xdist` non installé
  - Pas de catégorisation claire des suites
  - Fixtures PDF partagées sans isolation

**Tests identifiés:**
- Unit tests purs (mocks, pas de DB): ~15 fichiers
- Integration tests (DB + API): ~20 fichiers
- Tests avec fixtures PDF/images: ~8 fichiers (grading/processing)
- Tests PostgreSQL spécifiques: 2 fichiers (concurrency_postgres)

### 2.2 Frontend (Playwright)

**Configuration actuelle:**
```typescript
workers: 1,
fullyParallel: false,
baseURL: 'http://localhost:8088'
```

**Problèmes:**
- Pas de parallélisation
- Pas d'isolation DB par worker
- Port backend fixe (8088)
- Global setup valide seulement l'environnement (pas de setup par worker)

**Tests E2E:**
- ~3 fichiers spec (admin_flow, teacher_flow, example)
- Dépendent de seed_e2e.py pour données de test
- Lancés via `tools/e2e.sh` (Docker compose)

### 2.3 CI GitHub Actions

**Jobs actuels:**
1. `lint` → `unit` → `security` → `integration` → `packaging`
2. `tests-postgres` (parallèle à unit)

**Opportunités:**
- Certains jobs pourraient être parallélisés
- Pas de matrice de parallélisation intra-job

### 2.4 Docker & Zenflow

**Compose files:**
- `docker-compose.yml` (dev): ports 5435, 6385, 8088, 5173
- `docker-compose.e2e.yml` (override pour E2E)
- Ports fixes → conflits potentiels si plusieurs tasks Zenflow

**Zenflow:**
- Tasks isolées dans `.zenflow/worktrees/{task_id}`
- Variables env non définies par task
- Pas de convention pour ports dynamiques

## 3. Exigences Fonctionnelles

### 3.1 Découpage des Suites de Tests

#### Suite 1: Unit-Fast (Backend)
**Critères:**
- Pas d'accès DB (ou utilise `@pytest.mark.unit` avec mocks)
- Pas d'I/O fichier (sauf tempfile)
- Exécution < 10s au total

**Fichiers cibles:**
- `grading/tests/test_services_strict_unit.py`
- `grading/tests/test_validation.py`
- `grading/tests/test_error_handling.py` (marqués unit)
- `core/tests/test_*.py` (sauf full_audit)

**Exigences:**
- ✅ Exécutable sans Docker (pip install + pytest)
- ✅ Parallélisable avec pytest-xdist (4-8 workers)
- ✅ Aucune isolation DB nécessaire (pas de DB)

#### Suite 2: Integration-API (Backend)
**Critères:**
- Tests avec DB Django (SQLite ou PostgreSQL)
- APIClient REST
- Pas de fixtures lourdes (PDF/images)

**Fichiers cibles:**
- `grading/tests/test_workflow_complete.py`
- `grading/tests/test_lock_endpoints.py`
- `grading/tests/test_async_views.py`
- `students/tests/test_*.py`
- `core/tests/test_full_audit.py`

**Exigences:**
- ✅ Isolation DB par worker: `test_viatique_{worker_id}`
- ✅ Parallélisable avec pytest-xdist (2-4 workers)
- ✅ Transactions rollback automatiques (pytest-django)

#### Suite 3: Processing (Backend)
**Critères:**
- Tests utilisant des fixtures PDF/images
- Traitement PyMuPDF, OpenCV, Tesseract
- I/O fichiers lourds

**Fichiers cibles:**
- `grading/tests/test_fixtures_*.py`
- `grading/tests/test_integration_real.py`
- `processing/tests/test_splitter.py`
- `exams/tests/test_pdf_validators.py`

**Exigences:**
- ✅ Media dir isolé par worker: `MEDIA_ROOT=/tmp/korrigo_test_{worker_id}/`
- ✅ Fixtures PDF isolées (copie par worker ou lecture seule)
- ✅ Parallélisable avec pytest-xdist (2 workers max, I/O bound)
- ✅ DB isolation identique à Integration-API

#### Suite 4: E2E (Playwright)
**Critères:**
- Tests Playwright full-stack
- Dépendent de Docker compose + seed

**Fichiers cibles:**
- `frontend/e2e/tests/*.spec.ts`

**Exigences:**
- ✅ Backend isolé par worker (DB + port dynamique)
- ✅ Playwright workers: 2-4
- ✅ Seed data isolé par worker
- ✅ Cleanup automatique post-test

### 3.2 Isolation Technique

#### 3.2.1 Base de Données
**Pytest (Backend):**
- Stratégie: **DB suffix par worker**
- Implémentation existante (à compléter):
  ```python
  DB_SUFFIX = os.environ.get("PYTEST_XDIST_WORKER", "0")
  DATABASES['default']['TEST']['NAME'] = f'test_viatique_{DB_SUFFIX}'
  ```
- **Exigence:** Vérifier que chaque worker a sa propre DB test

**Playwright (Frontend E2E):**
- Stratégie: **DB name par worker OU schéma PostgreSQL**
- Options:
  1. `DATABASE_URL=postgres://user:pass@localhost:5432/test_e2e_w{N}`
  2. Schémas PostgreSQL: `SET search_path TO test_w{N};`
- **Exigence:** Global setup Playwright doit créer DB dédiée

#### 3.2.2 Media Files
**Pytest:**
- Déjà en place: `mock_media` fixture (autouse) avec `tempfile.mkdtemp()`
- **Exigence:** Vérifier unicité du suffix (inclure worker ID)

**Playwright:**
- **Exigence:** Variable env `MEDIA_ROOT` par worker
- Exemple: `MEDIA_ROOT=/tmp/korrigo_e2e_w${PLAYWRIGHT_WORKER_INDEX}/`

#### 3.2.3 Ports et Services (Zenflow)
**Problème:** Plusieurs tasks Zenflow en parallèle → conflits de ports

**Exigence: Convention de Ports Dynamiques**
```bash
# Variables env par task Zenflow
export ZENFLOW_TASK_ID="ci-suite-tests-parallele-zenflow-9947"
export ZENFLOW_PORT_OFFSET=$((9947 % 1000))  # Exemple: offset basé sur task ID

# Ports dérivés
export BACKEND_PORT=$((8000 + ZENFLOW_PORT_OFFSET))
export POSTGRES_PORT=$((5432 + ZENFLOW_PORT_OFFSET))
export REDIS_PORT=$((6379 + ZENFLOW_PORT_OFFSET))
export FRONTEND_PORT=$((5173 + ZENFLOW_PORT_OFFSET))
```

**Alternative:** Utiliser des ports aléatoires libres (plus complexe)

### 3.3 Configuration Pytest-Xdist

**Dépendance à ajouter:**
```txt
pytest-xdist~=3.5
```

**pytest.ini (ajouts):**
```ini
[pytest]
# ... existing config ...

# Xdist: auto-detect optimal workers (-n auto)
# Suite-specific overrides via CLI
addopts =
    --verbose
    --strict-markers
    --tb=short
    --dist=loadscope  # Distribute by test module (better for DB tests)
```

**Commandes d'exécution:**
```bash
# Unit-fast (8 workers, pas de DB)
pytest -n 8 -m unit

# Integration-API (4 workers, DB isolation)
pytest -n 4 -m api

# Processing (2 workers, I/O bound)
pytest -n 2 grading/tests/test_fixtures*.py processing/tests/

# Postgres-specific (1 worker, real PostgreSQL)
pytest -n 1 -m postgres
```

### 3.4 Configuration Playwright Parallèle

**playwright.config.ts (modifications):**
```typescript
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,  // Enable parallel execution
  workers: process.env.CI ? 4 : 2,  // 4 workers in CI, 2 locally
  
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:8088',
  },
  
  // Global setup: prepare isolated environments per worker
  globalSetup: './tests/e2e/global-setup-parallel.ts',
});
```

**global-setup-parallel.ts (nouveau fichier):**
- Détecter `PLAYWRIGHT_WORKER_INDEX`
- Créer DB dédiée: `test_e2e_w${index}`
- Seed data dans DB worker
- Retourner config (baseURL avec port dédié si nécessaire)

### 3.5 CI GitHub Actions

**Optimisations:**

1. **Parallélisation intra-job (pytest):**
```yaml
- name: Run pytest (parallel)
  run: |
    pytest -n auto --dist=loadscope -m "not postgres"
```

2. **Matrice pour suites longues:**
```yaml
strategy:
  matrix:
    suite: [unit, api, processing]
steps:
  - name: Run ${{ matrix.suite }}
    run: pytest -n auto tests_${{ matrix.suite }}/
```

3. **E2E avec workers Playwright:**
```yaml
- name: Run E2E
  run: |
    cd frontend
    npx playwright test --workers=4
```

## 4. Conventions Zenflow

### 4.1 Variables d'Environnement par Task

**Fichier: `.zenflow/tasks/{task_id}/.env.task`**
```bash
# Auto-généré par Zenflow lors de la création de task
ZENFLOW_TASK_ID=ci-suite-tests-parallele-zenflow-9947
ZENFLOW_PORT_OFFSET=947

# Derived ports
POSTGRES_PORT=6379
REDIS_PORT=7326
BACKEND_PORT=8947
FRONTEND_PORT=6120
```

**Intégration Docker Compose:**
```yaml
# docker-compose.zenflow.yml (template)
services:
  db:
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
  backend:
    ports:
      - "${BACKEND_PORT:-8000}:8000"
    environment:
      - DATABASE_URL=postgres://user:pass@db:5432/viatique
```

### 4.2 Script de Lancement Zenflow-Aware

**Nouveau fichier: `scripts/test_parallel_zenflow.sh`**
```bash
#!/usr/bin/env bash
set -euo pipefail

# Détecte si on est dans une task Zenflow
if [[ -n "${ZENFLOW_TASK_ID:-}" ]]; then
  echo "Zenflow task detected: $ZENFLOW_TASK_ID"
  source .zenflow/tasks/$ZENFLOW_TASK_ID/.env.task
fi

# Run tests with isolation
PYTEST_XDIST_WORKER_COUNT=${PYTEST_WORKERS:-auto}
pytest -n $PYTEST_XDIST_WORKER_COUNT "$@"
```

## 5. Livrables

### 5.1 Documentation

**Fichier: `docs/development/PARALLEL_TESTING_GUIDE.md`**
Contenu:
- Comment ajouter un test sans casser le parallèle
- Best practices: éviter les singletons, utiliser fixtures, isolation DB
- Debugging flaky tests
- Exemples de marqueurs pytest

### 5.2 Patches Techniques

1. **Backend:**
   - `requirements.txt`: ajouter `pytest-xdist~=3.5`
   - `pytest.ini`: config xdist
   - `conftest.py`: améliorer `mock_media` avec worker ID
   - `core/settings_test.py`: validation isolation DB

2. **Frontend:**
   - `playwright.config.ts`: enable parallel workers
   - `tests/e2e/global-setup-parallel.ts`: isolation DB par worker
   - `package.json`: scripts pour parallel run

3. **CI:**
   - `.github/workflows/korrigo-ci.yml`: ajout pytest-xdist, matrice jobs
   - Validation: 5 runs consécutifs sans flake

4. **Zenflow:**
   - `.zenflow/tasks/template/.env.task`: template variables
   - `scripts/test_parallel_zenflow.sh`: wrapper isolation

### 5.3 Preuves de Validation

**Critère de succès: 0 flaky sur 5 runs consécutifs**

Fichiers de preuve:
- `.zenflow/tasks/{task_id}/proof_run1.txt` → `proof_run5.txt`
- Chaque preuve contient:
  - Output complet pytest/playwright
  - Timing des tests
  - Confirmation: "X tests passed, 0 failed, 0 flaky"

**Commande de validation:**
```bash
for i in {1..5}; do
  echo "=== RUN $i ==="
  pytest -n auto --tb=short 2>&1 | tee proof_run$i.txt
  if grep -q "FAILED\|ERROR" proof_run$i.txt; then
    echo "FLAKY DETECTED in run $i"
    exit 1
  fi
done
echo "✅ 5 runs successful, 0 flaky"
```

## 6. Décisions Techniques

### 6.1 Choix de pytest-xdist vs pytest-parallel
**Décision: pytest-xdist**
- Raisons: 
  - Mieux intégré avec pytest-django
  - Support `--dist=loadscope` (optimal pour tests DB)
  - Communauté plus large, maintenance active

### 6.2 Isolation DB: Suffix vs Schémas PostgreSQL
**Décision: DB Suffix (databases séparées)**
- Raisons:
  - Plus simple (pas de gestion de schémas)
  - Compatible SQLite (dev local) et PostgreSQL (CI)
  - Django `TEST['NAME']` natif

### 6.3 Playwright: Workers séquentiels vs parallèles
**Décision: Parallèle avec isolation**
- Raisons:
  - Gain de temps significatif (2-4x)
  - Isolation DB garantit pas de conflits
  - Modern best practice Playwright

### 6.4 Zenflow: Ports fixes vs dynamiques
**Décision: Ports dynamiques basés sur task ID**
- Raisons:
  - Permet vraiment l'exécution parallèle de tasks
  - Déterministe (task ID → port)
  - Pas de random → reproductible

## 7. Risques et Mitigations

| Risque | Impact | Probabilité | Mitigation |
|--------|--------|-------------|------------|
| Tests non thread-safe (singletons) | Flaky tests | Moyen | Audit code, fixtures isolées |
| Fixtures PDF partagées (write) | Conflits I/O | Faible | Read-only ou copie par worker |
| Ports déjà utilisés (dev local) | Échec démarrage | Moyen | Check port disponible avant up |
| DB non nettoyée entre runs | Pollution données | Faible | Transaction rollback automatique |
| Zenflow tasks > 10 en parallèle | Épuisement ressources | Faible | Limiter workers par task (CI_MAX_WORKERS) |

## 8. Non-Scope (Hors Périmètre)

- ❌ Migration complète vers pytest pur (garder TestCase existants)
- ❌ Refonte architecture Docker (utiliser compose existant)
- ❌ Parallélisation Celery tasks (hors scope tests)
- ❌ Optimisation temps d'exécution tests (focus: stabilité)

## 9. Critères d'Acceptation

### Must-Have (Critères bloquants)
- ✅ pytest-xdist installé et configuré
- ✅ 4 suites identifiées et documentées (unit-fast, integration-api, processing, e2e)
- ✅ Isolation DB par worker (pytest + playwright)
- ✅ Media temp dir par worker
- ✅ 5 runs consécutifs sans flake (backend + frontend)
- ✅ Documentation: guide "comment ajouter un test"

### Should-Have (Souhaitable)
- ✅ Convention Zenflow ports dynamiques
- ✅ CI optimisé avec pytest-xdist
- ✅ Playwright workers > 1

### Nice-to-Have (Bonus)
- ⭕ Dashboard temps d'exécution par suite
- ⭕ Pre-commit hook validation parallèle locale
- ⭕ Métriques flakiness tracking

## 10. Questions Ouvertes et Clarifications

### Q1: Nombre optimal de workers
**Question:** Combien de workers pytest-xdist en CI (GitHub Actions)?
- Option A: `-n auto` (détection automatique CPU)
- Option B: Fixe `-n 4` (prévisible, budget CI)

**Recommandation:** `-n auto` local, `-n 4` CI (standard GitHub 2-core runners → 4 workers acceptable)

### Q2: Nettoyage bases de données test
**Question:** Faut-il nettoyer les DB `test_viatique_gw*` après chaque run?
- Option A: Laisser (Django recrée à chaque run)
- Option B: Cleanup explicite (CI)

**Recommandation:** Django gère automatiquement (`--create-db` pytest-django), cleanup explicite uniquement si problème espace disque CI.

### Q3: Seed data E2E par worker
**Question:** Dupliquer seed_e2e.py par worker ou schéma unique?
- Option A: DB dédiée par worker + seed complet
- Option B: DB partagée + cleanup entre tests

**Recommandation:** Option A (isolation maximale, pas de cleanup fragile)

---

**Document validé par:** [À compléter après revue utilisateur]
**Date:** 2026-01-31
**Version:** 1.0
