import cv2
import numpy as np
from django.utils.translation import gettext_lazy as _
from .vision import HeaderDetector

class A3Splitter:
    """
    Service responsable du découpage des scans A3 en pages individuelles A4
    et de la reconstruction de l'ordre logique des pages (Recto/Verso).
    """

    def __init__(self):
        self.detector = HeaderDetector()

    def process_scan(self, image_path: str):
        """
        Découpe une image A3 en deux A4 et détermine si c'est un Recto ou un Verso.
        
        Args:
            image_path (str): Chemin vers le scan A3.
            
        Returns:
            dict: {
                'type': 'RECTO' | 'VERSO' | 'UNKNOWN',
                'left_page': numpy.ndarray,
                'right_page': numpy.ndarray,
                'has_header': bool
            }
        """
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(_("Impossible de lire l'image : ") + image_path)

        height, width, _ = image.shape
        
        # Patch C: Functional Split with tempfile
        import tempfile
        import os

        # Découpage vertical strict à 50%
        mid_x = width // 2
        left_crop = image[:, :mid_x]
        right_crop = image[:, mid_x:]

        # Create localized temp file for detection
        # We need check right crop for Header
        fd, temp_path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd) # Close handle so cv2 can write
        
        try:
             # Logic is delegated to determine_scan_type_and_order
             # which writes to temp_path and calls detector
             result = self.determine_scan_type_and_order(left_crop, right_crop, temp_path)
             
             # Enrich result with crops if needed by caller (optional but good for debug)
             # But the contract says 'type' + 'pages'
             result['has_header'] = (result['type'] == 'RECTO')
             return result
             
        except Exception as e:
             # Fallback
             return {
                 'type': 'UNKNOWN',
                 'left': left_crop,
                 'right': right_crop,
                 'error': str(e)
             }
        finally:
             if os.path.exists(temp_path):
                 os.unlink(temp_path)

    def determine_scan_type_and_order(self, left_img, right_img, temp_right_path: str) -> dict:
        """
        Détermine si le scan est Recto ou Verso en cherchant un en-tête à droite.
        
        Args:
            left_img: Image de gauche (Page 4 ou Page 2)
            right_img: Image de droite (Page 1 ou Page 3)
            temp_right_path: Chemin temporaire de l'image de droite pour le détecteur
        
        Returns:
            dict: {
                'type': 'RECTO' or 'VERSO',
                'pages': {
                   'p1': img, 'p4': img 
                } OR {
                   'p2': img, 'p3': img
                }
            }
        """
        # Sauvegarder temp_right pour la détection
        cv2.imwrite(temp_right_path, right_img)
        
        is_recto = self.detector.detect_header(temp_right_path)
        
        if is_recto:
            # HEADER FOUND ON RIGHT -> RECTO
            # Structure A3 Recto: [Page 4 | Page 1 (Header)]
            return {
                'type': 'RECTO',
                'pages': {
                    'p1': right_img, # La page avec l'en-tête (Page 1)
                    'p4': left_img   # La dernière page (Page 4)
                }
            }
        else:
            # NO HEADER -> VERSO (Assomption contextuelle)
            # Structure A3 Verso: [Page 2 | Page 3]
            return {
                'type': 'VERSO',
                'pages': {
                    'p2': left_img, # Page 2 est à gauche
                    'p3': right_img # Page 3 est à droite
                }
            }

    def reconstruct_booklet(self, recto_data, verso_data):
        """
        Reconstruit l'ordre final: [P1, P2, P3, P4]
        """
        return [
            recto_data['pages']['p1'], # Page 1
            verso_data['pages']['p2'], # Page 2
            verso_data['pages']['p3'], # Page 3
            recto_data['pages']['p4']  # Page 4
        ]
