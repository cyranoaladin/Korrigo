# Schéma de Base de Données — Korrigo v2

> **Version** : 3.0
> **Date** : 2026-03-28
> **Migration la plus récente** : `exams/0028_copy_finalizing_at`
> **Base de données** : PostgreSQL 15

---

## Table des Matières

1. [Vue d'ensemble](#vue-densemble)
2. [App exams](#app-exams)
3. [App grading](#app-grading)
4. [App students](#app-students)
5. [App identification](#app-identification)
6. [App core](#app-core)
7. [Diagramme de relations](#diagramme-de-relations)
8. [Historique des migrations](#historique-des-migrations)

---

## Vue d'ensemble

Korrigo utilise **PostgreSQL 15** avec le modèle ORM Django. Toutes les clés primaires des entités métier sont des **UUIDs** (sauf `students_student` qui utilise un AutoField entier). Les coordonnées d'annotations sont normalisées `[0,1]` (ADR-002). Le statut d'une copie est une machine à 3 états : READY / IN_PROGRESS / FINALIZED (ADR-003).

---

## App exams

### `exams_examtype`

Catalogue des types d'examens (Bac Blanc, DNB, EAM…).

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | integer | PK, auto | |
| `code` | varchar(20) | UNIQUE, NOT NULL | Code court (ex : `BB2026`, `DNBM2026`) |
| `name` | varchar(100) | NOT NULL | Nom complet |
| `color` | varchar(7) | NOT NULL | Code couleur hex |
| `icon` | varchar(50) | NOT NULL | Icône Lucide |
| `is_active` | boolean | NOT NULL, default=True | Actif / archivé |

---

### `exams_exam`

Entité principale représentant un examen ou une session d'examen.

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | uuid | PK | |
| `name` | varchar(200) | NOT NULL | Nom (ex : `DNB_2026`, `BB_J1`) |
| `date` | date | NOT NULL | Date de l'épreuve |
| `upload_mode` | varchar(20) | NOT NULL, default=`BATCH_A3` | `BATCH_A3` ou `INDIVIDUAL_A4` |
| `pdf_source` | varchar(255) | NULL | Chemin du PDF original (BATCH_A3) |
| `grading_structure` | jsonb | NULL | Structure questions + barèmes |
| `results_released_at` | timestamptz | NULL | Date de publication aux élèves |
| `exam_type_id` | integer | FK → `exams_examtype`, NULL | |
| `created_at` | timestamptz | NOT NULL, auto | |
| `updated_at` | timestamptz | NOT NULL, auto | |

**Relation M:M correcteurs** via `exams_exam_correctors(exam_id uuid, user_id integer)`

**Index** : `(name)`, `(date)`, `(exam_type_id)`

**Format JSON `grading_structure`** :
```json
{
  "exercices": [
    {"id": "ex1", "label": "Exercice 1", "max": 5,
     "questions": [{"id": "q1.1", "label": "Q1", "max": 2}]}
  ],
  "total_max": 20
}
```

---

### `exams_booklet`

Fascicule (groupe de pages) extrait d'un PDF batch ou lié à un PDF individuel.

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | uuid | PK | |
| `exam_id` | uuid | FK → `exams_exam`, NOT NULL | |
| `start_page` | integer | NOT NULL | Début (1-indexé) |
| `end_page` | integer | NOT NULL | Fin incluse |
| `header_image` | varchar(255) | NULL | Image en-tête pour OCR |
| `student_name_guess` | varchar(200) | NULL | Nom détecté par OCR |
| `pages_images` | jsonb | NOT NULL | `["copies/pages/<id>/p000.png", ...]` |

---

### `exams_copy` ⭐ (Entité centrale)

Représente la copie d'un élève. Point de convergence de toute la logique métier.

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | uuid | PK | |
| `exam_id` | uuid | FK → `exams_exam`, NOT NULL, PROTECT | Examen parent |
| `anonymous_id` | varchar(50) | UNIQUE, NOT NULL | Identifiant d'anonymat |
| `final_pdf` | varchar(255) | NULL | PDF corrigé aplati (`copies/final/…`) |
| `pdf_source` | varchar(255) | NULL | PDF source (`copies/source/…`) |
| `status` | varchar(20) | NOT NULL, default=`READY` | `READY` / `IN_PROGRESS` / `FINALIZED` |
| `student_id` | integer | FK → `students_student`, NULL, SET_NULL | Élève identifié |
| `is_identified` | boolean | NOT NULL, default=False | True si `student_id` défini |
| `assigned_corrector_id` | integer | FK → `auth_user`, NULL, SET_NULL | Correcteur assigné |
| `dispatch_run_id` | uuid | NULL | UUID de la session de dispatch |
| `assigned_at` | timestamptz | NULL | Horodatage dispatch |
| `validated_at` | timestamptz | NULL | Horodatage validation initiale |
| `grading_error_message` | text | NULL | Erreur de finalisation |
| `grading_retries` | integer | NOT NULL, default=0 | Tentatives échouées |
| `locked_at` | timestamptz | NULL | Legacy (non utilisé activement) |
| `locked_by_id` | integer | FK → `auth_user`, NULL | Legacy |
| `graded_at` | timestamptz | NULL | Horodatage finalisation |
| `global_appreciation` | text | NULL | Appréciation globale du correcteur |
| `llm_summary` | text | NULL | Bilan IA (Ollama) |
| `subject_variant` | varchar(1) | NULL | `A` ou `B` — obsolète, conservé pour compatibilité |
| `finalizing_at` | timestamptz | NULL | **Mutex atomique anti-doublon** |

**Index** :
- `idx_copy_status` sur `(status)`
- `idx_copy_exam_status` sur `(exam_id, status)`
- `idx_copy_corrector_status` sur `(assigned_corrector_id, status)`

**Relation M:M booklets** via `exams_copy_booklets(copy_id uuid, booklet_id uuid)`

**Machine à états `status`** (ADR-003 v3) :
```
READY ──[1ère annotation]──→ IN_PROGRESS ──[POST /finalize/]──→ FINALIZED
  ↑                                                                   │
  └───────────────────[POST /reopen/, superuser only]─────────────────┘
```

**Mutex `finalizing_at`** :
Protège contre la double finalisation concurrente. L'UPDATE conditionnel atomique `SET finalizing_at=NOW() WHERE finalizing_at IS NULL` garantit qu'une seule requête concurrente passe. Libéré (`=NULL`) sur succès, annulé par rollback sur échec.

**Validateurs `pdf_source`** : extension `.pdf`, max 50 MB, max 500 pages, vrai PDF (magic bytes + parseable PyMuPDF).

---

### `exams_exampdf`

PDF individuel uploadé (mode INDIVIDUAL_A4, ex : workflow DNB).

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | uuid | PK | |
| `exam_id` | uuid | FK → `exams_exam`, NOT NULL | |
| `pdf_file` | varchar(255) | NOT NULL | Chemin du PDF |
| `student_identifier` | varchar(200) | NOT NULL | Format `NOM_PRENOM_DDMMYYYY` |
| `uploaded_at` | timestamptz | NOT NULL, auto | |

Le `student_identifier` est parsé par `identify_dnb_copies` pour faire le matching DDN+nom avec la table `students_student`.

---

### `exams_examdocumentset`

Ensemble de documents pédagogiques liés à un examen.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | uuid | PK |
| `exam_id` | uuid | FK → `exams_exam` |
| `version` | varchar(20) | Ex : `v1` |
| `label` | varchar(100) | Ex : "Sujet + Corrigé" |
| `is_active` | boolean | |
| `created_by_id` | integer | FK → `auth_user` |
| `created_at` | timestamptz | auto |

---

## App grading

### `grading_annotation`

Annotation vectorielle posée par un correcteur sur une page.

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | uuid | PK | |
| `copy_id` | uuid | FK → `exams_copy`, CASCADE | |
| `page_index` | integer | NOT NULL, ≥0 | Index de page 0-based |
| `x` | float | NOT NULL | Position X ∈ [0,1] |
| `y` | float | NOT NULL | Position Y ∈ [0,1] |
| `w` | float | NOT NULL | Largeur ∈ (0,1] |
| `h` | float | NOT NULL | Hauteur ∈ (0,1] |
| `content` | text | NOT NULL, default='' | Texte de l'annotation |
| `type` | varchar(20) | NOT NULL | `COMMENT`/`HIGHLIGHT`/`ERROR`/`BONUS`/`VRAI`/`FAUX` |
| `score_delta` | integer | NULL | Points (négatif possible) |
| `created_by_id` | integer | FK → `auth_user`, PROTECT | |
| `created_at` | timestamptz | auto | |
| `updated_at` | timestamptz | auto | |
| `version` | integer | NOT NULL, default=0 | Verrou optimiste (incrémenté à chaque update) |

**Règle** : modification impossible si `copy.status == FINALIZED`.

| Type | Couleur | Usage |
|------|---------|-------|
| `COMMENT` | Bleu | Commentaire libre |
| `HIGHLIGHT` | Jaune | Mise en évidence |
| `ERROR` | Rouge | Erreur pénalisante |
| `BONUS` | Vert | Bonus |
| `VRAI` | Vert ✓ | Réponse correcte |
| `FAUX` | Rouge ✗ | Réponse incorrecte |

---

### `grading_gradingevent`

Journal d'audit immuable. Une ligne par action sur une copie.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | uuid | PK |
| `copy_id` | uuid | FK → `exams_copy`, CASCADE |
| `action` | varchar(20) | Voir ci-dessous |
| `actor_id` | integer | FK → `auth_user` |
| `timestamp` | timestamptz | auto |
| `metadata` | jsonb | Données spécifiques |

| Action | Metadata typique |
|--------|-----------------|
| `IMPORT` | `{filename, pages}` |
| `VALIDATE` | `{}` |
| `LOCK` | `{token, ttl}` |
| `UNLOCK` | `{token}` |
| `CREATE_ANN` | `{annotation_id, page}` |
| `UPDATE_ANN` | `{annotation_id, changes: {}}` |
| `DELETE_ANN` | `{annotation_id}` |
| `FINALIZE` | `{final_score}` |
| `EXPORT` | `{format}` |
| `REOPEN` | `{old_status, old_pdf}` |
| `SAVE_APPREC` | `{length}` |

---

### `grading_score`

Notes structurées par question pour une copie.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | uuid | PK |
| `copy_id` | uuid | FK → `exams_copy`, UNIQUE |
| `scores_data` | jsonb | `{"ex1.q1": 1.5, "ex2.q1": 2.0, ...}` |
| `created_at` | timestamptz | auto |
| `updated_at` | timestamptz | auto |

---

### `grading_copylock`

Verrou pessimiste — un seul correcteur actif à la fois par copie.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | uuid | PK |
| `copy_id` | uuid | FK → `exams_copy`, UNIQUE |
| `owner_id` | integer | FK → `auth_user` |
| `token` | uuid | Token client (pour unlock/heartbeat) |
| `locked_at` | timestamptz | auto |
| `expires_at` | timestamptz | TTL (défaut now+1800s) |

---

### `grading_draftstate`

Sauvegarde automatique de l'état de correction (anti-perte de données).

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | uuid | PK |
| `copy_id` | uuid | FK → `exams_copy` |
| `owner_id` | integer | FK → `auth_user` |
| `content` | jsonb | État courant (annotations + notes) |
| `saved_at` | timestamptz | auto (mis à jour à chaque save) |

---

### `grading_questionremark`

Remarques structurées par chemin de question.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | uuid | PK |
| `copy_id` | uuid | FK → `exams_copy` |
| `question_path` | varchar(100) | Ex : `ex1.q2` |
| `remark_type` | varchar(50) | |
| `content` | text | |
| `created_by_id` | integer | FK → `auth_user` |
| `created_at` | timestamptz | auto |

---

### `grading_annotationtemplate`

Banque de commentaires fréquents.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | uuid | PK |
| `user_id` | integer | FK → `auth_user`, NULL = template global |
| `category` | varchar(100) | Ex : "Algèbre" |
| `content` | text | Texte du template |
| `is_global` | boolean | Visible par tous les correcteurs |
| `created_at` | timestamptz | auto |

---

## App students

### `students_student`

Profil élève. Clé d'identification : `(last_name, first_name, date_naissance)`.

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | integer | PK, auto | |
| `first_name` | varchar(100) | NOT NULL | Prénom (en MAJUSCULES) |
| `last_name` | varchar(100) | NOT NULL | Nom (en MAJUSCULES) |
| `date_naissance` | date | NOT NULL | Utilisée pour l'authentification |
| `email` | varchar(254) | NULL | Email = username Django |
| `class_name` | varchar(20) | NULL | Classe (ex : `3.5`) |
| `groupe` | varchar(50) | NULL | |
| `user_id` | integer | FK → `auth_user`, NULL, UNIQUE | Compte Django |

**Contrainte UNIQUE** : `(last_name, first_name, date_naissance)` — garantit l'idempotence des imports.

**Authentification** : POST `/api/students/login/` avec `{email, birth_date: "YYYY-MM-DD"}`.

---

## App identification

### `identification_ocrresult`

Résultat OCR sur l'en-tête d'une copie non-identifiée.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | uuid | PK |
| `copy_id` | uuid | FK → `exams_copy`, UNIQUE |
| `detected_text` | text | Texte brut extrait |
| `confidence` | float | Score [0,1] |
| `created_at` | timestamptz | auto |

**Relation M:M élèves suggérés** via `identification_ocrresult_suggested_students`

---

## App core

### `core_globalsettings`

Configuration globale de l'instance (singleton).

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | integer | PK |
| `institution_name` | varchar(200) | Nom de l'établissement |
| `theme` | varchar(50) | Thème UI |
| `default_exam_duration` | integer | Durée (minutes) |
| `notifications_enabled` | boolean | |

---

### `core_auditlog`

Journal RGPD — trace chaque accès aux données personnelles.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | integer | PK, auto |
| `timestamp` | timestamptz | auto |
| `user_id` | integer | FK → `auth_user`, NULL |
| `student_id` | varchar(100) | ID élève (string) |
| `action` | varchar(100) | Action effectuée |
| `resource_type` | varchar(100) | Type de ressource |
| `resource_id` | varchar(100) | ID de la ressource |
| `ip_address` | inet | IP client |
| `user_agent` | text | User-Agent |
| `metadata` | jsonb | Données supplémentaires |

---

### `core_userprofile`

Extension du profil utilisateur Django.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | integer | PK |
| `user_id` | integer | FK → `auth_user`, UNIQUE |
| `must_change_password` | boolean | Forcer changement mdp |

---

## Diagramme de relations

```
auth_user ────────────────────────────────────────────────────────────
  │ 1:1 → core_userprofile                                            │
  │ 1:1 ← students_student.user_id                                    │
  │ M:M ↔ exams_exam (correcteurs)                                    │
  │ 1:N → grading_annotation (created_by)                            │
  │ 1:N → grading_gradingevent (actor)                               │
  │ 1:N → core_auditlog                                              │
                                                                      │
exams_examtype ←── FK ── exams_exam                                   │
                              │                                       │
                    ┌─────────┼─────────────────────────┐            │
                    │         │                          │            │
              exams_booklet   │ 1:N               exams_exampdf      │
                    │         │                   (INDIVIDUAL_A4)    │
               M:M  ↓         │                                      │
              exams_copy ◄────┘                                      │
                  │                                                   │
                  ├── FK → students_student (student)                 │
                  ├── FK → auth_user (assigned_corrector) ────────────┘
                  │
                  ├── 1:N → grading_annotation
                  ├── 1:N → grading_gradingevent
                  ├── 1:1 → grading_copylock
                  ├── 1:1 → grading_score
                  ├── 1:1 → identification_ocrresult
                  └── 1:N → grading_draftstate
```

---

## Historique des migrations (app exams)

| N° | Nom | Description |
|----|-----|-------------|
| 0001–0012 | Schéma initial | Copy, Exam, Booklet, validateurs PDF, indexes |
| 0013 | dispatch_fields | `assigned_corrector`, `dispatch_run_id`, `assigned_at` |
| 0014 | error_tracking | `grading_error_message`, `grading_retries` |
| 0016–0018 | timestamps | Timestamps sur Exam |
| 0019 | results_released | `results_released_at` sur Exam |
| 0020 | subject_variant | `subject_variant` sur Copy |
| 0021 | annotation_templates | Modèle AnnotationTemplate |
| 0022 | document_sets | Modèle ExamDocumentSet |
| 0023 | llm_summary | `llm_summary` sur Copy |
| 0024 | exam_type | ExamType + JuryReport |
| 0025 | jury_report_exam_type | `exam_type` FK, suppression `exam` FK |
| **0026** | **simplify_copy_status** | **3 états : READY/IN_PROGRESS/FINALIZED** |
| 0027 | rename_copy_statuses | Renommage valeurs de statut |
| **0028** | **copy_finalizing_at** | **`Copy.finalizing_at` — mutex atomique** |
