#!/usr/bin/env python3
"""
Commande pour remplacer les images extraites d'une copie par celles d'un nouveau PDF.

Usage:
    python manage.py replace_copy_images <copy_id> --pdf-path <path>
    
Exemple:
    python manage.py replace_copy_images e4fab17c-b354-471d-9260-c380501880f0 \\
        --pdf-path /app/media/exams/individual/MNIF_YASMINE_28032011_Complet.pdf
"""

import fitz  # PyMuPDF
import os
import logging
from pathlib import Path
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
from django.db import transaction

from exams.models import Copy, Booklet
from core.utils.audit import log_data_access

logger = logging.getLogger(__name__)


def extract_pages_from_pdf(pdf_path, output_dir, copy_id, dpi=150):
    """
    Extrait toutes les pages d'un PDF en images PNG.
    
    Returns:
        List[str]: Liste des chemins relatifs des images extraites
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    doc = fitz.open(pdf_path)
    total_pages = doc.page_count
    pages_images = []
    
    logger.info(f"Extracting {total_pages} pages from {pdf_path}")
    
    for page_num in range(total_pages):
        page = doc.load_page(page_num)
        
        # Render page to image
        mat = fitz.Matrix(dpi/72, dpi/72)  # Convert DPI to matrix
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # Generate filename
        safe_copy_id = str(copy_id)[:8]
        filename = f"copy_{safe_copy_id}_page_{page_num + 1:03d}.png"
        relative_path = f"copies/pages/{filename}"
        full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        # Save image
        pix.save(full_path)
        pages_images.append(relative_path)
        
        logger.info(f"  Extracted page {page_num + 1}/{total_pages} -> {relative_path}")
    
    doc.close()
    return pages_images


def replace_copy_images(copy_id, pdf_path, dry_run=False):
    """
    Remplace les images des booklets d'une copie par celles extraites d'un nouveau PDF.
    
    Args:
        copy_id: UUID de la copie
        pdf_path: Chemin vers le nouveau PDF source
        dry_run: Si True, ne fait pas les modifications
    
    Returns:
        dict: Résultat de l'opération
    """
    try:
        copy = Copy.objects.get(id=copy_id)
    except Copy.DoesNotExist:
        raise ValueError(f"Copy {copy_id} not found")
    
    logger.info(f"Processing copy {copy_id} (Anonymous ID: {copy.anonymous_id})")
    logger.info(f"New PDF: {pdf_path}")
    
    # Get current booklets
    booklets = list(copy.booklets.all().order_by('start_page'))
    if not booklets:
        raise ValueError(f"Copy {copy_id} has no booklets")
    
    logger.info(f"Found {len(booklets)} booklets")
    
    # Backup current state
    backup_data = {
        'copy_id': str(copy_id),
        'booklets': []
    }
    for b in booklets:
        backup_data['booklets'].append({
            'id': str(b.id),
            'pages_images': b.pages_images.copy() if b.pages_images else []
        })
    
    logger.info(f"Backup created: {len(backup_data['booklets'])} booklets")
    
    if dry_run:
        logger.info("DRY RUN - No changes will be made")
        return {
            'success': True,
            'dry_run': True,
            'copy_id': str(copy_id),
            'booklets_count': len(booklets),
            'backup': backup_data
        }
    
    # Extract new images
    logger.info("Extracting new images...")
    new_pages_images = extract_pages_from_pdf(
        pdf_path, 
        f"copies/pages/", 
        copy_id,
        dpi=150
    )
    
    logger.info(f"Extracted {len(new_pages_images)} new images")
    
    # Calculate pages per booklet from first booklet
    first_booklet = booklets[0]
    pages_per_booklet = first_booklet.end_page - first_booklet.start_page + 1
    logger.info(f"Pages per booklet: {pages_per_booklet}")
    
    # Distribute images to booklets
    with transaction.atomic():
        page_idx = 0
        for i, booklet in enumerate(booklets):
            # Calculate how many pages for this booklet
            expected_pages = pages_per_booklet
            if i == len(booklets) - 1:  # Last booklet may have fewer pages
                expected_pages = len(new_pages_images) - page_idx
            
            booklet_pages = new_pages_images[page_idx:page_idx + expected_pages]
            
            # Update booklet
            old_images = booklet.pages_images.copy() if booklet.pages_images else []
            booklet.pages_images = booklet_pages
            booklet.save()
            
            logger.info(f"  Booklet {booklet.id}: {len(old_images)} -> {len(booklet_pages)} images")
            
            page_idx += len(booklet_pages)
        
        # Log audit event
        log_data_access(
            None,  # No request in management command
            'Copy',
            copy.id,
            action_detail=f'Replaced images from new PDF: {pdf_path}'
        )
    
    return {
        'success': True,
        'copy_id': str(copy_id),
        'booklets_updated': len(booklets),
        'total_pages': len(new_pages_images),
        'backup': backup_data
    }


if __name__ == '__main__':
    import django
    django.setup()
    
    import sys
    if len(sys.argv) < 3:
        print("Usage: python replace_copy_images.py <copy_id> <pdf_path>")
        sys.exit(1)
    
    copy_id = sys.argv[1]
    pdf_path = sys.argv[2]
    
    try:
        result = replace_copy_images(copy_id, pdf_path)
        print(f"\n✅ Success!")
        print(f"Copy: {result['copy_id']}")
        print(f"Booklets updated: {result['booklets_updated']}")
        print(f"Total pages: {result['total_pages']}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
