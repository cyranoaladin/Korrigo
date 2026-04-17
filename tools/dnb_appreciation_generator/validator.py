"""Validation stricte des appréciations générées."""

import re
from typing import Tuple

from config import Config


def validate(text: str, cfg: Config = Config()) -> Tuple[bool, str]:
    """Vérifie que `text` respecte les contraintes.

    Retourne (is_valid, reason).
    """
    if not text:
        return False, "sortie vide"

    # Nettoyage léger pour la validation
    cleaned = text.strip()

    # Une seule phrase
    sentences = [s for s in re.split(r'[.!?]', cleaned) if s.strip()]
    if len(sentences) != 1:
        return False, f"{len(sentences)} phrases détectées (1 attendue)"

    # Nombre de mots
    words = cleaned.split()
    word_count = len(words)
    if word_count < cfg.min_words:
        return False, f"trop courte ({word_count} mots, min {cfg.min_words})"
    if word_count > cfg.max_words:
        return False, f"trop longue ({word_count} mots, max {cfg.max_words})"

    # Aucun chiffre
    if re.search(r'\d', cleaned):
        return False, "contient des chiffres"

    # Aucune liste / puce / structuration
    if any(char in cleaned for char in ["-", "•", "*", ":", ";", "\n"]):
        return False, "contient des caractères de structuration interdits"

    # Mots interdits
    lowered = cleaned.lower()
    for word in cfg.forbidden_words:
        if word.lower() in lowered:
            return False, f"mot interdit détecté : '{word}'"

    # Formulations creuses
    for phrase in cfg.vague_phrases:
        if phrase.lower() in lowered:
            return False, f"formulation creuse détectée : '{phrase}'"

    return True, ""
