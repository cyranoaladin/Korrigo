"""The OCR schema must stay in Django's migration graph across deployments."""

from django.db.migrations.loader import MigrationLoader


def test_identification_initial_migration_is_discovered():
    loader = MigrationLoader(None)

    assert "identification" in loader.migrated_apps
    assert ("identification", "0001_initial") in loader.disk_migrations
    state = loader.project_state([("identification", "0001_initial")])
    ocr_result = state.apps.get_model("identification", "OCRResult")
    assert ocr_result._meta.get_field("copy").one_to_one
    assert ocr_result._meta.get_field("suggested_students").many_to_many
