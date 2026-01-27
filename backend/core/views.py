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
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                # Audit trail: Login réussi
                log_authentication_attempt(request, success=True, username=username)
                return Response({"message": "Login successful"})
            else:
                # Audit trail: Compte désactivé
                log_authentication_attempt(request, success=False, username=username)
                return Response({"error": "Account disabled"}, status=status.HTTP_403_FORBIDDEN)
        else:
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
        role = "Teacher"
        if user.is_superuser or user.is_staff:
            role = "Admin"
        elif user.groups.filter(name=UserRole.TEACHER).exists():
            role = "Teacher"
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": role,
            "is_superuser": user.is_superuser
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
        user = request.user
        password = request.data.get('password')
        
        # Use Django password validation (configured in settings.py)
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        
        try:
            validate_password(password, user=user)
        except ValidationError as e:
            return Response({"error": e.messages}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(password)
        user.save()
        # Updating password logs out all other sessions, usually, but need to keep current session active
        update_session_auth_hash(request, user)
        
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
        if 'email' in data: user.email = data['email']
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
