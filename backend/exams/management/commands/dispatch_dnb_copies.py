"""
Management command: dispatch_dnb_copies
=========================================
Distribue les copies du DNB BLANC MATHS 2026 aux correcteurs en respectant
deux niveaux de contraintes métier :

  Niveau 1 — Contrainte classe/enseignant (CSV) :
    Un correcteur ne doit pas corriger la copie d'un élève dont il est
    le professeur de classe.  La table de correspondance est lue depuis
    scan_DNB_maths/classes_troisieme.csv.

  Niveau 2 — Contrainte individuelle spéciale :
    Kamel BEN RHOUMA (26/06/2011, classe 3.5) ne doit pas être dispatché
    vers bentiba, saadi, ni nasri (même si certains ne sont pas correcteurs
    dans le système).

Algorithme :
    Pour chaque copie non assignée (status READY ou STAGING) :
      - Si la copie est identifiée (is_identified=True) : on connaît la
        classe de l'élève → on exclut le(s) professeur(s) de cette classe.
      - On applique en plus la liste de contraintes individuelles.
      - Parmi les correcteurs éligibles, on choisit celui qui a le moins
        de copies assignées pour cet examen (load-balancing greedy).
      - Si AUCUN correcteur n'est éligible (cas extrême), la copie reste
        non assignée et un avertissement est émis.

Usage :
    python manage.py dispatch_dnb_copies
    python manage.py dispatch_dnb_copies --dry-run
    python manage.py dispatch_dnb_copies --exam-id <uuid>
    python manage.py dispatch_dnb_copies --force-unidentified
        (dispatch aussi les copies non identifiées, sans contrainte de classe)
"""

import csv
import datetime
import logging
import uuid as uuid_module
from collections import defaultdict
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[4]
DNB_DIR = PROJECT_ROOT / "scan_DNB_maths"
CLASSES_CSV = DNB_DIR / "classes_troisieme.csv"
ENSEIGNANTS_CSV = PROJECT_ROOT / "enseignants.csv"

DNB_EXAM_TYPE_CODE = "DNBM2026"
DNB_EXAM_NAME = "DNB_2026"  # un seul examen, pas de sujet A/B contrairement à BBM2026

# ── Contraintes individuelles spéciales ──────────────────────────────────────
# Format : (last_name_upper, first_name_upper, date_naissance_DD/MM/YYYY)
#              → liste d'emails de correcteurs interdits
INDIVIDUAL_CONSTRAINTS: dict[tuple, list[str]] = {
    ("BEN RHOUMA", "KAMEL", "26/06/2011"): [
        "sami.bentiba@ert.tn",
        "chawki.saadi@ert.tn",
        "soumaya.nasri@ert.tn",
    ],
}


class Command(BaseCommand):
    help = (
        "Dispatch des copies DNB BLANC MATHS 2026 avec contraintes "
        "classe-enseignant et contraintes individuelles spéciales."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--exam-id",
            default=None,
            help="UUID de l'examen (facultatif, utilise DNB BLANC MATHS 2026 par défaut).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simule le dispatch sans écrire en base.",
        )
        parser.add_argument(
            "--force-unidentified",
            action="store_true",
            help=(
                "Inclut les copies non identifiées (sans contrainte de classe). "
                "Par défaut, seules les copies identifiées sont dispatchées avec contraintes."
            ),
        )

    # ── Main ─────────────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        from exams.models import Copy, Exam

        dry_run = options["dry_run"]
        force_unidentified = options["force_unidentified"]

        if dry_run:
            self.stdout.write(self.style.WARNING("=== MODE DRY-RUN — aucune écriture en base ===\n"))

        # 1. Resolve exam
        exam = self._get_exam(options["exam_id"])
        self.stdout.write(f"Examen cible : {exam.name} (id={exam.id})")

        # 2. Load constraint tables
        class_teacher_map = self._load_class_teacher_map()
        self.stdout.write(f"Table classe→enseignant : {len(class_teacher_map)} classes chargées")

        # 3. Resolve correctors (those registered on this exam)
        correctors = list(exam.correctors.all())
        if not correctors:
            raise CommandError(
                "Aucun correcteur enregistré sur cet examen. "
                "Lancez d'abord : python manage.py setup_dnb_exam"
            )
        corrector_emails = {u.email.lower(): u for u in correctors}
        corrector_usernames = {u.username.lower(): u for u in correctors}
        self.stdout.write(
            f"Correcteurs ({len(correctors)}) : "
            + ", ".join(u.username for u in correctors)
        )

        # 4. Current load per corrector for this exam
        load: dict[int, int] = defaultdict(int)
        for c in correctors:
            load[c.id] = Copy.objects.filter(
                exam=exam, assigned_corrector=c
            ).count()

        # 5. Get unassigned copies
        unassigned = list(
            Copy.objects.filter(
                exam=exam,
                assigned_corrector__isnull=True,
                status__in=[Copy.Status.READY, Copy.Status.STAGING],
            )
            .select_related("student")
            .order_by("anonymous_id")
        )

        if not unassigned:
            self.stdout.write(self.style.SUCCESS("Aucune copie à dispatcher."))
            return

        self.stdout.write(f"\nCopies à dispatcher : {len(unassigned)}")
        identified = [c for c in unassigned if c.is_identified and c.student]
        unidentified = [c for c in unassigned if not (c.is_identified and c.student)]
        self.stdout.write(f"  → identifiées    : {len(identified)}")
        self.stdout.write(f"  → non identifiées : {len(unidentified)}")

        if unidentified and not force_unidentified:
            self.stdout.write(
                self.style.WARNING(
                    f"\n  {len(unidentified)} copies non identifiées ignorées. "
                    "Utilisez --force-unidentified pour les inclure sans contrainte de classe."
                )
            )

        # 6. Build dispatch list
        to_dispatch = identified[:]
        if force_unidentified:
            to_dispatch += unidentified

        assignments: list[tuple[Copy, User]] = []
        skipped: list[tuple[Copy, str]] = []

        for copy in to_dispatch:
            eligible = list(correctors)

            # — Contrainte de classe (only for identified copies) —
            if copy.is_identified and copy.student:
                student_class = copy.student.class_name
                forbidden_by_class = class_teacher_map.get(student_class, [])
                eligible = [
                    c for c in eligible
                    if c.email.lower() not in forbidden_by_class
                    and c.username.lower() not in forbidden_by_class
                ]
                if len(eligible) < len(correctors):
                    excluded = [e for e in forbidden_by_class if e in corrector_emails or e in corrector_usernames]
                    self.stdout.write(
                        f"  {copy.anonymous_id} ({copy.student}) "
                        f"classe {student_class} → exclus pour classe : {excluded}"
                    )

            # — Contrainte individuelle spéciale —
            if copy.is_identified and copy.student:
                s = copy.student
                ddn_str = s.date_naissance.strftime("%d/%m/%Y")
                individual_key = (s.last_name.upper(), s.first_name.upper(), ddn_str)
                extra_forbidden = INDIVIDUAL_CONSTRAINTS.get(individual_key, [])
                if extra_forbidden:
                    eligible_before = len(eligible)
                    eligible = [
                        c for c in eligible
                        if c.email.lower() not in extra_forbidden
                        and c.username.lower() not in extra_forbidden
                    ]
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠  CONTRAINTE SPÉCIALE : {s.last_name} {s.first_name} "
                            f"({ddn_str}) → exclus : {extra_forbidden} "
                            f"({eligible_before - len(eligible)} correcteur(s) en plus exclus)"
                        )
                    )

            if not eligible:
                reason = (
                    f"Aucun correcteur éligible pour {copy.anonymous_id} "
                    f"(étudiant : {copy.student if copy.student else 'non identifié'})"
                )
                self.stdout.write(self.style.ERROR(f"  ✗ {reason}"))
                skipped.append((copy, reason))
                continue

            # — Load-balancing greedy : choisir le correcteur le moins chargé —
            chosen = min(eligible, key=lambda c: load[c.id])
            assignments.append((copy, chosen))
            load[chosen.id] += 1

        # 7. Apply (or simulate) assignments
        if not assignments:
            self.stdout.write(self.style.WARNING("\nAucun dispatch effectué."))
            return

        run_id = uuid_module.uuid4()
        now = timezone.now()

        self.stdout.write(f"\nRun ID : {run_id}")
        self.stdout.write(f"Affectations prévues : {len(assignments)}")

        # Distribution preview
        dist: dict[str, int] = defaultdict(int)
        for _, corrector in assignments:
            dist[corrector.username] += 1
        for username, count in sorted(dist.items()):
            self.stdout.write(f"  {username:40s} : {count} copie(s)")

        if skipped:
            self.stdout.write(
                self.style.WARNING(f"\n  {len(skipped)} copie(s) non dispatchée(s) :")
            )
            for copy, reason in skipped:
                self.stdout.write(f"    - {copy.anonymous_id} : {reason}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY-RUN : aucune écriture en base."))
            return

        # Persist
        copies_to_update = []
        for copy, corrector in assignments:
            copy.assigned_corrector = corrector
            copy.dispatch_run_id = run_id
            copy.assigned_at = now
            copies_to_update.append(copy)

        with transaction.atomic():
            Copy.objects.bulk_update(
                copies_to_update,
                ["assigned_corrector", "dispatch_run_id", "assigned_at"],
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Dispatch terminé : {len(copies_to_update)} copies assignées "
                f"(run_id={run_id})"
            )
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_exam(self, exam_id_str):
        from exams.models import Exam

        if exam_id_str:
            try:
                return Exam.objects.get(id=exam_id_str)
            except Exam.DoesNotExist:
                raise CommandError(f"Examen introuvable : {exam_id_str}")

        exam = Exam.objects.filter(
            exam_type__code=DNB_EXAM_TYPE_CODE,
            name=DNB_EXAM_NAME,
        ).first()
        if not exam:
            raise CommandError(
                f"Examen '{DNB_EXAM_NAME}' introuvable. "
                "Lancez d'abord : python manage.py setup_dnb_exam"
            )
        return exam

    def _load_class_teacher_map(self) -> dict[str, list[str]]:
        """
        Parse classes_troisieme.csv and return {class_name: [teacher_email, ...]}
        The values are lowercase emails/usernames for case-insensitive matching.
        """
        if not CLASSES_CSV.exists():
            self.stdout.write(
                self.style.WARNING(f"classes_troisieme.csv introuvable : {CLASSES_CSV}")
            )
            return {}

        result: dict[str, list[str]] = {}
        with open(CLASSES_CSV, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                classe = row.get("Classe", "").strip()
                mail = row.get("Mail", "").strip().lower()
                if classe and mail:
                    result.setdefault(classe, []).append(mail)

        self.stdout.write("  Correspondances classe → enseignant :")
        for cls, teachers in sorted(result.items()):
            self.stdout.write(f"    {cls:6s} → {', '.join(teachers)}")

        return result
