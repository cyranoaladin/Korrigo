from django.contrib import admin
from .models import Student

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('ine', 'last_name', 'first_name', 'class_name', 'email')
    search_fields = ('ine', 'last_name', 'first_name', 'email')
    list_filter = ('class_name',)
