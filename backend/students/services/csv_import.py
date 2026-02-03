from __future__ import annotations

import csv
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple, Type
import os

from django.db import transaction


# Format CSV attendu: Élèves, Né(e) le, Adresse E-mail, Classe, EDS, Groupe
# Clé primaire logique: (FULL_NAME, DATE_NAISSANCE)
REQUIRED_FIELDS = ("FULL_NAME", "DATE_NAISSANCE")
OPTIONAL_FIELDS = ("EMAIL", "CLASSE", "GROUPE_EDS")

# Mapping of alternative column names to standard names
COLUMN_ALIASES = {
    # FULL_NAME alternatives (Nom et Prénom ensemble)
    "ÉLÈVES": "FULL_NAME",
    "ELEVES": "FULL_NAME",
    "NOM ET PRÉNOM": "FULL_NAME",
    "NOM ET PRENOM": "FULL_NAME",
    "NOM PRÉNOM": "FULL_NAME",
    "NOM PRENOM": "FULL_NAME",
    "STUDENT": "FULL_NAME",
    "NAME": "FULL_NAME",
    # EMAIL alternatives
    "ADRESSE E-MAIL": "EMAIL",
    "ADRESSE EMAIL": "EMAIL",
    "E-MAIL": "EMAIL",
    "MAIL": "EMAIL",
    "COURRIEL": "EMAIL",
    # DATE_NAISSANCE alternatives
    "NÉ(E) LE": "DATE_NAISSANCE",
    "NE(E) LE": "DATE_NAISSANCE",
    "DATE DE NAISSANCE": "DATE_NAISSANCE",
    "BIRTH_DATE": "DATE_NAISSANCE",
    "BIRTHDATE": "DATE_NAISSANCE",
    # CLASSE alternatives
    "CLASS": "CLASSE",
    # GROUPE_EDS alternatives
    "GROUPE": "GROUPE_EDS",
    "EDS": "EDS_INFO",  # Additional EDS info
    "EDS ": "EDS_INFO",
}


@dataclass
class ImportErrorItem:
    row: int
    message: str
    data: Dict[str, str] = field(default_factory=dict)


@dataclass
class ImportResult:
    delimiter: str
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: List[ImportErrorItem] = field(default_factory=list)


def _normalize_key(key: str) -> str:
    """Normalize column key and apply aliases."""
    normalized = (key or "").strip().upper()
    # Apply alias mapping
    return COLUMN_ALIASES.get(normalized, normalized)


def _normalize_value(value: Optional[str]) -> str:
    return (value or "").strip()


def detect_delimiter(sample: str, default: str = ",") -> str:
    """
    Best-effort delimiter detection. We keep comma as the default separator,
    but accept sniffed delimiters when the file clearly uses another one.
    """
    try:
        # csv.Sniffer requires a str, so if sample is bytes, decode it
        if isinstance(sample, bytes):
            sample = sample.decode('utf-8', errors='ignore')
            
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t"])
        return dialect.delimiter or default
    except Exception:
        return default


def read_rows_from_csv(fp, delimiter: Optional[str] = None) -> Tuple[str, Iterable[Dict[str, str]]]:
    """
    Returns (delimiter_used, iterator over raw rows).
    """
    # Read a small sample for delimiter sniffing, then rewind.
    sample = fp.read(4096)
    fp.seek(0)

    delimiter_used = delimiter or detect_delimiter(sample, default=",")

    reader = csv.DictReader(fp, delimiter=delimiter_used)

    # Normalize BOM in first header if present
    if reader.fieldnames:
        reader.fieldnames = [fn.replace("\ufeff", "") if fn else fn for fn in reader.fieldnames]

    return delimiter_used, reader


class CsvReadError(Exception):
    pass
    
class CsvSchemaError(Exception):
    pass


def parse_students_csv(path: str, delimiter: str = ",") -> Tuple[ImportResult, List[Dict[str, str]]]:
    """
    Parse file into normalized rows without touching the DB.
    """
    result = ImportResult(delimiter=delimiter)
    rows: List[Dict[str, str]] = []

    if not os.path.exists(path):
        raise CsvReadError(f"File not found: {path}")

    # utf-8-sig handles BOM robustly
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            # Check for empty file
            first_char = f.read(1)
            if not first_char:
                 raise CsvReadError("Empty CSV file")
            f.seek(0)
            
            delimiter_used, reader = read_rows_from_csv(f, delimiter=delimiter)
            result.delimiter = delimiter_used
            
            # Helper to check headers early
            if not reader.fieldnames:
                raise CsvReadError("No headers found")

            for idx, row in enumerate(reader, start=1):
                if not row:
                    result.skipped += 1
                    continue

                normalized: Dict[str, str] = {}
                for k, v in row.items():
                    nk = _normalize_key(k)
                    if not nk:
                        continue
                    normalized[nk] = _normalize_value(v)

                # Validate required fields (FULL_NAME, DATE_NAISSANCE)
                missing = [k for k in REQUIRED_FIELDS if not normalized.get(k)]
                if missing:
                    result.skipped += 1
                    result.errors.append(
                        ImportErrorItem(
                            row=idx,
                            message=f"Missing required fields: {', '.join(missing)}",
                            data=normalized,
                        )
                    )
                    continue

                # Keep only known fields
                cleaned = {
                    "FULL_NAME": normalized.get("FULL_NAME", ""),
                    "DATE_NAISSANCE": normalized.get("DATE_NAISSANCE", ""),
                    "EMAIL": normalized.get("EMAIL", ""),
                    "CLASSE": normalized.get("CLASSE", ""),
                    "GROUPE_EDS": normalized.get("GROUPE_EDS", ""),
                }
                rows.append(cleaned)
                
    except (UnicodeDecodeError, csv.Error) as e:
        raise CsvReadError(f"CSV Parsing Error: {str(e)}")
    except Exception as e:
        if isinstance(e, (CsvReadError, CsvSchemaError)):
             raise e
        raise CsvReadError(f"Unexpected error reading CSV: {str(e)}")

    return result, rows


def _parse_date(date_str: str):
    """Parse date from various formats (DD/MM/YYYY, YYYY-MM-DD, etc.)"""
    if not date_str:
        return None
    
    from datetime import datetime
    formats = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def import_students_rows(rows: List[Dict[str, str]], student_model) -> ImportResult:
    """
    Apply rows to DB. Separated from parsing to keep it testable.
    Uses (full_name, date_of_birth) as unique identifier for students.
    """
    result = ImportResult(delimiter=",")

    for i, r in enumerate(rows, start=1):
        full_name = r["FULL_NAME"]
        date_of_birth = _parse_date(r.get("DATE_NAISSANCE", ""))
        email = r.get("EMAIL", "")
        class_name = r.get("CLASSE", "")
        eds_group = r.get("GROUPE_EDS", "")

        if not date_of_birth:
            result.errors.append(
                ImportErrorItem(
                    row=i,
                    message="Invalid or missing date of birth",
                    data=r,
                )
            )
            continue

        try:
            with transaction.atomic():
                obj, created = student_model.objects.update_or_create(
                    full_name=full_name,
                    date_of_birth=date_of_birth,
                    defaults={
                        "email": email,
                        "class_name": class_name,
                        "eds_group": eds_group,
                    },
                )
            if created:
                result.created += 1
            else:
                result.updated += 1
        except Exception as e:
            result.errors.append(
                ImportErrorItem(
                    row=i,
                    message=str(e),
                    data=r,
                )
            )

    return result


def import_students_from_csv(path: str, student_model, delimiter: str = ",") -> ImportResult:
    """
    High-level helper: parse + import.
    """
    parse_result, rows = parse_students_csv(path, delimiter=delimiter)
    db_result = import_students_rows(rows, student_model=student_model)

    # Merge results (delimiter + skipped/errors from parsing + created/updated/errors from DB)
    merged = ImportResult(delimiter=parse_result.delimiter)
    merged.created = db_result.created
    merged.updated = db_result.updated
    merged.skipped = parse_result.skipped
    merged.errors = [*parse_result.errors, *db_result.errors]
    return merged
