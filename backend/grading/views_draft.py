from rest_framework import views, status, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import F
from django.db import transaction
from .models import DraftState
from exams.models import Copy
import uuid
import logging

logger = logging.getLogger(__name__)


def _handle_value_error(message: str, context: str):
    logger.warning(f"{context} ValueError: {message}")
    return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)


def _handle_unexpected_error(e: Exception, context: str):
    logger.error(f"{context} Unexpected Error: {e}", exc_info=True)
    return Response(
        {"detail": "Une erreur inattendue s'est produite."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

class DraftReturnView(views.APIView):
    """
    GET /api/copies/<uuid:copy_id>/draft/
    PUT /api/copies/<uuid:copy_id>/draft/

    Gère le brouillon (Autosave). Pas de lock requis — l'assigned_corrector
    garantit qu'un seul correcteur accède à une copie.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, copy_id):
        try:
            draft = DraftState.objects.get(copy_id=copy_id, owner=request.user)
            return Response({
                "id": str(draft.id),
                "payload": draft.payload,
                "version": draft.version,
                "updated_at": draft.updated_at,
                "client_id": str(draft.client_id) if draft.client_id else None
            })
        except DraftState.DoesNotExist:
             return Response(status=status.HTTP_204_NO_CONTENT)

    def put(self, request, copy_id):
        context = "DraftReturnView.put"
        try:
            copy = get_object_or_404(Copy, id=copy_id)

            if copy.status == Copy.Status.GRADED:
                return Response({"detail": "Impossible de sauvegarder un brouillon sur une copie corrigée."}, status=status.HTTP_400_BAD_REQUEST)

            payload = request.data.get('payload', {})
            client_id = request.data.get('client_id')

            if not client_id:
                return _handle_value_error("client_id is required", context=context)

            try:
                existing_draft = DraftState.objects.get(copy=copy, owner=request.user)
                if existing_draft.client_id and str(existing_draft.client_id) != str(client_id):
                    return Response(
                        {"detail": "Conflit de brouillon : modifié par une autre session."},
                        status=status.HTTP_409_CONFLICT,
                    )
            except DraftState.DoesNotExist:
                pass

            draft, created = DraftState.objects.get_or_create(
                copy=copy,
                owner=request.user,
                defaults={
                    "payload": payload,
                    "client_id": client_id,
                    "version": 1,
                },
            )

            if not created:
                updated_count = DraftState.objects.filter(
                    id=draft.id,
                    client_id=draft.client_id
                ).update(
                    payload=payload,
                    version=F('version') + 1
                )

                if updated_count == 0:
                    return Response(
                        {"detail": "Conflit de brouillon : modifié par une autre session."},
                        status=status.HTTP_409_CONFLICT,
                    )

                draft.refresh_from_db()

            return Response({
                "status": "SAVED",
                "version": draft.version,
                "updated_at": draft.updated_at
            })
        except (ValueError, KeyError) as e:
            return _handle_value_error(str(e), context=context)
        except Exception as e:
            return _handle_unexpected_error(e, context=context)

    def delete(self, request, copy_id):
        """
        Supprime le brouillon (ex: après une sauvegarde réussie).
        """
        DraftState.objects.filter(copy_id=copy_id, owner=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
