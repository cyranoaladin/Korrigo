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


def test_pii_hash_gate_detects_synthetic_value_with_invisible_character_without_leaking_it(tmp_path, capsys, monkeypatch):
    spec = importlib.util.spec_from_file_location("check_frontend_pii_hashes", PII_GATE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    synthetic_value = "Synthetic Sentinel"
    synthetic_with_invisible = "Syn\u200bthetic Sentinel"
    marker_hash = module.digest(synthetic_value)
    monkeypatch.setitem(module.DENY_HASHES, marker_hash, "synthetic_test_marker")

    source = tmp_path / "Synthetic.vue"
    source.write_text(f"<template><p>{synthetic_with_invisible}</p></template>", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["check_frontend_pii_hashes.py", str(tmp_path)])

    rc = module.main()
    output = capsys.readouterr().out

    assert rc == 1
    assert "PII_HASH_MATCH_COUNT=1" in output
    assert "synthetic_test_marker" in output
    assert synthetic_value not in output
    assert synthetic_with_invisible not in output
