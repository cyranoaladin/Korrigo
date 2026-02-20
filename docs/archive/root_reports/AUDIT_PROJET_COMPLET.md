# Audit Complet du Projet Korrigo

**Date** : 11 février 2026 | **Commit** : `fc393d6` (main)

---

## 1. Architecture Globale

| Couche | Technologie |
|--------|------------|
| **Backend** | Django 4.x + DRF, Gunicorn, Celery + Redis |
| **Frontend** | Vue 3 (Composition API), Pinia, Vue Router, Axios |
| **DB** | PostgreSQL 15 |
| **PDF** | PyMuPDF (fitz), EasyOCR, PaddleOCR |
| **Infra** | Docker Compose, Nginx, GitHub Actions CI/CD |

### Apps Django
- `core` — Auth, settings, health, metrics
- `exams` — Exam/Booklet/Copy/ExamPDF, upload, export
- `grading` — Annotations, locks, scores, drafts, workflow
- `processing` — PDF splitting, flattening, OCR
- `identification` — OCR-assisted student identification
- `students` — Student model, auth, CSV import

### Modèle de Données
```
Exam ──1:N──▶ Booklet ──M:N──▶ Copy ──1:N──▶ Annotation
                                 ├──1:1──▶ CopyLock
                                 ├──1:N──▶ GradingEvent (audit)
                                 ├──1:N──▶ DraftState
                                 ├──1:N──▶ Score
                                 └──N:1──▶ Student
```

---

## 2. Workflow Création Examen

### Deux modes d'upload

**BATCH_A3** (défaut) : Un PDF multi-pages → `PDFSplitter` découpe en booklets de N pages → N copies STAGING

**INDIVIDUAL_A4** : Plusieurs PDFs individuels → chaque PDF → ExamPDF + Copy(STAGING)

### Flux BATCH_A3
1. Frontend `ExamUploadModal` → `POST /api/exams/upload/` (FormData)
2. `ExamUploadView` : validation PDF (taille, MIME, intégrité, pages)
3. `transaction.atomic()` → `Exam.create()`
4. `PDFSplitter.split_exam()` : fitz.open → chunks de N pages → PNG 150 DPI
5. Pour chaque booklet → `Copy.create(STAGING)` + `copy.booklets.add()`
6. Return 201 + `booklets_created`

### Suite du workflow
```
STAGING ──validate──▶ READY ──lock──▶ LOCKED ──finalize──▶ GRADED
```
En parallèle : Agrafer, Barème, Video-Coding, Dispatcher

---

## 3. Problèmes Identifiés

### 🔴 CRITIQUES

**P1 — Traitement PDF synchrone bloquant**
- `exams/views.py:58-92` : Le split est synchrone dans la requête HTTP
- Un PDF 200 pages = 30-60s → timeout Gunicorn/Nginx
- **Fix** : Tâche Celery + statut de progression

**P2 — Copies bloquées en STAGING**
- Les copies sont créées en STAGING mais `CopyValidationView` (ligne 632) n'est PAS dans `urls.py`
- Aucun mécanisme auto pour passer STAGING → READY
- **Fix** : Exposer l'endpoint ou auto-valider après split

**P3 — `ExamSourceUploadView` crée des doublons**
- `views.py:582-631` : Re-upload crée de nouvelles copies sans supprimer les anciennes
- **Fix** : Vérifier/supprimer copies existantes avant re-processing

**P4 — Collision `anonymous_id`**
- `str(uuid4())[:8]` = 8 chars hex → collision à ~5000 copies (birthday paradox)
- `unique=True` → crash `IntegrityError`
- **Fix** : Compteur séquentiel par examen ou UUID complet

### 🟠 IMPORTANTS

**P5 — Deux flux de création incohérents**
- "Nouvel Examen" → `POST /api/exams/` (nom+date seulement, pas de PDF)
- "Importer Examen" → `POST /api/exams/upload/` (complet avec PDF)
- **Fix** : Fusionner en un seul wizard

**P6 — Timeout API trop court**
- `api.js:11` : `timeout: 10000` (10s) — insuffisant pour le traitement PDF
- **Fix** : 120s pour uploads, ou async (cf. P1)

**P7 — Retry POST dangereux**
- `api.js:27-28` : retry sur 5xx même pour POST sans réponse → doublons
- **Fix** : Ne jamais retry les POST, utiliser tokens d'idempotence

**P8 — `UploadMetrics` model inexistant**
- `views_analytics.py:15` importe `UploadMetrics` qui n'existe pas dans `models.py`
- Endpoints commentés dans urls.py mais le fichier crasherait si activé
- **Fix** : Créer le modèle ou supprimer le fichier

**P9 — Pas de barre de progression upload**
- `ExamUploadModal.vue:116` : pas de `onUploadProgress` Axios
- **Fix** : Ajouter progression visuelle

### 🟡 MINEURS

- **P10** : Pas de `created_at`/`updated_at` sur `Exam`
- **P11** : `Exam.__init__` override fragile (aliases title→name)
- **P12** : `BookletSplitView` double-check `pdf_source` (lignes 310 et 321)
- **P13** : Pas de pagination sur `ExamListView`
- **P14** : Fichiers debug à la racine backend (`db.sqlite3`, `test_*.py`, `verify_*.py`)
- **P15** : 30+ fichiers `.md` à la racine du projet → déplacer dans `docs/`
- **P16** : `alert()` natif dans AdminDashboard (lignes 67, 71, 121, 122)

---

## 4. Sécurité

### ✅ Points Positifs
- Validation PDF robuste (4 validators : taille, vide, MIME, intégrité)
- Rate limiting sur uploads (20/h)
- Permissions `IsTeacherOrAdmin` sur tous les endpoints
- `transaction.atomic()` pour la création
- CSRF token via intercepteur Axios
- Audit trail complet (`GradingEvent`)

### ⚠️ Manques
- Pas de scan antivirus sur les PDFs
- Pas de limite de taille totale pour INDIVIDUAL_A4 (100 fichiers × 50MB = 5GB)
- `ExamDispatchView` ne vérifie pas que les copies sont READY

---

## 5. Gaps de Tests

- ❌ Aucun test pour `PDFSplitter` (composant le plus critique)
- ❌ Aucun test pour `ExamUploadView`
- ❌ Aucun test pour `IndividualPDFUploadView`
- ❌ Aucun test pour `ExamDispatchView`
- ❌ Aucun test pour `MergeBookletsView`
- ❌ Aucun test end-to-end mode INDIVIDUAL_A4
- ❌ Aucun test de concurrence

---

## 6. Plan d'Action — STATUT DES CORRECTIONS

### Sprint 1 — Corrections Critiques ✅ TERMINÉ
| # | Action | Statut |
|---|--------|--------|
| 1 | Exposer `CopyValidationView` + `BulkCopyValidationView` dans urls.py + auto-validation STAGING→READY | ✅ |
| 2 | Augmenter timeout API (30s default, 120s uploads) | ✅ |
| 3 | Corriger `anonymous_id` → `generate_anonymous_id()` séquentiel collision-free | ✅ |
| 4 | Protéger `ExamSourceUploadView` contre doublons (block si non-STAGING, cleanup avant re-process) | ✅ |
| 5 | Désactiver retry POST/PUT/PATCH/DELETE dans api.js | ✅ |

### Sprint 2 — Améliorations Workflow ✅ TERMINÉ
| # | Action | Statut |
|---|--------|--------|
| 6 | Barre de progression upload avec `onUploadProgress` Axios | ✅ |
| 7 | Réécrire `views_analytics.py` (UploadMetrics → Exam/Copy/ExamPDF) | ✅ |
| 8 | Remplacer `alert()` natif par toast notifications dans AdminDashboard | ✅ |
| 9 | Ajouter pagination sur `ExamListView` (50/page) | ✅ |
| 10 | Ajouter `created_at`/`updated_at` sur Exam + migration 0018 | ✅ |
| 11 | Corriger `Exam.__init__` override fragile (P14) | ✅ |

### Sprint 3 — Tests & Qualité ✅ TERMINÉ
| # | Action | Statut |
|---|--------|--------|
| 12 | Tests `generate_anonymous_id` (collision, séquentiel, many copies) | ✅ |
| 13 | Tests auto-validation (STAGING→READY, bulk, single) | ✅ |
| 14 | Tests protection doublons `ExamSourceUploadView` | ✅ |
| 15 | Tests dispatch filter (READY only, skip GRADED) | ✅ |
| 16 | Tests timestamps Exam + __init__ safety | ✅ |
| 17 | Nettoyage fichiers PNG orphelins en cas d'erreur | ✅ |
| 18 | Supprimer double-check inutile `BookletSplitView` | ✅ |
| 19 | Dispatch ne prend que copies READY/STAGING | ✅ |

### Restant (non bloquant pour prod)
| # | Action | Priorité |
|---|--------|----------|
| A | Split PDF → tâche Celery (pour PDFs > 100 pages) | P2 |
| B | Fusionner les deux flux de création en wizard | P3 |
| C | Nettoyage fichiers debug à la racine backend | P3 |
