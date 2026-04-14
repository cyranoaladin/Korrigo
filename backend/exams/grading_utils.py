"""
Shared utilities for extracting leaf questions from grading_structure.

Handles both ID formats:
- Explicit IDs (UUID or custom) from item.id in grading_structure
- Positional IDs ("1.1", "1.2") generated when item.id is absent (legacy BB_J1)

Every component that reads grading_structure should use these functions
to ensure consistent ID generation and label mapping.
"""


def _parse_exercise_number(label):
    """Extract the exercise number from a label like 'Exercice 2' or 'Exercice 12'."""
    import re
    m = re.search(r'(?:Exercice|Ex\.?)\s*(\d+)', label or '', re.IGNORECASE)
    return int(m.group(1)) if m else None


def _get_children(item):
    """Return the children list of a grading_structure node."""
    return (
        item.get('children', [])
        or item.get('questions', [])
        or item.get('items', [])
        or item.get('sub_questions', [])
    )


def _get_label(item):
    """Return the label of a grading_structure node."""
    return (
        item.get('label', '')
        or item.get('title', '')
        or item.get('name', '')
    )


def _get_points(item):
    """Return the points value of a grading_structure node."""
    return (
        item.get('points')
        or item.get('max_score')
        or item.get('maxScore')
        or item.get('max_points')
        or 0
    )


def _strip_exercise_prefix(label):
    """Drop the 'Exercice N — ' prefix for display configs."""
    if not label:
        return label
    if ' — ' in label:
        prefix, rest = label.split(' — ', 1)
        if _parse_exercise_number(prefix) is not None:
            return rest
    return label


def _flatten_exercises(grading_structure):
    """
    Flatten grading_structure into a list of exercises,
    handling both flat (2-level) and nested (3-level) structures.

    Returns [(exercise_idx, exercise_label, exercise_node, position_prefix), ...]
    where exercise_node is the dict whose children are the leaf questions.
    For a leaf top-level item (e.g. Partie 1 with no children), it is returned as-is.
    """
    gs = grading_structure or []
    if not isinstance(gs, list):
        return []

    exercises = []
    next_idx = 1

    for top_idx, item in enumerate(gs, 1):
        label = _get_label(item)
        children = _get_children(item)
        top_pos = str(top_idx)

        if not children:
            # Leaf at top-level (e.g. "Partie 1" scored directly)
            exercises.append((next_idx, label, item, top_pos))
            next_idx += 1
            continue

        # Check if children are themselves exercises (have their own children)
        # This detects 3-level nesting: Partie 2 > Exercice 2/3/4/5 > questions
        has_grandchildren = any(_get_children(c) for c in children if isinstance(c, dict))

        if has_grandchildren:
            # Grouping node (e.g. "Partie 2"): flatten children as separate exercises
            for child_idx, child in enumerate(children, 1):
                if not isinstance(child, dict):
                    continue
                child_label = _get_label(child)
                child_pos = f'{top_pos}.{child_idx}'
                ex_num = _parse_exercise_number(child_label)
                idx = ex_num if ex_num is not None else next_idx
                exercises.append((idx, child_label, child, child_pos))
                if ex_num is not None:
                    next_idx = max(next_idx, idx + 1)
                else:
                    next_idx += 1
        else:
            # Normal exercise with direct question children
            ex_num = _parse_exercise_number(label)
            idx = ex_num if ex_num is not None else next_idx
            exercises.append((idx, label, item, top_pos))
            if ex_num is not None:
                next_idx = max(next_idx, idx + 1)
            else:
                next_idx += 1

    return exercises


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
    exercises = _flatten_exercises(gs)

    for ex_idx, ex_label, ex_node, position_prefix in exercises:
        children = _get_children(ex_node)
        if not children:
            # Top-level leaf (e.g. Partie 1 scored as a block)
            item_id = str(ex_node.get('id', '')) if ex_node.get('id') else ''
            pos = position_prefix
            q_id = item_id or pos
            label = _get_label(ex_node)
            result.append({
                'id': q_id,
                'positional_id': pos,
                'label': label or q_id,
                'short_label': label or q_id,
                'points': float(_get_points(ex_node)) if _get_points(ex_node) else 0.0,
                'exercise_idx': ex_idx,
            })
        else:
            # Walk leaf questions under this exercise
            _walk_leaves(
                children,
                ex_idx,
                parent_labels=[ex_label] if ex_label else [],
                position_prefix=position_prefix,
                result=result,
            )

    return result


def _walk_leaves(items, exercise_idx, parent_labels, position_prefix, result):
    """Recursively collect leaf questions under an exercise."""
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        item_id = str(item.get('id', '')) if item.get('id') else ''
        label = _get_label(item)
        points = _get_points(item)
        pos = f'{position_prefix}.{idx + 1}'
        children = _get_children(item)

        if children:
            next_parent_labels = parent_labels + ([label] if label else [])
            _walk_leaves(children, exercise_idx, next_parent_labels, pos, result)
        else:
            q_id = item_id or pos
            short_label = label or q_id
            display = ' — '.join([*parent_labels, short_label]) if parent_labels else short_label
            result.append({
                'id': q_id,
                'positional_id': pos,
                'label': display,
                'short_label': short_label,
                'points': float(points) if points else 0.0,
                'exercise_idx': exercise_idx,
            })


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

    Handles 3-level nesting (e.g. Partie 2 > Exercice 2/3/4/5 > questions)
    by flattening into separate exercises.
    """
    exercises = _flatten_exercises(grading_structure)
    config = {}

    for ex_idx, ex_label, ex_node, _position_prefix in exercises:
        raw_name = ex_label or f'Exercice {ex_idx}'
        name = _strip_exercise_prefix(raw_name)

        # Points: use points_backup (original sum) or explicit points
        max_score = (
            ex_node.get('points_backup')
            or _get_points(ex_node)
        )

        # If no direct points, sum from children leaves
        if not max_score:
            leaves = extract_leaf_questions([ex_node])
            max_score = sum(l['points'] for l in leaves)

        config[ex_idx] = {'name': name, 'max': float(max_score) if max_score else 0.0}
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
