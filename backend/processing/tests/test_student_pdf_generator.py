"""
Tests unitaires pour StudentPDFGenerator.

Teste les méthodes de base (CSV, fuzzy matching, A3 detection, etc.)
sans appeler l'API GPT-4V (mockée).
"""
import csv
import os
import tempfile
from unittest.mock import patch, MagicMock

import cv2
import fitz
import numpy as np
import pytest

from processing.services.student_pdf_generator import StudentPDFGenerator


# ─── Helpers ─────────────────────────────────────────────────────────


def make_csv(students, path):
    """Crée un fichier CSV de test."""
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Élèves', 'Né(e) le', 'Adresse E-mail'])
        for name, dob, email in students:
            writer.writerow([name, dob, email])


def make_a3_pdf(pages=2, page_width=1190, page_height=842):
    """Crée un PDF A3 paysage en mémoire (ratio > 1.2)."""
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=page_width, height=page_height)
        page.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
    return doc


def make_a4_pdf(pages=4, page_width=595, page_height=842):
    """Crée un PDF A4 en mémoire."""
    doc = fitz.open()
    for i in range(pages):
        page = doc.new_page(width=page_width, height=page_height)
        page.insert_text((72, 72), f"Page {i + 1}", fontsize=24)
    return doc


# ─── CSV Loading Tests ───────────────────────────────────────────────


class TestCSVLoading:
    def test_load_csv_utf8sig(self, tmp_path):
        """Charge un CSV encodé en UTF-8 BOM."""
        csv_path = str(tmp_path / "eleves.csv")
        make_csv([
            ("DUPONT Jean", "15/03/2006", "jean@test.fr"),
            ("MARTIN Alice", "22/07/2005", "alice@test.fr"),
        ], csv_path)

        gen = StudentPDFGenerator(csv_path=csv_path)
        assert len(gen.students) == 2
        assert gen.students[0]['nom'] == "DUPONT Jean"
        assert gen.students[1]['date'] == "22/07/2005"

    def test_load_csv_alternate_columns(self, tmp_path):
        """Supporte les noms de colonnes alternatifs."""
        csv_path = str(tmp_path / "eleves.csv")
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Nom et Prénom', 'Date de naissance', 'Email'])
            writer.writerow(['LEBLANC Pierre', '01/01/2006', 'pierre@test.fr'])

        gen = StudentPDFGenerator(csv_path=csv_path)
        assert len(gen.students) == 1
        assert gen.students[0]['nom'] == "LEBLANC Pierre"

    def test_load_csv_latin1(self, tmp_path):
        """Supporte le CSV encodé en latin-1."""
        csv_path = str(tmp_path / "eleves.csv")
        with open(csv_path, 'w', newline='', encoding='latin-1') as f:
            writer = csv.writer(f)
            writer.writerow(['Elèves', 'Né(e) le', 'Adresse E-mail'])
            writer.writerow(['BÉNÉDICTE Léa', '05/06/2006', 'lea@test.fr'])

        gen = StudentPDFGenerator(csv_path=csv_path)
        assert len(gen.students) == 1

    def test_load_csv_missing_file(self):
        """Retourne une liste vide si le CSV est absent."""
        gen = StudentPDFGenerator(csv_path="/nonexistent/path.csv")
        assert gen.students == []

    def test_load_csv_none(self):
        """Aucun CSV → liste vide."""
        gen = StudentPDFGenerator()
        assert gen.students == []

    def test_load_csv_empty_names_skipped(self, tmp_path):
        """Les lignes avec un nom vide sont ignorées."""
        csv_path = str(tmp_path / "eleves.csv")
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Élèves', 'Né(e) le', 'Adresse E-mail'])
            writer.writerow(['DUPONT Jean', '01/01/2006', 'jean@test.fr'])
            writer.writerow(['', '02/02/2006', 'vide@test.fr'])
            writer.writerow(['MARTIN Alice', '03/03/2006', 'alice@test.fr'])

        gen = StudentPDFGenerator(csv_path=csv_path)
        assert len(gen.students) == 2


# ─── Text Normalization Tests ────────────────────────────────────────


class TestNormalizeText:
    def test_basic_normalization(self):
        assert StudentPDFGenerator._normalize_text("Dupont Jean") == "DUPONT JEAN"

    def test_removes_accents(self):
        assert StudentPDFGenerator._normalize_text("Bénédicte Léa") == "BENEDICTE LEA"

    def test_removes_special_chars(self):
        assert StudentPDFGenerator._normalize_text("O'Brien-Smith") == "OBRIENSMITH"

    def test_empty_string(self):
        assert StudentPDFGenerator._normalize_text("") == ""

    def test_none(self):
        assert StudentPDFGenerator._normalize_text(None) == ""


# ─── Fuzzy Matching Tests ────────────────────────────────────────────


class TestFuzzyMatch:
    def setup_method(self):
        self.gen = StudentPDFGenerator()
        self.gen.students = [
            {'nom': 'DUPONT Jean', 'date': '01/01/2006', 'email': ''},
            {'nom': 'MARTIN Alice', 'date': '02/02/2005', 'email': ''},
            {'nom': 'BÉNÉDICTE Léa', 'date': '03/03/2006', 'email': ''},
        ]

    def test_exact_match(self):
        nom, ratio = self.gen._fuzzy_match("DUPONT Jean")
        assert nom == "DUPONT Jean"
        assert ratio > 0.9

    def test_partial_match(self):
        nom, ratio = self.gen._fuzzy_match("DUPNT Jean")
        assert nom == "DUPONT Jean"
        assert ratio >= 0.50

    def test_no_match(self):
        nom, ratio = self.gen._fuzzy_match("ZZZZZ YYYYY")
        assert nom is None
        assert ratio < 0.50

    def test_empty_input(self):
        nom, ratio = self.gen._fuzzy_match("")
        assert nom is None
        assert ratio == 0.0

    def test_accent_tolerant(self):
        nom, ratio = self.gen._fuzzy_match("BENEDICTE Lea")
        assert nom == "BÉNÉDICTE Léa"
        assert ratio > 0.80


# ─── Safe Filename Tests ─────────────────────────────────────────────


class TestSafeFilename:
    def test_basic(self):
        assert StudentPDFGenerator._safe_filename("DUPONT Jean") == "DUPONT Jean"

    def test_accents(self):
        result = StudentPDFGenerator._safe_filename("BÉNÉDICTE Léa")
        assert "B" in result
        # Accented chars become underscores
        assert "_" in result or result == "BÉNÉDICTE Léa"  # depends on isalnum

    def test_special_chars(self):
        result = StudentPDFGenerator._safe_filename("O'Brien/Smith")
        assert "/" not in result
        assert "'" not in result


# ─── A3 Detection Tests ─────────────────────────────────────────────


class TestA3Detection:
    def test_a3_landscape(self):
        gen = StudentPDFGenerator()
        doc = make_a3_pdf(pages=1)
        assert gen._is_a3(doc) is True
        doc.close()

    def test_a4_portrait(self):
        gen = StudentPDFGenerator()
        doc = make_a4_pdf(pages=1)
        assert gen._is_a3(doc) is False
        doc.close()


# ─── A3 Split Tests ─────────────────────────────────────────────────


class TestA3Split:
    def test_split_dimensions(self):
        image = np.zeros((842, 1190, 3), dtype=np.uint8)
        left, right = StudentPDFGenerator._split_a3_to_a4(image)
        assert left.shape[1] == 595
        assert right.shape[1] == 595
        assert left.shape[0] == 842
        assert right.shape[0] == 842

    def test_split_content(self):
        """La moitié gauche et droite contiennent des pixels distincts."""
        image = np.zeros((100, 200, 3), dtype=np.uint8)
        image[:, :100, :] = 255  # gauche = blanc
        image[:, 100:, :] = 128  # droite = gris

        left, right = StudentPDFGenerator._split_a3_to_a4(image)
        assert np.mean(left) == pytest.approx(255.0, abs=0.1)
        assert np.mean(right) == pytest.approx(128.0, abs=0.1)


# ─── Post-Correction Tests ───────────────────────────────────────────


class TestPostCorrection:
    def setup_method(self):
        self.gen = StudentPDFGenerator()
        self.gen.students = [
            {'nom': 'Alice', 'date': '', 'email': ''},
            {'nom': 'Bob', 'date': '', 'email': ''},
            {'nom': 'Charlie', 'date': '', 'email': ''},
        ]

    def test_no_correction_needed(self):
        assigns = ['Alice', 'Alice', 'Bob', 'Bob', 'Charlie']
        result = self.gen._post_correct_assignments(assigns)
        assert result == ['Alice', 'Alice', 'Bob', 'Bob', 'Charlie']

    def test_corrects_non_consecutive(self):
        """Si Alice apparaît à [0,1] et aussi [4], et Charlie manque,
        la feuille isolée [4] est réattribuée à Charlie."""
        assigns = ['Alice', 'Alice', 'Bob', 'Bob', 'Alice']
        result = self.gen._post_correct_assignments(assigns)
        assert result[4] == 'Charlie'
        assert result[0] == 'Alice'
        assert result[1] == 'Alice'

    def test_no_correction_if_nobody_missing(self):
        """Pas de correction si tous les élèves sont présents."""
        assigns = ['Alice', 'Bob', 'Charlie']
        result = self.gen._post_correct_assignments(assigns)
        assert result == ['Alice', 'Bob', 'Charlie']


# ─── Validate GPT Choice Tests ───────────────────────────────────────


class TestValidateGPTChoice:
    def setup_method(self):
        self.gen = StudentPDFGenerator()
        self.gen.students = [
            {'nom': 'DUPONT Jean', 'date': '', 'email': ''},
            {'nom': 'DURAND Pierre', 'date': '', 'email': ''},
            {'nom': 'MARTIN Alice', 'date': '', 'email': ''},
        ]

    def test_correct_choice_kept(self):
        result = self.gen._validate_gpt_choice("DUPONT JEAN", "DUPONT Jean")
        assert result == "DUPONT Jean"

    def test_obviously_wrong_corrected(self):
        """Si GPT choisit DUPONT mais le texte lu est clairement MARTIN."""
        result = self.gen._validate_gpt_choice("MARTIN ALICE", "DUPONT Jean")
        assert result == "MARTIN Alice"

    def test_empty_nom_lu(self):
        result = self.gen._validate_gpt_choice("", "DUPONT Jean")
        assert result == "DUPONT Jean"

    def test_empty_eleve_choisi(self):
        result = self.gen._validate_gpt_choice("DUPONT JEAN", "")
        assert result == ""


# ─── Image to Base64 Test ────────────────────────────────────────────


class TestImageToBase64:
    def test_returns_valid_base64(self):
        import base64
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        b64 = StudentPDFGenerator._image_to_base64(img)
        # Should decode without error
        decoded = base64.b64decode(b64)
        assert len(decoded) > 0


# ─── Image to PDF Page Test ──────────────────────────────────────────


class TestImageToPDFPage:
    def test_adds_page(self):
        doc = fitz.open()
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        StudentPDFGenerator._image_to_pdf_page(doc, img)
        assert doc.page_count == 1
        doc.close()

    def test_correct_dimensions(self):
        """Page dimensions match the image (pixels → points at 72 DPI)."""
        doc = fitz.open()
        img = np.zeros((842, 595, 3), dtype=np.uint8)
        StudentPDFGenerator._image_to_pdf_page(doc, img)
        page = doc.load_page(0)
        # The ratio should match regardless of DPI scaling
        img_ratio = 595 / 842
        page_ratio = page.rect.width / page.rect.height
        assert abs(img_ratio - page_ratio) < 0.02
        doc.close()


# ─── Student List Text Tests ─────────────────────────────────────────


class TestBuildStudentListText:
    def test_formats_list(self):
        gen = StudentPDFGenerator()
        gen.students = [
            {'nom': 'DUPONT Jean', 'date': '01/01/2006', 'email': ''},
            {'nom': 'MARTIN Alice', 'date': '02/02/2005', 'email': ''},
        ]
        txt = gen._build_student_list_text()
        assert "1. DUPONT Jean" in txt
        assert "2. MARTIN Alice" in txt
        assert "01/01/2006" in txt


# ─── Rasterization Tests ─────────────────────────────────────────────


class TestRasterization:
    def test_rasterize_returns_ndarray(self):
        gen = StudentPDFGenerator()
        doc = make_a4_pdf(pages=1)
        img = gen._rasterize_page(doc, 0, 72)
        assert isinstance(img, np.ndarray)
        assert img.ndim == 3
        assert img.shape[2] == 3  # BGR
        doc.close()

    def test_dpi_affects_size(self):
        gen = StudentPDFGenerator()
        doc = make_a4_pdf(pages=1)
        img_low = gen._rasterize_page(doc, 0, 72)
        img_high = gen._rasterize_page(doc, 0, 150)
        assert img_high.shape[0] > img_low.shape[0]
        assert img_high.shape[1] > img_low.shape[1]
        doc.close()


# ─── Full Generate (mocked GPT) ─────────────────────────────────────


class TestGenerateWithMockedGPT:
    """
    Test end-to-end de generate() avec GPT mocké.
    """

    @pytest.fixture
    def csv_and_pdfs(self, tmp_path):
        """Crée un CSV + 1 PDF A3 avec 2 feuilles (4 pages)."""
        csv_path = str(tmp_path / "eleves.csv")
        make_csv([
            ("DUPONT Jean", "15/03/2006", "jean@test.fr"),
            ("MARTIN Alice", "22/07/2005", "alice@test.fr"),
        ], csv_path)

        pdf_path = str(tmp_path / "scan_a3.pdf")
        doc = make_a3_pdf(pages=4)  # 2 feuilles recto-verso
        doc.save(pdf_path)
        doc.close()

        return csv_path, [pdf_path], str(tmp_path / "output")

    def _mock_ocr_response(self, student_idx, nom_lu):
        """Crée un mock de réponse GPT."""
        import json
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = json.dumps({
            "numero": student_idx,
            "nom_lu": nom_lu,
            "date_lue": "15/03/2006"
        })
        return mock_resp

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_generate_creates_pdfs(self, csv_and_pdfs):
        csv_path, pdf_paths, output_dir = csv_and_pdfs
        gen = StudentPDFGenerator(csv_path=csv_path, api_key="test-key")

        call_count = [0]

        def mock_create(**kwargs):
            call_count[0] += 1
            # Alternate between students
            if call_count[0] % 2 == 1:
                return self._mock_ocr_response(1, "DUPONT JEAN")
            else:
                return self._mock_ocr_response(2, "MARTIN ALICE")

        with patch.object(gen, '_openai_client') as mock_client:
            mock_client.chat.completions.create = mock_create
            gen._openai_client = mock_client

            result = gen.generate(pdf_paths, output_dir=output_dir)

        assert result['generated_count'] == 2
        assert result['failed_count'] == 0
        assert os.path.isdir(output_dir)
        pdf_files = [f for f in os.listdir(output_dir) if f.endswith('.pdf')]
        assert len(pdf_files) == 2

        # Verify filename_to_student mapping
        assert len(result['filename_to_student']) == 2
        assert any("DUPONT" in v for v in result['filename_to_student'].values())

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_generate_returns_bytes_without_output_dir(self, csv_and_pdfs):
        csv_path, pdf_paths, _ = csv_and_pdfs
        gen = StudentPDFGenerator(csv_path=csv_path, api_key="test-key")

        call_count = [0]

        def mock_create(**kwargs):
            call_count[0] += 1
            if call_count[0] % 2 == 1:
                return self._mock_ocr_response(1, "DUPONT JEAN")
            else:
                return self._mock_ocr_response(2, "MARTIN ALICE")

        with patch.object(gen, '_openai_client') as mock_client:
            mock_client.chat.completions.create = mock_create
            gen._openai_client = mock_client

            result = gen.generate(pdf_paths)

        assert result['generated_count'] == 2
        assert 'DUPONT Jean' in result['student_pdfs']
        assert isinstance(result['student_pdfs']['DUPONT Jean'], bytes)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_generate_handles_ocr_failure_gracefully(self, csv_and_pdfs):
        """Si GPT renvoie toujours null, les feuilles sont INCONNU ou suite."""
        csv_path, pdf_paths, output_dir = csv_and_pdfs
        gen = StudentPDFGenerator(csv_path=csv_path, api_key="test-key")

        import json
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = json.dumps({
            "numero": None, "nom_lu": "illisible", "date_lue": ""
        })

        with patch.object(gen, '_openai_client') as mock_client:
            mock_client.chat.completions.create.return_value = mock_resp
            gen._openai_client = mock_client

            result = gen.generate(pdf_paths, output_dir=output_dir)

        # Should still generate something (with INCONNU)
        assert result['generated_count'] >= 1

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_generate_with_annexes(self, csv_and_pdfs, tmp_path):
        """Test avec annexes mockées."""
        csv_path, pdf_paths, output_dir = csv_and_pdfs

        # Créer un PDF d'annexes (2 pages A4)
        annexe_path = str(tmp_path / "annexes.pdf")
        ann_doc = make_a4_pdf(pages=2)
        ann_doc.save(annexe_path)
        ann_doc.close()

        gen = StudentPDFGenerator(csv_path=csv_path, api_key="test-key")

        call_count = [0]

        def mock_create(**kwargs):
            call_count[0] += 1
            import json
            # Copies: alternent DUPONT/MARTIN, Annexes: les 2 sont DUPONT
            content = kwargs.get('messages', [{}])[0].get('content', [])
            prompt_text = ""
            if isinstance(content, list):
                for c in content:
                    if isinstance(c, dict) and c.get('type') == 'text':
                        prompt_text = c.get('text', '')
                        break

            if 'CMEN' in prompt_text:
                # Annexe → DUPONT
                return self._mock_ocr_response(1, "DUPONT JEAN")
            elif call_count[0] % 2 == 1:
                return self._mock_ocr_response(1, "DUPONT JEAN")
            else:
                return self._mock_ocr_response(2, "MARTIN ALICE")

        with patch.object(gen, '_openai_client') as mock_client:
            mock_client.chat.completions.create = mock_create
            gen._openai_client = mock_client

            result = gen.generate(pdf_paths, annexe_path=annexe_path, output_dir=output_dir)

        assert result['annexes_matched'] >= 1
        assert result['generated_count'] == 2

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_a4_pdfs_are_skipped(self, tmp_path):
        """Les PDFs A4 (non-annexes) sont ignorés."""
        csv_path = str(tmp_path / "eleves.csv")
        make_csv([("TEST Eleve", "01/01/2006", "test@test.fr")], csv_path)

        pdf_path = str(tmp_path / "scan_a4.pdf")
        doc = make_a4_pdf(pages=4)
        doc.save(pdf_path)
        doc.close()

        gen = StudentPDFGenerator(csv_path=csv_path, api_key="test-key")

        result = gen.generate([pdf_path], output_dir=str(tmp_path / "out"))

        assert result['generated_count'] == 0
        assert result['missing_students'] == ['TEST Eleve']

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_missing_students_reported(self, csv_and_pdfs):
        """Les élèves du CSV non trouvés dans les scans sont rapportés."""
        csv_path, pdf_paths, output_dir = csv_and_pdfs
        gen = StudentPDFGenerator(csv_path=csv_path, api_key="test-key")

        # Make GPT always return student 1
        import json
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = json.dumps({
            "numero": 1, "nom_lu": "DUPONT JEAN", "date_lue": "15/03/2006"
        })

        with patch.object(gen, '_openai_client') as mock_client:
            mock_client.chat.completions.create.return_value = mock_resp
            gen._openai_client = mock_client

            result = gen.generate(pdf_paths, output_dir=output_dir)

        # MARTIN Alice should be in missing_students
        assert 'MARTIN Alice' in result['missing_students']
