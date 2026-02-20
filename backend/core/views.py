from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from core.utils.ratelimit import maybe_ratelimit
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from core.utils.audit import log_authentication_attempt
from core.auth import UserRole


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CSRFTokenView(APIView):
    """
    Sets the CSRF cookie so the SPA can read it for subsequent POST requests.
    GET /api/csrf/
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"detail": "Cookie CSRF défini."})

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    """
    Login endpoint for teachers and admins.
    Rate limited to 5 attempts per 15 minutes per IP.
    CSRF exempt: Public authentication endpoint, protected by rate limiting.
    
    Conformité: docs/security/MANUEL_SECURITE.md — Rate Limiting
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # No auth required, bypass SessionAuth CSRF

    @method_decorator(maybe_ratelimit(key='ip', rate='5/15m', method='POST', block=True))
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is None and username and '@' in username:
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        
        if user is not None:
            if not user.is_active:
                log_authentication_attempt(request, success=False, username=username)
                return Response(
                    {"error": "Compte désactivé."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # Isolation profil : rejeter les élèves (doivent utiliser /students/login/)
            from students.models import Student
            if Student.objects.filter(user=user).exists():
                log_authentication_attempt(request, success=False, username=username)
                return Response(
                    {"error": "Accès réservé aux enseignants et administrateurs. "
                              "Les élèves doivent se connecter via l'espace élève."},
                    status=status.HTTP_403_FORBIDDEN
                )

            login(request, user)
            log_authentication_attempt(request, success=True, username=username)
            
            must_change_password = False
            try:
                if hasattr(user, 'profile'):
                    must_change_password = user.profile.must_change_password
            except Exception:
                pass
            
            return Response({
                "message": "Connexion réussie.",
                "must_change_password": must_change_password
            })
        else:
            log_authentication_attempt(request, success=False, username=username)
            return Response(
                {"error": "Identifiants incorrects."},
                status=status.HTTP_401_UNAUTHORIZED
            )

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]  # Requires authenticated teacher/admin

    def post(self, request):
        from core.utils.audit import log_audit
        # Audit trail: Logout
        log_audit(request, 'logout', 'User', request.user.id)
        logout(request)
        return Response({"message": "Déconnexion réussie."})

class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Determine Role (check groups first, then fall back to flags)
        if user.groups.filter(name=UserRole.TEACHER).exists():
            role = "Teacher"
        elif user.groups.filter(name=UserRole.ADMIN).exists() or user.is_superuser:
            role = "Admin"
        else:
            role = "Teacher"
        
        must_change_password = False
        try:
            if hasattr(user, 'profile'):
                must_change_password = user.profile.must_change_password
        except Exception:
            pass
        
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": role,
            "is_superuser": user.is_superuser,
            "must_change_password": must_change_password
        })

class GlobalSettingsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from core.models import GlobalSettings
        settings_obj = GlobalSettings.load()
        return Response({
            "institutionName": settings_obj.institution_name,
            "theme": settings_obj.theme,
            "defaultDuration": settings_obj.default_exam_duration,
            "notifications": settings_obj.notifications_enabled,
        })
        
    def post(self, request):
        if not request.user.is_superuser and not request.user.is_staff:
             return Response({"error": "Réservé aux administrateurs."}, status=status.HTTP_403_FORBIDDEN)
             
        from core.models import GlobalSettings
        settings_obj = GlobalSettings.load()
        
        data = request.data
        if 'institutionName' in data: settings_obj.institution_name = data['institutionName']
        if 'theme' in data: settings_obj.theme = data['theme']
        if 'defaultDuration' in data: settings_obj.default_exam_duration = int(data['defaultDuration'])
        if 'notifications' in data: settings_obj.notifications_enabled = bool(data['notifications'])
        
        settings_obj.save()
        return Response({"message": "Paramètres enregistrés."})

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(maybe_ratelimit(key='user', rate='5/h', method='POST', block=True))
    def post(self, request):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        
        user = request.user
        password = request.data.get('password')
        
        try:
            validate_password(password, user=user)
        except ValidationError as e:
            return Response({"error": e.messages}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(password)
        user.save()
        update_session_auth_hash(request, user)
        
        try:
            if hasattr(user, 'profile'):
                user.profile.must_change_password = False
                user.profile.save()
        except Exception:
            pass
        
        return Response({"message": "Mot de passe mis à jour."})

class UserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Allow admins to view users
        if not request.user.is_superuser and not request.user.is_staff:
            return Response({"error": "Réservé aux administrateurs."}, status=status.HTTP_403_FORBIDDEN)
            
        role = request.query_params.get('role', None) 
        queryset = User.objects.all().order_by('username')
        
        if role == 'Admin':
            from django.db.models import Q
            queryset = queryset.filter(Q(is_staff=True) | Q(is_superuser=True))
        elif role == 'Teacher':
            queryset = queryset.filter(groups__name=UserRole.TEACHER)
        
        users = []
        for u in queryset:
            users.append({
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "is_active": u.is_active,
                "last_login": u.last_login
            })
            
        return Response(users)

    @method_decorator(maybe_ratelimit(key='user', rate='10/h', method='POST', block=True))
    def post(self, request):
        # Allow admins to create users
        if not request.user.is_superuser and not request.user.is_staff:
            return Response({"error": "Réservé aux administrateurs."}, status=status.HTTP_403_FORBIDDEN)
            
        data = request.data
        username = data.get('username')
        password = data.get('password')
        role = data.get('role') # 'Teacher' or 'Admin'
        email = data.get('email', '')
        
        if not username or not password or not role:
            return Response({"error": "Champs obligatoires manquants."}, status=status.HTTP_400_BAD_REQUEST)
            
        if User.objects.filter(username=username).exists():
            return Response({"error": "Nom d'utilisateur déjà existant."}, status=status.HTTP_400_BAD_REQUEST)
        
        if email and User.objects.filter(email=email).exists():
            return Response({"error": "Adresse email déjà utilisée."}, status=status.HTTP_400_BAD_REQUEST)
            
        user = User.objects.create_user(username=username, email=email, password=password)
        
        if role == 'Admin':
            user.is_staff = True
            user.is_superuser = True
            user.save()
        elif role == 'Teacher':
            from django.contrib.auth.models import Group
            g, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
            user.groups.add(g)
            
        return Response({"message": "Utilisateur créé.", "id": user.id}, status=status.HTTP_201_CREATED)


class UserManageView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        # Allow admins to edit users
        if not request.user.is_superuser and not request.user.is_staff:
            return Response({"error": "Réservé aux administrateurs."}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur introuvable."}, status=status.HTTP_404_NOT_FOUND)
            
        data = request.data
        if 'email' in data:
            if data['email'] and User.objects.filter(email=data['email']).exclude(pk=pk).exists():
                return Response({"error": "Adresse email déjà utilisée."}, status=status.HTTP_400_BAD_REQUEST)
            user.email = data['email']
        if 'is_active' in data: user.is_active = bool(data['is_active'])
        if 'password' in data and data['password']:
            if len(data['password']) >= 6:
                user.set_password(data['password'])
            else:
                 return Response({"error": "Mot de passe trop court."}, status=status.HTTP_400_BAD_REQUEST)

        user.save()
        return Response({"message": "Utilisateur mis à jour."})

    def delete(self, request, pk):
        # Allow admins to delete users
        if not request.user.is_superuser and not request.user.is_staff:
            return Response({"error": "Réservé aux administrateurs."}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur introuvable."}, status=status.HTTP_404_NOT_FOUND)
            
        if user.id == request.user.id:
            return Response({"error": "Impossible de supprimer votre propre compte."}, status=status.HTTP_400_BAD_REQUEST)
            
        user.delete()
        return Response({"message": "Utilisateur supprimé."}, status=status.HTTP_204_NO_CONTENT)


class UserResetPasswordView(APIView):
    permission_classes = [IsAuthenticated]
    
    @method_decorator(maybe_ratelimit(key='user', rate='10/h', method='POST', block=True))
    def post(self, request, pk):
        if not request.user.is_superuser and not request.user.is_staff:
            return Response({"error": "Réservé aux administrateurs."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur introuvable."}, status=status.HTTP_404_NOT_FOUND)
        
        if user.id == request.user.id:
            return Response({"error": "Impossible de réinitialiser votre propre mot de passe."}, status=status.HTTP_400_BAD_REQUEST)
        
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        temporary_password = ''.join(secrets.choice(alphabet) for _ in range(12))
        
        user.set_password(temporary_password)
        user.save()
        
        try:
            from core.models import UserProfile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.must_change_password = True
            profile.save()
        except Exception:
            pass
        
        from core.utils.audit import log_audit
        log_audit(
            request,
            'password.reset',
            'User',
            user.id,
            metadata={'reset_by': request.user.username}
        )
        
        return Response({
            "message": "Mot de passe réinitialisé.",
            "temporary_password": temporary_password
        })
