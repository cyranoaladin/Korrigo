"""Seed E2E déterministe et idempotent pour les tests Playwright.

Garantit:
- 1 Copy assignée avec status READY
- 1 Booklet avec pages_images valides
- 1 Image PNG réelle servie via MEDIA_URL
"""
import os
import django
import shutil
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from exams.models import Exam, Copy, Booklet
from grading.models import GradingEvent
from pathlib import Path

User = get_user_model()

# Image dimensions for E2E (A4 ratio ~0.707)
E2E_IMAGE_WIDTH = 1000
E2E_IMAGE_HEIGHT = 1414  # A4 ratio

# Unique tag to identify E2E seed data (reduces collision risk)
E2E_SEED_TAG = "[E2E-SEED]"
E2E_EXAM_PREFIX = f"{E2E_SEED_TAG} Exam"

# Minimum expected PNG sizes (discriminant fail-fast)
# Pillow image ~13KB, fallback 1x1 ~67 bytes
MIN_PNG_SIZE_PILLOW = 5000
MIN_PNG_SIZE_FALLBACK = 60


# Track Pillow availability globally for logging
_PILLOW_AVAILABLE = None


def _check_pillow():
    """Check and log Pillow availability once."""
    global _PILLOW_AVAILABLE
    if _PILLOW_AVAILABLE is None:
        try:
            from PIL import Image  # noqa
            _PILLOW_AVAILABLE = True
            print("  \u2713 Pillow available - using 1000x1414 PNG")
        except ImportError:
            _PILLOW_AVAILABLE = False
            print("  \u26a0 Pillow not available - using 1x1 PNG fallback")
    return _PILLOW_AVAILABLE


def _png_bytes_page():
    """
    G\u00e9n\u00e8re un PNG valide pour les tests E2E.
    
    Utilise Pillow pour une vraie image (1000x1414, ratio A4).
    Fallback sur PNG minimal 1x1 si Pillow non disponible.
    """
    if _check_pillow():
        from PIL import Image, ImageDraw
        import io
        
        # Cr\u00e9er une image blanche de taille raisonnable (ratio A4)
        img = Image.new('RGB', (E2E_IMAGE_WIDTH, E2E_IMAGE_HEIGHT), color='white')
        
        # Ajouter un cadre gris pour visualisation (pas de texte = pas de probl\u00e8me de police)
        draw = ImageDraw.Draw(img)
        draw.rectangle(
            [(10, 10), (E2E_IMAGE_WIDTH - 10, E2E_IMAGE_HEIGHT - 10)],
            outline='lightgray',
            width=2
        )
        # Croix diagonale pour rep\u00e9rage visuel (sans d\u00e9pendance police)
        draw.line([(0, 0), (E2E_IMAGE_WIDTH, E2E_IMAGE_HEIGHT)], fill='lightgray', width=1)
        draw.line([(E2E_IMAGE_WIDTH, 0), (0, E2E_IMAGE_HEIGHT)], fill='lightgray', width=1)
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    else:
        # Fallback: PNG minimal 1x1 pixel transparent
        # WARNING: Certains canvas peuvent ne pas bien g\u00e9rer cette taille minimale
        return (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc`\x00\x00"
            b"\x00\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82"
        )


def ensure_teacher(username="prof1", password="password"):
    """Crée ou récupère un teacher E2E."""
    teachers, _ = Group.objects.get_or_create(name="Teachers")
    u, created = User.objects.get_or_create(
        username=username, 
        defaults={"email": f"{username}@example.com"}
    )
    u.set_password(password)
    u.is_staff = False
    u.is_superuser = False
    u.save()
    u.groups.add(teachers)
    return u


def _save_page_image(page_num: int) -> str:
    """
    Sauvegarde une image PNG dans MEDIA_ROOT et retourne le chemin relatif.
    
    Returns:
        Chemin relatif depuis MEDIA_ROOT (ex: 'e2e/pages/e2e_page_1.png')
    """
    media_root = Path(settings.MEDIA_ROOT)
    e2e_pages_dir = media_root / "e2e" / "pages"
    e2e_pages_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"e2e_page_{page_num}.png"
    filepath = e2e_pages_dir / filename
    
    # Écrire l'image PNG
    png_data = _png_bytes_page()
    filepath.write_bytes(png_data)
    
    # Fail-fast validation: check file was written correctly
    actual_size = filepath.stat().st_size
    pillow = _check_pillow()  # Explicit call, no dependency on global state order
    min_expected = MIN_PNG_SIZE_PILLOW if pillow else MIN_PNG_SIZE_FALLBACK
    if actual_size < min_expected:
        raise RuntimeError(
            f"PNG file suspiciously small: {actual_size} bytes (expected >= {min_expected}). "
            f"Check filesystem/volume permissions."
        )
    
    # Log size for CI debugging
    print(f"    PNG written: {actual_size} bytes (min={min_expected})")
    
    # Retourner le chemin relatif depuis MEDIA_ROOT
    return f"e2e/pages/{filename}"


def _cleanup_e2e_media():
    """
    Nettoie les fichiers media E2E pour une idempotence complète.
    Supprime le dossier e2e/pages/ et son contenu.
    """
    media_root = Path(settings.MEDIA_ROOT)
    e2e_dir = media_root / "e2e"
    
    if e2e_dir.exists():
        shutil.rmtree(e2e_dir)
        print(f"  ✓ Cleaned up E2E media directory: {e2e_dir}")


@transaction.atomic
def main():
    """Seed principal - idempotent et déterministe."""
    teacher = ensure_teacher()

    # Clean up old seed data to ensure fresh state
    # Note: Exam.delete() cascade vers Booklet via FK on_delete=CASCADE
    # Using unique tag to avoid collision with user-created exams
    Exam.objects.filter(name__contains=E2E_SEED_TAG).delete()
    # Supprimer aussi les copies orphelines E2E (cas rare mais possible)
    Copy.objects.filter(anonymous_id="E2E-READY").delete()
    
    # Nettoyer les fichiers media E2E pour éviter accumulation
    _cleanup_e2e_media()
    
    exam = Exam.objects.create(
        name=f"{E2E_EXAM_PREFIX} {timezone.now().strftime('%Y%m%d-%H%M%S')}",
        date=timezone.now().date(),
    )

    # 1. Créer l'image de page AVANT le booklet
    page_image_path = _save_page_image(1)
    print(f"  ✓ Page image created: {page_image_path}")

    # 2. Créer le booklet avec le chemin d'image réel
    booklet = Booklet.objects.create(
        exam=exam,
        start_page=1,
        end_page=1,
        pages_images=[page_image_path]  # Chemin relatif MEDIA_ROOT
    )
    print(f"  ✓ Booklet created: {booklet.id}")

    # 3. Créer la copie READY et lier le booklet
    copy = Copy.objects.create(
        exam=exam,
        anonymous_id="E2E-READY",
        status=Copy.Status.READY,
        is_identified=False
    )
    copy.booklets.add(booklet)
    print(f"  ✓ Copy created: {copy.id} (status={copy.status})")

    # 4. Audit minimal pour la traçabilité
    GradingEvent.objects.get_or_create(
        copy=copy,
        action=GradingEvent.Action.IMPORT if hasattr(GradingEvent.Action, "IMPORT") else "IMPORT",
        defaults={
            "actor": teacher,
            "metadata": {"seed": True, "e2e": True}
        }
    )

    # 5. Trigger Gate 4 Seed (si disponible)
    try:
        from scripts.seed_gate4 import seed_gate4
        seed_gate4()
    except ImportError:
        print("  \u26a0 seed_gate4 not available, skipping")

    # Build expected media URL for CI verification
    media_url = getattr(settings, 'MEDIA_URL', '/media/').rstrip('/')
    full_media_url = f"{media_url}/{page_image_path}"
    
    print("\n\u2705 E2E Seed completed successfully!")
    print(f"  Teacher: {teacher.username}")
    print(f"  Exam: {exam.id}")
    print(f"  Copy: {copy.id} status={copy.status} anon={copy.anonymous_id}")
    print(f"  Booklet: {booklet.id} pages_images={booklet.pages_images}")
    print(f"  Media URL: {full_media_url}")

if __name__ == "__main__":
    main()
