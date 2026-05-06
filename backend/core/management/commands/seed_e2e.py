"""
Management command: seed_e2e
============================
Deterministic, idempotent E2E seed used by Playwright tests.

This command is safe by default: it refuses to run unless `E2E_TEST_MODE=true`
is set in the environment (prevents accidental execution on production DBs).
"""

from __future__ import annotations

import os
import shutil
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.auth import UserRole
from core.models import UserProfile
from exams.models import Exam, ExamType, Booklet, Copy, TeacherGroupAssignment
from grading.models import Annotation, GradingEvent, QuestionRemark, Score
from students.models import Student

User = get_user_model()


# ─────────────────────────────── E2E Contract ────────────────────────────────

E2E_ADMIN_USERNAME = os.environ.get("E2E_ADMIN_USERNAME", "admin")
E2E_ADMIN_PASSWORD = os.environ.get("E2E_ADMIN_PASSWORD", "admin")

E2E_TEACHER_USERNAME = os.environ.get("E2E_TEACHER_USERNAME", "prof1")
E2E_TEACHER_PASSWORD = os.environ.get("E2E_TEACHER_PASSWORD", "password")

E2E_STUDENT_DOB = os.environ.get("E2E_STUDENT_DOB", "2005-03-15")
E2E_STUDENT_LASTNAME = os.environ.get("E2E_STUDENT_LASTNAME", "E2E_STUDENT")
E2E_STUDENT_FIRSTNAME = os.environ.get("E2E_STUDENT_FIRSTNAME", "Jean")
E2E_STUDENT_EMAIL = os.environ.get("E2E_STUDENT_EMAIL", "eleve.test-e@ert.tn")
E2E_STUDENT_PASSWORD = os.environ.get("E2E_STUDENT_PASS", "15032005")

E2E_SEED_TAG = "[E2E-SEED]"
E2E_EXAM_PREFIX = f"{E2E_SEED_TAG} Exam"
E2E_EXAM_TYPE_CODE = "E2E_MATH"
E2E_EXAM_TYPE_NAME = "E2E Mathématiques"

E2E_GROUP_NAME = os.environ.get("E2E_GROUP_NAME", "G3")
E2E_CLASS_NAME = os.environ.get("E2E_CLASS_NAME", "T.01")


# ─────────────────────────────── PNG Helpers ─────────────────────────────────

E2E_IMAGE_WIDTH = 1000
E2E_IMAGE_HEIGHT = 1414

MIN_PNG_SIZE_PILLOW = 5000
MIN_PNG_SIZE_FALLBACK = 60

_PILLOW_AVAILABLE: bool | None = None


def _check_pillow() -> bool:
    global _PILLOW_AVAILABLE
    if _PILLOW_AVAILABLE is None:
        try:
            from PIL import Image  # noqa: F401
            _PILLOW_AVAILABLE = True
        except ImportError:
            _PILLOW_AVAILABLE = False
    return bool(_PILLOW_AVAILABLE)


def _png_bytes_page() -> bytes:
    """
    Generates a valid PNG for Canvas/PDF viewer tests.
    Uses Pillow when available for a realistic page size, else falls back to a tiny 1x1 PNG.
    """
    if _check_pillow():
        from PIL import Image, ImageDraw
        import io

        img = Image.new("RGB", (E2E_IMAGE_WIDTH, E2E_IMAGE_HEIGHT), color="white")
        draw = ImageDraw.Draw(img)
        draw.rectangle(
            [(10, 10), (E2E_IMAGE_WIDTH - 10, E2E_IMAGE_HEIGHT - 10)],
            outline="lightgray",
            width=2,
        )
        draw.line([(0, 0), (E2E_IMAGE_WIDTH, E2E_IMAGE_HEIGHT)], fill="lightgray", width=1)
        draw.line([(E2E_IMAGE_WIDTH, 0), (0, E2E_IMAGE_HEIGHT)], fill="lightgray", width=1)

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()

    # Fallback: minimal PNG 1x1
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc`\x00\x00"
        b"\x00\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def _cleanup_e2e_media() -> None:
    media_root = Path(settings.MEDIA_ROOT)
    e2e_dir = media_root / "e2e"
    if e2e_dir.exists():
        shutil.rmtree(e2e_dir)


def _save_page_image(page_num: int) -> str:
    """
    Writes a PNG into MEDIA_ROOT and returns the relative path (for pages_images[]).
    """
    media_root = Path(settings.MEDIA_ROOT)
    pages_dir = media_root / "e2e" / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    filename = f"e2e_page_{page_num}.png"
    filepath = pages_dir / filename
    filepath.write_bytes(_png_bytes_page())

    actual_size = filepath.stat().st_size
    min_expected = MIN_PNG_SIZE_PILLOW if _check_pillow() else MIN_PNG_SIZE_FALLBACK
    if actual_size < min_expected:
        raise RuntimeError(
            f"PNG file suspiciously small: {actual_size} bytes (expected >= {min_expected})."
        )

    return f"e2e/pages/{filename}"


# ─────────────────────────────── Seed Logic ──────────────────────────────────


def _ensure_admin() -> User:
    admins, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
    teachers, _ = Group.objects.get_or_create(name=UserRole.TEACHER)

    user, created = User.objects.get_or_create(
        username=E2E_ADMIN_USERNAME,
        defaults={"email": "e2e-admin@example.com"},
    )
    if created:
        user.set_password(E2E_ADMIN_PASSWORD)
    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    user.save()
    user.groups.add(admins)
    user.groups.add(teachers)

    # For E2E, keep admin usable without blocking overlays (student flow is tested separately).
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.must_change_password = False
    profile.save(update_fields=["must_change_password"])

    return user


def _ensure_teacher() -> User:
    teachers, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
    user, created = User.objects.get_or_create(
        username=E2E_TEACHER_USERNAME,
        defaults={"email": f"{E2E_TEACHER_USERNAME}@example.com"},
    )
    if created:
        user.set_password(E2E_TEACHER_PASSWORD)
    user.is_staff = False
    user.is_superuser = False
    user.is_active = True
    user.save()
    user.groups.add(teachers)
    return user


def _ensure_student() -> Student:
    students, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
    user, created = User.objects.get_or_create(
        username=E2E_STUDENT_EMAIL,
        defaults={"email": E2E_STUDENT_EMAIL},
    )
    if created:
        user.set_password(E2E_STUDENT_PASSWORD)
    user.is_active = True
    user.save()
    user.groups.add(students)

    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.must_change_password = True
    profile.save(update_fields=["must_change_password"])

    student, _ = Student.objects.update_or_create(
        first_name=E2E_STUDENT_FIRSTNAME,
        last_name=E2E_STUDENT_LASTNAME,
        date_naissance=E2E_STUDENT_DOB,
        defaults={
            "user": user,
            "email": E2E_STUDENT_EMAIL,
            "class_name": E2E_CLASS_NAME,
            "groupe": E2E_GROUP_NAME,
        },
    )
    return student


def seed_e2e() -> dict:
    """
    Run the deterministic seed inside a transaction.
    """
    teacher = _ensure_teacher()
    _ensure_admin()
    student = _ensure_student()

    # Clean previous seed data (idempotence)
    _cleanup_e2e_media()

    TeacherGroupAssignment.objects.filter(
        teacher=teacher,
        group_name=E2E_GROUP_NAME,
        level="terminale",
    ).delete()

    TeacherGroupAssignment.objects.create(
        teacher=teacher,
        level="terminale",
        assignment_type="groupe",
        group_name=E2E_GROUP_NAME,
    )

    exam_type, _ = ExamType.objects.update_or_create(
        code=E2E_EXAM_TYPE_CODE,
        defaults={
            "name": E2E_EXAM_TYPE_NAME,
            "description": "Type d'examen dédié aux tests E2E",
            "color": "#2563eb",
            "icon": "graduation-cap",
            "is_active": True,
            "sort_order": -100,
        },
    )

    # Delete any prior E2E exams (and cascade to copies/booklets)
    Exam.objects.filter(name__contains=E2E_SEED_TAG).delete()
    Copy.objects.filter(anonymous_id__in=["E2E-READY", "E2E-FINALIZED", "E2E-OTHER"]).delete()

    exam = Exam.objects.create(
        name=f"{E2E_EXAM_PREFIX} {timezone.now().strftime('%Y%m%d-%H%M%S')}",
        date=timezone.now().date(),
        exam_type=exam_type,
        results_released_at=timezone.now() - timedelta(days=1),
        grading_structure=[
            {"id": "q1", "label": "Question 1", "points": 12},
            {"id": "q2", "label": "Question 2", "points": 8},
        ],
    )
    exam.correctors.add(teacher)

    page_image_1 = _save_page_image(1)
    booklet_1 = Booklet.objects.create(exam=exam, start_page=1, end_page=1, pages_images=[page_image_1])

    ready_copy = Copy.objects.create(
        exam=exam,
        anonymous_id="E2E-READY",
        status=Copy.Status.READY,
        is_identified=False,
        assigned_corrector=teacher,
    )
    ready_copy.booklets.add(booklet_1)

    GradingEvent.objects.get_or_create(
        copy=ready_copy,
        action=GradingEvent.Action.IMPORT if hasattr(GradingEvent.Action, "IMPORT") else "IMPORT",
        defaults={"actor": teacher, "metadata": {"seed": True, "e2e": True}},
    )

    # Other student for cross-student security checks
    other_user, _ = User.objects.get_or_create(username="other_student", defaults={"email": "other@example.com"})
    other_student, _ = Student.objects.get_or_create(
        first_name="Student",
        last_name="OTHER",
        date_naissance="2005-05-20",
        defaults={"user": other_user, "class_name": "TG1"},
    )
    Copy.objects.create(
        exam=exam,
        anonymous_id="E2E-OTHER",
        status=Copy.Status.READY,
        is_identified=True,
        student=other_student,
    )

    page_image_2 = _save_page_image(2)
    booklet_2 = Booklet.objects.create(exam=exam, start_page=2, end_page=2, pages_images=[page_image_2])

    finalized_copy = Copy.objects.create(
        exam=exam,
        anonymous_id="E2E-FINALIZED",
        status=Copy.Status.FINALIZED,
        is_identified=True,
        student=student,
        assigned_corrector=teacher,
        graded_at=timezone.now(),
        global_appreciation="Copie solide et bien structurée.",
        llm_summary="Bonne maîtrise globale avec quelques imprécisions mineures.",
    )
    finalized_copy.booklets.add(booklet_2)

    Score.objects.update_or_create(
        copy=finalized_copy,
        defaults={"scores_data": {"q1": 9, "q2": 6}, "final_comment": "Bon travail dans l'ensemble."},
    )
    QuestionRemark.objects.update_or_create(
        copy=finalized_copy,
        question_id="q1",
        defaults={"remark": "Méthode correcte, résultat à sécuriser.", "created_by": teacher},
    )
    Annotation.objects.create(
        copy=finalized_copy,
        page_index=0,
        x=0.2,
        y=0.3,
        w=0.2,
        h=0.08,
        content="Bon raisonnement",
        type=Annotation.Type.COMMENTAIRE,
        created_by=teacher,
    )

    return {
        "teacher": teacher.username,
        "student": student.email,
        "exam": str(exam.id),
        "ready_copy": str(ready_copy.id),
        "finalized_copy": str(finalized_copy.id),
    }


class Command(BaseCommand):
    help = "Seed deterministic E2E data (requires E2E_TEST_MODE=true)"

    def handle(self, *args, **options):
        if os.environ.get("E2E_TEST_MODE") != "true":
            raise CommandError(
                "E2E_TEST_MODE must be set to 'true' to run this seed. "
                "This is a hard safety guard."
            )

        with transaction.atomic():
            out = seed_e2e()

        self.stdout.write(self.style.SUCCESS("✅ E2E Seed completed successfully"))
        self.stdout.write(f"  Teacher: {out['teacher']}")
        self.stdout.write(f"  Student: {out['student']}")
        self.stdout.write(f"  Exam: {out['exam']}")
        self.stdout.write(f"  Copy READY: {out['ready_copy']}")
        self.stdout.write(f"  Copy FINALIZED: {out['finalized_copy']}")
