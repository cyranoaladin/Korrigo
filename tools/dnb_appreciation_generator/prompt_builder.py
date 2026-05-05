"""Construction des prompts pour Kimi K2.6 : Rétroaction corrective Korrigo."""

from typing import Any, Dict
from config import Config

SYSTEM_PROMPT = """Tu es un Professeur Agrégé de Mathématiques expert en évaluation.
Ta mission : rédiger une rétroaction corrective unique et synthétique pour une copie d'examen.

RÈGLES CRITIQUES (L'infraction à une règle invalide l'analyse) :
1. UNE SEULE PHRASE. Aucun retour à la ligne, pas de listes, pas de segmentation par points-virgules.
2. LONGUEUR : Entre 15 et 40 mots maximum.
3. INTERDICTION : Ne jamais mentionner de scores chiffrés ou de pourcentages.
4. INTERDICTION : Ne pas utiliser les mots : copie, travail, élève, résultat, note, efforts, mathématiques, exercice, question.
5. STYLE : Académique, technique et factuel. Bannis les encouragements vagues ("Continuez", "Peut mieux faire").
6. LOGIQUE : Tu dois lier une lacune identifiée dans les scores à une observation faite dans les annotations.
7. CONTENU : Identifie le levier de progression principal (ex: la rigueur de rédaction, la maîtrise des algorithmes, la précision géométrique).
8. RÉPONSE : Produis uniquement la phrase finale, sans guillemets ni introduction."""


def build_user_prompt(diag: Dict[str, Any], cfg: Config) -> str:
    """
    Construit le prompt utilisateur en fournissant le diagnostic sémantique complet.
    L'IA reçoit les forces/faiblesses calculées et les annotations textuelles.
    """
    strengths = ", ".join(diag["strengths"]) if diag["strengths"] else "Aucun bloc dominant"
    weaknesses = ", ".join(diag["weaknesses"]) if diag["weaknesses"] else "Aucune lacune majeure"
    
    # Intégration des données textuelles saisies par le correcteur
    annotations = diag.get("annotations", "Aucune annotation technique")
    remarks = diag.get("remarks", "Aucune remarque globale")

    return (
        f"--- DONNÉES DE PERFORMANCE ---\n"
        f"Points forts (maîtrise > {int(cfg.success_threshold*100)}%) : {strengths}\n"
        f"Points faibles (maîtrise < {int(cfg.failure_threshold*100)}%) : {weaknesses}\n\n"
        f"--- OBSERVATIONS DU CORRECTEUR ---\n"
        f"Annotations sur les copies : {annotations}\n"
        f"Remarques globales : {remarks}\n\n"
        f"INSTRUCTION : Rédige une synthèse de diagnostic qui explique l'origine des erreurs à partir des observations."
    )


def build_correction_prompt(raw_text: str, rejection_reason: str) -> str:
    """
    Prompt utilisé en cas d'échec de validation (trop long, mots interdits, etc.).
    """
    return (
        f"L'analyse précédente a été rejetée par l'auditeur pédagogique.\n"
        f"RAISON DU REJET : {rejection_reason}\n"
        f"TEXTE INCORRECT : \"{raw_text}\"\n\n"
        f"CORRECTION : Réécris une phrase unique (15-40 mots), sobre, sans chiffres et sans les mots interdits, "
        f"en te concentrant sur le diagnostic méthodologique."
    )
