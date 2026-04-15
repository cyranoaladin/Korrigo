import uuid
from pathlib import Path

import pytest
from PIL import Image
from django.conf import settings
from django.utils import timezone

from exams.models import Booklet, Copy, Exam
from grading.models import GradingEvent


def _write_quadrant_image(rel_path: str, colors):
    full_path = Path(settings.MEDIA_ROOT) / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (8, 8), "white")
    pixels = img.load()
    for x in range(8):
        for y in range(8):
            if x < 4 and y < 4:
                pixels[x, y] = colors["tl"]
            elif x >= 4 and y < 4:
                pixels[x, y] = colors["tr"]
            elif x < 4 and y >= 4:
                pixels[x, y] = colors["bl"]
            else:
                pixels[x, y] = colors["br"]
    img.save(full_path)
    return full_path


@pytest.mark.django_db
def test_batch_rotate_last_pages_rotates_only_final_page(authenticated_client):
    exam = Exam.objects.create(name="Rotation Test", date=timezone.now().date())

    copies = []
    codes = ["69CB-010", "69CB-074", "69CB-094"]
    for idx, code in enumerate(codes):
        booklet_a = Booklet.objects.create(
            exam=exam,
            start_page=idx * 4,
            end_page=idx * 4 + 1,
            pages_images=[
                f"exams/{exam.id}/{code}/page_1.png",
                f"exams/{exam.id}/{code}/page_2.png",
            ],
        )
        booklet_b = Booklet.objects.create(
            exam=exam,
            start_page=idx * 4 + 2,
            end_page=idx * 4 + 3,
            pages_images=[
                f"exams/{exam.id}/{code}/page_3.png",
                f"exams/{exam.id}/{code}/page_4.png",
            ],
        )
        _write_quadrant_image(booklet_a.pages_images[0], {
            "tl": (255, 0, 0), "tr": (0, 255, 0), "bl": (0, 0, 255), "br": (255, 255, 0)
        })
        _write_quadrant_image(booklet_a.pages_images[1], {
            "tl": (10, 10, 10), "tr": (20, 20, 20), "bl": (30, 30, 30), "br": (40, 40, 40)
        })
        _write_quadrant_image(booklet_b.pages_images[0], {
            "tl": (50, 0, 0), "tr": (0, 50, 0), "bl": (0, 0, 50), "br": (50, 50, 0)
        })
        last_page_path = _write_quadrant_image(booklet_b.pages_images[1], {
            "tl": (100, 0, 0), "tr": (0, 100, 0), "bl": (0, 0, 100), "br": (200, 200, 0)
        })

        copy = Copy.objects.create(
            exam=exam,
            anonymous_id=code,
            status=Copy.Status.READY,
        )
        copy.booklets.add(booklet_a, booklet_b)
        copies.append((copy, booklet_a, booklet_b, last_page_path))

    response = authenticated_client.post(
        f"/api/exams/{exam.id}/copies/rotate-last-pages/",
        {"anonymous_ids": codes},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["rotated_count"] == 3
    assert response.data["error_count"] == 0
    assert GradingEvent.objects.filter(action=GradingEvent.Action.ROTATE_LAST_PAGE).count() == 3

    for copy, booklet_a, booklet_b, last_page_path in copies:
        copy.refresh_from_db()
        assert copy.status == Copy.Status.READY
        booklet_a.refresh_from_db()
        booklet_b.refresh_from_db()

        assert booklet_a.pages_images[0] == f"exams/{exam.id}/{copy.anonymous_id}/page_1.png"
        assert booklet_a.pages_images[1] == f"exams/{exam.id}/{copy.anonymous_id}/page_2.png"
        assert booklet_b.pages_images[0] == f"exams/{exam.id}/{copy.anonymous_id}/page_3.png"

        rotated_last_path = booklet_b.pages_images[1]
        assert rotated_last_path != str(last_page_path.relative_to(settings.MEDIA_ROOT))
        assert (Path(settings.MEDIA_ROOT) / rotated_last_path).exists()

        with Image.open(last_page_path) as original, Image.open(Path(settings.MEDIA_ROOT) / rotated_last_path) as rotated:
            assert rotated.getpixel((0, 0)) == original.getpixel((7, 7))
            assert rotated.getpixel((7, 0)) == original.getpixel((0, 7))
            assert rotated.getpixel((0, 7)) == original.getpixel((7, 0))
            assert rotated.getpixel((7, 7)) == original.getpixel((0, 0))
