import os
from unittest.mock import MagicMock

import pytest

from exams.models import Booklet, Copy, Exam
from exams.serializers import CopySerializer


@pytest.mark.unit
@pytest.mark.django_db
def test_copy_serializer_exposes_media_version_from_page_files(settings):
    exam = Exam.objects.create(name="Cache Bust Exam", date="2026-04-21")
    copy = Copy.objects.create(exam=exam, anonymous_id="69CB-237")
    booklet = Booklet.objects.create(
        exam=exam,
        start_page=1,
        end_page=1,
        pages_images=["copies/pages/copy_cache_bust_page_001.png"],
    )
    copy.booklets.add(booklet)

    page_path = os.path.join(settings.MEDIA_ROOT, "copies/pages/copy_cache_bust_page_001.png")
    os.makedirs(os.path.dirname(page_path), exist_ok=True)
    with open(page_path, "wb") as handle:
        handle.write(b"page")

    expected_mtime_seconds = 1_713_700_000
    os.utime(page_path, (expected_mtime_seconds, expected_mtime_seconds))

    request = MagicMock()
    request.build_absolute_uri.side_effect = lambda path: f"https://testserver{path}"

    data = CopySerializer(instance=copy, context={"request": request}).data

    assert data["media_version"] == expected_mtime_seconds * 1000
