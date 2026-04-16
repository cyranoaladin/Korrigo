from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from core.auth import UserRole, create_user_roles
from students.models import Student


class TestStudentImportPasswordPolicy(TestCase):
    def setUp(self):
        create_user_roles()
        teacher_group = Group.objects.get(name=UserRole.TEACHER)

        self.teacher = User.objects.create_user(
            username="teacher.import",
            email="teacher.import@ert.tn",
            password="TeacherImport2026!",
        )
        self.teacher.groups.add(teacher_group)

        self.client = APIClient()
        self.client.force_authenticate(user=self.teacher)

    def test_import_provisions_student_with_birth_date_password(self):
        csv_content = (
            "Élèves;Né(e) le;Adresse E-mail;Classe;Groupe\n"
            "BOUZIRI Nour;05/11/2008;nour.import-e@ert.tn;T.04;\n"
        )
        csv_file = SimpleUploadedFile(
            "students.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client.post(
            "/api/students/import/",
            {"file": csv_file},
            format="multipart",
        )

        self.assertEqual(response.status_code, 200)
        student = Student.objects.get(email="nour.import-e@ert.tn")
        self.assertIsNotNone(student.user)
        self.assertTrue(student.user.check_password("05112008"))
        self.assertFalse(student.user.check_password(settings.DEFAULT_PASSWORD))

