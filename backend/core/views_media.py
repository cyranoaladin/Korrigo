"""
LOT 2 — Protected media serving via X-Accel-Redirect.

All media files (page scans, final PDFs, header images) are now served
through Django permission checks, then delegated to Nginx internal location.

This replaces the previous direct Nginx ``/media/`` alias which had no
authentication — any user who guessed a file path could download student
scans, corrected PDFs, etc.

Flow:
    Browser → /api/media/<path> → Django (auth check) → X-Accel-Redirect
    → Nginx internal /internal-media/<path> → file on disk

Conformité: docs/data-integrity-audit.md §4 — Endpoints Servant des Fichiers Médias
"""
import mimetypes
import os
import logging

from django.conf import settings
from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class ProtectedMediaView(APIView):
    """
    GET /api/media/<path:file_path>

    Serves a file from MEDIA_ROOT after verifying authentication.
    Uses Nginx X-Accel-Redirect for efficient file delivery (zero-copy).

    Permission: Any authenticated user (teacher, admin, or student).
    Student access is further restricted: students can only access files
    related to their own copies (enforced below).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, file_path: str):
        # Sanitize: prevent directory traversal
        clean_path = os.path.normpath(file_path)
        if clean_path.startswith('..') or clean_path.startswith('/'):
            return HttpResponse(status=400)

        # Verify file exists on disk (optional — Nginx will 404 anyway,
        # but checking here gives us a chance to log the miss)
        full_path = os.path.join(settings.MEDIA_ROOT, clean_path)
        if not os.path.isfile(full_path):
            logger.warning(
                "Protected media 404: %s (user=%s)",
                clean_path,
                request.user.username,
            )
            return HttpResponse(status=404)

        # Student role restriction: only allow access to files belonging
        # to the student's own copies.  Teachers/admins pass through.
        if not self._has_access(request, clean_path):
            logger.warning(
                "Protected media 403: %s (user=%s)",
                clean_path,
                request.user.username,
            )
            return HttpResponse(status=403)

        # Guess MIME type
        content_type, _ = mimetypes.guess_type(full_path)
        if content_type is None:
            content_type = 'application/octet-stream'

        # Build X-Accel-Redirect response
        response = HttpResponse(content_type=content_type)
        response['X-Accel-Redirect'] = f'/internal-media/{clean_path}'
        response['Content-Disposition'] = ''  # inline by default

        # Cache control: images can be cached by the browser for a session
        if content_type and content_type.startswith('image/'):
            response['Cache-Control'] = 'private, max-age=3600'
        else:
            response['Cache-Control'] = 'private, no-cache'

        return response

    # ------------------------------------------------------------------
    @staticmethod
    def _has_access(request, file_path: str) -> bool:
        """
        Determine if the current user may access the given media file.

        Rules:
        - Superusers / staff → always allowed.
        - Users in Teacher or Admin groups → always allowed.
        - Students → only if the file belongs to one of their copies.
        """
        user = request.user

        # Staff / superuser shortcut
        if user.is_staff or user.is_superuser:
            return True

        # Group-based check (Teacher or Admin)
        from core.auth import UserRole
        user_groups = set(user.groups.values_list('name', flat=True))
        if UserRole.TEACHER in user_groups or UserRole.ADMIN in user_groups:
            return True

        # Student check: verify the file belongs to one of their copies.
        # Student files are under copies/pages/{uuid}/  or  copies/{copy_id}_corrected.pdf
        if UserRole.STUDENT in user_groups:
            return ProtectedMediaView._student_owns_file(user, file_path)

        # Unknown role — deny
        return False

    @staticmethod
    def _student_owns_file(user, file_path: str) -> bool:
        """
        Check if a student user owns the media file by tracing it back
        to a Copy assigned to their Student profile.
        """
        from students.models import Student
        from exams.models import Copy

        try:
            student = Student.objects.get(user=user)
        except Student.DoesNotExist:
            return False

        # Get all copy IDs for this student where results are released
        student_copies = Copy.objects.filter(
            student=student,
            status=Copy.Status.FINALIZED,
            exam__results_released_at__isnull=False,
        )

        # Check if file_path matches any booklet page or final PDF
        for copy in student_copies:
            # Check final PDF
            if copy.final_pdf and copy.final_pdf.name == file_path:
                return True

            # Check booklet page images
            for booklet in copy.booklets.all():
                if booklet.pages_images and file_path in booklet.pages_images:
                    return True

        return False
