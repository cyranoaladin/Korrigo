# Lot 0-E - Clean Hotfix Branch Strategy

Date: 2026-06-22

## 1. Contexte du NO-GO precedent

Le Lot 0-D a produit un candidat local audite, mais il a ete classe NO-GO push/PR/prod.

Cause: `origin/main` n'est pas alignee sur la production validee. La production de reference est le commit `1958681b082402e06d0f463e685d8a9895c460c5`, tag `korrigo-step3-20260620-1958681`, alors que `origin/main` pointe sur un commit plus ancien.

Une PR directe vers `main` embarquerait donc l'historique Step 3 en plus du hotfix RGPD/deploy. Ce ne serait pas une revue isolee.

## 2. Pourquoi `origin/main` ne peut pas servir de base hotfix

Topologie observee:

- `origin/main`: `c0f0b4905c9607dace1d92fbd49d3f6ebb785d84`
- `1958681`: `1958681b082402e06d0f463e685d8a9895c460c5`
- merge-base `origin/main` / `1958681`: `c0f0b4905c9607dace1d92fbd49d3f6ebb785d84`
- `origin/main` est ancetre de `1958681`
- `1958681` n'est pas ancetre de `origin/main`
- `origin/main...1958681`: `0 22`
- `origin/main...hotfix Lot 0-D`: `0 27`

Conclusion: `origin/main` ne contient pas la bascule Step 3. Comparer le hotfix a `origin/main` montre un diff massif parce que Step 3 est absent de `main`, pas parce que le hotfix est large.

## 3. Branche locale propre creee

Branches locales creees, non poussees:

- `release/prod-1958681-local`, base stricte: `1958681b082402e06d0f463e685d8a9895c460c5`
- `hotfix/lot0-rgpd-deploy-clean`, issue de `release/prod-1958681-local`

La branche `release/prod-1958681-local` porte bien le tag `korrigo-step3-20260620-1958681`.

## 4. Commits repris

Cherry-picks appliques sans conflit:

- source `44a5fcd28863fb0da1f4940e1efff89439de9b6a` -> local `875bcd4`: retrait PII frontend, neutralisation `deploy.yml`, gate anti-PII, capacite `/api/me`
- source `e7b3aeb9bd0f93b366cb7ba75fa340ef5c05c1ed` -> local `5dedc1b`: durcissement gate, tests, retrait emails frontend restants, asset public nettoye

Commit local additionnel Lot 0-E:

- `9e1dd9b`: remplacement de l'ancien asset public `Korrigo.png` par le logo public deja utilise, pour supprimer les faux positifs du scan email generique sur binaire public

Les commits documentaires Lot 0-D suivants n'ont pas ete repris dans le runtime hotfix:

- `5665027` passation post-bascule
- `7ce0400` audit pre-PR Lot 0-D
- `ddb3a78` note NO-GO push Lot 0-D

## 5. Diff contre la production `1958681`

Avant ajout du present document, le diff runtime contre `1958681` contient 18 fichiers:

- `.github/workflows/ci.yml`
- `.github/workflows/deploy.yml`
- `backend/core/tests/test_lot0_rgpd_deploy_contract.py`
- `backend/core/views.py`
- `docs/technical/LOT0B_RGPD_DEPLOY_HOTFIX_REVIEW_2026-06-22.md`
- `frontend/public/images/Korrigo.png`
- `frontend/src/components/Footer.vue`
- `frontend/src/components/stats/StatsQcmTab.vue`
- `frontend/src/components/stats/StatsQualityTab.vue`
- `frontend/src/views/BilanBacBlanc.vue`
- `frontend/src/views/DirectionConformite.vue`
- `frontend/src/views/ForgotPassword.vue`
- `frontend/src/views/GuideEtudiant.vue`
- `frontend/src/views/HomeView.vue`
- `frontend/src/views/admin/QuestionnaireBilan.vue`
- `frontend/src/views/admin/UserManagement.vue`
- `frontend/src/views/student/LoginStudent.vue`
- `scripts/ci/check_frontend_pii_hashes.py`

Ce diff est strictement explicable par le hotfix RGPD/deploy:

- neutralisation du deploiement automatique dangereux;
- ajout du gate CI anti-PII;
- retrait de PII et emails du bundle frontend;
- remplacement de l'autorisation frontend nominative par une capacite serveur;
- tests contractuels associes;
- documentation hotfix minimale.

Aucun dump, media, `.env`, migration, script de restauration, ou fichier Step 3 non lie au hotfix n'est present dans ce diff.

## 6. Diff contre `origin/main`

Le diff `origin/main..hotfix/lot0-rgpd-deploy-clean` reste massif:

- avant document Lot 0-E: 104 fichiers;
- cause: `origin/main` est en retard de 22 commits sur la production `1958681`.

Ce diff ne doit pas servir de reference de revue tant que `main` n'est pas realignee.

## 7. Tests executes

Resultats sur la branche propre:

- `git diff --check`: PASS
- `pytest -q -p no:cacheprovider backend/core/tests/test_lot0_rgpd_deploy_contract.py`: PASS, 14 tests
- `cd backend && pytest -q -p no:cacheprovider`: PASS, 1004 passed, 1 skipped, 3 deselected
- `cd frontend && npm test -- --run`: PASS, 334 tests
- `cd frontend && npm run build`: PASS
- `cd frontend && npm run lint`: PASS avec 4212 warnings existants, 0 erreur
- `ruff check backend`: FAIL, 379 erreurs existantes hors perimetre Lot 0-E

## 8. Scans PII executes

Resultats sans affichage de valeur personnelle:

- `frontend/src`: `PII_HASH_MATCH_COUNT=0`
- `frontend/dist`: `PII_HASH_MATCH_COUNT=0`
- `frontend/src`: `EMAIL_FILE_COUNT=0`, `EMAIL_TOTAL_COUNT=0`
- `frontend/dist`: `EMAIL_FILE_COUNT=0`, `EMAIL_TOTAL_COUNT=0`
- `frontend/public`: `EMAIL_FILE_COUNT=0`, `EMAIL_TOTAL_COUNT=0`
- image nginx locale extraite: `PII_HASH_MATCH_COUNT=0`
- image nginx locale extraite: `IMAGE_NGINX_EMAIL_FILE_COUNT=0`, `IMAGE_NGINX_EMAIL_TOTAL_COUNT=0`

## 9. Images Docker locales

Images locales runtime construites avant le commit du present document, sans push registry:

- tag backend: `korrigo-backend:korrigo-lot0e-clean-local-9e1dd9b`
- digest local backend: `sha256:68691bc21aa0c95fb5fb64013cd4dd17b4d3a3aaf17dabac927c0fd3efee0a88`
- tag nginx: `korrigo-nginx:korrigo-lot0e-clean-local-9e1dd9b`
- digest local nginx: `sha256:0377f7cc9df7ca94b99b2019230c5169bdf92a4bd8cae72d9549949c593ae540`
- label OCI backend/nginx: `org.opencontainers.image.revision=9e1dd9bbe25431ed9ffb78caa60a3dbddde6161f`

Apres le commit documentaire, les images doivent etre reconstruites pour porter le HEAD final. Les digests finaux sont a consigner dans le rapport d'execution, afin d'eviter une reference circulaire commit -> document -> digest -> commit.

## 10. Decision

Decision Lot 0-E:

- GO local candidat propre;
- NO-GO push;
- NO-GO PR;
- NO-GO production.

La branche propre est validee localement, mais la base distante de review doit etre decidee avant toute publication.

## 11. Options de livraison

### Option A - Branche distante `release/prod-1958681`

Creer une branche distante a partir de `1958681`, puis ouvrir une PR du hotfix vers cette branche.

Avantages:

- diff de revue minimal;
- ne depend pas de `main`;
- respecte l'etat reel de production.

Risques:

- ajoute un flux de release temporaire a gerer;
- necessite une decision explicite sur la future reconciliation avec `main`.

### Option B - Realigner `main` sur la production

Pousser d'abord l'etat production valide vers `main`, puis ouvrir une PR classique.

Avantages:

- restaure le modele attendu `main = prod`;
- simplifie les PR futures.

Risques:

- operation sensible sur branche principale;
- necessite une revue separee de l'alignement Step 3.

### Option C - Deployer depuis une branche release dediee

Publier une branche release dediee et deployer via runbook controle sans attendre `main`.

Avantages:

- rapide pour neutraliser l'exposition navigateur;
- compatible avec un deploiement controle par digest.

Risques:

- dette de reconciliation `main` repoussee;
- exige une validation humaine forte et une tracabilite explicite.

## 12. Recommandation

Recommandation: Option A.

Creer une branche distante `release/prod-1958681` depuis le tag prod, puis ouvrir une PR non deployante de `hotfix/lot0-rgpd-deploy-clean` vers cette branche. Cette option donne un diff minimal et auditable sans attendre le chantier plus large d'alignement de `main`.

Ensuite seulement:

1. revue humaine de la PR;
2. build/push d'images hotfix par digest;
3. staging sans overlay;
4. backup point-in-time;
5. deploiement production controle;
6. scan du bundle public servi;
7. reprise des backups chiffres;
8. Porte 4 Docker/disque.

