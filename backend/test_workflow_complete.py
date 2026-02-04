#!/usr/bin/env python
"""
Test complet du workflow: Upload -> Agrafage -> Video-coding -> Dispatch

Ce script teste le flux avec le fichier eval_loi_binom_log.pdf (28 élèves, 88 pages A3)
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from exams.models import Exam, Booklet, Copy
from students.models import Student
import uuid

User = get_user_model()

def print_section(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_stats(exam):
    """Affiche les statistiques d'un examen."""
    copies = Copy.objects.filter(exam=exam)
    booklets = Booklet.objects.filter(exam=exam)
    
    print(f"\n--- Statistiques Exam: {exam.name} ---")
    print(f"Booklets: {booklets.count()}")
    print(f"Copies totales: {copies.count()}")
    
    for status_choice in Copy.Status.choices:
        count = copies.filter(status=status_choice[0]).count()
        if count > 0:
            print(f"  - {status_choice[1]}: {count}")
    
    identified = copies.filter(is_identified=True).count()
    unidentified = copies.filter(is_identified=False).count()
    print(f"Identifiées: {identified}, Non identifiées: {unidentified}")
    
    dispatched = copies.filter(assigned_corrector__isnull=False).count()
    print(f"Dispatchées: {dispatched}")

def test_step1_upload(pdf_path):
    """Étape 1: Upload du PDF et création des booklets."""
    print_section("ÉTAPE 1: Upload du PDF")
    
    from processing.services.a3_pdf_processor import A3PDFProcessor
    
    # Créer l'examen
    exam = Exam.objects.create(
        name=f"Test Workflow {timezone.now().strftime('%Y%m%d-%H%M%S')}",
        date=timezone.now().date(),
        pages_per_booklet=4  # A3 = 4 pages A4
    )
    print(f"✓ Examen créé: {exam.id}")
    
    # Copier le PDF vers le media
    from django.core.files import File
    with open(pdf_path, 'rb') as f:
        exam.pdf_source.save('test_upload.pdf', File(f))
    print(f"✓ PDF uploadé: {exam.pdf_source.path}")
    
    # Traiter le PDF
    processor = A3PDFProcessor(dpi=150)
    booklets = processor.process_exam(exam)
    print(f"✓ Booklets créés: {len(booklets)}")
    
    # Créer les copies STAGING (comme le fait ExamUploadView)
    for booklet in booklets:
        copy = Copy.objects.create(
            exam=exam,
            anonymous_id=str(uuid.uuid4())[:8].upper(),
            status=Copy.Status.STAGING,
            is_identified=False
        )
        copy.booklets.add(booklet)
    
    print_stats(exam)
    return exam

def test_step2_stapling(exam):
    """Étape 2: Agrafage - Fusionner les booklets en copies READY."""
    print_section("ÉTAPE 2: Agrafage (Merge Booklets)")
    
    booklets = list(Booklet.objects.filter(exam=exam).order_by('start_page'))
    print(f"Booklets à traiter: {len(booklets)}")
    
    # Simuler l'agrafage: chaque booklet devient une copie READY
    # (Dans le cas réel, l'utilisateur peut fusionner plusieurs booklets)
    copies_created = 0
    
    for booklet in booklets:
        # Vérifier si ce booklet est déjà dans une copie non-STAGING
        existing_ready = booklet.assigned_copy.exclude(status=Copy.Status.STAGING)
        if existing_ready.exists():
            print(f"  Booklet {booklet.id} déjà dans copie READY, skip")
            continue
        
        # Supprimer les copies STAGING associées
        staging_copies = booklet.assigned_copy.filter(status=Copy.Status.STAGING)
        staging_ids = list(staging_copies.values_list('id', flat=True))
        if staging_ids:
            Copy.objects.filter(id__in=staging_ids).delete()
        
        # Créer une nouvelle copie READY
        copy = Copy.objects.create(
            exam=exam,
            anonymous_id=str(uuid.uuid4())[:8].upper(),
            status=Copy.Status.READY,
            is_identified=False,
            validated_at=timezone.now()
        )
        copy.booklets.add(booklet)
        copies_created += 1
    
    print(f"✓ Copies READY créées: {copies_created}")
    print_stats(exam)
    return exam

def test_step3_videocoding(exam):
    """Étape 3: Video-coding - Vérifier les copies disponibles pour identification."""
    print_section("ÉTAPE 3: Video-coding (Identification)")
    
    # Simuler ce que fait IdentificationDeskView
    unidentified_copies = Copy.objects.filter(
        exam=exam,
        is_identified=False,
        status=Copy.Status.READY
    ).prefetch_related('booklets')
    
    print(f"Copies disponibles pour identification: {unidentified_copies.count()}")
    
    # Vérifier qu'il n'y a pas de doublons
    seen_booklet_sets = set()
    duplicates = 0
    
    for copy in unidentified_copies:
        booklet_ids = tuple(sorted(str(b.id) for b in copy.booklets.all()))
        if booklet_ids in seen_booklet_sets:
            duplicates += 1
        else:
            seen_booklet_sets.add(booklet_ids)
    
    if duplicates > 0:
        print(f"⚠ ATTENTION: {duplicates} doublons détectés!")
    else:
        print(f"✓ Aucun doublon détecté")
    
    # Créer des étudiants de test si nécessaire
    students = list(Student.objects.all()[:unidentified_copies.count()])
    if len(students) < unidentified_copies.count():
        print(f"Création de {unidentified_copies.count() - len(students)} étudiants de test...")
        for i in range(len(students), unidentified_copies.count()):
            student = Student.objects.create(
                email=f"test_student_{i}@test.com",
                full_name=f"TEST STUDENT {i}",
                date_of_birth="2008-01-15",
                class_name="TEST"
            )
            students.append(student)
    
    # Simuler l'identification
    identified_count = 0
    for copy, student in zip(unidentified_copies, students):
        copy.student = student
        copy.is_identified = True
        copy.save()
        identified_count += 1
    
    print(f"✓ Copies identifiées: {identified_count}")
    print_stats(exam)
    return exam

def test_step4_dispatch(exam):
    """Étape 4: Dispatch - Assigner les copies aux correcteurs."""
    print_section("ÉTAPE 4: Dispatch")
    
    # Créer des correcteurs de test si nécessaire
    correctors = list(User.objects.filter(is_staff=True)[:4])
    if len(correctors) < 2:
        print("Création de correcteurs de test...")
        for i in range(len(correctors), 4):
            user, created = User.objects.get_or_create(
                username=f"corrector_{i}",
                defaults={
                    'email': f"corrector_{i}@test.com",
                    'is_staff': True
                }
            )
            if created:
                user.set_password('test123')
                user.save()
            correctors.append(user)
    
    # Assigner les correcteurs à l'examen
    exam.correctors.set(correctors)
    print(f"Correcteurs assignés: {len(correctors)}")
    
    # Simuler le dispatch
    unassigned_copies = list(
        Copy.objects.filter(
            exam=exam,
            assigned_corrector__isnull=True,
            status=Copy.Status.READY
        ).order_by('anonymous_id')
    )
    
    print(f"Copies à dispatcher: {len(unassigned_copies)}")
    
    if not unassigned_copies:
        print("⚠ Aucune copie à dispatcher!")
        return exam
    
    import random
    random.shuffle(unassigned_copies)
    
    distribution = {c.id: 0 for c in correctors}
    
    for i, copy in enumerate(unassigned_copies):
        corrector = correctors[i % len(correctors)]
        copy.assigned_corrector = corrector
        copy.assigned_at = timezone.now()
        copy.save()
        distribution[corrector.id] += 1
    
    print(f"✓ Copies dispatchées: {len(unassigned_copies)}")
    print("Distribution:")
    for corrector in correctors:
        print(f"  - {corrector.username}: {distribution[corrector.id]} copies")
    
    print_stats(exam)
    return exam

def test_step5_verify(exam):
    """Étape 5: Vérification finale."""
    print_section("ÉTAPE 5: Vérification finale")
    
    copies = Copy.objects.filter(exam=exam)
    booklets = Booklet.objects.filter(exam=exam)
    
    # Vérifications
    errors = []
    
    # 1. Pas de copies STAGING restantes
    staging = copies.filter(status=Copy.Status.STAGING).count()
    if staging > 0:
        errors.append(f"❌ {staging} copies STAGING restantes (devraient être 0)")
    else:
        print("✓ Aucune copie STAGING restante")
    
    # 2. Toutes les copies READY sont identifiées
    ready_unidentified = copies.filter(status=Copy.Status.READY, is_identified=False).count()
    if ready_unidentified > 0:
        errors.append(f"❌ {ready_unidentified} copies READY non identifiées")
    else:
        print("✓ Toutes les copies READY sont identifiées")
    
    # 3. Toutes les copies READY sont dispatchées
    ready_not_dispatched = copies.filter(status=Copy.Status.READY, assigned_corrector__isnull=True).count()
    if ready_not_dispatched > 0:
        errors.append(f"❌ {ready_not_dispatched} copies READY non dispatchées")
    else:
        print("✓ Toutes les copies READY sont dispatchées")
    
    # 4. Chaque booklet est dans exactement une copie non-STAGING
    for booklet in booklets:
        non_staging = booklet.assigned_copy.exclude(status=Copy.Status.STAGING).count()
        if non_staging == 0:
            errors.append(f"❌ Booklet {booklet.id} n'est dans aucune copie READY")
        elif non_staging > 1:
            errors.append(f"❌ Booklet {booklet.id} est dans {non_staging} copies (doublon)")
    
    if not any("Booklet" in e for e in errors):
        print("✓ Chaque booklet est dans exactement une copie")
    
    # Résumé
    print_section("RÉSUMÉ")
    print(f"Booklets: {booklets.count()}")
    print(f"Copies READY: {copies.filter(status=Copy.Status.READY).count()}")
    print(f"Copies identifiées: {copies.filter(is_identified=True).count()}")
    print(f"Copies dispatchées: {copies.filter(assigned_corrector__isnull=False).count()}")
    
    if errors:
        print("\n❌ ERREURS DÉTECTÉES:")
        for error in errors:
            print(f"  {error}")
        return False
    else:
        print("\n✓ WORKFLOW COMPLET VALIDÉ!")
        return True

def cleanup_test_data(exam):
    """Nettoie les données de test."""
    print_section("NETTOYAGE")
    
    # Supprimer les copies
    Copy.objects.filter(exam=exam).delete()
    
    # Supprimer les booklets
    Booklet.objects.filter(exam=exam).delete()
    
    # Supprimer l'examen
    exam.delete()
    
    # Supprimer les étudiants de test
    Student.objects.filter(email__startswith='test_student_').delete()
    
    print("✓ Données de test nettoyées")

def main():
    pdf_path = '/home/alaeddine/viatique__PMF/eval_loi_binom_log.pdf'
    
    if not os.path.exists(pdf_path):
        print(f"❌ Fichier non trouvé: {pdf_path}")
        return
    
    print_section("TEST WORKFLOW COMPLET")
    print(f"PDF: {pdf_path}")
    
    exam = None
    try:
        with transaction.atomic():
            exam = test_step1_upload(pdf_path)
            exam = test_step2_stapling(exam)
            exam = test_step3_videocoding(exam)
            exam = test_step4_dispatch(exam)
            success = test_step5_verify(exam)
            
            if not success:
                raise Exception("Workflow validation failed")
            
            # Demander si on veut garder les données
            print("\n" + "="*60)
            print("Test terminé avec succès!")
            print(f"Exam ID: {exam.id}")
            print("Les données de test ont été conservées.")
            print("Pour nettoyer: python manage.py shell")
            print(f"  >>> from exams.models import Exam; Exam.objects.get(id='{exam.id}').delete()")
            
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        if exam:
            print("\nNettoyage des données de test...")
            cleanup_test_data(exam)

if __name__ == '__main__':
    main()
