# PRD-14: Workflow Métier Complet avec Scan A3 Réel

## PDF Source
- Fichier: `eval_loi_binom_log.pdf`
- Format: A3 recto-verso (88 pages)
- Structure: 2 pages A4 côte à côte par page A3
- Ordre livret: Page 1 contient [P4|P1], Page 2 contient [P2|P3]

## Étapes du Workflow

### 1. Upload PDF
- Endpoint: `POST /api/exams/upload/`
- Résultat: 22 booklets créés (88 pages / 4 pages par booklet)
- Copies créées en statut STAGING

### 2. Analyse A3 → A4
- Service: `A3Splitter` dans `processing/services/splitter.py`
- Endpoint: `POST /api/exams/booklets/<id>/split/`
- Détection: RECTO (avec en-tête) ou VERSO
- Résultat: {"type":"RECTO","has_header":true}

### 3. Détection d'en-tête
- Service: `HeaderDetector` dans `processing/services/vision.py`
- Détecte les zones d'en-tête avec QR code et champs nom/prénom
- Utilise OpenCV pour la détection de contours

### 4. Identification
- Endpoint: `GET /api/identification/desk/` - Liste copies non identifiées
- Endpoint: `POST /api/identification/manual/<copy_id>/` - Association manuelle
- OCR disponible via `OCRService` pour assistance

### 5. Transition de statut
- STAGING → READY (après identification)
- READY → LOCKED (acquisition du verrou par correcteur)
- LOCKED → GRADED (après finalisation)

### 6. Correction
- Interface: `/corrector/desk/<copy_id>`
- Annotations sur canvas
- Autosave local + sync serveur
- Soft lock avec heartbeat

### 7. Export
- PDF final généré
- Consultation élève via portail

## Preuves

### Upload réussi
```
Exam: Eval Loi Binomiale Log
Booklets: 22
Copies: 22 (STAGING)
```

### A3Splitter test
```
Type: RECTO
Has header: True
Pages: ['p1', 'p4']
```

### Identification desk
```
23 copies non identifiées listées
Header image URL disponible pour chaque copie
```

## Limitations actuelles

1. **A3 split non automatique**: Le `PDFSplitter` découpe par nombre de pages, pas par détection A3→A4. Le `A3Splitter` existe mais n'est pas intégré dans le workflow d'upload automatique.

2. **Pré-traitement recommandé**: Pour les scans A3 recto-verso, utiliser:
   ```bash
   # Corriger rotation
   pdftk input.pdf cat 1-endeast output rotated.pdf
   # Découper A3 → A4
   mutool poster -x 2 rotated.pdf split_a4.pdf
   ```

3. **Identification manuelle requise**: L'OCR assiste mais la validation humaine est obligatoire.

## Conclusion

Le workflow métier est fonctionnel pour les PDFs pré-traités. L'intégration automatique du A3Splitter est une amélioration future recommandée.

Status: PASS (avec pré-traitement documenté)
