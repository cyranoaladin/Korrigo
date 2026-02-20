from rest_framework import views, status, permissions
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import CopyLock, GradingEvent
from exams.models import Copy
from exams.permissions import IsTeacherOrAdmin
import uuid
import datetime
from grading.services import GradingService, LockConflictError

class LockAcquireView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, copy_id):
        copy = get_object_or_404(Copy, id=copy_id)
        user = request.user
        now = timezone.now()
        
        # Default TTL=10min (600s), configurable via body (but enforced max)
        raw_ttl = request.data.get('ttl_seconds', 1800)
        try:
            ttl = int(raw_ttl)
        except (TypeError, ValueError):
            return Response({"detail": "ttl_seconds must be a positive integer"}, status=status.HTTP_400_BAD_REQUEST)

        if ttl <= 0:
            return Response({"detail": "ttl_seconds must be a positive integer"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            lock, created = GradingService.acquire_lock(copy=copy, user=user, ttl_seconds=ttl)
        except LockConflictError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        except Exception:
            return Response({"detail": "An unexpected error occurred. Please contact support."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {
                "copy_id": str(copy.id),
                "status": "LOCKED",
                "token": str(lock.token),
                "owner": {"id": user.id, "username": user.username},
                "expires_at": lock.expires_at,
                "server_time": now,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class LockHeartbeatView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacherOrAdmin]

    def post(self, request, copy_id):
        # We don't check Copy existence first to avoid double DB hit usually, 
        # but for robustness let's follow standard flow.
        # Actually, faster to query Lock directly.
        token = request.headers.get("X-Lock-Token") or request.data.get('token')
        if not token:
            return Response({"detail": "Missing lock token."}, status=status.HTTP_403_FORBIDDEN)

        try:
            copy = get_object_or_404(Copy, id=copy_id)
            lock = GradingService.heartbeat_lock(copy=copy, user=request.user, lock_token=str(token), ttl_seconds=1800)
        except LockConflictError as e:
            message = str(e)
            status_code = status.HTTP_404_NOT_FOUND if "not found" in message.lower() or "expired" in message.lower() else status.HTTP_409_CONFLICT
            return Response({"detail": message}, status=status_code)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception:
            return Response({"detail": "An unexpected error occurred. Please contact support."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"status": "HEARTBEAT_OK", "expires_at": lock.expires_at, "server_time": timezone.now()})


class LockReleaseView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacherOrAdmin]

    def delete(self, request, copy_id):
        token = request.headers.get("X-Lock-Token") or request.data.get('token')
        if not token:
            return Response({"detail": "Missing lock token."}, status=status.HTTP_403_FORBIDDEN)

        try:
            copy = get_object_or_404(Copy, id=copy_id)
            released = GradingService.release_lock(copy=copy, user=request.user, lock_token=str(token))
        except LockConflictError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        except PermissionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_403_FORBIDDEN)
        except Exception:
            return Response({"detail": "An unexpected error occurred. Please contact support."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not released:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_204_NO_CONTENT)


class LockStatusView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, IsTeacherOrAdmin]

    def get(self, request, copy_id):
        now = timezone.now()
        copy = get_object_or_404(Copy, id=copy_id)
        try:
            lock = GradingService.get_lock_status(copy=copy)
        except Exception:
            return Response({"detail": "An unexpected error occurred. Please contact support."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not lock:
            return Response({"status": "UNLOCKED", "server_time": now})

        return Response(
            {
                "status": "LOCKED",
                "owner": {"id": lock.owner.id, "username": lock.owner.username},
                "expires_at": lock.expires_at,
                "server_time": now,
                "is_active_user": (lock.owner == request.user),
            }
        )
