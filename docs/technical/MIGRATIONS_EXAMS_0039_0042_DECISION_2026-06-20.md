# Decision migrations `exams` 0039-0043

Date UTC: 2026-06-20T13:55Z
Reference: restauration StorageBox `20260620_133001`, prod active `docker-backend-1`, snapshot `wip/worktree-20260620`.

## Inventaire

| Migration | Local snapshot | `origin/main` | Image active | DB prod/restauree |
|---|---|---|---|---|
| `0039_alter_copy_status.py` | presente, SHA-256 `5cfcfec873ebc9244e93c68dc8c52624f1da1ef58d43da9b099d4a39f608c992` | presente, meme checksum | absente | appliquee le `2026-04-22 14:09:27+00` |
| `0040_add_pdf_regeneration_pending.py` | presente, SHA-256 `cf95c4bcfeb1a22721f419a6c6dd3bd60e8a7e8a649c6ff482fe082292c7d5cd` | presente, meme checksum | absente | appliquee le `2026-05-08 08:48:35+00` |
| `0041_merge_20260514_0001.py` | presente, SHA-256 `5f72b6aea4921a1568e3719c85855d36a741cd700c4c4e3d448b8ed422792ab9` | presente, meme checksum | absente | appliquee le `2026-05-14 01:13:33+00` |
| `0042_copy_pdf_regeneration_pending_db_default.py` | presente, SHA-256 `dd775d9acfdaaf75b3a8e8df9f7a29b55d37cbc82a9b9045056c39871806273a` | absente | absente | non appliquee |
| `0043_reconcile_copy_status_constraint.py` | creee dans `release/reconcile`, SHA-256 `e41cc91db0fa84a3e47e69b4811806eda7c076cb4a0935dd7bedacceebd1835f` | absente | absente | non appliquee |

## Schema live observe

`exams_copy.pdf_regeneration_pending`:

- type: `boolean`
- nullable: `NO`
- default SQL: `false`

`exams_copy.status`:

- type: `varchar(20)`
- nullable: `NO`
- contrainte live: `READY`, `IN_PROGRESS`, `FINALIZED`

## Analyse

1. `0039-0041` existent localement et dans `origin/main`, mais pas dans l'image active. Ils doivent etre presents dans l'image reconciliee pour que `showmigrations` reflete l'historique DB.
2. `0039` est un `AlterField` Django. `sqlmigrate` local indique un no-op SQL. Il documente un etat de modele a 5 statuts, mais ne peut pas expliquer la contrainte live a 3 statuts.
3. `0040` ajoute `pdf_regeneration_pending`. La DB live contient bien cette colonne, `boolean NOT NULL DEFAULT false`.
4. `0041` est une merge migration sans operation; elle doit rester pour refermer le graphe applique en DB.
5. `0042` ferait `ALTER COLUMN pdf_regeneration_pending SET DEFAULT FALSE`. La DB live est deja equivalente, mais `0042` n'est pas dans `django_migrations`.
6. Divergence additionnelle critique: le fichier local/origin `0038_copy_check_copy_status_valid.py` exprime une contrainte a 5 statuts, alors que la DB live et l'image active `models.py` expriment 3 statuts. Il ne faut pas modifier la prod pour rejoindre le fichier local; la release doit rejoindre le schema live.

## Decision

- Conserver `0039`, `0040`, `0041` comme contenu canonique d'historique, car leurs checksums correspondent a `origin/main` et la DB les marque appliquees.
- Integrer `0042` dans la release, mais l'appliquer sur clone DB comme migration idempotente/equivalente au schema live. Sur clone prod, elle ne doit produire aucun diff de schema effectif.
- Ajouter `0043_reconcile_copy_status_constraint.py` apres `0042` pour aligner explicitement l'etat Django final avec le schema live a 3 statuts. Cette migration:
  - conserver les donnees existantes;
  - garantir la contrainte `check_copy_status_valid` a `READY`, `IN_PROGRESS`, `FINALIZED`;
  - rendre `makemigrations --check` muet;
  - passer sur clone DB restaure et sur base vide.

## Preuves

- Inventaire fichiers/checksums: `proofs/assainissement_step2_20260620T131006Z/`
- Colonnes live: `proofs/assainissement_step2_20260620T131006Z/prod_exams_copy_columns_20260620T131006Z.txt`
- Contrainte live: `proofs/assainissement_step2_20260620T131006Z/prod_exams_copy_schema_20260620T131006Z.txt`
- Snippet modele image active: `proofs/assainissement_step2_20260620T131006Z/image_exams_model_status_snippet_20260620T131006Z.txt`
