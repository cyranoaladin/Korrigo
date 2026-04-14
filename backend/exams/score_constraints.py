"""
FALLBACK STATIQUE pour les anciens examens sans grading_structure complète.

⚠️  Les NOUVEAUX examens DOIVENT avoir un grading_structure complet dans la DB
    avec des maxScore par question. Ce fallback ne couvre que BB_J1, BB_J2 et DNB_2026
    créés avant le système d'IDs.

Le code primaire utilise exam.grading_structure via build_q_max() dans grading_utils.py.
Ce dictionnaire n'intervient que si grading_structure ne fournit pas de q_max.

Per-question maximum score constraints, keyed by exam name then question ID.
Used for server-side overflow validation in CopyScoresView (grading app)
and exposed to the student portal (exams app).
"""

from exams.dnb_2026_structure import build_dnb_2026_q_max

Q_MAX_BY_EXAM: dict[str, dict[str, float]] = {
    # ── DNB BLANC MATHS 2026 ──────────────────────────────────────────────────
    # Examen unique (pas de sujet A/B). Clé = exam.name = 'DNB_2026'.
    # Barème officiel : Partie 1 = 6 pts, Partie 2 = 14 pts, total = 20 pts.
    # Clés = IDs de grading_structure (UUID pour Partie 2, "1" pour Partie 1).
    'DNB_2026': build_dnb_2026_q_max(),

    # ── BAC BLANC MATHS 2026 ─────────────────────────────────────────────────
    'BB_J1': {
        '1.1': 1, '1.2': 1, '1.3': 1, '1.4': 1, '1.5': 1,
        '2.1': 0.25, '2.2': 0.50, '2.3': 0.50, '2.4': 0.75, '2.5': 0.25,
        '2.6': 0.75, '2.7': 0.50, '2.8': 0.25, '2.9': 0.75, '2.10': 0.50,
        '3.1': 0.75, '3.2': 0.50, '3.3': 0.50, '3.4': 1.00, '3.5': 0.50, '3.6': 0.75,
        '4.1': 0.25, '4.2': 0.25, '4.3': 0.25, '4.4': 0.75, '4.5': 0.50,
        '4.6': 0.75, '4.7': 0.50, '4.8': 1.00, '4.9': 0.25, '4.10': 0.25,
        '4.11': 1.00, '4.12': 0.25,
    },
    'BB_J2': {
        '1': 5.0,
        '2.1.1': 0.25, '2.1.2': 0.50, '2.1.3': 1.00, '2.1.4': 0.50, '2.1.5': 0.25,
        '2.2.1': 0.50, '2.2.2': 0.50, '2.2.3': 0.50, '2.2.4': 0.50, '2.2.5': 0.50,
        '3.1': 0.50, '3.2': 0.50, '3.3': 1.00, '3.4': 0.75, '3.5': 0.50,
        '3.6': 0.75, '3.7': 1.00,
        '4.1.1': 0.50, '4.1.2': 0.25,
        '4.2.1': 0.75, '4.2.2': 0.50, '4.2.3': 0.50, '4.2.4': 1.00,
        '4.2.5': 0.50, '4.2.6': 0.50, '4.2.7': 0.50,
    },
}
