# Korrigo Lots A-B-C Design

**Contexte**

Korrigo est en production active. Le travail doit donc minimiser les régressions sur les copies, annotations, notes, élèves, correcteurs et flux d'authentification.

**Découpage validé**

Le travail est découpé en trois lots séquentiels:

1. Lot A: sécurité et cohérence backend
2. Lot B: nouvelles capacités backend
3. Lot C: intégration frontend

**Lot A**

Objectif: corriger uniquement les écarts de sécurité et de cohérence encore présents dans le dépôt, sans toucher aux zones déjà corrigées.

Portée:
- permissions déclaratives admin-only sur les vues de remédiation grading
- suppression des checks inline redondants
- durcissement du login étudiant pour ne jamais planter sur la recherche par email
- réalignement du groupe `questionnaire_coordinator`
- tests de non-régression ciblés

Contraintes:
- respecter les patterns `permission_classes`
- ne pas casser la production ni les migrations déjà appliquées, sauf le cas explicitement demandé sur la migration `0004`

**Lot B**

Objectif: ajouter des fonctionnalités backend sans dégrader les workflows existants.

Portée:
- notification email asynchrone lors de la publication des résultats
- endpoint admin `global-stats` agrégé SQL
- endpoints JSON de reset password
- export JSON des annotations par copie et par examen
- audit et tests API associés

Choix:
- réponse rapide pour la publication des résultats, avec tâche Celery asynchrone
- exports déterministes en JSON d'abord
- réponses publiques non révélatrices pour le reset password

**Lot C**

Objectif: brancher le frontend sur les nouvelles API sans refonte structurelle.

Portée:
- `AdminOverview.vue` consomme `global-stats`
- vues publiques `ForgotPassword` et `ResetPasswordConfirm`
- lien depuis `Login.vue`
- export annotations depuis la vue admin des copies
- indicateur de complétion dans `CorrectorDesk.vue`

Choix UX:
- avertissement ou confirmation forte avant finalisation incomplète dans `CorrectorDesk`, pas de verrouillage absolu au premier passage

**Validation**

Chaque lot sera validé séparément:
- lot A: tests backend ciblés + checks migrations
- lot B: tests backend ciblés + tâches/exports
- lot C: tests frontend ciblés + vérification d'intégration
