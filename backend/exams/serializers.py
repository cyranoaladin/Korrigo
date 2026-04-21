import os

from django.conf import settings
from rest_framework import serializers
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _
from .models import Exam, Booklet, Copy, ExamPDF, ExamType, JuryReport
from core.auth import UserRole
from .validators import (
    validate_pdf_size,
    validate_pdf_not_empty,
    validate_pdf_mime_type,
    validate_pdf_integrity,
)

class BookletSerializer(serializers.ModelSerializer):
    """Pour correcteurs — sans student_name_guess (anonymisation)."""
    header_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Booklet
        fields = [
            'id', 'start_page', 'end_page',
            'pages_images',  # REQUIRED for CorrectorDesk.vue
            'header_image', 'header_image_url',
        ]
        read_only_fields = ['pages_images']

    def get_header_image_url(self, obj):
        request = self.context.get('request')
        if obj.header_image and request:
            # LOT 2: Route through protected media endpoint
            protected_path = f'/api/media/{obj.header_image.name}'
            return request.build_absolute_uri(protected_path)
        return None


class AdminBookletSerializer(BookletSerializer):
    """Pour admins uniquement — inclut student_name_guess pour identification."""
    class Meta(BookletSerializer.Meta):
        fields = BookletSerializer.Meta.fields + ['student_name_guess']

class ExamPDFSerializer(serializers.ModelSerializer):
    """Serializer for individual PDF files in INDIVIDUAL_A4 mode"""
    
    class Meta:
        model = ExamPDF
        fields = ['id', 'pdf_file', 'student_identifier', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class ExamSerializer(serializers.ModelSerializer):
    booklet_count = serializers.SerializerMethodField()
    individual_pdfs_count = serializers.SerializerMethodField()
    copies_count = serializers.SerializerMethodField()
    copies_by_status = serializers.SerializerMethodField()
    
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

    exam_type_details = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = [
            'id', 'name', 'date', 'upload_mode', 'grading_structure',
            'is_processed', 'booklet_count', 'individual_pdfs_count',
            'copies_count', 'copies_by_status',
            'pdf_source', 'students_csv', 'correctors', 'pages_per_booklet',
            'results_released_at', 'exam_type', 'exam_type_details',
        ]

    def get_exam_type_details(self, obj):
        if obj.exam_type:
            return ExamTypeSerializer(obj.exam_type).data
        return None

    def get_booklet_count(self, obj):
        return obj.booklets.count()
    
    def get_individual_pdfs_count(self, obj):
        return obj.individual_pdfs.count()

    def get_copies_count(self, obj):
        # Use annotated value if available (from ExamListView), else fallback
        if hasattr(obj, '_copies_count'):
            return obj._copies_count
        return obj.copies.count()

    def get_copies_by_status(self, obj):
        # Use annotated values if available (from ExamListView), else fallback
        if hasattr(obj, '_ready_count'):
            return {
                'READY': obj._ready_count,
                'IN_PROGRESS': obj._in_progress_count,
                'FINALIZED': obj._finalized_count,
            }
        from django.db.models import Count
        qs = obj.copies.values('status').annotate(count=Count('id'))
        result = {}
        for row in qs:
            result[row['status']] = row['count']
        return result

    def validate_exam_type(self, value):
        """Convert empty string to None for exam_type field."""
        if value == '' or value is None:
            return None
        return value

    def to_internal_value(self, data):
        """Clean up input data before validation."""
        # Convert empty string exam_type to None before DRF tries to validate it as UUID
        if 'exam_type' in data and data['exam_type'] == '':
            data = data.copy()
            data['exam_type'] = None
        return super().to_internal_value(data)

    def validate(self, data):
        """
        Validate that the correct fields are provided based on upload_mode.
        Only enforce pdf_source requirement on creation, not on partial updates (PATCH).

        Note: For simple exam creation (just name/date/exam_type), pdf_source is NOT required.
        The PDF can be uploaded later via ExamSourceUploadView.
        """
        # Skip pdf_source validation on update (instance already exists)
        if self.instance is not None:
            return data

        # pdf_source is only required if explicitly provided upload_mode=BATCH_A3 AND we're uploading now
        # For simple exam creation (metadata only), pdf_source is optional
        upload_mode = data.get('upload_mode')
        pdf_source = data.get('pdf_source')

        # Only enforce pdf_source if:
        # 1. upload_mode is explicitly set to BATCH_A3
        # 2. AND we're actually trying to process a PDF (indicated by presence of pdf_source or explicit mode)
        if upload_mode == Exam.UploadMode.BATCH_A3 and pdf_source is None:
            # Check if this is an upload request (has file) or just metadata creation
            request = self.context.get('request')
            if request and request.FILES:
                # Only raise error if we're in an upload context but pdf_source is missing
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
    media_version = serializers.SerializerMethodField()
    pdf_source_url = serializers.SerializerMethodField()
    final_pdf_url = serializers.SerializerMethodField()
    booklet_ids = serializers.SerializerMethodField()
    assigned_corrector_username = serializers.CharField(
        source='assigned_corrector.username',
        read_only=True,
        allow_null=True
    )
    student_name = serializers.SerializerMethodField()
    corrector = serializers.SerializerMethodField()
    total_score = serializers.SerializerMethodField()

    class Meta:
        model = Copy
        fields = [
            'id', 'exam', 'exam_name', 'anonymous_id', 'pdf_source',
            'media_version', 'pdf_source_url', 'final_pdf', 'final_pdf_url', 'status', 'is_identified',
            'student', 'student_name', 'booklet_ids', 'assigned_corrector',
            'assigned_corrector_username', 'corrector',
            'dispatch_run_id', 'assigned_at', 'graded_at', 'global_appreciation',
            'subject_variant', 'total_score',
        ]
        read_only_fields = [
            'id', 'exam_name', 'media_version', 'pdf_source_url', 'final_pdf_url', 'booklet_ids',
            'assigned_corrector_username', 'dispatch_run_id', 'assigned_at',
            'graded_at', 'total_score', 'student_name', 'corrector',
        ]

    def get_student_name(self, obj):
        if not obj.student:
            return None
        s = obj.student
        try:
            parts = [s.last_name, s.first_name]
            return ' '.join(p for p in parts if p).strip() or None
        except (AttributeError, TypeError):
            return str(s) if s else None

    def get_corrector(self, obj):
        if not obj.assigned_corrector:
            return None
        u = obj.assigned_corrector
        try:
            full = ' '.join(p for p in [u.first_name, u.last_name] if isinstance(p, str) and p.strip()).strip()
            return full or u.username
        except (AttributeError, TypeError):
            return str(u) if u else None

    def get_total_score(self, obj):
        score = obj.scores.first()
        if not score or not score.scores_data:
            return None
        try:
            scores = score.scores_data
            if isinstance(scores, str):
                import json
                scores = json.loads(scores)
            return sum(float(v) for v in scores.values() if v is not None and v != '')
        except (TypeError, ValueError, AttributeError):
            return None

    def _get_file_version_ms(self, relative_path):
        if not relative_path:
            return None

        full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        try:
            return int(os.path.getmtime(full_path) * 1000)
        except OSError:
            return None

    def _build_protected_media_url(self, relative_path, version=None):
        if not relative_path:
            return None

        protected_path = f'/api/media/{relative_path}'
        if version is not None:
            protected_path = f'{protected_path}?v={version}'

        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(protected_path)
        return protected_path

    def get_media_version(self, obj):
        versions = []

        pdf_source_name = getattr(obj.pdf_source, 'name', None) if getattr(obj, 'pdf_source', None) else None
        final_pdf_name = getattr(obj.final_pdf, 'name', None) if getattr(obj, 'final_pdf', None) else None

        if pdf_source_name:
            version = self._get_file_version_ms(pdf_source_name)
            if version is not None:
                versions.append(version)

        if final_pdf_name:
            version = self._get_file_version_ms(final_pdf_name)
            if version is not None:
                versions.append(version)

        for booklet in obj.booklets.all():
            for page_path in booklet.pages_images or []:
                version = self._get_file_version_ms(page_path)
                if version is not None:
                    versions.append(version)

        if not versions:
            return None
        return max(versions)

    def get_pdf_source_url(self, obj):
        pdf_source_name = getattr(obj.pdf_source, 'name', None) if getattr(obj, 'pdf_source', None) else None
        if pdf_source_name:
            version = self._get_file_version_ms(pdf_source_name)
            return self._build_protected_media_url(pdf_source_name, version=version)
        return None

    def get_final_pdf_url(self, obj):
        final_pdf_name = getattr(obj.final_pdf, 'name', None) if getattr(obj, 'final_pdf', None) else None
        if final_pdf_name:
            version = self._get_file_version_ms(final_pdf_name)
            return self._build_protected_media_url(final_pdf_name, version=version)
        return None

    def get_booklet_ids(self, obj):
        return list(obj.booklets.values_list('id', flat=True))

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Include full booklet data — use AdminBookletSerializer for admins (includes student_name_guess)
        request = self.context.get('request')
        user = getattr(request, 'user', None) if request else None
        is_admin_user = user and (
            user.is_superuser
            or user.groups.filter(name__iexact=UserRole.ADMIN).exists()
        )
        booklet_cls = AdminBookletSerializer if is_admin_user else BookletSerializer
        representation['booklets'] = booklet_cls(instance.booklets.all(), many=True, context=self.context).data
        # Include exam metadata needed by frontend (anonymization, grading)
        # We put it in 'exam_details' to avoid breaking code that expects 'exam' to be a UUID ID string.
        exam_data = {
            'id': str(instance.exam.id),
            'name': instance.exam.name,
            'pages_per_booklet': instance.exam.pages_per_booklet,
            'grading_structure': instance.exam.grading_structure,
        }
        if instance.exam.exam_type:
            exam_data['exam_type_details'] = ExamTypeSerializer(instance.exam.exam_type).data
        representation['exam_details'] = exam_data
        # Hide student identity from non-admin users (correctors must not see student info)
        if not is_admin_user:
            representation.pop('student', None)
            representation.pop('is_identified', None)
            for booklet in representation.get('booklets', []):
                booklet.pop('header_image', None)
                booklet.pop('header_image_url', None)
        return representation


class CorrectorCopySerializer(CopySerializer):
    """
    Serialiseur sécurisé pour les correcteurs — n'expose JAMAIS student ni is_identified.
    Hérite de CopySerializer mais force le masquage des champs sensibles.
    """
    class Meta(CopySerializer.Meta):
        exclude = None
        fields = [
            f for f in CopySerializer.Meta.fields
            if f not in ('student', 'is_identified', 'student_name')
        ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Double sécurité : supprimer tout champ student qui aurait fuité
        representation.pop('student', None)
        representation.pop('student_name', None)
        representation.pop('is_identified', None)
        for booklet in representation.get('booklets', []):
            booklet.pop('student_name_guess', None)
            booklet.pop('header_image', None)
            booklet.pop('header_image_url', None)
        return representation


class ExamTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamType
        fields = '__all__'


class JuryReportSerializer(serializers.ModelSerializer):
    exam_type_name = serializers.CharField(source='exam_type.name', read_only=True)
    exam_type_code = serializers.CharField(source='exam_type.code', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = JuryReport
        fields = '__all__'
        read_only_fields = ['created_by']
