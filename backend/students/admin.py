from django.contrib import admin
from .models import Student

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'date_naissance', 'class_name', 'groupe', 'email')
    search_fields = ('last_name', 'first_name', 'email')
    list_filter = ('class_name', 'groupe')
    date_hierarchy = 'date_naissance'
