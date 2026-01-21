from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import Exam, Booklet, Copy

class BookletSerializer(serializers.ModelSerializer):
    header_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Booklet
        fields = ['id', 'start_page', 'end_page', 'header_image', 'header_image_url', 'student_name_guess']

    def get_header_image_url(self, obj):
        request = self.context.get('request')
        if obj.header_image and request:
            return request.build_absolute_uri(obj.header_image.url)
        return None

class ExamSerializer(serializers.ModelSerializer):
    booklet_count = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = ['id', 'name', 'date', 'grading_structure', 'is_processed', 'booklet_count', 'pdf_source']

    def get_booklet_count(self, obj):
        return obj.booklets.count()

    def validate_grading_structure(self, value):
        """
        Validation récursive basique de la structure du barème.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError(_("La structure doit être une liste (JSON Array)."))

        def validate_node(node):
            if not isinstance(node, dict):
                raise serializers.ValidationError(_("Chaque élément doit être un objet JSON."))
            
            if 'label' not in node:
                raise serializers.ValidationError(_("Chaque élément doit avoir un 'label'."))
            
            # Points validation
            if 'points' in node:
                try:
                    points = float(node['points'])
                    if points < 0:
                         raise serializers.ValidationError(_("Les points doivent être positifs."))
                except (ValueError, TypeError):
                    raise serializers.ValidationError(_("Les points doivent être un nombre."))
            
            # Recursive Children
            if 'children' in node and isinstance(node['children'], list):
                for child in node['children']:
                    validate_node(child)
        
        for item in value:
            validate_node(item)

        return value


class CopySerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source='exam.name', read_only=True)
    final_pdf_url = serializers.SerializerMethodField()
    booklet_ids = serializers.SerializerMethodField()

    class Meta:
        model = Copy
        fields = [
            'id', 'exam', 'exam_name', 'anonymous_id', 'final_pdf',
            'final_pdf_url', 'status', 'is_identified', 'student',
            'booklet_ids'
        ]
        read_only_fields = ['id', 'exam_name', 'final_pdf_url', 'booklet_ids']

    def get_final_pdf_url(self, obj):
        if obj.final_pdf:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.final_pdf.url)
            return obj.final_pdf.url
        return None

    def get_booklet_ids(self, obj):
        return list(obj.booklets.values_list('id', flat=True))

