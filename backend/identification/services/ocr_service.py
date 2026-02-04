# Import cv2 only when needed to avoid dependency issues
import numpy as np
from PIL import Image
import pytesseract
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from identification.models import OCRResult
from students.models import Student


class OCRService:
    """
    Service OCR pour la lecture des en-têtes de copies
    """
    
    @staticmethod
    def extract_header_from_booklet(booklet):
        """
        Extrait l'image de l'en-tête d'un booklet pour OCR
        """
        if not booklet.header_image:
            # Si pas d'image d'en-tête, extraire de la première page
            # Utiliser la logique de vision.py pour extraire la zone d'en-tête
            from processing.services.vision import HeaderDetector
            detector = HeaderDetector()
            
            # Extraire la zone d'en-tête de la première page
            if booklet.pages_images:
                import os
                from django.conf import settings
                first_page_path = booklet.pages_images[0]
                full_path = os.path.join(settings.MEDIA_ROOT, first_page_path)
                header_bytes = detector.extract_header_crop(full_path)
                
                # Convertir en fichier Django
                image_io = BytesIO(header_bytes)
                image_file = InMemoryUploadedFile(
                    image_io, None, f"header_{booklet.id}.jpg", 
                    'image/jpeg', len(header_bytes), None
                )
                
                return image_file
        
        return booklet.header_image

    @staticmethod
    def perform_ocr_on_header(header_image_file):
        """
        Effectue l'OCR sur une image d'en-tête
        """
        try:
            with Image.open(header_image_file) as image:
                if image.mode != 'L':
                    image = image.convert('L')

                custom_config = r'--oem 3 --psm 6 -l fra+eng'
                text = pytesseract.image_to_string(image, config=custom_config)

                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0

                return {
                    'text': text.strip(),
                    'confidence': avg_confidence / 100.0
                }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"OCR failed: {e}", exc_info=True)
            return {
                'text': '',
                'confidence': 0.0,
                'error': 'OCR processing failed'
            }

    @staticmethod
    def find_matching_students(ocr_text):
        """
        Trouve les élèves correspondant au texte OCR.
        Utilise full_name car le modèle Student n'a pas de champs first_name/last_name séparés.
        """
        from django.db.models import Q
        
        words = ocr_text.upper().split()
        
        q_objects = Q()
        for word in words:
            if len(word) > 2:
                # Chercher dans full_name (le modèle Student utilise full_name, pas first_name/last_name)
                q_objects |= Q(full_name__icontains=word)
        
        if q_objects:
            matches = Student.objects.filter(q_objects).distinct()[:10]
            return list(matches)
        
        return []