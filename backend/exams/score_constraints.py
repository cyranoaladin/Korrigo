"""
Per-question maximum score constraints, keyed by exam name then question ID.

These values are used for server-side overflow validation in CopyScoresView
(grading app) and exposed to the student portal (exams app).

Source of truth: must stay aligned with the official grading barème.
When the barème is loaded into exam.grading_structure, prefer deriving
limits from there; this dict acts as an explicit override/fallback for
named exam sessions.
"""

Q_MAX_BY_EXAM: dict[str, dict[str, float]] = {
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
