from pathlib import Path
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys

import pytest
import yaml
from django.contrib.auth.models import Group, User
from rest_framework.test import APIClient

from core.auth import UserRole


REPO_ROOT = Path(__file__).resolve().parents[3]
DEPLOY_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy.yml"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
LOCAL_SMOKE = REPO_ROOT / "scripts" / "release" / "local_smoke_e2e.sh"
LOCAL_RELEASE = REPO_ROOT / "scripts" / "release" / "local_release_check.sh"
PII_GATE = REPO_ROOT / "scripts" / "ci" / "check_frontend_pii_hashes.py"
PII_HMAC_GENERATOR = REPO_ROOT / "scripts" / "ci" / "generate_pii_hmac_markers.py"
BILAN_BAC_BLANC_VIEW = REPO_ROOT / "frontend" / "src" / "views" / "BilanBacBlanc.vue"
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"
TEST_PII_PEPPER = "test-pepper-not-secret"


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


def test_frontend_known_pii_hmac_gate_passes_with_pepper(capsys, monkeypatch):
    assert PII_GATE.exists()
    spec = importlib.util.spec_from_file_location("check_frontend_pii_hashes", PII_GATE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    monkeypatch.setenv("PII_GATE_PEPPER", TEST_PII_PEPPER)
    monkeypatch.setitem(
        module.DENY_HMACS,
        module.hmac_digest("Synthetic Test Sentinel", TEST_PII_PEPPER),
        "synthetic_test_marker",
    )
    monkeypatch.setattr(sys, "argv", ["check_frontend_pii_hashes.py", str(FRONTEND_SRC)])

    rc = module.main()
    output = capsys.readouterr().out

    assert rc == 0, output
    assert "PII_GATE_STATUS=PASS" in output
    assert "PII_HASH_MATCH_COUNT=0" in output
    assert TEST_PII_PEPPER not in output


def test_frontend_known_pii_hmac_gate_fails_closed_without_markers(tmp_path, capsys, monkeypatch):
    spec = importlib.util.spec_from_file_location("check_frontend_pii_hashes", PII_GATE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    monkeypatch.setenv("PII_GATE_PEPPER", TEST_PII_PEPPER)
    monkeypatch.setattr(module, "DENY_HMACS", {})
    monkeypatch.setattr(sys, "argv", ["check_frontend_pii_hashes.py", str(tmp_path)])

    rc = module.main()
    output = capsys.readouterr().out

    assert rc == 2
    assert "PII_GATE_STATUS=FAIL_MISSING_MARKERS" in output
    assert "PII_HASH_MATCH_COUNT=0" in output
    assert "PII_GATE_STATUS=PASS" not in output
    assert TEST_PII_PEPPER not in output


def test_frontend_known_pii_hmac_gate_fails_closed_without_pepper():
    assert PII_GATE.exists()
    env = os.environ.copy()
    env.pop("PII_GATE_PEPPER", None)
    result = subprocess.run(
        [sys.executable, str(PII_GATE), "frontend/src"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert result.returncode != 0
    assert "PII_GATE_STATUS=FAIL_MISSING_PEPPER" in result.stdout


@pytest.mark.parametrize("pepper", ["inherited-synthetic-sentinel", None])
@pytest.mark.parametrize(
    ("caller", "gate_name", "scan_root"),
    [
        (LOCAL_SMOKE, None, "public_assets"),
        (LOCAL_RELEASE, "hmac_source_gate", "frontend/src"),
        (LOCAL_RELEASE, "hmac_dist_prebuild_gate", "frontend/dist"),
        (LOCAL_RELEASE, "hmac_dist_postbuild_gate", "frontend/dist"),
    ],
    ids=["smoke-assets", "release-source", "release-dist-prebuild", "release-dist-postbuild"],
)
def test_release_pii_gates_preserve_caller_pepper(tmp_path, pepper, caller, gate_name, scan_root):
    lines = caller.read_text().splitlines()
    if gate_name is None:
        gate_line = next(i for i, line in enumerate(lines) if "check_frontend_pii_hashes.py" in line)
        start = gate_line
        while start > 0 and lines[start - 1].rstrip().endswith("\\"):
            start -= 1
        end = gate_line + 1
        while lines[end - 1].rstrip().endswith("\\"):
            end += 1
        command = "\n".join(lines[start:end])
        expected_scan_root = str(tmp_path / scan_root)
    else:
        gate_line = next(line for line in lines if line.strip().startswith(f"run_step {gate_name} "))
        call = shlex.split(gate_line)
        assert call[:4] == ["run_step", gate_name, "bash", "-c"]
        command = call[4]
        expected_scan_root = scan_root

    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    capture = tmp_path / "pii-call.json"
    stub = stub_bin / "python"
    stub.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "Path(os.environ['PII_STUB_CAPTURE']).write_text(json.dumps({"
        "'args': sys.argv[1:], 'pepper': os.environ.get('PII_GATE_PEPPER')}))\n"
    )
    stub.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = str(stub_bin) + os.pathsep + env.get("PATH", "")
    env["ROOT_DIR"] = str(REPO_ROOT)
    env["WORK_DIR"] = str(tmp_path)
    env["PII_STUB_CAPTURE"] = str(capture)
    if pepper is None:
        env.pop("PII_GATE_PEPPER", None)
    else:
        env["PII_GATE_PEPPER"] = pepper
    result = subprocess.run(["bash", "-c", command], cwd=REPO_ROOT, env=env, text=True, capture_output=True, check=False)

    assert result.returncode == 0, result.stderr
    call = json.loads(capture.read_text())
    assert call["pepper"] == pepper
    assert (REPO_ROOT / call["args"][0]).resolve() == PII_GATE
    assert call["args"][1:] == [expected_scan_root]
    assert not result.stdout


def test_frontend_build_pii_gate_scans_dist_with_repository_secret():
    frontend_job = yaml.safe_load(CI_WORKFLOW.read_text())["jobs"]["frontend"]
    steps = frontend_job["steps"]
    build_index = next(i for i, step in enumerate(steps) if step.get("run") == "npm run build")
    gate_steps = [(i, step) for i, step in enumerate(steps) if "check_frontend_pii_hashes.py" in step.get("run", "")]

    assert len(gate_steps) == 1
    gate_index, gate = gate_steps[0]
    assert gate_index > build_index
    assert gate["env"]["PII_GATE_PEPPER"] == "${{ secrets.PII_GATE_PEPPER }}"
    command = shlex.split(gate["run"])
    assert command[0] in {"python", "python3"}
    assert len(command) == 3
    working_directory = REPO_ROOT / frontend_job["defaults"]["run"]["working-directory"]
    assert (working_directory / command[1]).resolve() == PII_GATE
    assert (working_directory / command[2]).resolve() == REPO_ROOT / "frontend" / "dist"


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
def test_pii_hmac_gate_detects_synthetic_variants_without_leaking_value(
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

    monkeypatch.setenv("PII_GATE_PEPPER", TEST_PII_PEPPER)
    marker_hmac = module.hmac_digest(deny_value, TEST_PII_PEPPER)
    monkeypatch.setitem(module.DENY_HMACS, marker_hmac, "synthetic_test_marker")

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


def test_pii_hmac_gate_avoids_synthetic_false_positive(tmp_path, capsys, monkeypatch):
    spec = importlib.util.spec_from_file_location("check_frontend_pii_hashes", PII_GATE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    monkeypatch.setenv("PII_GATE_PEPPER", TEST_PII_PEPPER)
    monkeypatch.setitem(
        module.DENY_HMACS,
        module.hmac_digest("Synthetic Person", TEST_PII_PEPPER),
        "synthetic_test_marker",
    )

    source = tmp_path / "Technical.vue"
    source.write_text("<template><p>Synthetic payload processed successfully.</p></template>", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["check_frontend_pii_hashes.py", str(tmp_path)])

    rc = module.main()
    output = capsys.readouterr().out

    assert rc == 0
    assert "PII_HASH_MATCH_COUNT=0" in output
    assert "Synthetic payload" not in output


def test_pii_hmac_gate_script_contract_has_no_sha_denylist_names():
    text = PII_GATE.read_text()

    assert "DENY_HMACS" in text
    assert "DENY_HASHES" not in text
    assert "def digest(" not in text
    assert "PII_GATE_PEPPER" in text


def test_pii_hmac_generator_uses_stdin_without_leaking_values():
    assert PII_HMAC_GENERATOR.exists()
    env = os.environ.copy()
    env["PII_GATE_PEPPER"] = TEST_PII_PEPPER
    source_value = "Synthetic Person Example"

    result = subprocess.run(
        [sys.executable, str(PII_HMAC_GENERATOR)],
        cwd=REPO_ROOT,
        input=source_value + "\n",
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "DENY_HMACS" in result.stdout
    assert "marker_001" in result.stdout
    assert source_value not in result.stdout + result.stderr
    assert TEST_PII_PEPPER not in result.stdout + result.stderr
