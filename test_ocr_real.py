#!/usr/bin/env python3
"""
Test OCR réel avec fixture image
Ce script crée une image de test avec du texte et exécute l'OCR dessus
"""
import os
import sys
import tempfile
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import cv2
import numpy as np

def create_test_image():
    """Crée une image de test avec du texte simulant un en-tête de copie"""
    # Créer une image blanche
    img = Image.new('RGB', (400, 100), color='white')
    draw = ImageDraw.Draw(img)
    
    # Ajouter du texte simulant un en-tête de copie
    text = "Jean DUBOIS - TG2 - Bac Blanc 2026"
    try:
        # Essayer d'utiliser une police par défaut
        font = ImageFont.load_default()
    except:
        font = None
    
    # Dessiner le texte
    draw.text((10, 40), text, fill='black', font=font)
    
    return img

def test_ocr_functionality():
    """Test la fonctionnalité OCR sur une image de test"""
    print("=== TEST OCR RÉEL ===")
    
    # Créer une image de test
    test_img = create_test_image()
    
    # Sauvegarder temporairement
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        test_img.save(tmp.name)
        img_path = tmp.name
    
    try:
        # Lire l'image avec OpenCV
        img_cv = cv2.imread(img_path)
        
        # Convertir en grayscale pour meilleur OCR
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # Améliorer la qualité pour OCR
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
        
        # Effectuer OCR
        custom_config = r'--oem 3 --psm 6 -l fra+eng'
        text = pytesseract.image_to_string(gray, config=custom_config)
        
        # Calculer la confiance moyenne
        data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
        confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        print(f"Texte détecté: '{text.strip()}'")
        print(f"Confiance moyenne: {avg_confidence:.2f}%")
        
        # Vérifier que le texte contient des mots significatifs
        detected_words = text.strip().upper().split()
        expected_words = ["JEAN", "DUBOIS", "TG2", "BAC", "BLANC"]
        
        found_words = [word for word in expected_words if any(word in det_word for det_word in detected_words)]
        
        print(f"Mots attendus trouvés: {found_words}")
        print(f"Taux de détection: {len(found_words)}/{len(expected_words)}")
        
        # Nettoyer
        os.unlink(img_path)
        
        if len(found_words) >= 2:  # Si on trouve au moins 2 mots significatifs
            print("✅ OCR fonctionnel: Texte détecté avec succès")
            return True
        else:
            print("❌ OCR échec: Peu de mots détectés")
            return False
            
    except Exception as e:
        print(f"❌ OCR échec: {str(e)}")
        # Nettoyer même en cas d'erreur
        if os.path.exists(img_path):
            os.unlink(img_path)
        return False

if __name__ == "__main__":
    success = test_ocr_functionality()
    sys.exit(0 if success else 1)