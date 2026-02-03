# Guide de Test Manuel - PRD-19 OCR Robustification

**Date:** 2026-02-03
**Statut:** ✅ Système opérationnel avec toutes les bibliothèques OCR

---

## État du Système

### ✅ Tous les composants opérationnels

- **Backend:** http://localhost:8088/api/ (healthy)
- **Frontend:** http://localhost:8088/ (build production)
- **Database:** PostgreSQL (connectée)
- **Redis:** Disponible pour Celery
- **Nginx:** Port 8088

### ✅ Bibliothèques OCR installées

```
✓ EasyOCR 1.7.2
✓ PaddleOCR 3.4.0
✓ Tesseract (système)
✓ Multi-layer OCR engine initialisé
```

### ✅ Tests passés

- 24/24 tests OCR engine ✅
- 5/5 tests batch processor ✅
- Structure validation ✅
- Integration tests ✅

---

## Accès au Système

### URLs Principales

- **Application:** http://localhost:8088/
- **Django Admin:** http://localhost:8088/admin/
- **API Backend:** http://localhost:8088/api/
- **Health Check:** http://localhost:8088/api/health/

### Identifiants de Test

#### Admin
```
URL: http://localhost:8088/admin/login
Username: admin
Password: (votre mot de passe admin)
```

#### Teacher/Enseignant
```
URL: http://localhost:8088/ (puis se connecter)
Username: (votre compte enseignant)
Password: (votre mot de passe)
```

---

## Scénarios de Test PRD-19

### 🎯 Scénario 1: Upload Batch A3 avec CSV

**Objectif:** Tester l'OCR multi-layer sur un lot de copies A3

#### Étapes:

1. **Se connecter en tant qu'admin/teacher**
   - Aller sur http://localhost:8088/admin/login
   - Se connecter avec vos identifiants

2. **Uploader un examen batch**
   - Aller sur: http://localhost:8088/admin-dashboard (ou équivalent)
   - Créer un nouvel examen avec mode batch activé
   - Upload PDF: `CSV/eval_loi_binom_log.pdf`
   - Upload CSV: `CSV/G3_EDS_MATHS.csv`
   - Cocher "Mode batch"
   - Soumettre

3. **Vérifier le traitement**
   - Le système devrait segmenter automatiquement les pages
   - OCR multi-layer s'exécute sur chaque en-tête
   - Copies créées avec top-5 candidats

#### Résultats attendus:

- ✅ PDF segmenté en copies individuelles (multi-sheet fusion)
- ✅ OCR détecte les noms d'étudiants sur les en-têtes
- ✅ Mode AUTO pour confiance >70% (identification automatique)
- ✅ Mode SEMI_AUTO pour 40-70% (top-k candidats générés)
- ✅ Mode MANUAL pour <40% (identification manuelle requise)

---

### 🎯 Scénario 2: Interface d'Identification Semi-Automatique

**Objectif:** Tester l'interface de sélection des candidats OCR

#### Étapes:

1. **Accéder au bureau d'identification**
   - URL: http://localhost:8088/identification-desk
   - Se connecter si nécessaire

2. **Observer l'interface avec candidats OCR**
   - Section "Candidats OCR Multi-Moteur" s'affiche
   - Cartes de candidats avec :
     - Badge de rang (1-5) avec couleurs (or, argent, bronze)
     - Nom, email, date de naissance de l'étudiant
     - Barre de confiance colorée (vert >70%, jaune 50-70%, orange <50%)
     - Indicateur de vote (X moteurs en accord)
     - Détails OCR expandables

3. **Tester la sélection d'un candidat**
   - Cliquer sur "Sélectionner cet étudiant" sur le premier candidat
   - Vérifier que la copie est identifiée
   - La copie suivante s'affiche automatiquement

4. **Tester le mode manuel override**
   - Cliquer sur "Aucun de ces candidats ? Recherche manuelle"
   - L'interface bascule en mode recherche manuelle
   - Taper un nom d'étudiant
   - Sélectionner et valider

5. **Tester les détails OCR**
   - Cliquer sur "Voir détails OCR" (expandable)
   - Vérifier les sources OCR :
     - Nom du moteur (tesseract, easyocr, paddleocr)
     - Variante de prétraitement (0-3)
     - Texte extrait
     - Score de confiance

#### Résultats attendus:

- ✅ UI affiche les candidats avec métriques visuelles
- ✅ Sélection d'un candidat fonctionne (API POST)
- ✅ Navigation automatique vers copie suivante
- ✅ Mode manuel override fonctionnel
- ✅ Détails OCR affichent les sources des 3 moteurs

---

### 🎯 Scénario 3: API Endpoints OCR

**Objectif:** Tester les nouveaux endpoints API

#### Endpoint 1: Récupérer les candidats OCR

```bash
# Obtenir l'ID d'une copie non identifiée
curl http://localhost:8088/api/identification/desk/ \
    -H "Cookie: sessionid=YOUR_SESSION_ID" | jq '.[] | .id'

# Récupérer les candidats OCR pour cette copie
curl http://localhost:8088/api/identification/copies/<COPY_UUID>/ocr-candidates/ \
    -H "Cookie: sessionid=YOUR_SESSION_ID" | jq '.'
```

**Réponse attendue:**
```json
{
  "copy_id": "uuid",
  "anonymous_id": "COPY-001",
  "ocr_mode": "SEMI_AUTO",
  "total_engines": 3,
  "candidates": [
    {
      "rank": 1,
      "student": {
        "id": 1,
        "first_name": "Jean",
        "last_name": "Dupont",
        "email": "jean.dupont@example.com",
        "date_of_birth": "15/03/2008"
      },
      "confidence": 0.65,
      "vote_count": 2,
      "vote_agreement": 0.67,
      "ocr_sources": [
        {
          "engine": "tesseract",
          "variant": 0,
          "text": "DUPONT JEAN",
          "score": 0.7
        }
      ]
    }
  ]
}
```

#### Endpoint 2: Sélectionner un candidat

```bash
# Sélectionner le candidat rang 1
curl -X POST http://localhost:8088/api/identification/copies/<COPY_UUID>/select-candidate/ \
    -H "Cookie: sessionid=YOUR_SESSION_ID" \
    -H "Content-Type: application/json" \
    -d '{"rank": 1}' | jq '.'
```

**Réponse attendue:**
```json
{
  "success": true,
  "copy_id": "uuid",
  "student": {
    "id": 1,
    "first_name": "Jean",
    "last_name": "Dupont",
    "email": "jean.dupont@example.com"
  },
  "status": "READY"
}
```

---

### 🎯 Scénario 4: Vérification Base de Données

**Objectif:** Vérifier que les données OCR sont correctement stockées

#### Via Django Admin:

1. Aller sur http://localhost:8088/admin/
2. Navigation: Identification > OCR Results
3. Vérifier les champs pour un résultat:
   - `top_candidates` (JSON) - contient 1-5 candidats
   - `ocr_mode` - AUTO, SEMI_AUTO, ou MANUAL
   - `selected_candidate_rank` - 1-5 si sélectionné
   - `confidence` - score de confiance (0-1)

#### Via API Django Shell:

```bash
docker compose -f infra/docker/docker-compose.local-prod.yml exec backend \
    python manage.py shell
```

```python
from identification.models import OCRResult
from exams.models import Copy

# Récupérer les résultats OCR
ocr_results = OCRResult.objects.all()
print(f"Total OCR results: {ocr_results.count()}")

# Examiner un résultat
ocr = OCRResult.objects.first()
if ocr:
    print(f"OCR Mode: {ocr.ocr_mode}")
    print(f"Confidence: {ocr.confidence}")
    print(f"Top candidates: {len(ocr.top_candidates)}")
    print(f"Selected rank: {ocr.selected_candidate_rank}")

# Vérifier les copies avec OCR
copies_with_ocr = Copy.objects.filter(ocr_result__isnull=False)
print(f"Copies with OCR: {copies_with_ocr.count()}")
```

---

### 🎯 Scénario 5: Tests de Performance

**Objectif:** Mesurer les temps de traitement OCR

#### Test 1: OCR sur une seule page

```bash
docker compose -f infra/docker/docker-compose.local-prod.yml exec backend python << 'PYEOF'
import time
import numpy as np
from processing.services.ocr_engine import MultiLayerOCR

# Créer une image test (blanc avec texte simulé)
test_image = np.ones((800, 600), dtype=np.uint8) * 255

ocr = MultiLayerOCR()

# Test Tesseract seul
start = time.time()
result_tesseract = ocr._ocr_tesseract(test_image)
time_tesseract = time.time() - start

print(f"Tesseract seul: {time_tesseract:.2f}s")
print(f"Temps estimé multi-layer (3 moteurs): ~{time_tesseract * 3:.2f}s")
PYEOF
```

#### Test 2: Batch processing complet

- Uploader un petit batch (5-10 pages)
- Mesurer le temps total de traitement
- Objectif: <10s par page (incluant rotation, segmentation, OCR, matching)

---

### 🎯 Scénario 6: Tests de Robustesse

**Objectif:** Vérifier que le système gère les cas limites

#### Test 1: Image avec peu de texte

- Uploader une copie avec en-tête vide/illisible
- Vérifier: Mode MANUAL activé, pas de crash

#### Test 2: Noms similaires dans CSV

- CSV avec "DUPONT Jean" et "DUPONT Jeanne"
- Vérifier: Les deux apparaissent dans top-k candidats
- Scores de confiance différents

#### Test 3: Image rotée

- Copie scannée avec rotation (5-10 degrés)
- Vérifier: Prétraitement deskew corrige l'angle
- OCR fonctionne correctement

#### Test 4: Bibliothèque OCR manquante (simulation)

```bash
# Temporairement renommer EasyOCR pour simuler absence
docker compose -f infra/docker/docker-compose.local-prod.yml exec backend \
    mv /usr/local/lib/python3.9/site-packages/easyocr \
       /usr/local/lib/python3.9/site-packages/easyocr.bak

# Tester que le système fonctionne toujours (fallback Tesseract + PaddleOCR)
docker compose -f infra/docker/docker-compose.local-prod.yml exec backend python -c "
from processing.services.ocr_engine import MultiLayerOCR
try:
    ocr = MultiLayerOCR()
    print('✅ Fallback fonctionne')
except Exception as e:
    print(f'✗ Erreur: {e}')
"

# Restaurer EasyOCR
docker compose -f infra/docker/docker-compose.local-prod.yml exec backend \
    mv /usr/local/lib/python3.9/site-packages/easyocr.bak \
       /usr/local/lib/python3.9/site-packages/easyocr
```

---

## Checklist de Validation

### Backend

- [ ] Toutes les bibliothèques OCR importent correctement
- [ ] Multi-layer OCR engine s'initialise sans erreur
- [ ] BatchA3Processor utilise le multi-layer OCR
- [ ] API endpoint `/ocr-candidates/` renvoie les données
- [ ] API endpoint `/select-candidate/` met à jour la copie
- [ ] Database migration appliquée (OCRResult avec nouveaux champs)
- [ ] Logs montrent l'utilisation des 3 moteurs OCR

### Frontend

- [ ] Page `/identification-desk` charge sans erreur
- [ ] Candidats OCR s'affichent avec cartes visuelles
- [ ] Badges de rang avec bonnes couleurs (or/argent/bronze)
- [ ] Barres de confiance colorées correctement
- [ ] Détails OCR expandables fonctionnent
- [ ] Bouton "Sélectionner" envoie API request
- [ ] Navigation automatique vers copie suivante
- [ ] Mode manuel override fonctionne
- [ ] Recherche manuelle affiche résultats

### Workflow Complet

- [ ] Upload batch A3 avec CSV
- [ ] Segmentation multi-sheet correcte
- [ ] OCR s'exécute sur chaque en-tête
- [ ] Top-k candidats générés (1-5 par copie)
- [ ] Mode AUTO: copies identifiées automatiquement (>70%)
- [ ] Mode SEMI_AUTO: candidats présentés à l'enseignant (40-70%)
- [ ] Mode MANUAL: recherche manuelle requise (<40%)
- [ ] Sélection d'un candidat met à jour la copie
- [ ] Audit trail enregistré (selected_candidate_rank)
- [ ] Status copie passe à READY après identification

### Performance

- [ ] OCR par page: <10s (acceptable)
- [ ] Pas de timeouts sur upload batch
- [ ] Mémoire backend stable (<500MB)
- [ ] Frontend responsive, pas de lag UI

### Robustesse

- [ ] Pas de crash si bibliothèque OCR manquante (fallback)
- [ ] Gestion correcte des images illisibles (mode MANUAL)
- [ ] Pas d'erreur si CSV vide ou invalide
- [ ] Pas de régression sur workflows existants

---

## Commandes Utiles

### Redémarrer les services

```bash
docker compose -f infra/docker/docker-compose.local-prod.yml restart backend
docker compose -f infra/docker/docker-compose.local-prod.yml restart nginx
```

### Voir les logs backend

```bash
docker compose -f infra/docker/docker-compose.local-prod.yml logs -f backend | grep -i ocr
```

### Rebuild frontend

```bash
npm run build --prefix /home/alaeddine/viatique__PMF/frontend
docker compose -f infra/docker/docker-compose.local-prod.yml restart nginx
```

### Accéder au shell backend

```bash
docker compose -f infra/docker/docker-compose.local-prod.yml exec backend bash
```

### Relancer les tests

```bash
bash /home/alaeddine/viatique__PMF/.antigravity/test-ocr-robustification.sh
```

---

## Problèmes Connus et Solutions

### Problème: "No module named 'easyocr'"

**Solution:**
```bash
docker compose -f infra/docker/docker-compose.local-prod.yml exec backend \
    pip install --no-cache-dir easyocr
```

### Problème: Frontend 404 sur assets

**Solution:**
```bash
npm run build --prefix /home/alaeddine/viatique__PMF/frontend
docker compose -f infra/docker/docker-compose.local-prod.yml restart nginx
```

### Problème: Database migration non appliquée

**Solution:**
```bash
docker compose -f infra/docker/docker-compose.local-prod.yml exec backend \
    python manage.py migrate identification
```

### Problème: Session expired / 401 Unauthorized

**Solution:** Se reconnecter via http://localhost:8088/admin/login

---

## Support et Documentation

### Documentation Technique

- **Plan d'implémentation:** `.antigravity/kind-wibbling-island.md`
- **Documentation backend:** `.antigravity/PRD-19-COMPLETE-SUMMARY.md`
- **Documentation frontend:** `.antigravity/PRD-19-frontend-implementation.md`
- **Preuve d'implémentation:** `.antigravity/PRD-19-PROOF-OF-IMPLEMENTATION.md`

### Tests Automatisés

- **Test suite:** `.antigravity/test-ocr-robustification.sh`
- **Tests unitaires backend:** `backend/processing/tests/test_ocr_engine.py`
- **Tests E2E frontend:** `frontend/tests/e2e/identification_ocr_flow.spec.ts`

---

## Prochaines Étapes (Post-Validation)

1. **Optimisation Performance:**
   - Paralléliser les appels OCR (Tesseract + EasyOCR + PaddleOCR en concurrent)
   - Cache preprocessing variants
   - Early termination si 2/3 moteurs en accord

2. **Amélioration UX:**
   - Raccourcis clavier (touches 1-5 pour sélectionner candidats)
   - Photos étudiants dans les cartes
   - Historique d'identification avec corrections

3. **Monitoring:**
   - Dashboard performance moteurs OCR
   - Métriques d'accuracy par moteur
   - Alertes si taux MANUAL trop élevé

4. **Fine-tuning:**
   - Ajuster seuils de confiance (0.4, 0.7) selon feedback terrain
   - Entraîner modèles OCR sur formulaires CMEN v2
   - Optimiser poids consensus voting (actuellement 60% Jaccard + 40% date)

---

**Bon test ! 🚀**

En cas de problème, vérifier d'abord les logs:
```bash
docker compose -f infra/docker/docker-compose.local-prod.yml logs -f backend
```
