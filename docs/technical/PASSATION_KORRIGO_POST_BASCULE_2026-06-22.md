# Passation Korrigo Post-Bascule

Date de redaction: 2026-06-22  
But: fournir a un futur agent (par exemple ChatGPT 5.5) un etat autonome et exploitable du projet Korrigo, de la migration realisee, de la production actuelle et des chantiers ouverts.

Ce document ne contient aucun secret, aucune valeur de mot de passe, aucun token et aucune donnee personnelle nominative. Les chemins, digests, commits et noms de services sont conserves car ils sont necessaires a l'exploitation.

---

## 1. Resume executif

Korrigo est une plateforme Django/Vue de correction, anonymisation, restitution et bilan d'examens. La production publique est `https://korrigo.labomaths.tn`.

Le chantier principal des 20-22 juin 2026 a transforme une production historiquement fragile en une pile reconstructible et deployee par image Docker digeree:

- avant: image `peer-review-20260525` non reconstructible, overlays montes en prod, compose divergent, migrations appliquees mais absentes de l'image, Redis sans mot de passe, backups StorageBox en clair, workflow GitHub Actions dangereux;
- apres bascule: image finale reconstruite depuis Dockerfiles committes, labels OCI vers le commit source, aucun overlay, Redis AUTH actif, migrations explicites appliquees, health public vert, rollback conserve;
- porte 3: validee par l'administrateur apres verification production;
- chantier post-bascule ouvert: Portes 4 a 9, avec Lot 0 RGPD/CI en cours localement.

Etat production verifie en lecture seule le 2026-06-22T21:12:59Z via `ssh nexus-prod`:

- host: `korrigo`;
- disque `/`: `929G`, `728G` utilises, `154G` libres, `83%`;
- 6 services Korrigo up/healthy;
- backend/celery/celery-beat sur digest backend `sha256:aafe75e7e4bc475f066ed57cc4b16dc816ea3497c70f3e8e954c5ba496929e1e`;
- nginx sur digest `sha256:5c4dda163f3ce4a4ff7e4a2b321adafb398cc3cdaa4461d708de89dabae0f61a`;
- labels OCI backend et nginx: `org.opencontainers.image.revision=1958681b082402e06d0f463e685d8a9895c460c5`, version `korrigo-step3-20260620-1958681`;
- health public: `{"status":"healthy","database":"connected"}`;
- overlays: `0` sur backend, celery et nginx;
- DB non recreatee: `docker-db-1` ID `54202b9d02f88175d077b24fd103cedc9c5e600b7913b82821cfd98bb474ffd1`;
- Redis recreate volontairement pour AUTH: `docker-redis-1` ID `8a8bf2b8e8cc8487ca771f973db12b9ddaddf1cdea96393d4e4a2ef70699aeaf`.

Point important post-bascule: les crons Korrigo backup/sync sont encore suspendus avec le marqueur `SUSPENDED_KORRIGO_BASCULE_20260621T075647Z`. Ils doivent etre remis en service apres correction du chiffrement et du script de retention. Ne pas les reactiver tels quels sans traiter la dette RGPD.

---

## 2. Regles d'exploitation toujours valables

1. Perimetre strict Korrigo. Ne jamais toucher aux projets `nexusreussite`, `nexus-vps` ou autres conteneurs/volumes/vhosts du serveur.
2. Connexion serveur: utiliser `ssh nexus-prod`. Ce canal Tailscale a ete valide et pointe vers le serveur `korrigo`, IP publique `88.99.254.59`.
3. Aucune operation destructive sans backup point-in-time et test de restauration.
4. Ne jamais afficher de secrets, de valeurs `.env`, de tokens, de mots de passe ou de donnees personnelles.
5. Les deploiements production ne doivent plus etre automatiques. Ils passent par runbook controle: backup, plan de migration, one-shot explicite, health, rollback.
6. Les anciennes images de rollback ne doivent pas etre supprimees avant une decision Porte 4 explicite.
7. Les donnees de moins d'un an ne doivent jamais etre supprimees.

---

## 3. Topologie production actuelle

### 3.1 Acces et repertoires

- Domaine public: `korrigo.labomaths.tn`.
- Acces serveur: `ssh nexus-prod`.
- Ancien repertoire historique conserve: `/var/www/labomaths/korrigo`.
- Repertoire release clone propre: `/var/www/labomaths/korrigo_release`.
- Fichier env actuellement utilise: `/var/www/labomaths/korrigo/.env`.
- Compose canonique attendu: `/var/www/labomaths/korrigo_release/infra/docker/docker-compose.prod.yml`.
- Projet Compose: `docker`.

Decision importante: le `.env` reste dans le repertoire legacy pour eviter de manipuler les secrets pendant la bascule. Pendant les operations de release, on lit uniquement ce fichier depuis le legacy; on ne lit pas le code legacy.

### 3.2 Services Docker

Etat verifie le 2026-06-22:

| Service | Conteneur | Image | Etat |
|---|---|---|---|
| PostgreSQL | `docker-db-1` | `postgres:15-alpine` | up healthy |
| Redis | `docker-redis-1` | `redis:7-alpine` | up healthy, AUTH actif |
| Backend Django | `docker-backend-1` | backend digest `aafe75...` | up healthy |
| Celery worker | `docker-celery-1` | backend digest `aafe75...` | up healthy |
| Celery beat | `docker-celery-beat-1` | backend digest `aafe75...` | up healthy |
| Nginx | `docker-nginx-1` | nginx digest `5c4dda...` | up healthy |

IDs verifies:

- `docker-db-1`: `54202b9d02f88175d077b24fd103cedc9c5e600b7913b82821cfd98bb474ffd1`;
- `docker-redis-1`: `8a8bf2b8e8cc8487ca771f973db12b9ddaddf1cdea96393d4e4a2ef70699aeaf`;
- `docker-backend-1`: `fcf0db653a50a49ca220e9c4c95303909820533d20dbbcfe31bb7760b01812e0`;
- `docker-celery-1`: `ded49af3d9f09743517e588cfccbc1d3434310e51dd1bca22c96b30f8ca7737c`;
- `docker-celery-beat-1`: `766294d0b07a8337c1215d244099465824648850f87cef6342e3c4e8786d65dd`;
- `docker-nginx-1`: `358790132e74cf7e819d726948f451cb4da74f61426b6dd6eedcac22d0a4eb30`.

### 3.3 Volumes vivants

- DB PostgreSQL: volume `docker_postgres_data`.
- Media: volume `docker_media_volume`, environ `8528` fichiers et `14G` lors de l'inventaire pre-bascule.
- Backups locaux: volume `docker_backup_volume`.

Ne pas supprimer ces volumes.

### 3.4 Disque et dette Docker

Etat verifie le 2026-06-22:

- `/`: `929G`, `728G` utilises, `154G` libres, `83%`;
- images Docker: `108` total, `572.1GB`, reclaimable `500.4GB`;
- build cache: `1487`, `518.8GB`, reclaimable `466.8GB`;
- volumes: `71`, `25.74GB`, reclaimable `626.1MB`.

Conclusion: la Porte 4 est urgente. Mais il faut nettoyer avec perimetre strict Korrigo, conserver l'image courante et les digests rollback, et ne jamais faire de prune global non cible.

---

## 4. Etat Git et branches

Worktree de travail post-bascule:

`/home/alaeddine/.config/superpowers/worktrees/korrigo_v2_improved/release-reconcile`

Etat au moment de cette passation:

- branche locale: `fix/lot0-rgpd-deploy`;
- HEAD: `1958681b082402e06d0f463e685d8a9895c460c5`;
- tag sur HEAD: `korrigo-step3-20260620-1958681`;
- sujet du commit: `fix: document student login rate-limit guards`;
- des changements locaux Lot 0-B sont presents et non pousses.

Important: ne pas pousser sans validation humaine. Le Lot 0-B neutralise justement un workflow `deploy.yml` dangereux; tant que ce patch n'est pas revu et pousse consciemment, eviter tout `git push`.

Branches et jalons majeurs:

- `wip/worktree-20260620`: snapshot de l'ancien worktree sale pour ne rien perdre;
- `release/reconcile`: reconciliation source/image/overlays et Porte 2;
- `release/prod-unification`: unification config et hardening Step 3;
- `audit/post-bascule-portes-4-9`: audit post-bascule;
- `fix/lot0-rgpd-deploy`: hotfix local RGPD Niveau 1 + neutralisation deploy + gate anti-PII.

---

## 5. Architecture fonctionnelle de Korrigo

Korrigo gere des examens numerises, des copies d'eleves, des corrections, des bilans et des restitutions.

Fonctions principales:

1. creation et parametre d'examens;
2. import PDF de scans/copies;
3. decoupage/anonymisation/traitement PDF;
4. identification et association aux eleves;
5. correction par correcteurs;
6. workflows peer-review;
7. finalisation PDF et restitution eleve;
8. generation de bilans et rapports direction;
9. authentification separee admin/professeur/direction/eleve;
10. sauvegardes, logs et controles RGPD.

### 5.1 Backend

Stack:

- Django + Django REST Framework;
- PostgreSQL 15;
- Redis 7 comme cache/broker;
- Celery + Celery beat;
- Nginx en reverse proxy;
- Gunicorn avec worker `gthread`.

Apps importantes:

- `core`: auth, roles, settings, health, vues plateforme, audit/logging;
- `exams`: examens, copies, imports, finalisation, media, migrations de statut;
- `grading`: correction, annotations, peer-review;
- `students`: authentification eleve, acces resultats, rate-limit metier;
- `bilan`: orchestrateurs et services de bilans;
- `identification`: identification/anonymisation;
- autres apps Django standard: `auth`, `admin`, `contenttypes`, `sessions`.

### 5.2 Frontend

Stack:

- Vue;
- Vite/Vitest;
- routing par vues selon roles;
- composants stats/bilans/admin/correcteur/eleve.

Zones sensibles:

- vues direction et bilans;
- dashboards stats;
- pages contenant historiquement des donnees nominatives en dur;
- guards frontend a aligner avec permissions backend.

### 5.3 Infra

Compose canonique:

- `infra/docker/docker-compose.prod.yml`;
- images referencees par digest;
- zero overlay apres bascule;
- `.env` prod hors Git, lu par Compose.

Nginx:

- route API vers backend;
- protections medias;
- headers CSP/frame pour PDF iframe;
- garde-fou anti-flood haut sur login eleve, sans remplacer la limite metier Django par identifiant.

---

## 6. Chronologie de l'assainissement

### 6.1 Etape 1: reference et backup initial

Objectif: etablir un point de reference avant toute action destructive.

Resultats:

- backup StorageBox `20260620_133001` confirme;
- restauration testee avec succes dans une pile jetable;
- health restore: `{"status":"healthy","database":"connected"}`;
- references fichiers: `file_refs=1793`, `missing=0`;
- migrations Django: `110`;
- `exams_copy=733`;
- `core_auditlog=33474`;
- aucun conteneur/reseau jetable restant.

### 6.2 Nettoyage scratch et confidentialite

Actions autorisees et realisees:

- source StorageBox confirmee par checksums;
- scratch distant non chiffre `/tmp/korrigo-restore-step1-20260620t115755z` efface;
- espace recupere: `/` passe d'environ `84%` a `83%`;
- sweep PII des preuves et logs;
- ajout de protections `.gitignore` pour eviter dump/media/export dans Git;
- aucun dump/media telecharge dans le depot.

### 6.3 Sauvegarde du worktree sale et classification

Le worktree sale a ete conserve sur:

- branche `wip/worktree-20260620`;
- snapshot `41765243f558b5466d71edfe25c6117acc16717f`;
- classification documentee dans `docs/technical/WORKTREE_CLASSIFICATION_2026-06-20.md`.

Classification:

- A: fonctionnalite/correctif a integrer;
- B: hotfix/overlay prod a reconcilier dans le code canonique;
- C: rebut ou element a exclure.

### 6.4 Migrations critiques exams/grading

Probleme initial:

- DB prod/restauree marquait `exams.0039`, `0040`, `0041` appliquees;
- image active ne contenait les fichiers que jusqu'a `0038`;
- schema live avait une contrainte `exams_copy.status` a 3 statuts (`READY`, `IN_PROGRESS`, `FINALIZED`);
- fichier Git `0038` historique exprimait une contrainte a 5 statuts (`READY`, `LOCKED`, `IN_PROGRESS`, `GRADED`, `FINALIZED`);
- deux migrations `grading` appliquees sans fichier (`0013_alter_annotation_type`, `0020_alter_annotation_type`) etaient absentes et ont ete reintegrees.

Decision:

- reintegrer `0039`, `0040`, `0041` comme historique canonique;
- integrer `0042_copy_pdf_regeneration_pending_db_default`;
- creer `0043_reconcile_copy_status_constraint` pour fixer explicitement la contrainte live a 3 statuts;
- creer `grading.0028_reconcile_peer_review_status_constraint`;
- reintegrer les migrations fantomes `grading.0013` et `grading.0020`.

Preuve Porte 2:

- `APPLIED_WITHOUT_FILE_COUNT=0`;
- fichiers pending attendus seulement: `exams.0042`, `exams.0043`, `grading.0028`;
- clone technique StorageBox + base vide: `SCHEMA_DIFF=EMPTY`.

### 6.5 Reconciliation release et suppression des overlays

Objectif: sortir d'une prod patchwork par overlays et rendre l'image reconstructible.

Travaux realises:

- integration des overlays utiles dans les sources canoniques;
- resolution des doublons `backend/...` vs chemins app;
- decision sur orchestrateurs EAM:
  - `backend/bilan/services/eam_orchestrator.py` est le flux actif;
  - `backend/bilan/services/orchestrator_eam.py` est dormant/redondant, conserve pour audit Porte 7;
- modele canonique `Copy`: `exams.models.Copy`, table `exams_copy`;
- `grading.models.Copy` n'est pas un modele distinct mais un alias d'import;
- tests et staging sans overlay.

Porte 2 validee:

- build complet depuis Dockerfiles committes;
- image prod sans dependances dev;
- labels OCI;
- tests backend/frontend;
- parite historique de migrations;
- staging sans overlay.

Digests Porte 2 conserves pour rollback:

- backend `sha256:a6b750e56dd976153d62bec16128ebf4d8a1efc6a68fb24fc86c11d46b5657c8`;
- nginx `sha256:09401293f50173ce8483df7ea7897ba880e6d3b79450955f9eb70c0fd8ebf7fd`.

### 6.6 Step 3 staging: configuration et hardening

Travaux realises avant prod:

- compose unique canonique;
- images par digest;
- aucun overlay;
- Redis AUTH;
- `DJANGO_AUTO_MIGRATE=false`;
- `SEED_ON_START=false`;
- `ENABLE_API_DOCS=false`;
- `DEFAULT_PASSWORD` retire du runtime;
- `E2E_SEED_TOKEN` retire;
- backups GPG au repos;
- client PostgreSQL 15 et `gpg` installes dans l'image backend;
- entrypoint fail-fast:
  - base vide/non migree refusee proprement;
  - migrations via one-shot explicite uniquement;
  - suppression des `|| true` dangereux;
- rate-limit login eleve par identifiant:
  - 10 echecs / 15 min;
  - 11e tentative => `429`;
  - IP partagee/NAT non penalisee pour identifiants distincts;
- nginx garde un anti-flood haut sur `/api/students/login/` (`30r/s`, `burst=60`);
- risque Redis `allkeys-lru` accepte car volume attendu faible, mais alerte memoire a ajouter Porte 8;
- alias silencieux `n_copies_graded` supprime; statut metier canonique = `FINALIZED`;
- sweeps logs RGPD.

Image finale validee:

- commit/tag: `1958681b082402e06d0f463e685d8a9895c460c5`, `korrigo-step3-20260620-1958681`;
- backend digest: `sha256:aafe75e7e4bc475f066ed57cc4b16dc816ea3497c70f3e8e954c5ba496929e1e`;
- nginx digest: `sha256:5c4dda163f3ce4a4ff7e4a2b321adafb398cc3cdaa4461d708de89dabae0f61a`;
- image prod sans `pytest`;
- `pg_dump`, `pg_restore` 15.18 et `gpg` presents;
- backend tests: `990` puis dernier Lot 0 local `994` passes selon contexte;
- frontend vitest: `334` passes.

### 6.7 Preparation prod et runbook

Decouvertes importantes:

1. `/var/www/labomaths/korrigo` n'etait pas un depot Git.
2. Decision: creer un clone propre dans `/var/www/labomaths/korrigo_release` et conserver legacy intact.
3. `.env` historique a ete complete par l'administrateur:
   - `REDIS_PASSWORD` neuf;
   - `BACKUP_GPG_PASSPHRASE` neuf;
   - flags politiques ajoutes;
   - `SEED_ON_START=false`;
   - `DEFAULT_PASSWORD` retire du runtime.
4. Lecture des secrets: ne pas sourcer `.env` comme shell. Le fichier contient des caracteres non shell-safe. Methode retenue: lire via le parseur Compose (`docker compose config --format json`) afin d'obtenir exactement les valeurs injectees, sans afficher de secrets.
5. StorageBox Hetzner a un shell restreint: pas de `ssh remote sha256sum -c`. Verification distante adaptee par `rsync --checksum --dry-run` et SFTP.
6. Les backups planifies existants etaient en clair et le sync retention etait en erreur. Dette reportee apres bascule.
7. Le backup predeploy a ete allege volontairement a DB + JSON, car les migrations etaient schema-only et ne touchaient pas le media. L'archive media de 14G a tout de meme fini par arriver sur StorageBox, mais elle n'etait pas requise pour le rollback schema-only.
8. Les crons backup/sync ont ete suspendus pour eviter saturation SSH et fuite RGPD par backup en clair.
9. Canal SSH fiable: `ssh nexus-prod` via Tailscale/OpenClaw.

### 6.8 Execution prod, etapes 0 a 11

Les operations prod ont ete executees par etapes avec arret humain entre chaque.

Etape 0: verification `.env`

- chemin: `/var/www/labomaths/korrigo/.env`;
- permissions `600`;
- cles obligatoires presentes;
- cles interdites absentes (`DEFAULT_PASSWORD`, `E2E_SEED_TOKEN`);
- aucune valeur affichee.

Etape 1: clone propre et preflight

- clone `/var/www/labomaths/korrigo_release`;
- verrou image sur `1958681`;
- compose config valide avec `.env`;
- digests finaux presents dans le config;
- DB/Redis IDs inchanges.

Etape 2: gel applicatif

- `nginx`, `celery`, `celery-beat` arretes;
- `db`, `redis`, `backend` conserves up;
- ingress public coupe;
- aucun worker actif.

Etape 3: backup predeploy

- backup leger DB + JSON chiffre GPG;
- upload StorageBox verifie par rsync checksum dry-run;
- jeu local conserve: `/tmp/korrigo_predeploy_20260620_215505`;
- dossier distant: `backups/korrigo_backups/20260620_215505_predeploy`;
- archive media locale 14G conservee et aussi disponible a distance, mais non requise pour rollback schema-only.

Etape 4: test restaurabilite

- dump restaure dans PostgreSQL 15 jetable;
- `django_migrations=110`;
- `exams_copy=733`;
- contrainte a 3 statuts verifiee;
- conteneur/reseau jetables detruits sans residu;
- prod intacte.

Etape 5: pull images finales

- backend `aafe75...` et nginx `5c4dda...` presents localement;
- labels OCI `revision=1958681...`;
- aucun service demarre/recree.

Etape 6: Redis AUTH

- Redis recreate volontairement:
  - ancien ID `e9974dab146d...`;
  - nouveau ID `8a8bf2b8e8cc...`;
- DB non recreatee;
- AUTH prouve:
  - PONG avec mot de passe;
  - NOAUTH sans mot de passe;
  - `maxmemory-policy=allkeys-lru`.

Etape 7: plan de migration

- one-shot `--entrypoint python`;
- plan exact:
  - `exams.0042_copy_pdf_regeneration_pending_db_default`;
  - `exams.0043_reconcile_copy_status_constraint`;
  - `grading.0028_reconcile_peer_review_status_constraint`;
- aucune migration inattendue.

Etape 8: application migrations

- les trois migrations ont ete appliquees une par une;
- `migrate --check rc=0`;
- `showmigrations` cible en `[X]`;
- `exams_copy.pdf_regeneration_pending` default `false`;
- contrainte `check_copy_status_valid`: `READY`, `IN_PROGRESS`, `FINALIZED`, sans `LOCKED` ni `GRADED`;
- contrainte peer-review: `NOT_STARTED`, `IN_PROGRESS`, `FINALIZED`;
- `exams_copy=733`;
- aucune copie hors statut valide;
- DB jamais recreatee.

Etape 9: backend final

- backend ancien remplace par image finale;
- nouveau backend ID `fcf0db653a50...`;
- healthy;
- `overlay_mount_count=0`;
- `manage.py check rc=0`;
- logs sans erreur Redis/DB.

Etape 10: workers + nginx

- celery, celery-beat et nginx demarres sur image finale;
- 6 services up/healthy;
- celery -> Redis AUTH OK;
- zero overlay partout;
- health public vert.

Etape 11: verification fonctionnelle

- health public OK;
- page login servie;
- rate-limit eleve verifie;
- medias proteges refuses sans auth;
- logs sans erreur recurrente, sans trace Redis NOAUTH/DB, sans fuite visible;
- celery/beat OK.

Conclusion: Porte 3 validee par l'administrateur.

---

## 7. Etat des migrations et schema production

Production actuelle:

- `exams.0042`, `exams.0043`, `grading.0028` appliquees;
- `migrate --check` OK apres bascule;
- `exams_copy` contient `733` lignes au moment de verification de migration;
- `exams_copy.status` doit rester limite a `READY`, `IN_PROGRESS`, `FINALIZED`;
- `grading_peerreviewcorrection.status` doit rester limite a `NOT_STARTED`, `IN_PROGRESS`, `FINALIZED`;
- `exams_copy.pdf_regeneration_pending` a un default DB `false`.

Cette reconciliation remplace l'ancien etat hybride ou Django croyait certains fichiers absents/presents differemment de la DB.

Ne pas revenir aux anciens statuts `LOCKED`/`GRADED` sans nouvelle analyse fonctionnelle. Le statut metier canonique pour copie finalisee est `FINALIZED`.

---

## 8. Backups et rollback

### 8.1 Backup predeploy de la bascule

Jeu principal:

- local: `/tmp/korrigo_predeploy_20260620_215505`;
- distant: `backups/korrigo_backups/20260620_215505_predeploy`;
- contenu utile rollback schema-only:
  - dump DB chiffre `.dump.gpg`;
  - exports JSON metier chiffres;
  - `SHA256SUMS_LIGHT` ou equivalent leger;
- media: archive 14G disponible mais non requise pour rollback schema-only.

Verification:

- checksum local OK;
- upload StorageBox verifie par `rsync --checksum --dry-run`;
- restore DB prouve en conteneur jetable.

### 8.2 Rollback logique

Rollback post-migration doit etre schema-conscient:

1. stopper services applicatifs Korrigo;
2. recreer la base, ne pas restaurer par-dessus une base deja migree;
3. restaurer le dump predeploy;
4. revenir aux digests Porte 2:
   - backend `sha256:a6b750e56dd976153d62bec16128ebf4d8a1efc6a68fb24fc86c11d46b5657c8`;
   - nginx `sha256:09401293f50173ce8483df7ea7897ba880e6d3b79450955f9eb70c0fd8ebf7fd`;
5. verifier que la contrainte copy revient a l'ancien schema si rollback pre-migration;
6. health/parcours.

Ne jamais lancer rollback sans ordre explicite.

### 8.3 Dette backup planifie

Les crons sont suspendus:

- root crontab:
  - ligne backup `korrigo_backup.sh` commentee avec `SUSPENDED_KORRIGO_BASCULE_20260621T075647Z`;
- `/etc/cron.d/korrigo_storagebox_sync`:
  - ligne sync retention commentee avec le meme marqueur.

Raison:

- le backup planifie poussait le media 14G toutes les 30 minutes et saturait SSH;
- il poussait des artefacts en clair;
- le sync retention etait en erreur.

A faire avant reactivation:

- rendre le backup planifie chiffre au repos;
- eviter l'upload integral media a chaque run ou passer a une strategie incrementale;
- corriger la retention StorageBox via SFTP/rsync compatible shell restreint;
- tester restore automatise;
- reactiver les crons et prouver le premier cycle.

---

## 9. Etat securite/RGPD

Acquis:

- Redis AUTH actif;
- `.env` prod en `600`;
- `DEFAULT_PASSWORD` absent du runtime;
- `E2E_SEED_TOKEN` retire;
- docs API desactivees en prod;
- backups Step 3 chiffres GPG;
- logs Step 3/staging sweeps sans email/secret;
- medias proteges valides;
- frontend Lot 0-B local retire des PII visibles dans plusieurs composants.

Risques residuels:

1. Backups planifies encore suspendus et a remettre en conformite chiffree.
2. PII frontend exposee dans l'image actuellement en prod jusqu'a deploiement du hotfix Lot 0-B. Le patch local retire ces valeurs du bundle, mais n'est pas encore deployee.
3. `deploy.yml` dangereux dans l'historique distant tant que le hotfix local n'est pas pousse/revu. Le patch local le neutralise.
4. Audit complet hardcoding/code mort/FE-BE-route encore a faire Portes 7-9.

---

## 10. Lot 0-B local en cours

Branche: `fix/lot0-rgpd-deploy`  
Base: `1958681b082402e06d0f463e685d8a9895c460c5`  
Etat: local seulement, non pousse, non build, non deployee.

Objectif:

- neutraliser le risque GitHub Actions deploy;
- retirer PII Niveau 1 du bundle frontend;
- ajouter un gate CI anti-PII par hashes;
- conserver l'acces direction via capacite serveur.

Fichiers modifies/ajoutes:

- `.github/workflows/deploy.yml`;
- `.github/workflows/ci.yml`;
- `backend/core/views.py`;
- `backend/core/tests/test_lot0_rgpd_deploy_contract.py`;
- `frontend/src/components/stats/StatsQcmTab.vue`;
- `frontend/src/components/stats/StatsQualityTab.vue`;
- `frontend/src/views/BilanBacBlanc.vue`;
- `frontend/src/views/HomeView.vue`;
- `frontend/src/views/admin/QuestionnaireBilan.vue`;
- `scripts/ci/check_frontend_pii_hashes.py`.

Details:

- `deploy.yml` devient un stub manuel `workflow_dispatch`, sans push auto, sans reset DB, sans migrate auto, sans seed prod auto.
- `StatsQcmTab.vue` ne contient plus de tableaux statiques nominatifs; il rend les donnees seulement depuis `props.data` et affiche un etat vide neutre.
- `BilanBacBlanc.vue` ne contient plus d'emails de direction; il consomme `authStore.user.can_view_direction_bilans`.
- `backend/core/views.py` ajoute `can_view_direction_bilans` dans `/api/me`, calcule depuis les roles/groupes direction existants.
- Le gate anti-PII stocke uniquement des hashes SHA-256 normalises dans `scripts/ci/check_frontend_pii_hashes.py`.

Tests executes localement:

- gate PII: `PII_HASH_MATCH_COUNT=0`;
- `git diff --check`: OK;
- frontend unit cible: `197 passed`;
- frontend complet: `334 passed`;
- backend cible: `4 passed`;
- backend complet: `994 passed, 1 skipped, 3 deselected`.

Important: le diff brut contient des lignes supprimees avec PII reelle. Ne pas coller le diff brut dans une conversation ou un ticket public sans redaction.

---

## 11. Workflow GitHub Actions

Risque initial:

- `deploy.yml` pouvait se declencher sur push main;
- il contenait des operations destructrices/automatiques: reset DB, `down -v`, migrations et seed prod.

Etat local Lot 0-B:

- `.github/workflows/deploy.yml` est neutralise;
- il renvoie vers le runbook controle;
- pas de chemin automatique vers prod.

Avant tout push:

1. revue humaine du patch Lot 0-B;
2. verifier qu'aucune valeur PII ne reapparait dans le diff;
3. verifier que `deploy.yml` ne contient pas de trigger push ni d'etape destructive;
4. pousser seulement apres accord, idealement via PR non deployante.

---

## 12. Portes restantes

### Porte 4: Docker/disque

Objectif: reduire l'empreinte Docker sans perdre le rollback.

Plan:

- inventaire exact des images Korrigo;
- conserver image courante `1958681` + digests rollback Porte 2 + au moins 3 dernieres releases utiles;
- supprimer uniquement images/cache Korrigo confirmes;
- ne pas toucher aux images/volumes d'autres projets;
- documenter espace recupere.

Contrainte: pas de `docker system prune` global aveugle.

### Porte 5: volumes/scratch/zombies

Objectif: nettoyer les orphelins Korrigo uniquement.

Ne jamais supprimer:

- `docker_postgres_data`;
- `docker_media_volume`;
- volumes actifs references par les conteneurs en prod.

### Porte 6: donnees orphelines + recette UI/UX

Objectif:

- rapport medias orphelins;
- lignes orphelines DB;
- purge retention > 1 an;
- recette UI/UX par roles admin/correcteur/eleve/direction;
- aucune suppression sans backup et validation explicite;
- jamais de donnees < 1 an.

### Porte 7: assainissement depot

Objectif:

- sortir donnees hors-code du suivi Git;
- clarifier `docs/` vs `documentation/`;
- detecter code mort;
- audit coherence FE <-> BE <-> DB <-> nginx <-> routage;
- trancher `orchestrator_eam.py` dormant;
- trancher commande `create_peer_review_produit_scalaire_g6.py` avec examen code en dur;
- sweep hardcoding.

### Porte 8: robustesse runtime

Objectif:

- healthchecks/start_period;
- restart policies;
- limites ressources;
- rotation logs;
- alertes disque/backup/certificats/health;
- alerte Redis `evicted_keys`;
- runbook exploitation.

### Porte 9: garde-fous CI

Objectif:

- CI anti-overlay;
- CI labels OCI/KORRIGO_SHA;
- PostgreSQL obligatoire pour migrations PG-only;
- controle historique migrations DB vs fichiers;
- test restore automatise;
- ruff/vulture/knip/depcheck;
- gate anti-PII frontend deja amorce en Lot 0-B.

---

## 13. Commandes de verification utiles

Toutes les commandes serveur doivent passer par `ssh nexus-prod`.

### Health prod

```bash
ssh nexus-prod 'curl -fsS https://korrigo.labomaths.tn/api/health/'
```

Attendu:

```json
{"status":"healthy","database":"connected"}
```

### Services Korrigo

```bash
ssh nexus-prod 'docker ps --filter name=docker- --format "{{.Names}}|{{.Image}}|{{.Status}}" | sort'
```

Attendu: 6 services `docker-db-1`, `docker-redis-1`, `docker-backend-1`, `docker-celery-1`, `docker-celery-beat-1`, `docker-nginx-1`, tous up/healthy.

### Labels OCI

```bash
ssh nexus-prod 'docker inspect docker-backend-1 --format "{{ index .Config.Labels \"org.opencontainers.image.revision\" }} {{ index .Config.Labels \"org.opencontainers.image.version\" }}"'
ssh nexus-prod 'docker inspect docker-nginx-1 --format "{{ index .Config.Labels \"org.opencontainers.image.revision\" }} {{ index .Config.Labels \"org.opencontainers.image.version\" }}"'
```

Attendu:

```text
1958681b082402e06d0f463e685d8a9895c460c5 korrigo-step3-20260620-1958681
```

### Overlays

```bash
ssh nexus-prod 'for c in docker-backend-1 docker-celery-1 docker-nginx-1; do echo "$c"; docker inspect "$c" --format "{{range .Mounts}}{{println .Source}}{{end}}" | grep -i overlay || true; done'
```

Attendu: aucune ligne overlay.

### Disque

```bash
ssh nexus-prod 'df -h / && docker system df'
```

Attention: `docker system df` peut etre lent a cause du cache massif.

### Crons suspendus

```bash
ssh nexus-prod 'crontab -l | grep SUSPENDED_KORRIGO_BASCULE || true; grep -R SUSPENDED_KORRIGO_BASCULE /etc/cron.d /etc/crontab 2>/dev/null || true'
```

Attendu actuellement: les deux lignes Korrigo backup/sync sont suspendues.

---

## 14. Pieges connus

1. Ne pas sourcer `.env` avec `. "$ENV_FILE"`: certains secrets peuvent contenir des caracteres non shell-safe. Utiliser Compose comme parseur.
2. StorageBox a un shell restreint: pas de commandes distantes type `sha256sum`. Utiliser `rsync --checksum --dry-run` et SFTP.
3. Ne pas lancer `docker compose up -d` global sans gardes: la DB ne doit pas etre recreatee.
4. Redis a change d'ID volontairement pour AUTH; tout changement ulterieur de Redis hors operation prevue est suspect.
5. Les backups planifies sont suspendus; ne pas oublier cette dette.
6. Le media fait environ 14G; l'envoyer integralement toutes les 30 minutes sature le lien et SSH.
7. Les vieux documents peuvent mentionner des digests intermediaires (`ead834e`, `332866...`, etc.). L'image prod actuelle validee est `1958681` avec digests `aafe75...` et `5c4dda...`.
8. `ASSAINISSEMENT_KORRIGO.md` peut etre en retard dans le worktree local concernant la Porte 3; la validation humaine de Porte 3 a bien ete donnee apres l'etape 11.
9. Le diff Lot 0-B contient des suppressions de PII: ne pas l'afficher brut hors contexte securise.

---

## 15. Prochaines actions recommandees

Priorite immediate:

1. Revoir le patch Lot 0-B local.
2. S'assurer que `deploy.yml` neutralise vraiment tout deploiement automatique.
3. Verifier que le gate anti-PII ne contient aucune valeur claire et passe.
4. Decider du mode de livraison Lot 0-B: PR, revue, build, staging, puis deploiement controle.
5. Apres Lot 0-B valide/deploye, reactiver un pipeline backup conforme:
   - backup chiffre;
   - pas d'upload media complet a chaque run;
   - retention StorageBox corrigee;
   - restore test periodique.
6. Lancer Porte 4 pour recuperer disque, avec perimetre Korrigo strict.

Priorite suivante:

- audit FE/BE/nginx/routes;
- suppression code mort;
- hardcoding;
- runbook exploitation;
- CI migrations/restore/overlay/OCI.

---

## 16. References locales importantes

- Checklist et journal: `ASSAINISSEMENT_KORRIGO.md`.
- Decision migrations exams/grading: `docs/technical/MIGRATIONS_EXAMS_0039_0042_DECISION_2026-06-20.md`.
- Cloture Porte 2: `docs/technical/STEP2_RELEASE_RECONCILE_CLOSURE_2026-06-20.md`.
- Classification du worktree sale: `docs/technical/WORKTREE_CLASSIFICATION_2026-06-20.md`.
- Plan Step 3: `docs/superpowers/plans/2026-06-20-korrigo-step3-prod-unification.md`.
- Preuves Step 3 finales:
  - `proofs/20260620_step3_n/`;
  - `proofs/20260620_step3_o/`;
  - `proofs/20260620_step3_p/`;
  - `proofs/20260620_step3_q/`;
  - `proofs/20260620_step3_s/`.
- Gate PII local: `scripts/ci/check_frontend_pii_hashes.py`.

---

## 17. Phrase de reprise pour futur agent

Si tu reprends ce projet, commence par:

1. lire ce document;
2. verifier `git status` dans `/home/alaeddine/.config/superpowers/worktrees/korrigo_v2_improved/release-reconcile`;
3. ne pas pousser tant que le patch Lot 0-B n'est pas revu;
4. verifier en lecture seule que prod tourne toujours sur `1958681` et health vert;
5. traiter les actions dans l'ordre: Lot 0-B, backup planifie chiffre, Porte 4 Docker, puis Portes 5-9.

La prod est saine mais encore fragile operationalement: la bascule technique est terminee, la dette d'exploitation et RGPD post-bascule doit etre fermee avec la meme discipline de backup, preuves et arrets humains.
