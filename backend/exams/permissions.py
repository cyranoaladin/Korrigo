from rest_framework import permissions

class IsTeacherOrAdmin(permissions.BasePermission):
    """
    Allows access only to authenticated staff users (teachers or admins).
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff

class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit/delete it.
    Admins can do anything.
    Assumes model has `created_by`.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any staff (Teacher/Admin)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Admins can do anything
        if request.user.is_superuser or getattr(request.user, 'role', '') == 'Admin':
            return True

        # Write permissions are only allowed to the owner
        return obj.created_by == request.user

    
class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.session.get('student_id') is not None

class IsOwnerStudent(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        student_id = request.session.get('student_id')
        if not student_id:
            return False
        if hasattr(obj, 'student'):
            return obj.student and obj.student.id == student_id
        return False
