"""
Serializers pour l'app grading.
"""
from rest_framework import serializers
from grading.models import Annotation, GradingEvent, QuestionRemark, AnnotationTemplate, UserAnnotation
from django.contrib.auth import get_user_model

User = get_user_model()

class UserMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class AnnotationSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Annotation
        fields = [
            'id', 'copy', 'page_index',
            'x', 'y', 'w', 'h',
            'content', 'type', 'score_delta',
            'created_by', 'created_by_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_by_username', 'created_at', 'updated_at']

    def validate(self, data):
        # Validation checks maintained...
        coords = ['x', 'y', 'w', 'h']
        if all(k in data for k in coords):
            x, y, w, h = data['x'], data['y'], data['w'], data['h']
            if not (0 <= x <= 1 and 0 <= y <= 1):
                raise serializers.ValidationError("x and y must be in [0,1]")
            if not (0 < w <= 1 and 0 < h <= 1):
                raise serializers.ValidationError("w and h must be in (0,1]")
            if x + w > 1:
                raise serializers.ValidationError("x + w must be <= 1")
            if y + h > 1:
                raise serializers.ValidationError("y + h must be <= 1")

        if 'page_index' in data and data['page_index'] < 0:
            raise serializers.ValidationError({'page_index': 'page_index must be >= 0'})

        return data


class GradingEventSerializer(serializers.ModelSerializer):
    actor_username = serializers.CharField(source='actor.username', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = GradingEvent
        fields = [
            'id', 'copy', 'action', 'action_display',
            'actor', 'actor_username',
            'timestamp', 'metadata'
        ]
        read_only_fields = ['id', 'copy', 'action', 'actor', 'timestamp', 'metadata']


class QuestionRemarkSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = QuestionRemark
        fields = [
            'id', 'copy', 'question_id', 'remark',
            'created_by', 'created_by_username',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_by_username', 'created_at', 'updated_at']


class AnnotationTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la banque d'annotations officielles.
    """
    criterion_type_display = serializers.CharField(source='get_criterion_type_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)

    class Meta:
        model = AnnotationTemplate
        fields = [
            'id', 'exam', 'document_set',
            'exercise_number', 'question_number', 'sub_question',
            'criterion_type', 'criterion_type_display',
            'severity', 'severity_display',
            'text',
            'linked_bareme_reference', 'linked_corrige_reference',
            'tags', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserAnnotationSerializer(serializers.ModelSerializer):
    """
    Serializer pour les annotations personnelles du correcteur.
    """
    class Meta:
        model = UserAnnotation
        fields = [
            'id', 'user',
            'text',
            'exercise_context', 'question_context',
            'usage_count', 'last_used',
            'tags', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'usage_count', 'last_used', 'created_at', 'updated_at']
