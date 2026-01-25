from django.contrib.auth import authenticate, login, logout
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
        
        # Support email login if needed, but for now assuming username or handling simple matching
        # If the user provides an email as username, our customized backend might handle it, 
        # or we just assume username matches.
        
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
        elif user.groups.filter(name="Teachers").exists():
            role = "Teacher"
        
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": role,
            "is_superuser": user.is_superuser
        })
