"""Construction des prompts system / user pour la LLM."""

from config import Config


SYSTEM_PROMPT = """Tu es un correcteur de mathématiques expérimenté.
Ta mission : rédiger une appréciation finale pour un devoir de DNB en classe de troisième.

RÈGLES ABSOLUES (toute infraction invalide la réponse) :
1. UNE SEULE PHRASE. Pas de liste, pas de puces, pas de point-virgule structurant.
2. Concision stricte : entre 8 et 18 mots, jamais plus de 22 mots.
3. AUCUN score chiffré dans la phrase.
4. AUCUN détail par exercice, par notion ou par question.
5. AUCUN des mots suivants : copie, devoir, devoir blanc, élève, travail, exercice, question, partie, QCM, fonctions, géométrie, statistiques, calcul littéral, équations, Thalès, Pythagore, automatismes.
6. AUCUNE formulation creuse : "poursuivez vos efforts", "il faut continuer ainsi", "des efforts sont à fournir", "travail sérieux", "peut mieux faire", "ensemble correct dans l'ensemble".
7. Ton : sobre, précis, humain, bienveillant, professionnel.
8. Contenu : refléter le niveau global et la régularité. Éventuellement un point fort général et/ou un axe général, mais sans entrer dans le détail.
9. Ne pas employer : "cette copie", "cet élève", "travail rendu", "la copie montre que".
10. Répondre uniquement par la phrase finale. Pas d'introduction, pas de conclusion, pas de guillemets."""


def _format_float(value: float) -> str:
    """Affiche un nombre avec virgule française, sans décimale inutile."""
    s = f"{value:.2f}".replace(".", ",")
    return s.rstrip("0").replace(",", ".") if "," in s else s


def build_user_prompt(
    total: float,
    partie1: float,
    e2_total: float,
    e3_total: float,
    e4_total: float,
    e5_total: float,
    level_label: str,
    regularity_profile: str,
    cfg: Config = Config(),
) -> str:
    """Construit le prompt utilisateur à partir des métriques calculées."""
    return (
        f"Niveau global : {level_label} ({_format_float(total)}/20).\n"
        f"Profil de régularité : {regularity_profile}.\n"
        f"Sous-totaux par bloc : Partie 1 = {_format_float(partie1)}/6, "
        f"Exercice 2 = {_format_float(e2_total)}/3, "
        f"Exercice 3 = {_format_float(e3_total)}/3,5, "
        f"Exercice 4 = {_format_float(e4_total)}/3, "
        f"Exercice 5 = {_format_float(e5_total)}/4,5.\n\n"
        "Rédige l'appréciation finale."
    )


def build_correction_prompt(raw_text: str, rejection_reason: str) -> str:
    """Prompt correctif utilisé lors du retry."""
    return (
        f"L'appréciation précédente a été rejetée pour la raison suivante : {rejection_reason}.\n"
        f"Texte rejeté : \"{raw_text}\"\n\n"
        "Corrige-la pour respecter strictement les règles : une seule phrase, 8-18 mots, "
        "globale, sans détail par exercice, sans chiffre, sans mot interdit. "
        "Réponds uniquement par la phrase corrigée."
    )
