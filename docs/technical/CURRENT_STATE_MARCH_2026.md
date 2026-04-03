# État du Projet Korrigo — 3 Avril 2026

> **Version** : 3.1
> **Date** : 2026-04-03
> **Production** : https://korrigo.labomaths.tn

---

## Résumé exécutif

Korrigo v2 est pleinement opérationnel en production. Au 3 avril 2026, l’instance publique héberge **4 examens**, **504 copies**, **3414 annotations** et **396 scores**. Le système de backup automatisé vers Hetzner StorageBox est en service et les archives historiques locales ont été externalisées.

---

## 1. Production observée

### Serveur
- **IP** : 88.99.254.59
- **Domaine principal** : `korrigo.labomaths.tn`
- **Alias** : `korrigo.nexusreussite.academy`
- **Chemin de déploiement** : `/var/www/labomaths/korrigo/`

### Conteneurs Docker

| Conteneur | État | Rôle |
|-----------|------|------|
| `docker-backend-1` | Up | Django + Gunicorn |
| `docker-db-1` | Up | PostgreSQL 15 |
| `docker-redis-1` | Up | Redis 7 |
| `docker-celery-1` | Up | Worker Celery |
| `docker-celery-beat-1` | Up | Scheduler |
| `docker-nginx-1` | Up | Reverse proxy + TLS |

### Point de santé de référence

Le point de contrôle opérationnel en production est :

```bash
curl -fsS https://korrigo.labomaths.tn/api/health/
```

Réponse attendue :

```json
{"status":"healthy","database":"connected"}
```

---

## 2. Données métier observées

Snapshot constaté après nettoyage et vérifications :

| Indicateur | Valeur |
|------------|--------|
| ExamTypes | 3 |
| Exams | 4 |
| Copies TOTAL | 504 |
| READY | 107 |
| IN_PROGRESS | 186 |
| FINALIZED | 211 |
| Students | 512 |
| Users | 519 |
| Annotations | 3414 |
| Scores | 396 |
| GradingEvents | 10311 |
| DraftStates | 104 |
| QuestionRemarks | 4273 |

---

## 3. Modèle fonctionnel courant

### Machine à états des copies

```text
READY -> IN_PROGRESS -> FINALIZED
  ^                         |
  +------ reopen admin -----+
```

### Observations importantes
- les anciens états `STAGING`, `LOCKED`, `GRADING_IN_PROGRESS` et `GRADED` ne sont plus les statuts actifs du modèle `Copy`
- la réouverture administrative ramène une copie `FINALIZED` vers `READY`
- le verrouillage concurrent visible historiquement via `CopyLock` reste un mécanisme auxiliaire, mais le flux métier courant repose d’abord sur `READY`, `IN_PROGRESS`, `FINALIZED`

---

## 4. État du schéma et des migrations

Migrations `exams` significatives :

| Migration | Statut actuel |
|-----------|---------------|
| `0026_simplify_copy_status` | Appliquée |
| `0027_rename_copy_statuses` | Appliquée |
| `0028_copy_finalizing_at` | Historique |
| `0029_remove_copy_finalizing_at_alter_copy_status` | Appliquée |
| `0030_add_copy_constraint_and_teacher_group` | Appliquée |
| `0031_seed_copy_constraints_and_teacher_groups` | Appliquée |
| `0032_copy_student_status_index` | Appliquée |

Point important :
- le champ `finalizing_at` n’est plus le mécanisme courant du schéma actif

---

## 5. Finalisation concurrente

Le code courant ne repose plus sur `finalizing_at`.

La finalisation est maintenant protégée par :
- `select_for_update(nowait=True)` pour sérialiser l’accès à la copie
- une mise à jour atomique du statut vers `FINALIZED`
- le rejet explicite des doublons via `LockConflictError`

---

## 6. Sauvegardes

Le système de backup en production fonctionne ainsi :
- exécution toutes les 30 minutes via cron
- dump PostgreSQL complet
- export JSON des corrections
- archive du volume `media_volume`
- envoi vers Hetzner StorageBox `u554481.your-storagebox.de` sur le port `23`
- stockage distant sous `backups/korrigo_backups/<timestamp>/`
- rétention distante de 24 heures
- suppression locale après succès
- conservation locale limitée à des `fallback_*` en cas d’échec réseau

Archives historiques externalisées :
- `backups/korrigo_archives_historiques/` sur le StorageBox
- manifeste local :
  [storagebox_korrigo_archives_historiques_manifest_2026-04-03.txt](/home/alaeddine/Bureau/KORRIGO/korrigo_v2_improved/storagebox_korrigo_archives_historiques_manifest_2026-04-03.txt)

---

## 7. Nettoyage de production déjà effectué

Changements d’exploitation déjà validés :
- correction de `celery-beat`
- suppression des snapshots et artefacts morts du projet
- confirmation que `overlay/media/` n’était pas le stockage live
- externalisation des archives historiques
- réduction de `backups/` local à un volume minimal

---

## 8. Points de vigilance

- la source de vérité opérationnelle est le couple `docs/deployment/RUNBOOK_PRODUCTION.md` + `scripts/korrigo_backup.sh`
- le point de santé de référence est celui derrière Nginx, pas un endpoint local brut sur `localhost:8000`
- le dossier `documentation/` reste utile pour l’historique, mais ne doit plus être utilisé seul comme référence actuelle
