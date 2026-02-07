from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import Exam, Booklet, Copy

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

class ExamSerializer(serializers.ModelSerializer):
    booklet_count = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = ['id', 'name', 'date', 'grading_structure', 'is_processed', 'booklet_count', 'pdf_source', 'correctors', 'results_released_at']

    def get_booklet_count(self, obj):
        return obj.booklets.count()

    def validate_grading_structure(self, value):
        """
        Validation récursive de la structure du barème.
        Vérifie: types, labels, points positifs, IDs uniques, profondeur max 5.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError(_("La structure doit être une liste (JSON Array)."))

        seen_ids = set()

        def validate_node(node, depth=0):
            if depth > 5:
                raise serializers.ValidationError(_("Profondeur maximale de 5 niveaux dépassée."))

            if not isinstance(node, dict):
                raise serializers.ValidationError(_("Chaque élément doit être un objet JSON."))

            if 'label' not in node:
                raise serializers.ValidationError(_("Chaque élément doit avoir un 'label'."))

            # ID uniqueness check
            node_id = node.get('id')
            if node_id:
                if node_id in seen_ids:
                    raise serializers.ValidationError(
                        _("ID dupliqué dans le barème: '%(id)s'.") % {'id': node_id}
                    )
                seen_ids.add(node_id)

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
                    validate_node(child, depth + 1)

        for item in value:
            validate_node(item)

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
            'dispatch_run_id', 'assigned_at', 'global_appreciation'
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
        # BookletSerializer is already defined above, no need for inline import
        representation['booklets'] = BookletSerializer(instance.booklets.all(), many=True, context=self.context).data
        return representation


class CorrectorCopySerializer(serializers.ModelSerializer):
    """
    Sérialiseur sécurisé pour les correcteurs.
    Exclut STRICTEMENT les informations nominatives (student, is_identified).
    Inclut les détails de l'examen avec grading_structure pour le barème.
    """
    exam_name = serializers.CharField(source='exam.name', read_only=True)
    booklet_ids = serializers.SerializerMethodField()

    class Meta:
        model = Copy
        fields = [
            'id', 'exam', 'exam_name', 'anonymous_id',
            'status',  # Note: student and is_identified REMOVED
            'booklet_ids', 'assigned_at', 'global_appreciation'
        ]
        read_only_fields = fields

    def get_booklet_ids(self, obj):
        return list(obj.booklets.values_list('id', flat=True))

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['booklets'] = BookletSerializer(instance.booklets.all(), many=True, context=self.context).data
        # Inclure les détails de l'examen avec grading_structure
        representation['exam'] = {
            'id': str(instance.exam.id),
            'name': instance.exam.name,
            'date': str(instance.exam.date) if instance.exam.date else None,
            'grading_structure': instance.exam.grading_structure or []
        }
        return representation