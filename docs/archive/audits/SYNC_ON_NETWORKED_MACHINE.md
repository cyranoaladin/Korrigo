# SYNC_ON_NETWORKED_MACHINE.md

**Objective**: Manually synchronize the documentation audit commits to `origin/main`.

# 0) Sécurité : vérifier repo & remote
git remote -v
git status -sb

# 1) Se caler sur le remote
git checkout main
git fetch origin
git reset --hard origin/main

# 2) Appliquer le patch
git am --3way < docs_audit_sync.patch

# 3) Push
git push origin main

# 4) Preuve distante
git fetch origin
git rev-parse origin/main
git log -10 --oneline --decorate origin/main

---

### Si git am échoue
```bash
git am --abort
git apply --reject --whitespace=fix docs_audit_sync.patch
# puis résolution manuelle + commit + push
```
