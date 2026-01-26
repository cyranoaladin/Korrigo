# SYNC_ON_NETWORKED_MACHINE.md

**Objective**: Manually synchronize the documentation audit commits to `origin/main`.

1.  **Transfer** `docs_audit_sync.patch` to a machine with internet access and the repository.
2.  **Run** the following commands:

```bash
git checkout main
git pull --ff-only origin main
git am < docs_audit_sync.patch
git push origin main
git log -3 --oneline origin/main    # Verify hashes match patch contents
```

**Validation**:
Push is successful only if the 3 audit commits (Update task, Clean SPEC, Sanitize legacy) appear in `git log origin/main`.
