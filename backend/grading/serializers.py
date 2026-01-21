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
        Validation globale des rectangles (ADR-002).
        - Coordonnées individuelles : x,y ∈ [0,1], w,h ∈ (0,1]
        - Rectangle borné : x+w ≤ 1, y+h ≤ 1
        - page_index ≥ 0
        """
        # Si toutes les coordonnées sont présentes (POST ou PATCH complet)
        coords = ['x', 'y', 'w', 'h']
        if all(k in data for k in coords):
            x, y, w, h = data['x'], data['y'], data['w'], data['h']

            # Bornes individuelles
            if not (0 <= x <= 1 and 0 <= y <= 1):
                raise serializers.ValidationError("x and y must be in [0,1]")
            if not (0 < w <= 1 and 0 < h <= 1):
                raise serializers.ValidationError("w and h must be in (0,1]")

            # Bornes du rectangle
            if x + w > 1:
                raise serializers.ValidationError("x + w must be <= 1")
            if y + h > 1:
                raise serializers.ValidationError("y + h must be <= 1")

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
