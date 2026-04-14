#!/usr/bin/env python3
"""
Fix unmatched copies by using fuzzy matching on CSV names.
Strategy:
1. Build all possible normalized variants from CSV full names
2. For each unmatched copy, try multiple normalization strategies
3. Use last_name + first_name tokens overlap as fallback
"""
import os
import sys
import csv
import re
import unicodedata
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher

sys.path.append(str(Path(__file__).resolve().parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

from exams.models import Exam, Copy
from students.models import Student


CSV_J1 = Path("/tmp/eleves_maths_J1.csv")
CSV_J2 = Path("/tmp/eleves_maths_J2.csv")


def strip_accents(s: str) -> str:
    """Remove all accents from a string."""
    nfkd = unicodedata.normalize('NFKD', s)
    return nfkd.encode('ASCII', 'ignore').decode('ASCII')


def tokenize(name: str) -> set:
    """Split a name into normalized tokens."""
    clean = strip_accents(name).upper()
    # Split on spaces, hyphens, underscores, apostrophes
    tokens = re.split(r'[\s\-_\'"]+', clean)
    return {t for t in tokens if t and len(t) > 1}


def build_csv_index(csv_path: Path) -> list:
    """
    Read CSV and build a list of dicts with multiple matching keys.
    """
    entries = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            full_name = row.get('Élèves', '').strip()
            email = row.get('Adresse E-mail', '').strip()
            dob_str = row.get('Né(e) le', '').strip()

            if not full_name or not email:
                continue

            # Parse name parts
            parts = full_name.split()
            # CSV format: LASTNAME FIRSTNAME (sometimes multi-word)
            # We'll try different splits

            # Normalized full name (no accents, uppercase)
            norm_full = strip_accents(full_name).upper()
            # As underscore-separated
            underscore_full = re.sub(r'[\s]+', '_', norm_full)
            # Tokens
            tokens = tokenize(full_name)

            # Also build variant without hyphens
            no_hyphen = underscore_full.replace('-', '_')

            # Build "LASTNAME_FIRSTNAME" variants
            # Try: first word = last name, rest = first name
            if len(parts) >= 2:
                last = strip_accents(parts[0]).upper()
                first = strip_accents(' '.join(parts[1:])).upper()
                first_underscore = re.sub(r'[\s\-]+', '_', first)
                key_simple = f"{last}_{first_underscore}"
            else:
                key_simple = underscore_full

            # For compound last names (BEN AYED, BEL HADJ, etc.)
            compound_keys = []
            prefixes = ['BEN', 'BEL', 'EL', 'AL']
            if len(parts) >= 3 and strip_accents(parts[0]).upper() in prefixes:
                compound_last = strip_accents(f"{parts[0]}_{parts[1]}").upper()
                compound_first = strip_accents('_'.join(parts[2:])).upper()
                compound_first = re.sub(r'[\s\-]+', '_', compound_first)
                compound_keys.append(f"{compound_last}_{compound_first}")

            entries.append({
                'full_name': full_name,
                'email': email,
                'dob': dob_str,
                'tokens': tokens,
                'keys': [underscore_full, no_hyphen, key_simple] + compound_keys,
            })

    return entries


def filename_to_variants(filename_key: str) -> tuple:
    """
    Generate multiple matching variants from a filename key.
    'BEN_AMEUR_MOHAMED-YOUSSEF' -> tokens + variants
    """
    clean = strip_accents(filename_key).upper()
    tokens = set()
    for t in re.split(r'[\s\-_]+', clean):
        if t and len(t) > 1:
            tokens.add(t)

    # Also generate variant without hyphens
    no_hyphen = clean.replace('-', '_')

    return tokens, [clean, no_hyphen]


def find_best_match(file_key: str, csv_entries: list) -> dict:
    """
    Find the best matching CSV entry for a filename key.
    Returns (entry, score, method) or None.
    """
    file_tokens, file_variants = filename_to_variants(file_key)

    best = None
    best_score = 0
    best_method = ""

    for entry in csv_entries:
        # Method 1: Exact key match (any variant)
        for fv in file_variants:
            for ek in entry['keys']:
                if fv == ek:
                    return entry, 1.0, "exact_key"

        # Method 2: Token overlap (Jaccard similarity)
        csv_tokens = entry['tokens']
        if file_tokens and csv_tokens:
            intersection = file_tokens & csv_tokens
            union = file_tokens | csv_tokens
            jaccard = len(intersection) / len(union) if union else 0

            # Bonus: if all file tokens are in CSV tokens (subset match)
            if file_tokens.issubset(csv_tokens):
                jaccard = max(jaccard, 0.85)
            elif csv_tokens.issubset(file_tokens):
                jaccard = max(jaccard, 0.85)

            if jaccard > best_score:
                best_score = jaccard
                best = entry
                best_method = f"token_jaccard({jaccard:.2f})"

        # Method 3: SequenceMatcher on the full normalized string
        for fv in file_variants:
            for ek in entry['keys']:
                ratio = SequenceMatcher(None, fv, ek).ratio()
                if ratio > best_score:
                    best_score = ratio
                    best = entry
                    best_method = f"sequence({ratio:.2f})"

    if best and best_score >= 0.65:
        return best, best_score, best_method

    return None, 0, ""


def main():
    print("=" * 60)
    print("🔧 FIX UNMATCHED COPIES")
    print("=" * 60)

    csv_map = {
        "BB_J1": build_csv_index(CSV_J1),
        "BB_J2": build_csv_index(CSV_J2),
    }

    total_fixed = 0
    total_still_unmatched = 0

    for exam_name in ["BB_J1", "BB_J2"]:
        csv_entries = csv_map[exam_name]
        unmatched = Copy.objects.filter(
            exam__name=exam_name, is_identified=False
        ).order_by("anonymous_id")

        print(f"\n━━ {exam_name}: {unmatched.count()} unmatched copies ━━")
        print(f"   CSV entries: {len(csv_entries)}")

        fixed = 0
        still_unmatched = []

        for copy in unmatched:
            file_key = copy.anonymous_id.replace(f"{exam_name}-", "")
            match, score, method = find_best_match(file_key, csv_entries)

            if match:
                # Find the student by email
                try:
                    student = Student.objects.get(email=match['email'])
                    copy.student = student
                    copy.is_identified = True
                    copy.save(update_fields=['student', 'is_identified'])
                    fixed += 1
                    print(f"  ✅ {file_key}")
                    print(f"     → {match['full_name']} ({match['email']}) [{method}]")
                except Student.DoesNotExist:
                    print(f"  ⚠️  {file_key} matched to {match['full_name']} but student not in DB")
                    still_unmatched.append(file_key)
            else:
                still_unmatched.append(file_key)
                print(f"  ❌ {file_key} — no match found")

        total_fixed += fixed
        total_still_unmatched += len(still_unmatched)
        print(f"\n  {exam_name}: {fixed} fixed, {len(still_unmatched)} still unmatched")

    print(f"\n{'=' * 60}")
    print(f"✅ TOTAL: {total_fixed} copies matched")
    print(f"❌ STILL UNMATCHED: {total_still_unmatched}")
    print(f"{'=' * 60}")

    # Final stats
    for exam_name in ["BB_J1", "BB_J2"]:
        total = Copy.objects.filter(exam__name=exam_name).count()
        identified = Copy.objects.filter(exam__name=exam_name, is_identified=True).count()
        print(f"  {exam_name}: {identified}/{total} identified")


if __name__ == "__main__":
    main()
