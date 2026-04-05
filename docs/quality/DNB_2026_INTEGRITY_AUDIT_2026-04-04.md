# Audit d'Intégrité DNB_2026 — 2026-04-04

## Périmètre

Audit read-only réalisé sur la production `korrigo.labomaths.tn`, sans écriture sur la base, les volumes Docker, les copies, les notes, les élèves ou les sauvegardes.

Objectif :
- vérifier la stabilité opérationnelle de la plateforme
- vérifier que les notes saisies sur les copies `DNB_2026` sont toujours présentes
- détecter d'éventuelles disparitions de notes par copie ou par exercice
- vérifier l'état du flux de sauvegarde actuel

## Stabilité plateforme

Constats au moment du contrôle :
- `docker-backend-1`: `Up` et `healthy`
- `docker-celery-1`: `Up` et `healthy`
- `docker-celery-beat-1`: `Up`
- `docker-nginx-1`: `Up` et `healthy`
- `docker-db-1`: `Up` et `healthy`
- `docker-redis-1`: `Up` et `healthy`

Point de santé vérifié :
- `GET http://127.0.0.1:8088/api/health/` → `200 OK`
- réponse : `{"status":"healthy","database":"connected"}`

Verdict :
- plateforme stable au moment de l'audit

## Périmètre DNB_2026

Examen identifié :
- `DNB_2026`
- date : `2026-03-27`
- copies : `290`

Répartition des statuts :
- `IN_PROGRESS`: `201`
- `READY`: `89`
- `FINALIZED`: `0`

## Intégrité des notes

### Couverture globale

Constats :
- `201/201` copies `IN_PROGRESS` ont une ligne `Score` non vide
- `89/89` copies sans score sont les copies `READY`
- `0` copie `IN_PROGRESS` sans score
- `0` ligne `Score` vide sur les copies commencées

Interprétation :
- aucune disparition massive ou systémique de notes n'a été détectée
- les copies non notées correspondent à des copies encore non démarrées

### Couverture par exercice

La structure de barème de `DNB_2026` contient `22` feuilles de notation.

Couverture observée sur les `201` copies notées :
- Exercice 2 : présent sur `200–201/201`
- Exercice 3 : présent sur `148–159/201`
- Exercice 4 : présent sur `97/201`
- Exercice 5 : présent sur `112–114/201`

Interprétation :
- ce profil correspond à une correction en cours par blocs d'exercices
- il ne ressemble pas à une perte globale de données

### Contrôle contre l'historique d'audit

Méthode :
- comparaison, pour chaque copie `DNB_2026`, entre :
  - le nombre actuel de questions notées (`scores_data` non vide)
  - le maximum historique observé dans les événements `GradingEvent(action='scores_saved')`

Résultat :
- seulement `2` copies ont actuellement moins de notes qu'à leur maximum historique

Copies concernées :
- `69CB-005` : `current_nq=7`, `max_hist_nq=8`, `save_events=9`
- `69CB-244` : `current_nq=9`, `max_hist_nq=10`, `save_events=14`

Analyse de l'historique :
- pour `69CB-005`, le dernier événement passe de `nq=8` à `nq=7`
- pour `69CB-244`, le dernier événement passe de `nq=10` à `nq=9`
- dans les deux cas, l'écart est limité à `1` question
- le profil est compatible avec une édition manuelle ponctuelle, pas avec une corruption systémique

Verdict :
- pas de perte massive de notes
- `2` copies à surveiller manuellement si l'on veut une clôture métier parfaite

## Répartition actuelle des copies notées par correcteur

État observé :
- `chawki.saadi@ert.tn`: `48` copies, `48` avec notes
- `fatma.abid@ert.tn`: `49` copies, `49` avec notes
- `gilles.colly@ert.tn`: `48` copies, `8` avec notes
- `maroua.fraiji@ert.tn`: `48` copies, `48` avec notes
- `sami.bentiba@ert.tn`: `49` copies, `0` avec notes
- `soumaya.nasri@ert.tn`: `48` copies, `48` avec notes

Interprétation :
- l'état métier courant est cohérent avec une campagne de correction encore en cours
- aucun signal de perte massive spécifique à un correcteur n'a été détecté

## Sauvegardes

### État local

Vérification :
- `/var/www/labomaths/korrigo/backups` : `5.8M`
- contenu local résiduel :
  - `backups/automated/20260403_003001/db_20260403_003001.dump`
  - `backups/automated/backup.log`
  - `backups/automated/cron.log`

Interprétation :
- pas d'accumulation locale anormale

### Dernier backup automatisé vérifié

Extrait du log `/var/log/korrigo_backup.log` :
- extraction terminée : `2026-04-03T20:30:14`
- archive media OK : `6.5G`
- envoi StorageBox OK : `2026-04-03 22:34:24`
- purge locale OK
- backup final : `20260403_223001`

### StorageBox

Backup récent vérifié :
- dossier : `backups/korrigo_backups/20260403_223001/`
- contenu :
  - `copies_data.json` : `7.4M`
  - `db_20260403_223001.dump` : `1.8M`
  - `exams_bareme.json` : `18K`
  - `media_20260403_223001.tar.gz` : `6.5G`
  - `pages_manifest.json` : `428K`
  - `summary.json` : `1.6K`

Rétention distante observée :
- suite continue de backups `20260403_005617` à `20260403_223001`

Verdict :
- le flux de sauvegarde fonctionne
- les artefacts attendus sont présents sur le StorageBox
- la purge locale fonctionne

## Conclusion

Conclusion honnête à date :
- la plateforme est stable
- aucune corruption globale n'a été observée
- aucune disparition massive de notes sur `DNB_2026` n'a été détectée
- toutes les copies `IN_PROGRESS` ont encore des notes présentes
- la progression par exercice est cohérente avec une correction en cours
- seules `2` copies présentent un écart historique limité de `1` question, à surveiller si nécessaire
- les sauvegardes sont opérationnelles et récentes

## Recommandations

- vérifier manuellement `69CB-005` et `69CB-244` côté métier si une validation exhaustive est requise
- conserver le flux de backup actuel inchangé
- traiter séparément le drift d'overlay de production, qui reste le principal risque opérationnel identifié, sans rapport direct avec une perte massive de notes constatée ici
