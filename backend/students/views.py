from rest_framework import generics, filters, status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Student
from .serializers import StudentSerializer
from exams.permissions import IsStudent

class StudentLoginView(views.APIView):
    permission_classes = [AllowAny]  # Public endpoint - student authentication

    def post(self, request):
        ine = request.data.get('ine')
        last_name = request.data.get('last_name')

        if not ine or not last_name:
            return Response({'error': 'INE et Nom sont requis.'}, status=status.HTTP_400_BAD_REQUEST)

        # Case insensitive match for URL/INE logic if needed, strictly speaking case insensitive filtering
        student = Student.objects.filter(ine__iexact=ine, last_name__iexact=last_name).first()

        if student:
            request.session['student_id'] = student.id
            request.session['role'] = 'Student'
            return Response({'message': 'Login successful', 'role': 'Student'})
        else:
            return Response({'error': 'Identifiants invalides.'}, status=status.HTTP_401_UNAUTHORIZED)

class StudentLogoutView(views.APIView):
    permission_classes = [AllowAny]  # Public endpoint - allow logout even if session expired

    def post(self, request):
        request.session.flush()
        return Response({'message': 'Logged out'})

class StudentMeView(views.APIView):
    permission_classes = [IsStudent]  # Student-only endpoint

    def get(self, request):
        student_id = request.session.get('student_id')
        if not student_id:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

        student = get_object_or_404(Student, id=student_id)
        serializer = StudentSerializer(student)
        return Response(serializer.data)


class StudentListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]  # Teacher/Admin only - requires Django User auth
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['first_name', 'last_name', 'ine']
