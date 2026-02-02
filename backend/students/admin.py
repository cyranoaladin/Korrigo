from django.contrib import admin
from .models import Student

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('email', 'last_name', 'first_name', 'date_of_birth', 'class_name', 'eds_group')
    search_fields = ('email', 'last_name', 'first_name')
    list_filter = ('class_name', 'eds_group')
