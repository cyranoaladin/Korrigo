# Zenflow Runner v3.0 - Final Version

**Status**: ✅ Production-Ready
**Date**: 2026-01-31
**Version**: 3.0 Final

---

## Ce qui a été corrigé

Votre runner Zenflow est maintenant **réellement fiable** avec les deux ajustements critiques appliqués :

### 1. ✅ Politique de Timeout Clarifiée (Politique A)

**Avant (v2.0)** :
```bash
# Timeout = success (DANGEREUX)
if [[ $exit_code -eq 0 ]] || [[ $exit_code -eq 124 ]]; then
  TASK_STATUS[$task_id]="success"
fi
```

**Maintenant (v3.0)** :
```bash
# Timeout = failure (BLOQUE les dépendants)
if [[ "${status}" == "timeout" ]]; then
  TASK_STATUS[$task_id]="timeout"
  echo "[...] Task ${task_id} timed out (will block dependents)" >&2
fi
```

**Impact** : Une tâche qui timeout ne débloque plus ses dépendants. Exemple :
- `40-seed-database` timeout → `41-e2e-teacher` ne démarre PAS
- Le rapport de deadlock affiche clairement : `dependency '40-seed-database' has status: timeout`

---

### 2. ✅ PHASE_TIMEOUT_SEC Remplace MAX_ITERATIONS

**Avant (v2.0)** :
```bash
MAX_ITERATIONS=200  # ~200 secondes max
for ((i=0; i<MAX_ITERATIONS; i++)); do
  sleep 1
  # polling...
done
```

**Maintenant (v3.0)** :
```bash
PHASE_TIMEOUT_SEC="${PHASE_TIMEOUT_SEC:-3600}"  # 1 heure par défaut
PHASE_START_TIME=$(date +%s)

while true; do
  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - PHASE_START_TIME))

  if [[ ${ELAPSED} -ge ${PHASE_TIMEOUT_SEC} ]]; then
    echo "ERROR: Phase timeout (${PHASE_TIMEOUT_SEC}s) exceeded" >&2
    # Kill all running tasks
    exit 1
  fi

  # ... polling
done
```

**Configuration** : Ajustez selon la phase
```bash
# Phase A (preflight) - rapide
PHASE_TIMEOUT_SEC=600 ./run_phase.sh A

# Phase E (E2E) - long
PHASE_TIMEOUT_SEC=3600 ./run_phase.sh E

# Phase F (prod) - moyen
PHASE_TIMEOUT_SEC=1800 ./run_phase.sh F
```

---

### 3. ✅ Amélioration du Rapport de Deadlock

**Avant (v2.0)** :
```
Max iterations exceeded - possible deadlock
```

**Maintenant (v3.0)** :
```
ERROR: Deadlock detected - 2 tasks still pending:
  - 42-e2e-admin-portal (needs: 40-seed-database)
    -> dependency '40-seed-database' has status: timeout
  - 43-e2e-corrector-flow (needs: 40-seed-database)
    -> dependency '40-seed-database' has status: timeout
```

**Avantage** : Vous voyez immédiatement :
- Quelles tâches sont bloquées
- Quelles dépendances ne sont pas satisfaites
- Quel est le statut de chaque dépendance (timeout, failure, pending)

---

## Fichiers Livrés

### 1. Scripts Core (Production-Ready)

| Fichier | Description | Statut |
|---------|-------------|--------|
| `.zenflow/_shared/scripts/run_task.sh` | Runner de tâche individuelle (v3.0) | ✅ Final |
| `.zenflow/_shared/scripts/run_phase.sh` | Orchestrateur de phase avec DAG (v3.0) | ✅ Final |
| `.zenflow/_shared/scripts/validate_runner.sh` | Script de validation automatique | ✅ Nouveau |

### 2. Documentation

| Fichier | Description |
|---------|-------------|
| `.zenflow/CHANGELOG-FINAL.md` | Changelog complet avec tous les fixes |
| `.zenflow/FINAL-VERSION-v3.0.md` | Ce document (résumé exécutif) |

---

## Validation Rapide

Exécutez le script de validation pour confirmer le bon fonctionnement :

```bash
cd /home/alaeddine/viatique__PMF
./.zenflow/_shared/scripts/validate_runner.sh
```

**Ce script teste automatiquement** :
1. **Test 1** : Timeout bloque les dépendants (+ deadlock detection)
2. **Test 2** : PHASE_TIMEOUT_SEC tue les tâches après X secondes
3. **Test 3** : Exécution parallèle avec MAX_JOBS

**Sortie attendue** :
```
Test 1 (Timeout Semantic): ✅ PASS
Test 2 (Phase Timeout):    ✅ PASS
Test 3 (Parallel Exec):    ✅ PASS

✅ ALL TESTS PASSED - Runner v3.0 is production-ready
```

---

## Utilisation en CI

### Configuration GitHub Actions

```yaml
name: Zenflow Audit

on: [push, pull_request]

jobs:
  phase-a-preflight:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v3
      - name: Run Phase A
        run: |
          export RUN_ID="${GITHUB_RUN_ID}-A"
          PHASE_TIMEOUT_SEC=600 ./.zenflow/_shared/scripts/run_phase.sh A

  phase-b-backend:
    needs: phase-a-preflight
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v3
      - name: Run Phase B
        run: |
          export RUN_ID="${GITHUB_RUN_ID}-B"
          MAX_JOBS=4 PHASE_TIMEOUT_SEC=1500 ./.zenflow/_shared/scripts/run_phase.sh B

  phase-e-e2e:
    needs: phase-b-backend
    runs-on: ubuntu-latest
    timeout-minutes: 90
    steps:
      - uses: actions/checkout@v3
      - name: Run Phase E
        run: |
          export RUN_ID="${GITHUB_RUN_ID}-E"
          MAX_JOBS=2 PHASE_TIMEOUT_SEC=5400 ./.zenflow/_shared/scripts/run_phase.sh E
```

**Points clés** :
- `timeout-minutes` du job doit être > PHASE_TIMEOUT_SEC (marge de 20%)
- `MAX_JOBS` limite le parallélisme (selon ressources CI)
- `RUN_ID` unique par pipeline pour isolation des preuves

---

## Variables d'Environnement

### Configuration du Runner

| Variable | Défaut | Description |
|----------|--------|-------------|
| `RUN_ID` | `$(date +%Y%m%d-%H%M%S)-$$` | Identifiant unique du run |
| `MAX_JOBS` | `4` | Nombre max de tâches parallèles |
| `PHASE_TIMEOUT_SEC` | `3600` | Timeout de phase (secondes) |
| `POLL_INTERVAL_SEC` | `1` | Intervalle de polling du scheduler |

### Configuration Docker (par tâche)

| Variable | Valeur | Description |
|----------|--------|-------------|
| `COMPOSE_PROJECT_NAME` | `zf-${RUN_ID}-${TASK_ID}` | Isolation Docker (automatique) |

---

## Codes de Sortie

| Code | Signification | Comportement Phase | Dépendants |
|------|---------------|-------------------|------------|
| `0` | Success | Continue | ✅ Débloqués |
| `1-123` | Failure | Stop | ❌ Bloqués |
| `124` | Timeout | Stop | ❌ Bloqués |

**Politique appliquée** : Timeout = Failure (Politique A)

---

## Structure des Preuves

Chaque exécution de tâche génère une structure de preuves complète :

```
.zenflow/proofs/${RUN_ID}/${TASK_ID}/
├── 00-meta/
│   ├── task.json          # Métadonnées d'exécution
│   └── env.sh             # Variables d'environnement
├── 10-commands/
│   ├── commands.json      # Liste des commandes
│   ├── step-0.sh          # Script de l'étape 0
│   └── step-0.json        # Métadonnées de l'étape 0
├── 20-logs/
│   └── step-0.log         # Logs stdout/stderr
├── 30-artifacts/
│   └── (artefacts générés par la tâche)
├── 40-checksums/
│   └── artifacts.sha256   # SHA256 des artefacts
└── 99-summary/
    ├── status.json        # Statut final (success/failure/timeout)
    └── .timeout_killed    # Flag de timeout (si applicable)
```

---

## Bugs Corrigés (Historique)

### v1.0 → v2.0
- ❌ Exécution ligne par ligne (cassait les scripts multi-lignes)
- ❌ `bash -c` eval (problème de sécurité)
- ❌ Timeout ne tuait pas l'arbre de processus
- ❌ Scope de EXIT_CODE dans les subshells

### v2.0 → v3.0 (FINAL)
- ✅ **TIMEOUT_KILLED via fichier flag** (pas de variable subshell)
- ✅ **Polling PID manuel** (pas de `wait -n`)
- ✅ **Timeout = failure** (bloque les dépendants)
- ✅ **PHASE_TIMEOUT_SEC** (pas de MAX_ITERATIONS)
- ✅ **Rapport de deadlock amélioré** (liste les dépendances insatisfaites)

---

## Checklist de Déploiement

Avant de déployer en production :

- [ ] Exécuter `./.zenflow/_shared/scripts/validate_runner.sh`
- [ ] Vérifier que les 3 tests passent (timeout, phase timeout, parallélisme)
- [ ] Configurer `PHASE_TIMEOUT_SEC` pour chaque phase dans votre CI
- [ ] Vérifier que `MAX_JOBS` est adapté aux ressources (2-4 recommandé)
- [ ] Tester un run complet local : `./run_phase.sh A && ./run_phase.sh B ...`
- [ ] Vérifier les preuves générées dans `.zenflow/proofs/${RUN_ID}/`
- [ ] Configurer archivage des preuves (CI artifacts, S3, etc.)

---

## Prochaines Étapes (Optionnel)

### Extension 1 : Flag `allow_timeout` par Tâche

Pour les tâches non critiques (rapports optionnels) :

```yaml
id: 90-optional-report
allow_timeout: true  # Ne bloque pas les dépendants si timeout
```

### Extension 2 : Retry Automatique

```yaml
id: 01-flaky-test
max_retries: 3
retry_delay_sec: 60
```

### Extension 3 : Exécution Conditionnelle

```yaml
id: 02-deploy-prod
condition: "${CI_BRANCH} == 'main' && ${CI_EVENT} == 'push'"
```

---

## Support et Documentation

### Fichiers de Référence
- **Convention des preuves** : `.zenflow/conventions/PROOFS_CONVENTION.md`
- **Modèle de sécurité** : `.zenflow/conventions/SECURITY.md`
- **Exemples de tâches** : `.zenflow/tasks/*/task.yaml`

### Dépannage

**Problème** : Phase timeout trop court
```bash
# Solution : Augmenter PHASE_TIMEOUT_SEC
PHASE_TIMEOUT_SEC=7200 ./run_phase.sh E
```

**Problème** : Trop de tâches en parallèle
```bash
# Solution : Réduire MAX_JOBS
MAX_JOBS=2 ./run_phase.sh B
```

**Problème** : Deadlock mystérieux
```bash
# Solution : Lire le rapport de deadlock qui liste les dépendances
# Vérifier les logs : .zenflow/proofs/${RUN_ID}/*/20-logs/
```

---

## Conclusion

Vous disposez maintenant d'un **runner Zenflow v3.0 production-ready** avec :

✅ **Sémantique de timeout cohérente** (timeout = failure)
✅ **Timeout de phase robuste** (PHASE_TIMEOUT_SEC)
✅ **Ordonnancement DAG fiable** (needs + parallel_safe)
✅ **Détection de deadlock explicite** (rapport de dépendances)
✅ **Traçabilité complète** (structure de preuves auditables)
✅ **Isolation Docker** (COMPOSE_PROJECT_NAME unique)
✅ **Cleanup de processus fiable** (setsid + PGID)
✅ **Communication subshell-safe** (flags fichier)

**Zero bug de correction connu**. Prêt pour déploiement CI/CD.

---

**Auteur** : Alaeddine BEN RHOUMA
**Date** : 2026-01-31
**Version** : 3.0 Final
**Statut** : ✅ Production-Ready
