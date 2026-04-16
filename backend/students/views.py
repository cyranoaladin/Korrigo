import os

# MAINTENANCE MODE - Pour bloquer: STUDENT_ACCESS_BLOCKED=true dans .env
MAINTENANCE_MESSAGE = "L'accès élève est temporairement suspendu pour maintenance. Veuillez réessayer ultérieurement."

def is_student_access_blocked():
    """Lit la variable d'environnement à chaque requête pour permettre le changement sans restart."""
    return os.environ.get("STUDENT_ACCESS_BLOCKED", "false").lower() == "true"

from django.conf import settings
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
from exams.permissions import IsStudent, IsTeacherOrAdmin
from core.utils.audit import log_authentication_attempt, log_audit

@method_decorator(csrf_exempt, name='dispatch')
class StudentLoginView(views.APIView):
    """
    Login endpoint for students.
    Rate limited to 30 attempts per 15 minutes per IP.
    CSRF exempt: Public authentication endpoint, protected by rate limiting.
    
    Authentification par: Email + Mot de passe
    
    Conformité: docs/security/MANUEL_SECURITE.md — Rate Limiting
    """
    permission_classes = [AllowAny]  # Public endpoint - student authentication
    authentication_classes = []  # No auth required, bypass SessionAuth CSRF

    @method_decorator(maybe_ratelimit(key='ip', rate='30/15m', method='POST', block=False))
    def post(self, request):
        # Rate limit check — return clear French message instead of generic 403
        if getattr(request, 'limited', False):
            return Response({
                'error': 'Trop de tentatives de connexion. Veuillez réessayer dans quelques minutes.',
                'rate_limited': True
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)
        # MAINTENANCE MODE CHECK - Blocage temporaire des étudiants
        if is_student_access_blocked():
            return Response({
                'error': MAINTENANCE_MESSAGE,
                'maintenance': True
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
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
            user_obj = User.objects.filter(email__iexact=email).first()
            if user_obj:
                user = authenticate(request, username=user_obj.username, password=password)

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

        # P2-D FIX: Use UserProfile.must_change_password as primary source
        # to avoid expensive bcrypt checks (2-3x ~100ms) on every login.
        # Fallback to bcrypt only if profile flag is not set (legacy accounts).
        profile = getattr(user, 'profile', None)
        if profile and profile.must_change_password:
            must_change_password = True
        else:
            dob_pwd = student.date_naissance.strftime('%d%m%Y') if student.date_naissance else None
            must_change_password = (
                not user.has_usable_password()
                or (settings.DEFAULT_PASSWORD and user.check_password(settings.DEFAULT_PASSWORD))
                or (dob_pwd and user.check_password(dob_pwd))
            )
            # Cache result in profile so we never re-check bcrypt for this user
            if profile and must_change_password:
                profile.must_change_password = True
                profile.save(update_fields=['must_change_password'])
        request.session['must_change_password'] = must_change_password

        log_authentication_attempt(request, success=True, student_id=student.id)
        return Response({
            'message': 'Connexion réussie.',
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
    permission_classes = [IsStudent]  # Requires valid student session to prevent CSRF logout attacks

    def post(self, request):
        # Le logout est TOUJOURS autorisé, même en maintenance
        student_id = request.session.get('student_id')
        if student_id:
            # Audit trail: Logout élève
            log_audit(request, 'student.logout', 'Student', student_id)
        request.session.flush()
        return Response({'message': 'Logged out'})

class StudentMeView(views.APIView):
    permission_classes = [IsStudent]  # Student-only endpoint

    def get(self, request):
        # Mode 1 : session student (login élève classique)
        student_id = request.session.get('student_id')

        # Mode 2 : User Django avec profil student
        if not student_id and request.user and request.user.is_authenticated:
            student_profile = Student.objects.filter(user=request.user).first()
            if student_profile:
                student_id = student_profile.id

        if not student_id:
            return Response({'error': 'Non authentifié.'}, status=status.HTTP_401_UNAUTHORIZED)

        student = get_object_or_404(Student, id=student_id)
        serializer = StudentSerializer(student)
        data = serializer.data

        # P2-D FIX: Use session cache → UserProfile flag → bcrypt fallback
        user = student.user
        must_change = request.session.get('must_change_password')
        if must_change is None and user:
            profile = getattr(user, 'profile', None)
            if profile and profile.must_change_password:
                must_change = True
            else:
                dob_pwd = student.date_naissance.strftime('%d%m%Y') if student.date_naissance else None
                must_change = (
                    not user.has_usable_password()
                    or (settings.DEFAULT_PASSWORD and user.check_password(settings.DEFAULT_PASSWORD))
                    or (dob_pwd and user.check_password(dob_pwd))
                )
            request.session['must_change_password'] = must_change
        data['must_change_password'] = must_change or False

        return Response(data)


class StudentChangePasswordView(views.APIView):
    """
    Change password endpoint for students.
    Requires current session authentication (IsStudent).
    Rate limited to 5 attempts per hour.
    """
    permission_classes = [IsStudent]

    @method_decorator(maybe_ratelimit(key='ip', rate='5/h', method='POST', block=True))
    def post(self, request):
        # Le changement de mot de passe est TOUJOURS autorisé, même en maintenance.
        # Un élève contraint de changer son MDP ne doit pas être bloqué.
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

        # Prevent reusing the default password or date of birth
        student = Student.objects.filter(user=user).first()
        dob_pwd = student.date_naissance.strftime('%d%m%Y') if student and student.date_naissance else None
        if (settings.DEFAULT_PASSWORD and new_password == settings.DEFAULT_PASSWORD) or (dob_pwd and new_password == dob_pwd):
            return Response({
                'error': 'Veuillez choisir un mot de passe différent du mot de passe par défaut.'
            }, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        update_session_auth_hash(request, user)

        # Invalider le cache bcrypt en session
        request.session['must_change_password'] = False

        log_audit(request, 'student.password_change', 'Student',
                  request.session.get('student_id'))

        return Response({
            'message': 'Mot de passe modifié avec succès.'
        })


class StudentListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]  # LOT 8 FIX: was IsAuthenticated only
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['first_name', 'last_name', 'email']

class StudentImportView(views.APIView):
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]  # LOT 8 FIX: was IsAuthenticated only
    parser_classes = [MultiPartParser, FormParser]

    @method_decorator(maybe_ratelimit(key='user', rate='10/h', method='POST', block=True))
    def post(self, request):
        # L'import admin est TOUJOURS autorisé, même en maintenance.
        # La maintenance ne bloque que le login et la consultation élèves.
        import csv
        import io
        from datetime import datetime
        from django.db import transaction

        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'error': 'Fichier requis.'}, status=status.HTTP_400_BAD_REQUEST)

        MAX_CSV_SIZE = 5 * 1024 * 1024  # 5 MB
        if file_obj.size > MAX_CSV_SIZE:
            return Response({'error': 'Fichier trop volumineux (max 5 MB).'}, status=status.HTTP_400_BAD_REQUEST)

        results = {"created": 0, "updated": 0, "errors": []}

        try:
            decoded_file = file_obj.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)

            # Auto-detect if it looks like XML
            if decoded_file.strip().startswith('<'):
                 return Response({'error': "XML Sconet parsing not fully implemented yet, please use CSV format"}, status=status.HTTP_501_NOT_IMPLEMENTED)

            # Auto-detect separator
            sample = decoded_file[:4096]
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
                delimiter = dialect.delimiter
            except csv.Error:
                delimiter = ';'  # fallback to French standard
            reader = csv.reader(io_string, delimiter=delimiter)
            
            for idx, row in enumerate(reader):
                line_num = idx + 1
                
                # Skip header if detected (Élèves, Né(e) le, Adresse E-mail, Classe, Groupe)
                if idx == 0 and any(header in row[0].upper() for header in ['ÉLÈVES', 'ELEVES', 'NOM']):
                    continue
                
                # Validate minimum columns: Nom Prénom, Date naissance, Email, Classe, Groupe
                if len(row) < 5:
                    results['errors'].append({
                        "line": line_num,
                        "error": f"Colonnes manquantes (attendu 5, reçu {len(row)})"
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
                        "error": f"Format de nom invalide : '{nom_prenom}' (attendu 'NOM PRENOM')"
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
                        "error": f"Format de date invalide : '{date_str}' (attendu JJ/MM/AAAA)"
                    })
                    continue
                
                # Validation des champs obligatoires
                if not last_name or not first_name:
                    results['errors'].append({
                        "line": line_num,
                        "error": "Nom et prénom sont requis."
                    })
                    continue
                
                # Truncate fields to model max_length to prevent DB errors
                last_name = last_name[:100]
                first_name = first_name[:100]
                class_name = class_name[:50]
                groupe = groupe[:50] if groupe else ""

                # Create or Update based on unique key: (last_name, first_name, date_naissance)
                try:
                  with transaction.atomic():
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
                            effective_password = date_naissance.strftime('%d%m%Y')
                            user_obj = AuthUser.objects.create_user(
                                username=email_lower,
                                email=email_lower,
                                password=effective_password or settings.DEFAULT_PASSWORD or 'changeme-provision',
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
                except (Exception,) as row_err:
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
