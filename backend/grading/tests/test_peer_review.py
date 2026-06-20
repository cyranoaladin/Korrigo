from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase, Client
from django.test import override_settings
from django.utils import timezone

from core.auth import UserRole
from core.views_media import ProtectedMediaView
from exams.models import Booklet, Copy, Exam
from grading.models import Annotation, PeerReviewAnnotation, PeerReviewCorrection, QuestionRemark, Score
from students.models import Student


User = get_user_model()


class PeerReviewTestCase(TestCase):
    def setUp(self):
        student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
        teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)

        self.teacher = User.objects.create_user(
            username="teacher.peer",
            email="teacher.peer@example.test",
            password="pass",
        )
        self.teacher.groups.add(teacher_group)

        self.student_user = User.objects.create_user(
            username="student.a@example.test",
            email="student.a@example.test",
            password="pass",
        )
        self.student_user.groups.add(student_group)
        self.student = Student.objects.create(
            first_name="Alice",
            last_name="A",
            date_naissance=date(2010, 1, 1),
            email="student.a@example.test",
            class_name="1 EDS",
            groupe="G6",
            user=self.student_user,
        )

        self.author_user = User.objects.create_user(
            username="student.b@example.test",
            email="student.b@example.test",
            password="pass",
        )
        self.author_user.groups.add(student_group)
        self.author = Student.objects.create(
            first_name="Bob",
            last_name="B",
            date_naissance=date(2010, 2, 2),
            email="student.b@example.test",
            class_name="1 EDS",
            groupe="G6",
            user=self.author_user,
        )

        self.other_user = User.objects.create_user(
            username="student.c@example.test",
            email="student.c@example.test",
            password="pass",
        )
        self.other_user.groups.add(student_group)
        self.other_student = Student.objects.create(
            first_name="Charlie",
            last_name="C",
            date_naissance=date(2010, 3, 3),
            email="student.c@example.test",
            class_name="1 EDS",
            groupe="G6",
            user=self.other_user,
        )

        self.exam = Exam.objects.create(
            name="Produit scalaire- 1 EDS G6",
            date=date(2026, 5, 16),
            grading_structure=[
                {
                    "id": "ex1",
                    "label": "Exercice 1",
                    "children": [{"id": "q1", "label": "Q1", "points": 2}],
                }
            ],
        )
        self.exam.correctors.add(self.teacher)

        self.source_copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id="4C9D-001",
            status=Copy.Status.IN_PROGRESS,
            student=self.author,
            is_identified=True,
            assigned_corrector=self.teacher,
            global_appreciation="Official appreciation",
            pdf_source="exams/individual/BOB_B_02022010.pdf",
        )
        self.source_booklet = Booklet.objects.create(
            exam=self.exam,
            start_page=0,
            end_page=1,
            pages_images=[
                f"copies/pages/{self.source_copy.id}/p000.png",
                f"copies/pages/{self.source_copy.id}/p001.png",
            ],
        )
        self.source_copy.booklets.add(self.source_booklet)
        Score.objects.create(copy=self.source_copy, scores_data={"q1": 1.5}, final_comment="Official")
        Annotation.objects.create(
            copy=self.source_copy,
            page_index=0,
            x=0.1,
            y=0.1,
            w=0.2,
            h=0.2,
            content="Official annotation",
            type=Annotation.Type.COMMENTAIRE,
            created_by=self.teacher,
        )
        QuestionRemark.objects.create(
            copy=self.source_copy,
            question_id="q1",
            remark="Official remark",
            created_by=self.teacher,
        )

        self.peer_review = PeerReviewCorrection.objects.create(
            exam=self.exam,
            source_copy=self.source_copy,
            assigned_student=self.student,
            assigned_user=self.student_user,
            supervising_teacher=self.teacher,
        )

        other_copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id="4C9D-003",
            status=Copy.Status.READY,
            student=self.student,
            is_identified=True,
            assigned_corrector=self.teacher,
        )
        self.other_peer_review = PeerReviewCorrection.objects.create(
            exam=self.exam,
            source_copy=other_copy,
            assigned_student=self.other_student,
            assigned_user=self.other_user,
            supervising_teacher=self.teacher,
        )

        self.client = Client()
        self.media_tmp = TemporaryDirectory()
        self.addCleanup(self.media_tmp.cleanup)

    def login_student(self, user, student):
        self.client.force_login(user)
        session = self.client.session
        session["student_id"] = student.id
        session["role"] = "Student"
        session.save()

    def test_student_list_only_returns_assigned_peer_reviews_without_author_identity(self):
        self.login_student(self.student_user, self.student)

        response = self.client.get("/api/students/peer-reviews/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], str(self.peer_review.id))
        self.assertEqual(data[0]["anonymous_id"], "4C9D-001")
        self.assertNotIn("source_student", data[0])
        self.assertNotIn("student", data[0])
        self.assertNotIn("source_copy_student_id", data[0])
        serialized = str(data)
        self.assertNotIn("Bob", serialized)
        self.assertNotIn("student.b@example.test", serialized)

    def test_student_detail_uses_only_peer_review_anonymized_media(self):
        media_root = Path(self.media_tmp.name)
        anonymized_page = media_root / "peer_reviews" / "anonymized" / str(self.source_copy.id) / "p000.png"
        anonymized_page.parent.mkdir(parents=True, exist_ok=True)
        anonymized_page.write_bytes(b"fake anonymized png")
        raw_page = media_root / "copies" / "pages" / str(self.source_copy.id) / "p000.png"
        raw_page.parent.mkdir(parents=True, exist_ok=True)
        raw_page.write_bytes(b"raw page with identity")

        self.login_student(self.student_user, self.student)
        with override_settings(MEDIA_ROOT=str(media_root)):
            response = self.client.get(f"/api/students/peer-reviews/{self.peer_review.id}/")

        self.assertEqual(response.status_code, 200)
        media = response.json()["source_media"]
        self.assertEqual(len(media["pages"]), 1)
        serialized_media = str(media)
        self.assertIn("peer_reviews/anonymized", serialized_media)
        self.assertNotIn("copies/pages", serialized_media)
        self.assertIsNone(media["pdf_source_url"])
        self.assertIsNone(media["final_pdf_url"])
        self.assertNotIn("BOB_B_02022010", serialized_media)

    def test_student_media_permission_allows_only_peer_review_anonymized_pages(self):
        anonymized_path = f"peer_reviews/anonymized/{self.source_copy.id}/p000.png"
        raw_page_path = f"copies/pages/{self.source_copy.id}/p000.png"
        raw_pdf_path = "exams/individual/BOB_B_02022010.pdf"

        self.assertTrue(ProtectedMediaView._student_owns_file(self.student_user, anonymized_path))
        self.assertFalse(ProtectedMediaView._student_owns_file(self.student_user, raw_page_path))
        self.assertFalse(ProtectedMediaView._student_owns_file(self.student_user, raw_pdf_path))

    def test_student_cannot_open_unassigned_peer_review(self):
        self.login_student(self.student_user, self.student)

        response = self.client.get(f"/api/students/peer-reviews/{self.other_peer_review.id}/")

        self.assertEqual(response.status_code, 404)

    def test_student_save_writes_peer_review_only_and_not_official_tables(self):
        self.login_student(self.student_user, self.student)
        before_copy = Copy.objects.get(id=self.source_copy.id)
        before_score = Score.objects.get(copy=self.source_copy)
        official_annotations = Annotation.objects.filter(copy=self.source_copy).count()
        official_remarks = QuestionRemark.objects.filter(copy=self.source_copy).count()

        response = self.client.patch(
            f"/api/students/peer-reviews/{self.peer_review.id}/save/",
            data={
                "scores_data": {"q1": 2},
                "global_appreciation": "Peer appreciation",
                "final_comment": "Peer final comment",
                "remarks": [{"question_id": "q1", "remark": "Peer remark"}],
                "annotations": [
                    {
                        "page_index": 0,
                        "x": 0.2,
                        "y": 0.2,
                        "w": 0.1,
                        "h": 0.1,
                        "content": "Peer annotation",
                        "type": "COMMENTAIRE",
                    }
                ],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.peer_review.refresh_from_db()
        self.assertEqual(self.peer_review.status, PeerReviewCorrection.Status.IN_PROGRESS)
        self.assertEqual(self.peer_review.scores_data, {"q1": 2})
        self.assertEqual(self.peer_review.global_appreciation, "Peer appreciation")
        self.assertEqual(PeerReviewAnnotation.objects.filter(peer_review=self.peer_review).count(), 1)

        self.source_copy.refresh_from_db()
        self.assertEqual(self.source_copy.status, before_copy.status)
        self.assertEqual(self.source_copy.global_appreciation, before_copy.global_appreciation)
        self.assertEqual(Score.objects.get(copy=self.source_copy).scores_data, before_score.scores_data)
        self.assertEqual(Annotation.objects.filter(copy=self.source_copy).count(), official_annotations)
        self.assertEqual(QuestionRemark.objects.filter(copy=self.source_copy).count(), official_remarks)

    def test_student_cannot_modify_finalized_peer_review(self):
        self.login_student(self.student_user, self.student)
        self.peer_review.status = PeerReviewCorrection.Status.FINALIZED
        self.peer_review.finalized_at = timezone.now()
        self.peer_review.save(update_fields=["status", "finalized_at"])

        response = self.client.patch(
            f"/api/students/peer-reviews/{self.peer_review.id}/save/",
            data={"scores_data": {"q1": 2}},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_finalize_blocked_when_no_scores(self):
        """P0: finalize must reject peer reviews with empty scores_data."""
        self.login_student(self.student_user, self.student)
        self.assertEqual(self.peer_review.scores_data, {})

        response = self.client.post(
            f"/api/students/peer-reviews/{self.peer_review.id}/finalize/",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("aucune note", response.json()["detail"])
        self.peer_review.refresh_from_db()
        self.assertNotEqual(self.peer_review.status, PeerReviewCorrection.Status.FINALIZED)

    def test_finalize_idempotent_returns_400_on_second_call(self):
        self.login_student(self.student_user, self.student)
        # Must save scores before finalize is allowed
        self.peer_review.scores_data = {"q1": 1.5}
        self.peer_review.status = PeerReviewCorrection.Status.IN_PROGRESS
        self.peer_review.save()

        response = self.client.post(
            f"/api/students/peer-reviews/{self.peer_review.id}/finalize/",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.peer_review.refresh_from_db()
        self.assertEqual(self.peer_review.status, PeerReviewCorrection.Status.FINALIZED)
        self.assertIsNotNone(self.peer_review.finalized_at)

        response2 = self.client.post(
            f"/api/students/peer-reviews/{self.peer_review.id}/finalize/",
            content_type="application/json",
        )
        self.assertEqual(response2.status_code, 400)

    def test_save_coerces_string_scores_to_float(self):
        """P0: string scores from HTML inputs must be coerced to float."""
        self.login_student(self.student_user, self.student)

        response = self.client.patch(
            f"/api/students/peer-reviews/{self.peer_review.id}/save/",
            data={"scores_data": {"q1": "1.5"}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.peer_review.refresh_from_db()
        self.assertEqual(self.peer_review.scores_data, {"q1": 1.5})

    def test_save_rejects_non_numeric_string_scores(self):
        """P0: non-numeric strings should return 400, not 500."""
        self.login_student(self.student_user, self.student)

        response = self.client.patch(
            f"/api/students/peer-reviews/{self.peer_review.id}/save/",
            data={"scores_data": {"q1": "abc"}},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_supervising_teacher_sees_all_exam_peer_reviews(self):
        self.client.force_login(self.teacher)

        response = self.client.get(f"/api/grading/teacher/exams/{self.exam.id}/peer-reviews/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual({row["anonymous_id"] for row in data}, {"4C9D-001", "4C9D-003"})
        self.assertIn("assigned_student", data[0])


class PeerReviewCommandTestCase(TestCase):
    def setUp(self):
        student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
        teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
        self.teacher = User.objects.create_user(
            username="teacher.supervisor@example.test",
            email="teacher.supervisor@example.test",
            password="pass",
        )
        self.teacher.groups.add(teacher_group)
        self.exam = Exam.objects.create(
            id="4c9dfd06-72fc-47b4-ad11-b63dba655076",
            name="Produit scalaire- 1 EDS G6",
            date=date(2026, 5, 16),
            grading_structure=[
                {
                    "id": "ex1",
                    "label": "Exercice 1",
                    "children": [{"id": "q1", "label": "Q1", "points": 20}],
                }
            ],
        )
        self.exam.correctors.add(self.teacher)

        for idx in range(23):
            user = User.objects.create_user(
                username=f"student{idx}@example.test",
                email=f"student{idx}@example.test",
                password="pass",
            )
            user.groups.add(student_group)
            student = Student.objects.create(
                first_name=f"First{idx}",
                last_name=f"Last{idx}",
                date_naissance=date(2010, 1, min(idx + 1, 28)),
                email=f"student{idx}@example.test",
                class_name="1 EDS",
                groupe="G6",
                user=user,
            )
            Copy.objects.create(
                exam=self.exam,
                anonymous_id=f"4C9D-{idx * 2 + 1:03d}",
                status=Copy.Status.READY,
                student=student,
                is_identified=True,
                assigned_corrector=self.teacher,
            )

    def test_command_dry_run_creates_nothing_then_real_run_is_idempotent(self):
        call_command(
            "create_peer_review_produit_scalaire_g6",
            "--dry-run",
            supervising_teacher_email=self.teacher.email,
        )
        self.assertEqual(PeerReviewCorrection.objects.filter(exam=self.exam).count(), 0)

        call_command(
            "create_peer_review_produit_scalaire_g6",
            supervising_teacher_email=self.teacher.email,
        )
        self.assertEqual(PeerReviewCorrection.objects.filter(exam=self.exam).count(), 23)
        for peer_review in PeerReviewCorrection.objects.select_related("source_copy", "assigned_student"):
            self.assertNotEqual(peer_review.source_copy.student_id, peer_review.assigned_student_id)
            self.assertEqual(peer_review.scores_data, {})

        call_command(
            "create_peer_review_produit_scalaire_g6",
            supervising_teacher_email=self.teacher.email,
        )
        self.assertEqual(PeerReviewCorrection.objects.filter(exam=self.exam).count(), 23)
