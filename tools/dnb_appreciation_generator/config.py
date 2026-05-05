"""Configuration pour le moteur de rétroaction corrective Korrigo (Kimi K2.6)."""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class Config:
    """Configuration immuable pour l'analyse sémantique des copies d'examen."""

    # --- INFRASTRUCTURE CLOUD (PUISSANCE DÉPORTÉE) ---
    kimi_gateway_url: str = "https://kimi-gateway.cyranoaladin.workers.dev/v1/chat/completions"
    model: str = "@cf/moonshotai/kimi-k2.6"
    temperature: float = 0.25  # Température basse pour garantir la rigueur mathématique
    max_tokens: int = 250      # Plus large pour permettre le raisonnement interne (Thinking)
    timeout_seconds: int = 60

    # --- CADRAGE DE LA RÉTROACTION ---
    min_words: int = 15
    max_words: int = 40  # Plus d'espace pour justifier la perte de points sur un exercice précis

    # --- DICTIONNAIRE PÉDAGOGIQUE ---
    # On bannit les termes vides pour forcer l'analyse des annotations saisies.
    forbidden_words: List[str] = (
        "travail", "élève", "résultat", "note", "copie", "ensemble",
        "poursuivez", "efforts", "encouragements", "moyen", "passable"
    )

    # --- LOGIQUE D'ANALYSE PAR EXERCICE (SEUILS) ---
    # Détermine comment Kimi doit interpréter le ratio (points obtenus / barème)
    # pour identifier les exercices "clés" à commenter.
    success_threshold: float = 0.8  # >80% : Exercice considéré comme acquis
    failure_threshold: float = 0.4  # <40% : Exercice identifié comme lacune majeure

    # --- RÉFÉRENTIEL DE QUALITÉ DE COPIE ---
    # Labels pour qualifier la rigueur à partir des annotations/remarques du correcteur
    quality_labels: List[Tuple[float, str]] = (
        (7.0,  "Fragilité conceptuelle majeure"),
        (10.0, "Acquis partiels - Manque de rigueur dans la rédaction"),
        (13.0, "Méthodologie correcte - Erreurs de calcul ponctuelles"),
        (16.0, "Analyse solide et structurée"),
        (20.0, "Excellence technique et clarté démonstrative"),
    )

    # --- PROMPT SYSTÈME (LE "CERVEAU" AGRÉGÉ) ---
    # Ce prompt définit le comportement de Kimi en mode "Thinking"
    system_instruction: str = (
        "Tu es un Professeur Agrégé de Mathématiques expert en évaluation. "
        "Ta mission est de rédiger une synthèse de correction pour une copie d'examen. "
        "SOURCES DE DONNÉES : \n"
        "1. Le barème vs les points attribués par exercice.\n"
        "2. Les annotations portées directement sur la copie.\n"
        "3. Tes remarques globales.\n\n"
        "DIRECTIVES DE RÉDACTION :\n"
        "- Ne sois jamais vague. Cite un exercice spécifique si le score y est bas.\n"
        "- Fais le lien entre une annotation (ex: 'raisonnement incomplet') et la perte de points.\n"
        "- Utilise un ton académique, factuel et constructif.\n"
        "- Ne répète pas la note, l'élève la connaît. Analyse le 'Pourquoi'."
    )


DEFAULT_CONFIG = Config()
