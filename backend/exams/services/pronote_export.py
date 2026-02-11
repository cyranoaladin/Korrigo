"""
PRONOTE CSV Export Service

Generates PRONOTE-compatible CSV files for grade import.
Format: INE;MATIERE;NOTE;COEFF;COMMENTAIRE

Specification:
- Encoding: UTF-8 with BOM
- Delimiter: semicolon (;)
- Decimal separator: comma (,)
- Line ending: CRLF (\r\n)
- Rounding: 2 decimal places (half-up)
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple
import re


class ValidationError(Exception):
    """Raised when export validation fails"""
    pass


class ValidationResult:
    """Result of export validation"""
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0
    
    def add_error(self, message: str):
        self.errors.append(message)
    
    def add_warning(self, message: str):
        self.warnings.append(message)


class PronoteExporter:
    """
    Service for exporting exam grades to PRONOTE CSV format.
    
    Usage:
        exporter = PronoteExporter(exam, coefficient=1.0)
        validation = exporter.validate_export_eligibility()
        if validation.is_valid:
            csv_content, warnings = exporter.generate_csv()
    """
    
    def __init__(self, exam, coefficient: float = 1.0):
        """
        Initialize exporter for an exam.
        
        Args:
            exam: Exam model instance
            coefficient: Grade coefficient (default: 1.0)
        """
        self.exam = exam
        self.coefficient = coefficient
    
    def format_decimal_french(self, value: float, precision: int = 2) -> str:
        """
        Format a decimal number to French format (comma separator).
        
        Args:
            value: Float value to format
            precision: Number of decimal places (default: 2)
        
        Returns:
            String formatted as "15,50"
        
        Examples:
            >>> format_decimal_french(15.5, 2)
            "15,50"
            >>> format_decimal_french(12.0, 2)
            "12,00"
            >>> format_decimal_french(15.555, 2)
            "15,56"
        """
        if value is None:
            value = 0.0
        
        # Use Decimal for precise rounding
        quantizer = Decimal('0.1') ** precision
        decimal_value = Decimal(str(value)).quantize(quantizer, rounding=ROUND_HALF_UP)
        
        # Format with proper precision
        formatted = f"{decimal_value:.{precision}f}"
        
        # Replace dot with comma
        return formatted.replace('.', ',')
    
    def sanitize_comment(self, comment: Optional[str]) -> str:
        """
        Sanitize comment for CSV export.
        
        Handles:
        - Empty/None values
        - Newlines (replace with space)
        - CSV injection (remove leading special chars)
        - Length limiting (500 chars max)
        - Proper CSV quoting if contains delimiter
        
        Args:
            comment: Comment text to sanitize
        
        Returns:
            Sanitized comment string
        
        Examples:
            >>> sanitize_comment("Bon travail")
            "Bon travail"
            >>> sanitize_comment("Bien; mais peut mieux faire")
            "Bien; mais peut mieux faire"  # Quotes added by CSV writer
            >>> sanitize_comment("Line 1\\nLine 2")
            "Line 1 Line 2"
        """
        if not comment:
            return ""
        
        # Remove leading/trailing whitespace
        comment = comment.strip()
        
        # Replace newlines with spaces
        comment = re.sub(r'[\r\n]+', ' ', comment)
        
        # CSV injection prevention: remove leading special characters
        if comment and comment[0] in ('=', '+', '-', '@'):
            comment = comment[1:]
        
        # Limit length to 500 characters
        if len(comment) > 500:
            comment = comment[:497] + '...'
        
        return comment
    
    def _calculate_max_score(self, grading_structure: List[Dict]) -> float:
        """
        Calculate maximum score from grading structure JSON.
        
        The grading_structure is a list of exercises/questions with max_points.
        
        Args:
            grading_structure: List of dictionaries with grading info
        
        Returns:
            Maximum total score (float)
        
        Examples:
            >>> _calculate_max_score([
            ...     {"name": "Ex1", "max_points": 10},
            ...     {"name": "Ex2", "max_points": 10}
            ... ])
            20.0
        """
        if not grading_structure:
            return 20.0  # Default to /20 scale
        
        total = 0.0
        
        def sum_points(items):
            """Recursively sum max_points from nested structure"""
            nonlocal total
            for item in items:
                if isinstance(item, dict):
                    # Add max_points if present
                    if 'max_points' in item:
                        total += float(item.get('max_points', 0))
                    elif 'points' in item:
                        total += float(item.get('points', 0))
                    
                    # Recursively process children/questions
                    if 'children' in item and isinstance(item['children'], list):
                        sum_points(item['children'])
                    if 'questions' in item and isinstance(item['questions'], list):
                        sum_points(item['questions'])
        
        sum_points(grading_structure)
        
        return total if total > 0 else 20.0
    
    def calculate_copy_grade(self, copy) -> float:
        """
        Calculate final grade for a copy from annotations and Score model.
        
        Priority:
        1. Use Score.scores_data if available (summed)
        2. Fall back to annotation score_delta sum
        3. Scale to /20 if exam uses different scale
        
        Args:
            copy: Copy model instance
        
        Returns:
            Final grade on /20 scale, clamped to [0, 20]
        
        Raises:
            ValueError: If no grade data available
        """
        # Calculate grade from annotations
        annotations = copy.annotations.filter(score_delta__isnull=False)
        if not annotations.exists():
            raise ValueError(f"No grade data found for copy {copy.anonymous_id}")
        
        raw_score = sum(
            ann.score_delta for ann in annotations 
            if ann.score_delta is not None
        )
        
        # Get max score from exam structure
        max_score = self._calculate_max_score(self.exam.grading_structure)
        
        # Scale to /20 if needed
        if max_score != 20.0 and max_score > 0:
            final_grade = (raw_score / max_score) * 20.0
        else:
            final_grade = raw_score
        
        # Clamp to [0, 20]
        final_grade = max(0.0, min(20.0, final_grade))
        
        return final_grade
    
    def validate_export_eligibility(self) -> ValidationResult:
        """
        Validate that the exam is ready for export.
        
        Checks:
        - At least one graded copy exists
        - All graded copies are identified
        - All identified students have valid INE
        - Warns about comments with delimiters
        
        Returns:
            ValidationResult with errors and warnings
        """
        result = ValidationResult()
        
        # Get all copies for this exam
        from exams.models import Copy
        all_copies = Copy.objects.filter(exam=self.exam)
        
        if not all_copies.exists():
            result.add_error("Aucune copie trouvée pour cet examen")
            return result
        
        # Get graded copies
        graded_copies = all_copies.filter(status=Copy.Status.GRADED)
        
        if not graded_copies.exists():
            result.add_error("Aucune copie notée trouvée. Toutes les copies doivent être dans l'état GRADED")
            return result
        
        # Check identification
        unidentified = graded_copies.filter(is_identified=False)
        if unidentified.exists():
            count = unidentified.count()
            result.add_error(
                f"{count} copie(s) notée(s) non identifiée(s). "
                f"Toutes les copies doivent être associées à un élève."
            )
        
        # Check student validity (must have a linked student)
        missing_student = graded_copies.filter(
            is_identified=True, 
            student__isnull=True
        )
        
        if missing_student.exists():
            count = missing_student.count()
            result.add_error(
                f"{count} copie(s) identifiée(s) sans élève associé. "
                f"Tous les élèves doivent être renseignés pour l'export PRONOTE."
            )
        
        # Warn about comments with delimiters
        if graded_copies.exists():
            for copy in graded_copies.select_related('student'):
                comment = copy.global_appreciation or ''
                if ';' in comment:
                    result.add_warning(
                        f"Copie {copy.anonymous_id}: le commentaire contient un point-virgule "
                        f"(sera échappé automatiquement)"
                    )
        
        return result
    
    def generate_csv(self) -> Tuple[str, List[str]]:
        """
        Generate PRONOTE CSV export.
        
        Format:
            INE;MATIERE;NOTE;COEFF;COMMENTAIRE
            12345678901;MATHS;15,50;1,0;Bon travail
        
        Returns:
            Tuple of (csv_content, warnings)
        
        Raises:
            ValidationError: If validation fails
        """
        import csv
        import io
        
        # Validate before export
        validation = self.validate_export_eligibility()
        if not validation.is_valid:
            raise ValidationError(
                "Export impossible: " + "; ".join(validation.errors)
            )
        
        # Create CSV with proper settings
        output = io.StringIO()
        
        # Add UTF-8 BOM for Excel/PRONOTE compatibility
        output.write('\ufeff')
        
        writer = csv.writer(
            output,
            delimiter=';',
            lineterminator='\r\n',  # CRLF for Windows
            quoting=csv.QUOTE_MINIMAL
        )
        
        # Write header
        writer.writerow(['INE', 'MATIERE', 'NOTE', 'COEFF', 'COMMENTAIRE'])
        
        # Query graded and identified copies with proper optimization
        from exams.models import Copy
        copies = Copy.objects.filter(
            exam=self.exam,
            status=Copy.Status.GRADED,
            is_identified=True
        ).select_related('student').prefetch_related('annotations')
        
        # Generate rows
        for copy in copies:
            # Get student identifier (last_name first_name as fallback since INE removed)
            ine = f"{copy.student.last_name} {copy.student.first_name}" if copy.student else ''
            
            # Get exam name as MATIERE
            matiere = self.exam.name.upper()
            
            # Calculate grade
            try:
                grade = self.calculate_copy_grade(copy)
            except ValueError:
                # Skip copies without grade data (should not happen due to validation)
                validation.add_warning(
                    f"Copie {copy.anonymous_id} ignorée: aucune donnée de note"
                )
                continue
            
            # Format grade in French format
            note = self.format_decimal_french(grade, precision=2)
            
            # Format coefficient in French format
            coeff = self.format_decimal_french(self.coefficient, precision=1)
            
            # Sanitize comment
            comment = self.sanitize_comment(copy.global_appreciation)
            
            # Write row
            writer.writerow([ine, matiere, note, coeff, comment])
        
        # Get CSV content
        csv_content = output.getvalue()
        output.close()
        
        return csv_content, validation.warnings
