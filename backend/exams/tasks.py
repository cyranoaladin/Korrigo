"""
Celery tasks pour l'extraction de texte des documents PDF (sujet, corrigé, barème).
Pipeline : extraction page par page → chunking par exercice/question → indexation.
"""
import re
import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def process_document_set(self, document_set_id):
    """
    Traite tous les documents d'un lot documentaire :
    extraction texte + chunking + indexation.
    """
    from exams.models import ExamDocumentSet, DocumentTextExtraction

    try:
        doc_set = ExamDocumentSet.objects.get(id=document_set_id)
    except ExamDocumentSet.DoesNotExist:
        logger.error(f"DocumentSet {document_set_id} introuvable.")
        return {'status': 'error', 'detail': 'DocumentSet introuvable'}

    results = []
    for doc in doc_set.documents.all():
        extraction = doc.extractions.filter(
            status__in=['pending', 'failed']
        ).order_by('-created_at').first()

        if not extraction:
            extraction = DocumentTextExtraction.objects.create(
                document=doc,
                status=DocumentTextExtraction.Status.PENDING,
                engine='pymupdf'
            )

        result = process_single_document(str(extraction.id))
        results.append(result)

    return {'status': 'done', 'results': results}


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def process_single_document(self, extraction_id):
    """
    Extrait le texte d'un document PDF page par page,
    puis découpe en chunks par exercice/question.
    """
    import os
    from django.conf import settings
    from exams.models import (
        DocumentTextExtraction,
        DocumentPage,
        DocumentChunk,
    )

    try:
        extraction = DocumentTextExtraction.objects.select_related('document').get(id=extraction_id)
    except DocumentTextExtraction.DoesNotExist:
        logger.error(f"Extraction {extraction_id} introuvable.")
        return {'status': 'error', 'detail': 'Extraction introuvable'}

    document = extraction.document
    extraction.status = DocumentTextExtraction.Status.PROCESSING
    extraction.save(update_fields=['status'])

    try:
        import fitz

        abs_path = os.path.join(settings.MEDIA_ROOT, document.storage_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Fichier introuvable : {abs_path}")

        pdf = fitz.open(abs_path)

        # --- Étape 1 : Extraction page par page ---
        DocumentPage.objects.filter(extraction=extraction).delete()
        pages_text = []
        for page_num in range(pdf.page_count):
            page = pdf[page_num]
            text = page.get_text()
            DocumentPage.objects.create(
                extraction=extraction,
                page_number=page_num + 1,
                page_text=text
            )
            pages_text.append((page_num + 1, text))

        pdf.close()

        # --- Étape 2 : Chunking intelligent ---
        DocumentChunk.objects.filter(extraction=extraction).delete()
        doc_type = document.doc_type
        chunks = _chunk_document(pages_text, doc_type)

        for i, chunk in enumerate(chunks):
            DocumentChunk.objects.create(
                extraction=extraction,
                doc_type=doc_type,
                chunk_index=i,
                page_start=chunk.get('page_start'),
                page_end=chunk.get('page_end'),
                exercise_number=chunk.get('exercise_number'),
                question_label=chunk.get('question_label', ''),
                chunk_text=chunk['text'],
                tags=chunk.get('tags', [])
            )

        extraction.status = DocumentTextExtraction.Status.DONE
        extraction.extracted_at = timezone.now()
        extraction.error_message = None
        extraction.save(update_fields=['status', 'extracted_at', 'error_message'])

        logger.info(
            f"Extraction réussie : {document.original_filename} "
            f"({len(pages_text)} pages, {len(chunks)} chunks)"
        )

        return {
            'status': 'done',
            'document_id': str(document.id),
            'pages': len(pages_text),
            'chunks': len(chunks),
        }

    except Exception as exc:
        extraction.status = DocumentTextExtraction.Status.FAILED
        extraction.error_message = str(exc)[:500]
        extraction.save(update_fields=['status', 'error_message'])
        logger.error(f"Extraction échouée pour {document.original_filename}: {exc}", exc_info=True)
        return {'status': 'error', 'detail': str(exc)}


def _chunk_document(pages_text, doc_type):
    """
    Découpe le texte extrait en segments exploitables.
    
    Pour le barème : découpe par exercice → question → critères.
    Pour le corrigé/sujet : découpe par exercice → question.
    
    Args:
        pages_text: list of (page_number, text)
        doc_type: 'sujet', 'corrige', 'bareme'
    
    Returns:
        list of chunk dicts with keys: text, page_start, page_end,
        exercise_number, question_label, tags
    """
    full_text = "\n".join(text for _, text in pages_text)
    
    # Patterns pour détecter les exercices et questions
    exercise_pattern = re.compile(
        r'(?:EXERCICE|Exercice)\s*(\d+)',
        re.IGNORECASE
    )
    question_pattern = re.compile(
        r'^(?:Q|Question\s*)?(\d+[a-z]?(?:\.\d+)?)\b',
        re.MULTILINE | re.IGNORECASE
    )
    # Pattern spécifique barème : lignes avec "Pts" ou points numériques
    bareme_question_pattern = re.compile(
        r'^([A-Z]?\d+[a-z]?(?:\.\d+)?)\s*$',
        re.MULTILINE
    )

    chunks = []
    
    # Découper par exercice d'abord
    exercise_splits = list(exercise_pattern.finditer(full_text))
    
    if not exercise_splits:
        # Pas de structure exercice détectée → un seul chunk
        page_start = pages_text[0][0] if pages_text else None
        page_end = pages_text[-1][0] if pages_text else None
        chunks.append({
            'text': full_text.strip(),
            'page_start': page_start,
            'page_end': page_end,
            'exercise_number': None,
            'question_label': '',
            'tags': [doc_type],
        })
        return chunks

    for idx, match in enumerate(exercise_splits):
        ex_num = int(match.group(1))
        start = match.start()
        end = exercise_splits[idx + 1].start() if idx + 1 < len(exercise_splits) else len(full_text)
        ex_text = full_text[start:end].strip()

        # Trouver les pages couvertes
        page_start = _find_page_for_offset(pages_text, start, full_text)
        page_end = _find_page_for_offset(pages_text, end - 1, full_text)

        if doc_type == 'bareme':
            # Pour le barème, découper plus finement par question
            q_chunks = _chunk_bareme_exercise(ex_text, ex_num, page_start, page_end)
            if q_chunks:
                chunks.extend(q_chunks)
            else:
                chunks.append({
                    'text': ex_text,
                    'page_start': page_start,
                    'page_end': page_end,
                    'exercise_number': ex_num,
                    'question_label': '',
                    'tags': [doc_type, f'exercice_{ex_num}'],
                })
        else:
            # Pour sujet/corrigé, découper par question si possible
            q_splits = list(question_pattern.finditer(ex_text))
            if len(q_splits) > 1:
                for qi, qm in enumerate(q_splits):
                    q_start = qm.start()
                    q_end = q_splits[qi + 1].start() if qi + 1 < len(q_splits) else len(ex_text)
                    q_text = ex_text[q_start:q_end].strip()
                    q_label = qm.group(1)
                    chunks.append({
                        'text': q_text,
                        'page_start': page_start,
                        'page_end': page_end,
                        'exercise_number': ex_num,
                        'question_label': q_label,
                        'tags': [doc_type, f'exercice_{ex_num}', f'question_{q_label}'],
                    })
            else:
                chunks.append({
                    'text': ex_text,
                    'page_start': page_start,
                    'page_end': page_end,
                    'exercise_number': ex_num,
                    'question_label': '',
                    'tags': [doc_type, f'exercice_{ex_num}'],
                })

    return chunks


def _chunk_bareme_exercise(ex_text, ex_num, page_start, page_end):
    """
    Découpe un exercice du barème en chunks par question.
    Détecte les patterns : numéro de question suivi de critères et points.
    """
    # Pattern : ligne commençant par un label de question (1, 2, 3a, 3b, A.1, B.2, etc.)
    q_pattern = re.compile(
        r'^([A-Z]?\d+[a-z]?(?:\.\d+)?)\s*\n',
        re.MULTILINE
    )
    
    matches = list(q_pattern.finditer(ex_text))
    if not matches:
        return []

    chunks = []
    for i, m in enumerate(matches):
        q_label = m.group(1)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(ex_text)
        q_text = ex_text[start:end].strip()

        # Détecter les tags automatiquement
        tags = ['bareme', f'exercice_{ex_num}', f'question_{q_label}']
        text_lower = q_text.lower()
        if 'plaf' in text_lower or 'plafond' in text_lower:
            tags.append('plafond')
        if 'erreur' in text_lower:
            tags.append('erreur_typique')
        if 'méthode' in text_lower or 'methode' in text_lower:
            tags.append('methode')
        if 'justification' in text_lower:
            tags.append('justification')
        if 'report en cascade' in text_lower:
            tags.append('report_cascade')

        chunks.append({
            'text': q_text,
            'page_start': page_start,
            'page_end': page_end,
            'exercise_number': ex_num,
            'question_label': q_label,
            'tags': tags,
        })

    return chunks


def _find_page_for_offset(pages_text, char_offset, full_text):
    """
    Trouve le numéro de page correspondant à un offset de caractère
    dans le texte concaténé.
    """
    current_offset = 0
    for page_num, text in pages_text:
        current_offset += len(text) + 1  # +1 for \n separator
        if current_offset > char_offset:
            return page_num
    return pages_text[-1][0] if pages_text else None
