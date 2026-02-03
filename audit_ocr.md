Après analyse du fichier `backend/processing/services/ocr_engine.py`, voici mes conclusions et ma proposition d'optimisation.

### 1. Diagnostic : Optimisation Manquante
Le système actuel **n'est pas optimisé**. Il utilise une approche "brute-force" qui exécute systématiquement **tous** les moteurs OCR (Tesseract, EasyOCR, PaddleOCR) sur **toutes** les variantes d'image (4 variantes) avant même de regarder si un résultat satisfaisant a été trouvé.

*   **Problème :** Même si Tesseract (très rapide) trouve le bon étudiant avec 100% de confiance sur la première image, le système attend inutilement que EasyOCR et PaddleOCR (coûteux en CPU/Temps) traitent les 4 variantes.
*   **Impact :** Le temps de traitement est dicté par le moteur le plus lent, multiplié par le nombre de variantes.

### 2. Méthode Proposée : Consensus en Cascade (Early Exit)
Je propose une méthode de **"Cascading Consensus"** (Consensus en Cascade) :

1.  **Passe Rapide (Tesseract) :** On lance uniquement Tesseract sur toutes les variantes.
2.  **Vérification :** Si un candidat obtient un score de consensus > **0.85** (configurable), on arrête tout et on renvoie le résultat. C'est le cas pour la majorité des copies propres.
3.  **Passe Robuste (EasyOCR/PaddleOCR) :** Seulement si Tesseract échoue, on lance les moteurs plus lourds (Deep Learning) pour tenter de récupérer l'information.

### 3. Implémentation Proposée
Voici le code refactoré pour `MultiLayerOCR` dans `backend/processing/services/ocr_engine.py`.

Il faut remplacer la méthode `extract_text_with_candidates` et diviser `_run_all_ocr_engines` en une méthode ciblée.

```python
    def extract_text_with_candidates(
        self, header_image: np.ndarray, csv_whitelist: List[dict]
    ) -> OCRResult:
        """
        Extract text using cascading OCR engines (Optimization: Early Exit).
        """
        # Generate preprocessing variants
        variants = self.preprocessor.preprocess_variants(header_image)
        logger.info(f"Generated {len(variants)} preprocessing variants")

        all_candidates = []
        
        # --- STAGE 1: Fast Path (Tesseract) ---
        logger.info("Stage 1: Running Tesseract...")
        tesseract_candidates = self._run_specific_engine('tesseract', variants)
        all_candidates.extend(tesseract_candidates)

        # Check for early exit
        top_matches = self._consensus_vote(all_candidates, csv_whitelist)
        if top_matches and top_matches[0].confidence > 0.85:
            logger.info(f"Early exit after Tesseract (Confidence: {top_matches[0].confidence:.2f})")
            return OCRResult(
                top_candidates=top_matches,
                ocr_mode='AUTO',
                all_ocr_outputs=all_candidates
            )

        # --- STAGE 2: Robust Path (EasyOCR) ---
        # Only load and run heavy models if necessary
        logger.info("Stage 2: Tesseract low confidence. Running EasyOCR...")
        easyocr_candidates = self._run_specific_engine('easyocr', variants)
        all_candidates.extend(easyocr_candidates)

        top_matches = self._consensus_vote(all_candidates, csv_whitelist)
        if top_matches and top_matches[0].confidence > 0.85:
            logger.info(f"Early exit after EasyOCR (Confidence: {top_matches[0].confidence:.2f})")
            return OCRResult(
                top_candidates=top_matches,
                ocr_mode='AUTO', # Still AUTO if we found a strong match
                all_ocr_outputs=all_candidates
            )

        # --- STAGE 3: Fallback (PaddleOCR) ---
        logger.info("Stage 3: Still low confidence. Running PaddleOCR...")
        paddle_candidates = self._run_specific_engine('paddleocr', variants)
        all_candidates.extend(paddle_candidates)

        # Final consensus
        top_matches = self._consensus_vote(all_candidates, csv_whitelist)
        
        # Determine mode based on final result
        if top_matches and top_matches[0].confidence > 0.7:
            ocr_mode = 'AUTO'
        elif top_matches and top_matches[0].confidence > 0.4:
            ocr_mode = 'SEMI_AUTO'
        else:
            ocr_mode = 'MANUAL'

        return OCRResult(
            top_candidates=top_matches,
            ocr_mode=ocr_mode,
            all_ocr_outputs=all_candidates
        )

    def _run_specific_engine(self, engine_name: str, variants: List[np.ndarray]) -> List[OCRCandidate]:
        """Run a specific OCR engine on all variants."""
        candidates = []
        
        for variant_idx, img in enumerate(variants):
            try:
                if engine_name == 'tesseract':
                    text = self._ocr_tesseract(img)
                    confidence = self._estimate_tesseract_confidence(text)
                    candidates.append(OCRCandidate('tesseract', variant_idx, text, confidence))
                
                elif engine_name == 'easyocr':
                    reader = self._get_easyocr()
                    if reader:
                        results = reader.readtext(img, detail=1)
                        text = ' '.join([res[1] for res in results])
                        confidence = sum([res[2] for res in results]) / len(results) if results else 0.0
                        candidates.append(OCRCandidate('easyocr', variant_idx, text, confidence))
                        
                elif engine_name == 'paddleocr':
                    paddle = self._get_paddleocr()
                    if paddle:
                        results = paddle.ocr(img, cls=True)
                        if results and results[0]:
                            text = ' '.join([line[1][0] for line in results[0]])
                            confidence = sum([line[1][1] for line in results[0]]) / len(results[0])
                            candidates.append(OCRCandidate('paddleocr', variant_idx, text, confidence))
                            
            except Exception as e:
                logger.warning(f"{engine_name} failed on variant {variant_idx}: {e}")
                
        return candidates
```

Cette modification devrait réduire drastiquement le temps de traitement moyen par copie (de quelques secondes à quelques centaines de millisecondes pour les cas simples) tout en conservant la robustesse pour les cas difficiles.
