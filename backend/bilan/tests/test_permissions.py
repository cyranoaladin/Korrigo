from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from bilan.permissions import IsAdminOrDNBCorrector
from exams.models import Copy, Exam


User = get_user_model()


@pytest.mark.django_db
def test_dnb_corrector_permission_uses_canonical_copy_model():
    teacher_group, _ = Group.objects.get_or_create(name="teacher")
    user = User.objects.create_user(username="dnb_corrector", password="testpass123")
    user.groups.add(teacher_group)
    exam = Exam.objects.create(name="DNB BLANC 2026", date="2026-06-20")
    Copy.objects.create(
        exam=exam,
        anonymous_id="DNB-001",
        assigned_corrector=user,
        status=Copy.Status.READY,
    )

    request = SimpleNamespace(user=user)

    assert IsAdminOrDNBCorrector().has_permission(request, None) is True
