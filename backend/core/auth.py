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
            or request.user.groups.filter(name=UserRole.ADMIN).exists()
        )

class IsTeacher(BasePermission):
    """
    Permission pour les enseignants
    """
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return request.user.groups.filter(name=UserRole.TEACHER).exists()
        return False

class IsStudent(BasePermission):
    """
    Permission pour les élèves.
    Exige un user authentifié dans le groupe 'student'.
    Le fallback session legacy a été supprimé (audit permissions 2026-03-10).
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.groups.filter(name=UserRole.STUDENT).exists()

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
            or request.user.groups.filter(name=UserRole.ADMIN).exists()
            or request.user.groups.filter(name=UserRole.TEACHER).exists()
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
            or request.user.groups.filter(name=UserRole.ADMIN).exists()
        )