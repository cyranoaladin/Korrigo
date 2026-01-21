import cv2
import numpy as np
from django.utils.translation import gettext_lazy as _

class HeaderDetector:
    """
    Service responsable de la détection des en-têtes de copies via Vision par Ordinateur.
    Respecte la contrainte : "Absence de QR Code, détection visuelle".
    """

    def __init__(self):
        pass

    def detect_header(self, image_path: str) -> bool:
        """
        Détecte si une page contient l'en-tête spécifique du Lycée.
        
        Args:
            image_path (str): Chemin vers le fichier image de la page.
            
        Returns:
            bool: Vrai si l'en-tête est détecté, Faux sinon.
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(_("Impossible de lire l'image : ") + image_path)

            height, width, _ = image.shape
            
            # Logic Placeholder : Détection de contour rectangulaire dans le top 20%
            # On se concentre sur la partie supérieure
            top_crop = image[0:int(height * 0.2), :]
            
            gray = cv2.cvtColor(top_crop, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edged = cv2.Canny(blurred, 50, 150)
            
            contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                # Approximation du contour
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
                
                # Si le contour a 4 points, c'est potentiellement notre en-tête
                if len(approx) == 4:
                    # Vérification de l'aire pour éviter le bruit
                    area = cv2.contourArea(contour)
                    if area > (width * height * 0.01): # Arbitraire 1% de l'aire
                        return True
                        
            return False

        except Exception as e:
            # En production, logger l'erreur
            print(f"{_('Erreur lors de la détection')}: {e}")
            return False

    def extract_header_crop(self, image_path: str) -> bytes:
        """
        Extrait la zone où l'élève inscrit son nom pour l'interface "Agrafeuse".
        
        Args:
            image_path (str): Chemin vers l'image complète.
            
        Returns:
            bytes: Contenu de l'image rognée (format JPEG).
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(_("Image introuvable"))

            height, width, _ = image.shape
            
            # Placeholder: On prend arbitrairement le top 15% centré
            # En réalité, utiliser les coordonnées du contour détecté par detect_header
            crop_h = int(height * 0.15)
            crop_img = image[0:crop_h, :] # Tout le haut pour l'instant
            
            success, encoded_img = cv2.imencode('.jpg', crop_img)
            if not success:
                raise ValueError(_("Échec de l'encodage de l'image"))
                
            return encoded_img.tobytes()

        except Exception as e:
            print(f"{_('Erreur extraction crop')}: {e}")
            return b""
