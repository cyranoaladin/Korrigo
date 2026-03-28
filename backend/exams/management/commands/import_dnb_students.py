"""
Management command: import_dnb_students
========================================
Importe les élèves de 3ème depuis troisieme.csv (ou les fichiers par classe 3.X.csv)
dans la base Korrigo — Student + User Django — prêts pour l'examen DNB_2026.

Format troisieme.csv (séparateur ; ou ,) :
    Nom;Prenom;Date_Naissance;Mail;Classe

Résultat pour chaque ligne :
  - Student créé ou mis à jour (last_name, first_name, date_naissance, email, class_name)
  - User Django créé (username=email, password=DEFAULT_PASSWORD)
  - Ajouté au groupe STUDENT

Idempotent : get_or_create sur email.

Usage :
    python manage.py import_dnb_students
    python manage.py import_dnb_students --dry-run
    python manage.py import_dnb_students --dir /chemin/vers/scan_DNB_maths/
    python manage.py import_dnb_students --file troisieme.csv
"""

import csv
import datetime
import io
import os
import re
from pathlib import Path

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.auth import UserRole
from students.models import Student

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_SCAN_DIR = PROJECT_ROOT / "scan_DNB_maths"


def _detect_delimiter(raw: str) -> str:
    """Detect CSV delimiter using csv.Sniffer, fallback to ';'."""
    try:
        import csv as _csv
        dialect = _csv.Sniffer().sniff(raw[:2048], delimiters=",;|\t")
        return dialect.delimiter
    except Exception:
        return ";"


def _parse_date(raw: str) -> datetime.date:
    """Parse DD/MM/YYYY or YYYY-MM-DD."""
    raw = raw.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Date non reconnue : '{raw}'")


def _normalize_name(s: str) -> str:
    """Uppercase + strip accents for display storage (keep original for display)."""
    return s.strip().upper()


class Command(BaseCommand):
    help = (
        "Importe les élèves de 3ème depuis troisieme.csv dans Korrigo "
        "(Student + User Django, groupe STUDENT)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            default=str(DEFAULT_SCAN_DIR),
            help=f"Dossier contenant les CSVs (défaut : {DEFAULT_SCAN_DIR})",
        )
        parser.add_argument(
            "--file",
            default="troisieme.csv",
            help="Fichier CSV à importer (défaut : troisieme.csv)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simule l'import sans écrire en base.",
        )
        parser.add_argument(
            "--password",
            default=None,
            help="Mot de passe par défaut (défaut : DEFAULT_PASSWORD env ou 'passe123')",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        scan_dir = Path(options["dir"])
        csv_file = scan_dir / options["file"]
        password = options["password"] or os.environ.get("DEFAULT_PASSWORD", "passe123")

        if dry_run:
            self.stdout.write(self.style.WARNING("=== MODE DRY-RUN — aucune écriture ===\n"))

        if not csv_file.exists():
            raise CommandError(f"Fichier introuvable : {csv_file}")

        # Ensure STUDENT group exists
        student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)

        # Read CSV
        raw = csv_file.read_text(encoding="utf-8-sig")
        delimiter = _detect_delimiter(raw)
        reader = csv.DictReader(io.StringIO(raw), delimiter=delimiter)

        # Normalize header keys
        rows = []
        for row in reader:
            normalized = {k.strip().lower(): v.strip() for k, v in row.items()}
            rows.append(normalized)

        self.stdout.write(f"Fichier : {csv_file.name} ({len(rows)} élèves)")

        # Detect column names (flexible)
        if not rows:
            raise CommandError("CSV vide.")

        sample = rows[0]
        col_nom = next((k for k in sample if k in ("nom", "last_name")), None)
        col_prenom = next((k for k in sample if k in ("prenom", "prénom", "first_name")), None)
        col_ddn = next((k for k in sample if "naiss" in k or k in ("ddn", "date_naissance")), None)
        col_mail = next((k for k in sample if "mail" in k or "email" in k), None)
        col_classe = next((k for k in sample if "class" in k or k == "classe"), None)

        if not all([col_nom, col_prenom, col_ddn]):
            raise CommandError(
                f"Colonnes requises introuvables. Colonnes détectées : {list(sample.keys())}"
            )

        self.stdout.write(
            f"Colonnes → nom={col_nom}, prénom={col_prenom}, "
            f"ddn={col_ddn}, mail={col_mail}, classe={col_classe}"
        )

        stats = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}

        for row in rows:
            try:
                last_name = _normalize_name(row[col_nom])
                first_name = _normalize_name(row[col_prenom])
                ddn = _parse_date(row[col_ddn])
                # Sanitize email: take first address if multiple separated by "et", space, or comma
                raw_mail = row.get(col_mail, "").strip() if col_mail else ""
                email = re.split(r"\s+et\s+|,\s*", raw_mail, maxsplit=1)[0].strip().lower()
                class_name = row.get(col_classe, "").strip() if col_classe else ""

                if not last_name or not first_name:
                    stats["errors"] += 1
                    continue

                if dry_run:
                    self.stdout.write(
                        f"  [DRY] {last_name} {first_name} | {ddn} | {class_name} | {email}"
                    )
                    stats["created"] += 1
                    continue

                with transaction.atomic():
                    # Student — unique on (last_name, first_name, date_naissance)
                    student, s_created = Student.objects.get_or_create(
                        last_name=last_name,
                        first_name=first_name,
                        date_naissance=ddn,
                        defaults={
                            "email": email,
                            "class_name": class_name,
                        },
                    )
                    if not s_created:
                        # Update email/class if changed
                        changed = False
                        if email and student.email != email:
                            student.email = email
                            changed = True
                        if class_name and student.class_name != class_name:
                            student.class_name = class_name
                            changed = True
                        if changed:
                            student.save(update_fields=["email", "class_name"])
                            stats["updated"] += 1
                        else:
                            stats["skipped"] += 1
                    else:
                        stats["created"] += 1

                    # User account (login via email)
                    if email:
                        user, u_created = User.objects.get_or_create(
                            username=email,
                            defaults={
                                "email": email,
                                "first_name": first_name.capitalize(),
                                "last_name": last_name.capitalize(),
                            },
                        )
                        if u_created:
                            user.set_password(password)
                            user.save()

                        student_group.user_set.add(user)

                        if not student.user:
                            student.user = user
                            student.save(update_fields=["user"])

            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ {row} — ERREUR : {exc}")
                )
                stats["errors"] += 1

        # Summary
        self.stdout.write("\n" + self.style.SUCCESS("─" * 60))
        self.stdout.write(self.style.SUCCESS(f"Élèves créés        : {stats['created']}"))
        if stats["updated"]:
            self.stdout.write(f"Mis à jour          : {stats['updated']}")
        if stats["skipped"]:
            self.stdout.write(f"Déjà en base (skip) : {stats['skipped']}")
        if stats["errors"]:
            self.stdout.write(self.style.ERROR(f"Erreurs             : {stats['errors']}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN : aucun enregistrement écrit."))
