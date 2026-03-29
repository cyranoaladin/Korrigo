"""
Configuration DÉFINITIVE des masques d'anonymisation.
Mesures vérifiées visuellement sur les copies réelles.

Référence :
    En-tête copie : 23% (67mm sur A4 297mm) — pages 1, 5, 9… (4N-3)
    En-tête annexe : 18% (53mm sur A4 297mm) — dernière page uniquement
    Marge sécurité copie : 25% (73mm) — recommandé pour OCR
    Marge sécurité annexe : 20% (59mm) — recommandé pour OCR

NE PAS MODIFIER CES VALEURS sans vérification visuelle.
"""

PAGE_HEIGHT_PTS = 842  # A4 en points PDF


def get_mask_config(nb_pages: int, pages_per_booklet: int = 4) -> dict:
    """
    Retourne la configuration des masques d'anonymisation par page.

    Args:
        nb_pages: nombre total de pages du document
        pages_per_booklet: nombre de pages par copie (défaut 4)

    Returns:
        dict[int, dict]: {page_number: mask_info} (1-indexed)
    """
    masks = {}

    # Pages en-tête copie : 4N-3 pour N=1,2,3…
    n = 1
    while True:
        page_idx = pages_per_booklet * n - (pages_per_booklet - 1)  # 1-indexed
        if page_idx > nb_pages:
            break
        masks[page_idx] = {
            'position': 'top',
            'height_pct': 23.0,
            'height_pts': int(PAGE_HEIGHT_PTS * 0.23),  # = 194
            'height_mm': 67,
            'type': 'en_tete_copie',
        }
        n += 1

    # Dernière page = annexe (si pas déjà marquée comme en-tête copie)
    if nb_pages not in masks:
        masks[nb_pages] = {
            'position': 'top',
            'height_pct': 18.0,
            'height_pts': int(PAGE_HEIGHT_PTS * 0.18),  # = 152
            'height_mm': 53,
            'type': 'en_tete_annexe',
        }

    return masks
