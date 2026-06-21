# Audit post-bascule Korrigo - Portes 4 a 9

Date: 2026-06-21  
Base d'audit code: `1958681b082402e06d0f463e685d8a9895c460c5` (`korrigo-step3-20260620-1958681`)  
Branche d'audit: `audit/post-bascule-portes-4-9`  
Worktree audite: `/home/alaeddine/.config/superpowers/worktrees/korrigo_v2_improved/release-reconcile`  
Prod observee en lecture seule: `ssh nexus-prod`, hostname `korrigo`, pile Docker projet `docker`

## 0. Etat de depart

- Le depot local de developpement audite est le worktree propre `release/prod-unification`, branche d'audit creee depuis le commit image valide `1958681`.
- Le worktree historique `/home/alaeddine/Bureau/KORRIGO/korrigo_v2_improved` reste sur `wip/worktree-20260620` avec `ASSAINISSEMENT_KORRIGO.md` modifie; il n'a pas ete utilise pour produire ce rapport.
- La production est saine en lecture seule: `docker-backend-1`, `docker-celery-1`, `docker-celery-beat-1`, `docker-nginx-1`, `docker-db-1`, `docker-redis-1` sont up/healthy; l'endpoint public `/api/health/` retourne `{"status":"healthy","database":"connected"}`.
- Les en-tetes de securite servis publiquement incluent HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, CSP et Permissions-Policy.

## 1. Inventaire architecture

### Backend Django

- `core`: settings, authentification, utilisateurs, health/metrics, media proteges, password reset, seed/dev endpoints, taches backup.
- `exams`: examens, copies, import PDF, booklets, identification rattachee, rapports de jury, stats, documents.
- `grading`: workflow de correction, brouillons, annotations, verrous, finalisation PDF, peer-review, questionnaires, exports.
- `students`: login eleve, espace eleve, copies, changement de mot de passe, import/admin reset.
- `identification`: bureau d'identification, OCR, rapprochement manuel.
- `bilan`: bilans pedagogiques DNB/EAM, analytics, RAG/LLM, generation PDF.
- `processing`: utilitaires de decoupe/splitter.

Couplages visibles: `grading` depend fortement de `exams.Copy`; `students` expose des vues specialisees sur `Copy` et `PeerReviewCorrection`; `bilan` depend des structures d'examens/corrections et contient du domaine metier EAM/DNB tres specifique.

### Frontend Vue

- `router/index.js`: routes publiques, admin, direction, correcteur, eleve, bilans, redirects legacy.
- `views/admin`: dashboards admin, examens, copies, correcteurs, baremes, identification, agrafage, bilans, utilisateurs.
- `views/corrector`, `views/student`, `views/peer`: workflows correcteur, eleve, peer-review.
- `components/admin`, `components/stats`, `services`: UI partagee, tableaux statistiques, clients API.
- `stores`: authentification et etat examen.

### Configuration

Variables d'environnement bien etablies: secrets Django, DB, Redis AUTH, CORS/CSRF, metrics, flags prod, rate-limit eleve, GPG backup, workers Gunicorn.  
Reste a consolider: constantes metier d'examens, modeles LLM/RAG par defaut, tailles/timeouts upload, routes de bilans, chemins de donnees one-shot.

| Severite | Emplacement | Constat | Remediation | Effort |
|---|---|---|---|---|
| Majeur | `infra/docker/docker-compose.prod.yml:45`, `:115`, `:177`, `:237` | Le compose au commit image `1958681` pointe encore vers des digests anterieurs, alors que la prod validee tourne sur `aafe75...` et `5c4dda...`. Le verrou OCI est correct cote image, mais la correspondance commit -> manifest deploiement reste fragile. | Ajouter un manifeste de release versionne ou mettre a jour le compose de branche release avec les digests deployes, puis ajouter une gate CI `compose digest == release manifest`. | S |
| Mineur | `backend/core/settings.py:92-95`, `frontend/src/services/api.js:10-17` | Tailles upload, timeouts et retries sont disperses entre Django, nginx et frontend. | Centraliser dans une matrice de configuration documentee et tester la coherence nginx/Django/frontend. | S |

## 2. Scan anti-hardcoding

| Severite | Emplacement | Constat | Remediation | Effort |
|---|---|---|---|---|
| Bloquant | `frontend/src/components/stats/StatsQcmTab.vue:237-254` | Donnees nominatives statiques dans le bundle frontend: noms d'eleves, classes et correcteurs apparaissent dans du code livre. | Remplacer par donnees backend anonymisees ou fixtures de demo sans PII; ajouter une gate CI de detection PII dans `frontend/src`. | S |
| Bloquant | `frontend/src/views/BilanBacBlanc.vue:666-674` | Autorisations direction codees cote frontend par adresses nominatives et listes d'examens; cela melange affichage et politique d'acces. | Supprimer cette matrice du frontend; exposer un `direction_scope` backend et laisser le frontend consommer une capacite, pas des identifiants. | M |
| Majeur | `frontend/src/views/BilanBacBlanc.vue:683-715` | Rapport Bac Blanc largement statique: histogrammes, mentions, indicateurs et correcteurs de demonstration codent un etat metier dans l'UI. | Faire servir le rapport par endpoint backend versionne; garder seulement des composants de rendu. | L |
| Majeur | `backend/bilan/services/eam_orchestrator.py:65-83` | Domaine EAM 2026 tres encode dans le service: classes, exclusions, catalogue de questions et mentions pedagogiques dans le code runtime. | Migrer ces constantes vers une table/fixture versionnee d'examen ou un registre `ExamType` administre. | L |
| Majeur | `frontend/src/views/CorrectorDashboard.vue:466-483`, `frontend/src/components/BilanButton.vue:109-171`, `frontend/src/views/admin/AdminOverview.vue:301-315` | Routage des bilans par codes/noms d'examens en dur (`BAC_BLANC`, `DNB`, `EAM`), avec recherche par libelle exact. | Creer une API `exam_types.capabilities.bilan_route` ou `bilan_url`; le frontend ne doit pas inferer depuis les noms. | M |
| Majeur | `backend/grading/management/commands/create_peer_review_produit_scalaire_g6.py:11-17` | Commande one-shot avec UUID et nom d'examen codifies. | Quarantiner en `scripts/one_shot/` non runtime ou parametrer entierement la commande avec garde `--confirm`. | S |
| Majeur | `backend/exams/management/commands/import_dnb_copies.py:42-44` | Chemin local et nom DNB fixes dans une commande d'import. | Parametrer chemin/examen via arguments obligatoires; documenter comme outil admin ponctuel. | S |
| Majeur | `backend/core/seed_prod.py:60-64`, `:320-324` | Le seed prod peut imprimer des mots de passe generes et des donnees de comptes dans les logs s'il est execute. | Retirer l'affichage de secrets; reserver la transmission des mots de passe a un canal separe; ajouter test anti-log-secret. | S |
| Mineur | `backend/core/settings.py:108-133`, `frontend/src/views/HomeView.vue:514-526` | Modeles LLM/RAG et pile technique par defaut sont visibles dans le code/landing, risque de drift avec l'infra reelle. | Externaliser les modeles actifs et eviter les listes marketing statiques non verifiees. | S |
| Mineur | `infra/nginx/nginx.conf:23-28`, `backend/core/settings.py:535-536` | Les seuils de rate-limit sont documentes et env-configurables cote Django, mais la limite nginx reste dans le fichier. | Garder la limite nginx comme garde anti-flood, mais ajouter un test contrat qui verifie le seuil combine. | S |

Aucun secret de production en clair n'a ete affiche dans ce rapport. Les occurrences `SECRET_KEY`, `PASSWORD`, `TOKEN` relevees dans les workflows sont des secrets CI factices ou references de configuration; elles doivent quand meme rester sous scan automatique.

## 3. Coherence FE/BE/nginx/routage

### Carte synthetique

- Frontend `/api/*` -> nginx `location /api/` -> Django `core.urls`.
- Media proteges: frontend `VITE_MEDIA_URL || /api/media` -> Django `ProtectedMediaView` -> `X-Accel-Redirect` nginx `/media/` interne.
- Routes Vue principales:
  - Admin: `/admin/dashboard`, `/admin/exams/*`, `/admin/users`, `/admin/settings`, `/admin/bilan/*`.
  - Direction: `/direction/dashboard`, `/direction/exams/:examId/results`, bilans partages.
  - Correcteur: `/corrector-dashboard`, `/corrector/desk/:copyId`, `/corrector/my-students`, questionnaires, peer-review.
  - Eleve: `/student/dashboard`, `/student/peer-review/:peerReviewId`, `/student/change-password`.
- Backend endpoints principaux: `exams`, `copies`, `grading`, `students`, `identification`, `bilan`, `media`, health/metrics.
- Nginx: `/api/`, `/metrics`, `/internal-media/`, `/media/` internal, SPA fallback.

| Severite | Emplacement | Constat | Remediation | Effort |
|---|---|---|---|---|
| Majeur | `frontend/src/views/admin/StapleView.vue:112` vs `backend/exams/urls.py` | Le frontend demande `/api/booklets/{id}/header/`, mais les routes backend exposent les booklets sous `/api/exams/booklets/{id}/header/`. Apercu d'agrafage potentiellement casse. | Corriger le chemin frontend et ajouter un test route-contract frontend/backend. | S |
| Majeur | `frontend/src/router/index.js:273-277`, `frontend/src/views/admin/ExamStudentList.vue:176`, `:291` | La route Direction reutilise `ExamStudentList` admin en lecture seule, mais le composant contient encore des actions admin/correcteur conditionnelles. Risque d'affichage hors-role si un garde UI est oublie. | Extraire un composant `ExamResultsReadOnly` commun; tester menus/actions par role. | M |
| Mineur | `frontend/src/router/index.js:280-315` | Les bilans DNB/EAM/Bac Blanc sont exposes comme routes statiques, pendant que le backend gere `BilanReport` dynamiquement. | Remplacer par routes generees depuis les bilans disponibles/capacites backend. | M |
| Mineur | `backend/exams/urls.py` et `backend/grading/urls.py` | Plusieurs endpoints backend semblent peu ou pas appeles par le frontend actuel: annulation de taches, regeneration PDF, document sets, endpoints legacy `student/copies`. | Produire une matrice contractuelle automatique API appelee/API exposee avant suppression. | M |
| Mineur | `infra/nginx/nginx.conf:87-95` et `backend/core/views_media.py` | La chaine media protegee est correcte conceptuellement; elle doit rester couverte par un test nginx + Django car une erreur d'alias rendrait des copies accessibles. | Ajouter test CI/staging `GET /media/...` direct refuse et `GET /api/media/...` controle par role. | S |

## 4. UI/UX et dashboards par profil

| Profil | Pages codees | Constats factuels |
|---|---|---|
| Admin | Dashboard, examens, copies, correcteurs, bareme, resultats, utilisateurs, settings, questionnaires, bilans | Parcours riche mais plusieurs sections specialisent DNB/EAM/Bac Blanc par nom d'examen; dashboard admin contient des blocs conditionnes a des libelles exacts. |
| Correcteur | Dashboard, import, desk de correction, mes eleves, questionnaire, bilan eleve, peer-review | Le dashboard correcteur contient des raccourcis bilans par codes hardcodes et recherche EAM par libelle exact. |
| Eleve | Dashboard resultats, peer-review, changement mot de passe | Surface plus limitee et mieux cloisonnee; a auditer en navigateur pour etats vides/erreur. |
| Direction | Dashboard, resultats examen, bilans partages | Plusieurs vues direction reutilisent des composants admin; les restrictions fines doivent venir du backend, pas du frontend. |

| Severite | Emplacement | Constat | Remediation | Effort |
|---|---|---|---|---|
| Majeur | `frontend/src/views/BilanBacBlanc.vue` | Vue de bilan statique, avec decisions d'acces, donnees et presentation melangees; difficile a maintenir et a tester par profil. | Decouper en `BilanReportView` generique + adaptateurs de donnees backend. | L |
| Majeur | `frontend/src/views/admin/AdminOverview.vue:301-315`, `frontend/src/components/admin/BilanCard.vue` | Dashboards admin dependants du nom exact des examens; un renommage casse les cartes. | Utiliser `exam_type.code` et des capacites renvoyees par `/exams/types/`. | M |
| Mineur | `frontend/src/router/index.js:413-430` | La protection anti-boucle de redirection laisse passer la navigation apres 3 redirects; utile en secours mais peut masquer une incoherence de garde. | Remonter une erreur observabilite et tester les routes par role pour eviter d'utiliser cette sortie comme comportement normal. | S |
| Mineur | `frontend/src/components/stats/*` | Les onglets stats affichent des donnees hardcodees en complement du `StatsReport` dynamique. | Rendre ces onglets strictement derives du payload backend ou les masquer tant que donnees absentes. | M |

## 5. Code mort / orphelins

| Severite | Emplacement | Constat | Remediation | Effort |
|---|---|---|---|---|
| Majeur | `backend/bilan/services/orchestrator_eam.py:20` | `BilanOrchestratorEAM` est defini mais aucun code runtime ne l'importe; le flux actif utilise `backend/bilan/services/eam_orchestrator.py` via `backend/bilan/views.py:18,71`. | Marquer dormant, comparer couverture fonctionnelle, puis supprimer ou fusionner dans une PR dediee avec tests EAM. | M |
| Majeur | `backend/bilan/services/eam_orchestrator.py` | Service actif tres volumineux et fortement specialise; risque de doublon/confusion avec `orchestrator_eam.py`. | Extraire catalogue, analytics, prompt building et rendu en modules testes. | L |
| Mineur | `frontend/src/components/ArchitectureDiagram.vue`, `WorkflowDiagram.vue`, `CopyLifecycleDiagram.vue`, `FeatureCard.vue` | Ces composants ne sont references que par la landing `/korrigo`; ils ne sont pas morts, mais sont marketing/documentaires dans une application operationnelle. | Decider s'ils restent dans le produit public ou dans une documentation separee. | S |
| Mineur | `frontend/src/components/stats/StatsPalmaresTab.vue`, `StatsQualityTab.vue`, `StatsQcmTab.vue` | Composants references par `StatsReport.vue`, mais leur contenu est partiellement statique. | Ne pas supprimer sans remplacement; convertir en composants 100% data-driven. | M |
| Mineur | `backend/staticfiles/` | Dossier collectstatic present dans l'arborescence locale; non trace par Git d'apres l'audit, mais bruite les scans locaux. | Nettoyer les artefacts locaux hors branche produit et verifier `.gitignore`. | S |

## 6. Robustesse runtime

| Severite | Emplacement | Constat | Remediation | Effort |
|---|---|---|---|---|
| Majeur | `backend/bilan/services/analytics_simple.py:163`, `backend/bilan/services/orchestrator.py:158`, `:180`, `:265`, `:380` | Plusieurs `except Exception: pass` masquent des erreurs d'analyse/bilan. | Remplacer par logs structures sans PII + statut partiel explicite dans le payload. | M |
| Majeur | `backend/bilan/services/orchestrator_eam.py:61-62`, `:129-130` | Le module dormant logge via `print()` des erreurs RAG/LLM; si reactive, il fuit hors logging structure. | Supprimer ou convertir en `logger.warning/exception` avec redaction. | S |
| Majeur | `backend/core/seed_prod.py:60-64` | Affichage direct de secrets generes par un script runtime potentiel. | Interdire logs de secrets par test et passer les valeurs via fichier/secret manager hors stdout. | S |
| Mineur | `frontend/src/utils/storage.js:63`, `:117`, `:145`, `:192`, `:195` | `console.log` en utilitaire frontend production; peut exposer cles locales et bruiter le support. | Logger seulement en dev ou supprimer les traces. | S |
| Mineur | `backend/bilan/services/rag_retriever.py:29`, `backend/bilan/services/rag_retriever_premiere.py:28` | Clients HTTP RAG timeout 30s; LLM/Ollama timeout 300s. Ces valeurs existent, mais les UX de fallback/etat partiel doivent etre explicites. | Ajouter statut de generation par section, retry borne et messages utilisateur non techniques. | M |

## 7. CI / garde-fous

Existant: workflows backend pytest, flake8, pip-audit, bandit, tests PostgreSQL marques, release-gate Docker/E2E, build image avec labels OCI dans Dockerfile. Frontend a scripts `vitest`, `eslint`, tests unitaires et e2e dans `frontend/`.

| Severite | Emplacement | Constat | Remediation | Effort |
|---|---|---|---|---|
| Bloquant | CI globale | Pas de gate automatique FE/BE/nginx/routes: un chemin front mort comme `StapleView.vue:112` peut arriver en prod. | Ajouter un job de coherence: extraire appels API frontend, urls Django et locations nginx; fail sur endpoint manquant ou route morte connue. | M |
| Bloquant | CI globale | Pas de scan PII/hardcoding metier ciblant `frontend/src` et services bilan; des noms/emails statiques sont passes. | Ajouter scan denylist PII/fixtures prod + allowlist stricte pour tests. | M |
| Majeur | `.github/workflows/korrigo-ci.yml:183-193` | Le packaging CI construit seulement le backend et ne verifie pas les labels OCI ni le digest nginx. | Construire backend + nginx, inspecter labels OCI `revision/source/version/created`, publier digest lie au commit. | M |
| Majeur | `.github/workflows/deploy.yml:318-340` | Le workflow deploy historique contient encore `RESET_DB`, migration/seed automatiques et `seed_prod`; incompatible avec la discipline post-bascule. | Desactiver ou remplacer par un runbook controle: backup, plan migration, one-shot explicite, pas de seed automatique. | M |
| Majeur | `.github/workflows/release-gate.yml:143-184` | La release gate cree et affiche un `.env` CI complet; acceptable pour valeurs factices, mais pattern dangereux a ne pas reproduire en prod. | Rediger les logs pour toute variable de type secret et imposer `set +x`; documenter que ces valeurs sont uniquement CI jetables. | S |
| Majeur | CI globale | Pas de verification de parite historique migrations appliquees/fichiers ni test restauration automatise dans les workflows courants. | Ajouter job PostgreSQL: apply empty DB, clone schema, compare `django_migrations`, test restore dump technique. | L |
| Mineur | `.github/workflows/korrigo-ci.yml:35-39` | Lint backend limite a flake8; pas de `ruff` ni `vulture` gate. | Ajouter `ruff check` puis `vulture` en mode baseline pour eviter nouveaux morts. | M |

## 8. Porte 4 - Docker / disque / backups

Inventaire lecture seule prod via `ssh nexus-prod`:

- Disque `/` et `/var/lib/docker`: 929G total, 729G utilises, 154G libres, 83%.
- `docker system df`: images 108 / 572.1GB dont 500.4GB reclaimable; build cache 1487 / 518.8GB dont 518.8GB reclaimable; volumes 25.73GB dont 626MB reclaimable; conteneurs 16.51MB.
- Conteneurs Korrigo actifs: backend/celery/celery-beat sur image `aafe75...`, nginx sur `5c4dda...`, DB `postgres:15-alpine`, Redis `redis:7-alpine`.
- Labels OCI des images finales: backend et nginx `org.opencontainers.image.revision=1958681b082402e06d0f463e685d8a9895c460c5`.
- Le grep local des images n'a confirme que les digests finaux `aafe75...` et `5c4dda...`; avant toute suppression Porte 4, il faut resoudre et verifier les digests complets de rollback, pas seulement les prefixes historiques `a6b750...` / `09401293...`.

| Severite | Emplacement | Constat | Remediation | Effort |
|---|---|---|---|---|
| Bloquant | Prod Docker | Disque a 83% avec 572GB d'images et 519GB de build cache; marge correcte aujourd'hui mais faible pour builds/restores futurs. | Porte 4: inventaire avec digests complets, conservation courant + rollback + db/redis, suppression ciblee images Korrigo obsoletes. | M |
| Bloquant | Backup StorageBox / cron Korrigo | Les backups planifies observes pendant la bascule sont en clair et les crons ont ete suspendus; RGPD a traiter avant reactivation. | Convertir le backup planifie en GPG obligatoire, verifier restore, puis reactiver cron/sync avec logs rediges. | M |
| Majeur | Build cache Docker | `docker builder du` indique 518.8GB reclaimable, mais le cache peut etre partage entre projets du serveur. | Ne pas faire de `docker builder prune` global sans attribution; preferer builder dedie Korrigo ou suppression apres preuve que les caches sont Korrigo-only. | M |
| Majeur | Images GHCR locales | Nombreuses images `ghcr.io/cyranoaladin/korrigo-*` anciennes, non actives, accumulees sur 5-8 semaines. | Apres validation rollback, supprimer par digest/tag Korrigo uniquement, jamais volumes ni images non Korrigo. | S |
| Mineur | Volumes Docker | Volumes locaux 25.73GB, reclaimable 626MB seulement; les volumes Korrigo media/db sont donnees de production. | Pas de prune volumes; gerer uniquement retention backups/media temporaires documentee. | S |

Plan Porte 4 propose, sans execution:

1. Reconfirmer prod healthy et backup chiffre post-bascule restaure.
2. Extraire la liste exacte des conteneurs actifs et leurs `Image` IDs.
3. Resoudre les digests complets de rollback a conserver ou declarer le rollback DB+image impossible si non present.
4. Supprimer uniquement les images `ghcr.io/cyranoaladin/korrigo-backend` et `korrigo-nginx` non actives, non rollback, par digest explicite.
5. Mesurer gain disque.
6. Ne traiter le build cache qu'apres isolation/attribution Korrigo; pas de prune global sur serveur partage.
7. Reactiver backups uniquement apres chiffrement au repos et test restore.

## Synthese priorisee

1. **Bloquant - RGPD frontend**: supprimer les donnees nominatives statiques dans `StatsQcmTab.vue` et les identifiants direction hardcodes dans `BilanBacBlanc.vue`; ajouter gate PII.
2. **Bloquant - Backups planifies**: ne pas reactiver les crons tant que les sauvegardes planifiees ne sont pas chiffrees et testees.
3. **Bloquant - Coherence route**: corriger le lien mort probable d'agrafage `/api/booklets/.../header/` et ajouter une gate FE/BE.
4. **Majeur - Bilan/EAM architecture**: centraliser `ExamType`/capabilities, retirer les comparaisons par noms exacts et dedupliquer les orchestrateurs EAM.
5. **Majeur - CI deploy**: neutraliser le workflow deploy historique qui migre/seed automatiquement et ajouter gates OCI/migrations/restore/overlay.
6. **Majeur - Porte 4 disque**: lancer un elagage Korrigo strict apres resolution des digests rollback; ne pas pruner le build cache global avant attribution.
7. **Majeur - Runtime logging**: remplacer les `except: pass`, `print()` et logs potentiellement sensibles par logging structure redige.
8. **Mineur - UX role**: extraire des composants read-only direction et tester menus/actions par profil.

## Arret volontaire

Aucune correction produit, aucun rebuild, aucun redeploiement, aucun prune et aucune suppression n'ont ete effectues pendant cet audit. Les constats ci-dessus doivent etre priorises puis traites dans des branches dediees avec tests et nouvelle image validee.
