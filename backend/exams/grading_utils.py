"""
Shared utilities for extracting leaf questions from grading_structure.

Handles both ID formats:
- Explicit IDs (UUID or custom) from item.id in grading_structure
- Positional IDs ("1.1", "1.2") generated when item.id is absent (legacy BB_J1)

Every component that reads grading_structure should use these functions
to ensure consistent ID generation and label mapping.
"""


def extract_leaf_questions(grading_structure):
    """
    Extract all leaf (scorable) questions from a grading_structure tree.

    Returns a list of dicts:
        [
            {
                'id': str,              # primary question ID (explicit or positional)
                'positional_id': str,   # always-positional ID ("1.1", "1.2")
                'label': str,           # human-readable label
                'points': float,        # max points for this question
                'exercise_idx': int     # 1-based exercise index
            },
            ...
        ]
    """
    gs = grading_structure or []
    if not isinstance(gs, list):
        return []

    result = []

    def _walk(items, parent_label='', position_prefix='', exercise_idx=0):
        for idx, item in enumerate(items):
            item_id = str(item.get('id', '')) if item.get('id') else ''
            label = (
                item.get('label', '')
                or item.get('title', '')
                or item.get('name', '')
            )
            points = (
                item.get('points')
                or item.get('max_score')
                or item.get('maxScore')
                or item.get('max_points')
                or 0
            )

            # Positional ID for this level (always generated)
            pos = f'{position_prefix}.{idx + 1}' if position_prefix else str(idx + 1)

            children = (
                item.get('children', [])
                or item.get('questions', [])
                or item.get('items', [])
                or item.get('sub_questions', [])
            )

            if children:
                _walk(
                    children,
                    parent_label=label or parent_label,
                    # For recursion: use item.id if present (matches CorrectorDesk),
                    # else positional. But always pass positional for pos tracking.
                    position_prefix=pos,
                    exercise_idx=exercise_idx or (idx + 1),
                )
            else:
                # Leaf: primary ID = explicit id or positional
                q_id = item_id or pos
                # Build human-readable label
                if label:
                    display = f'{parent_label} \u2014 {label}' if parent_label else label
                else:
                    display = q_id
                result.append({
                    'id': q_id,
                    'positional_id': pos,
                    'label': display,
                    'points': float(points) if points else 0.0,
                    'exercise_idx': exercise_idx or (idx + 1),
                })

    _walk(gs)
    return result


def build_question_labels(grading_structure):
    """
    Build a mapping {question_id: human_readable_label} from grading_structure.
    Returns labels indexed by BOTH explicit ID and positional ID.
    """
    leaves = extract_leaf_questions(grading_structure)
    labels = {}
    for q in leaves:
        labels[q['id']] = q['label']
        # Also index by positional ID if different (for legacy score formats)
        if q['positional_id'] != q['id']:
            labels[q['positional_id']] = q['label']
    return labels


def build_q_max(grading_structure):
    """
    Build a mapping {question_id: max_points} from grading_structure.
    Returns max points indexed by BOTH explicit ID and positional ID.
    """
    leaves = extract_leaf_questions(grading_structure)
    q_max = {}
    for q in leaves:
        q_max[q['id']] = q['points']
        if q['positional_id'] != q['id']:
            q_max[q['positional_id']] = q['points']
    return q_max


def build_exercise_config(grading_structure):
    """
    Build exercise_config for the student ResultView.
    Returns {exercise_index: {'name': str, 'max': float}}.
    """
    gs = grading_structure or []
    if not isinstance(gs, list):
        return {}

    config = {}
    for i, ex in enumerate(gs, 1):
        label = (
            ex.get('label', '')
            or ex.get('title', '')
            or ex.get('name', '')
            or f'Exercice {i}'
        )
        # Strip "Exercice N — " prefix to get just the topic name
        name = label
        if ' \u2014 ' in label:
            name = label.split(' \u2014 ', 1)[1]
        elif label.startswith('Exercice'):
            name = label

        # Try all possible point field names
        max_score = (
            ex.get('points')
            or ex.get('max_score')
            or ex.get('maxScore')
            or ex.get('max_points')
            or 0
        )

        # If no direct points, sum from children leaves
        if not max_score:
            leaves = extract_leaf_questions([ex])
            max_score = sum(l['points'] for l in leaves)

        config[i] = {'name': name, 'max': float(max_score) if max_score else 0.0}
    return config


def map_scores_to_exercises(scores_data, grading_structure):
    """
    Map scores_data keys to exercise numbers using grading_structure.
    Returns {exercise_idx: [(question_id, score, label, max_points), ...]}

    Handles both positional IDs (BB_J1, old BB_J2 scores) and UUID IDs (DNB).
    """
    leaves = extract_leaf_questions(grading_structure)

    # Build lookup by both explicit ID and positional ID
    id_to_leaf = {}
    for q in leaves:
        id_to_leaf[q['id']] = q
        if q['positional_id'] != q['id']:
            id_to_leaf[q['positional_id']] = q

    exercises = {}
    for q_id, score in scores_data.items():
        leaf = id_to_leaf.get(q_id)
        if leaf:
            ex_idx = leaf['exercise_idx']
        else:
            # Fallback: try to parse positional format
            parts = q_id.split('.')
            try:
                ex_idx = int(parts[0])
            except (ValueError, IndexError):
                ex_idx = 0  # Unknown exercise

        if ex_idx not in exercises:
            exercises[ex_idx] = []

        label = leaf['label'] if leaf else q_id
        max_pts = leaf['points'] if leaf else 0
        exercises[ex_idx].append((q_id, score, label, max_pts))

    return exercises
