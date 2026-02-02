from django.test import TestCase
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from exams.models import Exam, Copy, Booklet
from students.models import Student
from identification.models import OCRResult
from core.auth import UserRole, create_user_roles, IsAdmin, IsTeacher, IsStudent, IsAdminOrTeacher
from exams.permissions import IsTeacherOrAdmin
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated


# Mock view for testing permissions
class MockView(APIView):
    def get(self, request, *args, **kwargs):
        return Response({'message': 'Success'})


class RBACPermissionsTest(TestCase):
    """
    Tests pour le système RBAC strict
    """
    def setUp(self):
        # Create user roles
        self.admin_group, self.teacher_group, self.student_group = create_user_roles()
        
        # Create test users
        self.admin_user = User.objects.create_user(
            username='admin_user',
            password='testpass'
        )
        self.admin_user.groups.add(self.admin_group)
        
        self.teacher_user = User.objects.create_user(
            username='teacher_user',
            password='testpass'
        )
        self.teacher_user.groups.add(self.teacher_group)
        
        self.student_user = User.objects.create_user(
            username='student_user',
            password='testpass'
        )
        self.student_user.groups.add(self.student_group)
        
        self.regular_user = User.objects.create_user(
            username='regular_user',
            password='testpass'
        )
        
        # Create test data
        self.student = Student.objects.create(
            email="jean.dupont@test.com",
            first_name="Jean",
            last_name="Dupont",
            class_name="TG2"
        )
        
        self.exam = Exam.objects.create(
            name="Bac Blanc Maths",
            date="2026-01-25"
        )
        
        self.copy = Copy.objects.create(
            exam=self.exam,
            anonymous_id="ABC123",
            status=Copy.Status.STAGING
        )
        
        self.booklet = Booklet.objects.create(
            exam=self.exam,
            start_page=1,
            end_page=4,
            student_name_guess="Jean Dupont"
        )
        self.copy.booklets.add(self.booklet)

    def test_admin_permissions(self):
        """
        Test des permissions admin
        """
        permission = IsAdmin()
        
        # Admin should have permission
        self.assertTrue(permission.has_permission(
            type('MockRequest', (), {'user': self.admin_user})(),
            None
        ))
        
        # Others should not have admin permission
        self.assertFalse(permission.has_permission(
            type('MockRequest', (), {'user': self.teacher_user})(),
            None
        ))
        self.assertFalse(permission.has_permission(
            type('MockRequest', (), {'user': self.student_user})(),
            None
        ))
        self.assertFalse(permission.has_permission(
            type('MockRequest', (), {'user': self.regular_user})(),
            None
        ))

    def test_teacher_permissions(self):
        """
        Test des permissions teacher
        """
        permission = IsTeacher()
        
        # Teacher should have permission
        self.assertTrue(permission.has_permission(
            type('MockRequest', (), {'user': self.teacher_user})(),
            None
        ))
        
        # Others should not have teacher permission
        self.assertFalse(permission.has_permission(
            type('MockRequest', (), {'user': self.admin_user})(),
            None
        ))
        self.assertFalse(permission.has_permission(
            type('MockRequest', (), {'user': self.student_user})(),
            None
        ))
        self.assertFalse(permission.has_permission(
            type('MockRequest', (), {'user': self.regular_user})(),
            None
        ))

    def test_student_permissions(self):
        """
        Test des permissions student
        """
        permission = IsStudent()
        
        # Student should have permission
        self.assertTrue(permission.has_permission(
            type('MockRequest', (), {'user': self.student_user})(),
            None
        ))
        
        # Others should not have student permission
        self.assertFalse(permission.has_permission(
            type('MockRequest', (), {'user': self.admin_user})(),
            None
        ))
        self.assertFalse(permission.has_permission(
            type('MockRequest', (), {'user': self.teacher_user})(),
            None
        ))
        self.assertFalse(permission.has_permission(
            type('MockRequest', (), {'user': self.regular_user})(),
            None
        ))

    def test_admin_or_teacher_permissions(self):
        """
        Test des permissions admin ou teacher
        """
        permission = IsAdminOrTeacher()
        
        # Both admin and teacher should have permission
        self.assertTrue(permission.has_permission(
            type('MockRequest', (), {'user': self.admin_user})(),
            None
        ))
        self.assertTrue(permission.has_permission(
            type('MockRequest', (), {'user': self.teacher_user})(),
            None
        ))
        
        # Others should not have permission
        self.assertFalse(permission.has_permission(
            type('MockRequest', (), {'user': self.student_user})(),
            None
        ))
        self.assertFalse(permission.has_permission(
            type('MockRequest', (), {'user': self.regular_user})(),
            None
        ))

    def test_is_teacher_or_admin_permission(self):
        """
        Test de la permission IsTeacherOrAdmin
        """
        permission = IsTeacherOrAdmin()
        
        # Both admin and teacher should have permission
        self.assertTrue(permission.has_permission(
            type('MockRequest', (), {'user': self.admin_user})(),
            None
        ))
        self.assertTrue(permission.has_permission(
            type('MockRequest', (), {'user': self.teacher_user})(),
            None
        ))
        
        # Students and regular users should not have permission
        self.assertFalse(permission.has_permission(
            type('MockRequest', (), {'user': self.student_user})(),
            None
        ))
        self.assertFalse(permission.has_permission(
            type('MockRequest', (), {'user': self.regular_user})(),
            None
        ))

    def test_unauthenticated_user_permissions(self):
        """
        Test des permissions pour utilisateur non authentifié
        """
        permission = IsAdmin()
        unauthenticated_user = type('MockUser', (), {'is_authenticated': False})()
        
        self.assertFalse(permission.has_permission(
            type('MockRequest', (), {'user': unauthenticated_user})(),
            None
        ))
        
        permission = IsTeacher()
        self.assertFalse(permission.has_permission(
            type('MockRequest', (), {'user': unauthenticated_user})(),
            None
        ))
        
        permission = IsStudent()
        self.assertFalse(permission.has_permission(
            type('MockRequest', (), {'user': unauthenticated_user, 'session': {}})(),
            None
        ))


class APIEndpointSecurityTest(TestCase):
    """
    Tests de sécurité pour les endpoints API
    """
    def setUp(self):
        # Create user roles
        self.admin_group, self.teacher_group, self.student_group = create_user_roles()
        
        # Create test users
        self.admin_user = User.objects.create_user(
            username='admin_user',
            password='testpass'
        )
        self.admin_user.groups.add(self.admin_group)
        
        self.teacher_user = User.objects.create_user(
            username='teacher_user',
            password='testpass'
        )
        self.teacher_user.groups.add(self.teacher_group)
        
        self.student_user = User.objects.create_user(
            username='student_user',
            password='testpass'
        )
        self.student_user.groups.add(self.student_group)

    def test_api_endpoints_require_authentication(self):
        """
        Test que les endpoints nécessitent une authentification
        """
        factory = APIRequestFactory()
        
        # Test with unauthenticated request
        request = factory.get('/test/')
        request.user = type('MockUser', (), {'is_authenticated': False})()
        
        # Should fail authentication check
        auth_perm = IsAuthenticated()
        self.assertFalse(auth_perm.has_permission(request, MockView()))

    def test_role_based_access_control(self):
        """
        Test du contrôle d'accès basé sur les rôles
        """
        factory = APIRequestFactory()
        
        # Test admin access
        request = factory.get('/test/')
        request.user = self.admin_user
        admin_perm = IsAdmin()
        self.assertTrue(admin_perm.has_permission(request, MockView()))
        
        # Test teacher access
        request = factory.get('/test/')
        request.user = self.teacher_user
        teacher_perm = IsTeacher()
        self.assertTrue(teacher_perm.has_permission(request, MockView()))
        
        # Test student access
        request = factory.get('/test/')
        request.user = self.student_user
        student_perm = IsStudent()
        self.assertTrue(student_perm.has_permission(request, MockView()))