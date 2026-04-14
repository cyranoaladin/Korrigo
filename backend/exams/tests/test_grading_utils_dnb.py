import pytest


@pytest.mark.unit
def test_dnb_nested_grading_structure_is_flattened_by_exercise():
    from exams.grading_utils import build_exercise_config, extract_leaf_questions

    grading_structure = [
        {
            "label": "Partie 1",
            "points": 6,
        },
        {
            "label": "Partie 2",
            "children": [
                {
                    "label": "Exercice 2 — Automatismes",
                    "points_backup": 4,
                    "children": [
                        {"id": "q2a", "label": "2a", "points": 2},
                        {"id": "q2b", "label": "2b", "points": 2},
                    ],
                },
                {
                    "label": "Exercice 3 — Géométrie",
                    "children": [
                        {"id": "q3a", "label": "3a", "points": 3},
                        {"id": "q3b", "label": "3b", "points": 5},
                    ],
                },
            ],
        },
    ]

    leaves = extract_leaf_questions(grading_structure)
    config = build_exercise_config(grading_structure)

    assert [leaf["exercise_idx"] for leaf in leaves] == [1, 2, 2, 3, 3]
    assert leaves[0]["label"] == "Partie 1"
    assert leaves[1]["label"] == "Exercice 2 — Automatismes — 2a"
    assert leaves[1]["short_label"] == "2a"
    assert leaves[4]["label"] == "Exercice 3 — Géométrie — 3b"
    assert leaves[4]["short_label"] == "3b"

    assert config[1] == {"name": "Partie 1", "max": 6.0}
    assert config[2] == {"name": "Automatismes", "max": 4.0}
    assert config[3] == {"name": "Géométrie", "max": 8.0}
