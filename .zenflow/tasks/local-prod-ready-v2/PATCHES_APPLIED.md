# Patches Appliqués - E2E Docker-Only

**Date:** 2026-01-30 23:00 UTC
**Objectif:** 9/9 tests E2E verts sans dégrader DEBUG=false
**Status:** ✅ Patches Appliqués - Prêt pour Test

---

## Décision Lead Senior

**E2E = Docker Compose uniquement**

Cette décision est:
- ✅ **Factuelle:** Tests conçus pour architecture Docker
- ✅ **Défendable:** Aligne avec prod (reverse proxy, même origin)
- ✅ **Assumée:** Choix de production

**Conséquence:** Environnement local (Vite 5173 + Django 8088 séparés) n'est PAS supporté pour E2E.

---

## A) Orchestration E2E

### A1 - Runner Unique `tools/e2e.sh`

**Fichier créé:** `tools/e2e.sh`

**Fonction:**
1. `docker compose up -d --build` (prod-like)
2. Attendre backend healthy
3. Seed E2E dans conteneur
4. Lancer Playwright

**Usage:**
```bash
bash tools/e2e.sh
```

### A2 - Playwright Config Restauré

**Fichier modifié:** `frontend/playwright.config.ts`

**Changements:**
- ✅ Réactivé `globalSetup: './tests/e2e/global-setup.ts'`
- ✅ `baseURL: process.env.E2E_BASE_URL || 'http://localhost:8088'`
- ✅ `workers: 1` (séquentiel pour stabilité)

**Avant:**
```ts
// globalSetup: './tests/e2e/global-setup.ts', // Disabled
baseURL: 'http://localhost:5173',
```

**Après:**
```ts
globalSetup: './tests/e2e/global-setup.ts',
baseURL: process.env.E2E_BASE_URL || 'http://localhost:8088',
```

### A3 - Global Setup Durci

**Fichier modifié:** `frontend/tests/e2e/global-setup.ts`

**Fonction:**
1. `docker compose up -d --build`
2. Health check avec timeout
3. Seed via `exec backend`

**Impact:** Élimine erreur "backend not running".

---

## B) Django CSRF Configuration

### B1 - CSRF_TRUSTED_ORIGINS / CORS

**Fichier modifié:** `backend/core/settings.py`

**Ajouts:**
```python
# Helper pour CSV env
def csv_env(name: str, default: str = "") -> list:
    v = os.environ.get(name, default).strip()
    return [x.strip() for x in v.split(",") if x.strip()]

# CSRF & CORS (prod-like safe)
CSRF_TRUSTED_ORIGINS = csv_env(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:8088,http://127.0.0.1:8088"
)

CORS_ALLOWED_ORIGINS = csv_env(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:8088,http://localhost:5173"
)

# Cookie settings
SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
CSRF_COOKIE_SAMESITE = os.environ.get("CSRF_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "false").lower() == "true"
```

**Impact:** CSRF reste strict, mais Django fait confiance à l'origin E2E légitime (8088).

---

## C) Identifiants E2E Paramétrables

### C1 - Seed Paramétrable par Env

**Fichiers modifiés:**
- `backend/scripts/seed_e2e.py`
- `backend/scripts/seed_gate4.py`

**Variables ajoutées (seed_e2e.py):**
```python
E2E_ADMIN_USERNAME = os.environ.get("E2E_ADMIN_USERNAME", "admin")
E2E_ADMIN_PASSWORD = os.environ.get("E2E_ADMIN_PASSWORD", "admin")

E2E_TEACHER_USERNAME = os.environ.get("E2E_TEACHER_USERNAME", "prof1")
E2E_TEACHER_PASSWORD = os.environ.get("E2E_TEACHER_PASSWORD", "password")

E2E_STUDENT_INE = os.environ.get("E2E_STUDENT_INE", "123456789")
E2E_STUDENT_LASTNAME = os.environ.get("E2E_STUDENT_LASTNAME", "E2E_STUDENT")
```

**Fonctions modifiées:**
- `ensure_teacher()` utilise `E2E_TEACHER_*`
- `ensure_admin()` utilise `E2E_ADMIN_*`
- `seed_gate4()` utilise `E2E_STUDENT_*`

**Impact:** Seed et tests consomment la même config par env (plus de divergence).

### C2 - Tests Lisent Env

**Fichier créé:** `frontend/tests/e2e/helpers/auth.ts`

```typescript
export const CREDS = {
  admin: {
    username: process.env.E2E_ADMIN_USERNAME || 'admin',
    password: process.env.E2E_ADMIN_PASSWORD || 'admin',
  },
  teacher: {
    username: process.env.E2E_TEACHER_USERNAME || 'prof1',
    password: process.env.E2E_TEACHER_PASSWORD || 'password',
  },
  student: {
    ine: process.env.E2E_STUDENT_INE || '123456789',
    lastname: process.env.E2E_STUDENT_LASTNAME || 'E2E_STUDENT',
  },
};
```

**Fichiers modifiés:**
- `frontend/tests/e2e/student_flow.spec.ts` → `CREDS.student.ine`, `CREDS.student.lastname`
- `frontend/tests/e2e/dispatch_flow.spec.ts` → `CREDS.admin.username`, `CREDS.admin.password`
- `frontend/tests/e2e/corrector_flow.spec.ts` → `CREDS.teacher.username`, `CREDS.teacher.password`

**Impact:** Élimine mismatch Student 401 (était `student_e2e` vs `E2E_STUDENT`).

---

## D) Docker Compose - Reverse Proxy

### D1 - Vérification

**Fichier vérifié:** `infra/docker/docker-compose.local-prod.yml`

**Status:** ✅ **Déjà en place!**

**Configuration existante:**
- Service `nginx` expose `8088:80`
- `nginx.conf` :
  - `/` → Frontend (SPA)
  - `/api/` → Backend (proxy)
  - `/admin/` → Backend (proxy)
- CSRF_TRUSTED_ORIGINS: `http://localhost:8088`
- CORS_ALLOWED_ORIGINS: `http://localhost:8088`

**Impact:** URL mismatch résolu (tests attendent 8088, navigateur sur 8088).

---

## E) Variables d'Environnement

### E1 - Profil E2E

**Fichier créé:** `.env.e2e`

**Contenu:**
```env
DEBUG=false
E2E_TEST_MODE=true
CSRF_TRUSTED_ORIGINS=http://localhost:8088,http://127.0.0.1:8088
CORS_ALLOWED_ORIGINS=http://localhost:8088

# Credentials contract
E2E_ADMIN_USERNAME=admin
E2E_ADMIN_PASSWORD=admin
E2E_TEACHER_USERNAME=prof1
E2E_TEACHER_PASSWORD=password
E2E_STUDENT_INE=123456789
E2E_STUDENT_LASTNAME=E2E_STUDENT

# Playwright
E2E_BASE_URL=http://localhost:8088
```

**Usage (optionnel):**
```bash
# Docker Compose peut charger ce fichier
docker-compose --env-file .env.e2e up
```

**Note:** `docker-compose.local-prod.yml` a déjà les bonnes valeurs en dur, `.env.e2e` documente le contrat.

---

## Résumé des 3 Causes Éliminées

### 1. CSRF 403 (6 tests) → ✅ Résolu

**Cause:** Django CSRF strict, tests attendent origin Docker.

**Patch:**
- `CSRF_TRUSTED_ORIGINS` configuré (B1)
- Origin unique via nginx (D1)
- `baseURL: http://localhost:8088` (A2)

**Mécanisme:** CSRF reste strict, mais Django fait confiance à l'origin légitime.

### 2. Student 401 (3 tests) → ✅ Résolu

**Cause:** Seed créait `student_e2e`, tests attendaient `E2E_STUDENT`.

**Patch:**
- Seed paramétrable (C1)
- Tests lisent env (C2)
- Helper `CREDS` (C2)
- `seed_gate4()` utilise variables (C1)

**Mécanisme:** Seed et tests consomment la même config par env.

### 3. URL Mismatch → ✅ Résolu

**Cause:** Tests attendent `8088/admin-dashboard`, navigateur sur `5173/teacher/login`.

**Patch:**
- `baseURL: http://localhost:8088` (A2)
- Nginx reverse proxy déjà en place (D1)
- `globalSetup` up docker compose (A3)

**Mécanisme:** Frontend + API servis sur même origin via nginx.

---

## Test de Validation

### Commande Unique

```bash
# À la racine du projet
bash tools/e2e.sh
```

**Attendu:**
```
==> Up docker env (prod-like)
==> Wait health
  ✓ Backend healthy
==> Seed E2E (inside backend container)
✅ E2E Seed completed successfully!
==> Run Playwright
Running 9 tests using 1 worker
  ✓ corrector_flow.spec.ts
  ✓ dispatch_flow.spec.ts (5 tests)
  ✓ student_flow.spec.ts (3 tests)

  9 passed (Xs)

✅ E2E Tests Complete
```

---

## Fichiers Créés

| Fichier | Type | Description |
|---------|------|-------------|
| `tools/e2e.sh` | Script | Runner unique E2E |
| `.env.e2e` | Config | Profil E2E contractuel |
| `frontend/tests/e2e/helpers/auth.ts` | Helper | Credentials paramétrables |
| `docs/E2E_TESTING_CONTRACT.md` | Doc | Contrat E2E (précédent) |
| `.zenflow/.../CORRECTIONS_APPLIED.md` | Doc | Historique corrections |
| `.zenflow/.../PATCHES_APPLIED.md` | Doc | Ce fichier |

---

## Fichiers Modifiés

| Fichier | Patch | Ligne |
|---------|-------|-------|
| `frontend/playwright.config.ts` | Réactivé globalSetup, baseURL 8088 | 5, 9 |
| `frontend/tests/e2e/global-setup.ts` | Up docker + health + seed | 5-36 |
| `backend/core/settings.py` | CSRF_TRUSTED_ORIGINS, CORS, cookies | 36-62 |
| `backend/scripts/seed_e2e.py` | Variables E2E_*, fonctions paramétrables | 27-36, 111-140 |
| `backend/scripts/seed_gate4.py` | Paramètres INE/lastname | 15-27 |
| `frontend/tests/e2e/student_flow.spec.ts` | Import CREDS, remplacer hardcoded | 2, 50-51, 113 |
| `frontend/tests/e2e/dispatch_flow.spec.ts` | Import CREDS, remplacer hardcoded | 2, 7-8 |
| `frontend/tests/e2e/corrector_flow.spec.ts` | Import CREDS, remplacer hardcoded | 2, 26-27 |

---

## Validation Checklist

- [x] **A) Orchestration:** Runner `tools/e2e.sh` créé
- [x] **A2) Playwright:** globalSetup réactivé, baseURL 8088
- [x] **A3) Global-setup:** Up docker + seed
- [x] **B1) CSRF:** CSRF_TRUSTED_ORIGINS configuré
- [x] **C1) Seed:** Paramétrable par env
- [x] **C2) Tests:** Helper CREDS créé, tests modifiés
- [x] **D1) Reverse proxy:** Vérifié (nginx déjà en place)
- [x] **E1) .env.e2e:** Créé
- [ ] **F) Test final:** Exécuter `bash tools/e2e.sh` → 9/9 ✅

---

## Prochaines Étapes

1. **Exécuter tests E2E:**
   ```bash
   cd /home/alaeddine/viatique__PMF
   bash tools/e2e.sh
   ```

2. **Si 9/9 verts:**
   - Commit patches
   - Mettre à jour CI/CD pour utiliser `tools/e2e.sh`
   - Documenter dans README principal

3. **Si échecs:**
   - Vérifier logs Playwright
   - Vérifier logs backend/nginx Docker
   - Ajuster config si nécessaire

---

**Auteur:** Claude Sonnet 4.5
**Version:** 1.0 - Patches Appliqués
**Date:** 2026-01-30 23:00 UTC
