"""Security checks must propagate findings without silently allowlisting CVEs."""

import os
import subprocess
from core.tests._repo_paths import repo_root_from


def test_security_audit_gate_preserves_failure_without_suppressions(tmp_path):
    args_file = tmp_path / "audit-args"
    auditor = tmp_path / "pip-audit"
    auditor.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$@" > "$AUDIT_ARGS_FILE"\nexit 7\n'
    )
    auditor.chmod(0o755)
    environment = {
        **os.environ,
        "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
        "AUDIT_ARGS_FILE": str(args_file),
    }

    result = subprocess.run(
        ["bash", str(repo_root_from(__file__) / "backend/scripts/run_pip_audit_gate.sh")],
        cwd=repo_root_from(__file__) / "backend",
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 7, result.stderr
    assert args_file.read_text().splitlines() == ["-r", "requirements.txt"]
