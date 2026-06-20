# Assainissement Korrigo — Checklist d'exécution (pilotage Codex)

> Périmètre : dépôt local + production `korrigo.labomaths.tn` (`root@88.99.254.59`)
> Référence factuelle : `AUDIT_COMPLET_KORRIGO_2026-06-20.md`
> Objet : rendre la prod saine, sans surcouches, doublons, caches, orphelins, zombies, code mort ni incohérences — avec un comportement stable et robuste.
> Convention : `- [ ]` à cocher ; une **Porte de sortie** doit être franchie avant de passer à l'étape suivante.

## Comment utiliser ce document

1. Codex traite **une étape à la fois**, dans l'ordre.
2. Chaque tâche se fait en deux temps : **inventaire lecture seule** (preuve d'état) → **exécution réversible** (preuve avant/après).
3. Codex **s'arrête à chaque Porte de sortie** et attend une validation humaine explicite avant de la franchir.
4. Les preuves (chemins, IDs, checksums, rapports) sont consignées dans le **Journal des preuves** en fin de document.

---

## Règles permanentes (revérifier à chaque session)

- [ ] Sauvegarde complète point-in-time (dump + média) disponible et datée de moins de 24 h
- [ ] Aucune opération destructive sans restauration testée préalablement
- [ ] Périmètre **strictement Korrigo** : images `…/korrigo-*`, volumes `docker_*` / `korrigo_*` du projet uniquement
- [ ] Aucun objet d'un autre projet du serveur n'est touché (réseaux, volumes, conteneurs, vhosts)
- [ ] Tout changement de code passe par une branche dédiée puis une validation en staging
- [ ] **Aucun élagage d'image ou de volume avant la validation de l'Étape 2** (les anciennes images sont le seul rollback)
- [ ] Aucune suppression de données de moins d'un an

---

## Tableau de bord (portes franchies)

- [x] **Porte 1** — Point de référence établi
- [ ] **Porte 2** — Release réconciliée reconstructible validée *(gate central)*
- [ ] **Porte 3** — Prod basculée sans overlay, configuration unifiée
- [ ] **Porte 4** — Élagage Docker effectué (rollback préservé)
- [ ] **Porte 5** — Orphelins / zombies / scratch supprimés
- [ ] **Porte 6** — Orphelins de données traités
- [ ] **Porte 7** — Dépôt assaini (code mort, fichiers obsolètes, doublons)
- [ ] **Porte 8** — Robustesse runtime en place
- [ ] **Porte 9** — Garde-fous CI anti-rechute actifs

---

## Étape 1 — Point de référence et inventaire
**Mode : lecture seule.** *(réf. §18, §19, §21, §22)*

- [x] Sauvegarde complète (dump + média) confirmée
- [x] Restauration testée dans une pile jetable, health applicatif `OK`
- [x] Inventaire des images Korrigo : IDs, tailles, ancienneté (réf. §18.4 — ~74 images, ~15,2 Gio de cache)
- [x] Inventaire des volumes + références par conteneur (réf. §22.3, §17.2)
- [x] Inventaire des conteneurs : états, uptime (réf. §18.5)
- [x] Liste des montages `overlay/` du compose actif (réf. §19.2)
- [x] Comparaison `django_migrations` (DB) vs fichiers de migration de l'image (réf. §19.4 — écart `exams 0039–0042`)
- [x] `df -h` capturé (réf. §10.1 — disque à 83 %)
- [x] Rapport d'état de référence horodaté archivé

> **Porte de sortie 1** — [x] Backup restaurable **prouvé** + rapport d'état complet archivé.

---

## Étape 2 — Release réconciliée reconstructible *(gate central)*
**Mode : branche dédiée + staging.** *(réf. §19.3, §19.5)*

- [ ] Branche `release/reconcile` créée depuis l'état courant
- [ ] Overlays **DIFFERS** repliés dans le code source canonique :
  - [ ] `exams/views.py`
  - [ ] `exams/urls.py`
  - [ ] `exams/permissions.py`
  - [ ] `core/views.py`
  - [ ] `core/settings_prod.py`
  - [ ] `backend/bilan/permissions.py`
  - [ ] `gunicorn_config.py`
  - [ ] `students/serializers.py`
  - [ ] `core/views_platform.py`
- [ ] Overlays **MISSING_IN_IMAGE** intégrés à la source :
  - [ ] `exams/views_direction.py`
  - [ ] `exams/views_jury_report.py`
  - [ ] `bilan/services/orchestrator_eam.py`
  - [ ] `bilan/services/rag_retriever_premiere.py`
  - [ ] migrations `bilan 0002`, `exams 0021_merge`
- [ ] Doublons de chemins tranchés (`backend/bilan/…` vs `bilan/…`, `backend/exams/…` vs `exams/…`) : canonique = fichier réellement monté, décision documentée
- [ ] **Cas critique arbitré explicitement** : `eam_orchestrator.py` (94 597 vs 29 798 octets) — divergence majeure, ne pas dédupliquer à l'aveugle
- [ ] Overlays **IDENTICAL** confirmés inutiles et retirés du chemin runtime après tests
- [ ] Migrations `exams 0039 → 0042` tracées dans Git et présentes dans l'image
- [ ] `0042` réconciliée sur **clone** de la DB (migration réelle ou fake documentée)
- [ ] Images rebuild avec labels OCI : `revision`, `source`, `version`, `created`
- [ ] Images publiées sous **tag Git + digest** (tag ad hoc interdit)
- [ ] Staging : `manage.py check` `OK`
- [ ] Staging : `showmigrations --plan` cohérent avec la DB
- [ ] Staging : tests permissions / média / migrations / peer-review `OK`
- [ ] Staging : parcours admin / correcteur / élève / direction `OK`

> **Porte de sortie 2** — [ ] `docker image inspect` remonte au commit ; `showmigrations` reflète la DB ; **aucun overlay nécessaire** au fonctionnement ; staging entièrement vert.
> ⚠️ **Ne franchir aucune étape d'élagage tant que cette porte n'est pas validée.**

---

## Étape 3 — Bascule prod et unification de la configuration
**Mode : exécution prod, rollback conservé.** *(réf. §10.4, §11.5, §21.2)*

- [ ] Bascule prod sur l'image réconciliée **par digest** (pas un tag flottant)
- [ ] Montages `overlay/` retirés du compose
- [ ] **Compose unique** (suppression de la divergence racine vs `infra/docker/`)
- [ ] Redis protégé par mot de passe
- [ ] Chiffrement GPG des backups activé (`BACKUP_GPG_PASSPHRASE`)
- [ ] `SEED_ON_START=false`, `E2E_SEED_TOKEN` retiré, docs d'API désactivées en prod
- [ ] `KORRIGO_SHA` = tag/commit relié à Git
- [ ] Nom des dumps corrigé (`.dump`, pas `.sql.gz` trompeur)
- [ ] Redémarrage backend/celery/celery-beat/nginx + health + parcours par rôle `OK`
- [ ] Anciennes images conservées (rollback) jusqu'à validation finale

> **Porte de sortie 3** — [ ] Prod sans overlay, configuration unifiée, health vert, rollback encore possible.

---

## Étape 4 — Élagage Docker (images, cache)
**Mode : exécution, après validation finale. Périmètre Korrigo strict.** *(réf. §18.4, §10.1)*

- [ ] Validation de stabilité prod confirmée (durée/critère défini)
- [ ] Images Korrigo anciennes supprimées (conserver l'**active + 3 dernières releases**)
- [ ] Images dangling + cache de build élagués (ciblés Korrigo)
- [ ] (Optionnel) Backend allégé : build multi-stage, base slim, `.dockerignore` (image actuelle ~5,98 Go)
- [ ] Espace récupéré rapporté
- [ ] Aucune image d'un autre projet touchée

> **Porte de sortie 4** — [ ] Empreinte d'images réduite, disque sous le seuil d'alerte, rollback (3 dernières releases) préservé.

---

## Étape 5 — Volumes orphelins, conteneurs zombies, scratch
**Mode : inventaire puis suppression confirmée.** *(réf. §17.2, §22.3)*

- [ ] Inventaire des volumes Korrigo non référencés (candidats `*_local`, `korrigo_*`, `docker_seed_data_v2` si seed off)
- [ ] Confirmation : aucun conteneur ne référence ces volumes
- [ ] Conteneurs `exited`/`dead` Korrigo listés
- [ ] Répertoires scratch résiduels listés (`/tmp/korrigo-restore-*`)
- [ ] Dossiers `fallback_*` au-delà de la rétention listés
- [ ] Suppression des **seuls** orphelins confirmés
- [ ] Volumes vivants intacts (`docker_postgres_data`, `docker_media_volume`)

> **Porte de sortie 5** — [ ] Plus aucun orphelin/zombie Korrigo ; volumes vivants intacts.

---

## Étape 6 — Orphelins au niveau données
**Mode : inventaire puis suppression validée.** *(réf. §21.5)*

- [ ] Médias orphelins (fichiers non référencés par un `FileField`) — rapport
- [ ] Lignes orphelines (copies/annotations/scores/`OCRResult`/sessions expirées) — rapport
- [ ] État de la purge de rétention (`purge_old_exam_data`) vérifié ; reste-t-il des données > 1 an ?
- [ ] Suppression validée explicitement, sauvegarde préalable, **jamais < 1 an**

> **Porte de sortie 6** — [ ] Rapport produit ; suppressions validées et tracées ; rétention effectivement appliquée.

---

## Étape 7 — Assainissement du dépôt
**Mode : branche dédiée, tests verts.** *(réf. §3.1, §3.2, §12, §19.3)*

- [ ] Données hors-code sorties du suivi Git (archivées ou supprimées) : `docs_exam/`, `DS_NSI_Premiere_Algo/`, `copies_EAM_2026/`, `scan_*`, `PATCHES/`, `overlay/_archived_*`, `*.before_individual_upload_fix_*`, `stat_BB_MATHS_2026.md`
- [ ] `.gitignore` et `.dockerignore` ajoutés (médias, scans, venv, caches, artefacts de build)
- [ ] `docs/` (normatif) vs `documentation/` (archive) clarifiés ; `docs/INDEX.md` rafraîchi (chiffres périmés)
- [ ] Code mort détecté : `ruff` (imports inutilisés), `vulture` (Python mort), `ts-prune`/`knip` (exports TS), `depcheck` (dépendances)
- [ ] Routes/vues Django non câblées, commandes de management inutilisées, composants/routes Vue morts identifiés
- [ ] Suppression du code mort confirmé, suite de tests verte
- [ ] Worktree stabilisé (commits propres ou stash documenté)

> **Porte de sortie 7** — [ ] Dépôt sans données ni code mort ; tests verts ; worktree propre.

---

## Étape 8 — Robustesse et stabilité du runtime
**Mode : exécution.**

- [ ] Healthchecks avec `start_period` adapté sur tous les services
- [ ] `restart: unless-stopped`
- [ ] Limites de ressources (`mem_limit`, `cpus`) par conteneur (hôte partagé)
- [ ] Rotation des logs (`json-file` `max-size`/`max-file` ou journald)
- [ ] Format de log Nginx enrichi (`$request_time`, `$request_length`, `$body_bytes_sent`, `$request_id`) + rétention
- [ ] Alertes : disque (>80/90 %), échec de backup, expiration certificat, conteneur non `healthy`
- [ ] `.env` en permissions `600`, secrets hors dépôt
- [ ] Déploiement idempotent par digest
- [ ] Runbook d'exploitation rédigé

> **Porte de sortie 8** — [ ] Services résilients, supervisés ; déploiement reproductible et documenté.

---

## Étape 9 — Garde-fous CI (anti-rechute)
**Mode : intégration continue.**

- [ ] CI échoue si le compose contient un montage `overlay/`
- [ ] CI échoue si `KORRIGO_SHA` n'est pas relié à un commit/tag
- [ ] Gates `ruff` / `vulture` sur le code mort
- [ ] Contrôle de cohérence migrations (`django_migrations` vs fichiers — `migrate --check` ne suffit pas)
- [ ] Exigence des labels OCI sur les images publiées
- [ ] Test de restauration automatisé périodique

> **Porte de sortie 9** — [ ] Dérive structurellement empêchée ; CI verte.

---

## Journal des preuves

| Date | Étape | Artefact / preuve | Emplacement |
|---|---|---|---|
| 2026-06-20T12:10Z | 1 | Rapport synthèse Étape 1 ; backup complet StorageBox `20260620_133001`, health restore `OK`, `file_refs=1793 missing=0` | `proofs/assainissement_step1_20260620T115755Z/step1_summary_20260620T115755Z.md` |
| 2026-06-20T12:10Z | 1 | Inventaire prod lecture seule : `df -h` (`/` 81 %), 76 tags / 74 images Korrigo uniques, volumes, conteneurs, overlays, migrations | `proofs/assainissement_step1_20260620T115755Z/prod_reference_inventory_20260620T115755Z.txt` |
| 2026-06-20T12:10Z | 1 | Listing backup StorageBox confirmé : `db_20260620_133001.dump` + `media_20260620_133001.tar.gz` + exports JSON | `proofs/assainissement_step1_20260620T115755Z/prod_backup_listing_20260620T115755Z.txt` |
| 2026-06-20T12:10Z | 1 | Rapport distant de restauration jetable ; projet `korrigo-restore-step1-20260620t115755z`, conteneurs démontés, scratch conservé | `proofs/assainissement_step1_20260620T115755Z/restore_report_20260620T115755Z.remote.txt` |
| 2026-06-20T12:10Z | 1 | Checksums SHA-256 des preuves locales | `proofs/assainissement_step1_20260620T115755Z/SHA256SUMS.txt` |
| 2026-06-20T12:10Z | 1 | Backup restauré : `db_20260620_133001.dump` SHA-256 `8270e4a9ea0c4fd2d28a46f12fedf0d383fddbf1f7910588013607aa656bca61` ; `media_20260620_133001.tar.gz` SHA-256 `c4d0ac373a0d68271367dca460f8a469d9ecca54d36e7164c2989a96b7deed80` | StorageBox `backups/korrigo_backups/20260620_133001` ; copie scratch `/tmp/korrigo-restore-step1-20260620t115755z` |
| 2026-06-20T13:10Z | A | Source StorageBox confirmée intacte par streaming SHA-256 sans nouvelle copie locale : les 6 checksums de `20260620_133001` correspondent au journal Étape 1 | `proofs/assainissement_step2_20260620T131006Z/storagebox_checksum_confirm_20260620T131006Z.txt` |
| 2026-06-20T13:39Z | A | Scratch distant non chiffré `/tmp/korrigo-restore-step1-20260620t115755z` effacé par `shred -u -n 1 -z` puis `rm -rf`; `df /` avant `740G used / 143G free / 84%`, après `726G used / 156G free / 83%`; conteneurs/réseaux restore `0` | `proofs/assainissement_step2_20260620T131006Z/scratch_cleanup_20260620T131006Z.txt` |
| 2026-06-20T13:40Z | A | Nettoyage confidentialité local : ancien dossier non suivi `proofs/RC_2026-02-20` supprimé (`312` fichiers, dont `209` PDF et `36` JSON, `723M`) ; preuves conservées expurgées | `proofs/assainissement_step2_20260620T131006Z/local_pii_artifacts_cleanup_20260620T131006Z.txt` |
| 2026-06-20T13:40Z | A | Sweep PII : preuves conservées `email_count=0`, `pdf_count=0`, `dump_count=0`; `/var/log/korrigo_backup.log` `email_count=0`; scratch Étape 1 absent | `proofs/assainissement_step2_20260620T131006Z/pii_sweep_20260620T131006Z.txt` |
