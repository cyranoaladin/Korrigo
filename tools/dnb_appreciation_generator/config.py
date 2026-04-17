"""Configuration centralisée pour le générateur d'appréciations DNB."""

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Config:
    """Configuration immuable du workflow."""

    # --- LLM ---
    ollama_endpoint: str = "http://localhost:11434/api/generate"
    model: str = "qwen2.5:7b"
    temperature: float = 0.2
    top_p: float = 0.9
    max_tokens: int = 60
    timeout_seconds: int = 120

    # --- Retry ---
    max_llm_retries: int = 2

    # --- Validation ---
    min_words: int = 8
    max_words: int = 22

    # --- Mots interdits ---
    forbidden_words: List[str] = (
        "copie",
        "devoir",
        "devoir blanc",
        "élève",
        "travail",
        "exercice",
        "question",
        "partie",
        "qcm",
        "fonctions",
        "géométrie",
        "statistiques",
        "calcul littéral",
        "équations",
        "thalès",
        "pythagore",
        "automatismes",
    )

    # --- Formulations creuses interdites ---
    vague_phrases: List[str] = (
        "poursuivez vos efforts",
        "il faut continuer ainsi",
        "des efforts sont à fournir",
        "travail sérieux",
        "peut mieux faire",
        "ensemble correct dans l'ensemble",
    )

    # --- Seuils de niveau global ---
    # (borne_sup_exclue, label)
    level_thresholds: List[tuple] = (
        (5.75, "très fragile"),
        (8.75, "fragile"),
        (11.75, "correct mais insuffisamment maîtrisé"),
        (14.75, "satisfaisant"),
        (17.74, "solide"),
        (20.0, "très bonne maîtrise"),
    )

    # --- Seuils de régularité ---
    # basés sur l'écart-type et l'écart max-min des 5 blocs normalisés
    regularity_std_low: float = 0.12
    regularity_std_high: float = 0.30
    regularity_range_low: float = 0.25
    regularity_range_high: float = 0.55


DEFAULT_CONFIG = Config()
