# Lot 0-D - Pre-PR Release Audit

Date: 2026-06-22

## 1. Branche et commits

- Branche locale: `fix/lot0-rgpd-deploy`
- Base de production: `1958681b082402e06d0f463e685d8a9895c460c5`
- Hotfix Lot 0-C: `44a5fcd28863fb0da1f4940e1efff89439de9b6a`
- Note de passation: `56650273f494fc28f7116d0cf2846cff23163611`
- Durcissement Lot 0-D runtime: `e7b3aeb9bd0f93b366cb7ba75fa340ef5c05c1ed`

Le hotfix n'est pas deploye en production. La production publique reste figee sur l'image validee `1958681`.

## 2. Statut du fichier de passation

Le fichier `docs/technical/PASSATION_KORRIGO_POST_BASCULE_2026-06-22.md` a ete relu avant commit.

Controle effectue:

- pas de secret;
- pas de token;
- pas de mot de passe;
- pas de contenu `.env`;
- pas de dump;
- pas de donnee personnelle reelle detectee par les scans appliques.

Decision: fichier utile et sain, conserve dans le depot via un commit documentaire separe.

## 3. Audit global GitHub Actions

| Workflow | Triggers | Secrets | Build image | Push GHCR | SSH/prod | Migrations/prod | Risque | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `.github/workflows/deploy.yml` | `workflow_dispatch` uniquement | Non | Non | Non | Non | Non | Faible | OK: stub manuel, aucun chemin prod |
| `.github/workflows/ci.yml` | `push` main/develop/feature, `pull_request` main/develop | Non | Build Vite uniquement | Non | Non | Non | Faible | OK |
| `.github/workflows/korrigo-ci.yml` | `push` main/master/develop, `pull_request` main/master/develop | Non | Backend local CI | Non | Non | Non | Faible | OK |
| `.github/workflows/release-gate.yml` | `pull_request` chemins cibles, `push` main, `workflow_dispatch` | Non | Local runner | Non | Non | Non | Moyen | OK: operations Docker runner-local uniquement |
| `.github/workflows/security-scan.yml` | `push` main/develop, `pull_request` main/develop, schedule hebdo | Non | Scan seulement | Non | Non | Non | Faible | OK |
| `.github/workflows/tests-optimized.yml` | `push` main, `pull_request` main | Non | Non | Non | Non | Migrate sur PostgreSQL CI local | Faible | OK |

Conclusion: aucun workflow audite ne peut muter la production sur un push de branche `fix/lot0-rgpd-deploy`. Le workflow de deploiement production est neutralise et manuel uniquement.

## 4. Evaluation du gate anti-PII

Le script `scripts/ci/check_frontend_pii_hashes.py` ne contient aucune donnee personnelle en clair. Il stocke des SHA-256 de valeurs normalisees connues.

Limite importante: ces SHA-256 sont une pseudonymisation de controle, pas une anonymisation. Un hash de nom ou email peut etre attaque par dictionnaire si l'attaquant dispose d'hypotheses.

Decision Lot 0-D:

- conserver le SHA-256 pour ne pas retarder le hotfix navigateur;
- documenter la limite explicitement dans `LOT0B_RGPD_DEPLOY_HOTFIX_REVIEW_2026-06-22.md`;
- planifier Lot 0-E: remplacement par HMAC-SHA256 avec `PII_GATE_PEPPER` non committe, regeneration des marqueurs par l'administrateur, fail-closed en CI si le pepper manque.

Durcissements verifies:

- accents;
- casse;
- espaces multiples;
- caracteres invisibles intramot;
- email synthetique;
- nom compose synthetique;
- absence de fuite de la valeur detectee dans stdout/stderr;
- faux positif raisonnable evite sur contenu technique.

## 5. Scans PII

Resultats sans affichage de valeur sensible:

- `frontend/src`: `PII_HASH_MATCH_COUNT=0`
- `frontend/dist`: `PII_HASH_MATCH_COUNT=0`
- `frontend/src`: `EMAIL_FILE_COUNT=0`, `EMAIL_TOTAL_COUNT=0`
- `frontend/dist`: `EMAIL_FILE_COUNT=0`, `EMAIL_TOTAL_COUNT=0`
- `frontend/public`: `EMAIL_FILE_COUNT=0`, `EMAIL_TOTAL_COUNT=0`
- image nginx locale extraite: `PII_HASH_MATCH_COUNT=0`, `EMAIL_FILE_COUNT=0`, `EMAIL_TOTAL_COUNT=0`

Correction additionnelle Lot 0-D: `frontend/public/images/Korrigo.png` contenait un motif email dans ses metadonnees/binaires. L'image a ete reencodee sans metadonnees sensibles. Elle n'est pas referencee par les vues, mais reste un asset public potentiel.

Scan large non bloquant hors bundle navigateur:

- racines scannees: `backend`, `scripts`, `docs`, `.github`, `frontend/src`;
- resultats: `BROAD_EMAIL_FILE_COUNT=104`, `BROAD_EMAIL_TOTAL_COUNT=468`;
- interpretation: occurrences concentrees dans tests, scripts backend et documentation. Ce n'est pas corrige par le hotfix navigateur et doit etre traite en Lot 0-E/Porte 7 avec classification public/institutionnel/test/personnel.

## 6. Verification `/api/me` et capacite direction

`/api/me` expose:

- `can_view_direction_bilans`;
- `features.can_view_direction_bilans`;
- `direction_scope`.

La capacite ne depend plus d'emails codes en dur dans le frontend. Elle est calculee cote serveur a partir des roles/groupes:

- admin: autorise;
- enseignant: autorise;
- direction lycee: autorisee;
- direction college: non autorisee pour les bilans lycee;
- staff sans groupe metier: non autorise;
- eleve: refuse par le contrat `/api/me` enseignant/admin.

Risque residuel: cela reste un retrait d'urgence de PII frontend et une capacite d'UI. L'enforcement complet de tous les bilans doit etre consolide cote backend en Lot 2/Porte 7.

## 7. Verification frontend

Constats:

- `StatsQcmTab.vue`: tableaux nominaux statiques retires, rendu base sur `props.data`, etats vides neutres.
- `StatsQualityTab.vue`: pas de PII statique connue, pas de fallback nominatif.
- `BilanBacBlanc.vue`: emails frontend retires, acces UI base sur capacite serveur. La vue reste statique et doit etre refondue via endpoints backend.
- `HomeView.vue`, `QuestionnaireBilan.vue`, `Footer.vue`, `DirectionConformite.vue`, `GuideEtudiant.vue`, `ForgotPassword.vue`, `UserManagement.vue`, `LoginStudent.vue`: pas d'email en clair dans `frontend/src` apres Lot 0-D.

Dette explicite: `BilanBacBlanc.vue` ne doit pas etre consideree comme architecture finale.

## 8. Tests et builds locaux

Commandes executees:

- `git diff --check`: PASS
- `python scripts/ci/check_frontend_pii_hashes.py frontend/src`: PASS, `PII_HASH_MATCH_COUNT=0`
- `python scripts/ci/check_frontend_pii_hashes.py frontend/dist`: PASS, `PII_HASH_MATCH_COUNT=0`
- `pytest -q -p no:cacheprovider backend/core/tests/test_lot0_rgpd_deploy_contract.py`: PASS, 14 tests
- `cd backend && pytest -q -p no:cacheprovider`: PASS, 1004 passed, 1 skipped, 3 deselected
- `cd frontend && npm test -- --run`: PASS, 334 tests
- `cd frontend && npm run build`: PASS
- `cd frontend && npm run lint`: PASS avec 4212 warnings existants, 0 erreur
- `ruff check backend`: FAIL, 379 erreurs existantes hors perimetre Lot 0-D

Le build image local backend/nginx a ete execute sans push registry, sans deploiement et sans `docker compose up` production. Les labels OCI sont verifies dans le rapport de livraison.

## 9. Statut du push

Statut final Lot 0-D: NO-GO push automatique dans ce tour.

Garanties etablies:

- aucun workflow ne peut muter la production sur push de `fix/lot0-rgpd-deploy`;
- aucun push vers `main`;
- aucun tag release prod;
- aucun `workflow_dispatch`;
- aucun build/push GHCR;
- aucun deploiement.

Blocage de livraison PR: `origin/main` n'est pas aligne sur la production `1958681`. Un diff `origin/main..HEAD` embarque 106 fichiers et tout l'historique Step 3, pas seulement le hotfix RGPD/deploy. Une PR directe vers `main` ne serait donc pas une revue isolee du Lot 0.

Decision: ne pas pousser tant que la base de PR n'est pas tranchee. Options propres:

1. aligner d'abord `main` sur l'etat production valide;
2. ouvrir une PR vers une branche de release dediee issue de `1958681`;
3. extraire le hotfix dans une branche basee explicitement sur la future base de merge retenue.

## 10. Statut PR

PR non creee. Le push de branche est differe pour eviter une PR trop large et non representative du hotfix.

## 11. Risques residuels

- Production non corrigee tant que le hotfix n'est pas construit, publie et deploye via runbook controle.
- Hash SHA-256 de PII connue: pseudonymisation, pas anonymisation. HMAC avec pepper non committe a traiter en Lot 0-E.
- Emails generiques/potentiellement personnels encore presents hors bundle navigateur dans backend/scripts/docs.
- `BilanBacBlanc.vue` reste statique et doit etre remplacee par un flux backend coherent.
- Backups/sync StorageBox suspendus pendant la bascule: a remettre en service en mode chiffre conforme.
- `ruff check backend` echoue sur dette preexistante; a transformer en gate CI apres remediation ciblee.
- `infra/docker/docker-compose.prod.yml` local doit etre revalide contre les digests de production avant tout deploiement hotfix.
- `main` n'est pas encore la base de production courante, ce qui bloque une PR hotfix propre vers `main`.

## 12. Prochaine etape recommandee

1. Revue humaine du diff expurge et du present rapport.
2. Decider la base de PR: `main` alignee prod, branche de release issue de `1958681`, ou extraction du hotfix sur une base propre.
3. Push controle de la branche retenue.
4. PR draft non deployante.
5. Build/push d'images hotfix par digest, sous tag relie au commit.
6. Staging sans overlay.
7. Backup point-in-time.
8. Deploiement production controle.
9. Scan du bundle public servi.
10. Reprise des backups chiffres.
11. Porte 4 Docker/disque.
