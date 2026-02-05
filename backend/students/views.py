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
    Login endpoint for students using email + password.
    Rate limited to 5 attempts per 15 minutes per IP.
    CSRF exempt: Public authentication endpoint, protected by rate limiting.
    
    Conformité: .antigravity/rules/01_security_rules.md § 9
    """
    permission_classes = [AllowAny]  # Public endpoint - student authentication
    authentication_classes = []  # No auth required, bypass SessionAuth CSRF

    @method_decorator(maybe_ratelimit(key='ip', rate='5/15m', method='POST', block=True))
    def post(self, request):
        from django.contrib.auth import authenticate
        
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response({'error': 'Email et mot de passe sont requis.'}, status=status.HTTP_400_BAD_REQUEST)

        # Find student by email
        try:
            student = Student.objects.select_related('user').get(email__iexact=email)
        except Student.DoesNotExist:
            # Audit trail: Login élève échoué
            log_authentication_attempt(request, success=False, student_id=None)
            return Response({'error': 'Identifiants invalides.'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Verify student has a user account
        if not student.user:
            log_authentication_attempt(request, success=False, student_id=student.id)
            return Response({'error': 'Compte utilisateur non configuré. Contactez l\'administrateur.'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Authenticate with Django User
        user = authenticate(request, username=student.user.username, password=password)
        
        if user is not None and user.is_active:
            request.session['student_id'] = student.id
            request.session['role'] = 'Student'
            # Audit trail: Login élève réussi
            log_authentication_attempt(request, success=True, student_id=student.id)
            
            # Check if password needs to be changed (first login)
            must_change_password = False
            if hasattr(user, 'profile') and user.profile.must_change_password:
                must_change_password = True
            
            return Response({
                'message': 'Login successful', 
                'role': 'Student',
                'must_change_password': must_change_password
            })
        
        # Audit trail: Login élève échoué
        log_authentication_attempt(request, success=False, student_id=student.id)
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
    search_fields = ['full_name', 'email', 'class_name']


class StudentDetailView(generics.RetrieveAPIView):
    """Récupérer un étudiant par son ID"""
    permission_classes = [IsAuthenticated]
    queryset = Student.objects.all()
    serializer_class = StudentSerializer

class StudentImportView(views.APIView):
    """
    Import students from CSV file.
    
    Expected CSV format (headers):
    - NOM (required): Nom de famille
    - PRENOM (required): Prénom
    - EMAIL (required): Email pour connexion au portail élève (identifiant unique)
    - DATE_NAISSANCE (optional): Date de naissance (DD/MM/YYYY or YYYY-MM-DD)
    - CLASSE (optional): Classe (ex: T1, 1S2)
    - GROUPE_EDS (optional): Groupe EDS (ex: Maths-Physique, SVT-Chimie)
    """
    permission_classes = [IsAuthenticated]  # Teacher/Admin only
    parser_classes = [MultiPartParser, FormParser]

    @method_decorator(maybe_ratelimit(key='user', rate='10/h', method='POST', block=True))
    def post(self, request):
        import tempfile
        import os
        from students.services.csv_import import import_students_from_csv, CsvReadError
        
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'File required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check file extension
        filename = file_obj.name.lower()
        if filename.endswith('.xml'):
            return Response(
                {'error': "XML Sconet parsing not implemented. Please use CSV format with headers: NOM,PRENOM,EMAIL,DATE_NAISSANCE,CLASSE,GROUPE_EDS"},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        
        try:
            # Save uploaded file to temp location for csv_import service
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
                for chunk in file_obj.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name
            
            try:
                result = import_students_from_csv(tmp_path, Student)
                
                response_data = {
                    'created': result.created,
                    'updated': result.updated,
                    'skipped': result.skipped,
                    'errors': [
                        {'row': e.row, 'message': e.message}
                        for e in result.errors[:10]  # Limit errors in response
                    ],
                    'total_errors': len(result.errors),
                }
                
                # Add passwords to response if any were generated
                if hasattr(result, 'passwords') and result.passwords:
                    response_data['passwords'] = result.passwords
                    response_data['message'] = 'Import réussi. IMPORTANT: Sauvegardez les mots de passe générés et communiquez-les aux étudiants de manière sécurisée.'
                
                return Response(response_data)
                
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                    
        except CsvReadError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            from core.utils.errors import safe_error_response
            return Response(
                safe_error_response(e, context="CSV import", user_message="Failed to import students. Please check file format."),
                status=status.HTTP_400_BAD_REQUEST
            )


class StudentChangePasswordView(views.APIView):
    """
    Allow students to change their password.
    Students must be authenticated via session.
    """
    permission_classes = [IsStudent]

    @method_decorator(maybe_ratelimit(key='user', rate='5/h', method='POST', block=True))
    def post(self, request):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        from django.contrib.auth import update_session_auth_hash
        
        student_id = request.session.get('student_id')
        if not student_id:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        student = get_object_or_404(Student, id=student_id)
        
        if not student.user:
            return Response({'error': 'No user account associated'}, status=status.HTTP_400_BAD_REQUEST)
        
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        if not current_password or not new_password:
            return Response({'error': 'Current password and new password are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify current password
        if not student.user.check_password(current_password):
            return Response({'error': 'Current password is incorrect'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate new password
        try:
            validate_password(new_password, user=student.user)
        except ValidationError as e:
            return Response({'error': e.messages}, status=status.HTTP_400_BAD_REQUEST)
        
        # Set new password
        student.user.set_password(new_password)
        student.user.save()
        
        # Clear must_change_password flag if exists
        try:
            if hasattr(student.user, 'profile'):
                student.user.profile.must_change_password = False
                student.user.profile.save()
        except Exception:
            pass
        
        # Keep session alive after password change
        update_session_auth_hash(request, student.user)
        
        # Audit trail
        log_audit(request, 'student.password_changed', 'Student', student.id)
        
        return Response({'message': 'Password changed successfully'})
