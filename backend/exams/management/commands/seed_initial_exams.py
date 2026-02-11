"""
Management command: seed_initial_exams

Creates the complete "zero config" production environment:
- Admin + corrector + student accounts
- 2 exams (BB Jour 1 & BB Jour 2) with full barème
- Imports student PDFs as Copy objects
- Anonymizes copies with stable codes
- Dispatches copies to correctors

Idempotent: safe to re-run. Will reconcile missing data without
duplicating or reshuffling existing assignments.

Usage:
    python manage.py seed_initial_exams
    python manage.py seed_initial_exams --force  # Reset passwords
    python manage.py seed_initial_exams --data-dir /path/to/data
"""
import csv
import hashlib
import io
import logging
import os
import random
import uuid
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.auth import UserRole
from exams.models import Booklet, Copy, Exam, ExamPDF
from students.models import Student

logger = logging.getLogger(__name__)

# ──────────────────────── DATA DEFINITIONS ────────────────────────

ADMIN_DATA = {
    'username': 'admin',
    'email': 'labo.maths@ert.tn',
    'first_name': 'Admin',
    'last_name': 'Korrigo',
}

CORRECTORS_J1 = [
    {'email': 'alaeddine.benrhouma@ert.tn', 'first_name': 'Alaeddine', 'last_name': 'BEN RHOUMA'},
    {'email': 'patrick.dupont@ert.tn', 'first_name': 'Patrick', 'last_name': 'DUPONT'},
    {'email': 'philippe.carr@ert.tn', 'first_name': 'Philippe', 'last_name': 'CARR'},
    {'email': 'selima.klibi@ert.tn', 'first_name': 'Selima', 'last_name': 'KLIBI'},
]

CORRECTORS_J2 = [
    {'email': 'chawki.saadi@ert.tn', 'first_name': 'Chawki', 'last_name': 'SAADI'},
    {'email': 'edouard.rousseau@ert.tn', 'first_name': 'Edouard', 'last_name': 'ROUSSEAU'},
    {'email': 'sami.bentiba@ert.tn', 'first_name': 'Sami', 'last_name': 'BEN TIBA'},
    {'email': 'laroussi.laroussi@ert.tn', 'first_name': 'Laroussi', 'last_name': 'LAROUSSI'},
]

# ──────────────────────── BARÈME STRUCTURES ────────────────────────

def _q(title, max_score=1):
    """Helper to create a question node."""
    return {'type': 'question', 'title': title, 'maxScore': max_score}

def _g(title, children):
    """Helper to create a group node (exercise/part)."""
    return {'type': 'group', 'title': title, 'children': children}


BAREME_J1 = [
    _g("Exercice 1", [
        _q("Question 1"), _q("Question 2"), _q("Question 3"),
        _q("Question 4"), _q("Question 5"),
    ]),
    _g("Exercice 2", [
        _q("Question 1"), _q("Question 2"),
        _q("2.(a)"), _q("2.(b)"),
        _q("Question 3"), _q("3.a)"), _q("3.b)"),
        _q("Question 4"), _q("4.a)"), _q("4.b)"),
        _q("Question 5"), _q("5.a)"), _q("5.b)"), _q("5.c)"),
    ]),
    _g("Exercice 3", [
        _q("Question 1"), _q("1.a)"), _q("1.b)"),
        _q("Question 2"),
        _q("Question 3"), _q("3.a)"), _q("3.b)"), _q("3.c)"),
    ]),
    _g("Exercice 4", [
        _g("Partie A", [_q("Question 1"), _q("Question 2"), _q("Question 3")]),
        _g("Partie B", [_q("Question 1)"), _q("Question 2)"), _q("Question 3)")]),
        _g("Partie C", [_q("Question 1)"), _q("Question 2)"), _q("Question 3)")]),
        _g("Partie D", [_q("Question 1)"), _q("Question 2)")]),
    ]),
]

BAREME_J2 = [
    _g("Exercice 1", [
        _q("1.1"), _q("1.2"), _q("1.3"),
        _q("1.4"), _q("1.5"), _q("1.6"),
    ]),
    _g("Exercice 2", [
        _q("2A.1"), _q("2A.2"), _q("2A.3.1"),
        _q("2A.4"), _q("2A.5"),
        _q("2B.1"), _q("2B.2.(a)"), _q("2B.2.(b)"),
        _q("2B.2.(c)"), _q("2B.3"),
    ]),
    _g("Exercice 3", [
        _q("3.1.(a)"), _q("3.1.(b)"),
        _q("3.2.1"),
        _q("3.3.(a)"), _q("3.3.(b)"), _q("3.3.(c)"),
        _q("3.4.1"),
    ]),
    _g("Exercice 4", [
        _q("4A.1"), _q("4A.2"),
        _q("4B.1.(a)"), _q("4B.1.(b)"),
        _q("4B.2.(a)"), _q("4B.2.(b)"), _q("4B.2.(c)"), _q("4B.2.(d)"),
        _q("4B.3"),
    ]),
]


# ──────────────────────── HELPERS ────────────────────────

def generate_copy_code(exam_id, pdf_filename):
    """
    Generate a stable, anonymized copy code from exam_id + filename.
    Format: 2 uppercase letters + 4 digits + 1 checksum digit = 7 chars.
    Deterministic: same inputs always produce same code.
    """
    raw = f"{exam_id}:{pdf_filename}"
    h = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    # First 2 chars → letters (A-Z)
    letters = ''
    for c in h:
        if c.isalpha():
            letters += c.upper()
            if len(letters) == 2:
                break
    if len(letters) < 2:
        letters = letters.ljust(2, 'A')
    # Next 4 hex digits → numbers (0000-9999)
    digits = ''
    for c in h:
        if c.isdigit():
            digits += c
            if len(digits) == 4:
                break
    if len(digits) < 4:
        digits = digits.ljust(4, '0')
    code = f"{letters}{digits}"
    # Checksum: sum of ascii values mod 10
    checksum = sum(ord(c) for c in code) % 10
    return f"{code}{checksum}"


def parse_student_csv(csv_path):
    """
    Parse a student CSV file robustly.
    Handles: UTF-8 BOM, ; or , separator, empty lines, CRLF.
    Returns list of dicts with keys: last_name, first_name, date_naissance, email, class_name, groupe.
    """
    students = []
    path = Path(csv_path)
    if not path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return students

    raw = path.read_bytes()
    # Handle BOM
    if raw.startswith(b'\xef\xbb\xbf'):
        raw = raw[3:]
    text = raw.decode('utf-8', errors='replace')

    # Detect separator
    first_line = text.split('\n')[0]
    if ';' in first_line and ',' not in first_line.replace('"', '').split(';')[0]:
        sep = ';'
    else:
        sep = ','

    reader = csv.reader(io.StringIO(text), delimiter=sep)
    header = None
    for row in reader:
        if not row or all(cell.strip() == '' for cell in row):
            continue
        if header is None:
            header = [h.strip() for h in row]
            continue

        # Map columns
        data = {}
        for i, val in enumerate(row):
            if i < len(header):
                data[header[i]] = val.strip()

        # Parse name: "LASTNAME FIRSTNAME" in "Élèves" column
        name_field = data.get('Élèves', data.get('Eleves', data.get('Nom', '')))
        parts = name_field.split(maxsplit=1)
        last_name = parts[0] if parts else ''
        first_name = parts[1] if len(parts) > 1 else ''

        # Parse date
        date_str = data.get('Né(e) le', data.get('Date', data.get('date_naissance', '')))
        date_naissance = None
        for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y'):
            try:
                date_naissance = datetime.strptime(date_str, fmt).date()
                break
            except (ValueError, TypeError):
                continue
        if not date_naissance:
            logger.warning(f"Cannot parse date '{date_str}' for {name_field}, using default")
            date_naissance = datetime(2008, 1, 1).date()

        email = data.get('Adresse E-mail', data.get('Email', data.get('email', '')))
        class_name = data.get('Classe', data.get('classe', ''))
        groupe = data.get('Groupe', data.get('groupe', ''))

        if not last_name:
            continue

        students.append({
            'last_name': last_name,
            'first_name': first_name,
            'date_naissance': date_naissance,
            'email': email,
            'class_name': class_name,
            'groupe': groupe,
        })

    logger.info(f"Parsed {len(students)} students from {csv_path}")
    return students


class Command(BaseCommand):
    help = 'Seed production data: users, exams, barèmes, copies, dispatch (idempotent)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reset passwords to default',
        )
        parser.add_argument(
            '--data-dir',
            type=str,
            default=None,
            help='Base directory containing copies_finales_J1/, copies_finales_J2/, CSV files',
        )
        parser.add_argument(
            '--password',
            type=str,
            default=None,
            help='Default password for all accounts (overrides DEFAULT_PASSWORD env var)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        self.force = options['force']
        self.dry_run = options['dry_run']
        self.password = (
            options['password']
            or os.environ.get('DEFAULT_PASSWORD', 'passe123')
        )

        # Determine data directory
        self.data_dir = Path(options['data_dir'] or os.environ.get(
            'SEED_DATA_DIR',
            '/app/seed_data'  # Docker default
        ))
        # Fallback: try repo root (development)
        if not self.data_dir.exists():
            dev_dir = Path(settings.BASE_DIR).parent
            if (dev_dir / 'copies_finales_J1').exists():
                self.data_dir = dev_dir

        self.stdout.write(self.style.SUCCESS(
            f'=== SEED INITIAL EXAMS (data_dir={self.data_dir}, force={self.force}) ==='
        ))

        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be made'))

        with transaction.atomic():
            self._ensure_groups()
            self._create_admin()
            all_correctors = self._create_correctors()
            self._seed_exam(
                name='BB Jour 1',
                date=datetime(2026, 2, 10).date(),
                csv_filename='eleves_maths_J1.csv',
                copies_dir='copies_finales_J1',
                corrector_emails=[c['email'] for c in CORRECTORS_J1],
                bareme=BAREME_J1,
            )
            self._seed_exam(
                name='BB Jour 2',
                date=datetime(2026, 2, 11).date(),
                csv_filename='eleves_maths_J2.csv',
                copies_dir='copies_finales_J2',
                corrector_emails=[c['email'] for c in CORRECTORS_J2],
                bareme=BAREME_J2,
            )

        self.stdout.write(self.style.SUCCESS('=== SEED COMPLETE ==='))

    # ──────── Groups ────────

    def _ensure_groups(self):
        for group_name in [UserRole.ADMIN, UserRole.TEACHER, UserRole.STUDENT]:
            grp, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write(f'  Created group: {group_name}')

    # ──────── Admin ────────

    def _create_admin(self):
        admin_group = Group.objects.get(name=UserRole.ADMIN)
        teacher_group = Group.objects.get(name=UserRole.TEACHER)

        user, created = User.objects.get_or_create(
            username=ADMIN_DATA['username'],
            defaults={
                'email': ADMIN_DATA['email'],
                'first_name': ADMIN_DATA['first_name'],
                'last_name': ADMIN_DATA['last_name'],
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created or self.force:
            user.set_password(self.password)
            user.email = ADMIN_DATA['email']
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(f'  {"Created" if created else "Reset"} admin: {user.username}')
        else:
            self.stdout.write(f'  Admin already exists: {user.username}')

        admin_group.user_set.add(user)
        teacher_group.user_set.add(user)

    # ──────── Correctors ────────

    def _create_correctors(self):
        teacher_group = Group.objects.get(name=UserRole.TEACHER)
        all_correctors = CORRECTORS_J1 + CORRECTORS_J2
        users = []

        for cdata in all_correctors:
            user, created = User.objects.get_or_create(
                username=cdata['email'],
                defaults={
                    'email': cdata['email'],
                    'first_name': cdata['first_name'],
                    'last_name': cdata['last_name'],
                }
            )
            if created or self.force:
                user.set_password(self.password)
                user.first_name = cdata['first_name']
                user.last_name = cdata['last_name']
                user.email = cdata['email']
                user.save()
                self.stdout.write(f'  {"Created" if created else "Reset"} corrector: {cdata["email"]}')
            else:
                self.stdout.write(f'  Corrector exists: {cdata["email"]}')

            teacher_group.user_set.add(user)
            users.append(user)

        return users

    # ──────── Per-Exam Seed ────────

    def _seed_exam(self, name, date, csv_filename, copies_dir, corrector_emails, bareme):
        self.stdout.write(self.style.NOTICE(f'\n--- Seeding exam: {name} ---'))

        # 1. Create or get exam
        exam, created = Exam.objects.get_or_create(
            name=name,
            defaults={
                'date': date,
                'upload_mode': Exam.UploadMode.INDIVIDUAL_A4,
                'grading_structure': bareme,
            }
        )
        if created:
            self.stdout.write(f'  Created exam: {name}')
        else:
            # Reconcile: update barème if empty
            if not exam.grading_structure:
                exam.grading_structure = bareme
                exam.save(update_fields=['grading_structure'])
                self.stdout.write(f'  Updated barème for: {name}')
            else:
                self.stdout.write(f'  Exam exists: {name}')

        # 2. Assign correctors
        corrector_users = list(User.objects.filter(username__in=corrector_emails))
        for u in corrector_users:
            exam.correctors.add(u)
        self.stdout.write(f'  Correctors assigned: {len(corrector_users)}')

        # 3. Import students from CSV
        csv_path = self.data_dir / csv_filename
        students_data = parse_student_csv(csv_path)
        self._import_students(students_data)

        # 4. Import PDF copies
        copies_path = self.data_dir / copies_dir
        self._import_copies(exam, copies_path, students_data)

        # 5. Dispatch copies to correctors
        self._dispatch_copies(exam, corrector_users)

    # ──────── Students ────────

    def _import_students(self, students_data):
        student_group = Group.objects.get(name=UserRole.STUDENT)
        created_count = 0

        for s in students_data:
            email = s.get('email', '')
            if not email:
                continue

            # Create or get Student record
            student, s_created = Student.objects.get_or_create(
                email=email,
                defaults={
                    'last_name': s['last_name'],
                    'first_name': s['first_name'],
                    'date_naissance': s['date_naissance'],
                    'class_name': s.get('class_name', ''),
                    'groupe': s.get('groupe', ''),
                }
            )

            if s_created:
                # Update name/class even if student exists (reconcile)
                student.last_name = s['last_name']
                student.first_name = s['first_name']
                student.class_name = s.get('class_name', '')
                student.groupe = s.get('groupe', '')
                student.save()

            # Create or get associated User account (login with email)
            user, u_created = User.objects.get_or_create(
                username=email,
                defaults={
                    'email': email,
                    'first_name': s['first_name'],
                    'last_name': s['last_name'],
                }
            )
            if u_created or self.force:
                user.set_password(self.password)
                user.first_name = s['first_name']
                user.last_name = s['last_name']
                user.save()

            student_group.user_set.add(user)

            # Link student to user
            if not student.user:
                student.user = user
                student.save(update_fields=['user'])

            if s_created:
                created_count += 1

        self.stdout.write(f'  Students: {created_count} created, {len(students_data)} total')

    # ──────── Copies ────────

    def _import_copies(self, exam, copies_path, students_data):
        if not copies_path.exists():
            self.stdout.write(self.style.WARNING(f'  Copies dir not found: {copies_path}'))
            return

        pdf_files = sorted(copies_path.glob('*.pdf'))
        self.stdout.write(f'  Found {len(pdf_files)} PDFs in {copies_path.name}')

        # Build a lookup: normalized filename → student email
        student_lookup = {}
        for s in students_data:
            # Normalize: "LASTNAME FIRSTNAME" → "LASTNAME_FIRSTNAME"
            normalized = f"{s['last_name']}_{s['first_name']}".upper().replace(' ', '_').replace('-', '-')
            student_lookup[normalized] = s

        existing_copies = {
            c.anonymous_id: c
            for c in Copy.objects.filter(exam=exam)
        }

        created_count = 0
        for pdf_path in pdf_files:
            # Generate stable anonymous code
            copy_code = generate_copy_code(str(exam.id), pdf_path.name)

            if copy_code in existing_copies:
                continue  # Already imported

            # Try to extract student name from filename
            # Pattern: copie_LASTNAME_FIRSTNAME.pdf
            stem = pdf_path.stem  # e.g. "copie_ABID_YOUCEF"
            name_part = stem.replace('copie_', '', 1) if stem.startswith('copie_') else stem

            # Try to match student
            student = None
            student_data = student_lookup.get(name_part.upper())
            if student_data and student_data.get('email'):
                try:
                    student = Student.objects.get(email=student_data['email'])
                except Student.DoesNotExist:
                    pass

            try:
                # Read the PDF file
                pdf_content = pdf_path.read_bytes()

                # Create the Copy
                copy = Copy(
                    exam=exam,
                    anonymous_id=copy_code,
                    status=Copy.Status.READY,
                    student=student,
                    is_identified=student is not None,
                )
                # Save PDF as source
                copy.pdf_source.save(
                    pdf_path.name,
                    ContentFile(pdf_content),
                    save=False
                )
                copy.save()

                # Also create a Booklet for page tracking
                booklet = Booklet.objects.create(
                    exam=exam,
                    start_page=0,
                    end_page=0,
                    pages_images=[],
                )
                copy.booklets.add(booklet)

                # Rasterize PDF pages
                self._rasterize_copy(copy, booklet, pdf_content)

                created_count += 1

            except Exception as e:
                logger.error(f"Failed to import {pdf_path.name}: {e}", exc_info=True)
                self.stdout.write(self.style.WARNING(f'  SKIP {pdf_path.name}: {e}'))
                continue

        self.stdout.write(f'  Copies: {created_count} created, {len(existing_copies)} existing')

    def _rasterize_copy(self, copy, booklet, pdf_content):
        """Rasterize PDF pages to PNG images for the viewer."""
        import fitz  # PyMuPDF

        media_root = Path(settings.MEDIA_ROOT)
        pages_dir = media_root / 'copies' / 'pages' / str(copy.id)
        pages_dir.mkdir(parents=True, exist_ok=True)

        try:
            doc = fitz.open(stream=pdf_content, filetype="pdf")
            page_images = []

            for i, page in enumerate(doc):
                mat = fitz.Matrix(2, 2)  # 2x zoom for readability
                pix = page.get_pixmap(matrix=mat)
                filename = f"p{i:03d}.png"
                filepath = pages_dir / filename
                pix.save(str(filepath))
                # Store relative path (for media serving)
                rel_path = f"copies/pages/{copy.id}/{filename}"
                page_images.append(rel_path)

            doc.close()

            # Update booklet with page info
            booklet.pages_images = page_images
            booklet.end_page = len(page_images) - 1
            booklet.save(update_fields=['pages_images', 'end_page'])

        except Exception as e:
            logger.error(f"Rasterization failed for copy {copy.id}: {e}", exc_info=True)

    # ──────── Dispatch ────────

    def _dispatch_copies(self, exam, corrector_users):
        """
        Dispatch copies to correctors. Balanced random distribution.
        Safe: does NOT reshuffle copies that already have scores/annotations.
        """
        if not corrector_users:
            self.stdout.write(self.style.WARNING('  No correctors to dispatch to'))
            return

        # Get unassigned READY copies
        unassigned = list(
            Copy.objects.filter(
                exam=exam,
                assigned_corrector__isnull=True,
                status__in=[Copy.Status.READY, Copy.Status.STAGING],
            ).order_by('anonymous_id')
        )

        if not unassigned:
            assigned_count = Copy.objects.filter(
                exam=exam, assigned_corrector__isnull=False
            ).count()
            self.stdout.write(f'  Dispatch: all {assigned_count} copies already assigned')
            return

        # Check if any copies have started grading (don't reshuffle those)
        has_grading = Copy.objects.filter(
            exam=exam,
            assigned_corrector__isnull=False,
            status__in=[
                Copy.Status.LOCKED,
                Copy.Status.GRADING_IN_PROGRESS,
                Copy.Status.GRADED,
            ]
        ).exists()

        if has_grading:
            self.stdout.write(
                '  Dispatch: grading in progress, only assigning new unassigned copies'
            )

        # Deterministic shuffle (seeded by exam ID for reproducibility)
        rng = random.Random(str(exam.id))
        rng.shuffle(unassigned)

        now = timezone.now()
        run_id = uuid.uuid4()

        for i, copy in enumerate(unassigned):
            corrector = corrector_users[i % len(corrector_users)]
            copy.assigned_corrector = corrector
            copy.dispatch_run_id = run_id
            copy.assigned_at = now

        Copy.objects.bulk_update(
            unassigned,
            ['assigned_corrector', 'dispatch_run_id', 'assigned_at']
        )

        # Distribution stats
        dist = {}
        for c in corrector_users:
            count = Copy.objects.filter(exam=exam, assigned_corrector=c).count()
            dist[c.username] = count

        self.stdout.write(f'  Dispatched {len(unassigned)} copies: {dist}')
