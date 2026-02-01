from rest_framework import generics, filters, status, views
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login
from core.utils.ratelimit import maybe_ratelimit
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import Student
from .serializers import StudentSerializer
from exams.permissions import IsStudent
from core.utils.audit import log_authentication_attempt, log_audit
from core.middleware.login_lockout import (
    is_locked_out, record_failed_attempt,
    clear_failed_attempts, get_remaining_lockout_time
)

@method_decorator(csrf_exempt, name='dispatch')
class StudentLoginView(views.APIView):
    """
    Login endpoint for students using email + password.
    Rate limited to 5 attempts per 15 minutes per IP.
    Lockout after 5 failed attempts per email for 15 minutes.
    CSRF exempt: Public authentication endpoint, protected by rate limiting.

    Conformité: .antigravity/rules/01_security_rules.md § 9
    """
    permission_classes = [AllowAny]  # Public endpoint - student authentication
    authentication_classes = []  # No auth required, bypass SessionAuth CSRF

    @method_decorator(maybe_ratelimit(key='ip', rate='5/15m', method='POST', block=True))
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'error': 'Email et mot de passe requis'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier lockout
        if is_locked_out(email):
            remaining = get_remaining_lockout_time(email)
            log_authentication_attempt(request, success=False, username=email)
            return Response(
                {"error": "Compte temporairement verrouillé", "retry_after": remaining},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # Authentifier via Django (utilise EmailAuthBackend)
        user = authenticate(request, username=email, password=password)

        if user and hasattr(user, 'student_profile'):
            # Succès - Étudiant authentifié
            clear_failed_attempts(email)
            request.session.cycle_key()  # Régénérer session ID pour sécurité
            login(request, user)

            student = user.student_profile
            request.session['student_id'] = student.id
            request.session['role'] = 'Student'

            log_authentication_attempt(request, success=True, student_id=student.id)

            # Vérifier si changement de mot de passe requis
            must_change_password = False
            if hasattr(user, 'profile'):
                must_change_password = user.profile.must_change_password

            return Response({
                'message': 'Connexion réussie',
                'role': 'Student',
                'must_change_password': must_change_password
            })
        else:
            # Échec - Identifiants invalides ou pas de profil étudiant
            record_failed_attempt(email)
            log_authentication_attempt(request, success=False, username=email)
            return Response(
                {'error': 'Identifiants invalides'},
                status=status.HTTP_401_UNAUTHORIZED
            )

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

    @method_decorator(maybe_ratelimit(key='user', rate='10/h', method='POST', block=True))
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
