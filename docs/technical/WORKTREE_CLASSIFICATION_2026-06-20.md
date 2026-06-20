# Classification du worktree sale avant reconciliation

Date UTC: 2026-06-20T13:45Z
Snapshot: `wip/worktree-20260620` `41765243f558b5466d71edfe25c6117acc16717f`

Objectif: decider ce qui entre dans `release/reconcile` sans embarquer de donnees ni de rebut.

Legende:
- `A` = fonctionnalite/correctif a integrer dans la release reconciliee.
- `B` = correctif deja present ou lie au runtime prod par overlay/hotfix, a reconcilier dans la source canonique.
- `C` = rebut ou changement a exclure de la release tant qu'il n'est pas justifie par staging.

## Decisions par fichier

| Fichier | Statut | Classe | Decision release/reconcile |
|---|---:|---:|---|
| `.gitignore` | M | A | Integrer. Garde-fou contre dumps, medias, exports JSON et dossiers de restauration. |
| `ASSAINISSEMENT_KORRIGO.md` | A | A | Integrer. Document de pilotage et journal des preuves. |
| `backend/core/views_media.py` | M | A | Integrer. Necessaire pour acces media peer-review et alignement visibilite resultats. Tester permissions media. |
| `backend/exams/migrations/0042_copy_pdf_regeneration_pending_db_default.py` | A | A | Integrer seulement apres decision C: migration non appliquee prod, mais schema live a deja le default SQL `false`. |
| `backend/exams/tests/test_schema_defaults.py` | A | A | Integrer avec 0042. Prouve le default DB attendu. |
| `backend/exams/tests/test_upload_endpoint.py` | M | A/B | Integrer si le flux import individuel est retenu. Couvre le hotfix import PDF present aussi dans overlays locaux. |
| `backend/exams/views.py` | M | A/B | Integrer. Correctif import individuel: accepte l'endpoint explicite, rasterise, cree booklet/pages et event import. |
| `backend/grading/management/commands/create_peer_review_produit_scalaire_g6.py` | A | A | Integrer comme commande d'initialisation cible, mais verifier absence de dependance a donnees nominatives hardcodees avant release. |
| `backend/grading/management/commands/generate_peer_review_anonymized_media.py` | A | A | Integrer. Necessaire a la generation media anonymisee peer-review. |
| `backend/grading/migrations/0027_peerreviewcorrection_peerreviewevent_and_more.py` | A | A | Integrer. Migration peer-review deja appliquee en prod d'apres audit/restauration. |
| `backend/grading/models.py` | M | A | Integrer. Modeles peer-review. |
| `backend/grading/peer_review_media.py` | A | A | Integrer. Helpers media anonymises. |
| `backend/grading/serializers_peer_review.py` | A | A | Integrer. API peer-review. |
| `backend/grading/tests/test_peer_review.py` | A | A | Integrer. Tests cibles peer-review. |
| `backend/grading/urls.py` | M | A | Integrer. Routes enseignant peer-review. |
| `backend/grading/views_peer_review.py` | A | A | Integrer. Vues peer-review. |
| `backend/identification/migrations/0001_initial.py` | D | C | Exclure. Suppression dangereuse d'une migration appliquee en prod; a restaurer dans release. |
| `backend/identification/migrations/__init__.py` | D | C | Exclure. Package migrations requis. |
| `backend/students/urls.py` | M | A | Integrer. Routes eleve peer-review. |
| `backend/students/views.py` | M | A | Integrer. Ajustement rate-limit login eleve pour usage classe. A verifier avec nginx. |
| `backend/tests/test_security_fixes.py` | M | A | Integrer. Tests reset password sans fuite de secret et force change. |
| `docs/admin-password-reset-audit.md` | A | A | Integrer. Documentation du correctif reset password. |
| `docs/peer-review-produit-scalaire-g6.md` | A | A | Integrer apres redaction/verification: documentation peer-review sans donnees sensibles. |
| `frontend/public/images/Korrigo.png` | D | C | Exclure de release 2. Suppression d'assets publics sans lien direct avec reconciliation. |
| `frontend/public/images/favicon-32.png` | D | C | Exclure. |
| `frontend/public/images/favicon-64.png` | D | C | Exclure. |
| `frontend/public/images/favicon.ico` | D | C | Exclure. |
| `frontend/public/images/favicon.png` | D | C | Exclure. |
| `frontend/public/images/logo_korrigo_pmf.png` | D | C | Exclure. |
| `frontend/public/images/logo_korrigo_pmf.svg` | D | C | Exclure. |
| `frontend/src/components/ImportCopiesModal.vue` | A | A | Integrer. UI import batch/individuel alignee avec backend import. |
| `frontend/src/components/admin/PasswordResetDialog.vue` | A | A | Integrer. UI reset password sans affichage du mot de passe. |
| `frontend/src/router/index.js` | M | A | Integrer. Routes peer-review/admin selon diff. |
| `frontend/src/services/peerReviewApi.js` | A | A | Integrer. Client API peer-review. |
| `frontend/src/views/CorrectorDashboard.vue` | M | A | Integrer. Entree UI peer-review/import selon diff. |
| `frontend/src/views/admin/CorrectorDesk.vue` | M | A | Integrer si tests correcteur OK. |
| `frontend/src/views/admin/ExamCopies.vue` | M | A | Integrer. Ouverture import copies. |
| `frontend/src/views/admin/ExamStudentList.vue` | M | A | Integrer. UI reset password eleve. |
| `frontend/src/views/admin/UserManagement.vue` | M | A | Integrer. UI reset password utilisateur. |
| `frontend/src/views/peer/PeerReviewDesk.vue` | A | A | Integrer. Experience eleve peer-review. |
| `frontend/src/views/student/ResultView.vue` | M | A | Integrer seulement si regression visuelle acceptee: simplifie le titre resultats. Tester parcours eleve. |
| `frontend/tests/e2e/admin-password-reset-ui.spec.ts` | A | A | Integrer. E2E reset password. |
| `frontend/tests/unit/AdminPasswordReset.test.ts` | A | A | Integrer. Unit UI reset password. |
| `infra/nginx/nginx.conf` | M | A | Integrer en staging uniquement. Ajuste rate limits et headers `/api/media/`; prod active non modifiee a cette etape. |
| `overlay/backend/exams/views.py` | M | C | Exclure de release finale. Source canonique doit etre `backend/exams/views.py`; overlay sert seulement de preuve temporaire. |
| `overlay/exams/views.py` | M | C | Exclure de release finale. Doublon overlay non canonique. |
| `overlay/students/urls.py` | M | C | Exclure de release finale. Doublon overlay non canonique. |

## Donnees locales exclues

`DS_NSI_Premiere_Algo/` reste local et ignore par Git. Le dossier contient des PDFs/CSV nominatifs; il ne doit pas entrer dans `release/reconcile`.

## Base recommandee pour `release/reconcile`

Base: `origin/main` + selection explicite des classes `A` et `B`, en restaurant les fichiers classes `C` a leur etat `origin/main`.

Raison: le snapshot `41765243` conserve tout le travail, mais contient aussi des suppressions d'assets et migrations non justifiees. La release doit etre reconstructible et minimale.
