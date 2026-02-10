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
    
    Authentification par: Nom + Prénom + Date de naissance
    
    Conformité: .antigravity/rules/01_security_rules.md § 9
    """
    permission_classes = [AllowAny]  # Public endpoint - student authentication
    authentication_classes = []  # No auth required, bypass SessionAuth CSRF

    @method_decorator(maybe_ratelimit(key='ip', rate='5/15m', method='POST', block=True))
    def post(self, request):
        from datetime import datetime
        
        last_name = request.data.get('last_name')
        first_name = request.data.get('first_name')
        date_naissance_str = request.data.get('date_naissance')

        if not last_name or not first_name or not date_naissance_str:
            return Response({
                'error': 'Nom, Prénom et Date de naissance sont requis.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Parse date de naissance (format attendu: YYYY-MM-DD ou DD/MM/YYYY)
        try:
            # Try YYYY-MM-DD format first (standard ISO)
            try:
                date_naissance = datetime.strptime(date_naissance_str, "%Y-%m-%d").date()
            except ValueError:
                # Fallback to DD/MM/YYYY format
                date_naissance = datetime.strptime(date_naissance_str, "%d/%m/%Y").date()
        except ValueError:
            return Response({
                'error': 'Format de date invalide. Utilisez YYYY-MM-DD ou DD/MM/YYYY.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Case insensitive match
        student = Student.objects.filter(
            last_name__iexact=last_name,
            first_name__iexact=first_name,
            date_naissance=date_naissance
        ).first()

        if student:
            request.session['student_id'] = student.id
            request.session['role'] = 'Student'
            # Audit trail: Login élève réussi
            log_authentication_attempt(request, success=True, student_id=student.id)
            return Response({
                'message': 'Login successful',
                'role': 'Student',
                'student': {
                    'id': student.id,
                    'first_name': student.first_name,
                    'last_name': student.last_name,
                    'class_name': student.class_name
                }
            })
        else:
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
            # Establish Django session auth to enforce CSRF on unsafe methods
            from django.contrib.auth import login
            from django.contrib.auth.models import Group
            from core.auth import UserRole

            login(request, user)
            request.session['student_id'] = student.id
            request.session['role'] = 'Student'

            # Ensure student is in Student group (for permission checks)
            student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
            if not user.groups.filter(name=UserRole.STUDENT).exists():
                user.groups.add(student_group)
            # Audit trail: Login élève réussi
            log_authentication_attempt(request, success=True, student_id=student.id)
            
            # Check if password needs to be changed (first login)
            must_change_password = False
            if hasattr(user, 'profile') and user.profile.must_change_password:
                must_change_password = True
            
            # Check if privacy charter needs to be accepted
            must_accept_privacy_charter = not student.privacy_charter_accepted
            
            return Response({
                'message': 'Login successful', 
                'role': 'Student',
                'must_change_password': must_change_password,
                'must_accept_privacy_charter': must_accept_privacy_charter
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
    search_fields = ['first_name', 'last_name', 'email']

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
        import csv
        import io
        from datetime import datetime
        
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'File required'}, status=status.HTTP_400_BAD_REQUEST)
            
        results = {"created": 0, "updated": 0, "errors": []}
        
        try:
            decoded_file = file_obj.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            
            # Auto-detect if it looks like XML
            if decoded_file.strip().startswith('<'):
                 return Response({'error': "XML Sconet parsing not fully implemented yet, please use CSV format"}, status=status.HTTP_501_NOT_IMPLEMENTED)
            
            reader = csv.reader(io_string, delimiter=',')
            
            for idx, row in enumerate(reader):
                line_num = idx + 1
                
                # Skip header if detected (Élèves, Né(e) le, Adresse E-mail, Classe, Groupe)
                if idx == 0 and any(header in row[0].upper() for header in ['ÉLÈVES', 'ELEVES', 'NOM']):
                    continue
                
                # Validate minimum columns: Nom Prénom, Date naissance, Email, Classe, Groupe
                if len(row) < 5:
                    results['errors'].append({
                        "line": line_num,
                        "error": f"Missing columns (expected 5, got {len(row)})"
                    })
                    continue
                
                nom_prenom = row[0].strip()
                date_str = row[1].strip()
                email = row[2].strip()
                class_name = row[3].strip()
                groupe = row[4].strip() if len(row) > 4 else ""
                
                # Parse nom et prénom (format: "NOM PRENOM" ou "NOM Prénom")
                parts = nom_prenom.split()
                if len(parts) < 2:
                    results['errors'].append({
                        "line": line_num,
                        "error": f"Invalid name format: '{nom_prenom}' (expected 'NOM PRENOM')"
                    })
                    continue
                
                # Le premier mot est le nom (en majuscules), le reste est le prénom
                last_name = parts[0].upper()
                first_name = ' '.join(parts[1:]).capitalize()
                
                # Parse date de naissance (format: DD/MM/YYYY)
                try:
                    date_naissance = datetime.strptime(date_str, "%d/%m/%Y").date()
                except ValueError:
                    results['errors'].append({
                        "line": line_num,
                        "error": f"Invalid date format: '{date_str}' (expected DD/MM/YYYY)"
                    })
                    continue
                
                # Validation des champs obligatoires
                if not last_name or not first_name:
                    results['errors'].append({
                        "line": line_num,
                        "error": "Last name and first name are required"
                    })
                    continue
                
                # Create or Update based on unique key: (last_name, first_name, date_naissance)
                student, created = Student.objects.update_or_create(
                    last_name=last_name,
                    first_name=first_name,
                    date_naissance=date_naissance,
                    defaults={
                        'email': email or None,
                        'class_name': class_name,
                        'groupe': groupe or None
                    }
                )
                
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
                
            status_code = status.HTTP_200_OK if not results['errors'] else status.HTTP_207_MULTI_STATUS
            return Response(results, status=status_code)
            
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


class StudentAcceptPrivacyCharterView(views.APIView):
    """
    Allow students to accept the privacy charter.
    Students must be authenticated via session.
    """
    permission_classes = [IsStudent]

    def post(self, request):
        from django.utils import timezone
        
        student_id = request.session.get('student_id')
        if not student_id:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        student = get_object_or_404(Student, id=student_id)
        
        # Mark privacy charter as accepted
        student.privacy_charter_accepted = True
        student.privacy_charter_accepted_at = timezone.now()
        student.save()
        
        # Audit trail
        log_audit(request, 'student.privacy_charter_accepted', 'Student', student.id)
        
        return Response({'message': 'Privacy charter accepted successfully'})
