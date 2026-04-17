"""Fallback déterministe : génère une appréciation sans LLM.

La table est construite pour couvrir l'ensemble des croisements
niveau global × régularité avec des formulations sobres et variées.
"""

import random
from typing import List

from config import Config


# Table de fallback : (niveau_global, regularite) -> liste de formulations
FALLBACK_TABLE = {
    ("très fragile", "homogène"): [
        "Les bases restent à consolider sur l'ensemble du programme.",
        "Un travail de fond est nécessaire pour reconstruire les acquis.",
    ],
    ("très fragile", "irrégulier"): [
        "Des acquis isolés existent, mais l'ensemble reste très fragile.",
        "Quelques points sont saisis, mais la maîtrise globale est insuffisante.",
    ],
    ("très fragile", "très irrégulier"): [
        "Les résultats sont très contrastés et la base reste à sécuriser.",
        "Des réponses pertinentes côtoient des lacunes importantes.",
    ],
    ("fragile", "homogène"): [
        "Les acquis sont présents mais encore fragiles dans l'ensemble.",
        "Une base existe, mais elle demande à être renforcée partout.",
    ],
    ("fragile", "irrégulier"): [
        "Des compétences sont acquises, mais la maîtrise reste inégale.",
        "Progrès réels sur certains points, mais des fragilités persistent.",
    ],
    ("fragile", "très irrégulier"): [
        "Maîtrise très inégale : des points solides côtoient des difficultés nettes.",
        "Des réussites locales ne masquent pas des lacunes importantes ailleurs.",
    ],
    ("correct mais insuffisamment maîtrisé", "homogène"): [
        "Ensemble convenable mais la maîtrise mérite encore d'être affinée.",
        "Des acquis sérieux, sans encore la régularité souhaitable.",
    ],
    ("correct mais insuffisamment maîtrisé", "irrégulier"): [
        "Une base correcte, avec des maîtrises encore inégales selon les domaines.",
        "Des acquis sont là, mais la fiabilité varie d'un point à l'autre.",
    ],
    ("correct mais insuffisamment maîtrisé", "très irrégulier"): [
        "Des résultats corrects côtoient des fragilités significatives.",
        "La base existe, mais les écarts de réussite restent importants.",
    ],
    ("satisfaisant", "homogène"): [
        "Ensemble satisfaisant et assez régulier dans l'ensemble.",
        "Une bonne maîtrise globale, assez homogène.",
    ],
    ("satisfaisant", "irrégulier"): [
        "Ensemble satisfaisant, malgré une maîtrise encore irrégulière.",
        "De bons acquis, avec quelques points à consolider.",
    ],
    ("satisfaisant", "très irrégulier"): [
        "Un niveau satisfaisant dans l'ensemble, malgré des écarts notables.",
        "Des compétences solides côtoient encore quelques fragilités marquées.",
    ],
    ("solide", "homogène"): [
        "Ensemble solide et régulier, avec une bonne maîtrise d'ensemble.",
        "Des acquis solides et bien répartis sur tout le programme.",
    ],
    ("solide", "irrégulier"): [
        "Ensemble solide, même si quelques points méritent encore d'être affinés.",
        "Une bonne maîtrise globale, avec de légères variations selon les sujets.",
    ],
    ("solide", "très irrégulier"): [
        "Un bon niveau général, malgré des maîtrises très inégales.",
        "Des résultats solides dans l'ensemble, avec quelques baisses de régime.",
    ],
    ("très bonne maîtrise", "homogène"): [
        "Très bonne maîtrise globale, régulière et fiable.",
        "Ensemble très solide, avec une grande régularité dans les résultats.",
    ],
    ("très bonne maîtrise", "irrégulier"): [
        "Très bonne maîtrise générale, malgré quelques petites variations.",
        "Un excellent niveau global, avec quelques points à peaufiner.",
    ],
    ("très bonne maîtrise", "très irrégulier"): [
        "Un excellent niveau global, malgré des résultats très contrastés.",
        "Très bons acquis, même si la régularité n'est pas encore totale.",
    ],
}


def generate(level_label: str, regularity_profile: str, cfg: Config = Config()) -> str:
    """Retourne une appréciation de fallback déterministe."""
    key = (level_label, regularity_profile)
    candidates: List[str] = FALLBACK_TABLE.get(key, ["Niveau globalement en phase avec les attendus du programme."])
    return random.choice(candidates)
