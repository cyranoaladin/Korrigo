from rest_framework import permissions

class IsStudent(permissions.BasePermission):
    """
    Allows access only to authenticated students via custom session.
    """
    def has_permission(self, request, view):
        return request.session.get('student_id') is not None

class IsOwnerStudent(permissions.BasePermission):
    """
    Object-level permission to only allow students to see their own copies.
    Assumes the model instance has a 'student' attribute.
    """
    def has_object_permission(self, request, view, obj):
        student_id = request.session.get('student_id')
        if not student_id:
            return False
        # Check if the object's student ID matches the session student ID
        # Handle case where obj might be a Copy or other related model
        if hasattr(obj, 'student'):
            return obj.student and obj.student.id == student_id
        return False
