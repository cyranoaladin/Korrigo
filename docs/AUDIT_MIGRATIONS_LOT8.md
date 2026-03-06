# Audit Spécialisé — Migrations, Contraintes et Changements de Schéma LOT 8

**Date** : 6 mars 2026  
**Périmètre** : Exclusivement les migrations générées par les corrections P0/P1  
**Méthode** : Analyse ligne par ligne des fichiers de migration, traçage de l'historique complet des migrations sur les tables concernées, audit des scripts de recovery ayant pu créer des doublons  
**Exigence** : Conservatisme maximal — la base contient les notes réelles de 209 copies de bac blanc

---

## 1. Liste Exhaustive des Migrations Créées

### Migration A : `grading/migrations/0013_score_unique_copy_constraint.py`

| Champ | Valeur |
|-------|--------|
| **Objectif** | Empêcher la création de deux objets `Score` pour une même `Copy` au niveau DB |
| **Table impactée** | `grading_score` |
| **Colonne impactée** | `copy_id` (FK vers `exams_copy.id`, type UUID) |
| **Type de changement** | Ajout de contrainte UNIQUE |
| **SQL généré (PostgreSQL)** | `ALTER TABLE "grading_score" ADD CONSTRAINT "uniq_score_per_copy" UNIQUE ("copy_id");` |
| **Dépendance** | `grading/0012_annotation_bank_and_documents` |

**Observation critique** : Django traduit `UniqueConstraint(fields=['copy'])` en `UNIQUE ("copy_id")`. PostgreSQL implémente cela en créant implicitement un **index unique** nommé `uniq_score_per_copy`. Or la table `grading_score` possède déjà un **index FK automatique** créé par Django lors de la migration `0010_score` (nommé approximativement `grading_score_copy_id_<hash>`). Après migration 0013, il y aura donc **deux index** sur `copy_id` : l'index FK (non-unique) et l'index unique. C'est redondant — l'index unique subsume l'index FK pour les lookups. Ce n'est pas dangereux mais c'est un gaspillage d'espace et de temps d'écriture.

### Migration B : `exams/migrations/0023_copy_performance_indexes_lot8.py`

| Champ | Valeur |
|-------|--------|
| **Objectif** | Accélérer les queries fréquentes sur `exams_copy` |
| **Table impactée** | `exams_copy` |
| **Colonnes impactées** | `status`, `exam_id`, `assigned_corrector_id` |
| **Type de changement** | Ajout de 3 index (non-uniques) |
| **SQL généré (PostgreSQL)** | Voir détail ci-dessous |
| **Dépendance** | `exams/0022_copy_llm_summary` |

**Index créés :**

| Nom | Colonnes | SQL |
|-----|----------|-----|
| `idx_copy_status` | `(status)` | `CREATE INDEX "idx_copy_status" ON "exams_copy" ("status");` |
| `idx_copy_exam_status` | `(exam_id, status)` | `CREATE INDEX "idx_copy_exam_status" ON "exams_copy" ("exam_id", "status");` |
| `idx_copy_corrector_status` | `(assigned_corrector_id, status)` | `CREATE INDEX "idx_copy_corrector_status" ON "exams_copy" ("assigned_corrector_id", "status");` |

**Observation critique — historique d'index en yo-yo :**

La table `exams_copy` a subi le cycle suivant :
1. **Migration 0014** (jan 2026) : ajout de `exams_copy_status_idx` (status) + `exams_copy_exam_status_idx` (exam, status)
2. **Migration 0015** : ajout de `exams_copy_assigned_corrector_idx` (assigned_corrector) + `exams_copy_dispatch_run_idx` (dispatch_run_id)
3. **Migration 0016** (29 jan 2026) : **SUPPRESSION** des 4 index ci-dessus
4. **Migration 0023** (ma migration) : **RE-CRÉATION** de 3 index avec des noms différents

Cela signifie que si toutes les migrations jusqu'à 0022 sont appliquées en production, les anciens index n'existent plus (supprimés par 0016) et 0023 est safe.

**Risque** : Si l'état de migration en production est **incohérent** (ex: 0014/0015 appliquées mais pas 0016), les anciens index existent encore. Dans ce cas, 0023 ajouterait des index **en doublon** sur les mêmes colonnes. Ce n'est pas une erreur PostgreSQL (les noms sont différents), mais c'est un gaspillage et une source de confusion.

### Migrations NON créées mais rendues nécessaires

Aucune. Les corrections P0/P1 sur `grading/views.py`, `grading/views_async.py`, `exams/views_documents.py` et `StatsReport.vue` ne modifient aucun modèle et ne nécessitent aucune migration supplémentaire.

---

## 2. Analyse de Sûreté par Migration

### Migration A : `0013_score_unique_copy_constraint`

| Critère | Évaluation |
|---------|------------|
| **Destructive ?** | NON — n'exécute aucun `DELETE`, `UPDATE`, `ALTER COLUMN`, `DROP TABLE`. Ajoute uniquement une contrainte. |
| **Réversible ?** | OUI — `RemoveConstraint(model_name='score', name='uniq_score_per_copy')` ou `ALTER TABLE grading_score DROP CONSTRAINT uniq_score_per_copy;` |
| **Risque de casse si données existantes ?** | **ÉLEVÉ si doublons existent.** PostgreSQL lèvera `ERROR: could not create unique index "uniq_score_per_copy" DETAIL: Key (copy_id)=(<uuid>) is duplicated.` |
| **Risque de blocage si données incohérentes ?** | **ÉLEVÉ.** L'échec bloque la migration 0013 et TOUTES les migrations futures de l'app `grading`. |
| **Risque de lock prolongé ?** | **FAIBLE.** La table `grading_score` contient ~151 rows (151 copies avec scores sur 209). La création d'un index unique sur 151 rows prend < 1 seconde. Mais pendant cette opération, la table est lockée en `ACCESS EXCLUSIVE` (PostgreSQL default pour `ALTER TABLE ADD CONSTRAINT`). |
| **Nécessité d'audit préalable ?** | **OBLIGATOIRE.** Il faut vérifier l'absence de doublons AVANT exécution. |

### Migration B : `0023_copy_performance_indexes_lot8`

| Critère | Évaluation |
|---------|------------|
| **Destructive ?** | NON — `CREATE INDEX` uniquement. |
| **Réversible ?** | OUI — `RemoveIndex` ou `DROP INDEX idx_copy_status; DROP INDEX idx_copy_exam_status; DROP INDEX idx_copy_corrector_status;` |
| **Risque de casse si données existantes ?** | **NUL.** Un `CREATE INDEX` non-unique ne peut pas échouer à cause des données (contrairement à `CREATE UNIQUE INDEX`). |
| **Risque de blocage si données incohérentes ?** | **NUL.** Aucune contrainte d'unicité, aucun check de cohérence. |
| **Risque de lock prolongé ?** | **TRÈS FAIBLE.** La table `exams_copy` contient 209 rows. 3 × `CREATE INDEX` sur 209 rows ≈ millisecondes. MAIS : chaque `CREATE INDEX` (non-`CONCURRENTLY`) acquiert un `SHARE` lock qui bloque les `INSERT`/`UPDATE`/`DELETE` pendant la durée de la création. Sur 209 rows, cela dure < 100ms par index. |
| **Nécessité d'audit préalable ?** | **Recommandé** — vérifier que les anciens index (0014/0015) n'existent plus (supprimés par 0016). Si ils existent encore, la migration créera des index redondants. |

---

## 3. Focus Spécial : Migration d'Unicité `Score.copy`

### 3.1. Scénario exact d'échec si des doublons existent

**Étape par étape :**

1. Django exécute `python manage.py migrate grading 0013`.
2. Django ouvre une transaction et exécute :
   ```sql
   ALTER TABLE "grading_score" ADD CONSTRAINT "uniq_score_per_copy" UNIQUE ("copy_id");
   ```
3. PostgreSQL tente de créer un index unique B-tree sur `grading_score.copy_id`.
4. PostgreSQL scanne **toutes les lignes** de la table pour construire l'index.
5. PostgreSQL détecte que deux (ou plus) lignes ont la même valeur `copy_id`.
6. PostgreSQL **interrompt** la création de l'index et lève :
   ```
   django.db.utils.IntegrityError: could not create unique index "uniq_score_per_copy"
   DETAIL:  Key (copy_id)=(xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx) is duplicated.
   ```
7. Django catch l'erreur et **rollback** la transaction.

### 3.2. Effet exact côté PostgreSQL

- Le `ALTER TABLE ADD CONSTRAINT UNIQUE` est exécuté dans une **transaction implicite** gérée par Django.
- En cas d'échec, PostgreSQL effectue un **ROLLBACK** complet.
- L'index partiel qui était en cours de construction est **supprimé automatiquement**.
- La table `grading_score` revient **exactement** à son état antérieur : mêmes données, mêmes index, aucune contrainte ajoutée.

### 3.3. La base revient-elle proprement à l'état antérieur ?

**OUI, avec une nuance importante :**

- Les **données** sont intactes (ROLLBACK garanti par PostgreSQL ACID).
- Les **index existants** sont intacts.
- **Aucune** nouvelle contrainte n'est ajoutée.
- La table `django_migrations` n'enregistre **PAS** la migration 0013 (car le ROLLBACK annule aussi l'insertion dans `django_migrations`).

**Nuance** : si la migration fait partie d'un batch (`migrate` sans spécifier l'app), Django exécute chaque migration dans sa propre transaction. L'échec de 0013 n'annule PAS les migrations des autres apps déjà commitées. Mais les migrations suivantes de `grading` ne seront pas exécutées.

### 3.4. Les autres migrations sont-elles bloquées ?

**OUI pour l'app `grading`.** Toutes les futures migrations de `grading` (0014, 0015...) seront bloquées car Django refuse d'appliquer une migration si la précédente dans la chaîne de dépendances n'est pas marquée comme appliquée.

**NON pour les autres apps.** Les migrations de `exams`, `students`, `core` etc. ne dépendent pas de `grading/0013` et seront appliquées normalement.

**Exception** : la migration `exams/0023` ne dépend PAS de `grading/0013`. Elle peut être appliquée indépendamment.

### 3.5. Comment détecter précisément les doublons

**Query de détection exhaustive :**

```sql
-- 1. Compter les doublons
SELECT copy_id, COUNT(*) AS nb_scores
FROM grading_score
GROUP BY copy_id
HAVING COUNT(*) > 1
ORDER BY nb_scores DESC;
```

**Query de qualification des doublons (si trouvés) :**

```sql
-- 2. Détail de chaque doublon : quel score a été créé quand, avec quelles données
SELECT 
    s.id AS score_id,
    s.copy_id,
    c.anonymous_id,
    c.exam_id,
    e.name AS exam_name,
    c.assigned_corrector_id,
    u.username AS corrector,
    s.created_at,
    s.updated_at,
    jsonb_object_keys(s.scores_data::jsonb) AS sample_key_count,
    (SELECT COUNT(*) FROM jsonb_object_keys(s.scores_data::jsonb)) AS nq,
    (SELECT ROUND(SUM(value::numeric)::numeric, 2) 
     FROM jsonb_each_text(s.scores_data::jsonb) 
     WHERE value ~ '^[0-9]') AS total_score,
    s.final_comment
FROM grading_score s
JOIN exams_copy c ON s.copy_id = c.id
JOIN exams_exam e ON c.exam_id = e.id
LEFT JOIN auth_user u ON c.assigned_corrector_id = u.id
WHERE s.copy_id IN (
    SELECT copy_id FROM grading_score GROUP BY copy_id HAVING COUNT(*) > 1
)
ORDER BY s.copy_id, s.created_at;
```

**Note** : la query ci-dessus utilise `jsonb_object_keys` — si `scores_data` est stocké en `json` (pas `jsonb`), remplacer par `json_object_keys`. Django `JSONField` sur PostgreSQL utilise `jsonb` par défaut.

### 3.6. Comment qualifier les doublons

Pour chaque paire de doublons, il faut déterminer :

| Question | Signification | Action |
|----------|--------------|--------|
| L'un est vide (`scores_data = {}`) et l'autre non ? | Score placeholder vs score réel | Supprimer le vide |
| Les deux ont le même `scores_data` ? | Doublon exact (safe à dédupliquer) | Garder le plus récent (`updated_at`) |
| Les deux ont des `scores_data` différents ? | **Conflit réel** — deux versions de notes | Investigation manuelle obligatoire |
| L'un a plus de questions que l'autre ? | Recovery partielle vs complète | Garder le plus complet (plus de questions) |
| Les `updated_at` sont très proches (< 5s) ? | Race condition entre API et script recovery | Garder le plus récent |

### 3.7. Stratégies conservatrices de traitement sans perte injustifiée

**Stratégie 1 : Backup → Merge → Delete (recommandée)**

```sql
-- Étape 1 : Backup complet de la table
CREATE TABLE grading_score_backup_pre_dedup AS SELECT * FROM grading_score;

-- Étape 2 : Pour chaque doublon, identifier le "meilleur" score
-- (plus de questions renseignées = plus complet)
WITH ranked AS (
    SELECT 
        s.id,
        s.copy_id,
        (SELECT COUNT(*) FROM jsonb_each_text(s.scores_data::jsonb) 
         WHERE value IS NOT NULL AND value != '' AND value != 'null') AS nq_filled,
        s.updated_at,
        ROW_NUMBER() OVER (
            PARTITION BY s.copy_id 
            ORDER BY 
                (SELECT COUNT(*) FROM jsonb_each_text(s.scores_data::jsonb) 
                 WHERE value IS NOT NULL AND value != '' AND value != 'null') DESC,
                s.updated_at DESC
        ) AS rn
    FROM grading_score s
    WHERE s.copy_id IN (
        SELECT copy_id FROM grading_score GROUP BY copy_id HAVING COUNT(*) > 1
    )
)
-- Étape 3 : Vérifier AVANT suppression
SELECT id, copy_id, nq_filled, updated_at, rn,
       CASE WHEN rn = 1 THEN 'KEEP' ELSE 'DELETE' END AS action
FROM ranked;

-- Étape 4 : Supprimer les doublons inférieurs (rn > 1) SEULEMENT après vérification manuelle
DELETE FROM grading_score 
WHERE id IN (
    SELECT id FROM ranked WHERE rn > 1
);
```

**Stratégie 2 : Data migration Django (automatique mais plus risquée)**

Transformer la migration 0013 en deux étapes :
1. `RunPython` : déduplication programmatique
2. `AddConstraint` : ajout de la contrainte

Je **déconseille** cette approche car elle automatise une suppression de données sur des notes réelles sans contrôle humain.

**Stratégie 3 : Migration conditionnelle (la plus sûre)**

Ajouter un `RunPython` pré-check qui vérifie l'absence de doublons et lève `MigrationError` avec un message explicite si des doublons sont trouvés, AVANT de tenter l'`AddConstraint`.

---

## 4. Pré-Checks Obligatoires Avant Passage en Production

Toutes les requêtes ci-dessous doivent être exécutées **sur la base de production** (`korrigo_db`) via :
```bash
docker exec -it <container_db> psql -U korrigo_user -d korrigo_db
```

### 4.1. Doublons sur `Score.copy` (CRITIQUE — bloquant pour migration 0013)

```sql
-- Pré-check 1 : Existence de doublons
SELECT copy_id, COUNT(*) AS nb 
FROM grading_score 
GROUP BY copy_id 
HAVING COUNT(*) > 1;

-- Résultat attendu : 0 rows → GO
-- Résultat bloquant : ≥ 1 row → NO-GO, traitement manuel requis
```

### 4.2. Volume des tables concernées

```sql
-- Pré-check 2 : Volume
SELECT 
    'grading_score' AS table_name, 
    COUNT(*) AS row_count,
    pg_size_pretty(pg_total_relation_size('grading_score')) AS total_size
FROM grading_score
UNION ALL
SELECT 
    'exams_copy', 
    COUNT(*),
    pg_size_pretty(pg_total_relation_size('exams_copy'))
FROM exams_copy;

-- Résultat attendu : grading_score ~151 rows, exams_copy ~209 rows
-- Si >> 1000 rows : revoir la stratégie de lock
```

### 4.3. Incohérences de références FK (Score → Copy)

```sql
-- Pré-check 3 : Scores orphelins (copy_id pointe vers une Copy inexistante)
SELECT s.id AS score_id, s.copy_id
FROM grading_score s
LEFT JOIN exams_copy c ON s.copy_id = c.id
WHERE c.id IS NULL;

-- Résultat attendu : 0 rows
-- Si ≥ 1 : scores orphelins à nettoyer avant migration (sinon la contrainte
-- FK existe déjà et aurait dû les empêcher, mais vérifier quand même)
```

### 4.4. État des index existants sur les tables concernées

```sql
-- Pré-check 4 : Index existants sur grading_score
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'grading_score';

-- Vérifier : pas d'index nommé 'uniq_score_per_copy' déjà existant
-- Attendu : un index FK automatique sur copy_id (type btree, non-unique)
```

```sql
-- Pré-check 5 : Index existants sur exams_copy
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'exams_copy';

-- Vérifier :
-- 1. Pas d'index nommé 'idx_copy_status', 'idx_copy_exam_status', 'idx_copy_corrector_status'
-- 2. Pas d'anciens index 'exams_copy_status_idx', 'exams_copy_exam_status_idx',
--    'exams_copy_assigned_corrector_idx', 'exams_copy_dispatch_run_idx'
--    (supprimés par migration 0016 — vérifier que c'est bien le cas)
```

### 4.5. État de la table `django_migrations`

```sql
-- Pré-check 6 : Vérifier quelles migrations sont appliquées
SELECT app, name, applied 
FROM django_migrations 
WHERE app IN ('grading', 'exams') 
ORDER BY app, name;

-- Vérifier :
-- grading: 0001 à 0012 doivent être appliquées, 0013 ne doit PAS être appliquée
-- exams: jusqu'à 0022 doivent être appliquées, 0023 ne doit PAS être appliquée
-- CRITIQUE : vérifier que 0016 (RemoveIndex) est bien appliquée
```

### 4.6. Scores avec scores_data NULL ou vide

```sql
-- Pré-check 7 : Scores avec données manquantes
SELECT s.id, s.copy_id, c.anonymous_id, s.scores_data, s.created_at
FROM grading_score s
JOIN exams_copy c ON s.copy_id = c.id
WHERE s.scores_data IS NULL 
   OR s.scores_data::text = '{}'
   OR s.scores_data::text = 'null';

-- Si résultat non vide : ces rows ne sont pas des doublons mais des
-- scores vides (placeholder). Ils comptent quand même pour l'unicité.
```

### 4.7. Vérification des écritures concurrentes

```sql
-- Pré-check 8 : Connexions actives sur la base
SELECT pid, usename, application_name, state, query_start, query
FROM pg_stat_activity
WHERE datname = 'korrigo_db' AND state != 'idle';

-- Si des writes sont en cours sur grading_score ou exams_copy,
-- attendre qu'ils terminent avant de migrer.
```

---

## 5. Hypothèses Dangereuses Portées par les Migrations

### Hypothèse 1 : « Absence de doublons Score.copy »

**Statut : DANGEREUSE — non vérifiée.**

Les scripts de recovery localStorage (`import_laroussi_scores.py`, `import_patrick_scores.py`, `import_sami_scores.py`, `import_selima_scores.py`, `fix_laroussi_scores.py`) utilisent tous un pattern **check-then-act non atomique** :

```python
existing = Score.objects.filter(copy=copy).first()
if existing:
    existing.scores_data = ...
    existing.save()
else:
    Score.objects.create(copy=copy, scores_data=...)
```

Ce pattern est vulnérable à une race condition : si un correcteur sauvegarde via l'API (`CopyScoresView.put` → `update_or_create`) entre le `filter().first()` et le `create()`, un doublon est créé. En pratique, ces scripts étaient exécutés manuellement et séquentiellement, mais **aucune preuve formelle** que ce scénario ne s'est jamais produit.

De plus, si un script a été exécuté deux fois (erreur humaine, debugging), le second run trouverait un score existant (créé par le premier run) et le mettrait à jour — pas de doublon dans ce cas. Mais si le script a été lancé en parallèle (deux terminaux), le doublon est possible.

**Conclusion : le pré-check SQL est OBLIGATOIRE, pas optionnel.**

### Hypothèse 2 : « Cohérence des scores historiques (scores_data non corrompu) »

**Statut : PARTIELLEMENT VÉRIFIÉE.**

L'incident Laroussi (question fantôme `4.1.3`) a démontré que les scripts de recovery peuvent introduire des corruptions dans `scores_data`. Le fix a été appliqué (migration `fix_laroussi_scores.py`), mais il n'y a pas de contrainte DB validant la structure de `scores_data`. La migration 0013 ne change rien à ce risque — elle ne touche pas le contenu de `scores_data`.

### Hypothèse 3 : « Validité des FK (Score.copy → Copy) »

**Statut : NORMALEMENT GARANTIE par PostgreSQL.**

La FK est déclarée avec `ON DELETE CASCADE` depuis la migration `0010_score`. PostgreSQL enforce cette contrainte à chaque INSERT/UPDATE. Mais si un dump/restore a été fait avec `--no-constraints` ou si des manipulations manuelles `psql` ont eu lieu, des FK orphelines sont possibles. Le pré-check 3 vérifie ça.

### Hypothèse 4 : « Volume faible (~151 scores, ~209 copies) »

**Statut : PROBABLEMENT VRAIE mais à confirmer.**

Si des tests ou des scripts de charge ont été exécutés sur la base de production (ce qui arrive), le volume pourrait être supérieur. Le pré-check 2 le vérifie.

### Hypothèse 5 : « Absence d'écriture concurrente pendant la migration »

**Statut : DANGEREUSE si pas de fenêtre de maintenance.**

`ALTER TABLE ADD CONSTRAINT UNIQUE` acquiert un `ACCESS EXCLUSIVE` lock sur `grading_score`. Pendant ce lock :
- Tout `INSERT` ou `UPDATE` sur `grading_score` est **bloqué**.
- Tout `SELECT` sur `grading_score` est **bloqué** (c'est le niveau le plus restrictif).
- Si un correcteur est en train de sauvegarder des notes via l'API au même moment, son request sera bloquée pendant la durée du lock (~< 1s pour 151 rows), puis réussira ou échouera selon les données.

`CREATE INDEX` (non-`CONCURRENTLY`) acquiert un `SHARE` lock sur `exams_copy`. Pendant ce lock :
- Les `SELECT` passent.
- Les `INSERT`/`UPDATE`/`DELETE` sont **bloqués**.

Sur 209 rows, le lock dure < 100ms. Mais si un correcteur fait un `PUT` sur `CopyScoresView` exactement pendant ces millisecondes, sa requête sera **mise en attente**, pas échouée.

### Hypothèse 6 : « Les anciens index (0014/0015) ont été supprimés par 0016 »

**Statut : À VÉRIFIER.**

Le serveur a été réinstallé le 26 février depuis un dump du 20 février. Si les migrations 0014-0016 étaient appliquées au moment du dump, elles sont dans `django_migrations` et les index ont été supprimés. Mais il faut **vérifier** via le pré-check 5.

Si les anciens index existent encore, la migration 0023 créera des index **en doublon** (noms différents, mêmes colonnes). Ce n'est pas une erreur mais c'est du gaspillage.

---

## 6. Verdict par Migration

### Migration A : `0013_score_unique_copy_constraint`

**Verdict : ⚠️ SÛRE SI AUDIT PRÉALABLE**

Justification :
- La migration est non-destructive (ADD CONSTRAINT, pas de DELETE/UPDATE).
- La migration est réversible (DROP CONSTRAINT).
- La migration est atomique (PostgreSQL ROLLBACK en cas d'échec).
- **MAIS** elle échouera irrémédiablement si des doublons existent, et bloquera toutes les futures migrations `grading`.
- Le pré-check 1 (doublons) est **obligatoire et bloquant**.
- Les scripts de recovery utilisent un pattern non-atomique qui rend les doublons **théoriquement possibles**.

### Migration B : `0023_copy_performance_indexes_lot8`

**Verdict : ✅ SÛRE EN L'ÉTAT**

Justification :
- 3 × `CREATE INDEX` non-unique — ne peut pas échouer à cause des données.
- Réversible (DROP INDEX).
- Lock très court (< 300ms total pour 209 rows).
- Le seul risque est la **redondance** si les anciens index existent encore. Ce n'est pas bloquant mais un pré-check est **recommandé**.

---

## 7. Stratégie de Passage en Production Recommandée

### Protocole Strict

#### Phase 0 : Préparation (J-1 ou avant)

1. **Backup complet de la base** :
   ```bash
   docker exec <container_db> pg_dump -U korrigo_user -Fc korrigo_db > /var/www/labomaths/korrigo/backups/pre_migration_lot8_$(date +%Y%m%d_%H%M%S).dump
   ```

2. **Backup granulaire de la table Score** :
   ```bash
   docker exec <container_db> psql -U korrigo_user -d korrigo_db -c "COPY (SELECT * FROM grading_score) TO STDOUT WITH CSV HEADER;" > grading_score_backup.csv
   ```

3. **Déployer les fichiers** (overlay backend) **SANS migrer**.

#### Phase 1 : Pré-Checks (J0, en production, AVANT migration)

Exécuter les 8 pré-checks de la section 4, dans l'ordre. Critères go/no-go :

| Pré-check | Résultat GO | Résultat NO-GO |
|-----------|-------------|----------------|
| 1. Doublons Score.copy | 0 rows | ≥ 1 row → STOP, traitement manuel |
| 2. Volume tables | < 1000 rows chaque | > 10000 → revoir stratégie lock |
| 3. FK orphelines | 0 rows | ≥ 1 → nettoyer d'abord |
| 4. Index Score existants | 1 index FK, pas de `uniq_score_per_copy` | `uniq_score_per_copy` existe déjà → skip 0013 |
| 5. Index Copy existants | Pas d'anciens index 0014/0015 | Anciens index présents → noter (pas bloquant) |
| 6. django_migrations | 0012 appliquée, 0013 non | 0013 déjà appliquée → skip |
| 7. Scores vides | Informatif | Informatif |
| 8. Connexions actives | Pas de writes en cours | Attendre idle |

#### Phase 2 : Fenêtre de Maintenance (recommandée)

**Même si le lock dure < 1s sur 151 rows, je recommande une micro-fenêtre de 5 minutes** :
1. Prévenir les correcteurs (message Slack/email : « maintenance 5 min »).
2. Optionnel : couper l'accès frontend (nginx 503) ou simplement attendre que l'activité soit basse (soir/nuit).
3. Exécuter la migration.

**Raison** : en cas de problème (doublon non détecté, erreur inattendue), il faut pouvoir investiguer sans pression.

#### Phase 3 : Exécution

**Ordre obligatoire : migration B AVANT migration A.**

Raison : migration B (index) ne peut pas échouer. Si migration A échoue ensuite, au moins les index de performance sont en place.

```bash
# Étape 1 : Index Copy (safe, ne peut pas échouer)
docker exec <container_backend> python manage.py migrate exams 0023

# Étape 2 : Contrainte Score (peut échouer si doublons)
docker exec <container_backend> python manage.py migrate grading 0013
```

**Ne PAS exécuter `migrate` sans spécifier l'app** — migrer app par app, séquentiellement, pour isoler les erreurs.

#### Phase 4 : Vérifications Post-Migration

```sql
-- Vérif 1 : Contrainte Score bien créée
SELECT conname, contype 
FROM pg_constraint 
WHERE conrelid = 'grading_score'::regclass AND conname = 'uniq_score_per_copy';
-- Attendu : 1 row, contype = 'u' (unique)

-- Vérif 2 : Index Copy bien créés
SELECT indexname FROM pg_indexes 
WHERE tablename = 'exams_copy' AND indexname LIKE 'idx_copy_%';
-- Attendu : 3 rows

-- Vérif 3 : django_migrations à jour
SELECT app, name FROM django_migrations 
WHERE (app = 'grading' AND name = '0013_score_unique_copy_constraint')
   OR (app = 'exams' AND name = '0023_copy_performance_indexes_lot8');
-- Attendu : 2 rows

-- Vérif 4 : Test fonctionnel — l'API score write fonctionne encore
-- (tester manuellement un PUT /api/grading/copies/<uuid>/scores/ avec un score valide)
```

#### Phase 5 : Rollback (si nécessaire)

```bash
# Rollback migration A (si problème)
docker exec <container_backend> python manage.py migrate grading 0012

# Rollback migration B (si problème)
docker exec <container_backend> python manage.py migrate exams 0022
```

Ou en SQL direct :
```sql
-- Rollback contrainte Score
ALTER TABLE grading_score DROP CONSTRAINT IF EXISTS uniq_score_per_copy;
DELETE FROM django_migrations WHERE app = 'grading' AND name = '0013_score_unique_copy_constraint';

-- Rollback index Copy
DROP INDEX IF EXISTS idx_copy_status;
DROP INDEX IF EXISTS idx_copy_exam_status;
DROP INDEX IF EXISTS idx_copy_corrector_status;
DELETE FROM django_migrations WHERE app = 'exams' AND name = '0023_copy_performance_indexes_lot8';
```

---

## 8. Impact sur les Données Existantes

### Migration A : `0013_score_unique_copy_constraint`

**Ce qu'elle ne modifie pas :**
- Aucune valeur dans `grading_score` n'est modifiée (pas de `UPDATE`).
- Aucune ligne n'est supprimée (pas de `DELETE`).
- Les colonnes ne changent pas de type, de nullabilité, de default.
- Les autres tables (`exams_copy`, `grading_annotation`, `grading_questionremark`, `grading_gradingevent`, `grading_draftstate`) ne sont pas touchées.
- Les `scores_data` JSON ne sont pas validés ni modifiés.
- Les `final_comment` ne sont pas touchés.
- Les timestamps `created_at`/`updated_at` ne sont pas modifiés.

**Ce qu'elle pourrait bloquer :**
- Si des doublons existent → la migration elle-même est bloquée, et toutes les futures migrations `grading`.
- Après application réussie → tout futur `Score.objects.create(copy=copy_deja_scoree)` échouera avec `IntegrityError`. L'API (`CopyScoresView.put`) utilise `update_or_create` qui est safe. Mais les scripts de recovery utilisent `create()` qui **ne l'est plus** si un Score existe déjà.

**Ce qu'elle pourrait rendre temporairement indisponible :**
- Pendant le `ALTER TABLE ADD CONSTRAINT` (< 1s pour 151 rows), la table `grading_score` est lockée en `ACCESS EXCLUSIVE`. Toute requête touchant cette table (GET scores, PUT scores, pages correcteur) sera **mise en attente** pendant cette durée.

**Pourquoi elle ne doit pas être présentée comme "sans risque" sans pré-check :**
- Les scripts de recovery ont utilisé un pattern non-atomique (`filter().first()` + `create()`).
- L'historique du projet inclut des imports d'urgence, des corruptions corrigées (4.1.3 Laroussi), des réinstallations serveur. Ce n'est **pas** un environnement vierge et propre.
- La seule preuve que les doublons n'existent pas est le pré-check SQL. Toute assertion sans cette preuve est **spéculative**.

### Migration B : `0023_copy_performance_indexes_lot8`

**Ce qu'elle ne modifie pas :**
- Aucune donnée. `CREATE INDEX` ne touche que les métadonnées/structures PostgreSQL.
- Aucune colonne. Pas de `ALTER COLUMN`.
- Aucune autre table.

**Ce qu'elle pourrait bloquer :**
- Rien. Un `CREATE INDEX` non-unique ne peut pas échouer à cause du contenu des données.

**Ce qu'elle pourrait rendre temporairement indisponible :**
- Pendant les `CREATE INDEX` (< 100ms × 3 = < 300ms total pour 209 rows), les writes sur `exams_copy` sont bloqués. En pratique, aucun endpoint critique ne fait de write sur `exams_copy` pendant que les correcteurs corrigent.

**Pourquoi elle ne doit pas être présentée comme "sans risque" sans pré-check :**
- Si les anciens index (0014/0015) n'ont pas été supprimés par 0016 (état de migration incohérent), la migration créera des index en doublon. Ce n'est pas dangereux mais c'est une incohérence silencieuse qui complexifie le schéma.
- La seule preuve que les anciens index n'existent plus est le pré-check 5. Sans cette vérification, on accumule potentiellement des index redondants.

---

## Résumé Exécutif

| Migration | Verdict | Pré-check obligatoire | Risque données | Lock estimé |
|-----------|---------|----------------------|----------------|-------------|
| `0013` UniqueConstraint Score.copy | ⚠️ Sûre si audit | OUI — doublons | NUL si pas de doublons, BLOQUANT sinon | < 1s |
| `0023` Index ×3 Copy | ✅ Sûre en l'état | Recommandé — anciens index | NUL | < 300ms |

**Décision critique :** le pré-check 1 (doublons Score.copy) est un **GO/NO-GO absolu**. Aucune migration ne doit être exécutée avant d'avoir la réponse à cette query. Si des doublons existent, il faut les traiter manuellement (avec backup, qualification, et validation humaine) AVANT toute migration.
