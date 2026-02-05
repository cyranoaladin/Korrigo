"""
CMEN Checkbox Grid Decoder - Décode les grilles de cases à cocher du format CMEN.

Le format CMEN (Concours et Examens Nationaux) utilise des grilles de cases
où chaque colonne représente une position de caractère et chaque ligne une lettre
de l'alphabet (A-Z). Une case cochée indique la lettre à cette position.

Structure typique:
- Grille NOM: 26 lignes (A-Z) x N colonnes (positions)
- Grille PRENOM: similaire
- Grille DATE: format numérique
"""
import cv2
import numpy as np
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Alphabet CMEN (majuscules sans accents + espace)
CMEN_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CMEN_DIGITS = "0123456789"


@dataclass
class CMENField:
    """Champ décodé d'une grille CMEN."""
    value: str
    confidence: float
    grid_type: str  # 'name', 'firstname', 'date'


@dataclass
class CMENResult:
    """Résultat complet du décodage CMEN."""
    last_name: str
    first_name: str
    date_of_birth: str
    confidence: float


class CMENDecoder:
    """
    Décodeur de grilles CMEN pour extraire les noms des cases cochées.
    """

    def __init__(self, debug: bool = False):
        self.debug = debug
        # Paramètres de détection des cases
        self.min_cell_size = 8
        self.max_cell_size = 40
        self.fill_threshold = 0.3  # % de pixels noirs pour considérer une case cochée

    def decode_header(self, header_image: np.ndarray) -> Optional[CMENResult]:
        """
        Décode un en-tête CMEN complet (nom, prénom, date).
        
        Args:
            header_image: Image BGR de l'en-tête
            
        Returns:
            CMENResult avec les champs décodés, ou None si échec
        """
        try:
            # Convertir en niveaux de gris
            if len(header_image.shape) == 3:
                gray = cv2.cvtColor(header_image, cv2.COLOR_BGR2GRAY)
            else:
                gray = header_image.copy()

            # Détecter les zones de grille CMEN
            grids = self._detect_cmen_grids(gray)
            
            if not grids:
                logger.warning("No CMEN grids detected")
                return None

            # Décoder chaque grille
            last_name = ""
            first_name = ""
            date_of_birth = ""
            total_confidence = 0.0
            grid_count = 0

            for grid_type, grid_region in grids:
                decoded = self._decode_grid(grid_region, grid_type)
                if decoded:
                    if grid_type == 'name':
                        last_name = decoded.value
                    elif grid_type == 'firstname':
                        first_name = decoded.value
                    elif grid_type == 'date':
                        date_of_birth = decoded.value
                    total_confidence += decoded.confidence
                    grid_count += 1

            if grid_count == 0:
                return None

            return CMENResult(
                last_name=last_name,
                first_name=first_name,
                date_of_birth=date_of_birth,
                confidence=total_confidence / grid_count
            )

        except Exception as e:
            logger.error(f"CMEN decode failed: {e}")
            return None

    def _detect_cmen_grids(self, gray: np.ndarray) -> List[Tuple[str, np.ndarray]]:
        """
        Détecte les zones de grille CMEN dans l'image.
        
        Returns:
            Liste de (type_grille, region_image)
        """
        grids = []
        h, w = gray.shape

        # Binariser l'image
        _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)

        # Détecter les lignes horizontales (structure de grille)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
        horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)

        # Détecter les lignes verticales
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 30))
        vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)

        # Combiner pour avoir la structure de grille
        grid_structure = cv2.add(horizontal, vertical)

        # Trouver les contours des zones de grille
        contours, _ = cv2.findContours(grid_structure, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Filtrer les grandes zones rectangulaires (grilles CMEN)
        for contour in contours:
            x, y, cw, ch = cv2.boundingRect(contour)
            area = cw * ch
            aspect = cw / ch if ch > 0 else 0

            # Une grille CMEN est généralement large et pas trop haute
            if area > 5000 and aspect > 3 and cw > 200:
                # Extraire la région
                region = gray[y:y+ch, x:x+cw]
                
                # Déterminer le type de grille basé sur la position Y
                if y < h * 0.15:
                    grid_type = 'name'
                elif y < h * 0.25:
                    grid_type = 'firstname'
                else:
                    grid_type = 'date'

                grids.append((grid_type, region))
                logger.debug(f"Detected {grid_type} grid at y={y}, size={cw}x{ch}")

        # Si aucune grille détectée, essayer une approche alternative
        if not grids:
            grids = self._detect_grids_by_density(gray)

        return grids

    def _detect_grids_by_density(self, gray: np.ndarray) -> List[Tuple[str, np.ndarray]]:
        """
        Détection alternative basée sur la densité de pixels.
        """
        grids = []
        h, w = gray.shape

        # Diviser l'image en bandes horizontales
        band_height = h // 5
        
        for i, band_name in enumerate(['name', 'firstname', 'date']):
            y_start = i * band_height
            y_end = (i + 2) * band_height
            if y_end > h:
                y_end = h
            
            band = gray[y_start:y_end, :]
            
            # Vérifier si la bande contient une structure de grille
            _, binary = cv2.threshold(band, 180, 255, cv2.THRESH_BINARY_INV)
            density = np.sum(binary > 0) / binary.size
            
            if density > 0.02:  # Au moins 2% de pixels noirs
                grids.append((band_name, band))

        return grids

    def _decode_grid(self, grid_image: np.ndarray, grid_type: str) -> Optional[CMENField]:
        """
        Décode une grille CMEN individuelle.
        """
        try:
            h, w = grid_image.shape
            
            # Binariser
            _, binary = cv2.threshold(grid_image, 180, 255, cv2.THRESH_BINARY_INV)

            # Détecter les cellules individuelles
            cells = self._detect_cells(binary)
            
            if not cells:
                logger.debug(f"No cells detected in {grid_type} grid")
                return None

            # Organiser les cellules en colonnes
            columns = self._organize_cells_to_columns(cells)
            
            if not columns:
                return None

            # Décoder chaque colonne
            if grid_type == 'date':
                decoded = self._decode_digit_columns(columns, binary)
            else:
                decoded = self._decode_letter_columns(columns, binary)

            if decoded:
                return CMENField(
                    value=decoded,
                    confidence=0.7,  # Confiance par défaut
                    grid_type=grid_type
                )

            return None

        except Exception as e:
            logger.warning(f"Grid decode failed: {e}")
            return None

    def _detect_cells(self, binary: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Détecte les cellules individuelles dans une grille binarisée.
        """
        # Trouver les contours
        contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        cells = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Filtrer par taille (cellules CMEN typiques)
            if self.min_cell_size < w < self.max_cell_size and self.min_cell_size < h < self.max_cell_size:
                aspect = w / h if h > 0 else 0
                if 0.5 < aspect < 2.0:  # Cellules approximativement carrées
                    cells.append((x, y, w, h))

        return cells

    def _organize_cells_to_columns(self, cells: List[Tuple[int, int, int, int]]) -> List[List[Tuple[int, int, int, int]]]:
        """
        Organise les cellules en colonnes basées sur leur position X.
        """
        if not cells:
            return []

        # Trier par X
        cells_sorted = sorted(cells, key=lambda c: c[0])
        
        # Grouper par colonnes (cellules avec X similaire)
        columns = []
        current_column = [cells_sorted[0]]
        tolerance = 15  # pixels

        for cell in cells_sorted[1:]:
            if abs(cell[0] - current_column[0][0]) < tolerance:
                current_column.append(cell)
            else:
                if len(current_column) > 1:  # Au moins 2 cellules par colonne
                    columns.append(sorted(current_column, key=lambda c: c[1]))
                current_column = [cell]

        if len(current_column) > 1:
            columns.append(sorted(current_column, key=lambda c: c[1]))

        return columns

    def _decode_letter_columns(self, columns: List[List[Tuple[int, int, int, int]]], binary: np.ndarray) -> str:
        """
        Décode les colonnes de lettres (A-Z).
        """
        result = []
        
        for column in columns:
            # Trouver la cellule la plus remplie dans la colonne
            max_fill = 0
            best_idx = -1
            
            for idx, (x, y, w, h) in enumerate(column):
                # Extraire la région de la cellule
                cell_region = binary[y:y+h, x:x+w]
                fill_ratio = np.sum(cell_region > 0) / cell_region.size
                
                if fill_ratio > max_fill and fill_ratio > self.fill_threshold:
                    max_fill = fill_ratio
                    best_idx = idx

            if best_idx >= 0 and best_idx < len(CMEN_ALPHABET):
                result.append(CMEN_ALPHABET[best_idx])

        return ''.join(result)

    def _decode_digit_columns(self, columns: List[List[Tuple[int, int, int, int]]], binary: np.ndarray) -> str:
        """
        Décode les colonnes de chiffres (0-9) pour les dates.
        """
        result = []
        
        for column in columns:
            max_fill = 0
            best_idx = -1
            
            for idx, (x, y, w, h) in enumerate(column):
                cell_region = binary[y:y+h, x:x+w]
                fill_ratio = np.sum(cell_region > 0) / cell_region.size
                
                if fill_ratio > max_fill and fill_ratio > self.fill_threshold:
                    max_fill = fill_ratio
                    best_idx = idx

            if best_idx >= 0 and best_idx < len(CMEN_DIGITS):
                result.append(CMEN_DIGITS[best_idx])

        # Formater comme date DD/MM/YYYY
        if len(result) >= 8:
            return f"{result[0]}{result[1]}/{result[2]}{result[3]}/{result[4]}{result[5]}{result[6]}{result[7]}"
        
        return ''.join(result)
