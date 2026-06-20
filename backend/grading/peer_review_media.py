import os

from django.conf import settings


PEER_REVIEW_ANONYMIZED_ROOT = "peer_reviews/anonymized"


def peer_review_anonymized_dir(copy_id):
    return f"{PEER_REVIEW_ANONYMIZED_ROOT}/{copy_id}"


def peer_review_anonymized_page_paths(copy_id):
    relative_dir = peer_review_anonymized_dir(copy_id)
    absolute_dir = os.path.join(settings.MEDIA_ROOT, relative_dir)
    if not os.path.isdir(absolute_dir):
        return []

    names = sorted(
        name for name in os.listdir(absolute_dir)
        if name.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
    )
    return [f"{relative_dir}/{name}" for name in names]


def is_peer_review_anonymized_path_for_copy(file_path, copy_id):
    expected_prefix = f"{peer_review_anonymized_dir(copy_id)}/"
    clean_path = os.path.normpath(file_path)
    return clean_path == file_path and file_path.startswith(expected_prefix)
