import cv2
import numpy as np
from django.utils.translation import gettext_lazy as _

class HeaderDetector:
    """
    Service responsable de la détection des en-têtes de copies via Vision par Ordinateur.
    Respecte la contrainte : "Absence de QR Code, détection visuelle".
    
    ZF-AUD-04 FIX: Added aspect ratio validation and noise filtering.
    """

    def __init__(self, min_aspect_ratio=2.0, max_aspect_ratio=15.0, min_area_ratio=0.01):
        """
        Args:
            min_aspect_ratio (float): Minimum width/height ratio for header box (default 2.0)
            max_aspect_ratio (float): Maximum width/height ratio for header box (default 15.0)
            min_area_ratio (float): Minimum area as fraction of crop area (default 1%)
        """
        self.min_aspect_ratio = min_aspect_ratio
        self.max_aspect_ratio = max_aspect_ratio
        self.min_area_ratio = min_area_ratio

    def detect_header(self, image_path: str) -> bool:
        """
        Détecte si une page contient l'en-tête spécifique du Lycée.
        
        Args:
            image_path (str): Chemin vers le fichier image de la page.
            
        Returns:
            bool: Vrai si l'en-tête est détecté, Faux sinon.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError(_("Impossible de lire l'image : ") + image_path)

            height, width, channels = image.shape
            
            top_crop = image[0:int(height * 0.2), :]
            crop_height, crop_width = top_crop.shape[:2]
            crop_area = crop_height * crop_width
            
            gray = cv2.cvtColor(top_crop, cv2.COLOR_BGR2GRAY)
            
            # ZF-AUD-04 FIX: Apply adaptive thresholding for noisy scans
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Use adaptive threshold for better noise handling
            thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                            cv2.THRESH_BINARY_INV, 11, 2)
            
            # Morphological operations to reduce noise
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
            
            edged = cv2.Canny(blurred, 50, 150)
            
            contours, hierarchy = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            candidates = []
            
            for contour in contours:
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
                
                if len(approx) == 4:
                    area = cv2.contourArea(contour)
                    
                    # ZF-AUD-04 FIX: Validate area ratio
                    if area < (crop_area * self.min_area_ratio):
                        continue
                    
                    # ZF-AUD-04 FIX: Validate aspect ratio to filter noise
                    x, y, w, h = cv2.boundingRect(contour)
                    if h == 0:
                        continue
                    aspect_ratio = w / h
                    
                    if self.min_aspect_ratio <= aspect_ratio <= self.max_aspect_ratio:
                        candidates.append({
                            'contour': contour,
                            'area': area,
                            'aspect_ratio': aspect_ratio,
                            'bbox': (x, y, w, h)
                        })
            
            if candidates:
                # Return True if we have at least one valid candidate
                best = max(candidates, key=lambda c: c['area'])
                logger.debug(f"Header detected: area={best['area']}, aspect={best['aspect_ratio']:.2f}")
                return True
                        
            return False

        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Header detection error: {e}")
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

            height, width, channels = image.shape
            
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
