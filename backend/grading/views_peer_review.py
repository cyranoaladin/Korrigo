from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.auth import IsStudent, UserRole
from exams.models import Exam
from exams.permissions import IsTeacherOrAdmin
from students.models import Student

from .models import (
    PeerReviewAnnotation,
    PeerReviewCorrection,
    PeerReviewEvent,
    PeerReviewQuestionRemark,
)
from .serializers_peer_review import (
    PeerReviewAnnotationSerializer,
    PeerReviewDetailSerializer,
    TeacherPeerReviewListSerializer,
    StudentPeerReviewListSerializer,
)


def _event_actor(request, peer_review):
    """Return the authenticated user, or the assigned student as fallback for session-based auth."""
    if request.user and request.user.is_authenticated:
        return request.user
    return peer_review.assigned_user


def _student_context(request):
    student_id = request.session.get('student_id') if hasattr(request, 'session') else None
    if student_id:
        student = Student.objects.select_related('user').filter(id=student_id).first()
        if student and student.user:
            return student.user, student
    if request.user and request.user.is_authenticated:
        student = Student.objects.select_related('user').filter(user=request.user).first()
        if student:
            return request.user, student
    return None, None


def _teacher_can_supervise(user, exam):
    if user.is_superuser or user.groups.filter(name__iexact=UserRole.ADMIN).exists():
        return True
    return exam.correctors.filter(id=user.id).exists()


def _coerce_scores_to_float(scores_data):
    """Coerce all scores_data values to float, stripping empty entries.

    Frontend HTML inputs may send numbers as strings — convert them here
    so the model validator (which requires int|float) never sees a str.
    """
    if not isinstance(scores_data, dict):
        return scores_data
    coerced = {}
    for qid, value in scores_data.items():
        if value is None or value == '':
            continue
        try:
            coerced[qid] = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"La note pour '{qid}' doit être numérique.")
    return coerced


def _validate_scores_against_bareme(exam, scores_data):
    if not isinstance(scores_data, dict):
        raise ValueError("scores_data must be a dict.")

    from exams.grading_utils import build_q_max, extract_leaf_questions

    q_max = build_q_max(exam.grading_structure)
    for qid, value in scores_data.items():
        if value is None or value == '':
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"La note pour '{qid}' doit être numérique.")
        if numeric < 0:
            raise ValueError(f"La note pour '{qid}' ne peut pas être négative.")
        if qid in q_max and numeric > float(q_max[qid]) + 0.01:
            raise ValueError(f"La note pour '{qid}' dépasse le maximum autorisé ({q_max[qid]} pts).")

    leaves = extract_leaf_questions(exam.grading_structure) if exam.grading_structure else []
    max_total = sum(float(q['points']) for q in leaves) if leaves else 20.0
    total = sum(float(v) for v in scores_data.values() if v is not None and v != '')
    if total > max_total + 0.01:
        raise ValueError(f"Le total des notes ({total}) dépasse le maximum autorisé ({max_total} pts).")


class StudentPeerReviewListView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        user, student = _student_context(request)
        if not user or not student:
            return Response({"detail": "Authentification élève requise."}, status=status.HTTP_401_UNAUTHORIZED)

        qs = (
            PeerReviewCorrection.objects
            .filter(assigned_user=user, assigned_student=student)
            .select_related('exam', 'source_copy')
            .order_by('exam__date', 'source_copy__anonymous_id')
        )
        return Response(StudentPeerReviewListSerializer(qs, many=True).data)


class StudentPeerReviewDetailView(APIView):
    permission_classes = [IsStudent]

    def get_object(self, request, pk):
        user, student = _student_context(request)
        if not user or not student:
            return None
        return get_object_or_404(
            PeerReviewCorrection.objects
            .select_related('exam', 'source_copy', 'assigned_student', 'assigned_user')
            .prefetch_related('source_copy__booklets', 'annotations', 'question_remarks'),
            id=pk,
            assigned_user=user,
            assigned_student=student,
        )

    def get(self, request, pk):
        peer_review = self.get_object(request, pk)
        return Response(PeerReviewDetailSerializer(peer_review, context={'request': request}).data)

    def patch(self, request, pk):
        peer_review = self.get_object(request, pk)
        if peer_review.status == PeerReviewCorrection.Status.FINALIZED:
            return Response({"detail": "Correction participative déjà finalisée."}, status=status.HTTP_400_BAD_REQUEST)

        scores_data = request.data.get('scores_data', peer_review.scores_data or {})
        try:
            scores_data = _coerce_scores_to_float(scores_data)
            _validate_scores_against_bareme(peer_review.exam, scores_data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        annotations = request.data.get('annotations')
        remarks = request.data.get('remarks')

        with transaction.atomic():
            now = timezone.now()
            if peer_review.status == PeerReviewCorrection.Status.NOT_STARTED:
                peer_review.status = PeerReviewCorrection.Status.IN_PROGRESS
                peer_review.started_at = now
            peer_review.scores_data = scores_data
            peer_review.global_appreciation = request.data.get('global_appreciation', peer_review.global_appreciation or '')
            peer_review.final_comment = request.data.get('final_comment', peer_review.final_comment or '')
            peer_review.save()

            if isinstance(remarks, list):
                valid_qids = set()
                if peer_review.exam.grading_structure:
                    from exams.grading_utils import extract_leaf_questions
                    valid_qids = {q['id'] for q in extract_leaf_questions(peer_review.exam.grading_structure) if 'id' in q}
                for item in remarks:
                    question_id = item.get('question_id')
                    if not question_id:
                        continue
                    if valid_qids and question_id not in valid_qids:
                        continue
                    PeerReviewQuestionRemark.objects.update_or_create(
                        peer_review=peer_review,
                        question_id=question_id,
                        defaults={
                            'remark': item.get('remark', ''),
                            'points_awarded': item.get('points_awarded'),
                            'max_points': item.get('max_points'),
                        },
                    )

            if isinstance(annotations, list):
                peer_review.annotations.all().delete()
                for idx, item in enumerate(annotations):
                    serializer = PeerReviewAnnotationSerializer(data=item)
                    if not serializer.is_valid():
                        return Response(
                            {"detail": f"Annotation {idx + 1} invalide: {serializer.errors}"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    serializer.save(peer_review=peer_review)

            PeerReviewEvent.objects.create(
                peer_review=peer_review,
                actor=_event_actor(request, peer_review),
                action=PeerReviewEvent.Action.SAVE,
                metadata={'scores_count': len(scores_data or {})},
            )

        return Response(PeerReviewDetailSerializer(peer_review, context={'request': request}).data)


class StudentPeerReviewFinalizeView(StudentPeerReviewDetailView):
    def post(self, request, pk):
        peer_review = self.get_object(request, pk)
        if peer_review.status == PeerReviewCorrection.Status.FINALIZED:
            return Response({"detail": "Correction participative déjà finalisée."}, status=status.HTTP_400_BAD_REQUEST)

        # P0: Block finalization when no scores have been entered
        if not peer_review.scores_data:
            return Response(
                {"detail": "Impossible de finaliser : aucune note n'a été saisie."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check that at least one leaf question has a score
        from exams.grading_utils import extract_leaf_questions
        leaves = extract_leaf_questions(peer_review.exam.grading_structure) if peer_review.exam.grading_structure else []
        if leaves and not any(peer_review.scores_data.get(q['id']) is not None for q in leaves):
            return Response(
                {"detail": "Impossible de finaliser : aucune note n'a été saisie."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            if peer_review.status == PeerReviewCorrection.Status.NOT_STARTED:
                peer_review.started_at = timezone.now()
            peer_review.status = PeerReviewCorrection.Status.FINALIZED
            peer_review.finalized_at = timezone.now()
            peer_review.save(update_fields=['status', 'started_at', 'finalized_at', 'updated_at'])
            PeerReviewEvent.objects.create(
                peer_review=peer_review,
                actor=_event_actor(request, peer_review),
                action=PeerReviewEvent.Action.FINALIZE,
            )
        return Response(PeerReviewDetailSerializer(peer_review, context={'request': request}).data)


class TeacherExamPeerReviewListView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, exam_id):
        exam = get_object_or_404(Exam, id=exam_id)
        if not _teacher_can_supervise(request.user, exam):
            return Response({"detail": "Non autorisé pour cet examen."}, status=status.HTTP_403_FORBIDDEN)
        qs = (
            PeerReviewCorrection.objects
            .filter(exam=exam)
            .select_related('exam', 'source_copy', 'assigned_student')
            .order_by('source_copy__anonymous_id')
        )
        return Response(TeacherPeerReviewListSerializer(qs, many=True).data)


class TeacherPeerReviewDetailView(APIView):
    permission_classes = [IsTeacherOrAdmin]

    def get(self, request, pk):
        peer_review = get_object_or_404(
            PeerReviewCorrection.objects
            .select_related('exam', 'source_copy', 'assigned_student')
            .prefetch_related('source_copy__booklets', 'annotations', 'question_remarks'),
            id=pk,
        )
        if not _teacher_can_supervise(request.user, peer_review.exam):
            return Response({"detail": "Non autorisé pour cette correction."}, status=status.HTTP_403_FORBIDDEN)
        data = PeerReviewDetailSerializer(peer_review, context={'request': request}).data
        data['assigned_student'] = TeacherPeerReviewListSerializer(peer_review).data['assigned_student']
        return Response(data)
