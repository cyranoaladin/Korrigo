import os
import subprocess

import pytest

from core import tasks


def test_backup_log_redaction_masks_email_addresses():
    message = "pg_dump failed for student alice@example.test and admin root@labomaths.tn"

    redacted = tasks.redact_backup_log_message(message)

    assert "alice@example.test" not in redacted
    assert "root@labomaths.tn" not in redacted
    assert redacted.count("<redacted-email>") == 2


def test_backup_gpg_passphrase_is_required_when_enforced(monkeypatch):
    monkeypatch.setenv("REQUIRE_BACKUP_GPG", "true")
    monkeypatch.delenv("BACKUP_GPG_PASSPHRASE", raising=False)

    with pytest.raises(RuntimeError, match="BACKUP_GPG_PASSPHRASE"):
        tasks.get_required_backup_gpg_passphrase()


def test_encrypt_backup_artifact_removes_plaintext(tmp_path, monkeypatch):
    plaintext = tmp_path / "korrigo_db_20260620_180000.dump"
    plaintext.write_bytes(b"plain backup bytes")

    def fake_run(cmd, input, stdout, stderr, check):
        output_path = cmd[cmd.index("-o") + 1]
        with open(output_path, "wb") as output:
            output.write(b"encrypted backup bytes")
        assert input == b"test-passphrase"
        assert stdout == subprocess.DEVNULL
        assert stderr == subprocess.PIPE
        assert check is True
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(tasks.subprocess, "run", fake_run)

    encrypted = tasks.encrypt_backup_artifact(
        plaintext,
        passphrase="test-passphrase",
        label="database dump",
    )

    assert encrypted == plaintext.with_suffix(plaintext.suffix + ".gpg")
    assert encrypted.read_bytes() == b"encrypted backup bytes"
    assert not plaintext.exists()
