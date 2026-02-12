import os
import uuid
import fitz  # PyMuPDF
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from exams.models import Exam, Copy, Booklet
from grading.models import Annotation
from grading.services import GradingService, AnnotationService

User = get_user_model()

class Command(BaseCommand):
    help = 'Generate realistic test data (Exams, Copies, PDF, Images) with STRICT robust workflow'

    def add_arguments(self, parser):
        parser.add_argument('--copies', type=int, default=3, help='Number of copies to generate')
        parser.add_argument('--pages', type=int, default=4, help='Number of pages per copy')

    def handle(self, *args, **options):
        num_copies = options['copies']
        num_pages = options['pages']
        
        self.stdout.write("Generating test data...")
        
        # 1. Setup Users
        teacher, _ = User.objects.get_or_create(username="teacher_test")
        teacher.set_password("password123")
        if hasattr(teacher, 'role'): teacher.role = 'Teacher'
        teacher.is_staff = True
        teacher.save()
        
        admin, _ = User.objects.get_or_create(username="admin_test")
        admin.set_password("password123")
        if hasattr(admin, 'role'): admin.role = 'Admin'
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()
        
        self.stdout.write(f"Users ensured: teacher_test / admin_test (password123)")

        # 2. Create Exam
        exam = Exam.objects.create(
            name=f"Robust Exam {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            date=timezone.now().date(),
            is_processed=True
        )
        self.stdout.write(f"Created Exam: {exam.name} ({exam.id})")

        # 3. Generate Copies (Strict Transitions)
        
        # We need at least 1 Staging, 1 Ready, 1 Locked
        # Let's map indices to strict targets
        targets = [Copy.Status.READY, Copy.Status.LOCKED, Copy.Status.STAGING]
        
        for i in range(num_copies):
            target = targets[i % len(targets)]
            copy_uuid = uuid.uuid4()
            
            # --- Base: Create STAGING ---
            copy = Copy.objects.create(
                id=copy_uuid,
                exam=exam,
                anonymous_id=f"ROBUST-{i+1}",
                status=Copy.Status.STAGING 
            )
            
            # PDF & Media
            pdf_bytes = self.generate_pdf(copy_uuid, num_pages)
            copy.pdf_source.save(f"copy_{copy_uuid}.pdf", ContentFile(pdf_bytes), save=True)
            pages_images = self.rasterize_pdf(copy, pdf_bytes)
            
            Booklet.objects.create(
                exam=exam,
                copy=copy,
                start_page=0,
                end_page=num_pages-1,
                pages_images=pages_images,
                student_name_guess=f"Student {i+1}"
            )
            
            # --- Workflow Transitions (No Flipping) ---
            
            images_url_sample = pages_images[0] if pages_images else "N/A"
            
            if target == Copy.Status.STAGING:
                # Done, leave as STAGING
                self.stdout.write(f"  [STAGING] UUID: {copy.id}")
                
            elif target == Copy.Status.READY:
                # Validate -> READY -> Add Annotations
                GradingService.validate_copy(copy, teacher)
                self._add_fixtures_annotations(copy, teacher)
                self.stdout.write(f"  [READY]   UUID: {copy.id}")
                
            elif target == Copy.Status.LOCKED:
                # Validate -> READY -> Add Annotations -> Lock
                # Annotations MUST be added while READY, before Locking.
                GradingService.validate_copy(copy, teacher)
                self._add_fixtures_annotations(copy, teacher)
                GradingService.lock_copy(copy, teacher)
                self.stdout.write(f"  [LOCKED]  UUID: {copy.id}")

            self.stdout.write(f"      Image Sample: {images_url_sample}")


    def _add_fixtures_annotations(self, copy, user):
        """Helper to add annotations to a READY copy"""
        AnnotationService.add_annotation(copy, {
            'page_index': 0,
            'x': 0.1, 'y': 0.1, 'w': 0.2, 'h': 0.1,
            'type': Annotation.Type.COMMENTAIRE,
            'content': "Fixture Annotation Page 0"
        }, user)
        
        AnnotationService.add_annotation(copy, {
            'page_index': 1,
            'x': 0.5, 'y': 0.5, 'w': 0.1, 'h': 0.1,
            'type': Annotation.Type.ERREUR,
            'content': "Fixture Error Page 1"
        }, user)

    def generate_pdf(self, copy_uuid, pages):
        doc = fitz.open()
        for p in range(pages):
            page = doc.new_page()
            page.insert_text((50, 50), f"Copy: {copy_uuid}", fontsize=12)
            page.insert_text((50, 80), f"Page: {p+1}/{pages}", fontsize=20)
            page.insert_text((50, 150), "Strict Workflow Generation...", fontsize=12)
            for line in range(10):
                 page.draw_line((50, 200 + line*20), (500, 200 + line*20))
        return doc.tobytes()

    def rasterize_pdf(self, copy, pdf_bytes):
        doc = fitz.open("pdf", pdf_bytes)
        images = []
        path_rel = f"copies/pages/{copy.id}"
        path_abs = os.path.join(settings.MEDIA_ROOT, path_rel)
        os.makedirs(path_abs, exist_ok=True)
        
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            filename = f"p{i:03d}.png"
            filepath = os.path.join(path_abs, filename)
            pix.save(filepath)
            images.append(f"{path_rel}/{filename}")
            
        return images
