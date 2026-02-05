"""
GPT-4 Vision OCR Service for CMEN V2 Headers.

This service uses OpenAI's GPT-4 Vision model to extract student information
from CMEN V2 headers with handwritten text. GPT-4V is excellent at reading
handwritten text and understanding form structures.

Usage:
    service = GPT4VisionOCR(api_key="sk-...")
    result = service.extract_from_header(header_image)

Author: Korrigo Team
PRD-19: GPT-4 Vision OCR for 100% accuracy
"""
import cv2
import numpy as np
import base64
import logging
import re
import os
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class GPT4OCRResult:
    """Result of GPT-4 Vision OCR extraction."""
    last_name: str
    first_name: str
    date_of_birth: str
    raw_response: str
    confidence: float
    status: str  # OK, PARTIAL, FAILED


@dataclass
class StudentMatch:
    """A matched student from the whitelist."""
    student_id: Any
    last_name: str
    first_name: str
    full_name: str
    date_of_birth: str
    email: str
    score: float


class GPT4VisionOCR:
    """
    OCR service using GPT-4 Vision for CMEN V2 headers.
    
    GPT-4V can accurately read handwritten text in individual boxes,
    which is difficult for traditional OCR engines like Tesseract.
    """
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        Args:
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var.
            model: Model to use. If None, reads from OPENAI_MODEL env var or defaults to gpt-4.1-mini.
        """
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.model = model or os.environ.get('OPENAI_MODEL', 'gpt-4.1-mini-2025-04-14')
        
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY or pass api_key parameter.")
    
    def extract_from_header(self, header_image: np.ndarray) -> GPT4OCRResult:
        """
        Extract student information from a CMEN V2 header image using GPT-4 Vision.
        
        Args:
            header_image: BGR image of the header
            
        Returns:
            GPT4OCRResult with extracted fields
        """
        logger.info("Starting GPT-4 Vision OCR extraction...")
        
        # Convert image to base64
        base64_image = self._image_to_base64(header_image)
        
        # Create prompt for GPT-4V
        prompt = """Analyze this CMEN V2 exam header image. Extract the following information from the handwritten text in the boxes:

1. **Nom de famille** (Last name): The letters written in the boxes after "Nom de famille:"
2. **Prénom(s)** (First name): The letters written in the boxes after "Prénom(s):"
3. **Date de naissance** (Date of birth): The date written after "Né(e) le:" in format DD/MM/YYYY

IMPORTANT:
- Read each handwritten letter carefully from the individual boxes
- The text is in UPPERCASE
- Return ONLY the extracted values, nothing else
- If a field is empty or unreadable, return "UNKNOWN"

Respond in this exact JSON format:
{
    "last_name": "EXTRACTED_LAST_NAME",
    "first_name": "EXTRACTED_FIRST_NAME", 
    "date_of_birth": "DD/MM/YYYY"
}"""

        try:
            import openai
            
            client = openai.OpenAI(api_key=self.api_key)
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            raw_response = response.choices[0].message.content
            logger.info(f"GPT-4V response: {raw_response}")
            
            # Parse JSON response
            result = self._parse_response(raw_response)
            
            return result
            
        except Exception as e:
            logger.error(f"GPT-4 Vision OCR failed: {e}")
            return GPT4OCRResult(
                last_name="",
                first_name="",
                date_of_birth="",
                raw_response=str(e),
                confidence=0.0,
                status="FAILED"
            )
    
    def _image_to_base64(self, image: np.ndarray) -> str:
        """Convert numpy image to base64 string."""
        # Encode as JPEG
        _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return base64.b64encode(buffer).decode('utf-8')
    
    def _parse_response(self, response: str) -> GPT4OCRResult:
        """Parse GPT-4V response into structured result."""
        import json
        
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                # Try parsing the whole response as JSON
                data = json.loads(response)
            
            last_name = data.get('last_name', '').strip().upper()
            first_name = data.get('first_name', '').strip().upper()
            date_of_birth = data.get('date_of_birth', '').strip()
            
            # Clean up "UNKNOWN" values
            if last_name == "UNKNOWN":
                last_name = ""
            if first_name == "UNKNOWN":
                first_name = ""
            if date_of_birth == "UNKNOWN":
                date_of_birth = ""
            
            # Calculate confidence
            confidence = 0.0
            if last_name:
                confidence += 0.4
            if first_name:
                confidence += 0.2
            if date_of_birth and re.match(r'\d{2}/\d{2}/\d{4}', date_of_birth):
                confidence += 0.4
            
            # Determine status
            if last_name and date_of_birth:
                status = "OK"
            elif last_name or first_name:
                status = "PARTIAL"
            else:
                status = "FAILED"
            
            logger.info(f"Extracted: name='{last_name}', firstname='{first_name}', "
                       f"dob='{date_of_birth}', confidence={confidence:.2f}")
            
            return GPT4OCRResult(
                last_name=last_name,
                first_name=first_name,
                date_of_birth=date_of_birth,
                raw_response=response,
                confidence=confidence,
                status=status
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            
            # Try to extract fields manually
            last_name = ""
            first_name = ""
            date_of_birth = ""
            
            # Look for patterns
            name_match = re.search(r'last_name["\s:]+([A-Z\s\-]+)', response, re.IGNORECASE)
            if name_match:
                last_name = name_match.group(1).strip()
            
            firstname_match = re.search(r'first_name["\s:]+([A-Z\s\-]+)', response, re.IGNORECASE)
            if firstname_match:
                first_name = firstname_match.group(1).strip()
            
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', response)
            if date_match:
                date_of_birth = date_match.group(1)
            
            confidence = 0.3 if (last_name or first_name or date_of_birth) else 0.0
            
            return GPT4OCRResult(
                last_name=last_name,
                first_name=first_name,
                date_of_birth=date_of_birth,
                raw_response=response,
                confidence=confidence,
                status="PARTIAL" if confidence > 0 else "FAILED"
            )
    
    def match_student(self,
                      ocr_result: GPT4OCRResult,
                      students: List[Dict[str, Any]],
                      threshold: float = 0.70,
                      margin: float = 0.10) -> tuple:
        """
        Match OCR result against student whitelist.
        
        Args:
            ocr_result: Result from extract_from_header()
            students: List of student records
            threshold: Minimum score for auto-match
            margin: Minimum margin between best and second-best
            
        Returns:
            Tuple of (best_match or None, all_candidates)
        """
        if not students or ocr_result.status == "FAILED":
            return None, []
        
        candidates = []
        
        for student in students:
            s_last = self._normalize(student.get('last_name', ''))
            s_first = self._normalize(student.get('first_name', ''))
            s_date = student.get('date_of_birth', '')
            
            # Calculate name similarity
            name_score = self._similarity(
                self._normalize(ocr_result.last_name),
                s_last
            )
            
            firstname_score = self._similarity(
                self._normalize(ocr_result.first_name),
                s_first
            )
            
            # Calculate date similarity
            date_score = self._date_similarity(ocr_result.date_of_birth, s_date)
            
            # Combined score (date is most important)
            total_score = 0.35 * name_score + 0.15 * firstname_score + 0.50 * date_score
            
            candidates.append(StudentMatch(
                student_id=student.get('id'),
                last_name=student.get('last_name', ''),
                first_name=student.get('first_name', ''),
                full_name=student.get('full_name', f"{s_last} {s_first}"),
                date_of_birth=s_date,
                email=student.get('email', ''),
                score=total_score
            ))
        
        # Sort by score
        candidates.sort(key=lambda x: x.score, reverse=True)
        
        # Check threshold and margin
        if candidates:
            best = candidates[0]
            second = candidates[1] if len(candidates) > 1 else None
            actual_margin = best.score - (second.score if second else 0)
            
            if best.score >= threshold and actual_margin >= margin:
                logger.info(f"AUTO_MATCH: {best.full_name} (score={best.score:.3f})")
                return best, candidates[:10]
        
        return None, candidates[:10]
    
    def _normalize(self, text: str) -> str:
        """Normalize text for matching."""
        if not text:
            return ''
        import unicodedata
        text = text.upper()
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        text = re.sub(r'[^A-Z\s]', '', text)
        return ' '.join(text.split()).strip()
    
    def _similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity."""
        if not s1 or not s2:
            return 0.0
        if s1 == s2:
            return 1.0
        return SequenceMatcher(None, s1, s2).ratio()
    
    def _date_similarity(self, d1: str, d2: str) -> float:
        """Calculate date similarity."""
        if not d1 or not d2:
            return 0.0
        
        d1_clean = re.sub(r'[^\d]', '', d1)
        d2_clean = re.sub(r'[^\d]', '', d2)
        
        if d1_clean == d2_clean:
            return 1.0
        
        if len(d1_clean) == 8 and len(d2_clean) == 8:
            matches = sum(1 for a, b in zip(d1_clean, d2_clean) if a == b)
            return matches / 8
        
        return self._similarity(d1_clean, d2_clean)


def process_pdf_with_gpt4v(pdf_path: str, 
                           csv_students: List[Dict],
                           api_key: str,
                           output_dir: str = None,
                           max_pages: int = None) -> List[Dict]:
    """
    Process a PDF using GPT-4 Vision OCR.
    
    Args:
        pdf_path: Path to PDF file
        csv_students: List of student records from CSV
        api_key: OpenAI API key
        output_dir: Optional output directory for debug images
        max_pages: Maximum pages to process (for testing)
        
    Returns:
        List of results per page
    """
    import fitz
    from pathlib import Path
    
    if output_dir:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    doc = fitz.open(pdf_path)
    service = GPT4VisionOCR(api_key=api_key)
    
    results = []
    dpi = 200
    
    # Check if A3
    page = doc.load_page(0)
    ratio = page.rect.width / page.rect.height
    is_a3 = ratio > 1.2
    
    logger.info(f"Processing PDF: {doc.page_count} pages, format={'A3' if is_a3 else 'A4'}")
    
    page_num = 0
    pages_processed = 0
    
    for page_idx in range(doc.page_count):
        if max_pages and pages_processed >= max_pages:
            break
            
        page = doc.load_page(page_idx)
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        elif pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        
        pages_to_process = []
        
        if is_a3:
            mid_x = img.shape[1] // 2
            # Only process right side (has header) for A3
            pages_to_process = [
                (img[:, mid_x:], f"A3_{page_idx+1}_right")
            ]
        else:
            pages_to_process = [(img, f"A4_{page_idx+1}")]
        
        for page_img, page_name in pages_to_process:
            if max_pages and pages_processed >= max_pages:
                break
                
            page_num += 1
            
            # Extract header (top 25%)
            header_h = int(page_img.shape[0] * 0.25)
            header = page_img[:header_h, :]
            
            # Run GPT-4V OCR
            ocr_result = service.extract_from_header(header)
            
            # Match against students
            best_match, candidates = service.match_student(ocr_result, csv_students)
            
            status = "AUTO_MATCH" if best_match else ("AMBIGUOUS" if candidates else "NO_MATCH")
            
            results.append({
                'page_num': page_num,
                'page_name': page_name,
                'ocr_result': ocr_result,
                'status': status,
                'best_match': best_match,
                'candidates': candidates[:5],
            })
            
            if output_dir:
                cv2.imwrite(f"{output_dir}/{page_name}_header.png", header)
            
            match_info = f"✓ {best_match.full_name}" if best_match else "✗"
            logger.info(f"Page {page_num}: {ocr_result.last_name} {ocr_result.first_name} "
                       f"({ocr_result.date_of_birth}) -> {status} {match_info}")
            
            pages_processed += 1
    
    doc.close()
    return results
