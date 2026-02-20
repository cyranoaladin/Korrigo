# AUDIT KORRIGO — RC_2026-02-20

## 0. Résumé exécutif

- **P0 couverts** : P0-2 (rapports), P0-3 (stats), P0-4 (Locked), P0-5 (francisation), P0-6 (RBAC)
- **Risque global** : **Faible** — P0-4 et P0-6 déjà implémentés et testés. P0-2/P0-3 sont fonctionnels côté backend. P0-5 nécessite ~20 traductions de chaînes.
- **Décision** : **GO** — aucune migration destructive, aucun changement de schéma DB.

## 1. Périmètre & interdits

### Inclus
- P0-2 : Vérifier visibilité rapports élève (scores, remarques, appréciation, annotations, PDF)
- P0-3 : Vérifier calcul et affichage stats
- P0-4 : Confirmer suppression "Locked" (déjà fait commit 9fbdfe9)
- P0-5 : Franciser toutes les chaînes anglaises visibles
- P0-6 : Confirmer cloisonnement rôles (déjà fait commit b3d8ae0)

### Exclu
- Migration de schéma DB
- Modification des données existantes (notes, annotations, remarques)
- Rename des enums internes (READY, GRADED restent en DB)

### Interdits
- Écriture DB avant backup ✅ (dump vérifié)
- Migrations destructives
- Rename statuts internes en DB

## 2. Empreinte technique (baseline)

| Composant | Détail |
|-----------|--------|
| **Infra** | Ubuntu 22.04, kernel 6.8.0-100, 32GB RAM, Docker |
| **Backend** | Django 4.2 + DRF, Python 3.9, Gunicorn |
| **Frontend** | Vue 3 + Vite, SPA servi par nginx |
| **DB** | PostgreSQL 15-alpine (docker-db-1, port 5432) |
| **Queue** | Celery + Redis 7-alpine |
| **Stockage** | /var/www/labomaths/korrigo/overlay/ (backend overlay) |
| **Reverse proxy** | nginx 1.18.0 → port 8088 (docker-nginx-1) |
| **Git HEAD** | `9fbdfe9` (main) — "refactor: suppression complète du mécanisme de verrouillage" |

## 3. Intégrité données (preuves)

| Contrôle | Résultat |
|----------|----------|
| **Dump DB** | `db_2026-02-20.dump` (445K) |
| **SHA256** | `d1ec1b107698d08cd47053c78a017f0140df9ed8157dba9204bb99c13873f89f` |
| **Preuve restauration** | ✅ Restore → counts match (213/544/105/1075/2221/220) |

### Comptages entités

| Entité | Count |
|--------|-------|
| Users | 222 (4 staff, 1 superuser) |
| Students | 220 (210 with user, 10 without) |
| Exams | 3 |
| Copies | 213 (170 READY, 43 GRADED) |
| Booklets | 212 |
| Annotations | 544 |
| Scores | 105 |
| QuestionRemarks | 1075 |
| GradingEvents | 2221 |
| CopyLock | 0 |
| DraftState | 12 |

### Liaisons

| Contrôle | Résultat |
|----------|----------|
| Copies sans exam | 0 ✅ |
| Annotations sans copy | 0 ✅ |
| Scores sans copy | 0 ✅ |
| Copies avec corrector | 209 / 4 sans |
| Copies avec student | 210 / 3 sans |

### Par examen

| Exam | Total | Ready | Graded | Scores | Remarks | Annots | Events |
|------|-------|-------|--------|--------|---------|--------|--------|
| BB_J1 | 106 | 90 | 16 | 47 | 627 | 494 | 1519 |
| BB_J2 | 103 | 77 | 26 | 58 | 448 | 50 | 699 |
| Prod Validation | 4 | 3 | 1 | 0 | 0 | 0 | 3 |

## 4. Diagnostic P0-2 — Rapports élève incomplets

### Symptômes
Le user rapporte que remarques/annotations/appréciation/note finale sont invisibles dans les rapports élève.

### Trace DB → API → UI

| Champ | DB | API (StudentCopiesView) | Frontend (ResultView.vue) |
|-------|----|-----------------------|--------------------------|
| scores_details | ✅ Score.scores_data | ✅ Retourné | ✅ Affiché (.tags) |
| total_score | ✅ compute_score() | ✅ Retourné | ✅ Affiché (.score-value) |
| remarks | ✅ QuestionRemark | ✅ Dict par question_id | ✅ Affiché (.remarks-section) |
| global_appreciation | ✅ Copy.global_appreciation | ✅ Retourné | ✅ Affiché (.appreciation-section) |
| final_pdf_url | ✅ Copy.final_pdf | ✅ URL construite | ✅ iframe + download |
| annotations | ✅ 544 en DB | ❌ **Non retourné par API** | ❌ **Non affiché** |

### Cause racine
1. **Annotations non incluses dans le payload API** : `StudentCopiesView.list()` ne retourne pas les annotations individuelles. Les annotations sont visibles uniquement dans le PDF final (rendues par `pdf_flattener.py`). Si le PDF est bien généré, les annotations y sont visibles.
2. **BB_J2 `results_released_at=None`** : Les étudiants de BB_J2 ne voient **aucune** copie car le filtre exige `results_released_at__isnull=False`. Il faut release les résultats BB_J2.

### Plan correctif
- Ajouter `annotations_count` au payload API (informatif)
- S'assurer que le PDF contient bien les annotations (déjà le cas via pdf_flattener)
- **Pas de release automatique de BB_J2** — à confirmer avec l'utilisateur

### Risques : Faible — lecture seule, pas de modification de données
### Tests : Vérifier payload API sur copie graded, vérifier PDF contient annotations

## 5. Diagnostic P0-3 — Statistiques absentes

### Symptômes
Stats ne s'affichent pas dans le dashboard correcteur.

### Trace

| Couche | État |
|--------|------|
| **API** | ✅ `CorrectorStatsView` retourne 200 avec mean/median/std/distribution |
| **BB_J1** | mean=13.49, median=14.85, count=16 |
| **BB_J2** | mean=13.52, median=14.25, count=26 |
| **Frontend** | Auto-affichage seulement si `graded === total` (ligne 37 CorrectorDashboard.vue) |
| **Bouton manuel** | ✅ Fonctionne via "Voir les statistiques" |

### Cause racine
Le front n'auto-affiche les stats que quand **toutes** les copies sont corrigées. Puisque BB_J1 a 90/106 non corrigées et BB_J2 77/103, les stats ne s'affichent pas automatiquement. Le **bouton manuel** fonctionne.

### Plan correctif
- Afficher les stats dès qu'il y a au moins 1 copie corrigée (remplacer `graded === total` par `graded > 0`)
- Garder le badge "partielles" si `graded < total`

### Risques : Aucun — changement purement UI
### Tests : Vérifier que les stats s'affichent avec des copies partiellement corrigées

## 6. Diagnostic P0-4 — Suppression "Locked"

### État : ✅ COMPLÉTÉ (commit 9fbdfe9)

| Contrôle | Résultat |
|----------|----------|
| CopyLock rows | 0 |
| Copies LOCKED | 0 |
| Routes lock | 404 (supprimées) |
| Frontend | softLock/heartbeat/releaseLock supprimés |
| Workflow | STAGING → READY → GRADED (sans LOCKED) |

Voir `proofs/RC_2026-02-20/baseline/entity_counts.txt`

## 7. Diagnostic P0-5 — Francisation totale

### Scan frontend
La majorité des chaînes visibles sont déjà en français (commits b3d8ae0, 9fbdfe9). Termes restants : "Email" (adopté en français), "Login" (contexte technique admin).

### Scan backend — Chaînes anglaises à franciser

| Fichier | Ligne | Chaîne anglaise |
|---------|-------|----------------|
| grading/views.py | 224 | "Authentication required." |
| grading/views.py | 233 | "Invalid session." |
| grading/views.py | 239 | "You do not have permission to view this copy." |
| grading/views.py | 335 | "You do not have permission to edit this remark." |
| grading/views.py | 353 | "You do not have permission to delete this remark." |
| grading/views.py | 422 | "Cannot modify scores of a graded copy." |
| exams/views.py | 291 | "Invalid PDF file" |
| exams/views.py | 422 | "Page out of range" |
| exams/views.py | 596 | "Student ID required" |
| exams/views.py | 771 | "Invalid copy state" |
| students/views.py | 103 | "Not authenticated" |
| students/views.py | 189 | "File required" |
| students/views.py | 214 | "Missing columns..." |
| students/views.py | 230 | "Invalid name format..." |
| students/views.py | 257 | "Invalid date format..." |
| students/views.py | 265 | "Last name and first name are required" |

### Plan correctif
- Traduire toutes les chaînes ci-dessus
- Les enums internes (READY, GRADED, COMMENT, etc.) restent inchangés

### Risques : Aucun — traduction de strings uniquement

## 8. Diagnostic P0-6 — Cloisonnement strict des rôles

### État : ✅ COMPLÉTÉ (commit b3d8ae0)

| Test | Résultat | Preuve |
|------|----------|--------|
| Élève → portail enseignant | **403 Forbidden** | `validation/p0-6_student_on_teacher_portal.txt` |
| Enseignant → portail élève | **401 Unauthorized** | `validation/p0-6_teacher_on_student_portal.txt` |
| Backend LoginView | Vérifie is_staff/superuser/Teacher group | core/views.py:54-90 |
| Backend StudentLoginView | Vérifie Student.objects.filter(user=user) | students/views.py:57-62 |

## 9. Plan de livraison

### Ordre d'implémentation
1. **P0-5** : Francisation chaînes backend (~20 strings) — 0 risque
2. **P0-3** : Stats auto-affichage dès graded > 0 — 0 risque
3. **P0-2** : Ajouter annotations_count au payload StudentCopiesView — 0 risque
4. Tests E2E complets
5. Deploy + smoke tests

### Stratégie
- Commits atomiques par P0
- Pas de migration DB
- Pas de feature flags nécessaires
- Deploy via overlay + frontend build

## 10. Annexes (preuves)

- `baseline/entity_counts.txt` — comptages entités
- `baseline/docker_ps.txt` — état services
- `baseline/git_head.txt` — commit SHA
- `backups/db_2026-02-20.dump` — dump DB
- `backups/db_2026-02-20.dump.sha256` — hash
- `backups/restore_proof.txt` — preuve restauration
- `diagnostic/p0-2_db_api_trace.txt` — trace DB→API
- `diagnostic/p0-3_stats_trace.txt` — stats endpoint test
- `diagnostic/p0-5_backend_english.txt` — chaînes anglaises
- `validation/p0-6_student_on_teacher_portal.txt` — RBAC proof
- `validation/p0-6_teacher_on_student_portal.txt` — RBAC proof
