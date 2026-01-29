# 🎯 Release Gate One-Shot Runner

## Description

Script de validation **complète et automatisée** pour Korrigo/Viatique, exécutant toutes les phases du Release Gate en un seul run:

- **Phase A**: Build (no-cache)
- **Phase B**: Boot & Stability (3 minutes sans restart)
- **Phase C**: Migrations
- **Phase D**: Seed idempotent (x2) + validation pages_images
- **Phase E**: E2E Workflow (3 runs complets avec annotations)
- **Phase F**: Tests backend (pytest, 0 failed/skipped)
- **Phase G**: Capture logs
- **Phase H**: Validation summary

**Durée totale**: ~10-15 minutes
**Critères**: Zero-tolerance (0 failures, 0 warnings, 0 skipped)

---

## Usage

### Basique (défaut)

```bash
./scripts/release_gate_oneshot.sh
```

### Avec variables d'environnement personnalisées

```bash
# Production-like avec secrets
METRICS_TOKEN="your-strong-secret-token-64chars-min" \
ADMIN_PASSWORD="secure-admin-password" \
TEACHER_PASSWORD="secure-teacher-password" \
./scripts/release_gate_oneshot.sh

# Custom log directory
LOG_DIR="/custom/path/logs" \
./scripts/release_gate_oneshot.sh

# Custom compose file
COMPOSE_FILE="infra/docker/docker-compose.prod.yml" \
./scripts/release_gate_oneshot.sh
```

---

## Variables d'Environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `ROOT` | `/home/alaeddine/viatique__PMF` | Racine du projet |
| `COMPOSE_FILE` | `infra/docker/docker-compose.local-prod.yml` | Fichier Docker Compose |
| `NGINX_BASE_URL` | `http://localhost:8088` | URL de base Nginx |
| `BACKEND_SVC` | `backend` | Nom du service backend |
| `LOG_DIR` | `/tmp/release_gate_{timestamp}` | Répertoire des logs |
| `DJANGO_ENV` | `production` | Environnement Django |
| `DEBUG` | `False` | Mode debug |
| `METRICS_TOKEN` | `` (vide) | Token pour /metrics (vide = public) |
| `ADMIN_PASSWORD` | `` (vide) | Password admin (vide = random) |
| `TEACHER_PASSWORD` | `` (vide) | Password prof (vide = random) |
| `TEST_PROF_PASSWORD` | `prof` | Password pour tests E2E |

---

## Phases d'Exécution

### Phase 0: Clean Environment
- `docker compose down -v --remove-orphans`
- Nettoyage complet des volumes et containers

### Phase A: Build (no-cache)
- Build strict sans cache
- Vérifie la reproductibilité du build

### Phase B: Boot & Stability
- Démarrage des services
- Health checks (`/api/health/`, `/metrics`)
- Stabilité 3 minutes (0 restarts)

### Phase C: Migrations
- `python manage.py migrate --noinput`
- Vérification état migrations

### Phase D: Seed (idempotent)
- Run 1: Création données
- Run 2: Vérification idempotence
- Reset password prof1 pour E2E
- **Validation critique**: `pages_images > 0` pour toutes les copies READY

### Phase E: E2E Workflow (3 runs)
Chaque run exécute:
1. Login prof1 (session + CSRF)
2. Récupération copy READY
3. Lock copy (avec token)
4. POST annotation (format vectoriel)
5. GET annotations (vérification count > 0)
6. Release lock
7. Reset pour run suivant

**Validation P0**: Annotation POST retourne 201 (pas 400 "no pages")

### Phase F: Tests Backend
- `pytest -v --tb=short`
- **Zero tolerance**: 0 failed, 0 skipped

### Phase G: Logs Capture
- Logs complets de tous les services
- Logs backend (tail 500)
- État final des containers

### Phase H: Validation Summary
- Résumé des tests
- Validation seed (pages > 0)
- Health check logs
- Localisation artifacts

---

## Artifacts Générés

Tous les logs sont sauvegardés dans `$LOG_DIR` (exemple: `/tmp/release_gate_20260129T074500Z/`):

```
00_compose_down.log          - Clean initial
01_build_nocache.log         - Build logs
02_up.log                    - Boot logs
03_ps_initial.log            - État initial containers
04_wait_health.log           - Health check /api/health/
05_wait_metrics.log          - Health check /metrics
06_stability_180s.log        - Stabilité 3 minutes
07_migrate.log               - Migrations
08_seed_run1.log             - Seed run 1 (création)
09_seed_run2.log             - Seed run 2 (idempotence) ⭐
10_reset_prof_password.log   - Reset password E2E
11_db_sanity.log             - Sanity check + pages validation ⭐
12_e2e_3runs.log             - E2E 3 runs complets ⭐
13_pytest_full.log           - Tests backend complets ⭐
14_compose_logs.log          - Logs tous services
15_backend_logs_tail.log     - Logs backend (tail 500)
16_ps_final.log              - État final containers
17_validation_summary.log    - Résumé validation ⭐
```

**⭐ Logs critiques pour validation zero-tolerance**

---

## Vérification Rapide

Après exécution, vérifier rapidement:

```bash
# Résumé des validations
grep -E '✅|❌' /tmp/release_gate_*/17_validation_summary.log

# Tests: doit afficher "X passed in Y.YYs" avec 0 failed, 0 skipped
grep "passed" /tmp/release_gate_*/13_pytest_full.log | tail -1

# Seed: toutes les copies doivent avoir pages > 0
grep "pages=" /tmp/release_gate_*/11_db_sanity.log

# E2E: doit afficher "3/3 RUNS PASSED"
grep "E2E.*RUN.*PASSED" /tmp/release_gate_*/12_e2e_3runs.log
```

---

## Critères de Succès (Zero Tolerance)

| Critère | Attendu | Vérification |
|---------|---------|--------------|
| **Build** | Success | Log `01_build_nocache.log` |
| **Boot** | 5/5 healthy | Log `03_ps_initial.log` |
| **Stabilité** | 0 restarts (3 min) | Log `06_stability_180s.log` |
| **Migrations** | RC=0 | Log `07_migrate.log` |
| **Seed idempotent** | 2x success | Logs `08_*.log`, `09_*.log` |
| **Pages > 0** | All READY copies | Log `11_db_sanity.log` ⭐ |
| **E2E runs** | 3/3 passed | Log `12_e2e_3runs.log` ⭐ |
| **Annotation POST** | 201 (not 400) | Log `12_e2e_3runs.log` ⭐ |
| **Tests** | 0 failed, 0 skipped | Log `13_pytest_full.log` ⭐ |
| **Warnings** | 0 critical errors | Log `15_backend_logs_tail.log` |

---

## Dépannage

### Script échoue à la Phase A (Build)

**Symptôme**: Erreur lors du build
**Solution**: Vérifier que Docker a assez de mémoire/disk. Nettoyer images:
```bash
docker system prune -af
```

### Script échoue à la Phase B (Health checks timeout)

**Symptôme**: Health checks ne passent pas après 120s
**Solution**: Vérifier les logs backend:
```bash
docker compose -f infra/docker/docker-compose.local-prod.yml logs backend
```

### Script échoue à la Phase E (E2E)

**Symptôme**: Erreur 400 "page_index" ou "Missing lock token"
**Solution**: Vérifier que le code est à jour avec les derniers commits CI fixes

### Tests échouent (Phase F)

**Symptôme**: pytest affiche "X failed"
**Solution**: Consulter `13_pytest_full.log` pour détails. Si rate limiting tests échouent, vérifier que Redis est disponible.

### "No READY copy found" pendant E2E

**Symptôme**: Aucune copie READY disponible
**Solution**: Vérifier logs seed (`08_seed_run1.log`). Les copies doivent avoir `pages > 0`.

---

## Intégration CI/CD

### GitHub Actions

```yaml
- name: Release Gate Validation
  run: |
    export METRICS_TOKEN="${{ secrets.METRICS_TOKEN }}"
    export ADMIN_PASSWORD="${{ secrets.ADMIN_PASSWORD }}"
    export TEACHER_PASSWORD="${{ secrets.TEACHER_PASSWORD }}"
    ./scripts/release_gate_oneshot.sh

- name: Upload Artifacts
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: release-gate-logs
    path: /tmp/release_gate_*
    retention-days: 30
```

### GitLab CI

```yaml
release-gate:
  stage: validate
  script:
    - export METRICS_TOKEN="$METRICS_TOKEN"
    - export ADMIN_PASSWORD="$ADMIN_PASSWORD"
    - export TEACHER_PASSWORD="$TEACHER_PASSWORD"
    - ./scripts/release_gate_oneshot.sh
  artifacts:
    when: always
    paths:
      - /tmp/release_gate_*
    expire_in: 30 days
```

---

## Comparaison avec Validation Manuelle

| Aspect | Manuelle | One-Shot |
|--------|----------|----------|
| **Durée** | 30-45 min | 10-15 min |
| **Reproductibilité** | Variable | 100% |
| **Documentation** | Manuelle | Auto (logs) |
| **Erreurs humaines** | Possibles | Éliminées |
| **CI/CD** | Difficile | Natif |
| **Artifacts** | À créer manuellement | Auto |

---

## Liens Utiles

- **Release Gate Report**: `/tmp/final_deployment_report.txt`
- **CI Fixes Report**: `/tmp/CI_FIXES_VALIDATION_REPORT.md`
- **Documentation Rules**: `.claude/rules/`
- **Docker Compose**: `infra/docker/docker-compose.local-prod.yml`

---

## Changelog

### v1.0.0 (2026-01-29)
- ✅ Adaptation initiale du script original
- ✅ Authentification session Django + CSRF
- ✅ Format annotations bounding box (`page_index`, `x`, `y`, `w`, `h`)
- ✅ Lock token management
- ✅ Validation `pages_images > 0` (P0 fix)
- ✅ E2E 3 runs complets avec annotations
- ✅ Zero tolerance (0 failed, 0 skipped)
- ✅ Pagination handling pour GET annotations

---

**Auteur**: Claude Sonnet 4.5
**Date**: 2026-01-29
**Status**: Production Ready ✅
