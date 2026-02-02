# Audit Batch A3 - Segmentation Multi-Feuilles par Élève

**Date**: 2026-02-02
**Auditeur**: Claude Sonnet 4.5
**Contexte**: Finalisation PRD-19 - Workflow batch A3 complet

---

## Résumé Exécutif

✅ **Structure de base fonctionnelle** : Le découpage A3→A4 et le réordonnancement des pages fonctionnent correctement.
❌ **OCR défaillant** : L'OCR Tesseract standard échoue complètement sur l'écriture manuscrite des formulaires CMEN v2.
❌ **Segmentation multi-feuilles non activée** : La fusion par élève ne se produit JAMAIS car tous les `student_match` sont `None`.

---

## Tests Réalisés

### Test 1 : Batch réel (eval_loi_binom_log.pdf + G3_EDS_MATHS.csv)

**Données :**
- PDF : 88 pages A3 (44 feuilles élèves)
- CSV : 28 élèves dans la whitelist
- Format : Formulaires CMEN v2 avec cases manuscrites

**Résultats :**
```
Total A3 pages: 88
Total A4 pages: 176
Total sheets: 44
Copies created: 44 (au lieu de ~28)
Identified: 0
Needs review: 44
```

**Validation des invariants :**
✅ Toutes les copies ont un nombre de pages multiple de 4
✅ Chaque copie a exactement 4 pages (1 feuille)
❌ Aucune Copy multi-feuilles créée (fusion non activée)

---

## Analyse Technique

### Découpage A3→A4

**Status:** ✅ FONCTIONNEL

Le processeur applique correctement le mapping :
- A3 #1 (RECTO) : P4 (gauche) + P1 (droite)
- A3 #2 (VERSO) : P2 (gauche) + P3 (droite)
- Ordre final : [P1, P2, P3, P4]

**Preuve :** 88 A3 → 176 A4 (88 × 2)

### OCR Header

**Status:** ❌ DÉFAILLANT

**Exemple extraction réelle :**

**Formulaire CMEN v2:**
```
Nom : ZARDI (manuscrit)
Prénom : MOHAMED (manuscrit)
Né(e) le : 21/03/2007 (manuscrit)
```

**OCR Tesseract extrait:**
```
name='TITIIITITTITITII', date=''
```

**Cause root :**
- Tesseract standard optimisé pour texte imprimé
- Formulaires CMEN utilisent cases manuscrites individuelles
- Aucun prétraitement spécifique pour segmentation par cases

### Matching CSV

**Status:** ❌ INOPÉRANT (dépend de l'OCR)

- CSV chargé correctement : 28 élèves
- Algorithme Jaccard fonctionnel
- **Mais** : garbage OCR ne peut matcher aucun nom du CSV
- Résultat : `student_match = None` pour toutes les feuilles

### Segmentation Multi-Feuilles

**Status:** ⚠️ CODE PRÉSENT MAIS NON ACTIVÉ

**Code implémenté (batch_processor.py:534-650):**
```python
def _segment_by_student(self, pages, exam_id):
    # ...
    if self._is_same_student(current_student, new_student):
        # MÊME ÉLÈVE: on continue à accumuler les pages
        logger.info(f"Sheet {sheet_count}: Same student, concatenating")
        current_header_crops.append(...)
    else:
        # NOUVEL ÉLÈVE: fermer la copie précédente
        student_copies.append(StudentCopy(...))
        current_student = new_student
```

**Problème :**
```python
def _is_same_student(self, student1, student2):
    if student1 is None or student2 is None:
        return False  # ❌ TOUJOURS False si OCR échoue
```

**Conséquence :**
- Chaque feuille détectée comme "nouvel élève"
- 44 feuilles → 44 copies (au lieu de ~28)
- Aucune fusion multi-feuilles ne se produit

---

## Gaps Identifiés

### Gap 1 : OCR Manuscrit

**Sévérité :** CRITIQUE
**Impact :** Identification automatique impossible

**Solutions possibles :**

1. **OCR spécialisé manuscrit**
   - Utiliser un modèle entraîné pour handwriting (ex: TrOCR, PaddleOCR)
   - Segmentation par cases avant OCR
   - Effort : ÉLEVÉ

2. **Amélioration Tesseract**
   - Paramétrage PSM adapté (--psm 10 pour caractères isolés)
   - Prétraitement image plus agressif (binarisation, contours cases)
   - Effort : MOYEN

3. **Fallback manuel (MVP)**
   - Accepter que l'OCR échoue
   - Desk d'identification manuel obligatoire
   - Affichage header crops pour aide visuelle
   - Effort : FAIBLE

**Recommandation MVP :** Option 3 + amélioration incrémentale

### Gap 2 : Fusion Multi-Feuilles sans OCR

**Sévérité :** HAUTE
**Impact :** Segmentation incorrecte quand OCR échoue

**Solution proposée :**

Implémenter une heuristique de fallback :
```python
def _is_same_student_fallback(self, header_img1, header_img2):
    """
    Si OCR échoue, comparer visuellement les headers.
    Si l'écriture se ressemble → probablement même élève.
    """
    # Calculer similarité structurelle (SSIM)
    # ou comparaison histogramme
    return similarity > 0.8
```

**Complexité :** MOYENNE
**Bénéfice :** Permet fusion même sans OCR réussi

### Gap 3 : Tests d'Intégration

**Sévérité :** MOYENNE
**Impact :** Pas de preuve que la fusion fonctionne dans un cas nominal

**Action requise :**
- Créer un PDF synthétique avec texte imprimé
- Vérifier que la fusion fonctionne quand OCR réussit
- Tests unitaires sur `_is_same_student()`

---

## État PRD-14

**PRD-14 : Workflow métier complet (scan A3 réel)**

- [x] Import PDF scan A3 recto-verso
- [x] A3 → A4 split avec ordre correct
- [ ] Identification automatique par OCR (ÉCHEC)
- [x] Identification manuelle possible (fallback)
- [x] Segmentation par élève (CODE OK, OCR KO)
- [ ] Workflow correction/consultation (non testé)
- [ ] Export CSV (non testé)

**Verdict PRD-14 :** 🔴 **PARTIEL** (4/7)

---

## Recommandations

### Immédiat (MVP Prod-Ready)

1. **Accepter limitation OCR manuscrit**
   - Documenter clairement que l'OCR ne fonctionne PAS sur CMEN v2 manuscrit
   - Desk d'identification manuel obligatoire
   - Endpoint `/api/booklets/<id>/header/` fonctionnel pour affichage

2. **Test fusion avec OCR simulé**
   - Créer un test unitaire avec `StudentMatch` mocks
   - Vérifier que la fusion fonctionne quand 2 feuilles matchent le même élève
   - **Preuve que le code de fusion est correct**

3. **Documentation utilisateur**
   - Guide : "Comment identifier manuellement les copies"
   - Captures d'écran du desk d'identification

### Court Terme (Post-MVP)

4. **Amélioration OCR**
   - Prétraitement : segmentation cases individuelles
   - Tesseract --psm 10 (single character)
   - Tests A/B avec vraies copies

5. **Heuristique visuelle fallback**
   - Comparaison SSIM entre headers
   - Fusion automatique si similarity > 0.85

### Long Terme

6. **OCR Deep Learning**
   - TrOCR ou modèle custom entraîné sur formulaires CMEN
   - Dataset d'entraînement : 1000+ copies annotées

---

## Preuves Jointes

**Commande exécution :**
```bash
cd /home/alaeddine/viatique__PMF
source .venv/bin/activate
python backend/test_batch_integration.py
```

**Output complet :** `/tmp/batch_test_output.log`

**Headers générés :** `/home/alaeddine/viatique__PMF/backend/media/batch_processing/test_batch_001/headers/`

**Exemple header :** `header_sheet_0001.png`
- Nom : ZARDI (manuscrit)
- Prénom : MOHAMED (manuscrit)
- Date : 21/03/2007 (manuscrit)
- OCR extrait : "TITIIITITTITITII" ❌

---

## Conclusion

Le système de segmentation batch A3 est **structurellement correct** mais **dépendant d'un OCR défaillant**.

**Pour déclarer PRD-19 GREEN :**
1. Accepter la limitation OCR comme **known issue**
2. Prouver que la fusion fonctionne avec un test synthétique
3. Documenter le workflow manuel d'identification
4. Tester le workflow complet end-to-end avec identification manuelle

**Next Steps :** Passer à la tâche #2 (test synthétique multi-feuilles).

---

**Signature :**
Claude Sonnet 4.5
2026-02-02 20:52 UTC+01:00
