# API Reference - Korrigo PMF

> **Version**: 1.2.0  
> **Date**: Janvier 2026  
> **Base URL**: `http://localhost:8088/api/` (dev) | `https://viatique.example.com/api/` (prod)

Documentation complète de l'API REST de la plateforme Korrigo PMF.

---

## 📋 Table des Matières

1. [Authentification](#authentification)
2. [Endpoints Exams](#endpoints-exams)
3. [Endpoints Grading](#endpoints-grading)
4. [Endpoints Annotations](#endpoints-annotations)
5. [Endpoints Students](#endpoints-students)
6. [Codes d'Erreur](#codes-derreur)
7. [Rate Limiting](#rate-limiting)
8. [Exemples](#exemples)

---

## Authentification

### Méthode: Session-based Authentication

L'API utilise l'authentification par session Django (cookies).

**Login**:
```http
POST /api/auth/login/
Content-Type: application/json

{
  "username": "teacher1",
  "password": "password123"
}
```

**Response**:
```json
{
  "user": {
    "id": 1,
    "username": "teacher1",
    "role": "Teacher",
    "email": "teacher1@example.com"
  }
}
```

**Logout**:
```http
POST /api/auth/logout/
```

### Headers Requis

| Header | Valeur | Description |
|--------|--------|-------------|
| `Content-Type` | `application/json` | Format des données |
| `X-CSRFToken` | `<token>` | Token CSRF (POST/PUT/PATCH/DELETE) |
| `Cookie` | `sessionid=<id>` | Session cookie (automatique) |

### Permissions

| Rôle | Accès |
|------|-------|
| **Admin** | Tous les endpoints |
| **Teacher** | Correction, annotations, copies |
| **Student** | Consultation copies personnelles uniquement |

---

## Endpoints Exams

### Liste des Examens

```http
GET /api/exams/
```

**Permissions**: `IsTeacherOrAdmin`

**Response**:
```json
[
  {
    "id": "uuid-...",
    "name": "Bac Blanc Maths TG - Janvier 2026",
    "date": "2026-01-15",
    "pdf_source": "/media/exams/source/exam.pdf",
    "grading_structure": [...],
    "is_processed": true
  }
]
```

---

### Créer un Examen

```http
POST /api/exams/
Content-Type: multipart/form-data
```

**Permissions**: `IsTeacherOrAdmin`

**Payload**:
```
name: "Bac Blanc Maths TG - Janvier 2026"
date: "2026-01-15"
pdf_source: <file>
```

**Response** (201 Created):
```json
{
  "id": "uuid-...",
  "name": "Bac Blanc Maths TG - Janvier 2026",
  "date": "2026-01-15",
  "pdf_source": "/media/exams/source/exam.pdf",
  "booklets_created": 25,
  "message": "25 booklets created successfully"
}
```

**Validations**:
- `pdf_source`: Extension `.pdf`, taille max 50 MB, MIME type `application/pdf`
- `name`: Max 255 caractères
- `date`: Format ISO 8601

---

### Détails d'un Examen

```http
GET /api/exams/{id}/
```

**Permissions**: `IsTeacherOrAdmin`

**Response**:
```json
{
  "id": "uuid-...",
  "name": "Bac Blanc Maths TG - Janvier 2026",
  "date": "2026-01-15",
  "pdf_source": "/media/exams/source/exam.pdf",
  "grading_structure": [
    {
      "id": "ex1",
      "label": "Exercice 1",
      "points": 10,
      "children": [
        {"id": "ex1_q1", "label": "Question 1.a", "points": 3},
        {"id": "ex1_q2", "label": "Question 1.b", "points": 7}
      ]
    }
  ],
  "is_processed": true
}
```

---

### Mettre à Jour un Examen

```http
PATCH /api/exams/{id}/
Content-Type: application/json
```

**Permissions**: `IsTeacherOrAdmin`

**Payload** (exemple: mise à jour barème):
```json
{
  "grading_structure": [
    {
      "id": "ex1",
      "label": "Exercice 1",
      "points": 12,
      "children": [...]
    }
  ]
}
```

**Response** (200 OK):
```json
{
  "id": "uuid-...",
  "grading_structure": [...]
}
```

---

### Fusionner des Fascicules

```http
POST /api/exams/{exam_id}/merge/
Content-Type: application/json
```

**Permissions**: `IsTeacherOrAdmin`

**Payload**:
```json
{
  "booklet_ids": ["uuid-1", "uuid-2", "uuid-3"]
}
```

**Response** (201 Created):
```json
{
  "message": "Copie créée avec succès.",
  "copy_id": "uuid-...",
  "anonymous_id": "A3F7B2E1"
}
```

---

### Export PDF Finaux

```http
POST /api/exams/{id}/export_all/
```

**Permissions**: `IsTeacherOrAdmin`

**Description**: Génère les PDF finaux avec annotations pour toutes les copies de l'examen.

**Response** (200 OK):
```json
{
  "message": "25 copies traitées."
}
```

---

### Export CSV (Pronote)

```http
GET /api/exams/{id}/export_csv/
```

**Permissions**: `IsTeacherOrAdmin`

**Response**: Fichier CSV
```csv
AnonymousID,Total,ex1_q1,ex1_q2
A3F7B2E1,15.5,3,7
B4C8D3F2,12.0,2,5
```

---

### Liste des Fascicules

```http
GET /api/exams/{exam_id}/booklets/
```

**Permissions**: `IsTeacherOrAdmin`

**Response**:
```json
[
  {
    "id": "uuid-...",
    "exam_id": "uuid-...",
    "start_page": 1,
    "end_page": 4,
    "header_image": "/media/booklets/headers/header_1.png",
    "student_name_guess": "DUPONT",
    "pages_images": ["/media/pages/p1.png", "/media/pages/p2.png"]
  }
]
```

---

### Image En-tête Fascicule

```http
GET /api/booklets/{id}/header/
```

**Permissions**: `IsTeacherOrAdmin`

**Description**: Retourne l'image de l'en-tête du fascicule (crop dynamique du PDF).

**Response**: Image PNG (Content-Type: `image/png`)

---

### Liste des Copies

```http
GET /api/exams/{exam_id}/copies/
```

**Permissions**: `IsTeacherOrAdmin`

**Response**:
```json
[
  {
    "id": "uuid-...",
    "exam_id": "uuid-...",
    "student_id": null,
    "anonymous_id": "A3F7B2E1",
    "status": "READY",
    "is_identified": false,
    "pdf_source": "/media/copies/source/copy.pdf",
    "final_pdf": null
  }
]
```

---

### Copies Non Identifiées

```http
GET /api/exams/{exam_id}/unidentified_copies/
```

**Permissions**: `IsTeacherOrAdmin`

**Description**: Liste des copies en attente d'identification (pour le "Video-Coding").

**Response**:
```json
[
  {
    "id": "uuid-...",
    "anonymous_id": "A3F7B2E1",
    "header_image_url": "/api/booklets/uuid-.../header/",
    "status": "STAGING"
  }
]
```

---

### Identifier une Copie

```http
POST /api/copies/{id}/identify/
Content-Type: application/json
```

**Permissions**: `IsTeacherOrAdmin`

**Payload**:
```json
{
  "student_id": 123
}
```

**Response** (200 OK):
```json
{
  "message": "Identification successful"
}
```

---

### Valider une Copie

```http
POST /api/copies/{id}/validate/
```

**Permissions**: `IsTeacherOrAdmin`

**Description**: Transition `STAGING` → `READY`.

**Response** (200 OK):
```json
{
  "message": "Copy validated and ready for grading.",
  "status": "READY"
}
```

---

## Endpoints Grading

### Liste des Copies (Correcteur)

```http
GET /api/copies/
```

**Permissions**: `IsTeacherOrAdmin`

**Description**: Liste toutes les copies disponibles pour correction (statuts `READY`, `LOCKED`, `GRADED`).

**Response**:
```json
[
  {
    "id": "uuid-...",
    "exam": {
      "id": "uuid-...",
      "name": "Bac Blanc Maths TG",
      "date": "2026-01-15"
    },
    "anonymous_id": "A3F7B2E1",
    "status": "READY",
    "locked_by": null
  }
]
```

---

### Détails d'une Copie

```http
GET /api/copies/{id}/
```

**Permissions**: `IsTeacherOrAdmin`

**Response**:
```json
{
  "id": "uuid-...",
  "exam_id": "uuid-...",
  "anonymous_id": "A3F7B2E1",
  "status": "LOCKED",
  "locked_by": {
    "id": 1,
    "username": "teacher1"
  },
  "locked_at": "2026-01-25T10:30:00Z",
  "pdf_source": "/media/copies/source/copy.pdf"
}
```

---

### Verrouiller une Copie

```http
POST /api/copies/{id}/lock/
Content-Type: application/json
```

**Permissions**: `IsTeacherOrAdmin`

**Payload** (optionnel):
```json
{
  "client_id": "uuid-client-..."
}
```

**Response** (200 OK):
```json
{
  "status": "LOCKED",
  "lock_token": "uuid-token-...",
  "expires_at": "2026-01-25T11:00:00Z"
}
```

**Erreurs**:
- `400`: Copie déjà verrouillée par un autre utilisateur
- `400`: Copie pas en statut `READY`

---

### Déverrouiller une Copie

```http
POST /api/copies/{id}/unlock/
Content-Type: application/json
```

**Permissions**: `IsTeacherOrAdmin`

**Payload**:
```json
{
  "lock_token": "uuid-token-..."
}
```

**Response** (200 OK):
```json
{
  "status": "READY"
}
```

---

### Finaliser une Copie

```http
POST /api/copies/{id}/finalize/
```

**Permissions**: `IsTeacherOrAdmin`

**Description**: Transition `LOCKED` → `GRADED`. Génère le PDF final avec annotations.

**Response** (200 OK):
```json
{
  "status": "GRADED"
}
```

---

### Télécharger PDF Final

```http
GET /api/copies/{id}/final-pdf/
```

**Permissions**: `AllowAny` (avec gates de sécurité)

**Security Gates**:
1. **Status Check**: Copie doit être `GRADED`
2. **Permission Check**:
   - Teachers/Admins: Accès complet
   - Students: Accès uniquement à leurs propres copies

**Response**: Fichier PDF (Content-Type: `application/pdf`)

**Headers**:
```
Content-Disposition: attachment; filename="copy_A3F7B2E1_corrected.pdf"
Cache-Control: no-store, private
X-Content-Type-Options: nosniff
```

---

### Historique d'Audit

```http
GET /api/copies/{id}/audit/
```

**Permissions**: `IsTeacherOrAdmin`

**Response**:
```json
[
  {
    "id": "uuid-...",
    "copy_id": "uuid-...",
    "action": "LOCK",
    "actor": {
      "id": 1,
      "username": "teacher1"
    },
    "timestamp": "2026-01-25T10:30:00Z",
    "metadata": {}
  },
  {
    "action": "CREATE_ANN",
    "timestamp": "2026-01-25T10:35:00Z",
    "metadata": {"annotation_id": "uuid-..."}
  }
]
```

---

## Endpoints Annotations

### Liste des Annotations

```http
GET /api/copies/{copy_id}/annotations/
```

**Permissions**: `IsTeacherOrAdmin`

**Response**:
```json
[
  {
    "id": "uuid-...",
    "copy_id": "uuid-...",
    "page_index": 0,
    "x": 0.25,
    "y": 0.30,
    "w": 0.50,
    "h": 0.10,
    "content": "Bonne réponse mais manque de justification",
    "type": "COMMENT",
    "score_delta": -1,
    "created_by": {
      "id": 1,
      "username": "teacher1"
    },
    "created_at": "2026-01-25T10:35:00Z"
  }
]
```

---

### Créer une Annotation

```http
POST /api/copies/{copy_id}/annotations/
Content-Type: application/json
```

**Permissions**: `IsTeacherOrAdmin` + `IsLockedByOwnerOrReadOnly`

**Payload**:
```json
{
  "page_index": 0,
  "x": 0.25,
  "y": 0.30,
  "w": 0.50,
  "h": 0.10,
  "content": "Bonne réponse",
  "type": "COMMENT",
  "score_delta": 2
}
```

**Validations**:
- `page_index`: >= 0, < nombre de pages
- `x, y, w, h`: Entre 0.0 et 1.0 (coordonnées normalisées)
- `type`: `COMMENT`, `HIGHLIGHT`, `ERROR`, `BONUS`

**Response** (201 Created):
```json
{
  "id": "uuid-...",
  "copy_id": "uuid-...",
  "page_index": 0,
  "x": 0.25,
  "y": 0.30,
  "w": 0.50,
  "h": 0.10,
  "content": "Bonne réponse",
  "type": "COMMENT",
  "score_delta": 2,
  "created_by": {...},
  "created_at": "2026-01-25T10:35:00Z"
}
```

---

### Modifier une Annotation

```http
PATCH /api/annotations/{id}/
Content-Type: application/json
```

**Permissions**: `IsTeacherOrAdmin` + Owner uniquement

**Payload**:
```json
{
  "content": "Très bonne réponse",
  "score_delta": 3
}
```

**Response** (200 OK):
```json
{
  "id": "uuid-...",
  "content": "Très bonne réponse",
  "score_delta": 3,
  "updated_at": "2026-01-25T10:40:00Z"
}
```

---

### Supprimer une Annotation

```http
DELETE /api/annotations/{id}/
```

**Permissions**: `IsTeacherOrAdmin` + Owner uniquement

**Response** (204 No Content)

---

## Endpoints Students

### Liste des Élèves

```http
GET /api/students/
```

**Permissions**: `IsTeacherOrAdmin`

**Response**:
```json
[
  {
    "id": 123,
    "ine": "1234567890A",
    "first_name": "Jean",
    "last_name": "Dupont",
    "class_name": "TG2",
    "email": "jean.dupont@example.com"
  }
]
```

---

### Import CSV Élèves

```http
POST /api/students/import/
Content-Type: multipart/form-data
```

**Permissions**: `IsTeacherOrAdmin`

**Payload**:
```
csv_file: <file>
```

**Format CSV**:
```csv
ine,first_name,last_name,class_name,email
1234567890A,Jean,Dupont,TG2,jean.dupont@example.com
```

**Response** (201 Created):
```json
{
  "message": "25 students imported successfully"
}
```

---

### Mes Copies (Portail Élève)

```http
GET /api/students/my-copies/
```

**Permissions**: `IsStudent` (session-based)

**Response**:
```json
[
  {
    "id": "uuid-...",
    "exam_name": "Bac Blanc Maths TG",
    "date": "2026-01-15",
    "total_score": 15.5,
    "status": "GRADED",
    "final_pdf_url": "/api/copies/uuid-.../final-pdf/",
    "scores_details": {
      "ex1_q1": 3,
      "ex1_q2": 7
    }
  }
]
```

---

### Login Élève

```http
POST /api/students/login/
Content-Type: application/json
```

**Payload**:
```json
{
  "ine": "1234567890A",
  "birth_date": "2005-03-15"
}
```

**Response** (200 OK):
```json
{
  "student": {
    "id": 123,
    "first_name": "Jean",
    "last_name": "Dupont",
    "class_name": "TG2"
  }
}
```

**Session**: `student_id` stocké dans session Django

---

## Codes d'Erreur

| Code | Signification | Description |
|------|---------------|-------------|
| `200` | OK | Requête réussie |
| `201` | Created | Ressource créée |
| `204` | No Content | Suppression réussie |
| `400` | Bad Request | Données invalides |
| `401` | Unauthorized | Authentification requise |
| `403` | Forbidden | Permission refusée |
| `404` | Not Found | Ressource introuvable |
| `409` | Conflict | Conflit (ex: copie déjà verrouillée) |
| `429` | Too Many Requests | Rate limit dépassé |
| `500` | Internal Server Error | Erreur serveur |

### Format des Erreurs

```json
{
  "detail": "Description de l'erreur"
}
```

**Exemple** (400 Bad Request):
```json
{
  "detail": "Cannot lock copy not in READY status"
}
```

---

## Rate Limiting

### Limites par Défaut

| Endpoint | Limite | Fenêtre |
|----------|--------|---------|
| `POST /api/auth/login/` | 5 requêtes | 5 minutes |
| `POST /api/exams/upload/` | 10 requêtes | 1 heure |
| Autres endpoints | 100 requêtes | 1 minute |

### Headers de Réponse

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1643097600
```

### Erreur Rate Limit

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json

{
  "detail": "Request was throttled. Expected available in 45 seconds."
}
```

---

## Exemples

### Exemple 1: Workflow Complet de Correction

```bash
# 1. Login
curl -X POST http://localhost:8088/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "teacher1", "password": "pass123"}' \
  -c cookies.txt

# 2. Lister les copies disponibles
curl -X GET http://localhost:8088/api/copies/ \
  -b cookies.txt

# 3. Verrouiller une copie
curl -X POST http://localhost:8088/api/copies/{copy_id}/lock/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <token>" \
  -b cookies.txt

# 4. Créer une annotation
curl -X POST http://localhost:8088/api/copies/{copy_id}/annotations/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <token>" \
  -b cookies.txt \
  -d '{
    "page_index": 0,
    "x": 0.25,
    "y": 0.30,
    "w": 0.50,
    "h": 0.10,
    "content": "Bonne réponse",
    "type": "COMMENT",
    "score_delta": 2
  }'

# 5. Finaliser la copie
curl -X POST http://localhost:8088/api/copies/{copy_id}/finalize/ \
  -H "X-CSRFToken: <token>" \
  -b cookies.txt

# 6. Télécharger le PDF final
curl -X GET http://localhost:8088/api/copies/{copy_id}/final-pdf/ \
  -b cookies.txt \
  -o copy_final.pdf
```

---

### Exemple 2: Upload et Traitement Examen

```bash
# Upload PDF examen
curl -X POST http://localhost:8088/api/exams/ \
  -H "X-CSRFToken: <token>" \
  -b cookies.txt \
  -F "name=Bac Blanc Maths TG" \
  -F "date=2026-01-15" \
  -F "pdf_source=@exam.pdf"

# Response:
# {
#   "id": "uuid-...",
#   "booklets_created": 25,
#   "message": "25 booklets created successfully"
# }

# Lister les fascicules
curl -X GET http://localhost:8088/api/exams/{exam_id}/booklets/ \
  -b cookies.txt

# Fusionner des fascicules en copie
curl -X POST http://localhost:8088/api/exams/{exam_id}/merge/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: <token>" \
  -b cookies.txt \
  -d '{"booklet_ids": ["uuid-1", "uuid-2"]}'
```

---

### Exemple 3: Portail Élève

```bash
# Login élève
curl -X POST http://localhost:8088/api/students/login/ \
  -H "Content-Type: application/json" \
  -d '{"ine": "1234567890A", "birth_date": "2005-03-15"}' \
  -c student_cookies.txt

# Lister mes copies
curl -X GET http://localhost:8088/api/students/my-copies/ \
  -b student_cookies.txt

# Télécharger ma copie corrigée
curl -X GET http://localhost:8088/api/copies/{copy_id}/final-pdf/ \
  -b student_cookies.txt \
  -o ma_copie.pdf
```

---

## Schéma OpenAPI

L'API expose un schéma OpenAPI 3.0 généré automatiquement via DRF Spectacular:

```http
GET /api/schema/
```

**Interface Swagger UI**:
```
http://localhost:8088/api/schema/swagger-ui/
```

**Interface ReDoc**:
```
http://localhost:8088/api/schema/redoc/
```

---

## Références

- [ARCHITECTURE.md](file:///home/alaeddine/viatique__PMF/docs/ARCHITECTURE.md) - Architecture globale
- [DATABASE_SCHEMA.md](file:///home/alaeddine/viatique__PMF/docs/DATABASE_SCHEMA.md) - Schéma base de données
- [SECURITY_GUIDE.md](file:///home/alaeddine/viatique__PMF/docs/SECURITY_GUIDE.md) - Guide de sécurité
- [backend/exams/views.py](file:///home/alaeddine/viatique__PMF/backend/exams/views.py) - Code source views exams
- [backend/grading/views.py](file:///home/alaeddine/viatique__PMF/backend/grading/views.py) - Code source views grading

---

**Dernière mise à jour**: 25 janvier 2026  
**Auteur**: Aleddine BEN RHOUMA  
**Licence**: Propriétaire - AEFE/Éducation Nationale
