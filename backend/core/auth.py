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
    Vérifie: groupe Admin OU is_superuser OU is_staff
    """
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return (
                request.user.is_superuser or
                request.user.is_staff or
                request.user.groups.filter(name=UserRole.ADMIN).exists()
            )
        return False

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
    Permission pour les élèves
    """
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return request.user.groups.filter(name=UserRole.STUDENT).exists()
        # Fallback for legacy session auth
        if request.session.get('student_id'):
            return True
        return False

class IsAdminOrTeacher(BasePermission):
    """
    Permission pour admin ou teacher.
    Vérifie: is_superuser OU is_staff OU groupe Admin OU groupe Teacher
    """
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return (
                request.user.is_superuser or
                request.user.is_staff or
                request.user.groups.filter(name=UserRole.ADMIN).exists() or 
                request.user.groups.filter(name=UserRole.TEACHER).exists()
            )
        return False

class IsAdminOnly(BasePermission):
    """
    Permission pour admin seulement.
    Vérifie: groupe Admin OU is_superuser OU is_staff
    """
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return (
                request.user.is_superuser or
                request.user.is_staff or
                request.user.groups.filter(name=UserRole.ADMIN).exists()
            )
        return False