# Référence API — Korrigo v2

> **Version** : 3.1
> **Date** : 2026-04-03
> **Base URL** : `https://korrigo.labomaths.tn/api/` (prod) | `http://localhost:8000/api/` (dev)
> **Format** : JSON
> **Auth** : Session Django + cookie CSRF (`csrftoken` → header `X-CSRFToken`)
> **Documentation interactive** : `/api/schema/swagger-ui/` | `/api/schema/redoc/`

---

## Table des Matières

1. [Authentification](#authentification)
2. [Examens](#examens)
3. [Copies](#copies)
4. [Correction (Grading)](#correction-grading)
5. [Annotations](#annotations)
6. [Verrous (Locks)](#verrous-locks)
7. [Identification OCR](#identification-ocr)
8. [Élèves (Students)](#eleves-students)
9. [Système](#systeme)
10. [Codes de réponse](#codes-de-réponse)
11. [Pagination](#pagination)
12. [Rate Limiting](#rate-limiting)

---

## Authentification

### `POST /api/auth/login/`
Connexion admin/enseignant.

**Body** :
```json
{"username": "prof@school.tn", "password": "motdepasse"}
```

**Réponse 200** :
```json
{
  "user_id": 42,
  "username": "prof@school.tn",
  "role": "teacher",
  "is_admin": false,
  "is_teacher": true,
  "is_student": false
}
```

---

### `POST /api/auth/logout/`
Déconnexion. Efface la session.

**Réponse** : `200 OK`

---

### `GET /api/auth/me/`
Informations sur l'utilisateur courant.

**Réponse 200** : même format que login.

---

### `POST /api/students/login/`
Connexion élève (email + date de naissance, sans mot de passe).

**Body** :
```json
{"email": "eleve@school.tn", "birth_date": "2010-12-03"}
```

**Réponse 200** :
```json
{"user_id": 99, "username": "eleve@school.tn", "role": "student"}
```

**Erreur 401** : email ou date de naissance incorrect.

---

### `POST /api/students/change-password/`
Changement de mot de passe élève (après première connexion).

**Body** : `{"new_password": "nouveau_mdp"}`

---

## Examens

### `GET /api/exams/`
Liste des examens. Admin : tous. Enseignant : examens assignés uniquement.

**Query params** : `?status=`, `?exam_type=`

**Réponse 200** (paginée) :
```json
{
  "count": 4,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "69cb6f96-...",
      "name": "DNB_2026",
      "date": "2026-03-15",
      "upload_mode": "INDIVIDUAL_A4",
      "exam_type": {"code": "DNBM2026", "name": "DNB Blanc Maths 2026"},
      "copies_count": 289,
      "ready_count": 289,
      "in_progress_count": 0,
      "finalized_count": 0,
      "results_released_at": null
    }
  ]
}
```

---

### `POST /api/exams/`
Créer un examen. **Admin uniquement.**

**Body** :
```json
{
  "name": "BAC_BLANC_J1",
  "date": "2026-04-10",
  "upload_mode": "BATCH_A3",
  "exam_type_id": 1
}
```

**Réponse 201** : examen créé.

---

### `GET /api/exams/{id}/`
Détail d'un examen avec statistiques.

---

### `PUT /api/exams/{id}/`
Modifier un examen. **Admin uniquement.**

---

### `DELETE /api/exams/{id}/`
Supprimer un examen. **Admin uniquement.** Bloqué (PROTECT) si des copies existent.

---

### `POST /api/exams/upload/`
Uploader un PDF batch (mode BATCH_A3). Déclenche le découpage en booklets + création des copies.

**Body** : `multipart/form-data`
- `pdf` : fichier PDF (max 50 MB, max 500 pages)
- `exam_id` : UUID de l'examen

**Réponse 201** :
```json
{"copies_created": 45, "exam_id": "..."}
```

**Erreurs** :
- `400` : PDF invalide (pas un PDF, trop grand, trop de pages)
- `409` : Re-upload bloqué car des copies sont IN_PROGRESS ou FINALIZED

**Rate limit** : 10 requêtes/heure/utilisateur.

---

### `POST /api/exams/{id}/upload-individual-pdfs/`
Uploader des PDFs A4 individuels (mode INDIVIDUAL_A4). Un PDF par élève.

**Body** : `multipart/form-data`, champ `pdfs[]` (multiple)
- Nommage : `NOM_PRENOM_DDMMYYYY.pdf`

**Réponse 201** :
```json
{"copies_created": 10, "errors": []}
```

---

### `GET /api/exams/{id}/copies/`
Liste paginée des copies d'un examen.
- Admin : toutes les copies
- Enseignant : uniquement ses copies assignées

**Query params** : `?status=READY`, `?is_identified=false`, `?page=2`

**Réponse 200** (paginée) :
```json
{
  "count": 289,
  "results": [
    {
      "id": "uuid...",
      "anonymous_id": "69CB-066",
      "status": "READY",
      "is_identified": true,
      "student": {"id": 45, "first_name": "KAMEL", "last_name": "BEN RHOUMA", "class_name": "3.5"},
      "assigned_corrector": {"id": 7, "username": "fatma.abid@ert.tn"},
      "graded_at": null
    }
  ]
}
```

---

### `POST /api/exams/{id}/dispatch-copies/`
Assigner des copies à des correcteurs. **Admin uniquement.**

**Body** :
```json
{
  "assignments": [
    {"copy_id": "uuid...", "corrector_id": 7},
    {"copy_id": "uuid...", "corrector_id": 8}
  ]
}
```

---

### `GET /api/exams/{id}/stats/`
Statistiques détaillées de l'examen.

**Réponse 200** :
```json
{
  "total": 289,
  "ready": 0,
  "in_progress": 45,
  "finalized": 244,
  "avg_score": 12.4,
  "min_score": 2.0,
  "max_score": 19.5
}
```

---

### `POST /api/exams/{id}/release-results/`
Publier les résultats aux élèves. **Admin uniquement.** Définit `results_released_at`.

**Réponse 200** : `{"released_at": "2026-03-28T18:00:00Z"}`

---

### `GET /api/exam-types/`
Liste des types d'examens disponibles.

---

### `POST /api/exam-types/`
Créer un type d'examen. **Admin uniquement.**

---

## Copies

### `GET /api/grading/copies/{id}/`
Détail complet d'une copie avec annotations, score, statut du verrou.

**Réponse 200** :
```json
{
  "id": "uuid...",
  "anonymous_id": "69CB-066",
  "status": "IN_PROGRESS",
  "exam": {"id": "...", "name": "DNB_2026"},
  "student": {"first_name": "KAMEL", "last_name": "BEN RHOUMA"},
  "booklets": [{"id": "...", "pages_images": ["copies/pages/.../p000.png"]}],
  "annotations": [...],
  "score": {"scores_data": {"ex1.q1": 2.0}},
  "lock": {"owner": "fatma.abid@ert.tn", "expires_at": "2026-03-28T19:30:00Z"},
  "final_pdf": null,
  "graded_at": null
}
```

---

## Correction (Grading)

### `POST /api/grading/copies/{id}/finalize/`
Finaliser une copie : aplatit les annotations sur le PDF, passe en FINALIZED.

**Body** : `{"lock_token": "uuid..."}` (optionnel)

**Réponse 200** :
```json
{
  "status": "FINALIZED",
  "final_pdf": "/media/copies/final/copy_uuid_corrected.pdf",
  "graded_at": "2026-03-28T17:45:00Z",
  "final_score": 14.5
}
```

**Erreurs** :
- `409` : Copie déjà finalisée, ou finalisation déjà en cours (concurrent request)
- `400` : Statut invalide

---

### `POST /api/grading/copies/{id}/reopen/`
Réouvrir une copie finalisée. **Superuser uniquement.**

**Effets** : status → READY, final_pdf effacé, graded_at = null, grading_retries = 0.
Annotations et notes **conservées**.

**Réponse 200** : `{"status": "READY"}`

---

### `GET /api/grading/copies/{id}/score/`
Récupérer les notes de la copie.

---

### `POST /api/grading/copies/{id}/score/`
Sauvegarder les notes.

**Body** :
```json
{"scores_data": {"ex1.q1": 2.0, "ex1.q2": 1.5, "ex2.q1": 3.0}}
```

---

### `POST /api/grading/copies/{id}/appreciation/`
Sauvegarder l'appréciation globale.

**Body** : `{"text": "Bon travail d'ensemble..."}`

---

### `GET /api/grading/copies/{id}/draft/`
Récupérer la sauvegarde automatique.

---

### `POST /api/grading/copies/{id}/draft/`
Sauvegarder l'état courant (appelé automatiquement par le frontend).

**Body** : `{"content": {...}}`

---

### `GET /api/grading/copies/{id}/events/`
Historique complet des événements d'audit.

---

## Annotations

### `GET /api/grading/copies/{id}/annotations/`
Liste toutes les annotations, triées par `(page_index, created_at)`.

**Réponse 200** :
```json
[
  {
    "id": "uuid...",
    "page_index": 0,
    "x": 0.1, "y": 0.2, "w": 0.3, "h": 0.05,
    "type": "ERROR",
    "content": "Erreur de calcul",
    "score_delta": -1,
    "version": 0,
    "created_by": {"username": "fatma.abid@ert.tn"},
    "created_at": "2026-03-28T15:00:00Z"
  }
]
```

---

### `POST /api/grading/copies/{id}/annotations/`
Créer une annotation. Passe la copie en IN_PROGRESS si elle était READY.

**Body** :
```json
{
  "page_index": 0,
  "x": 0.1, "y": 0.2, "w": 0.3, "h": 0.05,
  "type": "ERROR",
  "content": "Erreur de calcul",
  "score_delta": -1
}
```

**Réponse 201** : annotation créée avec `id` et `version: 0`.

**Validations** :
- `x, y ∈ [0,1]`, `w, h ∈ (0,1]`
- `x + w ≤ 1.0`, `y + h ≤ 1.0`
- `page_index < total_pages`
- Copie non FINALIZED

---

### `PUT /api/grading/copies/{id}/annotations/{ann_id}/`
Modifier une annotation. Verrou optimiste via `version`.

**Body** :
```json
{
  "content": "Erreur de calcul — voir cours",
  "score_delta": -2,
  "version": 0
}
```

**Erreur 400** : version mismatch (modification concurrente détectée).
**Réponse 200** : annotation avec `version: 1`.

---

### `DELETE /api/grading/copies/{id}/annotations/{ann_id}/`
Supprimer une annotation.

**Réponse 204**

---

### `GET /api/grading/annotation-templates/`
Liste les templates de l'utilisateur courant + templates globaux.

---

### `POST /api/grading/annotation-templates/`
Créer un template.

**Body** : `{"category": "Algèbre", "content": "Erreur de signe", "is_global": false}`

---

## Verrous (Locks)

### `POST /api/grading/copies/{id}/lock/`
Acquérir un verrou pessimiste (exclusivité d'édition).

**Body** : `{"ttl_seconds": 1800}`

**Réponse 200** :
```json
{
  "token": "uuid...",
  "owner": "fatma.abid@ert.tn",
  "expires_at": "2026-03-28T18:30:00Z"
}
```

**Erreur 409** : copie déjà verrouillée par un autre utilisateur.

---

### `POST /api/grading/copies/{id}/unlock/`
Libérer le verrou.

**Body** : `{"token": "uuid..."}`

**Erreur 403** : token invalide ou mauvais propriétaire.

---

### `POST /api/grading/copies/{id}/heartbeat/`
Renouveler le TTL du verrou (toutes les 5 minutes depuis le frontend).

**Body** : `{"token": "uuid...", "ttl_seconds": 1800}`

---

## Identification OCR

### `POST /api/identification/perform-ocr/{copy_id}/`
Lancer l'OCR sur l'en-tête d'une copie non-identifiée.

**Pipeline** : GPT-4o-mini Vision (primaire) → Tesseract (fallback)

**Réponse 200** :
```json
{
  "detected_text": "ABBES MYRIAM 03/12/2010",
  "confidence": 0.92,
  "suggested_students": [
    {"id": 12, "first_name": "MYRIAM", "last_name": "ABBES",
     "date_naissance": "2010-12-03", "class_name": "3.1", "score": 0.95}
  ]
}
```

**Rate limit** : 30 requêtes/heure/utilisateur.

---

### `POST /api/identification/identify/{copy_id}/`
Associer manuellement un élève à une copie.

**Body** : `{"student_id": 12}`

**Réponse 200** :
```json
{"is_identified": true, "student": {"id": 12, "first_name": "MYRIAM", "last_name": "ABBES"}}
```

---

## Élèves (Students)

### `GET /api/students/`
Liste des élèves. **Admin uniquement.**

---

### `GET /api/students/{id}/`
Détail d'un élève. Admin ou l'élève lui-même.

---

### `GET /api/students/my-copies/`
Copies finalisées de l'élève connecté. Nécessite que `exam.results_released_at` soit défini.

**Réponse 200** :
```json
[
  {
    "id": "uuid...",
    "exam": {"name": "DNB_2026", "date": "2026-03-15"},
    "anonymous_id": "69CB-066",
    "status": "FINALIZED",
    "final_pdf": "/media/copies/final/...",
    "score": {"total": 14.5, "max": 20},
    "global_appreciation": "Bon travail...",
    "llm_summary": "Résumé personnalisé...",
    "graded_at": "2026-03-28T17:45:00Z"
  }
]
```

---

### `GET /api/students/copies/{copy_id}/`
Voir une copie spécifique (l'élève doit en être le propriétaire, résultats publiés).

---

## Système

### `GET /api/health/`
Vérification de l'état du système.

**Réponse 200** :
```json
{"status": "healthy", "database": "connected"}
```

> En production, le point de référence est `https://korrigo.labomaths.tn/api/health/` derrière Nginx.

---

### `GET /metrics`
Métriques Prometheus. Requiert le header `Authorization: Bearer <METRICS_TOKEN>`.

Métriques exposées :
- `grading_finalize_duration_seconds` (histogram)
- `grading_lock_conflicts_total` (counter, labels: conflict_type)
- `grading_ocr_errors_total` (counter, labels: error_type)
- `grading_import_duration_seconds` (histogram)

---

## Codes de réponse

| Code | Signification | Contexte |
|------|--------------|---------|
| `200` | OK | Succès (GET, PUT, PATCH) |
| `201` | Created | Ressource créée (POST) |
| `204` | No Content | Suppression réussie |
| `400` | Bad Request | Données invalides, validation échouée |
| `401` | Unauthorized | Non authentifié |
| `403` | Forbidden | Authentifié mais non autorisé |
| `404` | Not Found | Ressource introuvable |
| `409` | Conflict | Verrou en conflit, copie déjà finalisée, re-upload bloqué |
| `422` | Unprocessable Entity | Entité métier non traitée |
| `429` | Too Many Requests | Rate limit atteint |
| `500` | Internal Server Error | Erreur serveur |

**Format erreur standard** :
```json
{
  "detail": "Message d'erreur lisible",
  "code": "lock_conflict",
  "errors": {"field": ["message"]}
}
```

---

## Pagination

Toutes les listes utilisent la pagination DRF standard :

```json
{
  "count": 289,
  "next": "/api/exams/uuid/copies/?page=2",
  "previous": null,
  "results": [...]
}
```

Taille de page par défaut : 20. `?page_size=100` (max 200).

---

## Rate Limiting

| Endpoint | Limite | Par |
|----------|--------|-----|
| `POST /api/exams/upload/` | 10/heure | Utilisateur |
| `POST /api/auth/login/` | 20/heure | IP |
| `POST /api/students/login/` | 20/heure | IP |
| `POST /api/identification/perform-ocr/` | 30/heure | Utilisateur |

En cas de dépassement : `429 Too Many Requests` + header `Retry-After`.

Rate limiting désactivable uniquement en mode `E2E_TEST_MODE=true` (jamais en production).
