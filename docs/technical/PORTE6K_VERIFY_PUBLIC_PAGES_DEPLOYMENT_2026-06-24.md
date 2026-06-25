# Porte 6K-VERIFY — Vérification renforcée post-déploiement des pages publiques

**Date** : 2026-06-24
**Opérateur** : Claude Code
**Branche** : `hotfix/lot0-rgpd-deploy-clean`
**HEAD** : `5efbd31b37d0aef732628a1ad4ebce32233ce7ab`

## Contexte

Porte 6K a déployé nginx `korrigo-nginx:korrigo-direct-81b85c5` avec les pages publiques
durcies. Trois angles morts identifiés nécessitaient une vérification renforcée :

1. Le scan image nginx avait détecté `IMAGE_NGINX_ANONYMOUS_ID_COUNT=22` et
   `IMAGE_NGINX_PLACEHOLDER_COUNT=4`, classés manuellement comme faux positifs.
2. L'audit production des pages avait utilisé `curl`/assets, pas Playwright réel.
3. Le diff compose serveur avait été décrit comme "image-only" avec un diff massif pré-existant.

## 1. Préflight production

| Service | Image | Status |
|---------|-------|--------|
| nginx | `korrigo-nginx:korrigo-direct-81b85c5` | healthy (16 min) |
| backend | `korrigo-backend:korrigo-direct-c38a586` | healthy (7h) |
| celery | `korrigo-backend:korrigo-direct-c38a586` | healthy (7h) |
| celery-beat | `korrigo-backend:korrigo-direct-c38a586` | healthy (7h) |
| db | `postgres:15-alpine` | healthy (5 weeks) |
| redis | `redis:7-alpine` | healthy (3 days) |
| Health API | `{"status":"healthy","database":"connected"}` | OK |

## 2. Audit Playwright production réel

Navigateur Chromium headless contre `https://korrigo.labomaths.tn`, 4 routes testées :

| Route | Status | H1 | Text len | Email | Forbidden | Console | Network | Failed | `/admin/login` |
|-------|--------|----|----------|-------|-----------|---------|---------|--------|----------------|
| `/korrigo` | 200 | 1 | 2521 | 0 | 0 | 0 | 0 | 0 | 1 |
| `/korrigo/guide-enseignant` | 200 | 1 | 1583 | 0 | 0 | 0 | 0 | 0 | 1 |
| `/korrigo/guide-eleve` | 200 | 1 | 1346 | 0 | 0 | 0 | 0 | 0 | 1 |
| `/korrigo/direction` | 200 | 1 | 1684 | 0 | 0 | 0 | 0 | 0 | 1 |

Forbidden patterns testés (toutes 0) :
`guide-enseignanthttps`, `Lorem`, `TODO`, `fake`, `dummy`, `anonymous_id`,
`platform-stats`, `OCR`, `LLM`, `intelligence artificielle`.

Screenshots sauvegardés dans l'audit dir local.

**Résultat** : PASS — aucun texte interdit visible, aucune erreur console/réseau, CTA direction présent.

## 3. Classification déterministe du bundle nginx

Script automatique `korrigo_6k_classify_nginx_bundle_findings.py` :

| Métrique | Valeur | Seuil |
|----------|--------|-------|
| `BUNDLE_EMAIL_COUNT` | 0 | =0 |
| `BUNDLE_HTML_VISIBLE_RISK_COUNT` | 0 | =0 |
| `BUNDLE_UNKNOWN_FINDING_COUNT` | 0 | =0 |
| `BUNDLE_JS_CODE_TOKEN_COUNT` | 22 | documenté |
| `BUNDLE_THIRD_PARTY_TOKEN_COUNT` | 4 | documenté |

### Détail des 22 `js_bundle_code_token` (anonymous_id)

Fichiers JS applicatifs contenant la chaîne `anonymous_id` comme nom de propriété dans le code
Vue compilé (pas des données PII réelles) :

- `StudentBilan` (1), `IdentificationDesk` (1), `ResultView` (1), `BilanDetail` (1)
- `ExamStudentList` (6), `PeerReviewDesk` (1), `ExamCopies` (3)
- `index` (3), `CorrectorDesk` (5)

### Détail des 4 `third_party_token` (placeholder)

Occurrences du mot `todo` dans `index-DNCo1fxr.js` — token du parser markdown `marked.js`
pour les listes de tâches (`- [ ] todo`). Contexte confirme `task/checkbox/list`.

### Non visible en production

L'audit Playwright production a vérifié que :
- `anonymous_id` n'apparaît jamais dans le texte visible des 4 pages publiques
- `TODO` n'apparaît jamais dans le texte visible des 4 pages publiques

Ces tokens ne sont accessibles que dans le code source JS minifié, pas dans le rendu utilisateur.

**Résultat** : PASS avec faux positifs documentés.

## 4. Compose serveur/local

| Emplacement | nginx | backend | config |
|-------------|-------|---------|--------|
| Serveur `docker-compose.prod.yml` | `korrigo-direct-81b85c5` | `korrigo-direct-c38a586` (×3) | OK |
| Local `docker-compose.prod.yml` | `korrigo-direct-81b85c5` | `korrigo-direct-c38a586` (×3) | — |
| Local `local_release_check.sh` | `korrigo-direct-81b85c5` | `korrigo-direct-c38a586` | — |
| Local `test_prod_compose_contract.py` | `korrigo-direct-81b85c5` | — | — |

Ancien tag `korrigo-direct-f793f0c` : absent de tous les fichiers actifs.

## 5. Pipeline local officiel

- Audit dir : `/tmp/korrigo_porte6k_verify_release_check_20260624T191718Z`
- `LOCAL_RELEASE_CHECK_STATUS=PASS`
- `E2E_STATUS=PASS_EXISTING_PLAYWRIGHT_OR_CYPRESS`

## 6. Rollback

Non requis. Toutes les vérifications sont vertes.

## Verdict

**`PAGES_DEPLOY_VERIFIED_WITH_DOCUMENTED_BUNDLE_FALSE_POSITIVES`**

## Confirmations

- Aucun GitHub
- Aucun push
- Aucun build Docker
- Aucun déploiement nouveau
- Aucun redémarrage
- Aucun backend touché
- Aucun DB/Redis touché
- Aucune migration
- Aucun `docker compose down`
- Aucun `down -v`
- Aucun prune
- Aucun cleanup Docker
- Aucune PII visible
- Aucun `.env` / secret / pepper affiché
