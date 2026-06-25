# Porte 6N — Audit fonctionnel, UX, route guards et cohérence profils

**Date** : 2026-06-24
**Opérateur** : Claude Code
**Branche** : `hotfix/lot0-rgpd-deploy-clean`

## 1. Contexte

Porte 6M a validé l'infrastructure globale mais identifié des faiblesses UX :
- Routes protégées redirigent vers `/` (portail générique) au lieu de la page login du profil
- `/admin` (sans trailing slash) retourne 404 en production
- Flows authentifiés non testés avec comptes réels

## 2. Diagnostic route guards

### Avant correction

| Route protégée non auth | Redirection |
|-------------------------|-------------|
| `/teacher/dashboard` | `/` (portail) |
| `/student/dashboard` | `/` (portail) |
| `/admin/dashboard` | `/` (portail) |
| `/direction/dashboard` | `/` (portail) |
| `/corrector/desk/:id` | `/` (portail) |

UX faible : l'utilisateur atterrit sur le portail générique sans contexte.

### Après correction

| Route protégée non auth | Redirection |
|-------------------------|-------------|
| `/teacher/dashboard` | `/teacher/login` |
| `/student/dashboard` | `/student/login` |
| `/admin/dashboard` | `/admin/login` |
| `/direction/dashboard` | `/admin/login` |
| `/corrector/desk/:id` | `/teacher/login` |

UX améliorée : l'utilisateur est dirigé vers la page login de son profil.

### Fonction `getLoginForRoute(to)`

Ajoutée dans `frontend/src/router/index.js` :
- `/student/*` → `/student/login`
- `/corrector/*`, `/teacher/*` → `/teacher/login`
- `/admin/*`, `/direction/*` → `/admin/login`
- Fallback par rôle meta si le path ne suffit pas

### `/admin` sans trailing slash

- Produit un 404 en production car nginx proxy vers Django admin
- `/admin/login` et `/admin/dashboard` fonctionnent (routes SPA)
- Non corrigé : nécessiterait un changement nginx, impact minimal

### `/direction`

- Déjà redirigé vers `/korrigo/direction` (page publique) ✅

## 3. Corrections apportées

| Fichier | Modification |
|---------|-------------|
| `frontend/src/router/index.js` | Ajout `getLoginForRoute()`, remplacement des 2 redirects `'/'` |
| `frontend/tests/unit/routeGuards.contract.test.ts` | 17 tests contract (nouveau) |
| `frontend/tests/e2e/auth-flow.spec.ts` | Mise à jour attendu : `/admin/login` au lieu de `/` |
| `frontend/tests/e2e/direction-results.spec.ts` | Mise à jour attendu : `/admin/login` au lieu de `/` |

## 4. Matrice profils/workflows

### Public
- `/`, `/korrigo`, `/korrigo/guide-*`, `/korrigo/direction` : rendu SPA, H1, CTA, aucune PII ✅

### Enseignant
- `/teacher/login` : formulaire visible ✅
- `/corrector-dashboard` : requiresAuth + role Teacher ✅
- Sans auth → `/teacher/login` (après fix) ✅
- Auth local E2E : login → dashboard → correction → logout ✅

### Élève
- `/student/login` : formulaire visible ✅
- `/student/dashboard` : requiresAuth + role Student ✅
- Sans auth → `/student/login` (après fix) ✅
- Auth local E2E : login → résultats → logout ✅

### Admin/Direction
- `/admin/login` : formulaire visible ✅
- `/admin/dashboard` : requiresAuth + role Admin ✅
- `/direction/dashboard` : requiresAuth + role Direction ✅
- Sans auth → `/admin/login` (après fix) ✅
- Auth local E2E : login → dashboard → navigation → logout ✅

## 5. Tests

| Suite | Résultat |
|-------|----------|
| Frontend unit tests | 362/362 passed (29 files) |
| Route guard contracts | 17/17 passed |
| Frontend build | OK |
| E2E Playwright local | 130/130 passed |
| Pipeline officiel | `LOCAL_RELEASE_CHECK_STATUS=PASS` |
| E2E pipeline | `E2E_STATUS=PASS_EXISTING_PLAYWRIGHT_OR_CYPRESS` |

### Profils authentifiés

```
AUTHENTICATED_PRODUCTION_PROFILE_FLOW_NOT_TESTED_WITH_REAL_LOGIN=YES
REASON=no approved production test account
COVERAGE=E2E local with seeded accounts (admin, teacher, student, direction)
```

## 6. Déploiement

**Non déployé dans cette porte.** La correction est frontend-only et nécessitera un
build nginx + déploiement dans une porte dédiée (protocole 6K).

## 7. Dettes restantes

| Debt | Status | Blocker |
|------|--------|---------|
| Déploiement nginx fix route guards | Prêt, pipeline vert | Porte dédiée requise |
| HMAC réel admin | pepper/input non fournis | Non-bloquant |
| Compte test production | Non disponible | Flows couverts par E2E local |
| `/admin` 404 (Django proxy) | Non corrigé | Impact minimal, UX acceptable |

## Verdict

**`FUNCTIONAL_UX_AUDIT_READY_FOR_24H_OBSERVATION`**

Le fix est validé localement (pipeline vert, 130 E2E, 362 unit tests).
Le déploiement sera fait dans une porte dédiée quand autorisé.

## Confirmations

- Aucun GitHub
- Aucun push
- Aucun build Docker
- Aucun déploiement
- Aucun restart backend
- Aucune DB/Redis touchée
- Aucune migration
- Aucun down/prune
- Aucune suppression
- Aucune PII visible
