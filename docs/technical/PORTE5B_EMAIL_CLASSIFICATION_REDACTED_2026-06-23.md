# Porte 5B - Email classification redacted - 2026-06-23

## Objectif

Classifier les occurrences d'emails hors bundle sans afficher les adresses.
Le scan couvre :

- `backend`;
- `scripts`;
- `docs`;
- `.github`;
- `frontend/src`.

Exclusions :

- `.git`;
- caches Python/pytest/ruff;
- environnements virtuels;
- `node_modules`;
- `dist`;
- fichiers binaires.

## Resultats agreges

```text
EMAIL_CLASSIFICATION_FILE_COUNT=100
EMAIL_CLASSIFICATION_TOTAL_OCCURRENCES=461
EMAIL_CATEGORY_DOC_EXAMPLE=9
EMAIL_CATEGORY_PUBLIC_INSTITUTIONAL=69
EMAIL_CATEGORY_SECRET_LIKE=32
EMAIL_CATEGORY_TEST_FIXTURE=331
EMAIL_CATEGORY_TO_REVIEW=20
```

Aucune adresse n'a ete affichee par le script. Les sorties sont limitees au
chemin du fichier, au nombre d'occurrences, a la categorie et a la justification.

## Categories

- `TEST_FIXTURE` : exemples ou donnees de tests, souvent sur domaines reserves.
- `DOC_EXAMPLE` : documentation avec exemples non operationnels.
- `PUBLIC_INSTITUTIONAL` : documentation semblant decrire des contacts publics
  ou institutionnels.
- `TO_REVIEW` : code runtime, migration ou script a verifier manuellement.
- `SECRET_LIKE` : contexte adjacent a des mots de passe/tokens/secrets, a
  verifier prioritairement meme si le script n'affiche pas les valeurs.

## Fichiers les plus charges

Les chemins ci-dessous ne contiennent pas d'adresse email en clair.

| Fichier | Occurrences | Categorie |
| --- | ---: | --- |
| `backend/students/tests/test_student_change_password.py` | 29 | `TEST_FIXTURE` |
| `backend/exams/tests/test_seed_initial_exams.py` | 21 | `TEST_FIXTURE` |
| `backend/students/tests/test_student_auth_birth_date.py` | 17 | `TEST_FIXTURE` |
| `backend/core/tests/test_email_login_reset.py` | 13 | `TEST_FIXTURE` |
| `backend/grading/tests/test_peer_review.py` | 13 | `TEST_FIXTURE` |
| `backend/test_full_audit.py` | 13 | `TEST_FIXTURE` |
| `backend/exams/migrations/0031_seed_copy_constraints_and_teacher_groups.py` | 11 | `TO_REVIEW` |
| `docs/security/GESTION_DONNEES.md` | 11 | `TEST_FIXTURE` |
| `docs/support/SUPPORT.md` | 10 | `TEST_FIXTURE` |
| `backend/exams/management/commands/seed_initial_exams.py` | 9 | `SECRET_LIKE` |

## Priorites de revue

1. Examiner les fichiers `SECRET_LIKE`, car ils sont dans un contexte adjacent a
   des secrets ou mots de passe.
2. Examiner les fichiers `TO_REVIEW`, surtout migrations et scripts runtime.
3. Confirmer que les `PUBLIC_INSTITUTIONAL` correspondent bien a des contacts
   publics assumables.
4. Laisser les `TEST_FIXTURE` seulement si les domaines sont reserves ou
   clairement synthetiques.

## Script

Script local ajoute :

`scripts/audit/classify_plain_emails_redacted.py`

Commande :

```bash
python scripts/audit/classify_plain_emails_redacted.py
```

Le script ne doit jamais afficher les adresses detectees.
