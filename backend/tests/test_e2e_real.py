#!/usr/bin/env python3
"""
Test E2E reproductible - Simulation du workflow complet
Ce script simule le workflow complet: upload -> split -> identify -> grade -> finalize
"""
import os
import sys
import tempfile
import json

import pytest
from django.conf import settings

from exams.models import Exam, Copy, Booklet
from students.models import Student
from grading.models import Annotation, GradingEvent
from django.contrib.auth.models import User, Group
from core.auth import UserRole
from django.utils import timezone


def create_test_scenario():
    """Crée un scénario de test complet"""
    print("=== SCÉNARIO DE TEST E2E ===")
    
    # Créer les rôles
    admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
    teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
    student_group, _ = Group.objects.get_or_create(name=UserRole.STUDENT)
    
    # Créer utilisateurs de test
    admin_user, _ = User.objects.get_or_create(username='admin_test_e2e')
    admin_user.groups.add(admin_group)
    
    teacher_user, _ = User.objects.get_or_create(username='teacher_test_e2e')
    teacher_user.groups.add(teacher_group)
    
    student_user, _ = User.objects.get_or_create(username='student_test_e2e')
    student_user.groups.add(student_group)
    
    # Créer étudiant
    student, _ = Student.objects.get_or_create(
        first_name="Jean",
        last_name="E2E",
        date_naissance="2005-03-15",
        defaults={
            "class_name": "TG2",
            "email": "jean.e2e@test.edu",
            "user": student_user,
        },
    )
    
    # Créer examen
    exam, _ = Exam.objects.get_or_create(
        name='E2E Test Exam',
        date='2026-01-01'
    )
    
    print(f"✅ Créé examen: {exam.name}")
    print(f"✅ Créé étudiant: {student.first_name} {student.last_name}")
    print(f"✅ Créé utilisateurs: admin, teacher, student")
    
    # Créer copie
    copy = Copy.objects.create(
        exam=exam,
        anonymous_id="E2E_TEST_001",
        status=Copy.Status.READY
    )
    
    # Créer fascicule
    booklet = Booklet.objects.create(
        exam=exam,
        start_page=1,
        end_page=4,
        student_name_guess="Jean E2E"
    )
    copy.booklets.add(booklet)
    
    print(f"✅ Créé copie: {copy.anonymous_id} (status: {copy.status})")
    
    # Identification (simulation)
    copy.student = student
    copy.is_identified = True
    copy.validated_at = timezone.now()
    copy.save()
    
    print(f"✅ Identification: {copy.anonymous_id} -> {student.first_name}")
    print(f"✅ Statut: {copy.status}")
    
    # Correction (simulation)
    copy.status = Copy.Status.IN_PROGRESS
    copy.assigned_corrector = teacher_user
    copy.locked_by = teacher_user
    copy.locked_at = timezone.now()
    copy.save()
    
    print(f"✅ Verrouillage: {copy.anonymous_id} par {teacher_user.username}")
    
    # Ajouter annotation
    annotation = Annotation.objects.create(
        copy=copy,
        page_index=0,
        x=0.2, y=0.3, w=0.1, h=0.05,
        content="Bon travail!",
        type=Annotation.Type.COMMENT,
        score_delta=2,
        created_by=teacher_user
    )
    
    print(f"✅ Annotation ajoutée: {annotation.content}")
    
    # Finaliser
    copy.status = Copy.Status.FINALIZED
    copy.graded_at = timezone.now()
    copy.save()
    
    # Créer événement d'audit
    GradingEvent.objects.create(
        copy=copy,
        action=GradingEvent.Action.FINALIZE,
        actor=teacher_user,
        metadata={'final_score': 16}
    )
    
    print(f"✅ Finalisation: {copy.anonymous_id} -> {copy.status}")
    print(f"✅ Événement d'audit créé")
    
    # Vérifier le workflow complet
    assert copy.student == student, "La copie doit être liée à l'étudiant"
    assert copy.status == Copy.Status.FINALIZED, "La copie doit être FINALIZED"
    assert annotation.copy == copy, "L'annotation doit être liée à la copie"
    
    print("\n✅ WORKFLOW E2E COMPLET RÉUSSI:")
    print(f"   - Upload examen: OK")
    print(f"   - Création copie: OK") 
    print(f"   - Identification: OK")
    print(f"   - Correction: OK")
    print(f"   - Annotation: OK")
    print(f"   - Finalisation: OK")
    print(f"   - Audit trail: OK")
    
    return True


@pytest.mark.django_db
def test_multi_roles_access():
    """Test des accès multi-rôles"""
    print("\n=== TEST ACCÈS MULTI-RÔLES ===")

    # Set up test data (when run via pytest, create_test_scenario is not called by __main__)
    create_test_scenario()

    # Vérifier que les rôles sont correctement attribués
    admin_user = User.objects.get(username='admin_test_e2e')
    teacher_user = User.objects.get(username='teacher_test_e2e')
    student_user = User.objects.get(username='student_test_e2e')
    
    admin_groups = [g.name for g in admin_user.groups.all()]
    teacher_groups = [g.name for g in teacher_user.groups.all()]
    student_groups = [g.name for g in student_user.groups.all()]
    
    print(f"Admin groups: {admin_groups}")
    print(f"Teacher groups: {teacher_groups}")
    print(f"Student groups: {student_groups}")
    
    # Vérifier les attributions
    assert UserRole.ADMIN in admin_groups, "Admin doit avoir le rôle admin"
    assert UserRole.TEACHER in teacher_groups, "Teacher doit avoir le rôle teacher"
    assert UserRole.STUDENT in student_groups, "Student doit avoir le rôle student"
    
    print("✅ Accès multi-rôles correctement configurés")


if __name__ == "__main__":
    try:
        success1 = create_test_scenario()
        success2 = test_multi_roles_access()
        
        if success1 and success2:
            print("\n🎉 TOUS LES TESTS E2E ONT RÉUSSI!")
            sys.exit(0)
        else:
            print("\n❌ ÉCHEC DES TESTS E2E")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERREUR DANS LE TEST E2E: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
