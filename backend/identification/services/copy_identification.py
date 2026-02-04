"""
Service d'identification des copies avec protection anti-doublons.

PRD-19: Garantit qu'un seul Copy identifié existe par (exam, student).
Si une seconde copie est identifiée pour le même élève, fusion automatique.
"""
import logging
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from exams.models import Copy, Booklet
from grading.models import GradingEvent, Annotation, QuestionScore, QuestionRemark

logger = logging.getLogger(__name__)


class DuplicateCopyError(Exception):
    """Raised when duplicate copy detection fails."""
    pass


class CopyIdentificationService:
    """
    Service transactionnel pour l'identification des copies.
    
    Garanties:
    - Un seul Copy identifié par (exam, student)
    - Fusion automatique si doublon détecté
    - Race-condition safe via select_for_update
    - Audit trail complet
    """

    @staticmethod
    @transaction.atomic
    def identify_copy(copy_id: str, student_id: str, user, method: str = 'manual') -> dict:
        """
        Identifie une copie avec protection anti-doublons.
        
        Si une copie existe déjà pour cet élève sur cet examen:
        - Fusionne les booklets dans la copie existante
        - Supprime la copie doublon
        - Journalise l'opération
        
        Args:
            copy_id: UUID de la copie à identifier
            student_id: UUID de l'élève
            user: Utilisateur effectuant l'identification
            method: 'manual', 'ocr_assisted', 'auto'
            
        Returns:
            dict avec copy_id final, merged (bool), message
            
        Raises:
            ValueError: Si copie ou élève non trouvé, ou statut invalide
        """
        from students.models import Student
        
        # 1. Verrouiller la copie source
        try:
            copy = Copy.objects.select_for_update().get(id=copy_id)
        except Copy.DoesNotExist:
            raise ValueError(f"Copie {copy_id} non trouvée")
        
        # 2. Vérifier le statut
        allowed_statuses = [Copy.Status.READY, Copy.Status.LOCKED]
        if copy.status not in allowed_statuses:
            if copy.status == Copy.Status.STAGING:
                raise ValueError("Copie en STAGING - doit être agrafée avant identification")
            raise ValueError(f"Impossible d'identifier une copie en statut {copy.status}")
        
        # 3. Récupérer l'élève
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            raise ValueError(f"Élève {student_id} non trouvé")
        
        # 4. Vérifier si une copie existe déjà pour cet élève sur cet examen
        existing_copy = (
            Copy.objects
            .select_for_update()
            .filter(
                exam=copy.exam,
                student=student,
                is_identified=True
            )
            .exclude(id=copy.id)
            .first()
        )
        
        if existing_copy:
            # FUSION: Transférer les booklets vers la copie existante
            return CopyIdentificationService._merge_copies(
                source_copy=copy,
                target_copy=existing_copy,
                student=student,
                user=user,
                method=method
            )
        
        # 5. Pas de doublon - identification simple
        copy.student = student
        copy.is_identified = True
        if not copy.validated_at:
            copy.validated_at = timezone.now()
        copy.save()
        
        # 6. Audit trail
        GradingEvent.objects.create(
            copy=copy,
            action=GradingEvent.Action.VALIDATE,
            actor=user,
            metadata={
                'student_id': str(student.id),
                'student_name': student.full_name,
                'method': method,
                'merged': False
            }
        )
        
        logger.info(f"Copy {copy.id} identified as {student.full_name} (method={method})")
        
        return {
            'copy_id': str(copy.id),
            'student_id': str(student.id),
            'student_name': student.full_name,
            'merged': False,
            'message': 'Copie identifiée avec succès'
        }

    @staticmethod
    def _merge_copies(source_copy: Copy, target_copy: Copy, student, user, method: str) -> dict:
        """
        Fusionne source_copy dans target_copy.
        
        - Transfère tous les booklets
        - Transfère les annotations (si existantes)
        - Supprime source_copy
        - Journalise l'opération
        """
        logger.warning(
            f"MERGE DETECTED: Copy {source_copy.id} will be merged into {target_copy.id} "
            f"for student {student.full_name}"
        )
        
        # 1. Transférer les booklets
        source_booklets = list(source_copy.booklets.all())
        booklet_ids = [str(b.id) for b in source_booklets]
        
        for booklet in source_booklets:
            target_copy.booklets.add(booklet)
        
        # 2. Transférer les annotations (si existantes)
        annotations_transferred = 0
        for annotation in source_copy.annotations.all():
            annotation.copy = target_copy
            annotation.save()
            annotations_transferred += 1
        
        # 3. Transférer les scores de questions
        scores_transferred = 0
        for score in source_copy.question_scores.all():
            # Vérifier si un score existe déjà pour cette question
            existing = QuestionScore.objects.filter(
                copy=target_copy,
                question_id=score.question_id
            ).first()
            if not existing:
                score.copy = target_copy
                score.save()
                scores_transferred += 1
        
        # 4. Transférer les remarques
        remarks_transferred = 0
        for remark in source_copy.question_remarks.all():
            existing = QuestionRemark.objects.filter(
                copy=target_copy,
                question_id=remark.question_id
            ).first()
            if not existing:
                remark.copy = target_copy
                remark.save()
                remarks_transferred += 1
        
        # 5. Journaliser la fusion AVANT suppression
        GradingEvent.objects.create(
            copy=target_copy,
            action=GradingEvent.Action.VALIDATE,
            actor=user,
            metadata={
                'student_id': str(student.id),
                'student_name': student.full_name,
                'method': method,
                'merged': True,
                'merged_from_copy_id': str(source_copy.id),
                'merged_from_anonymous_id': source_copy.anonymous_id,
                'booklets_transferred': booklet_ids,
                'annotations_transferred': annotations_transferred,
                'scores_transferred': scores_transferred,
                'remarks_transferred': remarks_transferred
            }
        )
        
        # 6. Supprimer la copie source
        source_anonymous_id = source_copy.anonymous_id
        source_copy.delete()
        
        logger.info(
            f"MERGE COMPLETE: Copy {source_anonymous_id} merged into {target_copy.anonymous_id}. "
            f"Transferred: {len(booklet_ids)} booklets, {annotations_transferred} annotations, "
            f"{scores_transferred} scores, {remarks_transferred} remarks"
        )
        
        return {
            'copy_id': str(target_copy.id),
            'student_id': str(student.id),
            'student_name': student.full_name,
            'merged': True,
            'merged_from': source_anonymous_id,
            'booklets_transferred': len(booklet_ids),
            'message': f'Copie fusionnée avec la copie existante {target_copy.anonymous_id}'
        }

    @staticmethod
    def check_for_duplicates(exam_id: str) -> list:
        """
        Vérifie s'il existe des doublons (plusieurs copies identifiées pour le même élève).
        
        Returns:
            Liste des doublons détectés avec détails
        """
        from django.db.models import Count
        
        duplicates = (
            Copy.objects
            .filter(exam_id=exam_id, is_identified=True, student__isnull=False)
            .values('student_id', 'student__full_name')
            .annotate(copy_count=Count('id'))
            .filter(copy_count__gt=1)
        )
        
        result = []
        for dup in duplicates:
            copies = Copy.objects.filter(
                exam_id=exam_id,
                student_id=dup['student_id'],
                is_identified=True
            ).values('id', 'anonymous_id', 'status', 'validated_at')
            
            result.append({
                'student_id': str(dup['student_id']),
                'student_name': dup['student__full_name'],
                'copy_count': dup['copy_count'],
                'copies': list(copies)
            })
        
        return result

    @staticmethod
    @transaction.atomic
    def fix_duplicates(exam_id: str, user) -> dict:
        """
        Corrige automatiquement les doublons en fusionnant les copies.
        
        Stratégie: Garde la copie la plus ancienne, fusionne les autres dedans.
        
        Returns:
            dict avec nombre de fusions effectuées
        """
        duplicates = CopyIdentificationService.check_for_duplicates(exam_id)
        
        merges_done = 0
        for dup in duplicates:
            copies = list(
                Copy.objects
                .select_for_update()
                .filter(
                    exam_id=exam_id,
                    student_id=dup['student_id'],
                    is_identified=True
                )
                .order_by('validated_at', 'id')  # Plus ancienne en premier
            )
            
            if len(copies) < 2:
                continue
            
            target = copies[0]  # Garder la plus ancienne
            student = target.student
            
            for source in copies[1:]:
                CopyIdentificationService._merge_copies(
                    source_copy=source,
                    target_copy=target,
                    student=student,
                    user=user,
                    method='auto_fix_duplicates'
                )
                merges_done += 1
        
        logger.info(f"Fixed {merges_done} duplicate copies for exam {exam_id}")
        
        return {
            'exam_id': str(exam_id),
            'duplicates_found': len(duplicates),
            'merges_done': merges_done
        }
