#!/usr/bin/env python3
"""
Fix matching v2:
1. Revert false positives from v1 (sequence matches that were wrong)
2. Use strict matching: exact_key or token subset with same last name
3. List truly unmatched copies (students not in CSV)
"""
import os
import sys
import csv
import re
import unicodedata
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

from exams.models import Exam, Copy
from students.models import Student


CSV_J1 = Path("/tmp/eleves_maths_J1.csv")
CSV_J2 = Path("/tmp/eleves_maths_J2.csv")

# Known false positives from v1 to revert
FALSE_POSITIVES_J1 = [
    "BB_J1-BEN_AMEUR_MOHAMED-YOUSSEF",   # matched BEN MRAD YOUSSEF (wrong)
    "BB_J1-BEN_AYED_SALMA",               # matched BEN AYED HAFEDH (wrong)
    "BB_J1-BEN_RAYANA_MOHAMED",           # matched BEN AYED HAFEDH (wrong)
    "BB_J1-CHAOUCH_RIMA",                 # matched CHAOUCH YASMIN (wrong)
    "BB_J1-CHOUAYA_YOUSSEF",              # matched BOUHELA YOUSSEF (wrong)
    "BB_J1-KHEMIRI_HEDI",                 # matched HASSAIRI HEDI (wrong)
    "BB_J1-MHAMED_SELIMA",                # matched AMEUR SELIM (wrong)
    "BB_J1-MRAD_MOHAMED-AZIZ",            # matched ZARDI MOHAMED (wrong)
]


def strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize('NFKD', s)
    return nfkd.encode('ASCII', 'ignore').decode('ASCII')


def normalize(s: str) -> str:
    """Full normalization: strip accents, uppercase, replace separators with _."""
    clean = strip_accents(s).upper().strip()
    clean = re.sub(r'[\s\-\'\"]+', '_', clean)
    clean = re.sub(r'[^A-Z0-9_]', '', clean)
    return clean


def get_last_name_token(full_name: str) -> str:
    """Extract the last name (first word) from a CSV full name."""
    parts = full_name.strip().split()
    if parts:
        return strip_accents(parts[0]).upper()
    return ""


def build_csv_index(csv_path: Path) -> list:
    entries = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            full_name = row.get('Élèves', '').strip()
            email = row.get('Adresse E-mail', '').strip()
            dob = row.get('Né(e) le', '').strip()
            if not full_name or not email:
                continue

            norm = normalize(full_name)
            last_name = get_last_name_token(full_name)

            # Build multiple key variants
            keys = set()
            keys.add(norm)
            # Without hyphens converted
            keys.add(norm.replace('-', '_'))

            # For compound last names: BEN AYED SALMA -> BEN_AYED_SALMA
            parts = full_name.strip().split()
            prefixes = {'BEN', 'BEL', 'EL', 'AL'}
            if len(parts) >= 3 and strip_accents(parts[0]).upper() in prefixes:
                # compound: BEN_AYED as last, rest as first
                compound = normalize(' '.join(parts[:2]))
                first = normalize(' '.join(parts[2:]))
                keys.add(f"{compound}_{first}")

            # Tokens for subset matching
            tokens = set()
            for t in re.split(r'[\s\-_]+', strip_accents(full_name).upper()):
                if t and len(t) > 1:
                    tokens.add(t)

            entries.append({
                'full_name': full_name,
                'email': email,
                'dob': dob,
                'last_name': last_name,
                'keys': keys,
                'tokens': tokens,
                'norm': norm,
            })
    return entries


def match_copy(file_key: str, csv_entries: list):
    """
    Match a file key to a CSV entry using strict rules:
    1. Exact key match (any variant)
    2. Same last name + all first name tokens match
    """
    file_norm = normalize(file_key)
    file_norm_no_hyphen = file_norm.replace('-', '_')
    file_tokens = set()
    for t in re.split(r'[_]+', file_norm):
        if t and len(t) > 1:
            file_tokens.add(t)

    # Extract probable last name from filename (first token, or first two if compound)
    file_parts = file_norm.split('_')
    prefixes = {'BEN', 'BEL', 'EL', 'AL'}
    if len(file_parts) >= 2 and file_parts[0] in prefixes:
        file_last = f"{file_parts[0]}_{file_parts[1]}"
        file_first_tokens = set(file_parts[2:])
    else:
        file_last = file_parts[0] if file_parts else ""
        file_first_tokens = set(file_parts[1:])

    # Method 1: Exact key match
    for entry in csv_entries:
        if file_norm in entry['keys'] or file_norm_no_hyphen in entry['keys']:
            return entry, "exact_key"

    # Method 2: Same last name + first name tokens are a subset
    candidates = []
    for entry in csv_entries:
        entry_last = normalize(entry['last_name'])

        # Check compound last names in both directions
        entry_parts = entry['norm'].split('_')
        if len(entry_parts) >= 2 and entry_parts[0] in prefixes:
            entry_compound_last = f"{entry_parts[0]}_{entry_parts[1]}"
            entry_first_tokens = set(entry_parts[2:])
        else:
            entry_compound_last = entry_parts[0] if entry_parts else ""
            entry_first_tokens = set(entry_parts[1:])

        # Last name must match
        last_match = (file_last == entry_last or
                      file_last == entry_compound_last or
                      file_parts[0] == entry_parts[0] if file_parts and entry_parts else False)

        if not last_match:
            continue

        # Check first name token overlap
        if file_first_tokens and entry_first_tokens:
            # All file first tokens must be in entry first tokens or vice versa
            if file_first_tokens.issubset(entry_first_tokens):
                candidates.append((entry, len(file_first_tokens & entry_first_tokens), "subset_match"))
            elif entry_first_tokens.issubset(file_first_tokens):
                candidates.append((entry, len(file_first_tokens & entry_first_tokens), "superset_match"))
            else:
                # Partial overlap - at least 50% of tokens match
                overlap = file_first_tokens & entry_first_tokens
                if len(overlap) >= max(1, len(file_first_tokens) * 0.5):
                    candidates.append((entry, len(overlap), "partial_match"))

    if candidates:
        # Pick best candidate (most token overlap)
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0], candidates[0][2]

    return None, ""


def main():
    print("=" * 60)
    print("🔧 FIX MATCHING V2 — STRICT MODE")
    print("=" * 60)

    # Step 1: Revert false positives
    print("\n━━ STEP 1: Revert false positives from v1 ━━")
    reverted = 0
    for anon_id in FALSE_POSITIVES_J1:
        try:
            copy = Copy.objects.get(anonymous_id=anon_id)
            if copy.is_identified:
                old_student = copy.student
                copy.student = None
                copy.is_identified = False
                copy.save(update_fields=['student', 'is_identified'])
                reverted += 1
                print(f"  ↩ Reverted {anon_id} (was → {old_student})")
        except Copy.DoesNotExist:
            pass
    print(f"  Reverted {reverted} false positives")

    # Step 2: Re-match with strict rules
    csv_map = {
        "BB_J1": build_csv_index(CSV_J1),
        "BB_J2": build_csv_index(CSV_J2),
    }

    total_fixed = 0
    total_unmatched = 0

    for exam_name in ["BB_J1", "BB_J2"]:
        csv_entries = csv_map[exam_name]
        unmatched = Copy.objects.filter(
            exam__name=exam_name, is_identified=False
        ).order_by("anonymous_id")

        print(f"\n━━ STEP 2: {exam_name} — {unmatched.count()} unmatched ━━")

        fixed = 0
        still_unmatched = []

        for copy in unmatched:
            file_key = copy.anonymous_id.replace(f"{exam_name}-", "")
            match, method = match_copy(file_key, csv_entries)

            if match:
                try:
                    student = Student.objects.get(email=match['email'])
                    copy.student = student
                    copy.is_identified = True
                    copy.save(update_fields=['student', 'is_identified'])
                    fixed += 1
                    print(f"  ✅ {file_key}")
                    print(f"     → {match['full_name']} ({match['email']}) [{method}]")
                except Student.DoesNotExist:
                    still_unmatched.append((file_key, f"student not in DB: {match['email']}"))
            else:
                still_unmatched.append((file_key, "no CSV match"))

        total_fixed += fixed
        total_unmatched += len(still_unmatched)

        if still_unmatched:
            print(f"\n  ❌ Still unmatched ({len(still_unmatched)}):")
            for name, reason in still_unmatched:
                print(f"     - {name} ({reason})")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"✅ FIXED: {total_fixed} copies newly matched")
    print(f"❌ UNMATCHED: {total_unmatched} copies (students not in CSV)")
    for exam_name in ["BB_J1", "BB_J2"]:
        total = Copy.objects.filter(exam__name=exam_name).count()
        identified = Copy.objects.filter(exam__name=exam_name, is_identified=True).count()
        print(f"  {exam_name}: {identified}/{total} identified")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
