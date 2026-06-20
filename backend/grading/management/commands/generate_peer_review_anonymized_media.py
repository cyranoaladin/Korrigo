from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from grading.models import PeerReviewCorrection
from grading.peer_review_media import peer_review_anonymized_dir


class Command(BaseCommand):
    help = "Generate separate anonymized page images for peer-review corrections."

    def add_arguments(self, parser):
        parser.add_argument("--exam-id", required=True, help="Exam UUID to process.")
        parser.add_argument("--dry-run", action="store_true", help="Only report planned output files.")
        parser.add_argument("--force", action="store_true", help="Overwrite existing anonymized pages.")
        parser.add_argument(
            "--mask-ratio",
            type=float,
            default=0.18,
            help="Top page ratio to mask on each page. Default: 0.18.",
        )

    def handle(self, *args, **options):
        try:
            from PIL import Image, ImageDraw, ImageOps
        except ImportError as exc:
            raise CommandError("Pillow is required to generate anonymized peer-review media.") from exc

        exam_id = options["exam_id"]
        dry_run = options["dry_run"]
        force = options["force"]
        mask_ratio = options["mask_ratio"]
        if mask_ratio <= 0 or mask_ratio >= 0.5:
            raise CommandError("--mask-ratio must be between 0 and 0.5.")

        media_root = Path(settings.MEDIA_ROOT)
        peer_reviews = (
            PeerReviewCorrection.objects
            .filter(exam_id=exam_id)
            .select_related("source_copy", "source_copy__exam")
            .prefetch_related("source_copy__booklets")
            .order_by("source_copy__anonymous_id")
        )
        if not peer_reviews.exists():
            raise CommandError(f"No peer-review corrections found for exam {exam_id}.")

        generated = 0
        skipped = 0
        missing = 0
        copied = 0

        for peer_review in peer_reviews:
            source_copy = peer_review.source_copy
            ppb = source_copy.exam.pages_per_booklet or 4
            page_paths = []
            for booklet in sorted(source_copy.booklets.all(), key=lambda b: b.start_page or 0):
                page_paths.extend(booklet.pages_images or [])

            output_dir = media_root / peer_review_anonymized_dir(source_copy.id)
            if not dry_run:
                output_dir.mkdir(parents=True, exist_ok=True)

            self.stdout.write(f"{source_copy.anonymous_id}: {len(page_paths)} page(s), ppb={ppb}")
            for idx, relative_page in enumerate(page_paths):
                source_path = media_root / relative_page
                output_path = output_dir / f"p{idx:03d}.png"
                if not source_path.is_file():
                    missing += 1
                    self.stdout.write(self.style.WARNING(f"  missing source: {relative_page}"))
                    continue
                if output_path.exists() and not force:
                    skipped += 1
                    self.stdout.write(f"  exists: {output_path.relative_to(media_root)}")
                    continue
                if dry_run:
                    is_header = (idx % ppb) == 0
                    action = "mask" if is_header else "copy"
                    self.stdout.write(f"  would {action}: {output_path.relative_to(media_root)}")
                    continue

                is_header = (idx % ppb) == 0
                with Image.open(source_path) as img:
                    img = ImageOps.exif_transpose(img).convert("RGB")
                    if is_header:
                        draw = ImageDraw.Draw(img)
                        mask_height = max(1, int(img.height * mask_ratio))
                        draw.rectangle((0, 0, img.width, mask_height), fill="white")
                        generated += 1
                        self.stdout.write(f"  masked: {output_path.relative_to(media_root)}")
                    else:
                        copied += 1
                        self.stdout.write(f"  copied: {output_path.relative_to(media_root)}")
                    img.save(output_path, format="PNG", optimize=True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. masked={generated}, copied={copied}, skipped={skipped}, "
                f"missing={missing}, dry_run={dry_run}"
            )
        )
