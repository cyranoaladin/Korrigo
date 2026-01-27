from rest_framework import generics, filters, status, views
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from core.utils.ratelimit import maybe_ratelimit
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import Student
from .serializers import StudentSerializer
from exams.permissions import IsStudent
from core.utils.audit import log_authentication_attempt, log_audit

@method_decorator(csrf_exempt, name='dispatch')
class StudentLoginView(views.APIView):
    """
    Login endpoint for students.
    Rate limited to 5 attempts per 15 minutes per IP.
    CSRF exempt: Public authentication endpoint, protected by rate limiting.
    
    Conformité: .antigravity/rules/01_security_rules.md § 9
    """
    permission_classes = [AllowAny]  # Public endpoint - student authentication
    authentication_classes = []  # No auth required, bypass SessionAuth CSRF

    @method_decorator(maybe_ratelimit(key='ip', rate='5/15m', method='POST', block=True))
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
            # Audit trail: Login élève réussi
            log_authentication_attempt(request, success=True, student_id=student.id)
            return Response({'message': 'Login successful', 'role': 'Student'})
        else:
            # Audit trail: Login élève échoué
            log_authentication_attempt(request, success=False, student_id=None)
            return Response({'error': 'Identifiants invalides.'}, status=status.HTTP_401_UNAUTHORIZED)

class StudentLogoutView(views.APIView):
    permission_classes = [AllowAny]  # Public endpoint - allow logout even if session expired

    def post(self, request):
        student_id = request.session.get('student_id')
        if student_id:
            # Audit trail: Logout élève
            log_audit(request, 'student.logout', 'Student', student_id)
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

class StudentImportView(views.APIView):
    permission_classes = [IsAuthenticated] # Teacher/Admin only
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        import csv
        import io
        
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'File required'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Basic CSV Import: INE, Last Name, First Name, Class
        # Or simple XML Sconet parser mock-up
        
        results = {"created": 0, "errors": []}
        
        try:
            decoded_file = file_obj.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            
            # Auto-detect if it looks like XML
            if decoded_file.strip().startswith('<'):
                 # Very basic XML parsing mock for Sconet
                 # Assuming <Eleves><Eleve><INE>...</INE><Nom>...</Nom>...</Eleve></Eleves>
                 # For MVP we stick to CSV or basic failure if XML complex
                 return Response({'error': "XML Sconet parsing not fully implemented yet, please use CSV (INE,Nom,Prenom,Classe)"}, status=status.HTTP_501_NOT_IMPLEMENTED)
            
            reader = csv.reader(io_string, delimiter=',')
            # Skip header if present? Let's assume headers: INE, Last, First, Class
            
            for idx, row in enumerate(reader):
                if idx == 0 and "INE" in row[0].upper(): continue # Skip header
                if len(row) < 4: continue
                
                ine, last, first, class_name = row[0], row[1], row[2], row[3]
                
                # Create or Update
                _, created = Student.objects.update_or_create(
                    ine=ine,
                    defaults={
                        'last_name': last,
                        'first_name': first,
                        'class_name': class_name
                    }
                )
                if created: results['created'] += 1
                
            return Response(results)
            
        except Exception as e:
            from core.utils.errors import safe_error_response
            return Response(
                safe_error_response(e, context="CSV import", user_message="Failed to import students. Please check file format."),
                status=status.HTTP_400_BAD_REQUEST
            )
