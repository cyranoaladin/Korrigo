#!/usr/bin/env python
"""
PRONOTE CSV Export - Manual Verification Test Script
Task: ZF-AUD-10

This script creates test data and performs manual verification tests
for the PRONOTE CSV export feature.

Usage:
    # Start the Docker environment first
    docker-compose up -d
    
    # Run this script from the backend directory
    cd backend
    python ../zenflow/tasks/export-pronote-csv-format-encoda-2e50/manual_verification_test.py
    
    # Or use Django shell
    python manage.py shell < manual_verification_test.py
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..', 'backend'))
django.setup()

from django.contrib.auth import get_user_model
from students.models import Student
from exams.models import Exam, ExamCopy
from grading.models import Annotation, Score
from datetime import datetime
import uuid
import json

User = get_user_model()

def create_test_users():
    """Create admin and teacher test users"""
    print("\n=== Creating Test Users ===")
    
    # Create admin user
    admin, created = User.objects.get_or_create(
        username='admin_test',
        defaults={
            'email': 'admin@test.com',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin.set_password('adminpass123')
        admin.save()
        print(f"✅ Admin user created: admin_test / adminpass123")
    else:
        print(f"ℹ️  Admin user already exists: admin_test")
    
    # Create teacher user
    teacher, created = User.objects.get_or_create(
        username='teacher_test',
        defaults={
            'email': 'teacher@test.com',
            'is_staff': False,
            'is_superuser': False
        }
    )
    if created:
        teacher.set_password('teacherpass123')
        teacher.save()
        print(f"✅ Teacher user created: teacher_test / teacherpass123")
    else:
        print(f"ℹ️  Teacher user already exists: teacher_test")
    
    return admin, teacher


def create_test_students():
    """Create test students with valid INE"""
    print("\n=== Creating Test Students ===")
    
    students_data = [
        {
            'ine': '11111111111',
            'first_name': 'Alice',
            'last_name': 'Durand',
            'classe': 'TS1'
        },
        {
            'ine': '22222222222',
            'first_name': 'François',
            'last_name': 'Müller',
            'classe': 'TS1'
        },
        {
            'ine': '33333333333',
            'first_name': 'Marie',
            'last_name': "O'Connor",
            'classe': 'TS1'
        },
        # Student without INE for validation testing
        {
            'ine': '',
            'first_name': 'Jean',
            'last_name': 'Sans-INE',
            'classe': 'TS1'
        }
    ]
    
    students = []
    for data in students_data:
        student, created = Student.objects.get_or_create(
            ine=data['ine'],
            defaults=data
        )
        if created:
            print(f"✅ Student created: {data['first_name']} {data['last_name']} (INE: {data['ine'] or 'EMPTY'})")
        else:
            print(f"ℹ️  Student already exists: {data['first_name']} {data['last_name']}")
        students.append(student)
    
    return students


def create_test_exam():
    """Create test exam with grading structure"""
    print("\n=== Creating Test Exam ===")
    
    grading_structure = [
        {
            'id': 'ex1',
            'name': 'Exercice 1',
            'max_points': 10,
            'questions': [
                {'id': 'q1', 'name': 'Question 1', 'max_points': 5},
                {'id': 'q2', 'name': 'Question 2', 'max_points': 5}
            ]
        },
        {
            'id': 'ex2',
            'name': 'Exercice 2',
            'max_points': 10,
            'questions': [
                {'id': 'q3', 'name': 'Question 3', 'max_points': 10}
            ]
        }
    ]
    
    exam = Exam.objects.create(
        name='MATHEMATIQUES',
        date=datetime(2026, 2, 1).date(),
        grading_structure=grading_structure,
        academic_year='2025-2026'
    )
    
    print(f"✅ Exam created: {exam.name} (UUID: {exam.id})")
    return exam


def create_test_copies(exam, students):
    """Create test copies with various scenarios"""
    print("\n=== Creating Test Copies ===")
    
    copies_data = [
        {
            'student': students[0],  # Alice Durand
            'grade': 15.5,
            'comment': 'Excellent travail',
            'is_identified': True,
            'status': 'GRADED'
        },
        {
            'student': students[1],  # François Müller (accents)
            'grade': 12.0,
            'comment': 'Bien; peut mieux faire',  # Semicolon in comment
            'is_identified': True,
            'status': 'GRADED'
        },
        {
            'student': students[2],  # Marie O'Connor (apostrophe)
            'grade': 18.25,
            'comment': 'Très "bon" travail!',  # Quotes in comment
            'is_identified': True,
            'status': 'GRADED'
        },
        {
            'student': students[3],  # Jean Sans-INE
            'grade': 10.0,
            'comment': 'Moyen',
            'is_identified': True,
            'status': 'GRADED'
        },
        # Unidentified copy for validation testing
        {
            'student': students[0],
            'grade': 16.0,
            'comment': 'Test non identifié',
            'is_identified': False,
            'status': 'GRADED'
        }
    ]
    
    copies = []
    for data in copies_data:
        copy = ExamCopy.objects.create(
            exam=exam,
            student=data['student'],
            is_identified=data['is_identified'],
            status=data['status']
        )
        
        # Create annotations with score_delta to simulate grading
        # Assuming grade is out of 20
        Annotation.objects.create(
            copy=copy,
            annotation_type='SCORE',
            score_delta=data['grade'],
            comment=data['comment']
        )
        
        status = "✅" if data['is_identified'] else "⚠️"
        print(f"{status} Copy created: {data['student'].first_name} {data['student'].last_name} - "
              f"Grade: {data['grade']}/20 (identified: {data['is_identified']})")
        copies.append(copy)
    
    return copies


def test_api_export(exam, admin_token=None):
    """Test API export endpoint"""
    print("\n=== Testing API Export ===")
    print(f"ℹ️  Exam UUID: {exam.id}")
    
    # Print curl command for manual testing
    curl_cmd = f"""
    # Test with default coefficient
    curl -X POST \\
      -H "Content-Type: application/json" \\
      -H "Authorization: Bearer <admin_token>" \\
      http://localhost:8000/api/exams/{exam.id}/export-pronote/ \\
      --output export_test.csv
    
    # Test with custom coefficient
    curl -X POST \\
      -H "Content-Type: application/json" \\
      -H "Authorization: Bearer <admin_token>" \\
      -d '{{"coefficient": 2.5}}' \\
      http://localhost:8000/api/exams/{exam.id}/export-pronote/ \\
      --output export_test_coeff.csv
    
    # Test as non-admin (should fail)
    curl -X POST \\
      -H "Content-Type: application/json" \\
      -H "Authorization: Bearer <teacher_token>" \\
      http://localhost:8000/api/exams/{exam.id}/export-pronote/
    """
    
    print("📋 Copy these curl commands to test the API:")
    print(curl_cmd)


def test_management_command(exam):
    """Test management command"""
    print("\n=== Testing Management Command ===")
    print(f"ℹ️  Exam UUID: {exam.id}")
    
    commands = f"""
    # Basic export to stdout
    python manage.py export_pronote {exam.id}
    
    # Export to file
    python manage.py export_pronote {exam.id} --output /tmp/export_pronote.csv
    
    # Validation only
    python manage.py export_pronote {exam.id} --validate-only
    
    # Custom coefficient
    python manage.py export_pronote {exam.id} --coefficient 2.5 --output /tmp/export_coeff.csv
    
    # Inspect file format
    hexdump -C /tmp/export_pronote.csv | head -1  # Check UTF-8 BOM (ef bb bf)
    file /tmp/export_pronote.csv  # Check CRLF line endings
    cat -A /tmp/export_pronote.csv  # View raw format
    """
    
    print("📋 Run these commands to test the export:")
    print(commands)


def test_csv_validation(exam):
    """Test CSV format validation"""
    print("\n=== CSV Validation Checklist ===")
    
    validation_steps = """
    After generating the CSV, verify:
    
    ✓ Format Validation:
      - [ ] UTF-8 BOM at start (\\ufeff or ef bb bf in hex)
      - [ ] Header: INE;MATIERE;NOTE;COEFF;COMMENTAIRE
      - [ ] Delimiter: semicolon (;)
      - [ ] Line endings: CRLF (\\r\\n or ^M in vim)
      - [ ] No trailing semicolons
    
    ✓ Encoding Test:
      - [ ] Open in text editor → accents display correctly
      - [ ] Open in Excel → no encoding issues
      - [ ] François appears as François, not Fran├ºois
    
    ✓ Decimal Format:
      - [ ] All grades use comma (,) as separator
      - [ ] All grades have 2 decimal places
      - [ ] 15.5 → "15,50"
      - [ ] 12.0 → "12,00"
      - [ ] 18.25 → "18,25"
    
    ✓ Special Characters:
      - [ ] Quotes in comments are handled
      - [ ] Semicolons in comments don't break columns
      - [ ] Accented names display correctly
    
    ✓ Validation Errors:
      - [ ] Export fails for student without INE
      - [ ] Export fails for unidentified copies
      - [ ] Error messages in French
    
    Expected CSV output:
    INE;MATIERE;NOTE;COEFF;COMMENTAIRE
    11111111111;MATHEMATIQUES;15,50;1,0;Excellent travail
    22222222222;MATHEMATIQUES;12,00;1,0;Bien; peut mieux faire
    33333333333;MATHEMATIQUES;18,25;1,0;Très "bon" travail!
    """
    
    print(validation_steps)


def print_summary(exam):
    """Print test summary"""
    print("\n" + "="*60)
    print("MANUAL VERIFICATION TEST SETUP COMPLETE")
    print("="*60)
    
    print(f"\n📊 Test Data Summary:")
    print(f"   - Exam UUID: {exam.id}")
    print(f"   - Exam Name: {exam.name}")
    print(f"   - Graded Copies: {exam.copies.filter(status='GRADED').count()}")
    print(f"   - Identified Copies: {exam.copies.filter(is_identified=True, status='GRADED').count()}")
    
    print(f"\n👥 Test Users:")
    print(f"   - Admin: admin_test / adminpass123")
    print(f"   - Teacher: teacher_test / teacherpass123")
    
    print(f"\n📝 Next Steps:")
    print(f"   1. Start the application: docker-compose up -d")
    print(f"   2. Get admin token (login via API)")
    print(f"   3. Test API endpoint (see curl commands above)")
    print(f"   4. Test management command (see commands above)")
    print(f"   5. Validate CSV format (see checklist above)")
    print(f"   6. Update audit.md with test results")
    
    print(f"\n📄 Export URL:")
    print(f"   POST http://localhost:8000/api/exams/{exam.id}/export-pronote/")


def main():
    """Main test execution"""
    print("\n" + "="*60)
    print("PRONOTE CSV EXPORT - MANUAL VERIFICATION TEST")
    print("Task: ZF-AUD-10")
    print("="*60)
    
    try:
        # Create test data
        admin, teacher = create_test_users()
        students = create_test_students()
        exam = create_test_exam()
        copies = create_test_copies(exam, students)
        
        # Print test instructions
        test_api_export(exam)
        test_management_command(exam)
        test_csv_validation(exam)
        print_summary(exam)
        
        print("\n✅ Test data created successfully!")
        print("⚠️  Some copies have validation issues (missing INE, unidentified)")
        print("   This is intentional for testing validation logic.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
