import os
import base64
import logging
from io import BytesIO
from PIL import Image
from django.conf import settings
from students.models import Student

logger = logging.getLogger(__name__)


class OCRService:
    """
    Service OCR pour la lecture des en-têtes de copies.
    Utilise GPT-4o-mini Vision (meilleur pour l'écriture manuscrite)
    avec fallback sur pytesseract si OpenAI n'est pas configuré.
    """

    @staticmethod
    def _get_openai_client():
        """
        Returns an OpenAI client if API key is configured, None otherwise.
        """
        api_key = os.environ.get('OPENAI_API_KEY', '').strip()
        if not api_key or api_key.startswith('__CHANGE'):
            return None
        try:
            from openai import OpenAI
            return OpenAI(api_key=api_key)
        except Exception as e:
            logger.warning(f"OpenAI client init failed: {e}")
            return None

    @staticmethod
    def extract_header_from_booklet(booklet):
        """
        Extrait l'image de l'en-tête d'un booklet pour OCR.
        Retourne le chemin du fichier image (str) ou le FieldFile.
        """
        if booklet.header_image:
            return booklet.header_image

        # Crop top 25% of first page
        if booklet.pages_images:
            first_page = booklet.pages_images[0]
            full_path = os.path.join(settings.MEDIA_ROOT, first_page)
            if not os.path.exists(full_path):
                full_path = first_page

            if os.path.exists(full_path):
                try:
                    with Image.open(full_path) as img:
                        w, h = img.size
                        crop_box = (0, 0, w, int(h * 0.25))
                        header_crop = img.crop(crop_box)
                        buffer = BytesIO()
                        header_crop.save(buffer, format='JPEG', quality=90)
                        buffer.seek(0)
                        return buffer
                except Exception as e:
                    logger.error(f"Header extraction failed: {e}")

        return None

    @staticmethod
    def _image_to_base64(image_source):
        """
        Convert image source (path, BytesIO, FieldFile) to base64 JPEG string.
        """
        try:
            if isinstance(image_source, BytesIO):
                image_source.seek(0)
                return base64.b64encode(image_source.read()).decode('utf-8')

            if hasattr(image_source, 'path'):
                # Django FieldFile
                with open(image_source.path, 'rb') as f:
                    return base64.b64encode(f.read()).decode('utf-8')

            if isinstance(image_source, str) and os.path.exists(image_source):
                with open(image_source, 'rb') as f:
                    return base64.b64encode(f.read()).decode('utf-8')

            # Try opening as file-like
            if hasattr(image_source, 'read'):
                image_source.seek(0)
                return base64.b64encode(image_source.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Image to base64 failed: {e}")
        return None

    @staticmethod
    def perform_ocr_on_header(header_image_source):
        """
        Effectue l'OCR sur une image d'en-tête.
        Utilise GPT-4o-mini Vision si disponible, sinon pytesseract.
        """
        client = OCRService._get_openai_client()

        if client:
            return OCRService._ocr_with_openai(client, header_image_source)

        return OCRService._ocr_with_tesseract(header_image_source)

    @staticmethod
    def _ocr_with_openai(client, image_source):
        """
        OCR via GPT-4o-mini Vision - excellent pour l'écriture manuscrite française.
        """
        try:
            img_b64 = OCRService._image_to_base64(image_source)
            if not img_b64:
                return OCRService._ocr_with_tesseract(image_source)

            model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Tu es un assistant OCR spécialisé dans la lecture d'en-têtes "
                            "de copies d'examen. Extrais UNIQUEMENT le nom et prénom de "
                            "l'étudiant visible sur l'image. Réponds UNIQUEMENT avec le "
                            "nom et prénom, rien d'autre. Si tu ne peux pas lire, réponds "
                            "exactement: ILLISIBLE"
                        )
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{img_b64}",
                                    "detail": "high"
                                }
                            },
                            {
                                "type": "text",
                                "text": "Lis le nom et prénom de l'étudiant sur cette en-tête de copie d'examen."
                            }
                        ]
                    }
                ],
                max_tokens=100,
                temperature=0.0
            )

            text = response.choices[0].message.content.strip()

            if text == "ILLISIBLE":
                return {
                    'text': '',
                    'confidence': 0.0,
                    'error': 'Texte illisible (GPT-4o-mini)'
                }

            return {
                'text': text,
                'confidence': 0.95,
                'method': 'gpt-4o-mini-vision'
            }

        except Exception as e:
            logger.error(f"OpenAI OCR failed: {e}", exc_info=True)
            return OCRService._ocr_with_tesseract(image_source)

    @staticmethod
    def _ocr_with_tesseract(image_source):
        """
        Fallback OCR via pytesseract (Tesseract).
        """
        try:
            import pytesseract

            if isinstance(image_source, BytesIO):
                image_source.seek(0)

            with Image.open(image_source) as image:
                if image.mode != 'L':
                    image = image.convert('L')

                custom_config = r'--oem 3 --psm 6 -l fra+eng'
                text = pytesseract.image_to_string(image, config=custom_config)

                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0

                return {
                    'text': text.strip(),
                    'confidence': avg_confidence / 100.0,
                    'method': 'tesseract'
                }
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}", exc_info=True)
            return {
                'text': '',
                'confidence': 0.0,
                'error': 'OCR processing failed'
            }

    @staticmethod
    def find_matching_students(ocr_text):
        """
        Trouve les élèves correspondant au texte OCR.
        """
        from django.db.models import Q

        if not ocr_text:
            return []

        words = ocr_text.upper().split()

        q_objects = Q()
        for word in words:
            if len(word) > 2:
                q_objects |= Q(last_name__icontains=word) | Q(first_name__icontains=word)

        if q_objects:
            matches = Student.objects.filter(q_objects).distinct()[:10]
            return list(matches)

        return []