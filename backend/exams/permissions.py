from rest_framework import permissions
from core.auth import IsAdmin, IsTeacher, IsStudent, IsAdminOrTeacher, IsAdminOnly, UserRole

class IsTeacherOrAdmin(permissions.BasePermission):
    """
    Allows access only to authenticated users with Teacher or Admin roles.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        # Superusers and staff always have access
        if request.user.is_superuser or request.user.is_staff:
            return True

        # Check if user belongs to Teacher or Admin group
        return (request.user.groups.filter(name=UserRole.TEACHER).exists() or
                request.user.groups.filter(name=UserRole.ADMIN).exists())

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit/delete it.
    Admins can do anything.
    Assumes model has `created_by`.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authorized user (Teacher/Admin)
        if request.method in permissions.SAFE_METHODS:
            return IsAdminOrTeacher().has_permission(request, view)

        # Admins can do anything
        if IsAdmin().has_permission(request, view):
            return True

        # Write permissions are only allowed to the owner
        return obj.created_by == request.user

class IsStudentForOwnData(permissions.BasePermission):
    """
    Permission for student to access only their own data
    """
    def has_object_permission(self, request, view, obj):
        if IsAdmin().has_permission(request, view) or IsTeacher().has_permission(request, view):
            # Admins and teachers can access any data
            return True

        if IsStudent().has_permission(request, view):
            # Students can only access their own data
            if hasattr(obj, 'student'):
                # Assuming the object has a student attribute
                return obj.student.user == request.user if hasattr(obj.student, 'user') else False
            elif hasattr(obj, 'copy') and hasattr(obj.copy, 'student'):
                # For objects like annotations that have a copy with a student
                return obj.copy.student.user == request.user if hasattr(obj.copy.student, 'user') else False
        return False
