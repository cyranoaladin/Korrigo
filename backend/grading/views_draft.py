from rest_framework import views, status, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import F
from django.db import transaction
from .models import DraftState, CopyLock
from exams.models import Copy
import uuid
import logging

logger = logging.getLogger(__name__)


def _handle_value_error(message: str, context: str):
    logger.warning(f"{context} ValueError: {message}")
    return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)


def _handle_permission_error(message: str, context: str):
    logger.warning(f"{context} PermissionError: {message}")
    return Response({"detail": message}, status=status.HTTP_403_FORBIDDEN)


def _handle_lock_conflict_error(message: str, context: str):
    logger.warning(f"{context} LockConflictError: {message}")
    return Response({"detail": message}, status=status.HTTP_409_CONFLICT)


def _handle_unexpected_error(e: Exception, context: str):
    logger.error(f"{context} Unexpected Error: {e}", exc_info=True)
    return Response(
        {"detail": "An unexpected error occurred. Please contact support."},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )

class DraftReturnView(views.APIView):
    """
    GET /api/copies/<uuid:copy_id>/draft/
    PUT /api/copies/<uuid:copy_id>/draft/
    
    Gère le brouillon (Autosave).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, copy_id):
        # Retrieve latest draft for this user and copy
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
                return Response({"detail": "Cannot save draft to GRADED copy."}, status=status.HTTP_400_BAD_REQUEST)

            token = request.headers.get('X-Lock-Token') or request.data.get('token')
            if not token:
                return _handle_permission_error("Missing lock token.", context=context)

            try:
                lock = CopyLock.objects.select_related("owner").get(copy=copy)
            except CopyLock.DoesNotExist:
                return _handle_lock_conflict_error("Lock lost (not found).", context=context)

            if lock.owner != request.user:
                return _handle_lock_conflict_error("Lock owner mismatch.", context=context)

            if str(lock.token) != str(token):
                return _handle_permission_error("Invalid lock token.", context=context)

            payload = request.data.get('payload', {})
            client_id = request.data.get('client_id')

            if not client_id:
                return _handle_value_error("client_id is required", context=context)

            try:
                existing_draft = DraftState.objects.get(copy=copy, owner=request.user)
                if existing_draft.client_id and str(existing_draft.client_id) != str(client_id):
                    return _handle_lock_conflict_error(
                        "Draft conflict: Modified by another session.",
                        context=context,
                    )
            except DraftState.DoesNotExist:
                pass

            draft, created = DraftState.objects.get_or_create(
                copy=copy,
                owner=request.user,
                defaults={
                    "payload": payload,
                    "lock_token": token,
                    "client_id": client_id,
                    "version": 1,
                },
            )

            if not created:
                # P0-DI-002 FIX: Atomic version increment with F() expression
                updated_count = DraftState.objects.filter(
                    id=draft.id,
                    client_id=draft.client_id  # Prevent session conflict
                ).update(
                    payload=payload,
                    lock_token=token,
                    version=F('version') + 1  # Atomic increment
                )
                
                if updated_count == 0:
                    return _handle_lock_conflict_error(
                        "Draft conflict: Modified by another session.",
                        context=context
                    )
                
                draft.refresh_from_db()

            return Response({
                "status": "SAVED",
                "version": draft.version,
                "updated_at": draft.updated_at
            })
        except (ValueError, KeyError) as e:
            return _handle_value_error(str(e), context=context)
        except PermissionError as e:
            return _handle_permission_error(str(e), context=context)
        except Exception as e:
            return _handle_unexpected_error(e, context=context)

    def delete(self, request, copy_id):
        """
        Supprime le brouillon (ex: après une sauvegarde réussie).
        """
        DraftState.objects.filter(copy_id=copy_id, owner=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
