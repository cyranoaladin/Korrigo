# 🛡️ Release Gate Integrity - Règle de Discipline

**Version**: 1.0
**Date**: 2026-01-29
**Statut**: **OBLIGATOIRE** (non négociable)

---

## Principe Fondamental

> **"On ne merge dans `main` une modification du Release Gate (script/workflow) qu'après un run Release Gate SUCCESS sur `main`."**

Cette règle protège contre les **régressions silencieuses** qui casseraient la validation zero-tolerance.

---

## Fichiers Protégés (Release Gate Critical)

Toute modification de ces fichiers **déclenche** la règle :

### 1. Workflow CI
- `.github/workflows/release-gate.yml`

### 2. Script de Validation
- `scripts/release_gate_oneshot.sh`

### 3. Docker Compose (utilisé par Release Gate)
- `infra/docker/docker-compose.local-prod.yml`

### 4. Documentation Release Gate
- `.github/RELEASE_GATE_CI_SETUP.md`
- `RELEASE_GATE_REPORT_*.md`
- `PRODUCTION_CHECKLIST.md`
- `.github/RELEASE_GATE_INTEGRITY.md` (ce fichier)

---

## Procédure Obligatoire

### Étape 1 : Branche de Feature

```bash
# Créer branche pour modification Release Gate
git checkout -b fix/release-gate-improvement

# Modifier fichier(s) critique(s)
vim scripts/release_gate_oneshot.sh
vim .github/workflows/release-gate.yml

# Commit
git add -A
git commit -m "fix: Improve Release Gate detection for X"
git push origin fix/release-gate-improvement
```

### Étape 2 : Pull Request + CI Validation

```bash
# Créer PR
gh pr create --title "Fix: Improve Release Gate detection for X" \
  --body "Changes:
- Modified script to handle edge case Y
- Updated workflow pattern for Z

Release Gate Run on Feature Branch:
- CI Run: #XXXXXX (automated on PR)
- Status: ✅ SUCCESS
- Pytest: 205 passed, 0 failed, 0 skipped
- E2E: 3/3 runs passed"
```

**CI automatique sur PR** : Le workflow se déclenche automatiquement et valide la branche.

**Vérification** :
- [ ] CI run SUCCESS sur feature branch
- [ ] Tous les checks passent (pytest, E2E, seed)
- [ ] Pas de régression détectée

### Étape 3 : Merge dans Main

```bash
# Merger PR (après review + CI green)
gh pr merge --squash

# ⚠️ CRITIQUE : Déclencher workflow manuel sur main
git checkout main
git pull origin main

# Run manuel Release Gate sur main (workflow_dispatch)
gh workflow run release-gate.yml --ref main
```

### Étape 4 : Validation Post-Merge

```bash
# Attendre completion du run sur main
gh run watch <run_id> --exit-status

# Vérifier SUCCESS
gh run list --workflow="release-gate.yml" --limit 1
# → Status: success

# Si SUCCESS : ✅ Modification validée
# Si FAILURE : ⚠️ Rollback immédiat requis
```

---

## Cas d'Exception (Rollback Requis)

Si le run Release Gate **échoue sur main après merge** :

### Rollback Immédiat (< 10 min)

```bash
# 1. Identifier commit problématique
git log -1

# 2. Revert commit
git revert HEAD --no-edit

# 3. Push revert
git push origin main

# 4. Re-run Release Gate pour confirmer fix
gh workflow run release-gate.yml --ref main

# 5. Analyser cause sur branche séparée
git checkout -b fix/release-gate-hotfix
# ... investigation et correction
```

**Règle** : Main doit **toujours** être green. Un échec Release Gate post-merge = rollback immédiat, pas de "fix forward" sans validation.

---

## Rationalité (Pourquoi cette Règle)

### Problème Sans Cette Règle

**Scénario catastrophe** :
1. Dev modifie `scripts/release_gate_oneshot.sh` pour "améliorer" détection
2. Merge sans run final sur main
3. Pattern grep trop large → faux négatifs (tests cassés non détectés)
4. v1.0.1 déployé en prod avec tests cassés
5. **Incident production** découvert par utilisateurs, pas par CI

**Coût** : Perte de confiance, downtime, rollback d'urgence, investigation post-mortem.

### Bénéfice Avec Cette Règle

**Protection multi-niveaux** :
1. ✅ **CI sur PR** : Valide changement en isolation
2. ✅ **Run sur main** : Valide intégration finale
3. ✅ **Zero-tolerance** : Aucun échec toléré
4. ✅ **Artifacts** : Preuve archivée 30 jours

**Garantie** : Main reste **toujours** dans un état déployable validé.

---

## Exceptions Autorisées

**Seuls cas où la règle peut être relaxée** (à justifier explicitement) :

### 1. Documentation Pure (pas d'impact fonctionnel)
- Modification de `README.md`, `CHANGELOG.md`
- Typos dans commentaires
- Mise à jour documentation

**Justification** : Pas d'impact sur validation technique.

### 2. Urgence Production (Hotfix critique)
- Bug sécurité critique découvert en prod
- Rollback requis immédiatement

**Procédure d'urgence** :
1. Fix sur branche `hotfix/critical-X`
2. Run Release Gate sur branche hotfix
3. Merge avec `--no-ff` (garder historique)
4. Run Release Gate sur main **immédiatement après**
5. Si échec : rollback + re-fix

### 3. CI Indisponible (GitHub Actions down)
- GitHub Actions en panne globale
- Workflow bloqué par problème infra

**Procédure dégradée** :
1. Run Release Gate **en local** sur machine de confiance
2. Archiver logs locaux
3. Merge avec justification explicite dans commit message
4. Re-run CI dès rétablissement pour confirmer

---

## Gouvernance

### Responsable Release Gate
- **Propriétaire** : Shark (responsable technique)
- **Backup** : [À définir]

### Revue de Violation
Si cette règle est violée (merge sans run final) :
1. **Notification immédiate** (alerte Slack/email)
2. **Post-mortem** : Pourquoi la règle a été contournée
3. **Correction** : Rollback ou validation a posteriori
4. **Documentation** : Ajouter cas dans ce document si légitime

### Audit
- [ ] Review mensuel : Tous les merges Release Gate ont-ils un run associé ?
- [ ] Logs CI : Garder trace des runs (GitHub Actions garde 90 jours)

---

## Implémentation Technique (Optional Enforcement)

### GitHub Branch Protection (Recommandé)

```yaml
# .github/branch-protection.yml (GitHub API)
required_status_checks:
  strict: true
  contexts:
    - "Release Gate Validation (Zero-Tolerance)"

required_pull_request_reviews:
  required_approving_review_count: 1

enforce_admins: true
```

**Effet** : Impossible de merger sans CI green.

### Pre-Commit Hook (Optionnel, Local)

```bash
# .git/hooks/pre-push
#!/bin/bash

# Vérifier si modif Release Gate
if git diff --name-only HEAD origin/main | grep -qE "(release_gate|workflows/release-gate)"; then
  echo "⚠️  RELEASE GATE MODIFICATION DETECTED"
  echo "📋 Checklist:"
  echo "  [ ] CI run on feature branch: SUCCESS"
  echo "  [ ] After merge: Run 'gh workflow run release-gate.yml --ref main'"
  echo ""
  read -p "Confirmer que vous avez lu la règle (y/N): " confirm
  if [ "$confirm" != "y" ]; then
    echo "❌ Push annulé. Voir .github/RELEASE_GATE_INTEGRITY.md"
    exit 1
  fi
fi
```

**Note** : Hook local, non committé (chaque dev doit l'installer).

---

## Checklist Développeur

**Avant de toucher Release Gate** :
- [ ] J'ai lu ce document (`RELEASE_GATE_INTEGRITY.md`)
- [ ] Je comprends pourquoi cette règle existe
- [ ] J'ai créé une branche de feature
- [ ] J'ai testé localement avec `./scripts/release_gate_oneshot.sh`
- [ ] J'ai créé une PR et attendu CI green
- [ ] Après merge, je vais trigger workflow sur main
- [ ] Si échec post-merge, je rollback immédiatement

---

## Historique des Violations (Transparence)

| Date | Commit | Violation | Action | Résolution |
|------|--------|-----------|--------|------------|
| - | - | - | - | - |

*Pas de violation enregistrée à ce jour.*

---

## Révisions de ce Document

| Version | Date | Changements |
|---------|------|-------------|
| 1.0 | 2026-01-29 | Création initiale (post v1.0.0-rc1) |

---

**Règle Courte (à retenir)** :
> Modif Release Gate → PR + CI green → Merge → Run sur main → SUCCESS requis

**En cas de doute** : Demander review à Shark avant merge.

**Philosophie** : "Trust, but verify. Always."
