import os

from django.conf import settings
from rest_framework import serializers

from .models import PeerReviewAnnotation, PeerReviewCorrection, PeerReviewQuestionRemark
from .peer_review_media import peer_review_anonymized_page_paths


def _file_version_ms(relative_path):
    if not relative_path:
        return None
    try:
        return int(os.path.getmtime(os.path.join(settings.MEDIA_ROOT, relative_path)) * 1000)
    except OSError:
        return None


def _protected_media_url(request, relative_path):
    if not relative_path:
        return None
    url = f'/api/media/{relative_path}'
    version = _file_version_ms(relative_path)
    if version is not None:
        url = f'{url}?v={version}'
    return request.build_absolute_uri(url) if request else url


class PeerReviewAnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeerReviewAnnotation
        fields = ['id', 'page_index', 'x', 'y', 'w', 'h', 'content', 'type', 'color', 'metadata']
        read_only_fields = ['id']


class PeerReviewQuestionRemarkSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeerReviewQuestionRemark
        fields = ['id', 'question_id', 'remark', 'points_awarded', 'max_points']
        read_only_fields = ['id']


class StudentPeerReviewListSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source='exam.name', read_only=True)
    anonymous_id = serializers.CharField(source='source_copy.anonymous_id', read_only=True)
    total_score = serializers.SerializerMethodField()

    class Meta:
        model = PeerReviewCorrection
        fields = ['id', 'exam_name', 'anonymous_id', 'status', 'total_score', 'updated_at', 'finalized_at']

    def get_total_score(self, obj):
        return obj.total_score if obj.scores_data else None


class TeacherPeerReviewListSerializer(StudentPeerReviewListSerializer):
    assigned_student = serializers.SerializerMethodField()

    class Meta(StudentPeerReviewListSerializer.Meta):
        fields = StudentPeerReviewListSerializer.Meta.fields + ['assigned_student']

    def get_assigned_student(self, obj):
        student = obj.assigned_student
        return {
            'id': student.id,
            'name': f'{student.last_name} {student.first_name}'.strip(),
            'class_name': student.class_name,
            'groupe': student.groupe,
            'email': student.email,
        }


class PeerReviewDetailSerializer(serializers.ModelSerializer):
    exam_name = serializers.CharField(source='exam.name', read_only=True)
    anonymous_id = serializers.CharField(source='source_copy.anonymous_id', read_only=True)
    grading_structure = serializers.JSONField(source='exam.grading_structure', read_only=True)
    pages_per_booklet = serializers.IntegerField(source='exam.pages_per_booklet', read_only=True)
    source_copy_id = serializers.UUIDField(source='source_copy.id', read_only=True)
    source_status = serializers.CharField(source='source_copy.status', read_only=True)
    source_media = serializers.SerializerMethodField()
    annotations = PeerReviewAnnotationSerializer(many=True, read_only=True)
    remarks = serializers.SerializerMethodField()
    total_score = serializers.SerializerMethodField()

    class Meta:
        model = PeerReviewCorrection
        fields = [
            'id', 'exam', 'exam_name', 'source_copy_id', 'anonymous_id', 'source_status',
            'status', 'scores_data', 'global_appreciation', 'final_comment',
            'grading_structure', 'pages_per_booklet', 'source_media', 'annotations', 'remarks',
            'total_score', 'started_at', 'finalized_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_source_media(self, obj):
        request = self.context.get('request')
        pages = [
            _protected_media_url(request, page_path)
            for page_path in peer_review_anonymized_page_paths(obj.source_copy_id)
        ]
        return {
            'pdf_source_url': None,
            'final_pdf_url': None,
            'pages': pages,
        }

    def get_remarks(self, obj):
        return PeerReviewQuestionRemarkSerializer(obj.question_remarks.order_by('question_id'), many=True).data

    def get_total_score(self, obj):
        return obj.total_score if obj.scores_data else None
