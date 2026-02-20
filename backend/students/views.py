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
    
    Authentification par: Email + Mot de passe
    
    Conformité: docs/security/MANUEL_SECURITE.md — Rate Limiting
    """
    permission_classes = [AllowAny]  # Public endpoint - student authentication
    authentication_classes = []  # No auth required, bypass SessionAuth CSRF

    @method_decorator(maybe_ratelimit(key='ip', rate='5/15m', method='POST', block=True))
    def post(self, request):
        from django.contrib.auth import authenticate, login as auth_login
        from django.contrib.auth.models import User

        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')

        if not email or not password:
            return Response({
                'error': 'Email et mot de passe sont requis.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Authenticate: try email as username first, then lookup by email field
        user = authenticate(request, username=email, password=password)
        if user is None:
            try:
                user_obj = User.objects.get(email=email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass

        if user is None or not user.is_active:
            log_authentication_attempt(request, success=False, student_id=None)
            return Response({
                'error': 'Email ou mot de passe incorrect.'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Verify this user is linked to a student
        student = Student.objects.filter(user=user).first()
        if not student:
            log_authentication_attempt(request, success=False, student_id=None)
            return Response({
                'error': 'Aucun profil élève associé à ce compte.'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Django auth login (creates proper session)
        auth_login(request, user)
        request.session['student_id'] = student.id
        request.session['role'] = 'Student'

        # Check if must change default password
        must_change_password = not user.has_usable_password() or user.check_password('passe123')

        log_authentication_attempt(request, success=True, student_id=student.id)
        return Response({
            'message': 'Login successful',
            'role': 'Student',
            'must_change_password': must_change_password,
            'student': {
                'id': student.id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'class_name': student.class_name,
                'email': student.email,
            }
        })

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


class StudentChangePasswordView(views.APIView):
    """
    Change password endpoint for students.
    Requires current session authentication (IsStudent).
    Rate limited to 5 attempts per hour.
    """
    permission_classes = [IsStudent]

    @method_decorator(maybe_ratelimit(key='ip', rate='5/h', method='POST', block=True))
    def post(self, request):
        from django.contrib.auth import update_session_auth_hash
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError

        current_password = request.data.get('current_password', '')
        new_password = request.data.get('new_password', '')

        if not current_password or not new_password:
            return Response({
                'error': 'Mot de passe actuel et nouveau mot de passe sont requis.'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user or not user.is_authenticated:
            return Response({
                'error': 'Non authentifié.'
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Verify current password
        if not user.check_password(current_password):
            return Response({
                'error': 'Mot de passe actuel incorrect.'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate new password strength
        try:
            validate_password(new_password, user=user)
        except ValidationError as e:
            return Response({
                'error': e.messages
            }, status=status.HTTP_400_BAD_REQUEST)

        # Prevent reusing the default password
        if new_password == 'passe123':
            return Response({
                'error': 'Veuillez choisir un mot de passe différent du mot de passe par défaut.'
            }, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)

        log_audit(request, 'student.password_change', 'Student',
                  request.session.get('student_id'))

        return Response({
            'message': 'Mot de passe modifié avec succès.'
        })


class StudentListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]  # Teacher/Admin only - requires Django User auth
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['first_name', 'last_name', 'email']

class StudentImportView(views.APIView):
    permission_classes = [IsAuthenticated] # Teacher/Admin only
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
                
                # Parse nom et prénom (format: "NOM PRENOM" ou "BEN AMEUR MOHAMED-YOUSSEF")
                # Convention Pronote: les mots entièrement en MAJUSCULES = nom de famille
                parts = nom_prenom.split()
                if len(parts) < 2:
                    results['errors'].append({
                        "line": line_num,
                        "error": f"Invalid name format: '{nom_prenom}' (expected 'NOM PRENOM')"
                    })
                    continue
                
                # Split: uppercase words = last_name, remaining = first_name
                last_parts = []
                first_parts = []
                for p in parts:
                    if p == p.upper() and not first_parts:
                        last_parts.append(p)
                    else:
                        first_parts.append(p)
                
                # Fallback: if all words are uppercase, first word = last, rest = first
                if not first_parts:
                    last_parts = [parts[0]]
                    first_parts = parts[1:]
                
                last_name = ' '.join(last_parts).upper()
                first_name = ' '.join(first_parts).title()
                
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
                
                # Truncate fields to model max_length to prevent DB errors
                last_name = last_name[:100]
                first_name = first_name[:100]
                class_name = class_name[:50]
                groupe = groupe[:50] if groupe else ""

                # Create or Update based on unique key: (last_name, first_name, date_naissance)
                try:
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
                    
                    # Provision Django User for authentication if email present and no user linked
                    if email and not student.user:
                        from django.contrib.auth.models import User as AuthUser, Group
                        from core.auth import UserRole
                        email_lower = email.strip().lower()
                        user_obj = AuthUser.objects.filter(email=email_lower).first()
                        if not user_obj:
                            user_obj = AuthUser.objects.filter(username=email_lower).first()
                        if not user_obj:
                            user_obj = AuthUser.objects.create_user(
                                username=email_lower,
                                email=email_lower,
                                password='passe123',
                                first_name=first_name[:30],
                                last_name=last_name[:30],
                                is_active=True,
                            )
                        student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
                        user_obj.groups.add(student_group)
                        student.user = user_obj
                        student.save(update_fields=['user'])

                    if created:
                        results['created'] += 1
                    else:
                        results['updated'] += 1
                except Exception as row_err:
                    results['errors'].append({
                        "line": line_num,
                        "error": str(row_err)[:200]
                    })
                
            status_code = status.HTTP_200_OK if not results['errors'] else status.HTTP_207_MULTI_STATUS
            return Response(results, status=status_code)
            
        except Exception as e:
            from core.utils.errors import safe_error_response
            return Response(
                safe_error_response(e, context="CSV import", user_message="Failed to import students. Please check file format."),
                status=status.HTTP_400_BAD_REQUEST
            )
