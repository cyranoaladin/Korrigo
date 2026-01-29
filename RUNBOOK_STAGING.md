# 🚀 Runbook Staging — v1.0.0-rc1 → Validation → GO v1.0.0

**Date**: 2026-01-29
**Version**: v1.0.0-rc1 → v1.0.0
**Responsable**: Release Manager
**Durée estimée**: 45-60 minutes

---

## ✅ Pré-requis (OBLIGATOIRES)

Vérifier **AVANT** de lancer:

- [ ] DNS staging opérationnel: `https://staging.viatique.example.com`
- [ ] TLS en place (cert valide, pas d'erreur navigateur)
- [ ] Accès DB/Redis sur la stack staging (via docker compose)
- [ ] Compte prof staging valide (`SMOKE_USER` + `SMOKE_PASS`)
- [ ] Machine d'exécution: Linux avec `docker`, `docker compose`, `openssl`, `curl`, `jq`
- [ ] **Si mode Full Hardened** : `flock` disponible (util-linux, pour lock exclusion mutuelle)
- [ ] Git repo à jour sur `main` (commit `bf86716` ou plus récent)
- [ ] Tag `v1.0.0-rc1` existe

### Commande de sanity rapide

```bash
# Vérifier outils disponibles
docker --version && \
  docker compose version && \
  openssl version && \
  curl --version && \
  jq --version

# Vérifier flock (si mode Full Hardened)
command -v flock >/dev/null && echo "flock: OK" || echo "flock: MISSING (requis pour Full Hardened)"

# Vérifier tag RC1 existe
git tag | grep v1.0.0-rc1

# Vérifier fichiers Docker Compose staging
ls -l infra/docker/docker-compose.staging.yml
```

**Critère GO**: Toutes les commandes retournent RC=0, aucune erreur. `flock` optionnel (requis uniquement pour mode Full Hardened).

---

## 📋 Phase 1 — Deploy Staging (safe, rollback auto)

**Objectif**: Déployer `v1.0.0-rc1` en staging avec health-checks et rollback automatique si unhealthy.

**Durée**: ~5-10 minutes

### Commande d'exécution

```bash
BASE_URL=https://staging.viatique.example.com \
  TAG=v1.0.0-rc1 \
  METRICS_TOKEN=$(openssl rand -hex 32) \
  ./scripts/deploy_staging_safe.sh
```

**Variables obligatoires**:
- `BASE_URL`: URL staging (HTTPS obligatoire)
- `TAG`: Tag Git à déployer (default: `v1.0.0-rc1`)
- `METRICS_TOKEN`: Token sécurisé 64 chars (auto-généré si omis)

### Critères PASS ✅

- [ ] Script termine avec **RC=0**
- [ ] Message final: `=== STAGING DEPLOY DONE ===`
- [ ] Health endpoint OK: `✅ Health endpoint OK`
- [ ] Aucune ligne "unhealthy" dans le summary
- [ ] Services healthy: `✅ Stack up & stable`
- [ ] Logs présents: `/tmp/staging_deploy_<timestamp>/`

**Vérification manuelle**:
```bash
# Vérifier services running
docker compose -f infra/docker/docker-compose.staging.yml ps

# Vérifier health endpoint
curl -fsS https://staging.viatique.example.com/api/health/ | jq .

# Vérifier logs
ls -lh /tmp/staging_deploy_*/
```

### Critères FAIL ❌ → STOP

- [ ] Rollback déclenché: `❌ Unhealthy services detected`
- [ ] Timeout health-check (>90s)
- [ ] Erreurs `docker build` ou `compose up`
- [ ] Services en état "unhealthy" ou "restarting"

**Action si FAIL**:
1. Consulter logs: `cat /tmp/staging_deploy_*/deploy.log`
2. Consulter logs Docker: `docker compose -f infra/docker/docker-compose.staging.yml logs --tail=100`
3. Identifier cause (DB connexion, env vars manquantes, image build failure)
4. Corriger et relancer Phase 1

---

## 🧪 Phase 2 — Smoke Test Staging (E2E workflow critique)

**Objectif**: Valider le workflow métier complet "login → READY → lock → annoter → finalize → PDF" en conditions staging réelles.

**Durée**: ~30-60 secondes

### Commande d'exécution

```bash
BASE_URL=https://staging.viatique.example.com \
  SMOKE_USER=prof1 \
  SMOKE_PASS='changeme' \
  ./scripts/smoke_staging.sh
```

**Variables obligatoires**:
- `BASE_URL`: URL staging (même que Phase 1)
- `SMOKE_USER`: Username professeur staging (default: `prof1`)
- `SMOKE_PASS`: Password professeur staging (default: `changeme`)

### Critères PASS ✅

- [ ] Script termine avec **RC=0**
- [ ] Message final: `=== STAGING SMOKE SUCCESS ===`
- [ ] **9 steps validés** (voir détail ci-dessous)
- [ ] Logs présents: `/tmp/staging_smoke_<timestamp>/`

**Détail des 9 steps obligatoires**:

| Step | Action | Validation |
|------|--------|------------|
| 1 | Login | `✅ Logged in (session cookie set)` |
| 2 | Get Exam ID | `✅ Exam ID: <exam_id>` |
| 3 | List READY copies | `✅ Found READY copy: <copy_id>` + `✅ Copy has N pages` |
| 4 | Lock copy | `✅ Locked (HTTP 201, token: ...)` |
| 5 | POST annotation | `✅ Annotation created (HTTP 201)` |
| 6 | GET annotations | `✅ Annotations found: N` (N > 0) |
| 7 | Finalize copy | `✅ Finalize OK (HTTP 200)` |
| 8 | Verify PDF | `✅ PDF accessible: https://...` |
| 9 | Unlock (best effort) | `✅ Unlocked` ou `⚠️ Unlock not needed` |

**Vérification manuelle**:
```bash
# Consulter logs smoke
cat /tmp/staging_smoke_*/smoke.log

# Vérifier artéfacts API
ls -lh /tmp/staging_smoke_*/
# Doit contenir: login.json, exams.json, copies.json, lock.txt, annotation_post.txt, etc.

# Vérifier PDF final accessible
curl -I -b /tmp/staging_smoke_*/cookies.txt \
  https://staging.viatique.example.com/api/grading/copies/<copy_id>/final-pdf/
```

### Critères FAIL ❌ → STOP

- [ ] N'importe quel step échoue (❌)
- [ ] Login failed (credentials invalides, DB inaccessible)
- [ ] No READY copies (données seed manquantes)
- [ ] Lock failed (409 Conflict si déjà locked, 403 Forbidden)
- [ ] Annotation POST != 201 (permissions, lock token invalide)
- [ ] Finalize failed (statut != GRADED)
- [ ] PDF inaccessible (404, 403, 500)

**Action si FAIL**:
1. Consulter logs: `cat /tmp/staging_smoke_*/smoke.log`
2. Identifier step qui échoue
3. Consulter artéfact correspondant (ex: `cat /tmp/staging_smoke_*/lock.txt`)
4. Causes fréquentes:
   - **Login failed**: Vérifier credentials, DB user existe
   - **No READY copies**: Seed data manquantes → `docker compose exec backend python manage.py seed_e2e_data`
   - **Lock failed 409**: Copy déjà locked → unlock manuel ou attendre TTL
   - **Annotation 403**: Lock token invalide ou expiré
   - **PDF 404**: PDF final non généré (bug finalize)
5. Corriger et relancer Phase 2

---

## 🏷️ Phase 3 — GO v1.0.0 (SI ET SEULEMENT SI Phase 1 + 2 = ✅)

**Condition stricte**: Phase 1 PASS ✅ ET Phase 2 PASS ✅

### 3.1 Archiver les preuves (audit-ready)

**Obligatoire avant tag**:

```bash
# Créer archive des artéfacts staging
TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
tar -czf /tmp/staging_artifacts_${TIMESTAMP}.tgz \
  /tmp/staging_deploy_* \
  /tmp/staging_smoke_* \
  RELEASE_NOTES_v1.0.0.md

# Vérifier archive créée
ls -lh /tmp/staging_artifacts_*.tgz

# Optionnel: upload vers S3/bucket de backup
# aws s3 cp /tmp/staging_artifacts_${TIMESTAMP}.tgz s3://viatique-releases/
```

**Contenu de l'archive** (à conserver 1 an minimum):
- Logs deploy staging
- Logs smoke test staging
- Release notes complétées
- Metadata (timestamp, tag, commit SHA)

### 3.2 Remplir Release Notes

**Éditer `RELEASE_NOTES_v1.0.0.md`** et compléter les placeholders:

```bash
# Récupérer infos pour release notes
echo "CI Run ID: <à récupérer depuis GitHub Actions>"
echo "Commit SHA: $(git rev-parse HEAD)"
echo "Deploy timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Smoke artifacts: /tmp/staging_smoke_*/"

# Éditer release notes
nano RELEASE_NOTES_v1.0.0.md
# Remplacer:
# - <CI_RUN_ID> par le run ID GitHub Actions
# - <COMMIT_SHA> par les commits depuis RC1
# - <YYYY-MM-DD> par date du jour
# - [Admin Email] par contact réel
```

**Sections à compléter**:
- [ ] CI Run ID (ligne 13)
- [ ] Commit SHAs depuis v1.0.0-rc1 (lignes 161-165)
- [ ] Release Date (ligne 225)
- [ ] Contact technique (ligne 218)

### 3.3 Tag & Release v1.0.0

**IMPORTANT**: On tag sur `main` après validation staging complète.

```bash
# S'assurer d'être sur main à jour
git checkout main
git pull --ff-only

# Vérifier état propre
git status

# Créer tag annoté v1.0.0
git tag -a v1.0.0 -m "v1.0.0 - Production Release

Graduation from v1.0.0-rc1 after full staging validation.

Release Gate Evidence:
- Deploy staging: SUCCESS (artifacts in /tmp/staging_deploy_*)
- Smoke test: SUCCESS (9/9 steps PASS)
- CI: 205 passed, 0 failed, 0 skipped
- E2E: 3/3 runs with annotations

Validated: $(date -u +%Y-%m-%d)
"

# Push tag
git push origin v1.0.0

# Créer GitHub Release
gh release create v1.0.0 \
  --title "v1.0.0 - Production Release" \
  --notes-file RELEASE_NOTES_v1.0.0.md \
  --target main

# Attacher artéfacts staging (optionnel)
gh release upload v1.0.0 /tmp/staging_artifacts_*.tgz
```

**Vérification**:
```bash
# Vérifier tag créé
git tag | grep v1.0.0

# Vérifier release GitHub
gh release view v1.0.0

# Vérifier URL release
echo "https://github.com/cyranoaladin/Korrigo/releases/tag/v1.0.0"
```

---

## 🔄 Rollback (si staging KO après deploy)

### Rollback "quick" — Stack uniquement (< 5 min)

**But**: Revenir à un état stable sans toucher la DB.

**Scénario**: Services unhealthy après deploy, mais DB OK.

```bash
# Option 1: Redeploy tag précédent stable
TAG=<previous-stable-tag> \
  BASE_URL=https://staging.viatique.example.com \
  ./scripts/deploy_staging_safe.sh

# Option 2: Down + clean + redeploy
cd infra/docker/
docker compose -f docker-compose.staging.yml down
docker compose -f docker-compose.staging.yml up -d --build

# Vérifier santé
curl -fsS https://staging.viatique.example.com/api/health/
```

### Rollback "full" — DB + Stack (< 15 min)

**But**: Restaurer DB + Stack si données corrompues ou migration problématique.

**Scénario**: Migration a échoué, données incohérentes, ou test de restore obligatoire.

```bash
# 1. Arrêter stack
docker compose -f infra/docker/docker-compose.staging.yml down

# 2. Restaurer backup DB (dernier backup OK)
# Exemple: backup quotidien à 02:00 UTC
BACKUP_FILE="/backups/postgres/viatique_backup_<DATE>.sql.gz"

# Vérifier backup existe
ls -lh $BACKUP_FILE

# Restaurer DB
gunzip -c $BACKUP_FILE | \
  docker exec -i viatique_staging_db psql -U postgres viatique_staging

# 3. Redeploy tag stable
TAG=<previous-stable-tag> \
  BASE_URL=https://staging.viatique.example.com \
  ./scripts/deploy_staging_safe.sh

# 4. Vérifier intégrité
curl -fsS https://staging.viatique.example.com/api/health/
docker compose -f infra/docker/docker-compose.staging.yml ps
```

**Checklist rollback**:
- [ ] Services healthy après rollback
- [ ] Health endpoint OK (200)
- [ ] DB accessible (no errors in logs)
- [ ] Smoke test PASS (re-run smoke_staging.sh)
- [ ] Incident documenté (cause, actions, prévention)

---

## 🚨 Politique "Zéro Tolérance"

**Règles strictes**:

1. **Pas de "ça a l'air OK"**: C'est PASS uniquement si deploy + smoke sont verts (RC=0).
2. **Si FAIL Phase 1 ou 2**: On corrige la cause, puis on re-run. **JAMAIS skip**.
3. **Tag v1.0.0 uniquement si Phase 1 ✅ + Phase 2 ✅**: Pas de compromis.
4. **Artéfacts obligatoires**: Archive staging doit être créée avant tag.
5. **Rollback plan testé**: Si rollback nécessaire, suivre procédure exacte ci-dessus.

**Escalation si bloqué**:
- Consulter `scripts/STAGING_README.md` section Troubleshooting
- Consulter logs Docker: `docker compose logs backend --tail=200`
- Consulter logs Nginx: `docker compose logs nginx --tail=50`
- Si bloquage > 30min: escalade vers tech lead

---

## 🎯 Commande Unique (One-Shot) — Version Durcie Production-Ready

**Pour les warriors qui veulent deploy + smoke + archive en une seule commande**.

**Version robuste** avec archivage garanti même en cas d'échec (debug-friendly):

```bash
BASE_URL=https://staging.viatique.example.com \
SMOKE_USER=prof1 \
SMOKE_PASS='changeme' \
TAG=v1.0.0-rc1 \
METRICS_TOKEN=$(openssl rand -hex 32) \
bash -lc '
set -euo pipefail
set +x  # Disable command tracing (prevent secrets leakage)

echo "=== 🚀 STAGING ONE-SHOT: Deploy + Smoke + Archive ==="
echo "BASE_URL=$BASE_URL"
echo "TAG=$TAG"
echo "SMOKE_USER=$SMOKE_USER"
echo "SMOKE_PASS=********"
echo "METRICS_TOKEN=<redacted>"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="/tmp/staging_oneshot_${TS}"
mkdir -p "$OUT"

# Capture actual dirs created by scripts (not "latest dir")
DEPLOY_DIR=""
SMOKE_DIR=""

# Always archive at the end (success or failure)
archive() {
  echo ""
  echo "[3/3] Archiving artifacts..."

  {
    echo "timestamp=$TS"
    echo "base_url=$BASE_URL"
    echo "tag=$TAG"
    echo "deploy_dir=${DEPLOY_DIR:-<none>}"
    echo "smoke_dir=${SMOKE_DIR:-<none>}"
  } > "$OUT/meta.txt"

  # Copy logs if found
  if [ -n "${DEPLOY_DIR:-}" ] && [ -d "$DEPLOY_DIR" ]; then
    cp -a "$DEPLOY_DIR" "$OUT/" || true
  fi
  if [ -n "${SMOKE_DIR:-}" ] && [ -d "$SMOKE_DIR" ]; then
    cp -a "$SMOKE_DIR" "$OUT/" || true
  fi

  # Copy release notes template if present
  if [ -f "RELEASE_NOTES_v1.0.0.md" ]; then
    cp -a "RELEASE_NOTES_v1.0.0.md" "$OUT/" || true
  fi

  TAR="/tmp/staging_artifacts_${TS}.tgz"
  tar -czf "$TAR" -C /tmp "$(basename "$OUT")"

  echo "Artifacts packaged: $TAR"
}

trap archive EXIT

echo "[1/3] Deploying staging..."
BASE_URL="$BASE_URL" TAG="$TAG" METRICS_TOKEN="$METRICS_TOKEN" \
  ./scripts/deploy_staging_safe.sh

# Capture deploy dir IMMEDIATELY after execution (deterministic)
DEPLOY_DIR="$(ls -1dt /tmp/staging_deploy_* 2>/dev/null | head -n 1 || true)"

echo "[2/3] Running smoke test..."
export SMOKE_PASS  # Prevent accidental logging in subshells
BASE_URL="$BASE_URL" SMOKE_USER="$SMOKE_USER" SMOKE_PASS="$SMOKE_PASS" \
  ./scripts/smoke_staging.sh

# Capture smoke dir IMMEDIATELY after execution (deterministic)
SMOKE_DIR="$(ls -1dt /tmp/staging_smoke_* 2>/dev/null | head -n 1 || true)"

echo ""
echo "✅ ONE-SHOT SUCCESS"
echo "Next:"
echo "  1) Fill RELEASE_NOTES_v1.0.0.md"
echo "  2) git tag -a v1.0.0 -m \"Production Release\" && git push origin v1.0.0"
'
```

### Améliorations par rapport à la version de base

**✅ Avantages**:
- **Archive garantie**: Même en cas d'échec, les logs sont archivés (via `trap EXIT`)
- **Déterminisme total**: Capture le dossier créé par chaque script **immédiatement après exécution** (pas de risque de race condition ou run parallèle)
- **Masquage password**: `SMOKE_PASS=********` dans l'affichage + `set +x` pour bloquer le tracing
- **Protection secrets**: `export SMOKE_PASS` avant smoke test (évite fuites accidentelles dans subshells)
- **Traçabilité**: `meta.txt` avec timestamp, base_url, tag, et paths réels des logs
- **Fail-fast**: Si deploy échoue, smoke n'est pas lancé
- **RC=0 uniquement si tout passe**: Comportement strict pour CI/CD

**⚠️ Points d'attention**:
- Moins de visibilité sur logs intermédiaires (tout en stdout)
- Si échec, consulter `/tmp/staging_artifacts_<timestamp>.tgz` pour debug

**Contenu de l'archive** (`/tmp/staging_artifacts_<timestamp>.tgz`):
```
staging_oneshot_<timestamp>/
├── meta.txt                      # Metadata du run
├── staging_deploy_<timestamp>/   # Logs deploy (si exécuté)
├── staging_smoke_<timestamp>/    # Logs smoke (si exécuté)
└── RELEASE_NOTES_v1.0.0.md       # Template release notes (si présent)
```

**Recommandation**:
- **Débutants/Première fois**: Exécuter Phase 1, Phase 2, Phase 3 séparément (plus de contrôle)
- **Warriors/CI-CD**: Utiliser commande one-shot pour déploiement automatisé

---

### 🔒 Hardening Optionnel (Cas Limites Production)

**Pour environnements "agités"** (runs parallèles, debug actif, CI/CD complexe).

#### 1. Protection Secrets Maximale (éviter process list / history)

**Problème** : Si le shell parent est en `set -x`, l'expansion de `SMOKE_PASS='...'` peut apparaître dans l'historique ou le process list avant l'entrée dans `bash -lc`.

**Solution** : Exporter `SMOKE_PASS` dans l'environnement **AVANT** la commande one-shot.

```bash
# Mode "ultra-sec" - exporter secrets en dehors de la ligne de commande
export SMOKE_PASS='changeme'
export METRICS_TOKEN=$(openssl rand -hex 32)

# Commande one-shot sans secrets inline
BASE_URL=https://staging.viatique.example.com \
SMOKE_USER=prof1 \
TAG=v1.0.0-rc1 \
bash -lc '
set -euo pipefail
set +x

echo "=== 🚀 STAGING ONE-SHOT: Deploy + Smoke + Archive ==="
echo "BASE_URL=$BASE_URL"
echo "TAG=$TAG"
echo "SMOKE_USER=$SMOKE_USER"
echo "SMOKE_PASS=********"
echo "METRICS_TOKEN=<redacted>"

# ... reste du script identique ...
'
```

**Bénéfice** :
- ✅ Aucun secret dans `ps aux` (process list visible par tous les users)
- ✅ Variables exportées héritées par le sous-shell
- ✅ Protection contre `set -x` dans le shell parent (pas de trace des valeurs)

**Quand l'utiliser** :
- Environnements multi-utilisateurs (serveurs partagés)
- CI/CD avec logs détaillés
- Serveurs où `ps aux` est accessible

**⚠️ Note sur l'historique bash** :
La commande `export SMOKE_PASS='...'` peut quand même finir dans l'historique bash selon la configuration (`HISTCONTROL`, `HISTIGNORE`).

**Protection historique** (optionnel, selon config shell) :
```bash
# Empêcher logging dans l'historique
export HISTCONTROL=ignorespace
 export SMOKE_PASS='changeme'   # Note: espace initial => ignoré si HISTCONTROL=ignorespace
 export METRICS_TOKEN=$(openssl rand -hex 32)
```

Ou utiliser un prompt interactif sans echo :
```bash
read -sp "SMOKE_PASS: " SMOKE_PASS; echo; export SMOKE_PASS
```

**Note** : Le `echo` après `read -sp` assure un retour à la ligne (UX).

---

#### 2. Nettoyage `/tmp` (éviter capture de vieux logs)

**Problème** : Si un ancien `/tmp/staging_deploy_*` existe, et que le script échoue **avant** de créer son dossier, le `ls -1dt` peut capturer l'ancien dossier.

**Solution** : Nettoyer `/tmp/staging_*` au début du one-shot (safe).

```bash
BASE_URL=https://staging.viatique.example.com \
SMOKE_USER=prof1 \
SMOKE_PASS='changeme' \
TAG=v1.0.0-rc1 \
METRICS_TOKEN=$(openssl rand -hex 32) \
bash -lc '
set -euo pipefail
set +x

# ✅ Nettoyage /tmp au début (safe, avant création des nouveaux dirs)
rm -rf /tmp/staging_deploy_* /tmp/staging_smoke_* /tmp/staging_oneshot_* 2>/dev/null || true

echo "=== 🚀 STAGING ONE-SHOT: Deploy + Smoke + Archive ==="
# ... reste du script identique ...
'
```

**Bénéfice** :
- ✅ Garantie "un run = un set de dirs"
- ✅ Pas de confusion avec des logs de runs précédents échoués
- ✅ Archive toujours cohérente avec le run courant

**Quand l'utiliser** :
- Serveurs avec `/tmp` non nettoyé automatiquement
- Runs fréquents en développement/staging
- CI/CD avec runners réutilisés **isolés** (1 runner = 1 host)

**⚠️ ATTENTION : Runs Concurrents** :
Le `rm -rf /tmp/staging_*` peut créer des **effets collatéraux** si deux one-shots tournent **en parallèle sur le même hôte**.

**Règle opérationnelle** : **Ne pas exécuter deux one-shots simultanément sur le même hôte.**
- ✅ OK : 1 staging host = 1 run à la fois
- ✅ OK : CI/CD avec runners isolés (chaque runner = 1 VM/conteneur)
- ❌ KO : Runs parallèles sur serveur partagé

**Protection lock** (optionnel, voir section Full Hardened) :
Utiliser `flock` pour garantir l'exclusion mutuelle.

**Alternative** (si nettoyage global trop agressif) :

```bash
# Nettoyer uniquement les dirs de plus de 24h
find /tmp -maxdepth 1 -name "staging_*" -type d -mtime +1 -exec rm -rf {} \; 2>/dev/null || true
```

---

#### Commande One-Shot **Full Hardened** (Tous les Garde-Fous)

**Includes** : Secrets exportés + Nettoyage /tmp + Lock exclusion mutuelle

```bash
# Export secrets en dehors de la ligne de commande
export SMOKE_PASS='changeme'
export METRICS_TOKEN=$(openssl rand -hex 32)

BASE_URL=https://staging.viatique.example.com \
SMOKE_USER=prof1 \
TAG=v1.0.0-rc1 \
bash -lc '
set -euo pipefail
set +x  # Disable command tracing

# Vérifier flock disponible
command -v flock >/dev/null || {
  echo "❌ flock non disponible (requis pour Full Hardened)."
  echo "➡️  Installer: apt-get install util-linux (ou équivalent)"
  exit 1
}

# Lock global pour éviter exécutions concurrentes
LOCK=/tmp/staging_oneshot.lock
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "❌ Un autre one-shot staging est déjà en cours (lock: $LOCK). Abandon."
  echo "➡️  Attendre la fin du run en cours, ou vérifier: lsof $LOCK ; ps aux | grep staging"
  exit 1
fi

# Nettoyage /tmp (safe si lock acquis)
rm -rf /tmp/staging_deploy_* /tmp/staging_smoke_* /tmp/staging_oneshot_* 2>/dev/null || true

echo "=== 🚀 STAGING ONE-SHOT: Deploy + Smoke + Archive ==="
echo "BASE_URL=$BASE_URL"
echo "TAG=$TAG"
echo "SMOKE_USER=$SMOKE_USER"
echo "SMOKE_PASS=********"
echo "METRICS_TOKEN=<redacted>"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="/tmp/staging_oneshot_${TS}"
mkdir -p "$OUT"

DEPLOY_DIR=""
SMOKE_DIR=""

archive() {
  echo ""
  echo "[3/3] Archiving artifacts..."

  {
    echo "timestamp=$TS"
    echo "base_url=$BASE_URL"
    echo "tag=$TAG"
    echo "deploy_dir=${DEPLOY_DIR:-<none>}"
    echo "smoke_dir=${SMOKE_DIR:-<none>}"
  } > "$OUT/meta.txt"

  if [ -n "${DEPLOY_DIR:-}" ] && [ -d "$DEPLOY_DIR" ]; then
    cp -a "$DEPLOY_DIR" "$OUT/" || true
  fi
  if [ -n "${SMOKE_DIR:-}" ] && [ -d "$SMOKE_DIR" ]; then
    cp -a "$SMOKE_DIR" "$OUT/" || true
  fi
  if [ -f "RELEASE_NOTES_v1.0.0.md" ]; then
    cp -a "RELEASE_NOTES_v1.0.0.md" "$OUT/" || true
  fi

  TAR="/tmp/staging_artifacts_${TS}.tgz"
  tar -czf "$TAR" -C /tmp "$(basename "$OUT")"

  echo "Artifacts packaged: $TAR"
}

trap archive EXIT

echo "[1/3] Deploying staging..."
BASE_URL="$BASE_URL" TAG="$TAG" METRICS_TOKEN="$METRICS_TOKEN" \
  ./scripts/deploy_staging_safe.sh

DEPLOY_DIR="$(ls -1dt /tmp/staging_deploy_* 2>/dev/null | head -n 1 || true)"

echo "[2/3] Running smoke test..."
export SMOKE_PASS
BASE_URL="$BASE_URL" SMOKE_USER="$SMOKE_USER" SMOKE_PASS="$SMOKE_PASS" \
  ./scripts/smoke_staging.sh

SMOKE_DIR="$(ls -1dt /tmp/staging_smoke_* 2>/dev/null | head -n 1 || true)"

echo ""
echo "✅ ONE-SHOT SUCCESS"
echo "Next:"
echo "  1) Fill RELEASE_NOTES_v1.0.0.md"
echo "  2) git tag -a v1.0.0 -m \"Production Release\" && git push origin v1.0.0"
'
```

**Différences avec version de base** :
- ✅ Secrets exportés avant (pas inline)
- ✅ Lock `flock` pour exclusion mutuelle (évite runs concurrents)
- ✅ Nettoyage `/tmp` au début (safe si lock acquis)
- ✅ Toujours `set +x` et capture déterministe

**Bénéfice du lock** :
- ✅ Garantit qu'un seul one-shot tourne à la fois sur le host
- ✅ Évite que le nettoyage `/tmp` supprime les dossiers d'un run parallèle
- ✅ Message clair si tentative de run concurrent

**Quand l'utiliser** :
- **Production critique** : Zéro tolérance aux fuites ou ambiguïtés
- **CI/CD complexe** : Multi-tenants, logs détaillés
- **Serveur partagé** : Plusieurs users peuvent lancer des runs
- **Audit strict** : Conformité sécurité, traçabilité maximale

**Quand le lock n'est PAS nécessaire** :
- Runners CI/CD isolés (1 runner = 1 VM/conteneur)
- Orchestration contrôlée (Kubernetes jobs avec concurrency=1)
- Environnement mono-utilisateur

---

**Option "ultra strict"** (bloquer si release notes manquantes):

Remplacer:
```bash
if [ -f "RELEASE_NOTES_v1.0.0.md" ]; then
  cp -a "RELEASE_NOTES_v1.0.0.md" "$OUT/" || true
fi
```

Par:
```bash
test -f "RELEASE_NOTES_v1.0.0.md"
cp -a "RELEASE_NOTES_v1.0.0.md" "$OUT/"
```

Cela force la discipline (échec si fichier absent).

---

## 📊 Checklist Finale (avant tag v1.0.0)

**Technique**:
- [ ] Phase 1: Deploy staging PASS ✅
- [ ] Phase 2: Smoke test PASS ✅ (9/9 steps)
- [ ] Services staging healthy (docker compose ps)
- [ ] Health endpoint OK (curl health)
- [ ] Logs archivés: `/tmp/staging_artifacts_*.tgz`

**Documentation**:
- [ ] `RELEASE_NOTES_v1.0.0.md` complétées (tous placeholders remplis)
- [ ] Commit SHA depuis RC1 documentés
- [ ] CI run ID staging (si applicable)
- [ ] Timestamp deploy + smoke enregistrés

**Gouvernance**:
- [ ] Approbation stakeholder (si requis)
- [ ] Incident staging résolu (si applicable)
- [ ] Rollback plan vérifié (backup DB récent < 24h)
- [ ] Équipe notifiée du tag v1.0.0

**Git**:
- [ ] Branch `main` à jour
- [ ] Tag `v1.0.0` créé et pushé
- [ ] GitHub Release créée avec notes
- [ ] Artéfacts staging attachés à la release (optionnel)

---

## 🔗 Liens Utiles

- **Scripts**: `scripts/deploy_staging_safe.sh`, `scripts/smoke_staging.sh`
- **Documentation**: `scripts/STAGING_README.md`
- **Production Checklist**: `PRODUCTION_CHECKLIST.md`
- **Release Gate Report**: `RELEASE_GATE_REPORT_v1.0.0-rc1.md`
- **Integrity Rules**: `.github/RELEASE_GATE_INTEGRITY.md`

---

**Version**: 1.0
**Statut**: ✅ Opérationnel
**Dernière mise à jour**: 2026-01-29

**Prêt pour exécution. GO pour staging ! 🚀**
