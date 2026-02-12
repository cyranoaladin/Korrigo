from rest_framework import serializers
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _
from .models import Exam, Booklet, Copy, ExamPDF
from .validators import (
    validate_pdf_size,
    validate_pdf_not_empty,
    validate_pdf_mime_type,
    validate_pdf_integrity,
)

class BookletSerializer(serializers.ModelSerializer):
    header_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Booklet
        fields = [
            'id', 'start_page', 'end_page', 
            'pages_images', # REQUIRED for CorrectorDesk.vue
            'header_image', 'header_image_url', 'student_name_guess'
        ]
        read_only_fields = ['pages_images']

    def get_header_image_url(self, obj):
        request = self.context.get('request')
        if obj.header_image and request:
            return request.build_absolute_uri(obj.header_image.url)
        return None

class ExamPDFSerializer(serializers.ModelSerializer):
    """Serializer for individual PDF files in INDIVIDUAL_A4 mode"""
    
    class Meta:
        model = ExamPDF
        fields = ['id', 'pdf_file', 'student_identifier', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class ExamSerializer(serializers.ModelSerializer):
    booklet_count = serializers.SerializerMethodField()
    individual_pdfs_count = serializers.SerializerMethodField()
    
    # pdf_source is now optional (only required for BATCH_A3 mode)
    pdf_source = serializers.FileField(
        required=False,
        allow_null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf']),
            validate_pdf_size,
            validate_pdf_not_empty,
            validate_pdf_mime_type,
            validate_pdf_integrity,
        ]
    )
    
    # CSV file for student list (optional for both modes)
    students_csv = serializers.FileField(
        required=False,
        allow_null=True,
        validators=[FileExtensionValidator(allowed_extensions=['csv'])]
    )

    class Meta:
        model = Exam
        fields = [
            'id', 'name', 'date', 'upload_mode', 'grading_structure',
            'is_processed', 'booklet_count', 'individual_pdfs_count',
            'pdf_source', 'students_csv', 'correctors', 'pages_per_booklet',
            'results_released_at',
        ]

    def get_booklet_count(self, obj):
        return obj.booklets.count()
    
    def get_individual_pdfs_count(self, obj):
        return obj.individual_pdfs.count()
    
    def validate(self, data):
        """
        Validate that the correct fields are provided based on upload_mode.
        Only enforce pdf_source requirement on creation, not on partial updates (PATCH).
        """
        # Skip pdf_source validation on update (instance already exists)
        if self.instance is not None:
            return data

        upload_mode = data.get('upload_mode', Exam.UploadMode.BATCH_A3)
        pdf_source = data.get('pdf_source')
        
        if upload_mode == Exam.UploadMode.BATCH_A3:
            if not pdf_source:
                raise serializers.ValidationError({
                    'pdf_source': _("Le fichier PDF source est obligatoire en mode BATCH_A3")
                })
        
        return data

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

        # Validate total points = 20
        def get_node_points(node):
            children = node.get('children', [])
            if children and isinstance(children, list) and len(children) > 0:
                return sum(get_node_points(child) for child in children)
            return float(node.get('points', 0) or 0)

        if len(value) > 0:
            total = sum(get_node_points(item) for item in value)
            if total != 20.0:
                raise serializers.ValidationError(
                    _("Le total du barème doit être exactement 20 points (actuellement %(total)s pts).") % {'total': total}
                )

        return value


class CopySerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source='exam.name', read_only=True)
    final_pdf_url = serializers.SerializerMethodField()
    booklet_ids = serializers.SerializerMethodField()
    assigned_corrector_username = serializers.CharField(
        source='assigned_corrector.username', 
        read_only=True, 
        allow_null=True
    )

    class Meta:
        model = Copy
        fields = [
            'id', 'exam', 'exam_name', 'anonymous_id', 'final_pdf',
            'final_pdf_url', 'status', 'is_identified', 'student',
            'booklet_ids', 'assigned_corrector', 'assigned_corrector_username',
            'dispatch_run_id', 'assigned_at', 'global_appreciation',
            'subject_variant'
        ]
        read_only_fields = [
            'id', 'exam_name', 'final_pdf_url', 'booklet_ids',
            'assigned_corrector_username', 'dispatch_run_id', 'assigned_at'
        ]

    def get_final_pdf_url(self, obj):
        if obj.final_pdf:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.final_pdf.url)
            return obj.final_pdf.url
        return None

    def get_booklet_ids(self, obj):
        return list(obj.booklets.values_list('id', flat=True))

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Include full booklet data for frontend pages computation
        representation['booklets'] = BookletSerializer(instance.booklets.all(), many=True, context=self.context).data
        # Include exam metadata needed by frontend (anonymization, grading)
        representation['exam'] = {
            'id': str(instance.exam.id),
            'name': instance.exam.name,
            'pages_per_booklet': instance.exam.pages_per_booklet,
            'grading_structure': instance.exam.grading_structure,
        }
        return representation

