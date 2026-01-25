# PROTOCOLES CRITIQUES KORRIGO - TOLÉRANCE ZÉRO

## 1. Mode d'Intervention
- **DIRECT ONLY**: Interdiction formelle d'utiliser des worktrees. Toutes les corrections s'appliquent directement sur le 'File System' actuel.

## 2. Intégrité des Données
- **ACID**: Toute opération sur Copy/Annotation/Score doit être dans une transaction Django.
- **Validation PDF**: Respecter strictement validators.py (MIME, Size, Integrity).

## 3. Standards de Code
- **Backend**: Typage strict (Type hints) et logique métier uniquement dans services/.
- **Frontend**: Vue 3 Composition API et Pinia obligatoire.
