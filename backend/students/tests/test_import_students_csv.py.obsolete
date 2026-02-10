import pytest
import os
import csv
from students.services.csv_import import parse_students_csv, CsvReadError, import_students_from_csv
from students.models import Student

@pytest.fixture
def clean_csv(tmp_path):
    f = tmp_path / "valid.csv"
    content = "INE,NOM,PRENOM\n123,Doe,John\n456,Smith,Jane"
    f.write_text(content, encoding="utf-8")
    return str(f)

@pytest.fixture
def bom_csv(tmp_path):
    f = tmp_path / "bom.csv"
    content = "\ufeffINE,NOM,PRENOM\n123,Doe,John"
    f.write_text(content, encoding="utf-8")
    return str(f)

@pytest.fixture
def bad_header_csv(tmp_path):
    f = tmp_path / "bad.csv"
    f.write_text("ID,NOM,PRENOM\n1,A,B", encoding="utf-8")
    return str(f)

@pytest.mark.django_db
def test_read_csv_nominal(clean_csv):
    result, rows = parse_students_csv(clean_csv, delimiter=',')
    assert result.delimiter == ','
    assert len(rows) == 2
    assert rows[0]['INE'] == '123'

@pytest.mark.django_db
def test_read_csv_bom(bom_csv):
    result, rows = parse_students_csv(bom_csv, delimiter=',', )
    assert len(rows) == 1
    assert rows[0]['INE'] == '123' 

@pytest.mark.django_db
def test_read_csv_missing_header(bad_header_csv):
    # Service robustly handles missing headers by skipping rows and logging errors
    result, rows = parse_students_csv(bad_header_csv, delimiter=',')
    # "INE" is required but checking "ID" in fixture
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
