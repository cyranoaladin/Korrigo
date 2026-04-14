# Feuille de route — Fusion de la production dans `main`

> **Statut** : En cours de préparation  
> **Date** : 2026-04-15  
> **Auteur** : Kimi Code CLI  
> **Urgence** : Haute (divergence critique entre `main` et la prod)

---

## 1. Diagnostic de la situation

### 1.1 Historique de `main` (GitHub + local)
- **Dernier commit** : `372d3b5` — *cleanup(plan-a): coherence fixes, dead code removal, migration merges, infra alignment*
- Contient :
  - Le Plan A (UTF-8 fixes, HTML fix, cleanup frontend/backend, migrations merge, alignement infra)
  - Des features récentes non déployées (password reset, AdminOverview, theme system, etc.)
  - Des migrations Django complètes (`core`, `exams`, `grading`, `students`)

### 1.2 Historique du serveur de production (`korrigo.labomaths.tn`)
- **Dernier commit** : `025d889` — *hotfix(frontend): correct UTF-8 escape sequences in production*
- **Branche effective** : `main` locale sur le serveur (divergée complètement)
- Contient :
  - La refonte du bilan (`v2-bilan-improvements`)
  - Le questionnaire correcteur / bilan
  - La landing page / page `/korrigo`
  - Rate-limiting, transparence banner, iframe PDF embedding
  - **Suppression de features présentes dans `main`** : password reset, certaines migrations, `AdminOverview`, `theme.css`, etc.

### 1.3 Nature de la divergence
- **Aucun ancêtre commun** entre `main` local et le serveur.
- Les deux repos partagent le même nom de projet mais ont des historiques git indépendants (probablement suite à un `filter-repo`, rebase massif, ou clone parallèle).
- Un `git merge --allow-unrelated-histories` génère **des centaines de conflits** sur pratiquement tous les fichiers.

---

## 2. Stratégie recommandée

> **Principe** : Le serveur de production est la source de vérité pour le code actif. `main` contient des features importantes qui doivent être réintégrées manuellement.

### Option A — "Adoption chirurgicale" (Recommandée)
1. **Adopter le code du serveur comme nouveau tronc commun**.
2. **Nettoyer** le repo serveur (supprimer les fichiers parasites : `.coverage`, `.test_venv`, backups, data files, etc.).
3. **Réimplémenter manuellement** les features de `main` absentes de la prod :
   - Password reset (`core/views_password_reset.py`, templates, tests)
   - `AdminOverview` et les composants associés
   - Système de thème (`theme.css`, `useTheme.js`)
   - Migrations manquantes (vérifier la compatibilité avec la base de prod)
4. **Réappliquer le Plan A** sur cette base propre (clean imports, dead code removal, alignement infra).
5. **Remplacer `main`** par cette nouvelle ligne.

### Option B — "Merge unrelated histories"
1. `git merge --allow-unrelated-histories server-prod` dans `main`.
2. Résoudre les conflits un par un (travail de plusieurs heures).
3. **Risque élevé** d'introduire des régressions ou des fichiers parasites dans l'historique de `main`.

---

## 3. Différences critiques à résoudre

### 3.1 Features présentes dans `main` mais ABSENTES de la prod

| Feature / Fichier | Impact si perdu | Action |
|-------------------|-----------------|--------|
| `backend/core/views_password_reset.py` | Les utilisateurs ne peuvent plus réinitialiser leur mot de passe | Réimplémenter |
| `backend/core/templates/registration/password_reset_*.html` | UI du password reset | Réimplémenter |
| `backend/core/migrations/0004_questionnaire_coordinator_group.py` | Structure DB questionnaire | Vérifier si déjà appliquée |
| `backend/core/migrations/0005_normalize_questionnaire_group.py` | Structure DB questionnaire | Vérifier si déjà appliquée |
| `backend/core/migrations/0006_fix_questionnaire_coordinator_duplicates.py` | Données questionnaire | Vérifier si déjà appliquée |
| `backend/grading/migrations/0016_add_save_appreciation_action.py` | Action "save_appreciation" | Vérifier compatibilité |
| `backend/grading/migrations/0017-0022` | Évolution des annotations/scores | Vérifier compatibilité |
| `frontend/src/views/admin/AdminOverview.vue` | Dashboard admin | Réimplémenter |
| `frontend/src/components/admin/AdminBreadcrumb.vue` | Navigation admin | Réimplémenter |
| `frontend/src/components/admin/AdminSidebar.vue` | Navigation admin | Réimplémenter |
| `frontend/src/assets/theme.css` | Thème global | Réimplémenter |
| `frontend/src/composables/useTheme.js` | Logique thème | Réimplémenter |
| `frontend/src/views/ForgotPassword.vue` | UI mot de passe oublié | Réimplémenter |
| `frontend/src/views/ResetPasswordConfirm.vue` | UI confirmation reset | Réimplémenter |

### 3.2 Features présentes en prod mais ABSENTES de `main`

| Feature / Fichier | Impact si perdu | Action |
|-------------------|-----------------|--------|
| `backend/grading/questionnaire_bilan.py` | Bilan questionnaire | **Indispensable** — garder |
| `frontend/src/views/admin/QuestionnaireBilan.vue` | UI bilan questionnaire | **Indispensable** — garder |
| `frontend/src/views/corrector/QuestionnaireView.vue` | UI questionnaire correcteur | **Indispensable** — garder |
| `frontend/src/views/corrector/StudentBilan.vue` | UI bilan étudiant | **Indispensable** — garder |
| Landing page `/korrigo` (`Home.vue`, `HomeView.vue`) | Page d'accueil publique | **Indispensable** — garder |
| Rate limiting student login | Sécurité | **Indispensable** — garder |
| CSP / iframe fixes for PDF | Affichage PDF étudiant | **Indispensable** — garder |

### 3.3 Fichiers parasites à nettoyer (présents en prod, à supprimer)

```
.coverage
.env.backup.*
backend/.coverage
backend/.test_venv/
backend/test_exam.pdf
backend/test_results_*.txt
backend/verify_fixtures.py
backend/verify_mission20.py
debug_settings.py
deploy_*.sh (à déplacer dans scripts/deploy/)
docker-compose.prod.yml.obsolete
enseignants.csv
eval_loi_binom_log.pdf
fix_migrations.sh
korrigo_recovery_V3_*.json
manual_audit_script.py
proofs/ (tout le dossier)
reproduce_validation.sh
stat_BB_MATHS_2026.md
test_backup_restore_real*.py (à la racine)
test_e2e_real.py (à la racine)
test_ocr_real.py (à la racine)
verification_proof_*.txt
"20:, len(over_20))..." (fichier corrompu)
```

---

## 4. Plan d'action détaillé

### Étape 1 — Fenêtre de maintenance
- **Prérequis** : aucun correcteur actif (soir / week-end).
- **Durée estimée** : 2 à 4 heures.

### Étape 2 — Backup complet
```bash
ssh root@88.99.254.59
cd /tmp/korrigo_build
bash scripts/korrigo_backup.sh
```

### Étape 3 — Créer une branche de travail propre sur le serveur
```bash
cd /tmp/korrigo_build
git checkout -b prod-clean
git rm -rf backend/.test_venv/ .coverage backend/.coverage proofs/ ...
git rm -f *.pdf *.csv *.sh *.md *.txt *.json ...
# Réorganiser les scripts déployés à la racine
git mv deploy_*.sh scripts/deploy/ 2>/dev/null
```

### Étape 4 — Réconcilier les migrations
```bash
docker exec -e DJANGO_SETTINGS_MODULE=core.settings_prod docker-backend-1 \
  python manage.py showmigrations
```
- Vérifier que toutes les migrations de `main` sont soit appliquées, soit inutiles.
- Si des migrations de `main` sont absentes du code serveur mais appliquées en base, elles peuvent être recréées comme "fake" migrations.

### Étape 5 — Portage des features de `main` vers `prod-clean`
Pour chaque feature critique listée en 3.1 :
1. Copier les fichiers sources depuis `main`.
2. Vérifier les dépendances (imports, URLs, store, router).
3. Tester unitairement.

### Étape 6 — Réappliquer le Plan A
- Clean imports (ruff)
- Suppression du code mort identifié
- Alignement infra (si toujours pertinent)

### Étape 7 — Tests complets
```bash
# Frontend
cd frontend && npm run build && npm run lint

# Backend (Docker)
cd backend && docker build -t korrigo-backend-test . && \
  docker run --rm --entrypoint "" korrigo-backend-test bash -c \
  "python manage.py migrate && pytest -m 'not postgres and not slow' --tb=short"
```

### Étape 8 — Déploiement
```bash
# Sur le serveur
cd /tmp/korrigo_build
docker compose -f infra/docker/docker-compose.prod.yml down
docker compose -f infra/docker/docker-compose.prod.yml up -d --build
```

### Étape 9 — Synchroniser `main`
Une fois `prod-clean` validée en production :
```bash
# Local
git fetch origin
git checkout main
git reset --hard origin/prod-clean   # ou merge --allow-unrelated-histories
```

---

## 5. Risques et mitigation

| Risque | Mitigation |
|--------|------------|
| Perte de données correcteurs | Backup complet avant toute action |
| Migrations incompatibles | `showmigrations` + tests en preprod |
| Régression password reset | Tests E2E sur le flow complet |
| Régression bilan/questionnaire | Tests manuels avec un compte correcteur |
| Fichiers parasites dans le repo | Script de nettoyage exécuté avant le commit |

---

## 6. Historique des actions déjà réalisées

- **2026-04-14 23:xx** : Plan A exécuté et commité sur `main` (`372d3b5`).
- **2026-04-15 01:xx** : Backup de production (16 Mo).
- **2026-04-15 01:xx** : Hotfix UTF-8 déployé chirurgicalement en production (`CorrectorDesk.vue`, `AdminDashboard.vue`).
- **2026-04-15 01:xx** : Analyse de divergence : `main` et le serveur n'ont **aucun ancêtre commun**.

---

## 7. Prochaines étapes immédiates

1. [ ] Planifier une fenêtre de maintenance (soir / week-end).
2. [ ] Exécuter le nettoyage du repo serveur (`prod-clean`).
3. [ ] Auditer les migrations côté production.
4. [ ] Porter le password reset et `AdminOverview` depuis `main`.
5. [ ] Tests complets (build, pytest, E2E).
6. [ ] Déploiement et synchronisation de `main`.
