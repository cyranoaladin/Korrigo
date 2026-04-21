import os

import pytest


@pytest.mark.api
def test_protected_media_image_response_disables_cache(settings, teacher_client):
    relative_path = "copies/pages/cache-bust-test.png"
    full_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    with open(full_path, "wb") as handle:
        handle.write(b"fake-png")

    response = teacher_client.get(f"/api/media/{relative_path}")

    assert response.status_code == 200
    assert "no-store" in response["Cache-Control"]
    assert "no-cache" in response["Cache-Control"]
    assert "must-revalidate" in response["Cache-Control"]
    assert "max-age=0" in response["Cache-Control"]
    assert response["Pragma"] == "no-cache"
    assert response["Expires"] == "0"
    assert response["X-Content-Type-Options"] == "nosniff"
