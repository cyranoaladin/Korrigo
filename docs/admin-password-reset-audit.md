# Audit interface admin de réinitialisation de mot de passe

Date : 2026-05-26

## Périmètre

Audit des flux de réinitialisation de mot de passe accessibles depuis l'interface admin :

- gestion des utilisateurs : `frontend/src/views/admin/UserManagement.vue`
- liste des élèves d'un examen : `frontend/src/views/admin/ExamStudentList.vue`
- API utilisateur : `POST /api/users/<id>/reset-password/`
- API élève : `POST /api/students/admin/reset-password/`

## Diagnostic

Le backend est correctement séparé :

- `backend/core/views.py` / `UserResetPasswordView`
  - permission `IsKorrigoAdmin`
  - interdit à un admin de réinitialiser son propre mot de passe
  - génère un mot de passe temporaire côté serveur
  - force `UserProfile.must_change_password = True`
  - ne retourne pas le mot de passe dans la réponse API

- `backend/students/views.py` / `AdminResetStudentPasswordView`
  - permission `IsKorrigoAdmin`
  - exige un élève lié à un `User`
  - exige une date de naissance
  - réinitialise le mot de passe à la date de naissance au format `JJMMAAAA`
  - force `UserProfile.must_change_password = True`
  - ne retourne pas le mot de passe dans la réponse API

Défaut trouvé côté frontend :

- `ExamStudentList.vue` lisait encore `res.data.new_password`
- l'API ne renvoie volontairement plus `new_password`
- l'alerte affichait donc `Nouveau mot de passe: undefined`
- ce message était incohérent avec le contrat sécurité de non-exposition des secrets

## Correctif appliqué

Fichier modifié :

- `frontend/src/views/admin/ExamStudentList.vue`
- `frontend/src/views/admin/UserManagement.vue`
- `frontend/src/components/admin/PasswordResetDialog.vue`

Correction :

- suppression de la lecture de `res.data.new_password`
- remplacement des `confirm()` / `alert()` des resets par une modale applicative
- états confirmation, chargement, succès et erreur dans l'interface
- message de succès aligné entre gestion utilisateurs et liste élèves d'examen
- rappel explicite qu'aucun mot de passe n'est affiché dans l'interface
- aucune modification backend
- aucune modification de base de données

## Tests ajoutés

Backend :

- `backend/tests/test_security_fixes.py`
  - vérifie que le reset utilisateur change le hash de mot de passe
  - vérifie `must_change_password = True`
  - vérifie que la réponse ne contient ni `password`, ni `temporary_password`
  - vérifie que le reset élève met bien le mot de passe au format date de naissance `JJMMAAAA`
  - vérifie `must_change_password = True`
  - vérifie que la réponse ne contient ni `new_password`, ni `temporary_password`

Frontend unitaires :

- `frontend/tests/unit/AdminPasswordReset.test.ts`
  - workflow reset élève depuis la liste d'examen
  - workflow reset enseignant depuis la gestion utilisateurs
  - vérifie les endpoints appelés
  - vérifie l'ouverture de la modale applicative
  - vérifie l'absence d'appel à `window.confirm()` et `window.alert()`
  - vérifie l'absence de `new_password`, `temporary_password` et `undefined` dans l'interface

E2E :

- `frontend/tests/e2e/admin-password-reset-ui.spec.ts`
  - navigation réelle vers `/admin/exams/exam-123/results`
  - routage admin authentifié mocké
  - API mockée pour `/api/exams/exam-123/student-list/`
  - POST réel côté navigateur vers `/api/students/admin/reset-password/`
  - validation de la modale applicative et du message de succès sans secret affiché

## Résultats de validation

Backend :

```bash
cd backend
../venv/bin/python manage.py test tests.test_security_fixes core.tests.test_email_login_reset core.tests.test_admin_gate_remediation --settings=core.settings_test
```

Résultat :

- 43 tests exécutés
- OK

Frontend unitaires :

```bash
cd frontend
npm run test -- --run tests/unit/AdminPasswordReset.test.ts tests/unit/PasswordResetViews.test.ts tests/unit/ChangePasswordModal.test.ts
```

Résultat :

- 3 fichiers passés
- 7 tests passés

Workflows :

```bash
cd frontend
npm run test -- --run tests/workflows/navigation.test.ts tests/workflows/correction-workflow.test.ts
```

Résultat :

- 2 fichiers passés
- 40 tests passés

Build :

```bash
cd frontend
npm run build
```

Résultat :

- build Vite réussi
- avertissements de chunking existants sur les imports dynamiques/statics de `auth.js` et `router/index.js`

E2E :

```bash
cd frontend
npx playwright install chromium
npm run dev -- --host 127.0.0.1 --port 8088
E2E_BASE_URL=http://127.0.0.1:8089 npx playwright test tests/e2e/admin-password-reset-ui.spec.ts --project=tablet
```

Note : le port `8088` était occupé localement, Vite a démarré sur `8089`.

Résultat :

- 1 test Playwright passé

Lint :

```bash
cd frontend
npm run lint
npm run lint -- --quiet
```

Résultat :

- code de sortie 0
- 0 erreur
- avertissements de style préexistants

## Garanties confirmées

- le backend ne retourne pas les mots de passe générés
- l'interface admin n'affiche plus de mot de passe ni `undefined`
- seuls les admins Korrigo peuvent appeler les endpoints audités
- un admin ne peut pas réinitialiser son propre mot de passe via `UserResetPasswordView`
- le reset force le changement de mot de passe à la prochaine connexion
- les flux admin audités n'utilisent plus `confirm()` / `alert()`
- aucun modèle de correction, copie, score, annotation ou barème n'a été modifié

## Points de vigilance

- `UserResetPasswordView` ignore silencieusement une exception lors de la mise à jour de `UserProfile`. Les tests actuels couvrent le chemin nominal ; une amélioration future pourrait rendre cette erreur explicite côté logs applicatifs.
