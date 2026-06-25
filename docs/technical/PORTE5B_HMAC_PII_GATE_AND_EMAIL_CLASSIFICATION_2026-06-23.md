# Porte 5B - HMAC PII gate and email classification - 2026-06-23

## Contexte

La Porte 5A a reconcilie le compose canonique serveur avec le runtime Lot 0-G,
sans redemarrage. La dette prioritaire suivante etait le gate anti-PII :

- les marqueurs etaient des SHA-256 nus;
- ces marqueurs etaient une pseudonymisation de controle, pas une anonymisation;
- le depot GitHub est public;
- les emails hors bundle devaient etre classes sans afficher les valeurs.

## Nouveau gate anti-PII

Fichier modifie :

`scripts/ci/check_frontend_pii_hashes.py`

Nouveau comportement :

- HMAC-SHA256 via `hmac.new(pepper, normalized_value, hashlib.sha256)`;
- pepper obligatoire via `PII_GATE_PEPPER`;
- fail-closed si le pepper est absent;
- aucune valeur source stockee;
- aucune valeur detectee imprimee;
- sortie limitee au compteur, fichier, ligne et categorie de marqueur;
- normalisation conservee : casse, accents, espaces multiples, caracteres
  invisibles simples, emails et mots composes.

Sortie sans pepper :

```text
PII_GATE_STATUS=FAIL_MISSING_PEPPER
PII_HASH_MATCH_COUNT=0
```

Sortie avec pepper et aucun match :

```text
PII_GATE_STATUS=PASS
PII_HASH_MATCH_COUNT=0
```

## Statut des marqueurs

`HMAC_GATE_READY_NEEDS_ADMIN_REGENERATION`

Les anciens marqueurs SHA-256 ont ete retires du depot. Les valeurs sources
reelles ne sont pas disponibles dans un canal sur et ne doivent pas etre
reintroduites dans le depot. L'administrateur doit regenerer les HMAC hors depot
avec un pepper non commite, puis inserer uniquement les marqueurs HMAC.

## Utilitaire de generation

Fichier ajoute :

`scripts/ci/generate_pii_hmac_markers.py`

Usage :

```bash
PII_GATE_PEPPER="..." python scripts/ci/generate_pii_hmac_markers.py < /chemin/local/non_committe/pii_values.txt
```

L'entree ne doit jamais etre committee. Les protections `.gitignore` suivantes
ont ete ajoutees :

- `.pii_gate_pepper`;
- `pii_values*.txt`;
- `pii_hmac_input*.txt`;
- `scripts/ci/pii_values*.txt`;
- `scripts/ci/pii_hmac_input*.txt`.

## CI

`.github/workflows/ci.yml` a ete mis a jour pour que le job du gate lise :

`PII_GATE_PEPPER: ${{ secrets.PII_GATE_PEPPER }}`

Aucune valeur par defaut faible n'est fournie. Si le secret est absent, le gate
echoue.

## Tests

Tests cibles mis a jour dans :

`backend/core/tests/test_lot0_rgpd_deploy_contract.py`

Cas couverts :

- pepper absent -> fail-closed;
- pepper synthetique -> scan courant OK;
- detection synthetique avec accents/casse/espaces;
- detection avec caractere invisible intramot;
- detection email synthetique;
- faux positif technique evite;
- sortie sans fuite de valeur source;
- absence de `DENY_HASHES`;
- utilitaire HMAC sans fuite de valeur d'entree.

## Classification emails

Script ajoute :

`scripts/audit/classify_plain_emails_redacted.py`

Rapport detaille :

`docs/technical/PORTE5B_EMAIL_CLASSIFICATION_REDACTED_2026-06-23.md`

Resultat agrege :

```text
EMAIL_CLASSIFICATION_FILE_COUNT=100
EMAIL_CLASSIFICATION_TOTAL_OCCURRENCES=461
EMAIL_CATEGORY_DOC_EXAMPLE=9
EMAIL_CATEGORY_PUBLIC_INSTITUTIONAL=69
EMAIL_CATEGORY_SECRET_LIKE=32
EMAIL_CATEGORY_TEST_FIXTURE=331
EMAIL_CATEGORY_TO_REVIEW=20
```

Aucune adresse email n'est affichee dans le rapport.

## Fichiers modifies

- `.github/workflows/ci.yml`;
- `.gitignore`;
- `scripts/ci/check_frontend_pii_hashes.py`;
- `scripts/ci/generate_pii_hmac_markers.py`;
- `scripts/audit/classify_plain_emails_redacted.py`;
- `backend/core/tests/test_lot0_rgpd_deploy_contract.py`;
- `docs/technical/PORTE5B_EMAIL_CLASSIFICATION_REDACTED_2026-06-23.md`;
- `docs/technical/PORTE5B_HMAC_PII_GATE_AND_EMAIL_CLASSIFICATION_2026-06-23.md`.

## Confirmations

- Aucun push GitHub.
- Aucune PR.
- Aucun workflow GitHub.
- Aucun GHCR.
- Aucun build Docker.
- Aucun deploiement.
- Aucun redemarrage applicatif.
- Aucun secret, pepper ou PII affiche.

## Risques residuels

- Les marqueurs reels doivent etre regeneres hors depot par l'administrateur.
- Les emails classes `SECRET_LIKE` et `TO_REVIEW` doivent etre examines et
  corriges si necessaire.
- Git/main reste non aligne.
- `BilanBacBlanc.vue` reste une dette structurelle.

## Prochaine etape

1. Regeneration administrateur des marqueurs HMAC reels hors depot.
2. Correction des emails classes `SECRET_LIKE` et `TO_REVIEW`.
3. Strategie Git/main prive et integration controlee.
