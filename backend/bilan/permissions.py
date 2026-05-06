"""
Permissions for DNB Bilan Module
"""

from rest_framework.permissions import BasePermission
from django.contrib.auth import get_user_model

User = get_user_model()


class IsAdminOrTeacher(BasePermission):
    """
    Permission class that allows access to admin and teacher users.
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_staff
            or request.user.is_superuser
            or request.user.groups.filter(
                name__in=['admin', 'teacher', 'corrector']
            ).exists()
        )


class IsAdminOnly(BasePermission):
    """
    Permission class that allows access to admin users only.
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_staff
            or request.user.is_superuser
        )


class IsAdminOrDNBCorrector(BasePermission):
    """
    Permission class that allows access to admin users and DNB correctors only.
    """
    
    def has_permission(self, request, view):
        # Always allow admins
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if user is a teacher/corrector with DNB access
        if not request.user.groups.filter(
            name__in=['teacher', 'corrector']
        ).exists():
            return False
        
        # Check if user has access to DNB exams via assigned copies
        from grading.models import Copy
        from exams.models import Exam
        
        # Find DNB exams
        dnb_exams = Exam.objects.filter(name__contains='DNB')
        
        # Check if user is assigned to any copy in DNB exams
        for exam in dnb_exams:
            has_assigned_copies = Copy.objects.filter(
                exam=exam,
                assigned_corrector=request.user
            ).exists()
            if has_assigned_copies:
                return True
        
        return False
