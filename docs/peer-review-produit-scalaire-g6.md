# Correction participative - Produit scalaire- 1 EDS G6

## 1. Resume de l'intervention

Objectif: ajouter un dispositif parallele de correction participative par les eleves pour l'examen `Produit scalaire- 1 EDS G6`, sans modifier les copies ni corrections officielles.

Priorite absolue: aucune ecriture dans les tables officielles de correction (`exams_copy`, `grading_score`, `grading_annotation`, `grading_questionremark`, `grading_gradingevent`) pendant l'activite eleve.

## 2. Sauvegardes realisees

Sauvegardes effectuees le 2026-05-25 avant toute modification production.

- Dump PostgreSQL complet: `/var/backups/korrigo/korrigo_before_peer_review_20260525_214632.dump` (4.7M)
- Archive code/app production: `/var/backups/korrigo/korrigo_code_before_peer_review_20260525_214632.tar.gz` (14G)

Les deux fichiers ont ete verifies comme presents et non vides.

## 3. Etat initial observe

- Domaine: `korrigo.labomaths.tn`
- Repertoire production: `/var/www/labomaths/korrigo`
- Deploiement: Docker Compose, images GHCR taggees SHA
- Backend: Django + DRF, Gunicorn
- Frontend: Vue 3 + Vite
- Base: PostgreSQL dans le conteneur `docker-db-1`
- Redis/Celery actifs
- Nginx vers `127.0.0.1:8088`

Examen cible:

- Nom exact en base: `Produit scalaire- 1 EDS G6`
- ID: `4c9dfd06-72fc-47b4-ad11-b63dba655076`
- Copies: 23
- Eleves lies: 23
- Eleves distincts: 23
- Correcteur officiel: `alaeddine.benrhouma@ert.tn`
- Bareme: 4 exercices, total 20 points
- Statuts initiaux: 2 `IN_PROGRESS`, 21 `READY`

Copies officielles deja commencees:

| Copie | Statut | Score | Annotations | Remarques | Appreciation |
| --- | --- | --- | --- | --- | --- |
| 4C9D-001 | IN_PROGRESS | present | 10 | 22 | longueur 295 |
| 4C9D-003 | IN_PROGRESS | present | 11 | 22 | longueur 333 |

## 4. Architecture retenue

Architecture validee: modeles separes dans l'application `grading`.

- `PeerReviewCorrection`
- `PeerReviewAnnotation`
- `PeerReviewQuestionRemark`
- `PeerReviewEvent`

Les corrections participatives pointent vers la copie source officielle en lecture, mais n'ecrivent jamais dans les tables officielles.

## 5. Modeles ajoutes

Modeles ajoutes dans `backend/grading/models.py`:

- `PeerReviewCorrection`: correction participative separee, liee a `Exam`, `Copy`, `Student`, `User` eleve correcteur et enseignant superviseur.
- `PeerReviewAnnotation`: annotations eleves separees, liees a `PeerReviewCorrection`.
- `PeerReviewQuestionRemark`: remarques par question separees, liees a `PeerReviewCorrection`.
- `PeerReviewEvent`: journal leger des creations, sauvegardes et finalisations participatives.

Contraintes ajoutees:

- unique `(exam, source_copy)`.
- unique `(exam, assigned_student)`.
- controle applicatif empechant une auto-correction.
- controle applicatif imposant `assigned_user == assigned_student.user`.
- controle de statut parmi `NOT_STARTED`, `IN_PROGRESS`, `FINALIZED`.

## 6. Migrations ajoutees

- Migration principale: `grading.0027_peerreviewcorrection_peerreviewevent_and_more`.
- Tables creees:
  - `grading_peerreviewcorrection`
  - `grading_peerreviewannotation`
  - `grading_peerreviewquestionremark`
  - `grading_peerreviewevent`
- Index/contraintes crees:
  - `uniq_peer_review_exam_source_copy`
  - `uniq_peer_review_exam_assigned_student`
  - `check_peer_review_status_valid`
  - `uniq_peer_remark_review_question`
  - index par examen/statut, utilisateur/statut, superviseur/examen, annotation page, evenement timestamp.

Note de deploiement: le contexte de production ne contenait pas les fichiers de migrations `grading.0024`, `0025`, `0026`; ils ont ete ajoutes au contexte build car `0027` depend de `0026`. Ces migrations ne changent que les choix du champ `GradingEvent.action`.

Plan observe avant application:

```text
grading.0027_peerreviewcorrection_peerreviewevent_and_more
    Create model PeerReviewCorrection
    Create model PeerReviewEvent
    Create model PeerReviewAnnotation
    Create model PeerReviewQuestionRemark
    Create constraints and indexes PeerReview*
```

Application:

```text
Applying grading.0027_peerreviewcorrection_peerreviewevent_and_more... OK
```

## 7. Endpoints API ajoutes

Endpoints eleves:

- `GET /api/students/peer-reviews/`
- `GET /api/students/peer-reviews/<uuid>/`
- `PATCH /api/students/peer-reviews/<uuid>/save/`
- `POST /api/students/peer-reviews/<uuid>/finalize/`

Endpoints enseignant:

- `GET /api/grading/teacher/exams/<exam_id>/peer-reviews/`
- `GET /api/grading/teacher/peer-reviews/<uuid>/`

Garanties:

- les endpoints eleves filtrent strictement par `assigned_user` et `assigned_student`;
- aucune identite de l'auteur de la copie n'est retournee cote eleve;
- aucune ecriture dans `Score`, `Annotation`, `QuestionRemark`, `GradingEvent`, `Copy.status`, `Copy.global_appreciation`;
- modification refusee si la correction participative est `FINALIZED`;
- l'enseignant superviseur voit les corrections de l'examen.

## 8. Composants frontend ajoutes/modifies

- `frontend/src/services/peerReviewApi.js`: service API participatif.
- `frontend/src/router/index.js`: routes eleve et enseignant vers le desk participatif.
- `frontend/src/views/peer/PeerReviewDesk.vue`: interface de correction participative, en mode eleve editable et mode enseignant lecture seule.
- `frontend/src/views/student/ResultView.vue`: section `Corrections participatives`.
- `frontend/src/views/CorrectorDashboard.vue`: tableau enseignant `Corrections participatives`.

Le desk affiche un bandeau explicite indiquant que la correction est pedagogique et non officielle.

## 9. Commande d'assignation

Commande Django ajoutee:

```bash
python manage.py create_peer_review_produit_scalaire_g6
```

Options:

- `--dry-run`: simulation obligatoire sans creation.

Comportement:

- recherche par exam ID `4c9dfd06-72fc-47b4-ad11-b63dba655076`;
- verifie 23 copies, 23 eleves, 23 eleves distincts, bareme present, correcteur officiel present;
- cree une permutation circulaire par `anonymous_id`;
- refuse toute auto-correction;
- utilise `get_or_create`;
- ne remplace jamais une affectation existante;
- ne copie aucune annotation, note, remarque ou appreciation officielle.

## 10. Resultat du dry-run

Commande:

```bash
docker exec docker-backend-1 python manage.py create_peer_review_produit_scalaire_g6 --dry-run
```

Resultat:

- Examen detecte: `Produit scalaire- 1 EDS G6`
- Copies detectees: 23
- Eleves detectes: 23
- Corrections participatives existantes: 0
- Corrections creees: 0
- Message: `Dry-run uniquement : aucune correction participative creee.`

## 11. Resultat de la creation reelle

Commande:

```bash
docker exec docker-backend-1 python manage.py create_peer_review_produit_scalaire_g6
```

Resultat:

- Corrections participatives existantes avant creation: 0
- Corrections participatives creees: 23
- Message: `Creation terminee sans modifier les corrections officielles.`

Verification idempotence:

```bash
docker exec docker-backend-1 python manage.py create_peer_review_produit_scalaire_g6
```

Resultat: 23 existantes, 0 creee.

## 12. Nombre de corrections participatives creees

- Total `PeerReviewCorrection` pour l'examen: 23
- Statut initial: 23 `NOT_STARTED`
- `PeerReviewAnnotation`: 0
- `PeerReviewQuestionRemark`: 0
- `PeerReviewEvent`: 23 evenements `CREATE`

## 13. Liste des affectations

Liste anonymisee par identifiant de copie et ID interne eleve correcteur:

```text
4C9D-001 -> 607
4C9D-003 -> 532
4C9D-005 -> 690
4C9D-007 -> 674
4C9D-009 -> 537
4C9D-011 -> 733
4C9D-013 -> 731
4C9D-015 -> 738
4C9D-017 -> 726
4C9D-019 -> 533
4C9D-021 -> 735
4C9D-023 -> 655
4C9D-025 -> 736
4C9D-027 -> 721
4C9D-029 -> 608
4C9D-031 -> 540
4C9D-033 -> 739
4C9D-035 -> 724
4C9D-037 -> 722
4C9D-039 -> 538
4C9D-041 -> 728
4C9D-043 -> 688
4C9D-045 -> 723
```

## 14. Verification de non-alteration de 4C9D-001 et 4C9D-003

Etat avant creation participative:

| Copie | Statut | Score | Annotations | Remarques | Appreciation | graded_at |
| --- | --- | --- | --- | --- | --- | --- |
| 4C9D-001 | IN_PROGRESS | present | 10 | 22 | longueur 295 | None |
| 4C9D-003 | IN_PROGRESS | present | 11 | 22 | longueur 333 | None |

Etat apres creation participative:

| Copie | Statut | Score | Annotations | Remarques | Appreciation | graded_at |
| --- | --- | --- | --- | --- | --- | --- |
| 4C9D-001 | IN_PROGRESS | present | 10 | 22 | longueur 295 | None |
| 4C9D-003 | IN_PROGRESS | present | 11 | 22 | longueur 333 | None |

Conclusion: valeurs strictement identiques sur les champs controles. Les corrections officielles deja commencees n'ont pas ete modifiees.

## 15. Tests lances et resultats

Local:

```bash
cd backend && ../venv/bin/python manage.py check --settings=core.settings_test
cd backend && ../venv/bin/python manage.py test grading.tests.test_peer_review --settings=core.settings_test
cd frontend && npm run build
```

Resultats:

- Django check: OK
- Tests cibles PeerReview: 6 tests, OK
- Build Vite: OK, avec warnings existants de chunking dynamique/statique.

Production lecture seule:

- API eleve liste: HTTP 200, 1 correction retournee.
- API eleve detail: HTTP 200, aucune cle d'identite auteur (`student`, `author`, `source_student`, `student_email`, `author_email`) retournee.
- API enseignant liste: HTTP 200, 23 corrections retournees.
- API enseignant detail: HTTP 200 sur `4C9D-001`.

## 16. Build frontend/backend

- Frontend local build: `npm run build` OK.
- Frontend deploye par copie du `frontend/dist` vers `/var/www/labomaths/korrigo/frontend`.
- Backend image construite en production: `ghcr.io/cyranoaladin/korrigo-backend:peer-review-20260525`.
- Nginx image existante retaggee pour le meme tag: `ghcr.io/cyranoaladin/korrigo-nginx:peer-review-20260525`.

Corrections de coherence du contexte build production:

- alignement `students/views.py` pour conserver `AdminResetStudentPasswordView`;
- alignement `grading/views.py` pour conserver `CopyScoreCorrectionView`;
- ajout du package `bilan` et `bilan/services` dans l'image backend afin que Celery importe les memes modules que le backend HTTP;
- alignement `core/auth.py` pour `DIRECTION_GROUPS`.

## 17. Deploiement et redemarrage

- `.env` sauvegarde: `/var/www/labomaths/korrigo/.env.before_peer_review_20260525_221929`
- `KORRIGO_SHA` bascule de `c0f0b4905c9607dace1d92fbd49d3f6ebb785d84` vers `peer-review-20260525`.
- Redemarrage via Docker Compose:
  - `backend`
  - `celery`
  - `celery-beat`
  - `nginx`
- Migrations appliquees avant creation des corrections participatives.
- Verification HTTPS: `https://korrigo.labomaths.tn` repond HTTP 200.
- Verification API sante: `{"status":"healthy","database":"connected"}`.
- Etat final conteneurs: `backend`, `celery`, `celery-beat`, `db`, `nginx`, `redis` healthy.

Correction annexe non destructive:

- Healthcheck `celery-beat` corrige dans `/var/www/labomaths/korrigo/docker-compose.prod.yml`.
- Sauvegardes compose:
  - `/var/www/labomaths/korrigo/docker-compose.prod.yml.before_peer_review_health_20260525_222909`
  - `/var/www/labomaths/korrigo/docker-compose.prod.yml.before_peer_review_health2_20260525_223051`

## 18. Points a valider manuellement

- Connexion reelle avec un compte eleve en navigateur pour verifier l'ergonomie complete du desk participatif.
- Connexion reelle avec le compte enseignant `alaeddine.benrhouma@ert.tn` pour valider l'affichage dashboard et l'ouverture de corrections participatives.
- Verification visuelle responsive mobile/tablette si les eleves utilisent ces appareils en classe.
- Les corrections participatives sont creees et disponibles, mais aucune correction eleve n'a ete finalisee pendant l'intervention afin de ne pas introduire de donnees pedagogiques fictives.

## Validation responsive mobile

Intervention du 2026-05-26, limitee au frontend/UX.

Fichiers modifies:

- `frontend/src/views/peer/PeerReviewDesk.vue`
- `frontend/src/views/student/ResultView.vue`
- `frontend/src/views/CorrectorDashboard.vue`

Changements principaux:

- correction du rendu mobile de `PeerReviewDesk`: les onglets mobiles ne masquent plus le contenu principal;
- ajout des computed `isTeacherMode` et `canEdit` utilises par le desk;
- organisation mobile en onglets `Copie`, `Bareme`, `Remarques`, `Appreciation`;
- barre d'action mobile sticky avec total, `Enregistrer`, `Finaliser`, feedback de sauvegarde et safe-area iOS;
- champs numeriques et textareas en 16px pour eviter le zoom automatique iOS;
- boutons tactiles a 44px minimum;
- copie affichee en pleine largeur, sans overflow horizontal;
- barème sous forme de cartes avec champ points et remarque courte;
- section eleve `Corrections participatives` lisible en carte mobile;
- tableau enseignant des corrections participatives converti en cartes sous 900px.

Breakpoints couverts:

- `@media (max-width: 900px)`
- `@media (max-width: 768px)`
- `@media (max-width: 600px)`
- `@media (max-width: 430px)`
- `@media (max-width: 375px)`

Viewports verifies avec Playwright:

- 375 x 667: iPhone SE
- 390 x 844: iPhone standard
- 414 x 896: iPhone Plus
- 430 x 932: iPhone Pro Max
- 768 x 1024: tablette portrait

Verification Playwright effectuee:

- dashboard eleve: section `Corrections participatives` visible;
- bouton `Ouvrir` tactile et visible;
- desk participatif: onglets visibles;
- onglet `Copie`: pages en pleine largeur, pas d'overflow horizontal;
- onglet `Bareme`: cartes visibles, saisie d'une note possible;
- remarque courte saisissable;
- onglet `Appreciation`: textarea saisissable;
- boutons `Enregistrer` et `Finaliser` visibles avec zone tactile suffisante;
- captures generees localement dans `/tmp/korrigo-<viewport>-*.png`.
- meme scenario rejoue apres deploiement sur `https://korrigo.labomaths.tn` avec API mockee cote navigateur pour verifier les assets frontend deployes.

Commandes executees:

```bash
cd frontend && npm run build
cd frontend && npm run lint
cd frontend && npm run typecheck
cd frontend && npm run test -- --run
cd /home/alaeddine/.agents/skills/playwright && node run.js /tmp/korrigo-peer-mobile-check.js
```

Resultats:

- `npm run build`: OK.
- `npm run lint`: OK, 0 erreur, avertissements de style existants.
- `npm run typecheck`: OK.
- `npm run test -- --run`: 26 fichiers, 332 tests, OK.
- Playwright responsive: OK sur les 5 viewports.
- Playwright responsive production: OK sur les 5 viewports.

Deploiement frontend mobile:

- sauvegarde production avant remplacement: `/var/backups/korrigo/korrigo_frontend_before_peer_mobile_20260526_063603.tar.gz`;
- build `frontend/dist` copie vers `/var/www/labomaths/korrigo/frontend`;
- rapport synchronise vers `/var/www/labomaths/korrigo/docs/peer-review-produit-scalaire-g6.md`;
- verification production apres deploiement:
  - `https://korrigo.labomaths.tn`: HTTP 200;
  - `/api/health/`: `{"status":"healthy","database":"connected"}`;
  - conteneurs `backend`, `celery`, `celery-beat`, `db`, `nginx`, `redis`: healthy;
  - `PeerReviewCorrection` examen: 23;
  - `4C9D-001`: `IN_PROGRESS`, score present, 10 annotations, 22 remarques, appreciation longueur 295, `graded_at=None`;
  - `4C9D-003`: `IN_PROGRESS`, score present, 11 annotations, 22 remarques, appreciation longueur 333, `graded_at=None`.

Points restant a valider manuellement:

- test final avec un vrai compte eleve sur iPhone/Safari;
- test final avec le compte enseignant sur un telephone si usage enseignant mobile prevu;
- finalisation reelle par un eleve volontaire, hors intervention technique, pour ne pas creer de donnee pedagogique fictive.

## Audit qualite et correctifs 2026-05-26

Corrections backend:

- serializers_peer_review.py: elimination du N+1 query dans `get_source_media()` en utilisant le cache prefetch au lieu de `.all().order_by()`.
- views_peer_review.py: validation des `question_id` des remarques contre le bareme de l'examen; les IDs invalides sont ignores silencieusement.
- views_peer_review.py: erreurs de validation d'annotations retournent HTTP 400 avec detail au lieu de 500 non gere.
- views_peer_review.py: documentation de `_event_actor()` pour clarifier le fallback session-based auth.
- views_media.py: exception `except Exception` remplacee par `except (ImportError, ValueError, TypeError)`.
- test_peer_review.py: ajout du test `test_finalize_idempotent_returns_400_on_second_call`, portant le total a 7 tests.

Corrections frontend:

- PeerReviewDesk.vue: nettoyage du `setTimeout` de saveSuccess dans `onBeforeUnmount` pour eviter fuite memoire.
- PeerReviewDesk.vue: icones corrigees (`check-circle` → `check-circle-2`, `alert-circle` → `alert`) pour correspondre au registre.
- PeerReviewDesk.vue: ajout `aria-label` et `aria-pressed` sur les boutons de la barre d'outils d'annotation.
- CorrectorDashboard.vue: suppression du ref `peerReviewsLoading` inutilise.

Verification post-deploiement:

- `npm run build`: OK.
- 7 tests backend peer review: OK.
- Production: API health OK, conteneurs healthy.
- 4C9D-001: IN_PROGRESS, score present, 10 annotations, 22 remarques, appreciation 295, graded_at=None.
- 4C9D-003: IN_PROGRESS, score present, 11 annotations, 22 remarques, appreciation 333, graded_at=None.
- 23 PeerReviewCorrection presentes, 0 alteration officielle.

## Correctif anonymisation media des corrections participatives 2026-05-26

Cause racine:

- l'API detail eleve des corrections participatives renvoyait les medias bruts de la copie source (`Booklet.pages_images`) ainsi que les URLs potentielles `pdf_source_url` et `final_pdf_url`;
- les permissions media autorisaient aussi l'eleve assigne a une correction participative a acceder aux pages brutes et au PDF source de la copie;
- pour la copie attribuee a `sami.siala-e@ert.tn`, le PDF source etait `exams/individual/MNIF_LINA_24022009.pdf`, ce qui exposait une identite dans le nom de fichier et potentiellement dans le haut de page du document.

Correctif applique:

- ajout de `backend/grading/peer_review_media.py` pour centraliser les chemins media anonymises `peer_reviews/anonymized/<copy_id>/...`;
- modification de `backend/grading/serializers_peer_review.py`: le detail eleve ne renvoie plus que les pages anonymisees dediees aux corrections participatives; `pdf_source_url` et `final_pdf_url` sont toujours `None` dans ce contexte;
- modification de `backend/core/views_media.py`: un eleve correcteur participatif ne peut acceder qu'aux fichiers sous `peer_reviews/anonymized/<source_copy_id>/`; l'acces aux `copies/pages/...`, `exams/individual/...`, `pdf_source` et `final_pdf` bruts est refuse;
- ajout de la commande `backend/grading/management/commands/generate_peer_review_anonymized_media.py`, idempotente, qui cree des images separees avec masquage du haut de page, sans modification de base de donnees.

Sauvegarde production:

- sauvegarde code avant remplacement: `/var/backups/korrigo/peer_review_media_code_before_20260526_073440.tar.gz`.

Commandes executees:

```bash
cd backend && ../venv/bin/python manage.py test grading.tests.test_peer_review --settings=core.settings_test
cd backend && ../venv/bin/python manage.py check --settings=core.settings_test
ssh root@88.99.254.59 'docker exec docker-backend-1 bash -lc "python manage.py check"'
ssh root@88.99.254.59 'docker restart docker-backend-1'
ssh root@88.99.254.59 'docker exec docker-backend-1 bash -lc "python manage.py generate_peer_review_anonymized_media --exam-id 4c9dfd06-72fc-47b4-ad11-b63dba655076 --dry-run"'
ssh root@88.99.254.59 'docker exec docker-backend-1 bash -lc "python manage.py generate_peer_review_anonymized_media --exam-id 4c9dfd06-72fc-47b4-ad11-b63dba655076"'
```

Resultats:

- tests backend peer review: 9 tests OK;
- `manage.py check`: OK en local et en production;
- dry-run: 23 corrections participatives detectees, aucune suppression, aucune ecriture DB;
- generation reelle: 180 pages anonymisees creees sous `/app/media/peer_reviews/anonymized`;
- controle global API: 23 corrections participatives verifiees, 0 echec;
- chaque detail eleve retourne uniquement des URLs `peer_reviews/anonymized/...`;
- aucun detail eleve ne retourne `copies/pages`, `exams/individual`, `pdf_source_url` ou `final_pdf_url`.

Controle specifique `sami.siala-e@ert.tn`:

- correction participative assignee: copie anonymisee `4C9D-023`;
- detail API: HTTP 200;
- pages renvoyees: 8;
- premier media renvoye: `https://korrigo.labomaths.tn/api/media/peer_reviews/anonymized/d71f79d7-5a52-48aa-83d0-1b8ebaa6ffdb/p000.png?...`;
- `pdf_source_url`: `None`;
- `final_pdf_url`: `None`;
- absence confirmee dans la reponse: `copies/pages`, `exams/individual`, `MNIF`, `LINA`, `24022009`, `lina.mnif-e@ert.tn`;
- permission media: page anonymisee HTTP 200 avec `X-Accel-Redirect`;
- permission media: page brute `copies/pages/...` HTTP 403;
- permission media: PDF source `exams/individual/MNIF_LINA_24022009.pdf` HTTP 403.

Verification non-alteration officielle:

- aucune commande de generation n'ecrit dans `Copy`, `Score`, `Annotation`, `QuestionRemark` ou `GradingEvent`;
- `4C9D-001`: `IN_PROGRESS`, 1 score, 10 annotations, 22 remarques, appreciation longueur 295, PDF source conserve;
- `4C9D-003`: `IN_PROGRESS`, 1 score, 11 annotations, 22 remarques, appreciation longueur 333, PDF source conserve.

Point de vigilance:

- le masquage applique le haut de page des images generees pour la correction participative; si une copie contient une identite manuscrite ailleurs dans la page, une verification visuelle ponctuelle reste recommandee avant usage en classe.
