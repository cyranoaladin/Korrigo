from django.contrib import admin
from .models import CopyConstraint, TeacherGroupAssignment


@admin.register(CopyConstraint)
class CopyConstraintAdmin(admin.ModelAdmin):
    list_display = ['student_last_name', 'student_first_name', 'student_dob', 'forbidden_corrector', 'reason']
    list_filter = ['forbidden_corrector']
    search_fields = ['student_last_name', 'student_first_name']


@admin.register(TeacherGroupAssignment)
class TeacherGroupAssignmentAdmin(admin.ModelAdmin):
    list_display = ['teacher', 'group_name']
    list_filter = ['group_name']
    search_fields = ['teacher__username', 'teacher__email']
