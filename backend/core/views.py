from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from core.utils.ratelimit import maybe_ratelimit
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from core.utils.audit import log_authentication_attempt
from core.auth import UserRole
from core.middleware.login_lockout import (
    is_locked_out,
    record_failed_attempt,
    clear_failed_attempts,
    get_remaining_lockout_time,
)

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    """
    Login endpoint for teachers and admins.
    Rate limited to 5 attempts per 15 minutes per IP.
    CSRF exempt: Public authentication endpoint, protected by rate limiting.
    
    Conformité: .antigravity/rules/01_security_rules.md § 9
    """
    permission_classes = [AllowAny]
    authentication_classes = []  # No auth required, bypass SessionAuth CSRF

    @method_decorator(maybe_ratelimit(key='ip', rate='5/15m', method='POST', block=True))
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        # R4: Check lockout before attempting authentication
        if username and is_locked_out(username):
            remaining = get_remaining_lockout_time(username)
            log_authentication_attempt(request, success=False, username=username)
            return Response(
                {"error": "Account temporarily locked", "retry_after": remaining},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        user = authenticate(request, username=username, password=password)
        
        if user is None and username and '@' in username:
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        
        if user is not None:
            if user.is_active:
                # R4: Clear failed attempts on successful login
                clear_failed_attempts(username)
                # Session rotation to prevent session fixation
                request.session.cycle_key()
                login(request, user)
                # Audit trail: Login réussi
                log_authentication_attempt(request, success=True, username=username)
                
                must_change_password = False
                try:
                    if hasattr(user, 'profile'):
                        must_change_password = user.profile.must_change_password
                except Exception:
                    pass
                
                return Response({
                    "message": "Login successful",
                    "must_change_password": must_change_password
                })
            else:
                # Audit trail: Compte désactivé
                record_failed_attempt(username)
                log_authentication_attempt(request, success=False, username=username)
                return Response({"error": "Account disabled"}, status=status.HTTP_403_FORBIDDEN)
        else:
            # R4: Record failed attempt
            record_failed_attempt(username)
            # Audit trail: Identifiants invalides
            log_authentication_attempt(request, success=False, username=username)
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]  # Requires authenticated teacher/admin

    def post(self, request):
        from core.utils.audit import log_audit
        # Audit trail: Logout
        log_audit(request, 'logout', 'User', request.user.id)
        logout(request)
        return Response({"message": "Logout successful"})

class UserDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Determine Role
        # Admin = superuser only
        # Teacher = staff but not superuser
        role = "Teacher"
        if user.is_superuser:
            role = "Admin"
        elif user.is_staff or user.groups.filter(name=UserRole.TEACHER).exists():
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
             return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
             
        from core.models import GlobalSettings
        settings_obj = GlobalSettings.load()
        
        data = request.data
        if 'institutionName' in data: settings_obj.institution_name = data['institutionName']
        if 'theme' in data: settings_obj.theme = data['theme']
        if 'defaultDuration' in data: settings_obj.default_exam_duration = int(data['defaultDuration'])
        if 'notifications' in data: settings_obj.notifications_enabled = bool(data['notifications'])
        
        settings_obj.save()
        return Response({"message": "Settings saved"})

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @method_decorator(maybe_ratelimit(key='user', rate='5/h', method='POST', block=True))
    def post(self, request):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        # Validate required fields
        if not current_password or not new_password:
            return Response({
                "error": "Current password and new password are required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify current password
        if not user.check_password(current_password):
            return Response({
                "error": "Current password is incorrect"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate new password
        try:
            validate_password(new_password, user=user)
        except ValidationError as e:
            return Response({"error": e.messages}, status=status.HTTP_400_BAD_REQUEST)
        
        # Set new password
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)
        
        # Clear must_change_password flag
        try:
            if hasattr(user, 'profile'):
                user.profile.must_change_password = False
                user.profile.save()
        except Exception:
            pass
        
        return Response({"message": "Password updated successfully"})

class UserListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Allow admins to view users
        if not request.user.is_superuser and not request.user.is_staff:
            return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
            
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
            return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
            
        data = request.data
        username = data.get('username')
        password = data.get('password')
        role = data.get('role') # 'Teacher' or 'Admin'
        email = data.get('email', '')
        
        if not username or not password or not role:
            return Response({"error": "Missing fields"}, status=status.HTTP_400_BAD_REQUEST)
            
        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)
        
        if email and User.objects.filter(email=email).exists():
            return Response({"error": "Email already exists"}, status=status.HTTP_400_BAD_REQUEST)
            
        user = User.objects.create_user(username=username, email=email, password=password)
        
        if role == 'Admin':
            user.is_staff = True
            user.is_superuser = True
            user.save()
        elif role == 'Teacher':
            from django.contrib.auth.models import Group
            g, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
            user.groups.add(g)
            
        return Response({"message": "User created", "id": user.id}, status=status.HTTP_201_CREATED)


class UserManageView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, pk):
        # Allow admins to edit users
        if not request.user.is_superuser and not request.user.is_staff:
            return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
        data = request.data
        if 'email' in data:
            if data['email'] and User.objects.filter(email=data['email']).exclude(pk=pk).exists():
                return Response({"error": "Email already exists"}, status=status.HTTP_400_BAD_REQUEST)
            user.email = data['email']
        if 'is_active' in data: user.is_active = bool(data['is_active'])
        if 'password' in data and data['password']:
            if len(data['password']) >= 6:
                user.set_password(data['password'])
            else:
                 return Response({"error": "Password too short"}, status=status.HTTP_400_BAD_REQUEST)

        user.save()
        return Response({"message": "User updated"})

    def delete(self, request, pk):
        # Allow admins to delete users
        if not request.user.is_superuser and not request.user.is_staff:
            return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
        if user.id == request.user.id:
            return Response({"error": "Cannot delete yourself"}, status=status.HTTP_400_BAD_REQUEST)
            
        user.delete()
        return Response({"message": "User deleted"}, status=status.HTTP_204_NO_CONTENT)


class UserResetPasswordView(APIView):
    permission_classes = [IsAuthenticated]
    
    @method_decorator(maybe_ratelimit(key='user', rate='10/h', method='POST', block=True))
    def post(self, request, pk):
        if not request.user.is_superuser and not request.user.is_staff:
            return Response({"error": "Admin only"}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if user.id == request.user.id:
            return Response({"error": "Cannot reset your own password"}, status=status.HTTP_400_BAD_REQUEST)
        
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
            "message": "Password reset successfully",
            "temporary_password": temporary_password
        })


class CSRFTokenView(APIView):
    """
    Endpoint to get CSRF token cookie.
    This endpoint sets the CSRF cookie and returns a simple response.
    Used by frontend to initialize CSRF protection before making POST requests.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        from django.middleware.csrf import get_token
        csrf_token = get_token(request)
        return Response({"csrfToken": csrf_token})


class TaskStatusView(APIView):
    """
    Phase 3: Celery task status endpoint

    GET /api/tasks/<task_id>/status/

    Returns the current status and result of a Celery task.
    Used by frontend to poll for async task completion.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        from celery.result import AsyncResult

        # Get task result
        result = AsyncResult(task_id)

        response_data = {
            "task_id": task_id,
            "status": result.state,
            "ready": result.ready()
        }

        # Add result if task is complete
        if result.ready():
            try:
                task_result = result.result
                if isinstance(task_result, dict):
                    response_data["result"] = task_result
                else:
                    response_data["result"] = {"value": str(task_result)}
            except Exception as e:
                response_data["result"] = {
                    "error": str(e),
                    "status": "error"
                }

        # Add progress info if available
        if result.state == 'PROGRESS' and hasattr(result, 'info'):
            response_data["progress"] = result.info

        return Response(response_data)
