# Correction participative - Produit scalaire G6

Ce document de release décrit le mécanisme sans données personnelles. Les preuves nominatives et les journaux de production restent hors dépôt.

## Objectif

Ajouter un dispositif parallèle de correction participative par les élèves, sans modifier les copies ni corrections officielles.

Garanties:

- aucune écriture dans les tables officielles de correction pendant l'activité élève;
- aucune identité de l'auteur de la copie retournée côté élève;
- médias élève servis uniquement depuis les exports anonymisés `peer_reviews/anonymized/`;
- commande d'assignation idempotente et compatible `--dry-run`;
- correcteur superviseur fourni par argument ou variable d'environnement, jamais hardcodé dans le code source.

## Backend

Modèles ajoutés dans `grading`:

- `PeerReviewCorrection`
- `PeerReviewAnnotation`
- `PeerReviewQuestionRemark`
- `PeerReviewEvent`

Migration:

- `grading.0027_peerreviewcorrection_peerreviewevent_and_more`

Commande:

```bash
python manage.py create_peer_review_produit_scalaire_g6 --dry-run \
  --supervising-teacher-email teacher@example.test
```

La commande valide l'examen cible, le nombre de copies attendu, la présence des élèves, l'existence des comptes utilisateurs, l'absence d'auto-correction et l'idempotence des affectations.

## Frontend

Fichiers principaux:

- `frontend/src/services/peerReviewApi.js`
- `frontend/src/router/index.js`
- `frontend/src/views/peer/PeerReviewDesk.vue`
- `frontend/src/views/student/ResultView.vue`
- `frontend/src/views/CorrectorDashboard.vue`

## Tests

Tests ciblés:

- `backend/grading/tests/test_peer_review.py`
- `frontend/tests/e2e/admin-password-reset-ui.spec.ts`
- `frontend/tests/unit/AdminPasswordReset.test.ts`

Les tests utilisent exclusivement des comptes factices de domaine `example.test`.
