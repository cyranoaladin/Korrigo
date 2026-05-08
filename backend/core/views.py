import re
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from core.utils.ratelimit import maybe_ratelimit
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from core.utils.audit import log_authentication_attempt
from core.auth import UserRole, IsKorrigoAdmin, DIRECTION_GROUPS


def _is_admin_user(user) -> bool:
    """True if user has Korrigo admin privileges (superuser or Admin group).
    Deliberately excludes is_staff alone to prevent Django staff status
    from granting application-level admin rights.
    """
    return (
        user.is_superuser
        or user.groups.filter(name__iexact=UserRole.ADMIN).exists()
    )


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
            user_obj = User.objects.filter(email__iexact=username).first()
            if user_obj:
                user = authenticate(request, username=user_obj.username, password=password)
        
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
            # ROBUSTNESS FIX: if the username looks like a student email or
            # belongs to a Student user, guide them to the correct portal
            # instead of a generic 401 that creates confusion.
            is_student = False
            if username and '@' in username:
                user_obj = User.objects.filter(email__iexact=username).first()
                if user_obj:
                    from students.models import Student
                    is_student = Student.objects.filter(user=user_obj).exists()
                # Fallback heuristic: student emails use the -e@ert.tn pattern
                if not is_student and re.search(r'-e@ert\.tn$', username, re.IGNORECASE):
                    is_student = True
            if is_student:
                log_authentication_attempt(request, success=False, username=username)
                return Response(
                    {"error": "Les eleves doivent se connecter via l'espace eleve. "
                              "Cliquez sur 'Espace Eleve' ou allez directement sur /student/login"},
                    status=status.HTTP_403_FORBIDDEN
                )
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

class AuthStatusView(APIView):
    """
    GET /api/auth/status/
    Returns 200 always with the auth state. Avoids noisy 403s in browser console
    when the SPA bootstraps and probes for the current user.

    Response schema:
        {
            "authenticated": bool,
            "role": "Admin" | "Teacher" | "Student" | null,
            "user": { ... } | null,
        }
    """
    permission_classes = [AllowAny]
    # SessionAuthentication still attempts to populate request.user from the
    # session cookie; AllowAny just disables the IsAuthenticated check.

    def get(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            # Try the student session-based auth fallback
            student_id = request.session.get('student_id') if hasattr(request, 'session') else None
            if student_id:
                try:
                    from students.models import Student
                    student = Student.objects.filter(id=student_id).first()
                    if student:
                        first_name = getattr(student, 'first_name', None) or getattr(student, 'prenom', None)
                        last_name = getattr(student, 'last_name', None) or getattr(student, 'nom', None)
                        return Response({
                            'authenticated': True,
                            'role': 'Student',
                            'user': {
                                'id': student.id,
                                'first_name': first_name,
                                'last_name': last_name,
                                'email': getattr(student, 'email', None),
                            },
                        })
                except Exception:
                    pass
            return Response({
                'authenticated': False,
                'role': None,
                'user': None,
            })

        # Authenticated Django user — determine role
        if user.groups.filter(name__iexact=UserRole.ADMIN).exists() or user.is_superuser:
            role = 'Admin'
        elif user.groups.filter(name__iexact=UserRole.TEACHER).exists():
            role = 'Teacher'
        elif user.groups.filter(name__in=DIRECTION_GROUPS).exists():
            role = 'Direction'
        else:
            # Could be a Student account that uses Django auth
            try:
                from students.models import Student
                if Student.objects.filter(user=user).exists():
                    role = 'Student'
                else:
                    role = 'Unknown'
            except Exception:
                role = 'Unknown'

        return Response({
            'authenticated': True,
            'role': role,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
        })


class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Determine Role (check groups first, then fall back to flags)
        if user.groups.filter(name__iexact=UserRole.ADMIN).exists() or user.is_superuser:
            role = "Admin"
        elif user.groups.filter(name__iexact=UserRole.TEACHER).exists():
            role = "Teacher"
        elif user.groups.filter(name__in=DIRECTION_GROUPS).exists():
            role = "Direction"
        else:
            # Pure student account — reject, must use /api/students/me/
            from students.models import Student
            if Student.objects.filter(user=user).exists():
                return Response(
                    {"detail": "Compte élève — utilisez /api/students/me/"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            role = "Unknown"  # LOT 8 FIX: was "Teacher" — masks config issues
        
        must_change_password = False
        try:
            if hasattr(user, 'profile'):
                must_change_password = user.profile.must_change_password
        except Exception:
            pass
        
        # Compute which exam-type codes this corrector actually has copies in.
        # Admins/superusers get the full list so their dashboards work correctly.
        from grading.models import Copy
        from exams.models import ExamType, JuryReport
        if _is_admin_user(user):
            assigned_codes = list(
                ExamType.objects.values_list('code', flat=True)
            )
        else:
            assigned_codes = list(
                Copy.objects.filter(assigned_corrector=user)
                .values_list('exam__exam_type__code', flat=True)
                .distinct()
            )
        assigned_codes = [c for c in assigned_codes if c]  # strip None

        # Feature flags — business rules live here, not in the frontend.
        # jury_report_exam_codes: list of exam-type codes that have a published
        # jury report AND that this user is assigned to (or all, for admins).
        published_jury_codes = set(
            JuryReport.objects.filter(is_published=True)
            .values_list('exam_type__code', flat=True)
        )
        jury_report_codes = sorted(published_jury_codes & set(assigned_codes))

        features = {
            # True when the user has at least one published jury report available.
            'show_jury_report': len(jury_report_codes) > 0,
            # Per-code list so the frontend knows which reports to show.
            'jury_report_exam_codes': jury_report_codes,
            # Questionnaire is only for the designated coordinator group.
            'show_questionnaire': user.groups.filter(
                name__iexact='questionnaire_coordinator'
            ).exists(),
        }

        return Response({
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "email": user.email,
            "role": role,
            "must_change_password": must_change_password,
            "assigned_exam_type_codes": assigned_codes,
            "features": features,
        })

class GlobalSettingsView(APIView):
    permission_classes = [IsKorrigoAdmin]

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
    permission_classes = [IsKorrigoAdmin]

    def get(self, request):
            
        role = request.query_params.get('role', None) 
        queryset = User.objects.all().prefetch_related('groups').order_by('username')
        
        if role == 'Admin':
            from django.db.models import Q
            queryset = queryset.filter(Q(groups__name__iexact=UserRole.ADMIN) | Q(is_superuser=True)).distinct()
        elif role == 'Teacher':
            queryset = queryset.filter(groups__name__iexact=UserRole.TEACHER)
        
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
    permission_classes = [IsKorrigoAdmin]

    def put(self, request, pk):
            
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
            from django.contrib.auth.password_validation import validate_password
            from django.core.exceptions import ValidationError
            try:
                validate_password(data['password'], user=user)
            except ValidationError as e:
                return Response({"error": e.messages}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(data['password'])

        user.save()
        return Response({"message": "Utilisateur mis à jour."})

    def delete(self, request, pk):
            
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "Utilisateur introuvable."}, status=status.HTTP_404_NOT_FOUND)
            
        if user.id == request.user.id:
            return Response({"error": "Impossible de supprimer votre propre compte."}, status=status.HTTP_400_BAD_REQUEST)
            
        user.delete()
        return Response({"message": "Utilisateur supprimé."}, status=status.HTTP_204_NO_CONTENT)


class UserResetPasswordView(APIView):
    permission_classes = [IsKorrigoAdmin]

    @method_decorator(maybe_ratelimit(key='user', rate='10/h', method='POST', block=True))
    def post(self, request, pk):
        
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
