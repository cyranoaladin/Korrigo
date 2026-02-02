"""
Email Authentication Backend

Permet l'authentification par email pour tous les utilisateurs (étudiants/enseignants).
L'admin peut toujours utiliser username='admin'.
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailAuthBackend(ModelBackend):
    """
    Backend d'authentification personnalisé supportant:
    - Email + password pour étudiants et enseignants
    - username='admin' + password pour l'administrateur
    - Fallback sur username standard pour compatibilité
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username:
            return None

        # Cas spécial: Admin avec username='admin'
        if username == 'admin':
            try:
                user = User.objects.get(username='admin', is_superuser=True)
                if user.check_password(password):
                    return user
            except User.DoesNotExist:
                return None

        # Authentification par email pour tous les autres
        if '@' in username:
            try:
                user = User.objects.get(email=username)
                if user.check_password(password):
                    return user
            except User.DoesNotExist:
                return None
            except User.MultipleObjectsReturned:
                # Si plusieurs users avec même email (ne devrait pas arriver)
                return None

        # Fallback: username standard (pour enseignants existants)
        return super().authenticate(request, username=username, password=password, **kwargs)
