from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from exams.models import Copy, Exam
from grading.models import PeerReviewCorrection, PeerReviewEvent


EXAM_ID = "4c9dfd06-72fc-47b4-ad11-b63dba655076"
EXAM_NAME = "Produit scalaire- 1 EDS G6"
SUPERVISING_TEACHER_EMAIL = "alaeddine.benrhouma@ert.tn"


class Command(BaseCommand):
    help = "Create idempotent peer-review assignments for Produit scalaire- 1 EDS G6."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Only print planned assignments.")
        parser.add_argument("--exam-id", default=EXAM_ID, help="Exam UUID to process.")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        exam = self._get_exam(options["exam_id"])
        copies = list(
            Copy.objects.filter(exam=exam)
            .select_related("student", "student__user")
            .order_by("anonymous_id")
        )
        self._validate_exam(exam, copies)

        teacher = self._get_supervising_teacher(exam)
        assignments = self._build_assignments(copies)
        existing_count = PeerReviewCorrection.objects.filter(exam=exam).count()
        created_count = 0

        self.stdout.write(f"Examen détecté : {exam.name}")
        self.stdout.write(f"Exam ID : {exam.id}")
        self.stdout.write(f"Copies détectées : {len(copies)}")
        self.stdout.write(f"Élèves détectés : {len({c.student_id for c in copies})}")
        self.stdout.write(f"Corrections participatives existantes : {existing_count}")
        self.stdout.write("Affectations :")

        for source_copy, assigned_student in assignments:
            marker = "existe" if PeerReviewCorrection.objects.filter(exam=exam, source_copy=source_copy).exists() else "à créer"
            self.stdout.write(
                f"- {source_copy.anonymous_id} -> élève correcteur : "
                f"{assigned_student.id} ({marker})"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry-run uniquement : aucune correction participative créée."))
            return

        with transaction.atomic():
            for source_copy, assigned_student in assignments:
                peer_review, created = PeerReviewCorrection.objects.get_or_create(
                    exam=exam,
                    source_copy=source_copy,
                    defaults={
                        "assigned_student": assigned_student,
                        "assigned_user": assigned_student.user,
                        "supervising_teacher": teacher,
                    },
                )
                if created:
                    created_count += 1
                    PeerReviewEvent.objects.create(
                        peer_review=peer_review,
                        actor=teacher,
                        action=PeerReviewEvent.Action.CREATE,
                        metadata={"command": "create_peer_review_produit_scalaire_g6"},
                    )
                else:
                    if peer_review.assigned_student_id != assigned_student.id:
                        raise CommandError(
                            "Correction participative existante avec affectation différente "
                            f"pour {source_copy.anonymous_id}; arrêt sans écraser."
                        )

        self.stdout.write(f"Corrections participatives créées : {created_count}")
        self.stdout.write(self.style.SUCCESS("Création terminée sans modifier les corrections officielles."))

    def _get_exam(self, exam_id):
        exam = Exam.objects.filter(id=exam_id).first()
        if not exam:
            exam = Exam.objects.filter(name=EXAM_NAME).first()
        if not exam:
            raise CommandError(f"Examen introuvable: {EXAM_NAME} / {exam_id}")
        return exam

    def _get_supervising_teacher(self, exam):
        user_model = get_user_model()
        teacher = user_model.objects.filter(email__iexact=SUPERVISING_TEACHER_EMAIL).first()
        if not teacher:
            raise CommandError(f"Correcteur superviseur introuvable: {SUPERVISING_TEACHER_EMAIL}")
        if not exam.correctors.filter(id=teacher.id).exists():
            raise CommandError(f"{SUPERVISING_TEACHER_EMAIL} n'est pas correcteur de cet examen.")
        return teacher

    def _validate_exam(self, exam, copies):
        if exam.name != EXAM_NAME:
            raise CommandError(f"Nom d'examen inattendu: {exam.name!r}")
        if len(copies) != 23:
            raise CommandError(f"Nombre de copies inattendu: {len(copies)} au lieu de 23.")
        if not exam.grading_structure:
            raise CommandError("Barème absent.")
        missing_students = [copy.anonymous_id for copy in copies if not copy.student_id]
        if missing_students:
            raise CommandError(f"Copies sans élève: {missing_students}")
        missing_users = [copy.anonymous_id for copy in copies if not copy.student or not copy.student.user_id]
        if missing_users:
            raise CommandError(f"Copies avec élève sans compte utilisateur: {missing_users}")
        distinct_students = {copy.student_id for copy in copies}
        if len(distinct_students) != len(copies):
            raise CommandError("Le nombre d'élèves distincts ne correspond pas au nombre de copies.")
        if not exam.correctors.exists():
            raise CommandError("Aucun correcteur officiel présent sur l'examen.")

    def _build_assignments(self, copies):
        assignments = []
        students = [copy.student for copy in copies]
        shifted_students = students[1:] + students[:1]
        for source_copy, assigned_student in zip(copies, shifted_students):
            if source_copy.student_id == assigned_student.id:
                raise CommandError(f"Auto-attribution détectée pour {source_copy.anonymous_id}.")
            assignments.append((source_copy, assigned_student))
        return assignments
