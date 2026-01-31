from rest_framework import serializers
from .models import Student

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['id', 'ine', 'first_name', 'last_name', 'class_name', 'email', 'birth_date']
        extra_kwargs = {
            'birth_date': {'write_only': True}
        }
