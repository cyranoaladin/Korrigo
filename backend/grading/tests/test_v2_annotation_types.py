"""
Tests for VRAI/FAUX annotation types via the annotation CRUD API.
Covers creation, storage, listing, deletion, audit events, and validation
of all 6 annotation types (COMMENT, HIGHLIGHT, ERROR, BONUS, VRAI, FAUX).
"""
import pytest
import uuid
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from exams.models import Exam, Copy
from grading.models import Annotation, GradingEvent

User = get_user_model()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def exam(db):
    return Exam.objects.create(
        name="Test Exam",
        grading_structure=[
            {"label": "Ex1", "points": 10, "children": [
                {"label": "Q1", "points": 5},
                {"label": "Q2", "points": 5},
            ]}
        ],
    )


@pytest.fixture
def copy_ready(db, exam, teacher_user):
    return Copy.objects.create(
        exam=exam,
        status=Copy.Status.READY,
        assigned_corrector=teacher_user,
        anonymous_id=f"ANON-{uuid.uuid4().hex[:8]}",
    )


def _annotation_payload(ann_type="COMMENT", **overrides):
    """Build a valid annotation payload with sensible defaults."""
    data = {
        "page_index": 0,
        "x": 0.1,
        "y": 0.2,
        "w": 0.15,
        "h": 0.1,
        "type": ann_type,
        "content": f"Annotation of type {ann_type}",
        "score_delta": 0,
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestVraiFauxAnnotationTypes:

    def _list_url(self, copy_id):
        return f"/api/grading/copies/{copy_id}/annotations/"

    def _detail_url(self, ann_id):
        return f"/api/grading/annotations/{ann_id}/"

    # -- VRAI / FAUX creation -----------------------------------------------

    def test_create_vrai_annotation(self, teacher_user, copy_ready):
        """POST with type=VRAI succeeds (201)."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        payload = _annotation_payload("VRAI")
        resp = client.post(self._list_url(copy_ready.id), payload, format="json")
        assert resp.status_code == 201
        assert resp.data["type"] == "VRAI"

    def test_create_faux_annotation(self, teacher_user, copy_ready):
        """POST with type=FAUX succeeds (201)."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        payload = _annotation_payload("FAUX")
        resp = client.post(self._list_url(copy_ready.id), payload, format="json")
        assert resp.status_code == 201
        assert resp.data["type"] == "FAUX"

    # -- DB storage ---------------------------------------------------------

    def test_vrai_annotation_stored_correctly(self, teacher_user, copy_ready):
        """VRAI annotation fields stored correctly in DB."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        payload = _annotation_payload("VRAI", x=0.3, y=0.4)
        resp = client.post(self._list_url(copy_ready.id), payload, format="json")

        ann = Annotation.objects.get(id=resp.data["id"])
        assert ann.type == Annotation.Type.VRAI
        assert ann.x == pytest.approx(0.3)
        assert ann.y == pytest.approx(0.4)
        assert ann.created_by == teacher_user

    def test_faux_annotation_stored_correctly(self, teacher_user, copy_ready):
        """FAUX annotation fields stored correctly in DB."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        payload = _annotation_payload("FAUX", x=0.5, y=0.6)
        resp = client.post(self._list_url(copy_ready.id), payload, format="json")

        ann = Annotation.objects.get(id=resp.data["id"])
        assert ann.type == Annotation.Type.FAUX
        assert ann.x == pytest.approx(0.5)
        assert ann.y == pytest.approx(0.6)

    # -- listing ------------------------------------------------------------

    def test_list_annotations_includes_vrai_faux(self, teacher_user, copy_ready):
        """GET listing returns VRAI and FAUX annotations."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        for t in ("VRAI", "FAUX", "COMMENT"):
            client.post(
                self._list_url(copy_ready.id),
                _annotation_payload(t),
                format="json",
            )

        resp = client.get(self._list_url(copy_ready.id))
        assert resp.status_code == 200
        types = {a["type"] for a in resp.data}
        assert "VRAI" in types
        assert "FAUX" in types
        assert "COMMENT" in types

    # -- deletion -----------------------------------------------------------

    def test_delete_vrai_annotation(self, teacher_user, copy_ready):
        """A VRAI stamp annotation can be deleted."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        resp = client.post(
            self._list_url(copy_ready.id),
            _annotation_payload("VRAI"),
            format="json",
        )
        ann_id = resp.data["id"]

        del_resp = client.delete(self._detail_url(ann_id))
        assert del_resp.status_code == 204
        assert not Annotation.objects.filter(id=ann_id).exists()

    # -- audit event --------------------------------------------------------

    def test_vrai_creates_audit_event(self, teacher_user, copy_ready):
        """Creating a VRAI annotation produces a CREATE_ANN GradingEvent."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        client.post(
            self._list_url(copy_ready.id),
            _annotation_payload("VRAI"),
            format="json",
        )

        event = GradingEvent.objects.filter(
            copy=copy_ready, action=GradingEvent.Action.CREATE_ANN
        ).first()
        assert event is not None
        assert event.actor == teacher_user

    # -- all valid types ----------------------------------------------------

    def test_annotation_types_all_valid(self, teacher_user, copy_ready):
        """All 6 annotation types can be created: COMMENT, HIGHLIGHT, ERROR, BONUS, VRAI, FAUX."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        all_types = ["COMMENT", "HIGHLIGHT", "ERROR", "BONUS", "VRAI", "FAUX"]
        for i, t in enumerate(all_types):
            payload = _annotation_payload(t, y=0.1 * (i + 1))
            resp = client.post(
                self._list_url(copy_ready.id), payload, format="json"
            )
            assert resp.status_code == 201, f"Failed to create annotation type {t}: {resp.data}"

        assert Annotation.objects.filter(copy=copy_ready).count() == 6

    # -- invalid type -------------------------------------------------------

    def test_invalid_annotation_type_rejected(self, teacher_user, copy_ready):
        """An annotation with type='INVALID' is rejected (400)."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        payload = _annotation_payload("INVALID")
        resp = client.post(self._list_url(copy_ready.id), payload, format="json")
        assert resp.status_code == 400
