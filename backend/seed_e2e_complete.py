#!/usr/bin/env python
"""
E2E Complete Seed Script - PRD-19
Creates all necessary data for E2E Playwright tests.

Usage:
    python seed_e2e_complete.py

Expected credentials (matching frontend/tests/e2e/helpers/auth.ts):
    - Admin: admin / admin
    - Teacher: teacher / password
    - Student: e2e.student@test.com / E2E_STUDENT
"""
import os
import sys
import json
import django
from datetime import date, timedelta
from pathlib import Path

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from core.auth import create_user_roles
from students.models import Student
from exams.models import Exam, Copy, Booklet

User = get_user_model()


def seed_e2e_complete():
    """
    Complete E2E seeding with all workflow states.
    Idempotent: can be run multiple times safely.
    """
    print("=" * 60)
    print("🌱 E2E Complete Seed - PRD-19")
    print("=" * 60)
    
    result = {
        'users': {},
        'students': {},
        'exams': {},
        'copies': {}
    }
    
    with transaction.atomic():
        # ============================================================
        # 1. CREATE USER ROLES
        # ============================================================
        print("\n[1/5] Creating user roles...")
        admin_group, teacher_group, student_group = create_user_roles()
        print(f"  ✓ Roles: Admin, Teacher, Student")
        
        # ============================================================
        # 2. CREATE USERS (matching auth.ts credentials)
        # ============================================================
        print("\n[2/5] Creating users...")
        
        # Admin: admin / admin
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@e2e.test',
                'is_staff': True,
                'is_superuser': True
            }
        )
        admin.set_password('admin')
        admin.save()
        admin.groups.add(admin_group)
        result['users']['admin'] = {'id': admin.id, 'username': 'admin', 'password': 'admin'}
        print(f"  ✓ Admin: admin / admin (id={admin.id})")
        
        # Teacher: teacher / password
        teacher, created = User.objects.get_or_create(
            username='teacher',
            defaults={
                'email': 'teacher@e2e.test',
                'is_staff': True
            }
        )
        teacher.set_password('password')
        teacher.save()
        teacher.groups.add(teacher_group)
        result['users']['teacher'] = {'id': teacher.id, 'username': 'teacher', 'password': 'password'}
        print(f"  ✓ Teacher: teacher / password (id={teacher.id})")
        
        # Teacher2 for dispatch tests
        teacher2, created = User.objects.get_or_create(
            username='teacher2',
            defaults={
                'email': 'teacher2@e2e.test',
                'is_staff': True
            }
        )
        teacher2.set_password('password')
        teacher2.save()
        teacher2.groups.add(teacher_group)
        result['users']['teacher2'] = {'id': teacher2.id, 'username': 'teacher2', 'password': 'password'}
        print(f"  ✓ Teacher2: teacher2 / password (id={teacher2.id})")
        
        # ============================================================
        # 3. CREATE STUDENTS (matching auth.ts credentials)
        # ============================================================
        print("\n[3/5] Creating students...")
        
        # Primary E2E student: e2e.student@test.com / E2E_STUDENT
        # Note: Student model uses first_name + last_name, login checks last_name
        student1, created = Student.objects.get_or_create(
            email='e2e.student@test.com',
            defaults={
                'first_name': 'Test',
                'last_name': 'E2E_STUDENT',
                'class_name': '3A'
            }
        )
        student1_name = f"{student1.first_name} {student1.last_name}"
        result['students']['student1'] = {'id': student1.id, 'email': student1.email, 'name': student1_name}
        print(f"  ✓ Student1: {student1.email} / {student1_name} (id={student1.id})")
        
        # Secondary student for security tests
        student2, created = Student.objects.get_or_create(
            email='other.student@test.com',
            defaults={
                'first_name': 'Test',
                'last_name': 'OTHER_STUDENT',
                'class_name': '3B'
            }
        )
        student2_name = f"{student2.first_name} {student2.last_name}"
        result['students']['student2'] = {'id': student2.id, 'email': student2.email, 'name': student2_name}
        print(f"  ✓ Student2: {student2.email} / {student2_name} (id={student2.id})")
        
        # ============================================================
        # 4. CREATE EXAMS
        # ============================================================
        print("\n[4/5] Creating exams...")
        
        # Main E2E exam
        exam_e2e, created = Exam.objects.get_or_create(
            name='E2E Test Exam',
            defaults={'date': date.today()}
        )
        result['exams']['e2e'] = {'id': str(exam_e2e.id), 'name': exam_e2e.name}
        print(f"  ✓ E2E Exam: {exam_e2e.name} (id={exam_e2e.id})")
        
        # Gate 4 exam (for student flow tests)
        exam_gate4, created = Exam.objects.get_or_create(
            name='Gate 4 Exam',
            defaults={'date': date.today() - timedelta(days=7)}
        )
        result['exams']['gate4'] = {'id': str(exam_gate4.id), 'name': exam_gate4.name}
        print(f"  ✓ Gate4 Exam: {exam_gate4.name} (id={exam_gate4.id})")
        
        # Dispatch exam
        exam_dispatch, created = Exam.objects.get_or_create(
            name='Dispatch Test Exam',
            defaults={'date': date.today()}
        )
        result['exams']['dispatch'] = {'id': str(exam_dispatch.id), 'name': exam_dispatch.name}
        print(f"  ✓ Dispatch Exam: {exam_dispatch.name} (id={exam_dispatch.id})")
        
        # ============================================================
        # 5. CREATE COPIES IN ALL STATES
        # ============================================================
        print("\n[5/5] Creating copies in all workflow states...")
        
        # --- E2E Exam Copies ---
        
        # STAGING copy (for merge tests)
        copy_staging, _ = Copy.objects.get_or_create(
            exam=exam_e2e,
            anonymous_id='E2E-STAGING-001',
            defaults={
                'status': Copy.Status.STAGING,
                'is_identified': False
            }
        )
        result['copies']['staging'] = str(copy_staging.id)
        print(f"  ✓ STAGING copy: {copy_staging.id}")
        
        # READY copy unidentified (for identification desk)
        copy_ready_unid, _ = Copy.objects.get_or_create(
            exam=exam_e2e,
            anonymous_id='E2E-READY-UNID',
            defaults={
                'status': Copy.Status.READY,
                'is_identified': False
            }
        )
        result['copies']['ready_unidentified'] = str(copy_ready_unid.id)
        print(f"  ✓ READY (unidentified) copy: {copy_ready_unid.id}")
        
        # READY copy identified (for dispatch)
        copy_ready_id, _ = Copy.objects.get_or_create(
            exam=exam_e2e,
            anonymous_id='E2E-READY-ID',
            defaults={
                'status': Copy.Status.READY,
                'is_identified': True,
                'student': student1
            }
        )
        result['copies']['ready_identified'] = str(copy_ready_id.id)
        print(f"  ✓ READY (identified) copy: {copy_ready_id.id}")
        
        # LOCKED copy (for corrector flow)
        copy_locked, _ = Copy.objects.get_or_create(
            exam=exam_e2e,
            anonymous_id='E2E-LOCKED-001',
            defaults={
                'status': Copy.Status.LOCKED,
                'is_identified': True,
                'student': student1,
                'assigned_corrector': teacher
            }
        )
        result['copies']['locked'] = str(copy_locked.id)
        print(f"  ✓ LOCKED copy: {copy_locked.id}")
        
        # --- Gate 4 Exam Copies (for student portal) ---
        
        # GRADED copy for student1 (visible in portal)
        copy_graded, _ = Copy.objects.get_or_create(
            exam=exam_gate4,
            anonymous_id='GATE4-GRADED-001',
            defaults={
                'status': Copy.Status.GRADED,
                'is_identified': True,
                'student': student1,
                'assigned_corrector': teacher
            }
        )
        result['copies']['graded'] = str(copy_graded.id)
        print(f"  ✓ GRADED copy (student1): {copy_graded.id}")
        
        # LOCKED copy for student1 (NOT visible in portal)
        copy_locked_gate4, _ = Copy.objects.get_or_create(
            exam=exam_gate4,
            anonymous_id='GATE4-LOCKED-001',
            defaults={
                'status': Copy.Status.LOCKED,
                'is_identified': True,
                'student': student1,
                'assigned_corrector': teacher
            }
        )
        result['copies']['locked_gate4'] = str(copy_locked_gate4.id)
        print(f"  ✓ LOCKED copy (student1, not visible): {copy_locked_gate4.id}")
        
        # GRADED copy for student2 (for security test - 403)
        copy_graded_other, _ = Copy.objects.get_or_create(
            exam=exam_gate4,
            anonymous_id='GATE4-GRADED-OTHER',
            defaults={
                'status': Copy.Status.GRADED,
                'is_identified': True,
                'student': student2,
                'assigned_corrector': teacher
            }
        )
        result['copies']['graded_other'] = str(copy_graded_other.id)
        print(f"  ✓ GRADED copy (student2): {copy_graded_other.id}")
        
        # --- Dispatch Exam Copies (for dispatch tests) ---
        
        # Multiple READY copies for dispatch
        for i in range(5):
            copy_dispatch, _ = Copy.objects.get_or_create(
                exam=exam_dispatch,
                anonymous_id=f'DISPATCH-READY-{i+1:03d}',
                defaults={
                    'status': Copy.Status.READY,
                    'is_identified': True,
                    'student': student1 if i % 2 == 0 else student2
                }
            )
            if i == 0:
                result['copies']['dispatch_ready'] = str(copy_dispatch.id)
        print(f"  ✓ 5 READY copies for dispatch")
    
    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "=" * 60)
    print("✅ E2E SEED COMPLETED SUCCESSFULLY")
    print("=" * 60)
    
    print("\n📋 CREDENTIALS SUMMARY:")
    print("  Admin:    admin / admin")
    print("  Teacher:  teacher / password")
    print("  Student:  e2e.student@test.com / E2E_STUDENT")
    
    print("\n📊 DATA SUMMARY:")
    print(f"  Users:    {len(result['users'])}")
    print(f"  Students: {len(result['students'])}")
    print(f"  Exams:    {len(result['exams'])}")
    print(f"  Copies:   {len(result['copies'])}")
    
    return result


if __name__ == "__main__":
    result = seed_e2e_complete()
    
    # Output JSON for parsing
    print(f"\n__E2E_SEED_RESULT__: {json.dumps(result, default=str)}")
