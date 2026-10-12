from pathlib import Path
import runpy
import shutil

import pytest

from core.tests import _repo_paths


@pytest.mark.parametrize("root_source", ["environment", "mounted_repo"])
def test_rgpd_contract_finds_full_repository_from_backend_only_layout(tmp_path, monkeypatch, root_source):
    source_root = _repo_paths.repo_root_from(__file__)
    mounted_repo = tmp_path / "repo"
    for directory in ("backend", "infra", "scripts/ci"):
        (mounted_repo / directory).mkdir(parents=True)
    shutil.copyfile(
        source_root / "scripts/ci/check_frontend_pii_hashes.py",
        mounted_repo / "scripts/ci/check_frontend_pii_hashes.py",
    )

    app_root = tmp_path / "app"
    contract = app_root / "core/tests/test_lot0_rgpd_deploy_contract.py"
    contract.parent.mkdir(parents=True)
    shutil.copyfile(source_root / "backend/core/tests/test_lot0_rgpd_deploy_contract.py", contract)
    monkeypatch.chdir(app_root)

    if root_source == "environment":
        monkeypatch.setenv("KORRIGO_REPO_ROOT", str(mounted_repo))
    else:
        monkeypatch.delenv("KORRIGO_REPO_ROOT", raising=False)

        # Redirect only the absolute /repo mount so this layout is isolated and
        # reproducible without changing the host or the test container mounts.
        class MountedPath:
            def __new__(cls, value):
                return mounted_repo if value == "/repo" else Path(value)

            cwd = staticmethod(Path.cwd)

        monkeypatch.setattr(_repo_paths, "Path", MountedPath)

    loaded_contract = runpy.run_path(str(contract))

    assert loaded_contract["REPO_ROOT"] == mounted_repo
    assert loaded_contract["PII_GATE"].is_file()
