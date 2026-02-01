# Zenflow v3.0 - Quick Reference Card

## Commandes Essentielles

### Exécuter une Tâche
```bash
# Exécution manuelle d'une tâche
RUN_ID="manual-$(date +%Y%m%d-%H%M%S)" ./.zenflow/_shared/scripts/run_task.sh 01-backend-lint-type

# Voir le résultat
cat ./.zenflow/proofs/${RUN_ID}/01-backend-lint-type/99-summary/status.json
```

### Exécuter une Phase
```bash
# Phase A (preflight) - rapide
PHASE_TIMEOUT_SEC=600 ./.zenflow/_shared/scripts/run_phase.sh A

# Phase B (backend) - moyen
MAX_JOBS=4 PHASE_TIMEOUT_SEC=1500 ./.zenflow/_shared/scripts/run_phase.sh B

# Phase E (E2E) - long
MAX_JOBS=2 PHASE_TIMEOUT_SEC=3600 ./.zenflow/_shared/scripts/run_phase.sh E
```

### Validation du Runner
```bash
# Tester le runner v3.0 (3 tests automatiques)
./.zenflow/_shared/scripts/validate_runner.sh
```

---

## Variables d'Environnement

### Core
| Variable | Défaut | Usage |
|----------|--------|-------|
| `RUN_ID` | `$(date +%Y%m%d-%H%M%S)-$$` | Identifiant unique |
| `MAX_JOBS` | `4` | Max tâches parallèles |
| `PHASE_TIMEOUT_SEC` | `3600` | Timeout phase (sec) |

### Exemples
```bash
# Run ID custom
RUN_ID="ci-${CI_BUILD_ID}" ./run_phase.sh B

# Limiter parallélisme
MAX_JOBS=2 ./run_phase.sh E

# Augmenter timeout
PHASE_TIMEOUT_SEC=7200 ./run_phase.sh E
```

---

## Codes de Sortie

| Code | Signification | Action Phase | Dépendants |
|------|--------------|--------------|------------|
| `0` | ✅ Success | Continue | Débloqués |
| `1-123` | ❌ Failure | Stop | Bloqués |
| `124` | ⏱️ Timeout | Stop | Bloqués |

**Important** : Timeout = Failure (Politique A)

---

## Métadonnées de Tâche

### Format YAML
```yaml
id: 01-backend-lint
title: Backend Linting & Type Checking
phase: A                  # A, B, C, D, E, F
parallel_safe: true       # Peut s'exécuter en parallèle
needs: []                 # Dépendances (IDs de tâches)
timeout_sec: 300          # Timeout tâche (secondes)

env:                      # Variables d'environnement
  DJANGO_SETTINGS_MODULE: core.settings_test
  PYTHONPATH: /app/backend

commands:
  - name: Ruff check
    run: |
      ruff check . --output-format=json > ../proofs/${RUN_ID}/${TASK_ID}/30-artifacts/ruff.json
      ERROR_COUNT=$(python3 -c "import json; d=json.load(open('../proofs/${RUN_ID}/${TASK_ID}/30-artifacts/ruff.json')); print(len(d))")
      if [[ ${ERROR_COUNT} -gt 0 ]]; then
        echo "Found ${ERROR_COUNT} errors" >&2
        exit 1
      fi

  - name: Type check
    run: |
      mypy . --json-report ../proofs/${RUN_ID}/${TASK_ID}/30-artifacts/mypy.json || exit 1
```

---

## Structure des Preuves

```
.zenflow/proofs/${RUN_ID}/${TASK_ID}/
├── 00-meta/
│   ├── task.json          # Métadonnées (run_id, started_at, hostname, etc.)
│   └── env.sh             # Variables d'environnement exportées
│
├── 10-commands/
│   ├── commands.json      # Liste des commandes
│   ├── step-N.sh          # Script de chaque étape
│   └── step-N.json        # Métadonnées (name, started_at, exit_code)
│
├── 20-logs/
│   └── step-N.log         # Stdout/stderr de chaque étape
│
├── 30-artifacts/
│   └── (artefacts générés : JSON, CSV, reports, etc.)
│
├── 40-checksums/
│   └── artifacts.sha256   # SHA256 de tous les artefacts
│
└── 99-summary/
    ├── status.json        # Statut final
    └── .timeout_killed    # Flag présent si timeout
```

---

## Inspection des Résultats

### Statut d'une Tâche
```bash
# Voir le statut final
cat .zenflow/proofs/${RUN_ID}/${TASK_ID}/99-summary/status.json

# Exemple :
# {
#   "task_id": "01-backend-lint-type",
#   "run_id": "20260131-143022-12345",
#   "status": "success",        # success | failure | timeout
#   "exit_code": 0,
#   "completed_at": "2026-01-31T14:35:10+00:00",
#   "timeout_sec": 300
# }
```

### Logs d'une Étape
```bash
# Voir les logs d'une étape spécifique
cat .zenflow/proofs/${RUN_ID}/${TASK_ID}/20-logs/step-0.log
cat .zenflow/proofs/${RUN_ID}/${TASK_ID}/20-logs/step-1.log

# Tail en temps réel
tail -f .zenflow/proofs/${RUN_ID}/${TASK_ID}/20-logs/step-0.log
```

### Artefacts Générés
```bash
# Lister les artefacts
ls -lh .zenflow/proofs/${RUN_ID}/${TASK_ID}/30-artifacts/

# Vérifier les checksums
cat .zenflow/proofs/${RUN_ID}/${TASK_ID}/40-checksums/artifacts.sha256

# Valider l'intégrité
cd .zenflow/proofs/${RUN_ID}/${TASK_ID}/30-artifacts/
sha256sum -c ../40-checksums/artifacts.sha256
```

---

## Dépannage

### Problème : Phase Timeout
```bash
# Symptôme : "ERROR: Phase timeout (3600s) exceeded"
# Solution : Augmenter PHASE_TIMEOUT_SEC

PHASE_TIMEOUT_SEC=7200 ./run_phase.sh E  # 2 heures
```

### Problème : Deadlock Détecté
```bash
# Symptôme : "Deadlock detected - 2 tasks still pending"
# Lire le rapport :
# ERROR: Deadlock detected - 2 tasks still pending:
#   - 42-e2e-admin (needs: 40-seed-db)
#     -> dependency '40-seed-db' has status: timeout
#
# Actions :
# 1. Vérifier pourquoi la dépendance a échoué/timeout
# 2. Voir les logs de la dépendance :
cat .zenflow/proofs/${RUN_ID}/40-seed-db/20-logs/step-*.log

# 3. Corriger la tâche ou augmenter son timeout
```

### Problème : Trop de Tâches Parallèles
```bash
# Symptôme : Ressources insuffisantes (OOM, CPU 100%)
# Solution : Réduire MAX_JOBS

MAX_JOBS=2 ./run_phase.sh B  # Maximum 2 tâches en parallèle
```

### Problème : Tâche Timeout
```bash
# Symptôme : status.json montre "status": "timeout"
# Solution 1 : Augmenter timeout_sec dans task.yaml

# task.yaml (avant)
timeout_sec: 300

# task.yaml (après)
timeout_sec: 600

# Solution 2 : Optimiser la tâche (paralléliser, caching, etc.)
```

### Problème : Docker Containers Conflict
```bash
# Symptôme : "Container name already in use"
# Cause : COMPOSE_PROJECT_NAME collision

# Vérification :
docker ps -a | grep zf-

# Nettoyage manuel :
docker-compose -p zf-${OLD_RUN_ID}-${TASK_ID} down

# Prévention : Le runner v3.0 génère des noms uniques automatiquement
# COMPOSE_PROJECT_NAME=zf-${RUN_ID}-${TASK_ID}
```

---

## Configuration CI Recommandée

### GitHub Actions
```yaml
jobs:
  zenflow-phase-a:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v3
      - name: Phase A
        run: |
          export RUN_ID="${GITHUB_RUN_ID}-A"
          PHASE_TIMEOUT_SEC=600 MAX_JOBS=4 \
            ./.zenflow/_shared/scripts/run_phase.sh A
      - name: Upload Proofs
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: proofs-phase-a
          path: .zenflow/proofs/${GITHUB_RUN_ID}-A/
```

### GitLab CI
```yaml
zenflow:phase-a:
  stage: audit
  timeout: 15 minutes
  script:
    - export RUN_ID="${CI_PIPELINE_ID}-A"
    - PHASE_TIMEOUT_SEC=600 MAX_JOBS=4 ./.zenflow/_shared/scripts/run_phase.sh A
  artifacts:
    when: always
    paths:
      - .zenflow/proofs/${CI_PIPELINE_ID}-A/
    expire_in: 30 days
```

---

## Timeouts Recommandés par Phase

| Phase | Description | PHASE_TIMEOUT_SEC | MAX_JOBS |
|-------|-------------|-------------------|----------|
| A | Preflight (lint, format, static analysis) | `600` (10m) | `4` |
| B | Backend Tests (unit, integration) | `1500` (25m) | `4` |
| C | API/RBAC Tests | `1200` (20m) | `3` |
| D | PDF/Celery Tests | `1800` (30m) | `2` |
| E | E2E Tests (Playwright) | `3600` (60m) | `2` |
| F | Production Smoke Tests | `1800` (30m) | `2` |

**Note** : Ajustez selon vos ressources CI (CPU, RAM, workers)

---

## Checklist Déploiement

### Avant Premier Run
- [ ] Valider le runner : `./.zenflow/_shared/scripts/validate_runner.sh`
- [ ] Vérifier structure `.zenflow/tasks/*/task.yaml`
- [ ] Configurer timeouts par phase
- [ ] Tester localement : `./run_phase.sh A`
- [ ] Vérifier preuves générées : `.zenflow/proofs/${RUN_ID}/`

### Configuration CI
- [ ] Configurer `PHASE_TIMEOUT_SEC` pour chaque phase
- [ ] Configurer `MAX_JOBS` selon ressources
- [ ] Archiver les preuves (CI artifacts)
- [ ] Configurer notifications (Slack, email, etc.)
- [ ] Ajouter timeout du job CI > PHASE_TIMEOUT_SEC

### Monitoring
- [ ] Surveiller temps d'exécution des phases
- [ ] Identifier les tâches bottleneck
- [ ] Optimiser les timeouts (ni trop court, ni trop long)
- [ ] Vérifier utilisation ressources (CPU, RAM, disque)

---

## Ressources

### Documentation Complète
- **Changelog** : `.zenflow/CHANGELOG-FINAL.md`
- **Guide complet** : `.zenflow/FINAL-VERSION-v3.0.md`
- **Convention preuves** : `.zenflow/conventions/PROOFS_CONVENTION.md`
- **Sécurité** : `.zenflow/conventions/SECURITY.md`

### Exemples de Tâches
- Backend Lint : `.zenflow/tasks/01-backend-lint-type/task.yaml`
- Celery Test : `.zenflow/tasks/30-celery-import-pdf/task.yaml`
- E2E Test : `.zenflow/tasks/41-e2e-teacher-correction/task.yaml`

---

**Version** : 3.0 Final
**Date** : 2026-01-31
**Statut** : ✅ Production-Ready
