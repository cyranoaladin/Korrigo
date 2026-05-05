import cv2
import numpy as np
import base64
import httpx
import json
import logging
from django.utils.translation import gettext_lazy as _
from django.conf import settings

logger = logging.getLogger(__name__)

class HeaderDetector:
    """
    Service hybride : OpenCV (Calcul local léger) + Kimi K2.6 (Calcul Cloud fort).
    Optimisé pour la détection visuelle sans QR Code.
    """

    def __init__(self):
        self.config = getattr(settings, "AI_CONFIG", {})

    def detect_header(self, image_path: str) -> bool:
        """
        Détection géométrique via OpenCV (Local).
        Vérifie la présence d'un contour rectangulaire dans le haut de la page.
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(_("Impossible de lire l'image : ") + image_path)

            height, width, _ = image.shape
            top_crop = image[0:int(height * 0.2), :]
            
            gray = cv2.cvtColor(top_crop, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edged = cv2.Canny(blurred, 50, 150)
            
            contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
                if len(approx) == 4:
                    area = cv2.contourArea(contour)
                    if area > (width * height * 0.01):
                        return True
            return False
        except Exception as e:
            logger.error(f"Erreur detect_header: {e}")
            return False

    def extract_header_crop(self, image_path: str) -> bytes:
        """
        Découpe la zone d'en-tête pour l'envoyer au moteur d'intelligence.
        """
        try:
            image = cv2.imread(image_path)
            if image is None: return b""
            
            height, _, _ = image.shape
            crop_h = int(height * 0.23) # Zone spécifique Lycée PMF
            crop_img = image[0:crop_h, :]
            
            success, encoded_img = cv2.imencode('.jpg', crop_img)
            return encoded_img.tobytes() if success else b""
        except Exception as e:
            logger.error(f"Erreur extract_header_crop: {e}")
            return b""

    async def identify_student_with_kimi(self, crop_bytes: bytes) -> dict:
        """
        Appel à Kimi K2.6 via le Worker Cloudflare.
        Utilise le mode 'Thinking' pour une précision identique à Opus 4.7.
        """
        if not crop_bytes:
            return {"is_valid": False, "student_name": None}

        base64_image = base64.b64encode(crop_bytes).decode('utf-8')
        
        payload = {
            "model": self.config.get("MODEL"),
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", 
                            "text": "Analyse cet en-tête de copie Korrigo. "
                                    "Extrais le NOM et le PRÉNOM de l'élève. "
                                    "Réponds uniquement en JSON: {'is_valid': bool, 'student_name': 'NOM PRENOM'}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            "extra_body": {"thinking": True} # Force la réflexion maximale
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.config.get("BASE_URL"),
                    json=payload,
                    timeout=30.0,
                    headers={"Authorization": f"Bearer {self.config.get('API_KEY')}"}
                )
                res_data = response.json()
                content = res_data['choices'][0]['message']['content']
                
                # Nettoyage Markdown si nécessaire
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                
                return json.loads(content)
            except Exception as e:
                logger.error(f"Kimi API Error: {e}")
                return {"is_valid": False, "student_name": None, "error": str(e)}
