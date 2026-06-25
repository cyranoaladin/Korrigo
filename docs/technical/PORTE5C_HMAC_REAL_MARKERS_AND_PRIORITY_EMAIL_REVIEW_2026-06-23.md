# Porte 5C - HMAC real markers and priority email review - 2026-06-23

## Contexte

La Porte 5B a remplace le gate anti-PII par un mecanisme HMAC-SHA256 avec
pepper non commite. Son statut etait :

`HMAC_GATE_READY_NEEDS_ADMIN_REGENERATION`

La Porte 5C avait deux objectifs :

1. regenerer les vrais marqueurs HMAC a partir des anciennes valeurs sensibles,
   sans remettre ces valeurs dans le depot;
2. traiter en priorite les emails classes `SECRET_LIKE` et `TO_REVIEW`.

## Preflight

Etat local initial :

- branche : `hotfix/lot0-rgpd-deploy-clean`;
- HEAD initial : `d0f23ca022f73247022df619fc2511676c911de6`;
- worktree propre.

Production, lecture seule :

- host : `korrigo`;
- Compose canonique seul OK;
- services healthy;
- health public : `{"status":"healthy","database":"connected"}`.

Aucune action production n'a ete executee.

## Etat du gate HMAC

Controle structurel :

```text
HAS_DENY_HMACS=True
HAS_DENY_HASHES=False
HAS_PII_GATE_PEPPER=True
HAS_HMAC=True
DENY_HMAC_HEX_COUNT=0
MENTIONS_NEEDS_ADMIN_REGENERATION=True
```

Interpretation : le mecanisme HMAC est pret, mais aucun marqueur reel n'est
encore present dans le depot.

## Regeneration HMAC reelle

La regeneration reelle n'a pas pu etre faite dans ce tour, car les deux
prerequis administrateur etaient absents :

```text
PII_INPUT_EXISTS=NO
PII_GATE_PEPPER_PRESENT=NO
```

Le fichier attendu est hors depot :

`/tmp/korrigo_pii_hmac_input_values.txt`

Le pepper attendu doit etre fourni par variable d'environnement :

`PII_GATE_PEPPER`

Decision : `WAIT_ADMIN_INPUT` et `WAIT_ADMIN_PEPPER`.

La commande a utiliser par l'administrateur, sans mettre les valeurs dans Git :

```bash
export PII_GATE_PEPPER='<secret long genere hors depot>'
printf '%s\n' '<une valeur sensible par ligne>' > /tmp/korrigo_pii_hmac_input_values.txt
chmod 600 /tmp/korrigo_pii_hmac_input_values.txt
```

Le contenu exact ne doit jamais etre affiche, commite ou copie dans le depot.

## Emails prioritaires

Classification initiale Porte 5C :

```text
EMAIL_CLASSIFICATION_FILE_COUNT=100
EMAIL_CLASSIFICATION_TOTAL_OCCURRENCES=461
EMAIL_CATEGORY_DOC_EXAMPLE=9
EMAIL_CATEGORY_PUBLIC_INSTITUTIONAL=69
EMAIL_CATEGORY_SECRET_LIKE=32
EMAIL_CATEGORY_TEST_FIXTURE=331
EMAIL_CATEGORY_TO_REVIEW=20
```

Fichiers prioritaires identifies, sans afficher les adresses :

- `backend/core/management/commands/init_pmf.py`;
- `backend/core/migrations/0004_questionnaire_coordinator_group.py`;
- `backend/core/seed_prod.py`;
- `backend/core/views.py`;
- `backend/exams/management/commands/seed_initial_exams.py`;
- `backend/exams/migrations/0031_seed_copy_constraints_and_teacher_groups.py`;
- `backend/exams/migrations/0034_seed_premiere_groups.py`;
- `backend/scripts/archive/rebuild_full.py`;
- `backend/scripts/archive/rebuild_production.py`;
- `backend/seed_e2e.py`;
- `backend/students/management/commands/anonymize_student.py`;
- `scripts/verify_grading.py`.

## Corrections effectuees

Corrections sures appliquees :

- remplacement des emails d'exemple dans les scripts non-migration par des
  domaines reserves `example.test`;
- remplacement des libelles de correcteurs du seed initial par des noms
  synthetiques;
- mise a jour du test `test_seed_initial_exams` pour utiliser les constantes du
  seed au lieu d'une liste historique;
- commentaire runtime rendu generique sans adresse concrete.

Fichiers modifies :

- `backend/core/management/commands/init_pmf.py`;
- `backend/core/seed_prod.py`;
- `backend/core/views.py`;
- `backend/exams/management/commands/seed_initial_exams.py`;
- `backend/exams/tests/test_seed_initial_exams.py`;
- `backend/scripts/archive/rebuild_full.py`;
- `backend/scripts/archive/rebuild_production.py`;
- `backend/seed_e2e.py`;
- `backend/students/management/commands/anonymize_student.py`;
- `scripts/verify_grading.py`.

## Emails restants

Classification finale :

```text
EMAIL_CLASSIFICATION_FILE_COUNT=100
EMAIL_CLASSIFICATION_TOTAL_OCCURRENCES=453
EMAIL_CATEGORY_DOC_EXAMPLE=9
EMAIL_CATEGORY_PUBLIC_INSTITUTIONAL=69
EMAIL_CATEGORY_TEST_FIXTURE=356
EMAIL_CATEGORY_TO_REVIEW=19
```

Resultat :

- `SECRET_LIKE` : 32 -> 0;
- `TO_REVIEW` : 20 -> 19.

Les `TO_REVIEW` restants sont des migrations historiques :

- `backend/core/migrations/0004_questionnaire_coordinator_group.py`;
- `backend/exams/migrations/0031_seed_copy_constraints_and_teacher_groups.py`;
- `backend/exams/migrations/0034_seed_premiere_groups.py`.

Elles sont conservees pour eviter une modification risquee de migrations
historiques deja versionnees.

## Verifications

Gates HMAC avec pepper synthetique :

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
18 passed
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
- Aucun secret affiche.
- Aucun pepper affiche.
- Aucune valeur PII affichee.
- Aucun email reel affiche dans les rapports.

## Risques residuels

- Les vrais marqueurs HMAC restent a regenerer par l'administrateur hors depot.
- Les migrations historiques `TO_REVIEW` contiennent encore des emails et
  doivent etre traitees dans une strategie dediee si necessaire.
- Git/main reste non aligne avec la production.
- `BilanBacBlanc.vue` reste une dette structurelle.
- La CI publique reste inadaptee tant que le depot et les secrets ne sont pas
  gouvernes correctement.

## Prochaine etape

1. Fournir hors depot `/tmp/korrigo_pii_hmac_input_values.txt` et
   `PII_GATE_PEPPER`.
2. Relancer uniquement la sous-etape de regeneration HMAC reelle.
3. Definir une strategie pour les migrations historiques restantes.
