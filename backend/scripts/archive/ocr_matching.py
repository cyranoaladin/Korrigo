#!/usr/bin/env python3
"""
OCR-based matching for unmatched copies.
Strategy:
1. For each unmatched copy, OCR the header of page 1
2. Extract nom, prénom, date de naissance from OCR text
3. Match against eleves_terminale_maths.csv using the triplet
4. Import missing students and link copies
"""
import os
import sys
import csv
import re
import io
import unicodedata
from pathlib import Path
from datetime import datetime, date
from difflib import SequenceMatcher

sys.path.append(str(Path(__file__).resolve().parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

import django
django.setup()

import fitz
from PIL import Image
import pytesseract

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from exams.models import Exam, Copy
from students.models import Student

User = get_user_model()

CSV_FULL = Path("/tmp/eleves_terminale_maths.csv")

# False positive from v2 to revert
FALSE_POSITIVE = "BB_J1-BEN_AMEUR_MOHAMED-YOUSSEF"


def strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize('NFKD', s)
    return nfkd.encode('ASCII', 'ignore').decode('ASCII')


def normalize(s: str) -> str:
    clean = strip_accents(s).upper().strip()
    clean = re.sub(r'[^A-Z0-9\s]', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def tokenize(s: str) -> set:
    return {t for t in normalize(s).split() if len(t) > 1}


def parse_date_csv(date_str: str) -> date:
    try:
        return datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def build_csv_index(csv_path: Path) -> list:
    """Build index from full CSV with all students."""
    entries = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            full_name = row.get('Élèves', '').strip()
            email = row.get('Adresse E-mail', '').strip()
            dob_str = row.get('Né(e) le', '').strip()
            classe = row.get('Classe', '').strip()
            groupe = row.get('Groupe', '').strip()

            if not full_name or not email:
                continue

            parts = full_name.split()
            last_name = parts[0] if parts else full_name
            first_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
            dob = parse_date_csv(dob_str)

            entries.append({
                'full_name': full_name,
                'last_name': last_name,
                'first_name': first_name,
                'email': email,
                'dob': dob,
                'dob_str': dob_str,
                'class_name': classe,
                'groupe': groupe,
                'tokens': tokenize(full_name),
                'norm': normalize(full_name),
            })
    return entries


def ocr_header(copy) -> str:
    """Extract text from the top 30% of the first page via OCR."""
    try:
        copy.pdf_source.open()
        pdf_bytes = copy.pdf_source.read()
        copy.pdf_source.close()

        with fitz.open("pdf", pdf_bytes) as doc:
            page = doc[0]
            rect = page.rect
            clip = fitz.Rect(rect.x0, rect.y0, rect.x1, rect.y1 * 0.30)
            mat = fitz.Matrix(300/72, 300/72)
            pix = page.get_pixmap(matrix=mat, clip=clip)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img, lang="fra")
            return text
    except Exception as e:
        return f"[OCR ERROR: {e}]"


def extract_name_from_ocr(ocr_text: str) -> dict:
    """
    Parse OCR text to extract:
    - last_name (NOM DE FAMILLE)
    - first_name (Prénom)
    - date of birth (Né(e) le)
    """
    result = {'last_name': '', 'first_name': '', 'dob_str': '', 'dob': None}

    lines = ocr_text.split('\n')

    # Strategy: look for patterns in the OCR text
    # The form has:
    # NOM DE FAMILLE (naissance) : <handwritten>
    # Prénom : <handwritten>
    # Né(e) le : <handwritten>

    # We'll look for lines that contain boxed handwritten text
    # Often OCR reads handwritten text in boxes as uppercase letters with pipes/brackets

    for i, line in enumerate(lines):
        line_upper = line.upper().strip()

        # Look for NOM line - often contains the last name in boxes
        # Pattern: after "NOM DE FAMILLE" there's usually a line with the handwritten name
        if 'NOM DE FAMILLE' in line_upper or 'NOM' == line_upper.strip():
            # The name is usually on this line or the next, in box characters
            # Look for content after the label, or next line
            name_text = extract_boxed_text(line)
            if not name_text and i + 1 < len(lines):
                name_text = extract_boxed_text(lines[i + 1])
            if name_text:
                result['last_name'] = clean_ocr_name(name_text)

        # Look for Prénom line
        if 'PRÉNOM' in line_upper or 'PRENOM' in line_upper or 'nom:' in line.lower():
            # "nom:" with lowercase often means "prénom:" misread
            prenom_text = extract_boxed_text(line)
            if not prenom_text and i + 1 < len(lines):
                prenom_text = extract_boxed_text(lines[i + 1])
            if prenom_text:
                result['first_name'] = clean_ocr_name(prenom_text)

        # Look for date of birth
        if 'NÉ' in line_upper or 'NE(' in line_upper or 'le :' in line.lower() or 'le:' in line.lower():
            dob_text = extract_date_from_line(line)
            if dob_text:
                result['dob_str'] = dob_text
                result['dob'] = try_parse_ocr_date(dob_text)

    # Fallback: try to extract from boxed/bracketed text patterns
    if not result['last_name']:
        # Look for patterns like [M|E|H|E|R|Z|I] or melHlelel2Nl
        for line in lines:
            boxed = extract_boxed_text(line)
            if boxed and len(boxed) >= 3:
                if not result['last_name']:
                    result['last_name'] = clean_ocr_name(boxed)
                elif not result['first_name']:
                    result['first_name'] = clean_ocr_name(boxed)

    return result


def extract_boxed_text(line: str) -> str:
    """Extract text that appears to be in boxes (handwritten form fields)."""
    # Pattern 1: Text between brackets/pipes: [M|E|H|E|R|Z|I]
    m = re.search(r'[\[\(]([A-Za-zÀ-ÿ\|]+)[\]\)]', line)
    if m:
        return m.group(1).replace('|', '')

    # Pattern 2: Pipe-separated letters: M|E|H|E|R|Z|I
    m = re.search(r'([A-Za-zÀ-ÿ]\|){2,}[A-Za-zÀ-ÿ]', line)
    if m:
        return m.group(0).replace('|', '')

    # Pattern 3: After a colon or bracket, extract uppercase letters
    m = re.search(r'[:»]\s*([A-ZÀ-Ÿ][A-Za-zÀ-ÿ\s\-]{2,})', line)
    if m:
        return m.group(1).strip()

    # Pattern 4: Boxed characters like melHlelel2Nl (OCR of handwritten in boxes)
    # These often have mixed case and numbers mixed in
    m = re.search(r'[:\s]([a-zA-ZÀ-ÿ0-9]{4,})[|\]\s]', line)
    if m:
        text = m.group(1)
        # Filter out if it's mostly numbers
        letters = sum(1 for c in text if c.isalpha())
        if letters >= len(text) * 0.5:
            return text

    return ''


def clean_ocr_name(text: str) -> str:
    """Clean OCR'd name: fix common OCR errors, uppercase."""
    text = text.strip()
    # Remove pipes, brackets, numbers that are OCR artifacts
    text = re.sub(r'[|\[\]{}()\d]', '', text)
    # Replace common OCR misreads
    text = text.replace('l', 'I').replace('0', 'O').replace('1', 'I')
    text = text.upper().strip()
    # Remove stray single characters
    text = re.sub(r'\b[A-Z]\b', '', text).strip()
    return text


def extract_date_from_line(line: str) -> str:
    """Extract a date pattern from a line."""
    # Look for dd/mm/yyyy or dd.mm.yyyy patterns
    m = re.search(r'(\d{1,2})\s*[/.\-]\s*(\d{1,2})\s*[/.\-]\s*(\d{2,4})', line)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"

    # OCR often reads dates with errors - look for digit clusters
    m = re.search(r'(\d{1,2})\s*[oOl|]\s*(\d{1,2})\s*[oOl|]\s*(\d{2,4})', line)
    if m:
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"

    return ''


def try_parse_ocr_date(date_str: str) -> date:
    """Try to parse an OCR'd date string."""
    # Normalize separators
    clean = re.sub(r'[/.\-\s]+', '/', date_str.strip())
    parts = clean.split('/')
    if len(parts) == 3:
        try:
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2])
            if year < 100:
                year += 2000
            if 1 <= day <= 31 and 1 <= month <= 12 and 2000 <= year <= 2030:
                return date(year, month, day)
        except ValueError:
            pass
    return None


def match_ocr_to_csv(ocr_info: dict, csv_entries: list, file_key: str) -> tuple:
    """
    Match OCR-extracted info against CSV entries.
    Priority:
    1. Exact date match + name token overlap
    2. Strong name token overlap (>= 70% Jaccard)
    3. Filename-based matching with the full CSV
    """
    ocr_tokens = set()
    if ocr_info['last_name']:
        ocr_tokens.update(tokenize(ocr_info['last_name']))
    if ocr_info['first_name']:
        ocr_tokens.update(tokenize(ocr_info['first_name']))

    file_tokens = tokenize(file_key.replace('_', ' ').replace('-', ' '))

    best = None
    best_score = 0
    best_method = ""

    for entry in csv_entries:
        score = 0
        method_parts = []

        # Date match bonus
        if ocr_info['dob'] and entry['dob'] and ocr_info['dob'] == entry['dob']:
            score += 0.4
            method_parts.append("dob_exact")

        # OCR name tokens vs CSV name tokens
        if ocr_tokens and entry['tokens']:
            overlap = ocr_tokens & entry['tokens']
            jaccard = len(overlap) / len(ocr_tokens | entry['tokens'])
            if jaccard > 0:
                score += jaccard * 0.3
                method_parts.append(f"ocr_name({jaccard:.2f})")

        # Filename tokens vs CSV name tokens
        if file_tokens and entry['tokens']:
            overlap = file_tokens & entry['tokens']
            jaccard = len(overlap) / len(file_tokens | entry['tokens'])
            if jaccard > 0:
                score += jaccard * 0.3
                method_parts.append(f"file_name({jaccard:.2f})")

        if score > best_score:
            best_score = score
            best = entry
            best_method = "+".join(method_parts)

    # Require minimum confidence
    if best and best_score >= 0.35:
        return best, best_score, best_method

    return None, 0, ""


def ensure_student(entry: dict) -> Student:
    """Get or create a Student from a CSV entry."""
    student, created = Student.objects.get_or_create(
        email=entry['email'],
        defaults={
            'first_name': entry['first_name'],
            'last_name': entry['last_name'],
            'date_naissance': entry['dob'] or date(2008, 1, 1),
            'class_name': entry['class_name'],
            'groupe': entry['groupe'],
        }
    )
    if created:
        grp, _ = Group.objects.get_or_create(name='student')
        user = User.objects.create_user(
            username=entry['email'],
            email=entry['email'],
            password=os.environ.get('DEFAULT_PASSWORD', 'changeme')
        )
        user.groups.add(grp)
        student.user = user
        student.save()
        print(f"     [NEW STUDENT] {entry['full_name']} ({entry['email']})")
    return student


def main():
    print("=" * 70)
    print("🔍 OCR-BASED MATCHING FOR UNMATCHED COPIES")
    print("=" * 70)

    # Step 0: Revert false positive
    try:
        fp = Copy.objects.get(anonymous_id=FALSE_POSITIVE)
        if fp.is_identified:
            print(f"↩ Reverting false positive: {FALSE_POSITIVE}")
            fp.student = None
            fp.is_identified = False
            fp.save(update_fields=['student', 'is_identified'])
    except Copy.DoesNotExist:
        pass

    # Build CSV index
    csv_entries = build_csv_index(CSV_FULL)
    print(f"CSV: {len(csv_entries)} students loaded from {CSV_FULL.name}")

    # Get unmatched copies
    unmatched = Copy.objects.filter(
        exam__name="BB_J1", is_identified=False
    ).order_by("anonymous_id")
    print(f"Unmatched copies: {unmatched.count()}")

    fixed = 0
    still_unmatched = []

    for i, copy in enumerate(unmatched, 1):
        file_key = copy.anonymous_id.replace("BB_J1-", "")
        print(f"\n[{i}/{unmatched.count()}] {file_key}")

        # OCR the header
        ocr_text = ocr_header(copy)
        ocr_info = extract_name_from_ocr(ocr_text)

        print(f"  OCR → nom={ocr_info['last_name']!r}, "
              f"prénom={ocr_info['first_name']!r}, "
              f"dob={ocr_info['dob_str']!r}")

        # Match against CSV
        match, score, method = match_ocr_to_csv(ocr_info, csv_entries, file_key)

        if match:
            student = ensure_student(match)
            copy.student = student
            copy.is_identified = True
            copy.save(update_fields=['student', 'is_identified'])
            fixed += 1
            print(f"  ✅ → {match['full_name']} ({match['email']}) "
                  f"[score={score:.2f}, {method}]")
        else:
            still_unmatched.append(file_key)
            print(f"  ❌ No match (best score={score:.2f})")
            # Print OCR text for debugging
            print(f"  OCR raw (first 200 chars): {ocr_text[:200]!r}")

    # Summary
    print(f"\n{'=' * 70}")
    print(f"✅ FIXED: {fixed} copies matched via OCR")
    print(f"❌ STILL UNMATCHED: {len(still_unmatched)}")
    if still_unmatched:
        for name in still_unmatched:
            print(f"   - {name}")

    for exam_name in ["BB_J1", "BB_J2"]:
        total = Copy.objects.filter(exam__name=exam_name).count()
        identified = Copy.objects.filter(exam__name=exam_name, is_identified=True).count()
        print(f"  {exam_name}: {identified}/{total} identified")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
