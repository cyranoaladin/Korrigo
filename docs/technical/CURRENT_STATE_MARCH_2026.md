# État du Projet Korrigo — 28 Mars 2026

> **Version** : 3.0
> **Date** : 2026-03-28
> **Production** : https://korrigo.labomaths.tn

---

## Résumé exécutif

Korrigo v2 est une plateforme de correction numérique d'examens pleinement opérationnelle en production. Le système gère actuellement **4 examens**, **289 copies DNB** en attente de correction, et a déjà traité les résultats des examens Bac Blanc (BB_J1 et BB_J2). La suite de tests passe intégralement (636 tests) et la release gate CI est verte.

---

## 1. Examens en Production

### Examens actifs

| Examen | ID DB | Statut | Copies | Correcteurs |
|--------|-------|--------|--------|-------------|
| `BB_J1` | baa78b5b | Publié (résultats sortis) | ~150 | Tous les profs maths |
| `BB_J2` | bd24af37 | Publié (résultats sortis) | ~150 | Tous les profs maths |
| `DNB_2026` | 69cb6f96 | **PRÊT — dispatch effectué** | 289 | 6 enseignants |
| `Prod Validation Exam` | ba447c45 | Test technique | — | — |

### DNB_2026 — État détaillé

- **Mode** : INDIVIDUAL_A4 (1 PDF A4 par élève)
- **Copies** : 289 READY, 0 IN_PROGRESS, 0 FINALIZED
- **Élèves** : 294 dans `students_student` (293 créés + 1 mis à jour)
- **Identification** : 289/289 (100%) — toutes identifiées
- **Dispatch** : Effectué le 2026-03-28

#### Répartition des copies DNB_2026

| Enseignant | Email | Copies | Classes |
|-----------|-------|--------|---------|
| Fatma ABID | fatma.abid@ert.tn | 49 | 3.1, 3.7 |
| Maroua FRAIJI | maroua.fraiji@ert.tn | 48 | 3.2, 3.4 |
| Chawki SAADI | chawki.saadi@ert.tn | 48 | 3.3 |
| Soumaya NASRI | soumaya.nasri@ert.tn | 48 | 3.5, 3.6 |
| Sami BEN TIBA | sami.bentiba@ert.tn | 48 | 3.8, 3.9 |
| Gilles COLLY | gilles.colly@ert.tn | 48 | 3.10 |

#### Contraintes de dispatch appliquées
- Aucun enseignant ne corrige ses propres élèves
- KAMEL BEN RHOUMA (3.5) → assigné à Fatma ABID (exclu de NASRI, SAADI, BEN TIBA)

---

## 2. Infrastructure Production

### Serveur
- **IP** : 88.99.254.59
- **Domaine** : korrigo.labomaths.tn (alias korrigo.nexusreussite.academy)
- **Chemin de déploiement** : `/var/www/labomaths/korrigo/`

### Conteneurs Docker (6 services)

| Conteneur | État | Description |
|-----------|------|-------------|
| docker-backend-1 | ✅ Up/healthy | Django 4.2 + Gunicorn |
| docker-db-1 | ✅ Up/healthy | PostgreSQL 15 |
| docker-redis-1 | ✅ Up/healthy | Redis 7 (broker + cache) |
| docker-celery-1 | ✅ Up | Worker Celery |
| docker-celery-beat-1 | ✅ Up | Scheduler Celery Beat |
| docker-nginx-1 | ✅ Up | Reverse proxy + TLS |

---

## 3. État du Code et des Migrations

### Branche principale
- **Branche** : `main`
- **Dernier commit** : `5857dd5` — fix(grading): atomic finalizing_at claim

### Migrations (app exams)

| Migration | Description | Statut |
|-----------|-------------|--------|
| 0001–0025 | Schéma initial + évolutions | ✅ Appliqué |
| 0026 | Simplification status 3 états | ✅ Appliqué |
| 0027 | Renommage valeurs status | ✅ Appliqué |
| **0028** | **Copy.finalizing_at** | ✅ **À appliquer sur prod** |

> ⚠️ La migration 0028 doit être appliquée sur la production :
> ```bash
> docker exec docker-backend-1 python manage.py migrate
> ```

---

## 4. Changements Récents (Mars 2026)

### Architecture — Simplification machine à états (migrations 0026/0027)

**Avant** (5 états) :
```
STAGING → READY → LOCKED → GRADING_IN_PROGRESS → GRADED
```

**Après** (3 états) :
```
READY → IN_PROGRESS → FINALIZED
  ↑                        │
  └──── reopen (admin) ────┘
```

**Impact** :
- Suppression des états STAGING, LOCKED, GRADING_IN_PROGRESS, GRADED
- Transition READY → IN_PROGRESS automatique à la 1ère annotation
- Plus de lock/unlock manuel pour le workflow correcteur
- Tests mis à jour (636 passent)

### Sécurité concurrence — `Copy.finalizing_at` (migration 0028)

Problème détecté : sous forte concurrence PostgreSQL, deux requêtes simultanées de finalisation pouvaient toutes deux appeler `flatten_copy()` si la première terminait avant que la seconde tente son `SELECT FOR UPDATE NOWAIT`.

Solution : mutex atomique SQL :
```sql
UPDATE exams_copy SET finalizing_at = NOW()
WHERE id = X AND status IN ('READY', 'IN_PROGRESS') AND finalizing_at IS NULL
```
PostgreSQL garantit qu'exactement une requête concurrente obtient `rows_affected=1`.
Le test `test_finalize_concurrent_requests_flatten_called_once_postgres` passe désormais.

### UI — Suppression Sujets A/B

La fonctionnalité "Sujet A / Sujet B" a été supprimée de l'interface :
- `CorrectorDesk.vue` : removed `subjectVariant` computed, `handleSubjectVariantChange`, bloc HTML `subject-variant-control`
- `AdminDashboard.vue` : removed modal Sujets A/B, bouton "Sujets A/B", toutes les fonctions associées

Le champ `Copy.subject_variant` reste en base pour compatibilité des données existantes, mais n'est plus exposé ni modifiable via l'UI.

### Commandes de gestion ajoutées

| Commande | Description |
|----------|-------------|
| `import_dnb_students` | Import CSV élèves troisième (Student + User Django) |
| `identify_dnb_copies` | Matching automatique copies → élèves (DDN + fuzzy) |
| `import_dnb_copies` | Ingestion batch des 289 PDFs DNB A4 |

### Compte enseignante créé

Maroua FRAIJI (`maroua.fraiji@ert.tn`) : compte créé le 2026-03-28, groupe TEACHER.

### Fix celery-beat

Problème : `ValueError: SECRET_KEY looks like a placeholder` au démarrage du conteneur.
Cause : `SECRET_KEY=django-insecure-...` dans `.env` — rejeté par `settings_prod.py`.
Fix : génération d'une vraie clé 50 caractères + `KORRIGO_SHA` mis à jour vers l'image disponible.

---

## 5. État des Tests

### Suite complète (CI)
- **636 tests passent**, 3 déselectionnés (fixtures non-postgres)
- **0 échec**

### Release Gate (zero-tolerance)
- ✅ pytest : 636 passed, 0 failed, 0 skipped
- ✅ E2E : 3/3 runs passed (annotations POST 201, GET 200)
- ✅ Seed : all READY copies have pages > 0

### Catégories de tests

| App | Modules | Lignes approx. |
|-----|---------|---------------|
| grading | 60+ | ~8 000 |
| exams | 24 | ~2 000 |
| core | 12 | ~1 200 |
| students | 4 | ~500 |
| processing | 1 | ~200 |
| identification | 1 | ~100 |

---

## 6. Décisions Techniques Actives

### ADR-001 : Authentification élèves
Email + date de naissance (sans mot de passe). Compte Django créé automatiquement (password `passe123` par défaut, modifiable).

### ADR-002 : Coordonnées annotations normalisées [0,1]
Toutes les annotations utilisent des coordonnées relatives à la page (x, y, w, h ∈ [0,1]). Indépendant de la résolution d'affichage.

### ADR-003 v3 : Machine à états 3 statuts
READY / IN_PROGRESS / FINALIZED. Mutex atomique `finalizing_at` pour la finalisation concurrente.

### Pas de variantes de sujet A/B
Décision opérationnelle mars 2026 : un seul sujet par examen. Le champ `subject_variant` reste en DB mais est désactivé en UI.

---

## 7. Prochaines Étapes

- [ ] Appliquer migration 0028 sur production (`python manage.py migrate`)
- [ ] Correction des copies DNB_2026 par les 6 enseignants
- [ ] Publication des résultats DNB après finalisation de toutes les copies
- [ ] Génération des bilans LLM après finalisation
- [ ] Export Pronote pour remontée des notes
