# Porte 6O — Déploiement direct profile guards + fix /admin

**Date** : 2026-06-24
**Opérateur** : Claude Code
**Branche** : `hotfix/lot0-rgpd-deploy-clean`
**Commit source** : `ac5487c20bda9b771fe01f6e694d680a7eb5f11c`

## 1. Corrections déployées

### Route guards profil-spécifiques (from Porte 6N)

Fonction `getLoginForRoute(to)` dans `frontend/src/router/index.js` :
- `/student/*` → `/student/login`
- `/corrector/*`, `/teacher/*` → `/teacher/login`
- `/admin/*`, `/direction/*` → `/admin/login`

### Fix `/admin` nginx (Porte 6O)

Ajout dans `infra/nginx/nginx.conf` :
```nginx
location = /admin {
    return 302 /admin/login;
}
```

**Avant** : `/admin` → 301 → `/admin/` → Django proxy → 404
**Après** : `/admin` → 302 → `/admin/login` → SPA login form

## 2. Build nginx

- Image : `korrigo-nginx:korrigo-direct-ac5487c`
- SHA : `ac5487c20bda9b771fe01f6e694d680a7eb5f11c`
- Labels OCI : `source=direct-local-korrigo-porte6o-profile-guards`
- PII gate : `PASS`, `PII_HASH_MATCH_COUNT=0`

## 3. Déploiement

- Commande : `docker compose ... up -d --no-deps nginx`
- Override temporaire : `docker-compose.porte6o.override.yml`

### Services

| Service | Image | Modified |
|---------|-------|----------|
| nginx | `korrigo-nginx:korrigo-direct-ac5487c` | YES |
| backend | `korrigo-backend:korrigo-direct-c38a586` | NO |
| celery | `korrigo-backend:korrigo-direct-c38a586` | NO |
| celery-beat | `korrigo-backend:korrigo-direct-c38a586` | NO |
| db | `postgres:15-alpine` | NO |
| redis | `redis:7-alpine` | NO |

## 4. Production verification

### HTTP routes

| URL | Before | After |
|-----|--------|-------|
| `/admin` | 301→404 | **302→/admin/login** |
| `/admin/` | 404 | 404 (Django, expected) |
| `/admin/login` | 200 | 200 |
| `/admin/dashboard` | 200 | 200 |
| `/teacher/login` | 200 | 200 |
| `/student/login` | 200 | 200 |

### Playwright production (12/12 PASS)

| Category | Route | Redirect | Result |
|----------|-------|----------|--------|
| public | `/korrigo` | — | H1=1 ✅ |
| public | `/korrigo/guide-enseignant` | — | H1=1 ✅ |
| public | `/korrigo/guide-eleve` | — | H1=1 ✅ |
| public | `/korrigo/direction` | — | H1=1 ✅ |
| login | `/teacher/login` | — | Form=1 ✅ |
| login | `/student/login` | — | Form=1 ✅ |
| login | `/admin/login` | — | Form=1 ✅ |
| guard | `/corrector-dashboard` | → `/teacher/login` | ✅ |
| guard | `/student/dashboard` | → `/student/login` | ✅ |
| guard | `/admin/dashboard` | → `/admin/login` | ✅ |
| guard | `/direction/dashboard` | → `/admin/login` | ✅ |
| admin | `/admin` | → `/admin/login` | ✅ |

0 emails, 0 forbidden, 0 console errors, 0 network errors.

## 5. Compose reconciliation

| File | nginx image |
|------|-------------|
| Server `docker-compose.prod.yml` | `korrigo-direct-ac5487c` |
| Local `docker-compose.prod.yml` | `korrigo-direct-ac5487c` |
| `local_release_check.sh` | `korrigo-direct-ac5487c` |
| `test_prod_compose_contract.py` | `korrigo-direct-ac5487c` |

## 6. Pipeline post-déploiement

- `LOCAL_RELEASE_CHECK_STATUS=PASS`
- `E2E_STATUS=PASS_EXISTING_PLAYWRIGHT_OR_CYPRESS`

## Verdict

**`PROFILE_GUARDS_DEPLOYED_AND_VERIFIED`**

## Confirmations

- Aucun GitHub
- Aucun push
- Aucun backend rebuild
- Aucune DB/Redis touchée
- Aucune migration
- Aucun `docker compose down`
- Aucun prune
- Aucune suppression
- Aucune PII visible
