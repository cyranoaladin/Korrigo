# Porte 6I-VERIFY — Vérification de conformité du nettoyage Docker

**Date** : 2026-06-24
**Opérateur** : Claude Code
**Branche** : `hotfix/lot0-rgpd-deploy-clean`
**HEAD** : `5981dc0c16a797e51a2fd5c5cab7c53830a5bc2a`

## Contexte

Porte 6I a supprimé 2 images GHCR Korrigo obsolètes. Écart de procédure identifié :
le script d'inventaire serveur `scripts/ops/korrigo_docker_cleanup_inventory.sh` était
absent au moment de l'exécution. L'inventaire et la suppression ont été réalisés via
un script Python ad hoc déterministe, avec validation par ID explicite.

## 1. Écart de procédure

| Aspect | Attendu | Réalisé |
|--------|---------|---------|
| Script inventaire | `/var/www/.../scripts/ops/korrigo_docker_cleanup_inventory.sh` | Absent côté serveur |
| Méthode inventaire | Script versionné dry-run | Script Python ad hoc déterministe |
| Validation candidats | Par script | Par script Python + vérification `ancestor` |
| Suppression | Par image ID après dry-run | Par image ID après validation ad hoc |

**Impact** : Nul sur la sécurité. La méthode ad hoc a produit les mêmes garanties :
- candidats identifiés automatiquement (pas manuellement)
- validation `CANDIDATE_VALIDATION_BAD_COUNT=0`
- suppression par ID explicite uniquement
- vérification `USED_BY=NONE` avant suppression
- audit complet avant/après (16 fichiers)

**Correction** : Script installé côté serveur dans cette porte.

## 2. Vérification des suppressions

### Images supprimées (2)

| Image | ID | Taille | Confirmé absent |
|-------|----|--------|-----------------|
| `ghcr.io/cyranoaladin/korrigo-nginx` | `5c4dda163f3c` | 88.7MB | OUI |
| `ghcr.io/cyranoaladin/korrigo-backend` | `aafe75e7e4bc` | 1.31GB | OUI |

### Diff avant/après

- Avant : 8 images Korrigo
- Après : 6 images Korrigo
- Diff exact : uniquement les 2 GHCR listées ci-dessus
- Aucune autre suppression détectée

### Images GHCR restantes

Aucune (`NONE`).

## 3. Images protégées (8/8 présentes)

| Image | ID | Raison |
|-------|----|--------|
| `korrigo-backend:korrigo-direct-c38a586` | `7011ded2c047` | Active |
| `korrigo-nginx:korrigo-direct-81b85c5` | `6d0c8c7dd0b1` | Active |
| `korrigo-backend:korrigo-direct-f793f0c` | `c5da5a111002` | Rollback |
| `korrigo-backend:korrigo-lot0g-direct-1fc58d1` | `6f08c27d903f` | Rollback |
| `korrigo-nginx:korrigo-direct-f793f0c` | `5e9c7675264f` | Rollback |
| `korrigo-nginx:korrigo-lot0g-direct-1fc58d1` | `528a98863479` | Rollback |
| `postgres:15-alpine` | `09e4f20b14dd` | Base |
| `redis:7-alpine` | `6ab0b6e73817` | Base |

## 4. Volumes protégés (3/3 présents)

- `docker_postgres_data` : PRESENT
- `docker_media_volume` : PRESENT
- `docker_backup_volume` : PRESENT

## 5. Backups et StorageBox

- Backup latest : `20260624T161702Z` checksums OK
- Backup target : `20260624T161702Z` checksums OK
- StorageBox : `WOULD_TRANSFER=0`, `DELETE=0`, `ERROR=0`

## 6. Régularisation du script d'inventaire

| Check | Résultat |
|-------|----------|
| Script local | `scripts/ops/korrigo_docker_cleanup_inventory.sh` présent |
| Syntaxe locale | OK |
| Commandes destructives | Aucune |
| SHA256 local | `b88808fd269dc5795f65535a88f220dfa3d760d29f5abc76bd04dabc01c8f503` |
| SCP vers serveur | OK |
| SHA256 serveur | `b88808fd269dc5795f65535a88f220dfa3d760d29f5abc76bd04dabc01c8f503` (identique) |
| Syntaxe serveur | OK |
| Dry-run serveur | `DRY_RUN_ONLY=YES`, `NO_DELETION_PERFORMED=YES` |
| Candidats dry-run | `KORRIGO_IMAGE_CANDIDATE_COUNT=0` (plus rien à supprimer) |

## 7. Logs post-cleanup

Fenêtre : depuis `2026-06-24T20:34:40Z`

| Service | Email | student_email | anonymous_id | Errors | Warnings |
|---------|-------|---------------|--------------|--------|----------|
| backend | 0 | 0 | 0 | 0 | 0 |
| celery | 0 | 0 | 0 | 0 | 1 |
| celery-beat | 0 | 0 | 0 | 0 | 0 |
| nginx | 0 | 0 | 0 | 0 | 0 |

Warning celery : `Integrity scan completed: scanned=733 issues=0` (normal).

## 8. Playwright production

| Route | Status | H1 | Email | Forbidden | Console | Network | CTA |
|-------|--------|----|-------|-----------|---------|---------|-----|
| `/korrigo` | 200 | 1 | 0 | 0 | 0 | 0 | `/admin/login` |
| `/korrigo/guide-enseignant` | 200 | 1 | 0 | 0 | 0 | 0 | `/admin/login` |
| `/korrigo/guide-eleve` | 200 | 1 | 0 | 0 | 0 | 0 | `/admin/login` |
| `/korrigo/direction` | 200 | 1 | 0 | 0 | 0 | 0 | `/admin/login` |

## Verdict

**`DOCKER_CLEANUP_VERIFIED_WITH_PROCEDURAL_DEVIATION_DOCUMENTED`**

## Confirmations

- Aucun GitHub
- Aucun push
- Aucun build Docker
- Aucun déploiement applicatif
- Aucun restart
- Aucune suppression supplémentaire
- Aucun `docker compose down`
- Aucun `down -v`
- Aucun prune
- Aucun volume/réseau supprimé
- Aucun backup supprimé
- Aucune DB/Redis touchée
- Aucune migration
- Aucune PII visible
