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
    
    return admin_group, teacher_group, student_group

class IsAdmin(BasePermission):
    """
    Permission pour les administrateurs.
    Vérifie group membership, is_superuser, ou is_staff (cohérent avec _is_admin).
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return (
            request.user.is_superuser
            or request.user.is_staff
            or request.user.groups.filter(name__iexact=UserRole.ADMIN).exists()
        )

class IsTeacher(BasePermission):
    """
    Permission pour les enseignants. 
    Autorise également les administrateurs pour le monitoring.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return (
            request.user.is_superuser 
            or request.user.is_staff 
            or request.user.groups.filter(name__iexact=UserRole.TEACHER).exists()
        )

class IsStudent(BasePermission):
    """
    Permission pour les élèves.
    Autorise également les administrateurs pour le support/audit.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return (
            request.user.is_superuser 
            or request.user.is_staff 
            or request.user.groups.filter(name__iexact=UserRole.STUDENT).exists()
        )

class IsAdminOrTeacher(BasePermission):
    """
    Permission pour admin ou teacher.
    Inclut is_superuser/is_staff pour cohérence.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return (
            request.user.is_superuser
            or request.user.is_staff
            or request.user.groups.filter(name__iexact=UserRole.ADMIN).exists()
            or request.user.groups.filter(name__iexact=UserRole.TEACHER).exists()
        )

class IsAdminOnly(BasePermission):
    """
    Permission pour admin seulement.
    Vérifie group membership, is_superuser, ou is_staff (cohérent avec IsAdmin).
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return (
            request.user.is_superuser
            or request.user.is_staff
            or request.user.groups.filter(name__iexact=UserRole.ADMIN).exists()
        )


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
        return (
            request.user.is_superuser
            or request.user.groups.filter(name__iexact=UserRole.ADMIN).exists()
        )