# ADR-002 : Normalisation des Coordonnées d'Annotations [0, 1]

## Statut
✅ **Accepté** (2026-01-21)

## Contexte

Les annotations vectorielles (traits, textes, formes) sont capturées sur un Canvas HTML côté frontend et doivent être exportées sur un PDF côté backend.

**Problème** :
- Le Canvas frontend peut avoir différentes tailles (zoom, responsive)
- Le PDF backend a sa propre résolution (points PDF)
- Les annotations doivent rester précises quel que soit l'affichage

**Contraintes** :
- Fidélité visuelle entre interface correction et PDF final
- Support du zoom sans perte de précision
- Indépendance résolution d'affichage
- Export PDF identique quel que soit le device de correction

## Décision

**Normaliser TOUTES les coordonnées dans l'intervalle [0, 1] relatif aux dimensions de la page.**

### Format

```json
{
  "type": "path",
  "points": [
    {"x": 0.1234, "y": 0.5678},  // x = 12.34% largeur, y = 56.78% hauteur
    {"x": 0.2345, "y": 0.6789}
  ]
}
```

### Transformation

**Frontend (capture)** :
```javascript
function normalizeCoordinates(x, y, canvasWidth, canvasHeight) {
  return {
    x: x / canvasWidth,   // [0, 1]
    y: y / canvasHeight   // [0, 1]
  }
}
```

**Backend (export PDF)** :
```python
def denormalizeCoordinates(normalizedX, normalizedY, pdfWidth, pdfHeight):
    return {
        x: normalizedX * pdfWidth,
        y: normalizedY * pdfHeight
    }
```

## Conséquences

### Positives
- ✅ Indépendance de la résolution d'affichage
- ✅ Zoom sans perte de précision
- ✅ Export PDF correct quelle que soit la taille
- ✅ Coordination frontend/backend simple
- ✅ Format de stockage compact et lisible

### Négatives
- ❌ Transformation nécessaire à chaque affichage/export
- ❌ Légère complexité calcul (mais triviale)
- ❌ Tests précision floating point nécessaires

### Risques
- ⚠️ Erreurs d'arrondi si trop de transformations (mitigé : 1 seule dénormalisation à l'export)
- ⚠️ Coordonnées hors [0, 1] si bug (validation stricte requise)

## Alternatives Considérées

### Alternative A : Coordonnées en pixels absolus
**Rejetée car** :
- Dépendance à la résolution d'affichage
- Zoom casserait la précision
- Export PDF incorrect si tailles différentes
- Problème responsive mobile

### Alternative B : Coordonnées en points PDF natifs
**Rejetée car** :
- Frontend devrait connaître dimension PDF exacte
- Zoom complexifié
- Couplage fort frontend/backend

### Alternative C : Stocker pixels + résolution
**Rejetée car** :
- Format plus lourd
- Calcul de conversion plus complexe
- Pas d'avantage réel

## Validation

Cette décision respecte :
- ✅ Pipeline PDF déterministe (règle 05_pdf_processing_rules.md)
- ✅ Pas de perte d'annotations
- ✅ Qualité visuelle garantie

## Implémentation Requise

- [x] Normalisation frontend (useCanvas composable)
- [x] Dénormalisation backend (PDFAnnotationFlattener)
- [x] Validation coordonnées [0, 1] côté backend
- [x] Tests précision (round-trip frontend → backend → PDF)
- [x] Documentation workflow pdf_annotation_export_flow.md

## Tests Critiques

```python
def test_annotation_coordinates_normalized():
    # Annotation doit avoir coordonnées [0, 1]
    for point in annotation['points']:
        assert 0 <= point['x'] <= 1
        assert 0 <= point['y'] <= 1

def test_pdf_export_precision():
    # Round-trip : capture → stockage → export
    # Vérifier position visuelle identique (tolerance ±2 pixels)
    pass
```

## Exemple Concret

**Canvas 800x600px** :
- Clic à (400, 300) → stocké comme (0.5, 0.5)

**PDF A4 (595x842 points)** :
- Export à (0.5 * 595, 0.5 * 842) = (297.5, 421)

**Canvas 1600x1200px (zoom x2)** :
- Clic à (800, 600) → stocké comme (0.5, 0.5) → **identique**

## Date
2026-01-21

## Auteur
Alaeddine BEN RHOUMA (PDF Processing Expert)
