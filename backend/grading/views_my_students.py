"""
Views pour la fonctionnalité "Mes Élèves" des correcteurs.
Permet à un correcteur de voir les élèves de son groupe avec leurs bilans.
"""
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from exams.permissions import IsTeacherOrAdmin

from django.db.models import Prefetch
from students.models import Student
from exams.models import Copy
from grading.models import Score, Annotation, QuestionRemark

from django.db.models import Q

try:
    from exams.models import TeacherGroupAssignment
    _HAS_TGA_MODEL = True
except ImportError:
    _HAS_TGA_MODEL = False


def _get_teacher_assignments(user, level=None):
    """Renvoie la liste des assignations d'un correcteur, optionnellement filtrée par niveau.
    Chaque élément est un dict {level, assignment_type, group_name}."""
    if not _HAS_TGA_MODEL:
        return []
    qs = TeacherGroupAssignment.objects.filter(teacher=user)
    if level:
        qs = qs.filter(level=level)
    return list(qs.values('level', 'assignment_type', 'group_name'))


# Map level to class_name prefix patterns for cross-level disambiguation
_LEVEL_CLASS_PREFIXES = {
    'terminale': ['T.', 'Terminale'],
    'premiere':  ['1.'],
    'troisieme': ['3.'],
}


def _class_prefix_q(level):
    """Build a Q filter restricting to students whose class_name matches the level."""
    prefixes = _LEVEL_CLASS_PREFIXES.get(level, [])
    if not prefixes:
        return Q()
    q = Q(pk__in=[])  # empty base
    for pfx in prefixes:
        q |= Q(class_name__startswith=pfx)
    return q


def _students_for_assignments(assignments):
    """Construit un queryset Student couvrant toutes les assignations données,
    en filtrant par niveau pour éviter les collisions (ex: G1 terminale vs G1 première)."""
    q = Q(pk__in=[])  # empty base
    for a in assignments:
        level_q = _class_prefix_q(a['level'])
        if a['assignment_type'] == 'classe':
            q |= (Q(class_name=a['group_name']) & level_q)
        else:
            q |= (Q(groupe=a['group_name']) & level_q)
    return Student.objects.filter(q)


def _student_matches_assignments(student, assignments):
    """Vérifie si un élève correspond à au moins une assignation (avec vérification de niveau)."""
    for a in assignments:
        # Check level prefix
        prefixes = _LEVEL_CLASS_PREFIXES.get(a['level'], [])
        level_ok = any(student.class_name.startswith(pfx) for pfx in prefixes) if prefixes else True
        if not level_ok:
            continue
        if a['assignment_type'] == 'classe' and student.class_name == a['group_name']:
            return True
        if a['assignment_type'] == 'groupe' and student.groupe == a['group_name']:
            return True
    return False


def _build_question_labels(exam):
    """Construit un mapping {question_id: label_lisible} depuis le grading_structure de l'examen.
    Utilise le module partagé grading_utils pour gérer les deux formats d'ID (UUID et positionnel)."""
    from exams.grading_utils import build_question_labels
    if not exam:
        return {}
    return build_question_labels(exam.grading_structure)


class MyStudentsListView(views.APIView):
    """
    GET /api/grading/my-students/
    Liste les élèves du groupe du correcteur connecté avec leurs notes.

    Query params:
        - exam_id (optional): UUID de l'examen pour filtrer les élèves de cet examen uniquement
        - exam_type_id (optional): ID du type d'examen (alternative à exam_id)
        - level (optional): Niveau pour filtrer les assignations (terminale, premiere, troisieme)

    Si exam_id ou exam_type_id est fourni:
        - Ne retourne que les élèves qui ont une copie FINALISÉE dans cet examen
        - Le correcteur ne voit que les copies qui lui sont assignées
        - Les copies non finalisées ne sont pas affichées
    """
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request):
        level = request.query_params.get('level', None)
        exam_id = request.query_params.get('exam_id', None)
        exam_type_id = request.query_params.get('exam_type_id', None)
        assignments = _get_teacher_assignments(request.user, level=level)

        # Si un examen (ou type d'examen) est spécifié, filtrer les copies
        if exam_id or exam_type_id:
            from exams.models import Exam
            from core.auth import UserRole

            # exam : l'examen précis si exam_id donné, sinon None
            # exams_in_scope : QuerySet d'examens à considérer pour le filtrage
            exam = None
            if exam_id:
                exam = get_object_or_404(Exam, id=exam_id)
                exams_in_scope = Exam.objects.filter(pk=exam.pk)
                scope_name = exam.name
                scope_id = str(exam.id)
            else:
                # exam_type_id : agréger sur TOUS les examens de ce type
                # (évite le bug 'latest only' qui ratait BB_J1 quand
                # 'Prod Validation Exam' était plus récent).
                from exams.models import ExamType
                exam_type = get_object_or_404(ExamType, id=exam_type_id)
                exams_in_scope = Exam.objects.filter(exam_type=exam_type)
                if not exams_in_scope.exists():
                    return Response({
                        'detail': f'Aucun examen trouvé pour le type {exam_type.code}.'
                    }, status=status.HTTP_404_NOT_FOUND)
                scope_name = exam_type.name
                scope_id = str(exam_type.id)

            is_admin = (
                request.user.is_superuser
                or request.user.groups.filter(name__iexact=UserRole.ADMIN).exists()
            )

            # ═══════════════════════════════════════════════════════════════
            # Construction de la liste des élèves + copies à afficher.
            #
            # Règle métier (UNION) :
            #   Un élève s'affiche pour un correcteur si :
            #    (A) il est dans l'assignation officielle du correcteur
            #        (group_name ou class_name) ET au moins une copie dans
            #        le scope a été finalisée (par n'importe qui), OU
            #    (B) le correcteur a personnellement finalisé au moins une
            #        copie de cet élève dans le scope (couvre le cas
            #        d'assignations d\u00e9synchronisées).
            #
            # Admin : voit tous les élèves ayant une copie finalisée dans
            # le scope, sans filtre d'assignation.
            # ═══════════════════════════════════════════════════════════════
            finalized_in_scope_qs = Copy.objects.filter(
                exam__in=exams_in_scope, status=Copy.Status.FINALIZED
            )

            # Admin : voit tous les élèves ayant une copie finalisée dans le scope
            if is_admin:
                student_ids = set(
                    finalized_in_scope_qs.exclude(student__isnull=True)
                    .values_list('student_id', flat=True)
                )
                # For admin, we don't have assignments, so we create a virtual one
                students_data = self._get_students_data(student_ids, finalized_in_scope_qs)
                return Response({
                    'exam_id': scope_id,
                    'exam_name': scope_name,
                    'scope': 'exam' if exam else 'exam_type',
                    'filter': 'finalized_only',
                    'students': students_data,  # Flat list for backward compatibility with tests
                    'assignments': [{
                        'group_name': 'Tous les élèves',
                        'assignment_type': 'classe',
                        'level': level or 'tous',
                        'students': students_data
                    }]
                })

            # For regular corrector: group by assignments
            result_assignments = []
            assigned_students_qs = _students_for_assignments(assignments)
            
            for assign in assignments:
                # Filter students for this specific assignment
                prefixes = _LEVEL_CLASS_PREFIXES.get(assign['level'], [])
                level_q = Q()
                for pfx in prefixes:
                    level_q |= Q(class_name__startswith=pfx)
                
                if assign['assignment_type'] == 'classe':
                    assign_students_ids = set(
                        assigned_students_qs.filter(class_name=assign['group_name'])
                        .filter(level_q)
                        .values_list('id', flat=True)
                    )
                else:
                    assign_students_ids = set(
                        assigned_students_qs.filter(groupe=assign['group_name'])
                        .filter(level_q)
                        .values_list('id', flat=True)
                    )

                # Include all assigned students to ensure the class (and export button) is visible
                # as requested: "visible pour toutes les classes".
                students_data = self._get_students_data(assign_students_ids, finalized_in_scope_qs)
                result_assignments.append({
                    'group_name': assign['group_name'],
                    'assignment_type': assign['assignment_type'],
                    'level': assign['level'],
                    'students': students_data
                })

            # Handle case B: students I corrected personally but who are NOT in my official assignments
            all_assigned_ids = set(assigned_students_qs.values_list('id', flat=True))
            extra_ids = set(
                finalized_in_scope_qs.filter(assigned_corrector=request.user)
                .exclude(student__isnull=True)
                .exclude(student_id__in=all_assigned_ids)
                .values_list('student_id', flat=True)
            )
            
            if extra_ids:
                extra_students_data = self._get_students_data(extra_ids, finalized_in_scope_qs)
                result_assignments.append({
                    'group_name': 'Autres corrections',
                    'assignment_type': 'extra',
                    'level': level or 'tous',
                    'students': extra_students_data
                })

            # Flatten students for 'students' top-level key to satisfy existing tests
            all_students = []
            seen_student_ids = set()
            for ra in result_assignments:
                for s in ra['students']:
                    if s['id'] not in seen_student_ids:
                        all_students.append(s)
                        seen_student_ids.add(s['id'])

            return Response({
                'exam_id': scope_id,
                'exam_name': scope_name,
                'scope': 'exam' if exam else 'exam_type',
                'filter': 'finalized_only',
                'students': all_students,  # Key expected by tests
                'assignments': result_assignments
            })

        # Mode legacy (sans exam_id): comportement existant
        if not assignments:
            return Response({
                'filter': 'legacy',
                'groupe': None,
                'detail': 'Aucun groupe associé à ce correcteur.' + (f' (niveau={level})' if level else ''),
                'students': []
            }, status=status.HTTP_200_OK)

        students = _students_for_assignments(assignments).order_by('last_name', 'first_name').prefetch_related(
            Prefetch('copies', queryset=Copy.objects.select_related('exam', 'assigned_corrector').prefetch_related(
                Prefetch('scores', queryset=Score.objects.only('id', 'copy_id', 'scores_data'))
            ))
        )

        result = []
        for student in students:
            copies = student.copies.all()

            student_data = {
                'id': student.id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'class_name': student.class_name,
                'groupe': student.groupe,
                'email': student.email,
                'copies': []
            }

            for copy in copies:
                is_finalized = copy.status == 'FINALIZED'

                # Notes et correcteur : uniquement visibles si la copie est finalisée
                total_score = None
                corrector_name = None
                if is_finalized:
                    scores_list = list(copy.scores.all())
                    score_obj = scores_list[0] if scores_list else None
                    if score_obj and score_obj.scores_data:
                        total_score = sum(
                            float(v) for v in score_obj.scores_data.values()
                            if v is not None and v != ''
                        )
                    if copy.assigned_corrector:
                        corrector_name = f"{copy.assigned_corrector.first_name} {copy.assigned_corrector.last_name}".strip()
                        if not corrector_name:
                            corrector_name = copy.assigned_corrector.username

                student_data['copies'].append({
                    'copy_id': str(copy.id),
                    'exam_name': copy.exam.name if copy.exam else 'N/A',
                    'status': copy.status,
                    'total_score': round(total_score, 2) if total_score is not None else None,
                    'anonymous_id': copy.anonymous_id if is_finalized else None,
                    'corrector_name': corrector_name,
                })

            result.append(student_data)

        group_labels = [f"{a['group_name']} ({a['level']})" for a in assignments]
        return Response({
            'assignments': assignments,
            'groupe': ', '.join(group_labels),
            'count': len(result),
            'students': result
        })

    def _get_students_data(self, student_ids, finalized_in_scope_qs):
        """Helper to fetch and format student data with their copies."""
        # Only consider students who actually have at least one finalized copy in the scope
        active_student_ids = set(
            finalized_in_scope_qs.filter(student_id__in=student_ids)
            .values_list('student_id', flat=True)
        )

        copies_qs = finalized_in_scope_qs.filter(student_id__in=active_student_ids).select_related(
            'exam', 'assigned_corrector', 'student'
        ).prefetch_related(
            Prefetch('scores', queryset=Score.objects.only('id', 'copy_id', 'scores_data'))
        )

        students = Student.objects.filter(id__in=active_student_ids).order_by(
            'last_name', 'first_name'
        ).prefetch_related(Prefetch('copies', queryset=copies_qs))

        result = []
        for student in students:
            student_copies = list(student.copies.all())
            student_data = {
                'id': student.id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'class_name': student.class_name,
                'groupe': student.groupe,
                'email': student.email,
                'copies': []
            }

            for copy in student_copies:
                scores_list = list(copy.scores.all())
                score_obj = scores_list[0] if scores_list else None
                total_score = None
                if score_obj and score_obj.scores_data:
                    total_score = sum(
                        float(v) for v in score_obj.scores_data.values()
                        if v is not None and v != ''
                    )

                corrector_name = None
                if copy.assigned_corrector:
                    corrector_name = f"{copy.assigned_corrector.first_name} {copy.assigned_corrector.last_name}".strip()
                    if not corrector_name:
                        corrector_name = copy.assigned_corrector.username

                student_data['copies'].append({
                    'copy_id': str(copy.id),
                    'exam_name': copy.exam.name if copy.exam else 'N/A',
                    'exam_id': str(copy.exam.id) if copy.exam else None,
                    'status': copy.status,
                    'total_score': round(total_score, 2) if total_score is not None else None,
                    'anonymous_id': copy.anonymous_id,
                    'corrector_name': corrector_name,
                    'has_appreciation': bool(copy.global_appreciation and copy.global_appreciation.strip()),
                })
            result.append(student_data)
        return result


class StudentBilanView(views.APIView):
    """
    GET /api/grading/students/<student_id>/bilan/
    Détails complets du bilan d'un élève: notes, remarques, annotations, appréciation.
    """
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, student_id):
        assignments = _get_teacher_assignments(request.user)
        
        student = get_object_or_404(Student, id=student_id)
        
        # Vérifier que l'élève est dans au moins une assignation du correcteur (sauf admin)
        from core.auth import UserRole
        is_admin = (
            request.user.is_superuser
            or request.user.groups.filter(name__iexact=UserRole.ADMIN).exists()
        )
        if not is_admin:
            # Accès autorisé si :
            #  - l'élève match une assignation (cas historique), OU
            #  - le correcteur a finalisé au moins une copie de cet élève
            has_corrected_student = Copy.objects.filter(
                student=student,
                assigned_corrector=request.user,
                status=Copy.Status.FINALIZED,
            ).exists()
            if not (_student_matches_assignments(student, assignments) or has_corrected_student):
                return Response({
                    'detail': 'Vous n\'avez pas accès à cet élève.'
                }, status=status.HTTP_403_FORBIDDEN)
        
        # Récupérer toutes les copies de l'élève
        copies = Copy.objects.filter(student=student).select_related('exam')

        copies_data = []
        for copy in copies:
            is_finalized = copy.status == 'FINALIZED'

            # Toutes les données sensibles sont masquées tant que la copie n'est pas finalisée
            scores_data = {}
            total_score = None
            final_comment = ''
            question_labels = {}
            remarks_data = {}
            annotations_data = []
            global_appreciation = ''
            llm_summary = ''

            if is_finalized:
                score_obj = Score.objects.filter(copy=copy).first()
                if score_obj:
                    scores_data = score_obj.scores_data or {}
                    total_score = sum(
                        float(v) for v in scores_data.values()
                        if v is not None and v != ''
                    ) if scores_data else None
                    final_comment = score_obj.final_comment or ''

                question_labels = _build_question_labels(copy.exam) if copy.exam else {}

                remarks = QuestionRemark.objects.filter(copy=copy)
                remarks_data = {r.question_id: r.remark for r in remarks}

                annotations = Annotation.objects.filter(copy=copy)
                annotations_data = [{
                    'id': str(a.id),
                    'page_index': a.page_index,
                    'content': a.content,
                    'type': a.type,
                    'x': a.x,
                    'y': a.y,
                    'w': a.w,
                    'h': a.h,
                } for a in annotations]

                global_appreciation = copy.global_appreciation or ''
                llm_summary = copy.llm_summary or ''

            pdf_url = f'/grading/copies/{copy.id}/final-pdf/' if is_finalized else None

            copies_data.append({
                'copy_id': str(copy.id),
                'exam_name': copy.exam.name if copy.exam else 'N/A',
                'exam_id': str(copy.exam.id) if copy.exam else None,
                'status': copy.status,
                'anonymous_id': copy.anonymous_id if is_finalized else None,
                'total_score': round(total_score, 2) if total_score is not None else None,
                'scores_data': scores_data,
                'question_labels': question_labels,
                'final_comment': final_comment,
                'remarks': remarks_data,
                'annotations': annotations_data,
                'global_appreciation': global_appreciation,
                'llm_summary': llm_summary,
                'pdf_url': pdf_url,
            })
        
        return Response({
            'student': {
                'id': student.id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'class_name': student.class_name,
                'groupe': student.groupe,
                'email': student.email,
            },
            'copies': copies_data
        })


class ExportClassPronoteView(views.APIView):
    """
    GET /api/grading/my-students/export-csv/
    Exporte les notes d'une classe spécifique pour un examen donné au format PRONOTE.
    """
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request):
        exam_id = request.query_params.get('exam_id')
        group_name = request.query_params.get('group_name')
        assignment_type = request.query_params.get('assignment_type', 'classe')
        level = request.query_params.get('level', 'troisieme')

        if not exam_id:
            return Response({'detail': 'exam_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        from exams.models import Exam
        from exams.services.pronote_export import PronoteExporter
        from django.http import HttpResponse

        exam = get_object_or_404(Exam, id=exam_id)

        # Build filter for students
        student_ids = None
        if group_name:
            prefixes = _LEVEL_CLASS_PREFIXES.get(level, [])
            level_q = Q()
            for pfx in prefixes:
                level_q |= Q(class_name__startswith=pfx)
            
            if assignment_type == 'classe':
                student_ids = list(Student.objects.filter(class_name=group_name).filter(level_q).values_list('id', flat=True))
            else:
                student_ids = list(Student.objects.filter(groupe=group_name).filter(level_q).values_list('id', flat=True))

            if not student_ids:
                return Response({'detail': f'Aucun élève trouvé pour {group_name}'}, status=status.HTTP_404_NOT_FOUND)

        exporter = PronoteExporter(exam, student_ids=student_ids)
        try:
            csv_content, warnings = exporter.generate_csv()
            filename = f"PRONOTE_{exam.name}_{group_name}.csv"
            
            response = HttpResponse(csv_content.encode('utf-8'), content_type='text/csv')
            # Pronote/Excel expectation: UTF-8 with BOM (handled by service)
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
