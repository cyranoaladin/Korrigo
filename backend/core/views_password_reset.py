from django.conf import settings
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.audit import log_audit
from core.utils.ratelimit import maybe_ratelimit


def _build_reset_url(uid: str, token: str) -> str:
    frontend_url = getattr(settings, 'FRONTEND_URL', 'https://korrigo.labomaths.tn').rstrip('/')
    return f"{frontend_url}/reset-password?uid={uid}&token={token}"


@method_decorator(maybe_ratelimit(key='ip', rate='5/h', method='POST', block=True), name='dispatch')
class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        generic_response = {
            'message': (
                "Si un compte existe pour cette adresse email, un lien de "
                "réinitialisation a été envoyé."
            )
        }
        if not email:
            return Response({'error': 'Adresse email requise.'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            log_audit(request, 'password_reset.request.unknown', 'User', email)
            return Response(generic_response)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = _build_reset_url(uid, token)
        html_message = render_to_string(
            'email/password_reset.html',
            {'user': user, 'reset_url': reset_url},
        )
        send_mail(
            subject='[Korrigo] Réinitialisation de votre mot de passe',
            message=(
                "Bonjour,\n\n"
                "Un lien de réinitialisation de mot de passe a été demandé pour votre compte.\n"
                f"{reset_url}\n\n"
                "Si vous n'êtes pas à l'origine de cette demande, ignorez ce message."
            ),
            from_email=settings.SERVER_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        log_audit(request, 'password_reset.request', 'User', user.id)
        return Response(generic_response)


@method_decorator(maybe_ratelimit(key='ip', rate='10/h', method='POST', block=True), name='dispatch')
class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        uid = request.data.get('uid', '')
        token = request.data.get('token', '')
        new_password = request.data.get('new_password', '')

        if not uid or not token or not new_password:
            return Response(
                {'error': 'uid, token et nouveau mot de passe sont requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(new_password) < 12:
            return Response(
                {'error': 'Le nouveau mot de passe doit contenir au moins 12 caractères.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id, is_active=True)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response({'error': 'Lien de réinitialisation invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({'error': 'Lien de réinitialisation invalide ou expiré.'}, status=status.HTTP_400_BAD_REQUEST)

        form = SetPasswordForm(user=user, data={'new_password1': new_password, 'new_password2': new_password})
        if not form.is_valid():
            errors = []
            for field_errors in form.errors.values():
                errors.extend(field_errors)
            return Response({'error': errors}, status=status.HTTP_400_BAD_REQUEST)

        form.save()
        if hasattr(user, 'profile'):
            user.profile.must_change_password = False
            user.profile.save(update_fields=['must_change_password'])
        log_audit(request, 'password_reset.confirm', 'User', user.id)
        return Response({'message': 'Mot de passe réinitialisé avec succès.'})
