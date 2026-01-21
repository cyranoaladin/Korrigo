"""
Serializers pour l'app grading.
"""
from rest_framework import serializers
from grading.models import Annotation, GradingEvent


class AnnotationSerializer(serializers.ModelSerializer):
    """
    Serializer pour Annotation.
    Validation stricte des coordonnées [0, 1] (ADR-002).
    """
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
        """
        Validation globale : coordonnées [0, 1] et page_index >= 0.
        """
        # Validation coordonnées ADR-002
        for coord_name in ['x', 'y', 'w', 'h']:
            if coord_name in data:
                coord_value = data[coord_name]
                if not (0 <= coord_value <= 1):
                    raise serializers.ValidationError(
                        {coord_name: f"{coord_name} must be in [0, 1], got {coord_value}"}
                    )

        # Validation page_index
        if 'page_index' in data and data['page_index'] < 0:
            raise serializers.ValidationError(
                {'page_index': 'page_index must be >= 0'}
            )

        return data

    def validate_type(self, value):
        """
        Validation du type d'annotation.
        """
        if value not in Annotation.Type.values:
            raise serializers.ValidationError(
                f"Invalid type. Must be one of: {', '.join(Annotation.Type.values)}"
            )
        return value


class GradingEventSerializer(serializers.ModelSerializer):
    """
    Serializer pour GradingEvent (journal d'audit).
    Lecture seule uniquement.
    """
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
