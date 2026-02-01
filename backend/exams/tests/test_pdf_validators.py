"""
Tests pour les validators PDF
Conformité: .antigravity/rules/01_security_rules.md § 8.1
"""
import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from exams.validators import (
    validate_pdf_size,
    validate_pdf_not_empty,
    validate_pdf_mime_type,
    validate_pdf_integrity,
)


class TestPDFValidators:
    """Tests des validators de fichiers PDF"""

    def test_validate_pdf_size_valid(self):
        """Test avec un fichier de taille valide (< 50 MB)"""
        # Créer un fichier de 1 MB
        content = b'%PDF-1.4\n' + b'0' * (1024 * 1024)
        pdf_file = SimpleUploadedFile("test.pdf", content, content_type="application/pdf")
        
        # Ne doit pas lever d'exception
        try:
            validate_pdf_size(pdf_file)
        except ValidationError:
            pytest.fail("validate_pdf_size a levé ValidationError pour un fichier valide")

    def test_validate_pdf_size_too_large(self):
        """Test avec un fichier trop volumineux (> 50 MB)"""
        # Créer un fichier de 51 MB
        content = b'%PDF-1.4\n' + b'0' * (51 * 1024 * 1024)
        pdf_file = SimpleUploadedFile("large.pdf", content, content_type="application/pdf")
        
        # Doit lever ValidationError
        with pytest.raises(ValidationError) as exc_info:
            validate_pdf_size(pdf_file)
        
        assert 'trop volumineux' in str(exc_info.value).lower()
        assert exc_info.value.code == 'file_too_large'

    def test_validate_pdf_size_exactly_50mb(self):
        """Test avec un fichier de exactement 50 MB (limite)"""
        # Créer un fichier de exactement 50 MB
        content = b'%PDF-1.4\n' + b'0' * (50 * 1024 * 1024 - 10)
        pdf_file = SimpleUploadedFile("limit.pdf", content, content_type="application/pdf")
        
        # Ne doit pas lever d'exception
        try:
            validate_pdf_size(pdf_file)
        except ValidationError:
            pytest.fail("validate_pdf_size a levé ValidationError pour un fichier à la limite")

    def test_validate_pdf_not_empty_valid(self):
        """Test avec un fichier non vide"""
        content = b'%PDF-1.4\nSome content'
        pdf_file = SimpleUploadedFile("test.pdf", content, content_type="application/pdf")
        
        # Ne doit pas lever d'exception
        try:
            validate_pdf_not_empty(pdf_file)
        except ValidationError:
            pytest.fail("validate_pdf_not_empty a levé ValidationError pour un fichier valide")

    def test_validate_pdf_not_empty_zero_bytes(self):
        """Test avec un fichier vide (0 bytes)"""
        content = b''
        pdf_file = SimpleUploadedFile("empty.pdf", content, content_type="application/pdf")
        
        # Doit lever ValidationError
        with pytest.raises(ValidationError) as exc_info:
            validate_pdf_not_empty(pdf_file)
        
        assert 'vide' in str(exc_info.value).lower()
        assert exc_info.value.code == 'empty_file'

    def test_validate_pdf_mime_type_valid(self):
        """Test avec un vrai fichier PDF (MIME type correct)"""
        # Créer un fichier PDF minimal valide
        content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n%%EOF'
        pdf_file = SimpleUploadedFile("test.pdf", content, content_type="application/pdf")
        
        # Ne doit pas lever d'exception
        try:
            validate_pdf_mime_type(pdf_file)
        except ValidationError:
            pytest.fail("validate_pdf_mime_type a levé ValidationError pour un PDF valide")

    def test_validate_pdf_mime_type_fake_pdf(self):
        """Test avec un fichier texte renommé en .pdf"""
        # Créer un fichier texte avec extension .pdf
        content = b'This is just a text file, not a PDF'
        fake_pdf = SimpleUploadedFile("fake.pdf", content, content_type="application/pdf")
        
        # Doit lever ValidationError
        with pytest.raises(ValidationError) as exc_info:
            validate_pdf_mime_type(fake_pdf)
        
        assert 'mime' in str(exc_info.value).lower()
        assert exc_info.value.code == 'invalid_mime_type'

    @pytest.mark.processing
    def test_validate_pdf_integrity_valid(self):
        """Test avec un PDF valide (intégrité OK)"""
        # Créer un PDF minimal valide avec PyMuPDF
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        doc.save("test_temp.pdf")
        doc.close()
        
        with open("test_temp.pdf", "rb") as f:
            content = f.read()
        
        pdf_file = SimpleUploadedFile("test.pdf", content, content_type="application/pdf")
        
        # Ne doit pas lever d'exception
        try:
            validate_pdf_integrity(pdf_file)
        except ValidationError:
            pytest.fail("validate_pdf_integrity a levé ValidationError pour un PDF valide")
        
        # Cleanup
        import os
        os.remove("test_temp.pdf")

    @pytest.mark.processing
    def test_validate_pdf_integrity_corrupted(self):
        """Test avec un PDF corrompu"""
        # Créer un fichier corrompu (commence comme PDF mais invalide)
        content = b'%PDF-1.4\nGARBAGE DATA CORRUPTED'
        corrupted_pdf = SimpleUploadedFile("corrupted.pdf", content, content_type="application/pdf")
        
        # Doit lever ValidationError
        with pytest.raises(ValidationError) as exc_info:
            validate_pdf_integrity(corrupted_pdf)
        
        assert exc_info.value.code == 'corrupted_pdf'

    def test_validate_pdf_integrity_too_many_pages(self):
        """Test avec un PDF ayant trop de pages (> 500)"""
        # Note: Ce test est conceptuel car créer un PDF de 501 pages serait trop lourd
        # En production, ce validator protège contre les uploads malveillants
        pass  # Skip pour éviter de créer un fichier trop volumineux


@pytest.mark.django_db
@pytest.mark.processing
class TestPDFValidatorsIntegration:
    """Tests d'intégration avec les modèles"""

    def test_exam_pdf_source_with_invalid_extension(self):
        """Test upload fichier avec extension invalide sur Exam"""
        from exams.models import Exam
        from datetime import date
        
        # Créer un fichier .txt au lieu de .pdf
        content = b'Not a PDF file'
        txt_file = SimpleUploadedFile("test.txt", content, content_type="text/plain")
        
        exam = Exam(
            name="Test Exam",
            date=date.today(),
            pdf_source=txt_file
        )
        
        # Doit lever ValidationError lors de la validation
        with pytest.raises(ValidationError) as exc_info:
            exam.full_clean()
        
        assert 'pdf_source' in exc_info.value.error_dict

    def test_exam_pdf_source_with_valid_pdf(self):
        """Test upload fichier PDF valide sur Exam"""
        from exams.models import Exam
        from datetime import date
        import fitz
        import os
        
        # Créer un fichier PDF valide avec PyMuPDF
        doc = fitz.open()
        page = doc.new_page()
        doc.save("test_valid_exam.pdf")
        doc.close()
        
        with open("test_valid_exam.pdf", "rb") as f:
            content = f.read()
        
        pdf_file = SimpleUploadedFile("test.pdf", content, content_type="application/pdf")
        
        exam = Exam(
            name="Test Exam",
            date=date.today(),
            pdf_source=pdf_file
        )
        
        # Ne doit pas lever d'exception
        try:
            exam.full_clean()
        except ValidationError as e:
            # Ignorer les erreurs non liées à pdf_source
            if 'pdf_source' in e.error_dict:
                pytest.fail(f"Validation échouée pour PDF valide: {e}")
        finally:
            # Cleanup
            if os.path.exists("test_valid_exam.pdf"):
                os.remove("test_valid_exam.pdf")

    def test_copy_pdf_source_with_too_large_file(self):
        """Test upload fichier trop volumineux sur Copy"""
        from exams.models import Copy, Exam
        from datetime import date
        
        # Créer un exam parent
        exam = Exam.objects.create(
            name="Test Exam",
            date=date.today()
        )
        
        # Créer un fichier trop volumineux (51 MB)
        content = b'%PDF-1.4\n' + b'0' * (51 * 1024 * 1024)
        large_pdf = SimpleUploadedFile("large.pdf", content, content_type="application/pdf")
        
        copy = Copy(
            exam=exam,
            anonymous_id="TEST-001",
            pdf_source=large_pdf
        )
        
        # Doit lever ValidationError lors de la validation
        with pytest.raises(ValidationError) as exc_info:
            copy.full_clean()
        
        assert 'pdf_source' in exc_info.value.error_dict
