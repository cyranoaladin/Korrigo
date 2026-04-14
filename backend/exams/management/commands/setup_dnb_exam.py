"""
Management command: setup_dnb_exam
===================================
Idempotent setup of the DNB BLANC MATHS 2026 exam in Korrigo:

  1. Creates (or returns existing) the Exam object linked to ExamType DNBM2026.
  2. Imports all students from scan_DNB_maths/troisieme.csv into the Student table
     preserving class_name (3.1 → 3.10).
  3. Registers all correctors listed in enseignants.csv on exam.correctors.
  4. Attaches the troisieme.csv as the exam's students_csv file so it is available
     in the admin UI and for the identification desk.

Usage:
    python manage.py setup_dnb_exam
    python manage.py setup_dnb_exam --dry-run
    python manage.py setup_dnb_exam --csv /path/to/troisieme.csv
    python manage.py setup_dnb_exam --date 2026-03-15
"""

import csv
import datetime
import io
import logging
import os
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

logger = logging.getLogger(__name__)

# ── Paths relative to the project root ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[4]  # korrigo_v2_improved/
DNB_DIR = PROJECT_ROOT / "scan_DNB_maths"
DEFAULT_CSV = DNB_DIR / "troisieme.csv"
CLASSES_CSV = DNB_DIR / "classes_troisieme.csv"
ENSEIGNANTS_CSV = PROJECT_ROOT / "enseignants.csv"

# ── Exam defaults ────────────────────────────────────────────────────────────
from exams.exam_type_codes import DNB_BLANC_CODE as DNB_EXAM_TYPE_CODE  # noqa: E402
from exams.dnb_2026_structure import build_dnb_2026_grading_structure  # noqa: E402
DNB_EXAM_NAME = "DNB_2026"
DNB_EXAM_DATE = datetime.date(2026, 3, 15)   # adjust if needed
UPLOAD_MODE = "INDIVIDUAL_A4"               # copies déjà découpées individuellement


class Command(BaseCommand):
    help = (
        "Configure l'examen DNB BLANC MATHS 2026 : "
        "création de l'examen, import des élèves, enregistrement des correcteurs."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            default=str(DEFAULT_CSV),
            help=f"Chemin vers le CSV élèves (défaut : {DEFAULT_CSV})",
        )
        parser.add_argument(
            "--date",
            default=str(DNB_EXAM_DATE),
            help=f"Date de l'examen YYYY-MM-DD (défaut : {DNB_EXAM_DATE})",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche ce qui serait fait sans rien modifier en base.",
        )

    # ── Main entry ───────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        csv_path = Path(options["csv"])
        exam_date = datetime.date.fromisoformat(options["date"])

        if dry_run:
            self.stdout.write(self.style.WARNING("=== MODE DRY-RUN — aucune écriture en base ===\n"))

        if not csv_path.exists():
            raise CommandError(f"Fichier CSV introuvable : {csv_path}")

        # Step 1 – Get or create exam
        exam = self._setup_exam(exam_date, csv_path, dry_run)

        # Step 2 – Import students
        students_created, students_skipped = self._import_students(csv_path, dry_run)

        # Step 3 – Register correctors
        correctors_added = self._register_correctors(exam, dry_run)

        # Summary
        self.stdout.write("\n" + self.style.SUCCESS("─" * 60))
        self.stdout.write(self.style.SUCCESS(f"Examen    : {DNB_EXAM_NAME}"))
        self.stdout.write(self.style.SUCCESS(f"Élèves    : {students_created} créés, {students_skipped} existants"))
        self.stdout.write(self.style.SUCCESS(f"Correcteurs enregistrés : {correctors_added}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN : aucun changement persisté."))

    # ── Step 1 : exam ─────────────────────────────────────────────────────────

    def _setup_exam(self, exam_date, csv_path, dry_run):
        from exams.models import Exam, ExamType

        try:
            exam_type = ExamType.objects.get(code=DNB_EXAM_TYPE_CODE)
        except ExamType.DoesNotExist:
            raise CommandError(
                f"ExamType '{DNB_EXAM_TYPE_CODE}' introuvable. "
                "Vérifiez que les types d'examens ont été créés (create_exam_types)."
            )

        existing = Exam.objects.filter(exam_type=exam_type, name=DNB_EXAM_NAME).first()
        if existing:
            if not existing.grading_structure and not dry_run:
                existing.grading_structure = build_dnb_2026_grading_structure()
                existing.save(update_fields=["grading_structure"])
                self.stdout.write(self.style.SUCCESS("  ✓ Barème DNB_2026 backfillé sur l'examen existant"))
            self.stdout.write(f"  Examen déjà existant : {existing.name} (id={existing.id})")
            return existing

        self.stdout.write(f"  Création de l'examen '{DNB_EXAM_NAME}'…")
        if dry_run:
            self.stdout.write(self.style.WARNING("    [DRY-RUN] Examen non créé."))
            return None

        with transaction.atomic():
            exam = Exam.objects.create(
                name=DNB_EXAM_NAME,
                date=exam_date,
                exam_type=exam_type,
                upload_mode=UPLOAD_MODE,
                grading_structure=build_dnb_2026_grading_structure(),
            )
            # Attach CSV as students_csv
            csv_content = csv_path.read_bytes()
            exam.students_csv.save(
                f"dnb_troisieme_{exam_date}.csv",  # pas de sujet A/B — un seul fichier
                ContentFile(csv_content),
                save=True,
            )

        self.stdout.write(self.style.SUCCESS(f"  ✓ Examen créé : id={exam.id}"))
        return exam

    # ── Step 2 : students ─────────────────────────────────────────────────────

    def _import_students(self, csv_path, dry_run):
        """
        Parse troisieme.csv (semicolon-separated, columns: Nom;Prenom;Date_Naissance;Mail;Classe)
        and create Student objects.  Existing records (unique on last_name+first_name+date_naissance)
        are skipped (idempotent).
        """
        from students.models import Student

        created = 0
        skipped = 0
        errors = 0

        with open(csv_path, newline="", encoding="utf-8-sig") as f:
            # Auto-detect separator
            sample = f.read(4096)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
                delimiter = dialect.delimiter
            except csv.Error:
                delimiter = ';'  # fallback to French standard
            reader = csv.DictReader(f, delimiter=delimiter)
            rows = list(reader)

        self.stdout.write(f"\n  Import de {len(rows)} élèves depuis {csv_path.name}…")

        for row in rows:
            nom = row.get("Nom", "").strip().upper()
            prenom = row.get("Prenom", "").strip().upper()
            ddn_raw = row.get("Date_Naissance", "").strip()
            email = row.get("Mail", "").strip()
            classe = row.get("Classe", "").strip()

            if not nom or not prenom or not ddn_raw:
                self.stdout.write(self.style.WARNING(f"    Ligne ignorée (données manquantes) : {row}"))
                errors += 1
                continue

            try:
                ddn = datetime.date(
                    int(ddn_raw[6:10]),   # YYYY
                    int(ddn_raw[3:5]),    # MM
                    int(ddn_raw[0:2]),    # DD
                )
            except (ValueError, IndexError):
                self.stdout.write(self.style.WARNING(f"    Date invalide pour {nom} {prenom} : '{ddn_raw}'"))
                errors += 1
                continue

            if dry_run:
                exists = Student.objects.filter(
                    last_name=nom, first_name=prenom, date_naissance=ddn
                ).exists()
                if exists:
                    skipped += 1
                else:
                    created += 1
                continue

            try:
                with transaction.atomic():
                    _, was_created = Student.objects.get_or_create(
                        last_name=nom,
                        first_name=prenom,
                        date_naissance=ddn,
                        defaults={
                            "email": email or None,
                            "class_name": classe,
                        },
                    )
                if was_created:
                    created += 1
                else:
                    skipped += 1
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"    Erreur pour {nom} {prenom} : {exc}"))
                errors += 1

        self.stdout.write(
            f"  Import élèves : {created} créés, {skipped} existants, {errors} erreurs."
        )
        return created, skipped

    # ── Step 3 : correctors ───────────────────────────────────────────────────

    def _register_correctors(self, exam, dry_run):
        """
        Add correctors listed in enseignants.csv to exam.correctors.
        Only adds users that actually exist in the Django User table.
        """
        if exam is None:
            return 0

        if not ENSEIGNANTS_CSV.exists():
            self.stdout.write(self.style.WARNING(f"  Fichier enseignants.csv introuvable : {ENSEIGNANTS_CSV}"))
            return 0

        added = 0
        with open(ENSEIGNANTS_CSV, newline="", encoding="utf-8-sig") as f:
            # Auto-detect separator
            sample = f.read(4096)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
                delimiter = dialect.delimiter
            except csv.Error:
                delimiter = ';'  # fallback to French standard
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                email = row.get("mail", "").strip().lower()
                if not email:
                    continue
                user = (
                    User.objects.filter(username=email).first()
                    or User.objects.filter(email=email).first()
                )
                if not user:
                    self.stdout.write(
                        self.style.WARNING(f"  Correcteur introuvable en DB : {email}")
                    )
                    continue

                if not exam.correctors.filter(pk=user.pk).exists():
                    if not dry_run:
                        exam.correctors.add(user)
                    self.stdout.write(
                        f"  {'[DRY-RUN] ' if dry_run else ''}Correcteur enregistré : {email}"
                    )
                    added += 1
                else:
                    self.stdout.write(f"  Correcteur déjà enregistré : {email}")

        return added
