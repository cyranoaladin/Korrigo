# Porte 5D - HMAC admin activation and migration email sanitization - 2026-06-23

## Contexte

La Porte 5B a migre le gate anti-PII vers HMAC/pepper, sans marqueurs reels.
La Porte 5C a reduit les emails prioritaires :

- `SECRET_LIKE` : 32 -> 0;
- `TO_REVIEW` : 20 -> 19;
- les 19 restants etaient dans des migrations historiques.

Objectif Porte 5D :

1. activer les marqueurs HMAC reels si les entrees administrateur sont
   disponibles;
2. sinon, poursuivre l'assainissement des migrations historiques restantes sans
   exposer d'email ou de valeur PII.

## Preflight

Etat local :

- branche : `hotfix/lot0-rgpd-deploy-clean`;
- HEAD initial : `96cb50787053071fb131d9cc671a9c0667ced5ed`.

Production, lecture seule :

- host : `korrigo`;
- Compose canonique seul OK;
- services healthy;
- health public : `{"status":"healthy","database":"connected"}`.

Aucune action production n'a ete executee.

## HMAC

Prerequis administrateur :

```text
PII_INPUT_EXISTS=NO
PII_GATE_PEPPER_PRESENT=NO
```

La generation des marqueurs HMAC reels n'a donc pas ete faite. Aucun pepper,
aucune valeur source et aucun fichier d'entree sensible n'ont ete affiches ou
commites.

Verdict HMAC :

`WAIT_ADMIN_INPUT_OR_PEPPER`

Le gate reste operationnel en mode mecanisme, mais sans marqueurs reels :

- `DENY_HMACS` present;
- `DENY_HASHES` absent;
- fail-closed si `PII_GATE_PEPPER` est absent.

## Test de detection reel

Non realise, car il necessite :

- `/tmp/korrigo_pii_hmac_input_values.txt`;
- `PII_GATE_PEPPER`.

Ces elements doivent etre fournis hors depot par l'administrateur.

## Migration emails

Migrations historiques traitees :

- `backend/core/migrations/0004_questionnaire_coordinator_group.py`;
- `backend/exams/migrations/0031_seed_copy_constraints_and_teacher_groups.py`;
- `backend/exams/migrations/0034_seed_premiere_groups.py`.

Remplacements effectues :

```text
backend/core/migrations/0004_questionnaire_coordinator_group.py: 1 valeur unique
backend/exams/migrations/0031_seed_copy_constraints_and_teacher_groups.py: 9 valeurs uniques
backend/exams/migrations/0034_seed_premiere_groups.py: 7 valeurs uniques
```

Les adresses historiques ont ete remplacees par des adresses reservees
`example.test`, de maniere coherente par fichier. Les anciennes valeurs n'ont pas
ete affichees.

## Classifieur email

`scripts/audit/classify_plain_emails_redacted.py` a ete mis a jour pour
distinguer les migrations assainies :

- migration avec uniquement des domaines reserves -> `SANITIZED_MIGRATION_FIXTURE`;
- migration avec domaine non reserve -> `TO_REVIEW`.

Classification avant Porte 5D :

```text
EMAIL_CLASSIFICATION_FILE_COUNT=100
EMAIL_CLASSIFICATION_TOTAL_OCCURRENCES=453
EMAIL_CATEGORY_DOC_EXAMPLE=9
EMAIL_CATEGORY_PUBLIC_INSTITUTIONAL=69
EMAIL_CATEGORY_TEST_FIXTURE=356
EMAIL_CATEGORY_TO_REVIEW=19
```

Classification apres Porte 5D :

```text
EMAIL_CLASSIFICATION_FILE_COUNT=100
EMAIL_CLASSIFICATION_TOTAL_OCCURRENCES=453
EMAIL_CATEGORY_DOC_EXAMPLE=9
EMAIL_CATEGORY_PUBLIC_INSTITUTIONAL=69
EMAIL_CATEGORY_SANITIZED_MIGRATION_FIXTURE=19
EMAIL_CATEGORY_TEST_FIXTURE=356
```

Resultat :

- `SECRET_LIKE=0`;
- `TO_REVIEW=0`;
- `SANITIZED_MIGRATION_FIXTURE=19`.

## Verifications

Gates avec pepper synthetique :

```text
frontend/src: PII_GATE_STATUS=PASS, PII_HASH_MATCH_COUNT=0
frontend/dist: PII_GATE_STATUS=PASS, PII_HASH_MATCH_COUNT=0
```

Fail-closed sans pepper :

```text
PII_GATE_STATUS=FAIL_MISSING_PEPPER
PII_HASH_MATCH_COUNT=0
```

Tests backend :

```text
42 passed
1007 passed, 1 skipped, 3 deselected
```

Frontend :

```text
27 files passed
334 tests passed
vite build OK
```

## Confirmations

- Aucun push GitHub.
- Aucune PR.
- Aucun workflow GitHub.
- Aucun GHCR.
- Aucun build Docker.
- Aucun deploiement.
- Aucun redemarrage applicatif.
- Aucune migration appliquee en production.
- Aucun secret affiche.
- Aucun pepper affiche.
- Aucune valeur PII affichee.
- Aucun email reel affiche.
- Aucun fichier d'entree sensible commite.

## Verdict

`PORTE5D_PARTIAL_EMAILS_DONE_WAIT_HMAC_ADMIN`

La dette email prioritaire hors bundle est assainie. L'activation HMAC reelle
reste bloquee par absence des entrees administrateur.

## Prochaine etape

Fournir hors depot :

- `/tmp/korrigo_pii_hmac_input_values.txt`;
- `PII_GATE_PEPPER`.

Puis relancer uniquement la sous-etape d'activation HMAC reelle. Si ces
elements ne sont pas disponibles, la prochaine piste est la strategie
Git/main prive et integration controlee.
