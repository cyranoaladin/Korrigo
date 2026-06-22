from pathlib import Path
import importlib.util
import re
import subprocess
import sys

import pytest
import yaml
from django.contrib.auth.models import Group, User
from rest_framework.test import APIClient

from core.auth import UserRole


REPO_ROOT = Path(__file__).resolve().parents[3]
DEPLOY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
PII_GATE = REPO_ROOT / "scripts" / "ci" / "check_frontend_pii_hashes.py"
BILAN_BAC_BLANC_VIEW = REPO_ROOT / "frontend" / "src" / "views" / "BilanBacBlanc.vue"
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"


@pytest.mark.django_db
def test_me_exposes_server_side_direction_bilan_capability():
    user = User.objects.create_user(username="direction_scope_user", password="pass")
    group, _ = Group.objects.get_or_create(name="direction_lycee")
    user.groups.add(group)

    client = APIClient()
    client.force_authenticate(user)
    response = client.get("/api/me/")

    assert response.status_code == 200
    assert response.data["role"] == "Direction"
    assert response.data["can_view_direction_bilans"] is True
    assert response.data["features"]["can_view_direction_bilans"] is True


@pytest.mark.django_db
def test_me_denies_direction_bilan_capability_for_college_only_scope():
    user = User.objects.create_user(username="direction_college_user", password="pass")
    group, _ = Group.objects.get_or_create(name="direction_college")
    user.groups.add(group)

    client = APIClient()
    client.force_authenticate(user)
    response = client.get("/api/me/")

    assert response.status_code == 200
    assert response.data["role"] == "Direction"
    assert response.data["can_view_direction_bilans"] is False
    assert response.data["features"]["can_view_direction_bilans"] is False


@pytest.mark.django_db
def test_me_exposes_direction_bilan_capability_for_admin_and_teacher_only():
    admin = User.objects.create_user(username="admin_scope_user", password="pass")
    admin_group, _ = Group.objects.get_or_create(name=UserRole.ADMIN)
    admin.groups.add(admin_group)

    teacher = User.objects.create_user(username="teacher_scope_user", password="pass")
    teacher_group, _ = Group.objects.get_or_create(name=UserRole.TEACHER)
    teacher.groups.add(teacher_group)

    staff_only = User.objects.create_user(username="staff_scope_user", password="pass", is_staff=True)

    client = APIClient()
    for user, expected_role, expected_capability in [
        (admin, "Admin", True),
        (teacher, "Teacher", True),
        (staff_only, "Unknown", False),
    ]:
        client.force_authenticate(user)
        response = client.get("/api/me/")

        assert response.status_code == 200
        assert response.data["role"] == expected_role
        assert response.data["can_view_direction_bilans"] is expected_capability
        assert response.data["features"]["can_view_direction_bilans"] is expected_capability


@pytest.mark.django_db
def test_me_rejects_student_accounts_from_teacher_admin_endpoint():
    from students.models import Student

    user = User.objects.create_user(username="student_scope_user", password="pass")
    Student.objects.create(
        user=user,
        last_name="Synthetic",
        first_name="Student",
        class_name="TEST",
        date_naissance="2010-01-01",
    )

    client = APIClient()
    client.force_authenticate(user)
    response = client.get("/api/me/")

    assert response.status_code == 403
    assert "can_view_direction_bilans" not in response.data


def test_deploy_workflow_is_manual_stub_without_prod_mutations():
    workflow = yaml.safe_load(DEPLOY_WORKFLOW.read_text())
    triggers = workflow.get(True) or workflow.get("on") or {}

    assert "push" not in triggers
    assert "pull_request" not in triggers
    assert "schedule" not in triggers
    assert set(triggers) == {"workflow_dispatch"}

    text = DEPLOY_WORKFLOW.read_text()
    forbidden_snippets = [
        "down -v",
        "reset_db",
        "RESET_DB",
        "docker volume",
        "ssh nexus-prod",
        "workflow_run",
        "manage.py migrate",
        "manage.py seed",
        "seed_prod",
        "seed_prod --confirm-production",
        "docker compose --env-file .env -f infra/docker/docker-compose.prod.yml up",
        "docker compose up -d",
    ]
    for snippet in forbidden_snippets:
        assert snippet not in text


def test_frontend_known_pii_hash_gate_passes():
    assert PII_GATE.exists()
    result = subprocess.run(
        [sys.executable, str(PII_GATE), "frontend/src"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PII_HASH_MATCH_COUNT=0" in result.stdout


def test_bilan_bac_blanc_uses_server_capability_without_hardcoded_direction_emails():
    text = BILAN_BAC_BLANC_VIEW.read_text()

    assert "can_view_direction_bilans" in text
    assert "PROVISEUR_PERMS" not in text
    assert "canAccessThisView" not in text
    assert re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text) == []


def test_frontend_src_contains_no_plain_email_addresses():
    email_re = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    matches = []
    for path in FRONTEND_SRC.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if email_re.search(text):
            matches.append(path.relative_to(REPO_ROOT))

    assert matches == []


@pytest.mark.parametrize(
    ("deny_value", "source_value"),
    [
        ("Eleonore Synthetic", "ÉLÉONORE   synthetic"),
        ("Synthetic Sentinel", "Syn\u200bthetic Sentinel"),
        ("Synthetic Sentinel", "Synthetic     Sentinel"),
        ("Synthetic Example", "synthetic example"),
        ("synthetic.person@example.test", "SYNTHETIC.PERSON@example.test"),
    ],
)
def test_pii_hash_gate_detects_synthetic_variants_without_leaking_value(
    tmp_path,
    capsys,
    monkeypatch,
    deny_value,
    source_value,
):
    spec = importlib.util.spec_from_file_location("check_frontend_pii_hashes", PII_GATE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    marker_hash = module.digest(deny_value)
    monkeypatch.setitem(module.DENY_HASHES, marker_hash, "synthetic_test_marker")

    source = tmp_path / "Synthetic.vue"
    source.write_text(f"<template><p>{source_value}</p></template>", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["check_frontend_pii_hashes.py", str(tmp_path)])

    rc = module.main()
    output = capsys.readouterr().out

    assert rc == 1
    assert "PII_HASH_MATCH_COUNT=1" in output
    assert "synthetic_test_marker" in output
    assert deny_value not in output
    assert source_value not in output


def test_pii_hash_gate_avoids_synthetic_false_positive(tmp_path, capsys, monkeypatch):
    spec = importlib.util.spec_from_file_location("check_frontend_pii_hashes", PII_GATE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    monkeypatch.setitem(module.DENY_HASHES, module.digest("Synthetic Person"), "synthetic_test_marker")

    source = tmp_path / "Technical.vue"
    source.write_text("<template><p>Synthetic payload processed successfully.</p></template>", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["check_frontend_pii_hashes.py", str(tmp_path)])

    rc = module.main()
    output = capsys.readouterr().out

    assert rc == 0
    assert "PII_HASH_MATCH_COUNT=0" in output
    assert "Synthetic payload" not in output
