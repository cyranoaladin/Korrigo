# Étape 3 — Backend Annotation & Grading : Rapport de Conformité

**Date** : 2026-01-21
**Statut** : ✅ COMPLÉTÉ - Runtime Tests OK
**Gouvernance** : `.claude/` v1.1.0
**Référence ADR** : ADR-002 (coordonnées normalisées), ADR-003 (machine d'état)
**Commits précédents** : Étape 1 (P0), Étape 2 (Pipeline PDF)

---

## Résumé Exécutif

L'Étape 3 implémente le workflow complet d'**annotation** et de **grading** des copies, côté backend :

1. ✅ **Modèles de données** : Annotation (ADR-002 compliant), GradingEvent (audit log), champs traçabilité Copy
2. ✅ **Services métier** : AnnotationService + GradingService avec machine d'état stricte (ADR-003)
3. ✅ **API REST** : 7 endpoints protégés par `IsTeacherOrAdmin` (staff only)
4. ✅ **PDFFlattener** : Adapté pour coordonnées normalisées [0,1] + page de synthèse
5. ✅ **Tests runtime** : 6 tests passés (création, refus, lock, unlock, finalize)

---

## Machine d'État (ADR-003)

### Diagramme

```
STAGING ──(validate)──> READY ──(lock)──> LOCKED ──(finalize)──> GRADED
                          ↑                 │
                          └──── (unlock) ───┘
```

### Règles Strictes pour Annotations

| État    | Création | Modification | Suppression | Lecture |
|---------|----------|--------------|-------------|---------|
| STAGING | ❌ Refus | ❌ Refus     | ❌ Refus    | ✅ OK   |
| READY   | ✅ OK    | ✅ OK        | ✅ OK       | ✅ OK   |
| LOCKED  | ❌ Refus | ❌ Refus     | ❌ Refus    | ✅ OK   |
| GRADED  | ❌ Refus | ❌ Refus     | ❌ Refus    | ✅ OK   |

**LOCKED et GRADED sont en lecture seule.**

---

## Modèles Implémentés

### 1. Annotation (Refactor Complet)

**Fichier** : `backend/grading/models.py`

**Changements** :
- ❌ Suppression : `page_number` (1-based), `vector_data` (JSONField)
- ❌ Suppression : Modèle `Score` (redondant avec `score_delta`)
- ✅ Ajout : `page_index` (0-based), `x, y, w, h` (float [0,1])
- ✅ Ajout : `content`, `type` (enum), `score_delta`, `created_by`

**Structure** :
```python
class Annotation(models.Model):
    class Type(models.TextChoices):
        COMMENT = 'COMMENT'
        HIGHLIGHT = 'HIGHLIGHT'
        ERROR = 'ERROR'
        BONUS = 'BONUS'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    copy = models.ForeignKey(Copy, on_delete=models.CASCADE, related_name='annotations')
    page_index = models.PositiveIntegerField()  # 0-based

    # ADR-002 : Coordonnées normalisées [0, 1]
    x = models.FloatField()
    y = models.FloatField()
    w = models.FloatField()
    h = models.FloatField()

    content = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.COMMENT)
    score_delta = models.IntegerField(null=True, blank=True)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='annotations_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### 2. GradingEvent (Nouveau)

**Fichier** : `backend/grading/models.py`

**Rôle** : Journal d'audit des événements de correction

**Structure** :
```python
class GradingEvent(models.Model):
    class Action(models.TextChoices):
        VALIDATE = 'VALIDATE'  # STAGING→READY
        LOCK = 'LOCK'          # READY→LOCKED
        UNLOCK = 'UNLOCK'      # LOCKED→READY
        GRADE = 'GRADE'        # Notation en cours
        FINALIZE = 'FINALIZE'  # LOCKED→GRADED

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    copy = models.ForeignKey(Copy, on_delete=models.CASCADE, related_name='grading_events')
    action = models.CharField(max_length=20, choices=Action.choices)
    actor = models.ForeignKey(User, on_delete=models.PROTECT, related_name='grading_actions')
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)
```

### 3. Copy (Traçabilité ajoutée)

**Fichier** : `backend/exams/models.py`

**Champs ajoutés** :
```python
validated_at = models.DateTimeField(null=True, blank=True)  # STAGING→READY
locked_at = models.DateTimeField(null=True, blank=True)     # READY→LOCKED
locked_by = models.ForeignKey(User, null=True, blank=True)
graded_at = models.DateTimeField(null=True, blank=True)     # LOCKED→GRADED
```

---

## Services Métier

### AnnotationService

**Fichier** : `backend/grading/services.py`

**Méthodes** :
- `add_annotation(copy, payload, user)` : Création (READY uniquement)
- `update_annotation(annotation, payload, user)` : Modification (READY uniquement)
- `delete_annotation(annotation, user)` : Suppression (READY uniquement)
- `list_annotations(copy)` : Lecture (tous statuts)
- `validate_coordinates(x, y, w, h)` : Validation ADR-002

**Règles** :
- Validation stricte coordonnées [0, 1]
- Vérification machine d'état avant chaque opération
- Transactions atomiques
- Logging de toutes les actions

### GradingService

**Fichier** : `backend/grading/services.py`

**Méthodes** :
- `compute_score(copy)` : Calcul score total (somme des `score_delta`)
- `validate_copy(copy, user)` : STAGING → READY
- `lock_copy(copy, user)` : READY → LOCKED
- `unlock_copy(copy, user)` : LOCKED → READY
- `finalize_copy(copy, user)` : LOCKED → GRADED + génération PDF

**Règles** :
- Vérification stricte des transitions (ADR-003)
- Création systématique de GradingEvent
- Appel PDFFlattener lors du finalize
- Transactions atomiques

---

## Endpoints API

**Tous protégés par `IsTeacherOrAdmin` (staff uniquement)**

| Méthode | Route | Fonction | Permission |
|---------|-------|----------|------------|
| GET | `/api/copies/<copy_id>/annotations/` | Liste annotations | IsTeacherOrAdmin |
| POST | `/api/copies/<copy_id>/annotations/` | Crée annotation | IsTeacherOrAdmin |
| GET | `/api/annotations/<id>/` | Récupère annotation | IsTeacherOrAdmin |
| PATCH | `/api/annotations/<id>/` | Modifie annotation | IsTeacherOrAdmin |
| DELETE | `/api/annotations/<id>/` | Supprime annotation | IsTeacherOrAdmin |
| POST | `/api/copies/<id>/lock/` | Verrouille copie | IsTeacherOrAdmin |
| POST | `/api/copies/<id>/unlock/` | Déverrouille copie | IsTeacherOrAdmin |
| POST | `/api/copies/<id>/finalize/` | Finalise correction | IsTeacherOrAdmin |

**Fichiers** :
- Views : `backend/grading/views.py`
- URLs : `backend/grading/urls.py`
- Permission : `backend/exams/permissions.py`

---

## PDFFlattener (Adapté)

**Fichier** : `backend/processing/services/pdf_flattener.py`

**Modifications ADR-002** :
- ✅ Lecture annotations via `x, y, w, h` (au lieu de `vector_data`)
- ✅ Utilisation `page_index` 0-based (au lieu de `page_number` 1-based)
- ✅ Dénormalisation coordonnées : `x_pdf = x * page_width`
- ✅ Dessin rectangles d'annotation avec couleurs par type
- ✅ Affichage `score_delta` sur chaque annotation
- ✅ Page de synthèse avec score total et détails

**Workflow** :
```python
1. Pour chaque page (PNG) du booklet :
   a. Convertir PNG → page PDF
   b. Filtrer annotations pour page_index
   c. Dénormaliser coordonnées [0,1] → points PDF
   d. Dessiner rectangles + texte + score_delta
2. Ajouter page de synthèse :
   - Titre "Relevé de Notes"
   - Détail par annotation avec score_delta
   - Score total
3. Sauvegarder PDF final dans copy.final_pdf
```

**Couleurs** :
- COMMENT : Bleu (0, 0, 1)
- HIGHLIGHT : Jaune (1, 1, 0)
- ERROR : Rouge (1, 0, 0)
- BONUS : Vert (0, 0.5, 0)

---

## Migrations Créées

### 1. grading/migrations/0002_refactor_annotation_and_add_grading_event.py

**Actions** :
- Suppression modèle `Score`
- Suppression ancien modèle `Annotation`
- Création nouveau modèle `Annotation` (ADR-002 compliant)
- Création modèle `GradingEvent`
- Ajout indexes sur `(copy, page_index)` et `(copy, -timestamp)`

**Statut** : ✅ Applied

### 2. exams/migrations/0005_add_copy_traceability_fields.py

**Actions** :
- Ajout `validated_at` à Copy
- Ajout `locked_at` à Copy
- Ajout `locked_by` à Copy
- Ajout `graded_at` à Copy

**Statut** : ✅ Applied

---

## Permissions

### IsTeacherOrAdmin (Nouveau)

**Fichier** : `backend/exams/permissions.py`

```python
class IsTeacherOrAdmin(permissions.BasePermission):
    """
    Allows access only to authenticated staff users (teachers or admins).
    Used for all grading and annotation endpoints.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff
```

**Usage** : Appliqué sur TOUS les endpoints de l'Étape 3 (aucun accès élève).

---

## Tests Runtime (6 OBLIGATOIRES)

**Date** : 2026-01-21 11:06 UTC
**User** : admin (staff)
**Copies test** :
- `fe7d097c-1b5c-491a-ae30-a58aaed216bb` : READY → LOCKED → READY → LOCKED → GRADED
- `6d862159-3f40-4325-a92e-a505a7121d37` : STAGING (pour test refus)

### Test 1 : Créer annotation sur copy READY → 201

**Commande** :
```bash
curl -i -X POST "http://localhost:8088/api/copies/fe7d097c-1b5c-491a-ae30-a58aaed216bb/annotations/" \
  -b /tmp/cookiejar_etape3 \
  -H "X-CSRFToken: Zj36axjtvZ1OGPoArhmWiCaI4q5L23GM" \
  -H "Content-Type: application/json" \
  -d '{
    "page_index": 0,
    "x": 0.1,
    "y": 0.2,
    "w": 0.3,
    "h": 0.05,
    "content": "Bonne réponse!",
    "type": "COMMENT",
    "score_delta": 5
  }'
```

**Résultat** :
```
HTTP/1.1 201 Created
Content-Type: application/json

{
  "id":"4b31af66-6d7d-41ea-84d7-caf220f7a726",
  "copy":"fe7d097c-1b5c-491a-ae30-a58aaed216bb",
  "page_index":0,
  "x":0.1,"y":0.2,"w":0.3,"h":0.05,
  "content":"Bonne réponse!",
  "type":"COMMENT",
  "score_delta":5,
  "created_by":6,
  "created_by_username":"admin",
  "created_at":"2026-01-21T11:06:07.239935Z",
  "updated_at":"2026-01-21T11:06:07.239942Z"
}
```

✅ **Validé** : Annotation créée avec succès sur copy READY.

### Test 2 : Créer annotation sur copy STAGING → refus (400)

**Commande** :
```bash
curl -i -X POST "http://localhost:8088/api/copies/6d862159-3f40-4325-a92e-a505a7121d37/annotations/" \
  -b /tmp/cookiejar_etape3 \
  -H "X-CSRFToken: Zj36axjtvZ1OGPoArhmWiCaI4q5L23GM" \
  -H "Content-Type: application/json" \
  -d '{
    "page_index": 0,
    "x": 0.1,
    "y": 0.2,
    "w": 0.3,
    "h": 0.05,
    "content": "Test",
    "type": "COMMENT"
  }'
```

**Résultat** :
```
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error":"Cannot add annotation to copy in status STAGING. Only READY copies can be annotated."
}
```

✅ **Validé** : Création refusée sur copy STAGING (machine d'état respectée).

### Test 3 : Lock copy READY → 200 + status LOCKED

**Commande** :
```bash
curl -i -X POST "http://localhost:8088/api/copies/fe7d097c-1b5c-491a-ae30-a58aaed216bb/lock/" \
  -b /tmp/cookiejar_etape3 \
  -H "X-CSRFToken: Zj36axjtvZ1OGPoArhmWiCaI4q5L23GM"
```

**Résultat** :
```
HTTP/1.1 200 OK
Content-Type: application/json

{
  "message":"Copy locked successfully",
  "copy_id":"fe7d097c-1b5c-491a-ae30-a58aaed216bb",
  "status":"LOCKED",
  "locked_by":"admin"
}
```

✅ **Validé** : Transition READY → LOCKED réussie.

### Test 4 : Modifier annotation quand copy LOCKED → refus (400)

**Commande** :
```bash
curl -i -X PATCH "http://localhost:8088/api/annotations/4b31af66-6d7d-41ea-84d7-caf220f7a726/" \
  -b /tmp/cookiejar_etape3 \
  -H "X-CSRFToken: Zj36axjtvZ1OGPoArhmWiCaI4q5L23GM" \
  -H "Content-Type: application/json" \
  -d '{"content": "Tentative modification"}'
```

**Résultat** :
```
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error":"Cannot update annotation of copy in status LOCKED. Only READY copies can have their annotations modified."
}
```

✅ **Validé** : Modification refusée sur copy LOCKED (lecture seule).

### Test 5a : Unlock copy → 200 + status READY

**Commande** :
```bash
curl -i -X POST "http://localhost:8088/api/copies/fe7d097c-1b5c-491a-ae30-a58aaed216bb/unlock/" \
  -b /tmp/cookiejar_etape3 \
  -H "X-CSRFToken: Zj36axjtvZ1OGPoArhmWiCaI4q5L23GM"
```

**Résultat** :
```
HTTP/1.1 200 OK
Content-Type: application/json

{
  "message":"Copy unlocked successfully",
  "copy_id":"fe7d097c-1b5c-491a-ae30-a58aaed216bb",
  "status":"READY"
}
```

✅ **Validé** : Transition LOCKED → READY réussie (unlock).

### Test 5b : Modification annotation après unlock → 200

**Commande** :
```bash
curl -i -X PATCH "http://localhost:8088/api/annotations/4b31af66-6d7d-41ea-84d7-caf220f7a726/" \
  -b /tmp/cookiejar_etape3 \
  -H "X-CSRFToken: Zj36axjtvZ1OGPoArhmWiCaI4q5L23GM" \
  -H "Content-Type: application/json" \
  -d '{"content": "Modification réussie après unlock"}'
```

**Résultat** :
```
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id":"4b31af66-6d7d-41ea-84d7-caf220f7a726",
  "content":"Modification réussie après unlock",
  "updated_at":"2026-01-21T11:06:07.735620Z",
  ...
}
```

✅ **Validé** : Modification autorisée après unlock (copy READY).

### Test 6a : Finalize copy → 200 + status GRADED + PDF généré

**Commande** :
```bash
# Re-lock first
curl -X POST "http://localhost:8088/api/copies/fe7d097c-1b5c-491a-ae30-a58aaed216bb/lock/" \
  -b /tmp/cookiejar_etape3 -H "X-CSRFToken: Zj36axjtvZ1OGPoArhmWiCaI4q5L23GM"

# Then finalize
curl -i -X POST "http://localhost:8088/api/copies/fe7d097c-1b5c-491a-ae30-a58aaed216bb/finalize/" \
  -b /tmp/cookiejar_etape3 -H "X-CSRFToken: Zj36axjtvZ1OGPoArhmWiCaI4q5L23GM"
```

**Résultat** :
```
HTTP/1.1 200 OK
Content-Type: application/json

{
  "message":"Copy finalized successfully",
  "copy_id":"fe7d097c-1b5c-491a-ae30-a58aaed216bb",
  "status":"GRADED",
  "final_score":5,
  "final_pdf":"/media/copies/final/copy_fe7d097c-1b5c-491a-ae30-a58aaed216bb_corrected.pdf"
}
```

✅ **Validé** : Transition LOCKED → GRADED + PDF généré (score: 5 points).

### Test 6b : Modification annotation après GRADED → refus (400)

**Commande** :
```bash
curl -i -X PATCH "http://localhost:8088/api/annotations/4b31af66-6d7d-41ea-84d7-caf220f7a726/" \
  -b /tmp/cookiejar_etape3 \
  -H "X-CSRFToken: Zj36axjtvZ1OGPoArhmWiCaI4q5L23GM" \
  -H "Content-Type: application/json" \
  -d '{"content": "Tentative modification après GRADED"}'
```

**Résultat** :
```
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error":"Cannot update annotation of copy in status GRADED. Only READY copies can have their annotations modified."
}
```

✅ **Validé** : Modification refusée sur copy GRADED (immutable).

---

## Conformité Gouvernance `.claude/`

### Règles Respectées

✅ `.claude/rules/01_security_rules.md` § 1.1.1 - IsTeacherOrAdmin sur tous endpoints
✅ `.claude/rules/02_backend_rules.md` § 2.1 - Service Layer (AnnotationService, GradingService)
✅ `.claude/rules/02_backend_rules.md` § 4.2 - Pas de logique métier dans views
✅ `.claude/rules/02_backend_rules.md` § 6.1 - Transactions atomiques (@transaction.atomic)
✅ `.claude/rules/04_database_rules.md` § 2.1 - Migrations cohérentes (0002 grading, 0005 exams)

### ADR Respectés

✅ **ADR-002** : Coordonnées normalisées [0,1] (x, y, w, h + dénormalisation dans PDFFlattener)
✅ **ADR-003** : Machine d'état stricte (STAGING → READY → LOCKED → GRADED)
✅ **ADR-003** : LOCKED = lecture seule pour annotations
✅ **ADR-003** : Traçabilité complète (GradingEvent + champs timestamps)

---

## Invariants Garantis

### Machine d'État

✅ **Transitions validées**
- STAGING peut uniquement aller vers READY (via validate)
- READY peut aller vers LOCKED (via lock)
- LOCKED peut aller vers READY (via unlock) ou GRADED (via finalize)
- GRADED est immutable (pas de transition sortante)

✅ **Règles annotations**
- Création/modification/suppression : READY uniquement
- LOCKED et GRADED : lecture seule
- Toute tentative invalide → ValueError (HTTP 400)

### Données

✅ **Coordonnées normalisées (ADR-002)**
- Validation stricte [0, 1] avant création
- Dénormalisation lors de l'export PDF
- Indépendance résolution d'affichage

✅ **Traçabilité**
- Chaque transition → GradingEvent créé
- Timestamps : validated_at, locked_at, graded_at
- Actor tracké (locked_by, created_by)

✅ **Atomicité**
- Toutes les opérations métier : @transaction.atomic
- Rollback automatique en cas d'erreur
- Cohérence base de données garantie

---

## Statut Final : ✅ ANNOTATION & GRADING WORKFLOW FONCTIONNEL

### Métriques

| Métrique | Valeur |
|----------|--------|
| Modèles créés/refactorés | 2 (Annotation refactor, GradingEvent nouveau) |
| Modèles supprimés | 1 (Score) |
| Services créés | 2 (AnnotationService, GradingService) |
| Endpoints ajoutés | 7 (annotations + workflow) |
| Permission créée | 1 (IsTeacherOrAdmin) |
| Migrations créées | 2 (grading 0002, exams 0005) |
| Tests runtime OK | 6/6 ✅ |
| PDFFlattener | Adapté ADR-002 |
| Conformité ADR | 100% |
| Régression Étape 2 | ❌ Aucune |

---

**Auteur** : Claude Sonnet 4.5
**Date** : 2026-01-21
**Prochaine Étape** : Étape 4 (Features frontend annotation/grading ou autre selon cahier)
