# Scripts de test runtime - Étape 3

## `test_etape3_p0_validation_simple.sh`

### Objectif

Prouve les 4 invariants P0 de validation des annotations (ADR-002) :

1. **w = 0** → rejeté avec 400 (rectangle vide)
2. **x + w > 1** → rejeté avec 400 (débordement horizontal)
3. **page_index hors bornes** → rejeté avec 400 (page inexistante)
4. **PATCH partiel causant débordement** → rejeté avec 400 (validation avec valeurs candidates)

### Prérequis

- Backend Docker up : `docker-compose up -d backend`
- Base de données migrée : `docker-compose exec backend python manage.py migrate`
- User staff existant (le script crée `admin/adminpass123` automatiquement)
- Copy READY avec au moins 2 pages dans `pages_images`

### Exécution

```bash
./scripts/test_etape3_p0_validation_simple.sh
```

Le script crée automatiquement :
- Un user staff `admin` (si inexistant)
- Un exam avec un booklet (2 pages fake)
- Une copy READY

### Output attendu

```
✅ w=0 rejected -> 400
✅ x+w overflow rejected -> 400
✅ page_index out of bounds rejected -> 400
✅ PATCH partial overflow rejected -> 400

✅✅ All 4 P0 validation tests passed!
```

### ⚠️ Note importante : recharger le code

Si tu modifies le code backend (`services.py`, `views.py`, etc.), **redémarre le conteneur** avant de relancer les tests :

```bash
docker-compose restart backend
sleep 5
./scripts/test_etape3_p0_validation_simple.sh
```

Sinon, le conteneur utilise l'ancienne version du code et les tests peuvent donner des faux positifs/négatifs.

### Dépannage

**Erreur 403/401** : Vérifie que le user `admin` existe et est staff.

**Erreur 404** : Vérifie que les URLs `/api/copies/<id>/annotations/` et `/api/annotations/<id>/` sont bien configurées dans `grading/urls.py`.

**Erreur 500** : Regarde les logs backend : `docker-compose logs backend --tail=50`

**Login échoue** : Vérifie que l'endpoint `/api/login/` existe (devrait retourner 405 sur GET, 200 sur POST avec credentials valides).

### Architecture testée

```
HTTP POST /api/copies/{copy_id}/annotations/
  ↓
AnnotationListCreateView.create()
  ↓
AnnotationService.add_annotation()
  ↓
  ├─ validate_page_index(copy, page_index)  [borne [0, nb_pages-1]]
  └─ validate_coordinates(x, y, w, h)       [w>0, h>0, x+w≤1, y+h≤1]
     ↓
  ValueError → HTTP 400
```

La validation se fait au **service layer** (source de vérité), pas au serializer (qui est bypassé).
