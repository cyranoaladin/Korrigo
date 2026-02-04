import pytest
import os
import csv
from students.services.csv_import import parse_students_csv, CsvReadError, import_students_from_csv
from students.models import Student

@pytest.fixture
def clean_csv(tmp_path):
    f = tmp_path / "valid.csv"
    # Use expected format: Élèves (FULL_NAME), Né(e) le (DATE_NAISSANCE), Adresse E-mail (EMAIL)
    content = "Élèves,Né(e) le,Adresse E-mail\nDoe John,15/01/2008,john@test.com\nSmith Jane,20/02/2008,jane@test.com"
    f.write_text(content, encoding="utf-8")
    return str(f)

@pytest.fixture
def bom_csv(tmp_path):
    f = tmp_path / "bom.csv"
    content = "\ufeffÉlèves,Né(e) le,Adresse E-mail\nDoe John,15/01/2008,john@test.com"
    f.write_text(content, encoding="utf-8")
    return str(f)

@pytest.fixture
def bad_header_csv(tmp_path):
    f = tmp_path / "bad.csv"
    # Missing required FULL_NAME and DATE_NAISSANCE columns
    f.write_text("ID,EMAIL\n1,test@test.com", encoding="utf-8")
    return str(f)

@pytest.mark.django_db
def test_read_csv_nominal(clean_csv):
    result, rows = parse_students_csv(clean_csv, delimiter=',')
    assert result.delimiter == ','
    assert len(rows) == 2
    assert rows[0]['EMAIL'] == 'john@test.com'

@pytest.mark.django_db
def test_read_csv_bom(bom_csv):
    result, rows = parse_students_csv(bom_csv, delimiter=',', )
    assert len(rows) == 1
    assert rows[0]['EMAIL'] == 'john@test.com'

@pytest.mark.django_db
def test_read_csv_missing_header(bad_header_csv):
    # Service robustly handles missing headers by skipping rows and logging errors
    result, rows = parse_students_csv(bad_header_csv, delimiter=',')
    # "EMAIL" is required but checking "ID" in fixture
    assert len(result.errors) > 0
    assert result.skipped > 0

@pytest.mark.django_db
def test_read_csv_file_not_found():
    with pytest.raises(CsvReadError):
        parse_students_csv("nonexistent.csv")

@pytest.mark.django_db
def test_import_integration(clean_csv):
    # Test high level integration
    result = import_students_from_csv(clean_csv, Student, delimiter=',')
    assert result.created == 2
    assert Student.objects.count() == 2
