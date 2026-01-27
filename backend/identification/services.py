# Import cv2 only when needed to avoid dependency issues
import numpy as np
from PIL import Image
import pytesseract
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from .models import OCRResult
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
                first_page_path = booklet.pages_images[0]
                header_bytes = detector.extract_header_crop(first_page_path)
                
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
            # Charger l'image (P1-REL-006: Use context manager to prevent resource leak)
            with Image.open(header_image_file) as image:
                # Convertir en grayscale pour meilleur OCR
                if image.mode != 'L':  # L = grayscale
                    image = image.convert('L')

                # Effectuer OCR
                custom_config = r'--oem 3 --psm 6 -l fra+eng'
                text = pytesseract.image_to_string(image, config=custom_config)

                # Calculer la confiance moyenne
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0

                return {
                    'text': text.strip(),
                    'confidence': avg_confidence / 100.0  # Normaliser à [0,1]
                }
        except Exception as e:
            # Gérer les erreurs proprement
            return {
                'text': '',
                'confidence': 0.0,
                'error': str(e)
            }

    @staticmethod
    def find_matching_students(ocr_text):
        """
        Trouve les élèves correspondant au texte OCR
        """
        # Extraire nom/prénom potentiel du texte OCR
        words = ocr_text.upper().split()
        
        # Chercher des correspondances dans la base élèves
        # P1-REL-009: Use single query with OR conditions instead of N queries
        from django.db.models import Q
        
        suggestions = []
        if not words:
            return suggestions
        
        # Build Q objects for all valid words
        q_objects = Q()
        for word in words:
            if len(word) > 2:  # Mot suffisamment long pour être un nom
                q_objects |= Q(last_name__icontains=word) | Q(first_name__icontains=word)
        
        # Single query instead of N queries
        if q_objects:
            matches = Student.objects.filter(q_objects).distinct()[:20]  # Get top 20 matches
            suggestions = list(matches)
        
        # Retirer les doublons
        seen_ids = set()
        unique_suggestions = []
        for student in suggestions:
            if student.id not in seen_ids:
                seen_ids.add(student.id)
                unique_suggestions.append(student)
        
        return unique_suggestions[:10]  # Max 10 suggestions