"""
Management command: identify_dnb_copies
==========================================
Pour chaque copie DNB_2026 non-identifiée, retrouve l'élève correspondant
en croisant ExamPDF.student_identifier (NOM_PRENOM_DDMMYYYY) avec la table Student.

Algorithme :
  1. Récupère le ExamPDF lié à la copie via pdf_source
  2. Parse student_identifier → (name_part, date_naissance)
  3. Cherche parmi les Students :
     a. DDN exacte  → candidats
     b. Si 1 candidat unique → match direct
     c. Si plusieurs → meilleur score de similarité nom+prénom
     d. Si 0 → copie reste non identifiée (warning)
  4. Met à jour copy.student, copy.is_identified=True

Idempotent : saute les copies déjà identifiées.

Usage :
    python manage.py identify_dnb_copies
    python manage.py identify_dnb_copies --dry-run
    python manage.py identify_dnb_copies --min-score 0.7
    python manage.py identify_dnb_copies --exam DNB_2026
"""

import datetime
import re
import unicodedata
from difflib import SequenceMatcher

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


def _normalize(s: str) -> str:
    """Uppercase, strip accents, replace spaces/hyphens/dots with _, collapse __."""
    s = s.upper().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[\s\-\.]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def _lcs_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _best_match(name_part: str, candidates) -> tuple:
    """Return (best_student, score) among candidates."""
    norm = _normalize(name_part)
    best, best_score = None, -1.0
    for s in candidates:
        n1 = _normalize(f"{s.last_name}_{s.first_name}")
        n2 = _normalize(f"{s.first_name}_{s.last_name}")
        score = max(_lcs_ratio(norm, n1), _lcs_ratio(norm, n2))
        if score > best_score:
            best_score = score
            best = s
    return best, best_score


def _parse_identifier(identifier: str):
    """
    Parse NOM_PRENOM_DDMMYYYY → (name_part, date_naissance) or (name_part, None).
    identifier = ExamPDF.student_identifier, e.g. 'ABBES_MYRIAM_03122010'
    """
    m = re.search(r"^(.+)_(\d{8})$", identifier)
    if not m:
        return identifier, None
    name_part = m.group(1)
    ddn_str = m.group(2)  # DDMMYYYY
    try:
        ddn = datetime.date(
            int(ddn_str[4:8]),
            int(ddn_str[2:4]),
            int(ddn_str[0:2]),
        )
    except ValueError:
        return name_part, None
    return name_part, ddn


class Command(BaseCommand):
    help = (
        "Identifie les copies DNB_2026 non-identifiées en croisant "
        "ExamPDF.student_identifier avec la table Student."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--exam",
            default="DNB_2026",
            help="Nom de l'examen (défaut : DNB_2026)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simule sans écrire en base.",
        )
        parser.add_argument(
            "--min-score",
            type=float,
            default=0.65,
            help="Score minimal de similarité pour accepter un match (défaut : 0.65).",
        )

    def handle(self, *args, **options):
        from exams.models import Copy, Exam, ExamPDF
        from students.models import Student

        dry_run = options["dry_run"]
        exam_name = options["exam"]
        min_score = options["min_score"]

        if dry_run:
            self.stdout.write(self.style.WARNING("=== MODE DRY-RUN — aucune écriture ===\n"))

        # Get exam
        try:
            exam = Exam.objects.get(name=exam_name)
        except Exam.DoesNotExist:
            raise CommandError(f"Examen '{exam_name}' introuvable.")

        self.stdout.write(f"Examen : {exam.name} (id={exam.id})")

        # Unidentified copies
        copies = Copy.objects.filter(
            exam=exam,
            is_identified=False,
            student__isnull=True,
        ).select_related("student")

        total = copies.count()
        self.stdout.write(f"Copies non identifiées : {total}")

        if total == 0:
            self.stdout.write(self.style.SUCCESS("Toutes les copies sont déjà identifiées."))
            return

        # Build student DDN index for fast lookup
        student_by_ddn: dict[datetime.date, list] = {}
        for s in Student.objects.all():
            student_by_ddn.setdefault(s.date_naissance, []).append(s)

        self.stdout.write(f"Élèves en base : {Student.objects.count()}")

        # Build ExamPDF lookup: pdf_file path → student_identifier
        exam_pdf_map = {
            str(ep.pdf_file): ep.student_identifier
            for ep in ExamPDF.objects.filter(exam=exam)
        }
        self.stdout.write(f"ExamPDFs trouvés : {len(exam_pdf_map)}")

        stats = {
            "identified": 0,
            "ambiguous": 0,
            "no_match": 0,
            "no_examPDF": 0,
            "errors": 0,
        }
        unmatched: list[str] = []

        for copy in copies:
            pdf_path = str(copy.pdf_source) if copy.pdf_source else None

            if not pdf_path:
                self.stdout.write(
                    self.style.WARNING(f"  [NO PDF] Copy {copy.anonymous_id} — pdf_source vide")
                )
                stats["no_examPDF"] += 1
                continue

            identifier = exam_pdf_map.get(pdf_path)
            if not identifier:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [NO EXAM_PDF] Copy {copy.anonymous_id} — "
                        f"aucun ExamPDF pour '{pdf_path}'"
                    )
                )
                stats["no_examPDF"] += 1
                continue

            name_part, ddn = _parse_identifier(identifier)
            if ddn is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [PARSE ERR] Copy {copy.anonymous_id} — "
                        f"impossible de parser '{identifier}'"
                    )
                )
                stats["errors"] += 1
                continue

            # Match student
            candidates = student_by_ddn.get(ddn, [])
            student = None
            id_method = ""

            if len(candidates) == 1:
                student = candidates[0]
                id_method = "DDN unique"
            elif len(candidates) > 1:
                best, score = _best_match(name_part, candidates)
                if score >= min_score:
                    student = best
                    id_method = f"fuzzy ({score:.2f})"
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  [AMBIGU] {identifier} — meilleur score {score:.2f} < {min_score} "
                            f"({best}) → non identifiée"
                        )
                    )
                    stats["ambiguous"] += 1
                    unmatched.append(identifier)
                    continue
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [NO MATCH] {identifier} (DDN {ddn}) → 0 élève en base"
                    )
                )
                stats["no_match"] += 1
                unmatched.append(identifier)
                continue

            # Apply identification
            if dry_run:
                self.stdout.write(
                    f"  [DRY] {copy.anonymous_id} ← {student} ({id_method})"
                )
                stats["identified"] += 1
                continue

            try:
                with transaction.atomic():
                    copy.student = student
                    copy.is_identified = True
                    copy.save(update_fields=["student", "is_identified"])
                stats["identified"] += 1
                self.stdout.write(
                    f"  ✓ {copy.anonymous_id} ← {student} ({id_method})"
                )
            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ {copy.anonymous_id} — ERREUR : {exc}")
                )
                stats["errors"] += 1

        # Summary
        self.stdout.write("\n" + self.style.SUCCESS("─" * 60))
        self.stdout.write(self.style.SUCCESS(f"Identifiées         : {stats['identified']} / {total}"))
        if stats["no_match"]:
            self.stdout.write(
                self.style.WARNING(f"Aucun élève trouvé  : {stats['no_match']}")
            )
        if stats["ambiguous"]:
            self.stdout.write(
                self.style.WARNING(f"Ambiguïté (score<{min_score}) : {stats['ambiguous']}")
            )
        if stats["no_examPDF"]:
            self.stdout.write(
                self.style.WARNING(f"ExamPDF manquant    : {stats['no_examPDF']}")
            )
        if stats["errors"]:
            self.stdout.write(self.style.ERROR(f"Erreurs             : {stats['errors']}"))
        if unmatched:
            self.stdout.write(self.style.WARNING("\nCopies non identifiées :"))
            for u in unmatched:
                self.stdout.write(f"  - {u}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN : aucune modification en base."))
