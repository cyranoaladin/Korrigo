"""
Canonical DNB_2026 grading structure.

This module is the single source of truth for the DNB 2026 marking tree used
by backfills, exam setup, and fallback score constraints.
"""

from __future__ import annotations

from copy import deepcopy


DNB_2026_STRUCTURE_TEMPLATE = [
    {
        "id": "1",
        "label": "Partie 1",
        "points": 6.0,
    },
    {
        "id": "partie-2",
        "label": "Partie 2",
        "points": 14.0,
        "children": [
            {
                "id": "ex2",
                "label": "Exercice 2",
                "points": 3.0,
                "children": [
                    {"id": "2f4ab2ea-a9c4-4310-ae09-c3f302570bf7", "label": "Q2.1", "points": 0.5},
                    {"id": "047f1c98-0e22-4c7f-803a-4e52697337dc", "label": "Q2.2", "points": 0.5},
                    {"id": "9597000a-b327-4bc6-8a8b-38a9e0eeebfd", "label": "Q2.3", "points": 0.5},
                    {"id": "7179bdcd-3541-4880-bda3-2d793e5d1102", "label": "Q2.4", "points": 0.5},
                    {"id": "9d7989af-0d2f-4631-ab6a-707c3a088b3b", "label": "Q2.5", "points": 1.0},
                ],
            },
            {
                "id": "ex3",
                "label": "Exercice 3",
                "points": 3.5,
                "children": [
                    {"id": "ee620dea-15cb-4827-8e48-b250a19d0d0b", "label": "Q3.1", "points": 0.75},
                    {"id": "3c9daad4-7972-443b-b945-b57a09ee18eb", "label": "Q3.2", "points": 0.75},
                    {"id": "d5339469-52ea-4b91-9462-afc38e13c181", "label": "Q3.3", "points": 0.75},
                    {"id": "2fbf9076-fab0-496e-a857-d50f77a287e7", "label": "Q3.4", "points": 0.75},
                    {"id": "94f9bf79-f634-4544-950f-2f7789562262", "label": "Q3.5", "points": 0.5},
                ],
            },
            {
                "id": "ex4",
                "label": "Exercice 4",
                "points": 3.0,
                "children": [
                    {"id": "95a8b2a8-3fdd-4545-b1d2-553ec895ea49", "label": "Q4.1", "points": 0.5},
                    {"id": "f8be3f16-28da-4c8c-84c8-a397573a0a14", "label": "Q4.2", "points": 0.5},
                    {"id": "ad4bd6e5-be6c-44e5-b953-1bc4a68a054b", "label": "Q4.3", "points": 1.0},
                    {"id": "9f14ec6e-54d5-495c-b515-21d5bd7b0e12", "label": "Q4.4", "points": 1.0},
                ],
            },
            {
                "id": "ex5",
                "label": "Exercice 5",
                "points": 4.5,
                "children": [
                    {"id": "673fd8b5-6ae1-44d7-9080-531018cf9a31", "label": "Q5.1", "points": 0.5},
                    {"id": "049664c6-3c33-4dca-b1ba-351d55d4db45", "label": "Q5.2", "points": 0.5},
                    {"id": "6ccf34c7-548a-418c-9719-cc7f0809a300", "label": "Q5.3", "points": 0.5},
                    {"id": "0a6af297-a57e-4110-bfb0-a5db0c446c1c", "label": "Q5.4a", "points": 1.0},
                    {"id": "1416c68e-e82a-41a2-87cd-be6fd43c7dc7", "label": "Q5.4b", "points": 1.0},
                    {"id": "dd36d3fe-5abc-4479-846c-b2e91b1eddea", "label": "Q5.4c", "points": 0.5},
                    {"id": "4e12035e-6b07-4c5a-a4c7-49ad32bc0ed8", "label": "Q5.4d", "points": 0.5},
                ],
            },
        ],
    },
]


def build_dnb_2026_grading_structure():
    """Return a fresh DNB_2026 grading structure tree."""
    return deepcopy(DNB_2026_STRUCTURE_TEMPLATE)


def build_dnb_2026_q_max():
    """Return the per-question max score mapping for DNB_2026."""
    q_max = {}
    for top in DNB_2026_STRUCTURE_TEMPLATE:
        children = top.get("children") or []
        if not children:
            q_max[top["id"]] = float(top["points"])
            continue
        for exercise in children:
            for leaf in exercise.get("children") or []:
                q_max[leaf["id"]] = float(leaf["points"])
    return q_max
