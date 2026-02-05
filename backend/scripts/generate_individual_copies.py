#!/usr/bin/env python3
"""
Générateur de Copies Individuelles (A3 Landscape ↔ A4 Portrait)

Automatisation du découpage, de l'indexation et de la reconstruction
séquentielle des copies d'examen.

Algorithme de Mapping A3 → A4:
- Chaque feuille A3 = 1 "Leaf" (N)
- Page Impaire (1,3,5...): Droite→P1+4(N-1), Gauche→P4+4(N-1)
- Page Paire (2,4,6...): Droite→P3+4(N-1), Gauche→P2+4(N-1)

Usage:
    python generate_individual_copies.py --pdf scan.pdf --csv students.csv --output ./copies/

Author: Korrigo Team
PRD-19: Générateur de copies individuelles
"""
import os
import sys
import csv
import json
import logging
import argparse
import unicodedata
import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from difflib import SequenceMatcher

import fitz  # PyMuPDF
import cv2
import numpy as np

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass
class StudentRecord:
    """Enregistrement étudiant depuis le CSV."""
    id: int
    raw_name: str
    last_name: str
    first_name: str
    full_name_normalized: str
    date_of_birth: str
    classe: str = ""
    email: str = ""


@dataclass
class CopySegment:
    """Segment de copie identifié pour un élève."""
    student: Optional[StudentRecord]
    start_page_a3: int  # Index 0-based de la première page A3
    end_page_a3: int    # Index 0-based de la dernière page A3 (inclusive)
    leaf_count: int     # Nombre de feuilles A3 (paires impaire+paire)
    match_score: float
    ocr_name: str
    ocr_date: str
    status: str  # VALIDATED, AMBIGUOUS, NO_MATCH


@dataclass
class ProcessingResult:
    """Résultat du traitement d'une copie."""
    student_name: str
    output_file: str
    page_count: int
    status: str
    error: str = ""


class IndividualCopyGenerator:
    """
    Générateur de copies individuelles A4 Portrait depuis un scan A3 Landscape.
    """
    
    # Seuils de matching
    THRESHOLD_VALIDATED = 0.80
    THRESHOLD_AMBIGUOUS = 0.60
    
    def __init__(self, 
                 pdf_path: str,
                 csv_path: str,
                 output_dir: str,
                 api_key: str = None,
                 model: str = None,
                 dpi: int = 200):
        """
        Args:
            pdf_path: Chemin vers le PDF A3 scanné
            csv_path: Chemin vers le CSV des élèves
            output_dir: Répertoire de sortie pour les PDFs individuels
            api_key: Clé API OpenAI (ou depuis env)
            model: Modèle GPT-4 Vision (ou depuis env)
            dpi: Résolution pour l'analyse OCR
        """
        self.pdf_path = pdf_path
        self.csv_path = csv_path
        self.output_dir = output_dir
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.model = model or os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini-2025-04-14')
        self.dpi = dpi
        
        self.students: List[StudentRecord] = []
        self.segments: List[CopySegment] = []
        self.results: List[ProcessingResult] = []
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY env var.")
    
    def load_csv(self) -> List[StudentRecord]:
        """Charge le CSV des élèves comme référentiel."""
        self.students = []
        
        with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
            sample = f.read(2048)
            f.seek(0)
            delimiter = ';' if ';' in sample and ',' not in sample else ','
            reader = csv.DictReader(f, delimiter=delimiter)
            
            for idx, row in enumerate(reader):
                record = self._parse_csv_row(row, idx + 1)
                if record:
                    self.students.append(record)
        
        logger.info(f"Loaded {len(self.students)} students from CSV")
        return self.students
    
    def _parse_csv_row(self, row: Dict[str, str], idx: int) -> Optional[StudentRecord]:
        """Parse une ligne CSV."""
        name_cols = ['Élèves', 'Eleves', 'NOM', 'Nom', 'name', 'full_name']
        date_cols = ['Né(e) le', 'DATE_NAISSANCE', 'Date de naissance', 'dob']
        class_cols = ['Classe', 'CLASSE', 'class']
        email_cols = ['Adresse E-mail', 'Email', 'email']
        
        raw_name = next((row[c].strip() for c in name_cols if c in row and row[c].strip()), "")
        if not raw_name:
            return None
        
        parts = raw_name.split(' ', 1)
        last_name = parts[0].strip()
        first_name = parts[1].strip() if len(parts) > 1 else ""
        dob = next((row[c].strip() for c in date_cols if c in row and row[c].strip()), "")
        classe = next((row[c].strip() for c in class_cols if c in row and row[c].strip()), "")
        email = next((row[c].strip() for c in email_cols if c in row and row[c].strip()), "")
        
        return StudentRecord(
            id=idx,
            raw_name=raw_name,
            last_name=last_name,
            first_name=first_name,
            full_name_normalized=self._normalize_text(f"{last_name} {first_name}"),
            date_of_birth=dob,
            classe=classe,
            email=email
        )
    
    def _normalize_text(self, text: str) -> str:
        """Normalise le texte pour comparaison."""
        if not text:
            return ""
        text = text.upper()
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        text = re.sub(r'[^A-Z\s]', '', text)
        return ' '.join(text.split()).strip()
    
    def identify_segments(self) -> List[CopySegment]:
        """
        Phase 1: Identification des segments de copies.
        
        Analyse chaque page impaire pour identifier l'élève via OCR.
        Regroupe les pages consécutives appartenant au même élève.
        """
        doc = fitz.open(self.pdf_path)
        self.segments = []
        
        logger.info(f"Analyzing {doc.page_count} A3 pages for student identification...")
        
        current_segment = None
        
        for page_idx in range(doc.page_count):
            is_odd_page = (page_idx % 2 == 0)  # 0-indexed, so 0,2,4 are odd pages (1,3,5)
            
            if is_odd_page:
                # Extraire et analyser l'en-tête de la page impaire
                page = doc.load_page(page_idx)
                ocr_result = self._extract_header_ocr(page)
                
                # Matcher avec le CSV
                student, score = self._match_student(ocr_result)
                
                if score >= self.THRESHOLD_VALIDATED:
                    status = 'VALIDATED'
                elif score >= self.THRESHOLD_AMBIGUOUS:
                    status = 'AMBIGUOUS'
                else:
                    status = 'NO_MATCH'
                
                # Vérifier si c'est le même élève que le segment courant
                if current_segment and student and current_segment.student:
                    if student.id == current_segment.student.id:
                        # Même élève, étendre le segment
                        current_segment.end_page_a3 = page_idx + 1  # +1 pour inclure la page paire
                        current_segment.leaf_count += 1
                        continue
                
                # Nouveau segment
                if current_segment:
                    self.segments.append(current_segment)
                
                current_segment = CopySegment(
                    student=student,
                    start_page_a3=page_idx,
                    end_page_a3=page_idx + 1,  # Inclut la page paire suivante
                    leaf_count=1,
                    match_score=score,
                    ocr_name=f"{ocr_result.get('last_name', '')} {ocr_result.get('first_name', '')}".strip(),
                    ocr_date=ocr_result.get('date_of_birth', ''),
                    status=status
                )
                
                logger.info(f"Page {page_idx+1}: {current_segment.ocr_name} -> "
                           f"{student.raw_name if student else 'NO_MATCH'} [{status}]")
        
        # Ajouter le dernier segment
        if current_segment:
            self.segments.append(current_segment)
        
        doc.close()
        
        logger.info(f"Identified {len(self.segments)} copy segments")
        return self.segments
    
    def _extract_header_ocr(self, page: fitz.Page) -> Dict[str, str]:
        """Extrait les informations de l'en-tête via GPT-4 Vision."""
        import base64
        import openai
        
        # Rendre la page en image
        mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        elif pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        
        # Extraire le côté droit (page impaire) et le header (25% haut)
        h, w = img.shape[:2]
        mid_x = w // 2
        right_page = img[:, mid_x:]
        
        header_h = int(right_page.shape[0] * 0.25)
        header = right_page[:header_h, :]
        
        # Encoder en base64
        _, buffer = cv2.imencode('.jpg', header, [cv2.IMWRITE_JPEG_QUALITY, 95])
        base64_image = base64.b64encode(buffer).decode('utf-8')
        
        prompt = """Extract from this exam header:
1. NOM_MANUSCRIT: Last name from boxes after "Nom de famille:"
2. PRENOM_MANUSCRIT: First name from boxes after "Prénom(s):"
3. DOB_MANUSCRIT: Date of birth after "Né(e) le:" (DD/MM/YYYY)

Return JSON: {"last_name": "...", "first_name": "...", "date_of_birth": "..."}
Use "" if unreadable."""

        try:
            client = openai.OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}", "detail": "high"}}
                ]}],
                max_tokens=300,
                temperature=0.1
            )
            
            raw = response.choices[0].message.content
            json_match = re.search(r'\{[^}]+\}', raw, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    'last_name': data.get('last_name', '').strip().upper(),
                    'first_name': data.get('first_name', '').strip().upper(),
                    'date_of_birth': data.get('date_of_birth', '').strip()
                }
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
        
        return {'last_name': '', 'first_name': '', 'date_of_birth': ''}
    
    def _match_student(self, ocr: Dict[str, str]) -> Tuple[Optional[StudentRecord], float]:
        """Match OCR result avec le CSV."""
        if not ocr.get('last_name') and not ocr.get('first_name'):
            return None, 0.0
        
        ocr_name = self._normalize_text(f"{ocr.get('last_name', '')} {ocr.get('first_name', '')}")
        ocr_date = re.sub(r'[^\d]', '', ocr.get('date_of_birth', ''))
        
        best_match = None
        best_score = 0.0
        
        for student in self.students:
            name_score = SequenceMatcher(None, ocr_name, student.full_name_normalized).ratio()
            
            date_score = 0.0
            if ocr_date and student.date_of_birth:
                student_date = re.sub(r'[^\d]', '', student.date_of_birth)
                if ocr_date == student_date:
                    date_score = 1.0
                elif len(ocr_date) == 8 and len(student_date) == 8:
                    date_score = sum(1 for a, b in zip(ocr_date, student_date) if a == b) / 8
            
            total = 0.60 * name_score + 0.40 * date_score
            
            if total > best_score:
                best_score = total
                best_match = student
        
        return best_match, best_score
    
    def generate_individual_pdfs(self) -> List[ProcessingResult]:
        """
        Phase 2-4: Génération des PDFs individuels A4 Portrait.
        
        Pour chaque segment identifié:
        1. Découpe les pages A3 en deux moitiés
        2. Réordonne selon l'algorithme de mapping
        3. Assemble en PDF A4 Portrait
        """
        doc = fitz.open(self.pdf_path)
        self.results = []
        
        for segment in self.segments:
            if segment.status == 'NO_MATCH' or not segment.student:
                self.results.append(ProcessingResult(
                    student_name=segment.ocr_name or "UNKNOWN",
                    output_file="",
                    page_count=0,
                    status="SKIPPED",
                    error="No matching student found"
                ))
                continue
            
            try:
                result = self._generate_single_copy(doc, segment)
                self.results.append(result)
            except Exception as e:
                logger.error(f"Failed to generate copy for {segment.student.raw_name}: {e}")
                self.results.append(ProcessingResult(
                    student_name=segment.student.raw_name,
                    output_file="",
                    page_count=0,
                    status="FAILED",
                    error=str(e)
                ))
        
        doc.close()
        return self.results
    
    def _generate_single_copy(self, doc: fitz.Document, segment: CopySegment) -> ProcessingResult:
        """Génère un PDF individuel pour un segment."""
        student = segment.student
        
        # Nom du fichier: NOM_PRENOM_CLASSE.pdf
        safe_name = re.sub(r'[^A-Za-z0-9_-]', '_', student.raw_name)
        safe_classe = re.sub(r'[^A-Za-z0-9_-]', '_', student.classe) if student.classe else "UNKNOWN"
        output_filename = f"{safe_name}_{safe_classe}.pdf"
        output_path = os.path.join(self.output_dir, output_filename)
        
        # Collecter toutes les demi-pages avec leur index A4
        a4_pages = []  # List of (a4_index, page_image)
        
        leaf_n = 0  # Compteur de feuilles (N)
        
        for a3_idx in range(segment.start_page_a3, segment.end_page_a3 + 1):
            if a3_idx >= doc.page_count:
                break
            
            page = doc.load_page(a3_idx)
            is_odd = (a3_idx % 2 == 0)  # 0-indexed
            
            if is_odd:
                leaf_n += 1  # Nouvelle feuille à chaque page impaire
            
            # Calculer les index A4 selon l'algorithme
            if is_odd:
                # Page impaire: Droite→P1+4(N-1), Gauche→P4+4(N-1)
                right_idx = 1 + 4 * (leaf_n - 1)
                left_idx = 4 + 4 * (leaf_n - 1)
            else:
                # Page paire: Droite→P3+4(N-1), Gauche→P2+4(N-1)
                right_idx = 3 + 4 * (leaf_n - 1)
                left_idx = 2 + 4 * (leaf_n - 1)
            
            # Découper la page A3 en deux moitiés
            rect = page.rect
            mid_x = rect.width / 2
            
            left_rect = fitz.Rect(0, 0, mid_x, rect.height)
            right_rect = fitz.Rect(mid_x, 0, rect.width, rect.height)
            
            a4_pages.append((left_idx, page, left_rect))
            a4_pages.append((right_idx, page, right_rect))
        
        # Trier par index A4
        a4_pages.sort(key=lambda x: x[0])
        
        # Vérifier le nombre de pages (doit être multiple de 4)
        expected_pages = segment.leaf_count * 4
        actual_pages = len(a4_pages)
        
        if actual_pages != expected_pages:
            logger.warning(f"{student.raw_name}: Expected {expected_pages} pages, got {actual_pages}")
        
        # Créer le nouveau PDF A4
        output_doc = fitz.open()
        
        # Dimensions A4 Portrait (en points: 595 x 842)
        a4_width = 595
        a4_height = 842
        
        for idx, (a4_idx, src_page, crop_rect) in enumerate(a4_pages):
            # Créer une nouvelle page A4 Portrait
            new_page = output_doc.new_page(width=a4_width, height=a4_height)
            
            # Calculer le facteur d'échelle pour adapter la moitié A3 en A4
            src_width = crop_rect.width
            src_height = crop_rect.height
            
            scale_x = a4_width / src_width
            scale_y = a4_height / src_height
            scale = min(scale_x, scale_y)  # Conserver les proportions
            
            # Centrer sur la page
            dest_width = src_width * scale
            dest_height = src_height * scale
            offset_x = (a4_width - dest_width) / 2
            offset_y = (a4_height - dest_height) / 2
            
            dest_rect = fitz.Rect(offset_x, offset_y, offset_x + dest_width, offset_y + dest_height)
            
            # Insérer la portion de page
            new_page.show_pdf_page(dest_rect, doc, src_page.number, clip=crop_rect)
        
        # Sauvegarder
        output_doc.save(output_path)
        output_doc.close()
        
        logger.info(f"Generated: {output_filename} ({len(a4_pages)} pages)")
        
        return ProcessingResult(
            student_name=student.raw_name,
            output_file=output_path,
            page_count=len(a4_pages),
            status="SUCCESS"
        )
    
    def generate_report(self) -> str:
        """Génère le rapport processing_report.csv."""
        report_path = os.path.join(self.output_dir, "processing_report.csv")
        
        with open(report_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'student_name', 'output_file', 'page_count', 'status', 'error', 'timestamp'
            ])
            
            for result in self.results:
                writer.writerow([
                    result.student_name,
                    result.output_file,
                    result.page_count,
                    result.status,
                    result.error,
                    datetime.now().isoformat()
                ])
        
        logger.info(f"Report generated: {report_path}")
        return report_path
    
    def process(self) -> Dict[str, Any]:
        """Exécute le pipeline complet."""
        logger.info("="*60)
        logger.info("INDIVIDUAL COPY GENERATOR - A3 to A4 Conversion")
        logger.info("="*60)
        
        # 1. Charger le CSV
        self.load_csv()
        
        # 2. Identifier les segments
        self.identify_segments()
        
        # 3. Générer les PDFs individuels
        self.generate_individual_pdfs()
        
        # 4. Générer le rapport
        report_path = self.generate_report()
        
        # Résumé
        success = sum(1 for r in self.results if r.status == 'SUCCESS')
        failed = sum(1 for r in self.results if r.status == 'FAILED')
        skipped = sum(1 for r in self.results if r.status == 'SKIPPED')
        
        summary = {
            'total_segments': len(self.segments),
            'success': success,
            'failed': failed,
            'skipped': skipped,
            'report_path': report_path,
            'output_dir': self.output_dir
        }
        
        logger.info("="*60)
        logger.info("PROCESSING COMPLETE")
        logger.info(f"  Success: {success}")
        logger.info(f"  Failed: {failed}")
        logger.info(f"  Skipped: {skipped}")
        logger.info(f"  Report: {report_path}")
        logger.info("="*60)
        
        return summary


def main():
    parser = argparse.ArgumentParser(
        description='Generate individual A4 PDFs from A3 scanned exams'
    )
    parser.add_argument('--pdf', required=True, help='Path to A3 scanned PDF')
    parser.add_argument('--csv', required=True, help='Path to students CSV')
    parser.add_argument('--output', required=True, help='Output directory for individual PDFs')
    parser.add_argument('--api-key', help='OpenAI API key (or set OPENAI_API_KEY)')
    parser.add_argument('--model', help='GPT-4 Vision model (or set OPENAI_MODEL)')
    parser.add_argument('--dpi', type=int, default=200, help='DPI for OCR analysis')
    
    args = parser.parse_args()
    
    # Load .env if available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    generator = IndividualCopyGenerator(
        pdf_path=args.pdf,
        csv_path=args.csv,
        output_dir=args.output,
        api_key=args.api_key,
        model=args.model,
        dpi=args.dpi
    )
    
    summary = generator.process()
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
