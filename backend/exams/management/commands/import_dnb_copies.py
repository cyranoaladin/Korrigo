"""
Management command: import_dnb_copies
=======================================
Importe en masse les PDFs des copies DNB_2026 depuis le répertoire
scan_DNB_maths/Copies_DNB_BLANC_2026/ dans Korrigo.

Pour chaque fichier NOM_PRENOM_DDMMYYYY_Complet.pdf :
  1. Crée un ExamPDF (stockage Django FileField → copies/source/)
  2. Crée un Copy (status=READY, validated_at=now)
  3. Tente l'auto-identification de l'élève depuis le nom de fichier :
     - Extrait DDN (8 derniers chiffres avant _Complet)
     - Requête Student.objects.filter(date_naissance=ddn) → candidats
     - Si 1 candidat → match direct
     - Si plusieurs → meilleur score de normalisation sur NOM_PRENOM
     - Si 0 → copie créée non-identifiée (warning)
  4. Met is_identified=True + student=<Student> si match confirmé

Idempotent : skip les ExamPDF dont student_identifier est déjà présent.

Usage :
    python manage.py import_dnb_copies
    python manage.py import_dnb_copies --dry-run
    python manage.py import_dnb_copies --dir /chemin/vers/copies/
    python manage.py import_dnb_copies --skip-identification
"""

import datetime
import logging
import os
import re
import unicodedata
import uuid as uuid_module
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_COPIES_DIR = PROJECT_ROOT / "scan_DNB_maths" / "Copies_DNB_BLANC_2026"
DNB_EXAM_NAME = "DNB_2026"


def _normalize(s: str) -> str:
    """Uppercase, strip accents, replace spaces/hyphens with _, collapse __."""
    s = s.upper().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[\s\-]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s


def _parse_filename(fname: str):
    """
    Parse NOM_PRENOM_DDMMYYYY_Complet.pdf → (name_raw, ddn) or None.
    The DDMMYYYY is the 8-digit block immediately before _Complet.
    """
    base = fname.replace("_Complet.pdf", "").replace("_complet.pdf", "")
    m = re.search(r"^(.+)_(\d{8})$", base)
    if not m:
        return None, None
    name_part = m.group(1)   # e.g. "BEN_RHOUMA_KAMEL" or "ABDELLATIF_MOHAMED-YACINE"
    ddn_str = m.group(2)     # DDMMYYYY
    try:
        ddn = datetime.date(
            int(ddn_str[4:8]),
            int(ddn_str[2:4]),
            int(ddn_str[0:2]),
        )
    except ValueError:
        return name_part, None
    return name_part, ddn


def _best_student_match(name_part: str, candidates):
    """
    Among candidates (Student queryset), pick the one whose
    normalized last_name + '_' + first_name best matches name_part.
    Returns (student, score) where score ∈ [0, 1].
    """
    norm_fname = _normalize(name_part)
    best, best_score = None, -1

    for s in candidates:
        # Try both orders: NOM_PRENOM and PRENOM_NOM
        norm_student = _normalize(f"{s.last_name}_{s.first_name}")
        norm_reversed = _normalize(f"{s.first_name}_{s.last_name}")

        # Longest common subsequence ratio (simple overlap)
        score = max(
            _lcs_ratio(norm_fname, norm_student),
            _lcs_ratio(norm_fname, norm_reversed),
        )
        if score > best_score:
            best_score = score
            best = s

    return best, best_score


def _lcs_ratio(a: str, b: str) -> float:
    """Simple character-level similarity: 2*LCS / (len(a)+len(b))."""
    if not a or not b:
        return 0.0
    # Use SequenceMatcher for speed
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b).ratio()


class Command(BaseCommand):
    help = (
        "Import en masse des copies PDF DNB_2026 dans Korrigo "
        "avec auto-identification depuis le nom de fichier."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dir",
            default=str(DEFAULT_COPIES_DIR),
            help=f"Dossier contenant les PDFs (défaut : {DEFAULT_COPIES_DIR})",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simule l'import sans écrire en base ni copier de fichiers.",
        )
        parser.add_argument(
            "--skip-identification",
            action="store_true",
            help="Importe les copies sans tenter l'auto-identification.",
        )
        parser.add_argument(
            "--min-score",
            type=float,
            default=0.65,
            help="Score minimal de similarité pour accepter un match (défaut : 0.65).",
        )

    def handle(self, *args, **options):
        from exams.models import Copy, Exam, ExamPDF
        from exams.views import generate_anonymous_id
        from students.models import Student

        dry_run = options["dry_run"]
        skip_id = options["skip_identification"]
        copies_dir = Path(options["dir"])
        min_score = options["min_score"]

        if dry_run:
            self.stdout.write(self.style.WARNING("=== MODE DRY-RUN — aucune écriture ===\n"))

        if not copies_dir.exists():
            raise CommandError(f"Répertoire introuvable : {copies_dir}")

        # 1. Get exam
        try:
            exam = Exam.objects.get(name=DNB_EXAM_NAME)
        except Exam.DoesNotExist:
            raise CommandError(
                f"Examen '{DNB_EXAM_NAME}' introuvable. "
                "Lancez d'abord : python manage.py setup_dnb_exam"
            )

        self.stdout.write(f"Examen : {exam.name} (id={exam.id})")

        # 2. List PDFs
        pdfs = sorted(
            p for p in copies_dir.iterdir()
            if p.suffix.lower() == ".pdf"
        )
        self.stdout.write(f"PDFs trouvés : {len(pdfs)}")

        # 3. Build student DDN index
        student_by_ddn: dict[datetime.date, list] = {}
        for s in Student.objects.all():
            student_by_ddn.setdefault(s.date_naissance, []).append(s)

        # 4. Existing identifiers (idempotency)
        existing_ids = set(
            ExamPDF.objects.filter(exam=exam)
            .values_list("student_identifier", flat=True)
        )
        self.stdout.write(f"Copies déjà importées : {len(existing_ids)}")

        # 5. Process each PDF
        stats = {"created": 0, "identified": 0, "unmatched": 0, "skipped": 0, "errors": 0}
        unmatched_files: list[str] = []

        for pdf_path in pdfs:
            fname = pdf_path.name
            base_id = fname.replace("_Complet.pdf", "").replace("_complet.pdf", "")

            # Idempotency check
            if base_id in existing_ids:
                stats["skipped"] += 1
                continue

            name_part, ddn = _parse_filename(fname)
            if ddn is None:
                self.stdout.write(self.style.WARNING(f"  [SKIP] Nom non parseable : {fname}"))
                stats["errors"] += 1
                continue

            # Student identification
            student = None
            id_method = ""
            if not skip_id:
                candidates = student_by_ddn.get(ddn, [])
                if len(candidates) == 1:
                    student = candidates[0]
                    id_method = "DDN unique"
                elif len(candidates) > 1:
                    student, score = _best_student_match(name_part, candidates)
                    if score >= min_score:
                        id_method = f"fuzzy ({score:.2f})"
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  [AMBIGU] {fname} — meilleur score {score:.2f} < {min_score} "
                                f"({student}) → non identifiée"
                            )
                        )
                        student = None
                        stats["unmatched"] += 1
                        unmatched_files.append(fname)
                else:
                    self.stdout.write(
                        self.style.WARNING(f"  [NO MATCH] {fname} (DDN {ddn}) → 0 élève en base")
                    )
                    stats["unmatched"] += 1
                    unmatched_files.append(fname)

            if dry_run:
                line = f"  [DRY] {fname}"
                if student:
                    line += f" → {student} ({id_method})"
                else:
                    line += " → non identifiée"
                self.stdout.write(line)
                stats["created"] += 1
                if student:
                    stats["identified"] += 1
                continue

            # --- Persist ---
            try:
                with transaction.atomic():
                    with open(pdf_path, "rb") as fh:
                        django_file = File(fh, name=fname)

                        exam_pdf = ExamPDF.objects.create(
                            exam=exam,
                            pdf_file=django_file,
                            student_identifier=base_id,
                        )

                    copy = Copy.objects.create(
                        exam=exam,
                        anonymous_id=generate_anonymous_id(exam, 0),
                        status=Copy.Status.READY,
                        is_identified=student is not None,
                        student=student,
                        pdf_source=exam_pdf.pdf_file,
                        validated_at=timezone.now(),
                    )

                stats["created"] += 1
                if student:
                    stats["identified"] += 1
                    self.stdout.write(
                        f"  ✓ {fname} → {student} ({id_method})"
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠ {fname} → copie créée, NON identifiée")
                    )

            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  ✗ {fname} — ERREUR : {exc}"))
                logger.exception(f"import_dnb_copies: failed for {fname}")
                stats["errors"] += 1

        # 6. Summary
        self.stdout.write("\n" + self.style.SUCCESS("─" * 60))
        self.stdout.write(self.style.SUCCESS(f"Copies créées       : {stats['created']}"))
        self.stdout.write(self.style.SUCCESS(f"Auto-identifiées    : {stats['identified']}"))
        if stats["unmatched"]:
            self.stdout.write(
                self.style.WARNING(f"Non identifiées     : {stats['unmatched']}")
            )
            for f in unmatched_files:
                self.stdout.write(self.style.WARNING(f"  - {f}"))
        if stats["skipped"]:
            self.stdout.write(f"Déjà importées (skip): {stats['skipped']}")
        if stats["errors"]:
            self.stdout.write(self.style.ERROR(f"Erreurs             : {stats['errors']}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN : aucun fichier écrit."))
