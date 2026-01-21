from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User

class LoginView(APIView):
    permission_classes = [AllowAny]

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
                return Response({"message": "Login successful"})
            else:
                return Response({"error": "Account disabled"}, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]  # Requires authenticated teacher/admin

    def post(self, request):
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
