"""
Test de fusion multi-feuilles par élève.
Vérifie que la logique de segmentation fusionne correctement
les feuilles multiples d'un même élève en 1 seule Copy.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from processing.services.batch_processor import BatchA3Processor, StudentMatch, PageInfo


class TestMultiSheetFusion:
    """Tests de la logique de fusion multi-feuilles."""

    def test_is_same_student_by_email(self):
        """Vérifie que 2 StudentMatch avec même email sont détectés comme même élève."""
        processor = BatchA3Processor()

        student1 = StudentMatch(
            student_id=1,
            last_name="DUPONT",
            first_name="JEAN",
            date_of_birth="01/01/2000",
            email="jean.dupont@test.com",
            confidence=0.9,
            ocr_text="DUPONT JEAN"
        )

        student2 = StudentMatch(
            student_id=1,
            last_name="DUPONT",
            first_name="JEAN",
            date_of_birth="01/01/2000",
            email="jean.dupont@test.com",
            confidence=0.85,
            ocr_text="DUPONT J"  # OCR légèrement différent
        )

        assert processor._is_same_student(student1, student2) is True

    def test_is_same_student_by_name_normalized(self):
        """Vérifie que 2 StudentMatch avec même nom normalisé sont détectés comme même élève."""
        processor = BatchA3Processor()

        student1 = StudentMatch(
            student_id=1,
            last_name="BEN-ATTOUCH",
            first_name="DONIA",
            date_of_birth="25/06/2007",
            email="",  # Pas d'email
            confidence=0.9,
            ocr_text="BEN ATTOUCH DONIA"
        )

        student2 = StudentMatch(
            student_id=1,
            last_name="BENATTOUCH",  # Sans tiret
            first_name="DONIA",
            date_of_birth="25/06/2007",
            email="",
            confidence=0.85,
            ocr_text="BENATTOUCH DONIA"
        )

        # La normalisation doit supprimer les tirets
        assert processor._is_same_student(student1, student2) is True

    def test_is_same_student_different_students(self):
        """Vérifie que 2 élèves différents ne sont PAS détectés comme même élève."""
        processor = BatchA3Processor()

        student1 = StudentMatch(
            student_id=1,
            last_name="DUPONT",
            first_name="JEAN",
            date_of_birth="01/01/2000",
            email="jean.dupont@test.com",
            confidence=0.9,
            ocr_text="DUPONT JEAN"
        )

        student2 = StudentMatch(
            student_id=2,
            last_name="MARTIN",
            first_name="PAUL",
            date_of_birth="02/02/2000",
            email="paul.martin@test.com",
            confidence=0.85,
            ocr_text="MARTIN PAUL"
        )

        assert processor._is_same_student(student1, student2) is False

    def test_is_same_student_none_returns_false(self):
        """Vérifie que None students ne sont PAS considérés comme même élève."""
        processor = BatchA3Processor()

        student1 = StudentMatch(
            student_id=1,
            last_name="DUPONT",
            first_name="JEAN",
            date_of_birth="01/01/2000",
            email="jean.dupont@test.com",
            confidence=0.9,
            ocr_text="DUPONT JEAN"
        )

        assert processor._is_same_student(student1, None) is False
        assert processor._is_same_student(None, student1) is False
        assert processor._is_same_student(None, None) is False

    @patch.object(BatchA3Processor, '_detect_header_on_page')
    @patch.object(BatchA3Processor, '_ocr_header')
    @patch.object(BatchA3Processor, '_match_student')
    def test_segment_by_student_single_sheet(
        self,
        mock_match,
        mock_ocr,
        mock_detect_header
    ):
        """Test segmentation avec 1 seule feuille (4 pages A4)."""
        processor = BatchA3Processor()

        # Mock: 1 feuille avec header détecté
        mock_detect_header.return_value = True
        mock_ocr.return_value = ("DUPONT JEAN", "01/01/2000")
        mock_match.return_value = StudentMatch(
            student_id=1,
            last_name="DUPONT",
            first_name="JEAN",
            date_of_birth="01/01/2000",
            email="jean.dupont@test.com",
            confidence=0.9,
            ocr_text="DUPONT JEAN"
        )

        # Créer 4 pages A4 (1 feuille)
        pages = [
            PageInfo(1, 1, 1, np.zeros((100, 100, 3))),
            PageInfo(2, 1, 2, np.zeros((100, 100, 3))),
            PageInfo(3, 1, 3, np.zeros((100, 100, 3))),
            PageInfo(4, 1, 4, np.zeros((100, 100, 3))),
        ]

        with patch('processing.services.batch_processor.settings') as mock_settings:
            mock_settings.MEDIA_ROOT = "/tmp"  # nosec B108 - Test file path, not used in production
            with patch('processing.services.batch_processor.cv2.imwrite'):
                copies = processor._segment_by_student(pages, "test_exam")

        # Vérifications
        assert len(copies) == 1
        assert len(copies[0].pages) == 4
        assert copies[0].student_match is not None
        assert copies[0].student_match.last_name == "DUPONT"
        assert copies[0].needs_review is False

    @patch.object(BatchA3Processor, '_detect_header_on_page')
    @patch.object(BatchA3Processor, '_ocr_header')
    @patch.object(BatchA3Processor, '_match_student')
    def test_segment_by_student_two_sheets_same_student(
        self,
        mock_match,
        mock_ocr,
        mock_detect_header
    ):
        """
        TEST CRITIQUE : Fusion multi-feuilles.
        2 feuilles (8 pages A4) du MÊME élève doivent produire 1 seule Copy de 8 pages.
        """
        processor = BatchA3Processor()

        # Mock: 2 feuilles avec headers détectés, MÊME élève
        mock_detect_header.return_value = True
        mock_ocr.return_value = ("DUPONT JEAN", "01/01/2000")

        # Créer le même StudentMatch pour les 2 feuilles
        same_student = StudentMatch(
            student_id=1,
            last_name="DUPONT",
            first_name="JEAN",
            date_of_birth="01/01/2000",
            email="jean.dupont@test.com",
            confidence=0.9,
            ocr_text="DUPONT JEAN"
        )
        mock_match.return_value = same_student

        # Créer 8 pages A4 (2 feuilles)
        pages = [
            # Feuille 1
            PageInfo(1, 1, 1, np.zeros((100, 100, 3))),
            PageInfo(2, 1, 2, np.zeros((100, 100, 3))),
            PageInfo(3, 1, 3, np.zeros((100, 100, 3))),
            PageInfo(4, 1, 4, np.zeros((100, 100, 3))),
            # Feuille 2
            PageInfo(5, 2, 1, np.zeros((100, 100, 3))),
            PageInfo(6, 2, 2, np.zeros((100, 100, 3))),
            PageInfo(7, 2, 3, np.zeros((100, 100, 3))),
            PageInfo(8, 2, 4, np.zeros((100, 100, 3))),
        ]

        with patch('processing.services.batch_processor.settings') as mock_settings:
            mock_settings.MEDIA_ROOT = "/tmp"  # nosec B108 - Test file path, not used in production
            with patch('processing.services.batch_processor.cv2.imwrite'):
                copies = processor._segment_by_student(pages, "test_exam")

        # Vérifications CRITIQUES
        assert len(copies) == 1, "Doit créer 1 seule Copy pour les 2 feuilles du même élève"
        assert len(copies[0].pages) == 8, "La Copy doit avoir 8 pages (2 feuilles fusionnées)"
        assert copies[0].student_match is not None
        assert copies[0].student_match.last_name == "DUPONT"
        assert copies[0].needs_review is False
        assert len(copies[0].header_crops) == 2, "Doit avoir 2 header crops (1 par feuille)"

    @patch.object(BatchA3Processor, '_detect_header_on_page')
    @patch.object(BatchA3Processor, '_ocr_header')
    @patch.object(BatchA3Processor, '_match_student')
    def test_segment_by_student_two_sheets_different_students(
        self,
        mock_match,
        mock_ocr,
        mock_detect_header
    ):
        """
        2 feuilles (8 pages A4) de 2 élèves DIFFÉRENTS doivent produire 2 Copies de 4 pages chacune.
        """
        processor = BatchA3Processor()

        mock_detect_header.return_value = True

        # Alterner entre 2 élèves différents
        student1 = StudentMatch(
            student_id=1,
            last_name="DUPONT",
            first_name="JEAN",
            date_of_birth="01/01/2000",
            email="jean.dupont@test.com",
            confidence=0.9,
            ocr_text="DUPONT JEAN"
        )

        student2 = StudentMatch(
            student_id=2,
            last_name="MARTIN",
            first_name="PAUL",
            date_of_birth="02/02/2000",
            email="paul.martin@test.com",
            confidence=0.85,
            ocr_text="MARTIN PAUL"
        )

        mock_match.side_effect = [student1, student2]
        mock_ocr.side_effect = [
            ("DUPONT JEAN", "01/01/2000"),
            ("MARTIN PAUL", "02/02/2000")
        ]

        # Créer 8 pages A4 (2 feuilles)
        pages = [
            # Feuille 1 (DUPONT)
            PageInfo(1, 1, 1, np.zeros((100, 100, 3))),
            PageInfo(2, 1, 2, np.zeros((100, 100, 3))),
            PageInfo(3, 1, 3, np.zeros((100, 100, 3))),
            PageInfo(4, 1, 4, np.zeros((100, 100, 3))),
            # Feuille 2 (MARTIN)
            PageInfo(5, 2, 1, np.zeros((100, 100, 3))),
            PageInfo(6, 2, 2, np.zeros((100, 100, 3))),
            PageInfo(7, 2, 3, np.zeros((100, 100, 3))),
            PageInfo(8, 2, 4, np.zeros((100, 100, 3))),
        ]

        with patch('processing.services.batch_processor.settings') as mock_settings:
            mock_settings.MEDIA_ROOT = "/tmp"  # nosec B108 - Test file path, not used in production
            with patch('processing.services.batch_processor.cv2.imwrite'):
                copies = processor._segment_by_student(pages, "test_exam")

        # Vérifications
        assert len(copies) == 2, "Doit créer 2 Copies pour 2 élèves différents"
        assert len(copies[0].pages) == 4, "Copy 1 doit avoir 4 pages"
        assert len(copies[1].pages) == 4, "Copy 2 doit avoir 4 pages"
        assert copies[0].student_match.last_name == "DUPONT"
        assert copies[1].student_match.last_name == "MARTIN"

    @patch.object(BatchA3Processor, '_detect_header_on_page')
    @patch.object(BatchA3Processor, '_ocr_header')
    @patch.object(BatchA3Processor, '_match_student')
    def test_segment_by_student_three_sheets_same_student(
        self,
        mock_match,
        mock_ocr,
        mock_detect_header
    ):
        """
        3 feuilles (12 pages A4) du MÊME élève → 1 Copy de 12 pages.
        """
        processor = BatchA3Processor()

        mock_detect_header.return_value = True
        mock_ocr.return_value = ("ZARDI MOHAMED", "21/03/2007")

        same_student = StudentMatch(
            student_id=1,
            last_name="ZARDI",
            first_name="MOHAMED",
            date_of_birth="21/03/2007",
            email="mohamed.zardi@test.com",
            confidence=0.9,
            ocr_text="ZARDI MOHAMED"
        )
        mock_match.return_value = same_student

        # Créer 12 pages A4 (3 feuilles)
        pages = []
        for sheet in range(1, 4):  # 3 feuilles
            for pos in range(1, 5):  # 4 pages par feuille
                page_num = (sheet - 1) * 4 + pos
                pages.append(PageInfo(page_num, sheet, pos, np.zeros((100, 100, 3))))

        with patch('processing.services.batch_processor.settings') as mock_settings:
            mock_settings.MEDIA_ROOT = "/tmp"  # nosec B108 - Test file path, not used in production
            with patch('processing.services.batch_processor.cv2.imwrite'):
                copies = processor._segment_by_student(pages, "test_exam")

        # Vérifications
        assert len(copies) == 1, "Doit créer 1 seule Copy pour 3 feuilles du même élève"
        assert len(copies[0].pages) == 12, "La Copy doit avoir 12 pages (3 feuilles fusionnées)"
        assert copies[0].student_match.last_name == "ZARDI"
        assert len(copies[0].header_crops) == 3, "Doit avoir 3 header crops"

    def test_invariant_page_count_multiple_of_4(self):
        """
        Invariant : Toute Copy valide doit avoir un nombre de pages multiple de 4.
        """
        # Ce test est déjà couvert dans _segment_by_student qui valide cet invariant
        # et met needs_review=True si violation
        processor = BatchA3Processor()

        # Simuler une Copy avec 5 pages (invalide)
        pages = [
            PageInfo(i, 1, i, np.zeros((100, 100, 3)))
            for i in range(1, 6)  # 5 pages
        ]

        with patch('processing.services.batch_processor.settings') as mock_settings:
            mock_settings.MEDIA_ROOT = "/tmp"  # nosec B108 - Test file path, not used in production
            with patch('processing.services.batch_processor.cv2.imwrite'):
                with patch.object(processor, '_detect_header_on_page', return_value=False):
                    copies = processor._segment_by_student(pages, "test_exam")

        # La copie doit être marquée needs_review car 5 % 4 != 0
        assert len(copies) == 1
        assert len(copies[0].pages) == 5
        assert copies[0].needs_review is True
        assert "not multiple of 4" in copies[0].review_reason
