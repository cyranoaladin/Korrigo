from django.contrib import admin
from .models import Student

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'date_of_birth', 'email', 'class_name', 'eds_group')
    search_fields = ('full_name', 'email')
    list_filter = ('class_name', 'eds_group')
