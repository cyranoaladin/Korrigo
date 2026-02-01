import cv2
import numpy as np
from django.utils.translation import gettext_lazy as _
from .vision import HeaderDetector

class A3Splitter:
    """
    Service responsable du découpage des scans A3 en pages individuelles A4
    et de la reconstruction de l'ordre logique des pages (Recto/Verso).
    
    ZF-AUD-04 FIX: Added deskew pre-processing and margin tolerance.
    """

    def __init__(self, split_tolerance=0.02, deskew_enabled=True):
        """
        Args:
            split_tolerance (float): Tolerance for split point (default 2% of width)
            deskew_enabled (bool): Enable automatic deskew correction
        """
        self.detector = HeaderDetector()
        self.split_tolerance = split_tolerance
        self.deskew_enabled = deskew_enabled

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

        # ZF-AUD-04 FIX: Apply deskew correction if enabled
        if self.deskew_enabled:
            image = self._deskew_image(image)

        height, width, channels = image.shape
        
        # Patch C: Functional Split with tempfile
        import tempfile
        import os

        # ZF-AUD-04 FIX: Smart split with edge detection for better accuracy
        mid_x = self._find_split_point(image, width)
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

    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """
        ZF-AUD-04 FIX: Correct skew/rotation in scanned images.
        Uses Hough line detection to find dominant angle and rotate.
        
        Args:
            image: Input BGR image
            
        Returns:
            Deskewed image (or original if angle < 0.5 degrees)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                                     minLineLength=100, maxLineGap=10)
            
            if lines is None or len(lines) == 0:
                return image
            
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if x2 - x1 != 0:
                    angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                    if abs(angle) < 45:
                        angles.append(angle)
            
            if not angles:
                return image
            
            median_angle = np.median(angles)
            
            if abs(median_angle) < 0.5:
                return image
            
            logger.info(f"Deskew: correcting {median_angle:.2f} degrees rotation")
            
            height, width = image.shape[:2]
            center = (width // 2, height // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
            rotated = cv2.warpAffine(image, rotation_matrix, (width, height),
                                      flags=cv2.INTER_LINEAR,
                                      borderMode=cv2.BORDER_REPLICATE)
            return rotated
            
        except Exception as e:
            logger.warning(f"Deskew failed, using original: {e}")
            return image

    def _find_split_point(self, image: np.ndarray, width: int) -> int:
        """
        ZF-AUD-04 FIX: Find optimal split point with tolerance for offset scans.
        Looks for vertical edge/fold line near center.
        
        Args:
            image: Input BGR image
            width: Image width
            
        Returns:
            X coordinate for split (defaults to width//2 if no edge found)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        mid_x = width // 2
        tolerance_px = int(width * self.split_tolerance)
        
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            search_region = gray[:, mid_x - tolerance_px:mid_x + tolerance_px]
            
            sobel_x = cv2.Sobel(search_region, cv2.CV_64F, 1, 0, ksize=3)
            sobel_x = np.abs(sobel_x)
            
            col_sums = np.sum(sobel_x, axis=0)
            
            if len(col_sums) > 0:
                best_offset = np.argmax(col_sums)
                split_x = mid_x - tolerance_px + best_offset
                
                if abs(split_x - mid_x) > tolerance_px // 2:
                    logger.info(f"Split point adjusted: {mid_x} -> {split_x}")
                    return split_x
            
            return mid_x
            
        except Exception as e:
            logger.warning(f"Smart split failed, using center: {e}")
            return mid_x
