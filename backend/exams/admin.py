from django.contrib import admin

try:
    from .models import CopyConstraint, TeacherGroupAssignment
except ImportError:
    # Production may temporarily mount an older overlay/exams/models.py during deploy.
    # Keep admin autodiscovery non-fatal so migrations and startup can complete.
    CopyConstraint = None
    TeacherGroupAssignment = None


if CopyConstraint is not None:
    @admin.register(CopyConstraint)
    class CopyConstraintAdmin(admin.ModelAdmin):
        list_display = ['student_last_name', 'student_first_name', 'student_dob', 'forbidden_corrector', 'reason']
        list_filter = ['forbidden_corrector']
        search_fields = ['student_last_name', 'student_first_name']


if TeacherGroupAssignment is not None:
    @admin.register(TeacherGroupAssignment)
    class TeacherGroupAssignmentAdmin(admin.ModelAdmin):
        list_display = ['teacher', 'level', 'assignment_type', 'group_name']
        list_filter = ['level', 'assignment_type', 'group_name']
        search_fields = ['teacher__username', 'teacher__email']
