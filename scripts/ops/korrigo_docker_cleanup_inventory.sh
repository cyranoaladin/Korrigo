#!/usr/bin/env bash
set -euo pipefail

if [ "${1:-}" = "" ]; then
  echo "usage: $0 AUDIT_DIR" >&2
  exit 2
fi

AUDIT_DIR="$1"
mkdir -p "$AUDIT_DIR"
chmod 700 "$AUDIT_DIR"

echo "DRY_RUN_ONLY=YES"
echo "NO_DELETION_PERFORMED=YES"
echo "AUDIT_DIR=$AUDIT_DIR"

docker ps --format "{{.Names}} {{.ID}} {{.Image}} {{.Status}}" \
  > "$AUDIT_DIR/docker_ps_running.txt"

docker ps -a --format "{{.Names}} {{.ID}} {{.Image}} {{.Status}}" \
  > "$AUDIT_DIR/docker_ps_all.txt"

docker images --digests --format "{{.Repository}} {{.Tag}} {{.Digest}} {{.ID}} {{.Size}}" \
  > "$AUDIT_DIR/docker_images.txt"

docker volume ls --format "{{.Name}}" \
  > "$AUDIT_DIR/docker_volumes.txt"

docker ps --format "{{.Image}}" | sort -u \
  > "$AUDIT_DIR/images_used_by_running_containers.txt"

python3 - "$AUDIT_DIR" <<'PY'
from pathlib import Path
import sys

audit = Path(sys.argv[1])
images = []
for line in (audit / "docker_images.txt").read_text(errors="ignore").splitlines():
    parts = line.split()
    if len(parts) < 5:
        continue
    repo, tag, digest, image_id, size = parts[0], parts[1], parts[2], parts[3], parts[4]
    images.append((repo, tag, digest, image_id, size, line))

used = set((audit / "images_used_by_running_containers.txt").read_text(errors="ignore").splitlines())

protected_refs = {
    "korrigo-backend:korrigo-direct-c38a586",
    "korrigo-nginx:korrigo-direct-f793f0c",
    "korrigo-backend:korrigo-direct-f793f0c",
    "korrigo-backend:korrigo-lot0g-direct-1fc58d1",
    "korrigo-nginx:korrigo-lot0g-direct-1fc58d1",
    "postgres:15-alpine",
    "redis:7-alpine",
}

protected_lines = []
candidates = []
for repo, tag, digest, image_id, size, line in images:
    ref = f"{repo}:{tag}"
    is_korrigo = (
        repo.startswith("korrigo-")
        or "korrigo-backend" in repo
        or "korrigo-nginx" in repo
        or "ghcr.io/cyranoaladin/korrigo-" in repo
    )
    if ref in protected_refs or repo in {"postgres", "redis"}:
        protected_lines.append(line)
        continue
    if ref in used or repo in used:
        protected_lines.append(line)
        continue
    if is_korrigo:
        candidates.append(line)

(audit / "protected_images_observed.txt").write_text(
    "\n".join(protected_lines) + ("\n" if protected_lines else ""),
    encoding="utf-8",
)
(audit / "candidate_korrigo_images_dry_run.txt").write_text(
    "\n".join(candidates) + ("\n" if candidates else ""),
    encoding="utf-8",
)

print(f"KORRIGO_IMAGE_CANDIDATE_COUNT={len(candidates)}")
print("CANDIDATE_REPORT=candidate_korrigo_images_dry_run.txt")
print("PROTECTED_REPORT=protected_images_observed.txt")
PY

for volume in docker_postgres_data docker_media_volume docker_backup_volume; do
  if grep -Fxq "$volume" "$AUDIT_DIR/docker_volumes.txt"; then
    echo "PROTECTED_VOLUME_${volume}=PRESENT"
  else
    echo "PROTECTED_VOLUME_${volume}=MISSING"
  fi
done

echo "DRY_RUN_ONLY=YES"
echo "NO_DELETION_PERFORMED=YES"
