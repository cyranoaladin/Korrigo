from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from rest_framework.permissions import BasePermission

User = get_user_model()

class UserRole:
    ADMIN = 'admin'
    TEACHER = 'teacher'
    STUDENT = 'student'

def create_user_roles():
    """
    Crée les groupes et permissions pour les rôles utilisateurs
    """
    # Groupe Admin - Accès complet
    admin_group, created = Group.objects.get_or_create(name=UserRole.ADMIN)
    
    # Groupe Prof - Accès limité à la correction
    teacher_group, created = Group.objects.get_or_create(name=UserRole.TEACHER)
    
    # Groupe Élève - Accès lecture seule à ses copies
    student_group, created = Group.objects.get_or_create(name=UserRole.STUDENT)

    # Groupe coordinateur questionnaire (feature flag)
    Group.objects.get_or_create(name='questionnaire_coordinator')

    return admin_group, teacher_group, student_group

class IsAdmin(BasePermission):
    """
    Permission pour les administrateurs.
    Vérifie group membership ou is_superuser (exclut is_staff seul).
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return (
            request.user.is_superuser
            or request.user.groups.filter(name__iexact=UserRole.ADMIN).exists()
        )

class IsTeacher(BasePermission):
    """
    Permission pour les enseignants.
    Autorise également les administrateurs et superusers pour le monitoring.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return (
            request.user.is_superuser
            or request.user.groups.filter(name__iexact=UserRole.TEACHER).exists()
            or request.user.groups.filter(name__iexact=UserRole.ADMIN).exists()
        )

class IsStudent(BasePermission):
    """
    Permission pour les élèves.
    Autorise : session student, User Django avec groupe Student + profil Student lié,
    ou administrateurs/superusers pour le support.
    """
    def has_permission(self, request, view):
        # Session-based student auth (StudentLoginView sets student_id)
        if hasattr(request, 'session') and request.session.get('student_id'):
            return True
        if not request.user.is_authenticated:
            return False
        # Admin/superuser pass-through for support
        if request.user.is_superuser or request.user.groups.filter(name__iexact=UserRole.ADMIN).exists():
            return True
        # Student group + must have actual Student profile linked
        if request.user.groups.filter(name__iexact=UserRole.STUDENT).exists():
            from students.models import Student
            return Student.objects.filter(user=request.user).exists()
        return False

class IsAdminOrTeacher(BasePermission):
    """
    Permission pour admin ou teacher.
    Utilise group membership (pas is_staff) pour distinguer admin de teacher.
    """
    def has_permission(self, request, view):
        import logging
        logger = logging.getLogger(__name__)

        # LOGGING DE DIAGNOSTIC POUR 403
        is_auth = request.user.is_authenticated
        username = request.user.username if is_auth else "Anonymous"
        groups = list(request.user.groups.values_list('name', flat=True)) if is_auth else []
        
        if not is_auth:
            logger.warning(f"PERMISSION_DENIED [IsAdminOrTeacher]: User not authenticated. Path: {getattr(request, 'path', '<no-path>')}")
            return False

        res = (
            request.user.is_superuser
            or request.user.groups.filter(name__iexact=UserRole.ADMIN).exists()
            or request.user.groups.filter(name__iexact=UserRole.TEACHER).exists()
        )
        
        if not res:
             logger.warning(
                 f"PERMISSION_DENIED [IsAdminOrTeacher]: User {username} lacks required groups. "
                 f"Groups found: {groups}, is_superuser: {request.user.is_superuser}. Path: {getattr(request, 'path', '<no-path>')}"
             )
        return res

class IsAdminOnly(BasePermission):
    """
    Permission pour admin seulement.
    Vérifie group membership ou is_superuser (exclut is_staff seul).
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        res = (
            request.user.is_superuser
            or request.user.groups.filter(name__iexact=UserRole.ADMIN).exists()
        )
        if not res and request.user.is_staff:
             import logging
             logger = logging.getLogger(__name__)
             logger.warning(f"IsAdminOnly failed for staff user {request.user.username} (missing admin group)")
        return res


class IsKorrigoAdmin(BasePermission):
    """
    Strict Korrigo application-level admin permission.
    Grants access only to:
      - Django superusers (is_superuser=True)
      - Users explicitly in the Korrigo Admin group
    Deliberately excludes is_staff alone: Django staff status (access to the
    Django admin panel) must not implicitly grant Korrigo admin rights such as
    user management or global-settings modification.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        res = (
            request.user.is_superuser
            or request.user.groups.filter(name__iexact=UserRole.ADMIN).exists()
        )
        if not res:
             import logging
             logger = logging.getLogger(__name__)
             if request.user.is_staff:
                 logger.warning(f"IsKorrigoAdmin denied for staff user {request.user.username}")
        return res