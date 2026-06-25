#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: scripts/release/local_smoke_e2e.sh <audit-dir>" >&2
  exit 2
fi

AUDIT_DIR="$1"
ROOT_DIR="$(git rev-parse --show-toplevel)"
WORK_DIR="$AUDIT_DIR/local_smoke_e2e"
free_port() {
  python3 - <<'PY'
import socket
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind(("127.0.0.1", 0))
    print(s.getsockname()[1])
PY
}

BACKEND_PORT="${KORRIGO_LOCAL_BACKEND_PORT:-$(free_port)}"
FRONTEND_PORT="${KORRIGO_LOCAL_FRONTEND_PORT:-$(free_port)}"
if [ "$BACKEND_PORT" = "$FRONTEND_PORT" ]; then
  FRONTEND_PORT="$(free_port)"
fi
BACKEND_URL="http://127.0.0.1:${BACKEND_PORT}"
FRONTEND_URL="http://127.0.0.1:${FRONTEND_PORT}"
PYTHON_BIN="${KORRIGO_RELEASE_PYTHON:-$ROOT_DIR/.venv-release-check/bin/python}"

if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3)"
fi

mkdir -p "$WORK_DIR"
chmod 700 "$WORK_DIR"
DIAGNOSTIC="$WORK_DIR/E2E_DIAGNOSTIC.md"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  if [ -n "${FRONTEND_PID:-}" ] && kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
    wait "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [ -n "${BACKEND_PID:-}" ] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

wait_http() {
  local url="$1"
  local name="$2"
  local log="$3"
  for _ in $(seq 1 60); do
    if curl -fsS --max-time 3 "$url" >>"$log" 2>&1; then
      echo "${name}=READY" >>"$log"
      return 0
    fi
    sleep 1
  done
  echo "${name}=TIMEOUT" >>"$log"
  return 1
}

request_ok() {
  local url="$1"
  local name="$2"
  local out_file="$WORK_DIR/${name}.headers"
  local code
  code="$(curl -fsS -o /dev/null -D "$out_file" -w "%{http_code}" --max-time 10 "$url")"
  printf "%s_HTTP_STATUS=%s\n" "$name" "$code" | tee -a "$WORK_DIR/smoke_status.txt"
  case "$code" in
    200|204|301|302|304) return 0 ;;
    *) return 1 ;;
  esac
}

echo "E2E_STATUS=STARTING_LOCAL_HTTP_SMOKE" | tee "$WORK_DIR/status.txt"

if [ ! -d "$ROOT_DIR/frontend/dist" ]; then
  echo "E2E_STATUS=NO-GO_E2E_NOT_AVAILABLE" | tee -a "$WORK_DIR/status.txt"
  echo "E2E_REASON=frontend_dist_missing" | tee -a "$WORK_DIR/status.txt"
  exit 1
fi

DB_FILE="$WORK_DIR/e2e.sqlite3"
MEDIA_ROOT="$WORK_DIR/media"
STATIC_ROOT="$WORK_DIR/staticfiles"
mkdir -p "$MEDIA_ROOT" "$STATIC_ROOT"

(
  cd "$ROOT_DIR/backend"
  export DJANGO_ENV=development
  export DEBUG=True
  export ALLOWED_HOSTS="localhost,127.0.0.1"
  export DATABASE_URL="sqlite:///$DB_FILE"
  export MEDIA_ROOT="$MEDIA_ROOT"
  export STATIC_ROOT="$STATIC_ROOT"
  export RATELIMIT_ENABLE=false
  export E2E_TEST_MODE=true
  "$PYTHON_BIN" manage.py migrate --noinput
  if "$PYTHON_BIN" manage.py help seed_e2e >/dev/null 2>&1; then
    "$PYTHON_BIN" manage.py seed_e2e >/dev/null 2>&1
  fi
  "$PYTHON_BIN" manage.py runserver "127.0.0.1:${BACKEND_PORT}"
) >"$WORK_DIR/backend.log" 2>&1 &
BACKEND_PID="$!"

wait_http "${BACKEND_URL}/api/health/" "BACKEND" "$WORK_DIR/backend_wait.log"

cat >"$WORK_DIR/frontend_proxy.py" <<'PY'
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import mimetypes
import os

dist = Path(os.environ["KORRIGO_FRONTEND_DIST"]).resolve()
backend = os.environ["KORRIGO_BACKEND_URL"].rstrip("/")

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        if self.path.startswith("/api/"):
            self.proxy()
            return
        self.serve_static()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self.proxy()
            return
        self.send_response(404)
        self.end_headers()

    def do_HEAD(self):
        if self.path.startswith("/api/"):
            self.proxy(head=True)
            return
        self.serve_static(head=True)

    def proxy(self, head=False):
        target = backend + self.path
        body = None
        if self.command in {"POST", "PUT", "PATCH"}:
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length) if length else b""
        try:
            req = Request(target, data=body, method="HEAD" if head else self.command)
            for key in ("Content-Type", "Cookie", "X-CSRFToken", "X-Requested-With"):
                value = self.headers.get(key)
                if value:
                    req.add_header(key, value)
            with urlopen(req, timeout=10) as resp:
                body = b"" if head else resp.read()
                self.send_response(resp.status)
                for key in resp.headers.keys():
                    if key.lower() in {"transfer-encoding", "connection"}:
                        continue
                    for value in resp.headers.get_all(key, []):
                        self.send_header(key, value)
                self.end_headers()
                if not head:
                    self.wfile.write(body)
        except HTTPError as exc:
            body = b"" if head else exc.read()
            self.send_response(exc.code)
            for key in exc.headers.keys():
                if key.lower() in {"transfer-encoding", "connection"}:
                    continue
                for value in exc.headers.get_all(key, []):
                    self.send_header(key, value)
            self.end_headers()
            if not head:
                self.wfile.write(body)

    def serve_static(self, head=False):
        clean = self.path.split("?", 1)[0].lstrip("/")
        path = (dist / clean).resolve() if clean else dist / "index.html"
        if not str(path).startswith(str(dist)) or not path.exists() or path.is_dir():
            path = dist / "index.html"
        data = b"" if head else path.read_bytes()
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.end_headers()
        if not head:
            self.wfile.write(data)

port = int(os.environ["KORRIGO_FRONTEND_PORT"])
ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
PY

(
  export KORRIGO_FRONTEND_DIST="$ROOT_DIR/frontend/dist"
  export KORRIGO_BACKEND_URL="$BACKEND_URL"
  export KORRIGO_FRONTEND_PORT="$FRONTEND_PORT"
  python "$WORK_DIR/frontend_proxy.py"
) >"$WORK_DIR/frontend_proxy.log" 2>&1 &
FRONTEND_PID="$!"

wait_http "${FRONTEND_URL}/" "FRONTEND" "$WORK_DIR/frontend_wait.log"

{
  echo "# Local E2E diagnostic"
  echo
  echo "- Backend port: $BACKEND_PORT"
  echo "- Frontend port: $FRONTEND_PORT"
  echo "- Backend ready: YES"
  echo "- Frontend ready: YES"
} > "$DIAGNOSTIC"

request_ok "${FRONTEND_URL}/" "ROOT"
request_ok "${FRONTEND_URL}/korrigo" "KORRIGO_ROUTE"
request_ok "${FRONTEND_URL}/student/login" "STUDENT_LOGIN_ROUTE"
request_ok "${FRONTEND_URL}/admin/login" "ADMIN_LOGIN_ROUTE"
request_ok "${FRONTEND_URL}/api/health/" "API_HEALTH"
request_ok "${FRONTEND_URL}/api/csrf/" "API_CSRF"

{
  echo
  echo "## HTTP routes"
  cat "$WORK_DIR/smoke_status.txt"
} >> "$DIAGNOSTIC"

(
  cd "$ROOT_DIR/backend"
  export DJANGO_ENV=development
  export DEBUG=True
  export ALLOWED_HOSTS="localhost,127.0.0.1"
  export DATABASE_URL="sqlite:///$DB_FILE"
  export MEDIA_ROOT="$MEDIA_ROOT"
  export STATIC_ROOT="$STATIC_ROOT"
  export RATELIMIT_ENABLE=false
  export E2E_TEST_MODE=true
  "$PYTHON_BIN" manage.py shell -c '
import os
from django.contrib.auth import get_user_model
from core.auth import UserRole
User = get_user_model()
teacher_name = os.environ.get("E2E_TEACHER_USERNAME", "prof1")
admin_name = os.environ.get("E2E_ADMIN_USERNAME", "admin")
direction_name = os.environ.get("E2E_DIRECTION_USERNAME", "direction_e2e")
teacher = User.objects.filter(username=teacher_name).first()
admin = User.objects.filter(username=admin_name).first()
direction = User.objects.filter(username=direction_name).first()
print("E2E_USER_COUNT=", User.objects.count())
print("E2E_TEACHER_EXISTS=", "YES" if teacher else "NO")
print("E2E_TEACHER_ACTIVE=", "YES" if teacher and teacher.is_active else "NO")
print("E2E_TEACHER_GROUP_TEACHER=", "YES" if teacher and teacher.groups.filter(name=UserRole.TEACHER).exists() else "NO")
print("E2E_ADMIN_EXISTS=", "YES" if admin else "NO")
print("E2E_ADMIN_STAFF=", "YES" if admin and admin.is_staff else "NO")
print("E2E_DIRECTION_EXISTS=", "YES" if direction else "NO")
print("E2E_DIRECTION_ACTIVE=", "YES" if direction and direction.is_active else "NO")
print("E2E_DIRECTION_GROUP_DIRECTION=", "YES" if direction and direction.groups.filter(name="direction_all").exists() else "NO")
'
) > "$WORK_DIR/e2e_user_diagnostic.txt" 2>&1

cat "$WORK_DIR/e2e_user_diagnostic.txt" >> "$DIAGNOSTIC"
if ! grep -q "E2E_TEACHER_EXISTS= YES" "$WORK_DIR/e2e_user_diagnostic.txt" ||
   ! grep -q "E2E_TEACHER_ACTIVE= YES" "$WORK_DIR/e2e_user_diagnostic.txt" ||
   ! grep -q "E2E_TEACHER_GROUP_TEACHER= YES" "$WORK_DIR/e2e_user_diagnostic.txt" ||
   ! grep -q "E2E_DIRECTION_EXISTS= YES" "$WORK_DIR/e2e_user_diagnostic.txt" ||
   ! grep -q "E2E_DIRECTION_ACTIVE= YES" "$WORK_DIR/e2e_user_diagnostic.txt" ||
   ! grep -q "E2E_DIRECTION_GROUP_DIRECTION= YES" "$WORK_DIR/e2e_user_diagnostic.txt"; then
  echo "E2E_STATUS=NO-GO_E2E_SEED_MISSING" | tee -a "$WORK_DIR/status.txt"
  echo "- Decision: NO-GO_E2E_SEED_MISSING" >> "$DIAGNOSTIC"
  exit 1
fi

TEACHER_LOGIN_HTTP_STATUS="$(curl -fsS -o "$WORK_DIR/teacher_login_response.json" -c "$WORK_DIR/teacher_login_cookies.txt" -w "%{http_code}" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${E2E_TEACHER_USERNAME:-prof1}\",\"password\":\"${E2E_TEACHER_PASSWORD:-password}\"}" \
  "${FRONTEND_URL}/api/login/")"
TEACHER_SESSION_COOKIE_COUNT="$(grep -c 'sessionid' "$WORK_DIR/teacher_login_cookies.txt" || true)"
{
  echo
  echo "## Login diagnostic"
  echo "TEACHER_LOGIN_HTTP_STATUS=$TEACHER_LOGIN_HTTP_STATUS"
  echo "TEACHER_SESSION_COOKIE_COUNT=$TEACHER_SESSION_COOKIE_COUNT"
} >> "$DIAGNOSTIC"
if [ "$TEACHER_LOGIN_HTTP_STATUS" != "200" ] || [ "$TEACHER_SESSION_COOKIE_COUNT" -lt 1 ]; then
  echo "E2E_STATUS=NO-GO_E2E_LOGIN_FAILED" | tee -a "$WORK_DIR/status.txt"
  echo "- Decision: NO-GO_E2E_LOGIN_FAILED" >> "$DIAGNOSTIC"
  exit 1
fi

rm -rf "$WORK_DIR/public_assets"
mkdir -p "$WORK_DIR/public_assets"
curl -fsS "${FRONTEND_URL}/" -o "$WORK_DIR/index.html"
python - <<PY
from pathlib import Path
import re
index = Path("$WORK_DIR/index.html").read_text(encoding="utf-8", errors="ignore")
assets = sorted(set(re.findall(r'/(assets/[^"\\']+\\.(?:js|css))', index)))
Path("$WORK_DIR/assets.txt").write_text("\\n".join("/" + a for a in assets), encoding="utf-8")
print(f"LOCAL_PUBLIC_ASSET_COUNT={len(assets)}")
PY
while read -r asset; do
  [ -n "$asset" ] || continue
  curl -fsS "${FRONTEND_URL}${asset}" -o "$WORK_DIR/public_assets/$(basename "$asset")"
done < "$WORK_DIR/assets.txt"

PII_GATE_PEPPER="test-pepper-not-secret" \
  python "$ROOT_DIR/scripts/ci/check_frontend_pii_hashes.py" "$WORK_DIR/public_assets" \
  > "$WORK_DIR/public_asset_pii_gate.log"
cat "$WORK_DIR/public_asset_pii_gate.log"

python - <<PY
from pathlib import Path
import re
email_re = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}")
files = total = 0
for path in Path("$WORK_DIR/public_assets").rglob("*"):
    if path.is_file():
        text = path.read_text(encoding="utf-8", errors="ignore")
        count = len(email_re.findall(text))
        if count:
            files += 1
            total += count
print(f"LOCAL_PUBLIC_ASSETS_EMAIL_FILE_COUNT={files}")
print(f"LOCAL_PUBLIC_ASSETS_EMAIL_TOTAL_COUNT={total}")
raise SystemExit(0 if total == 0 else 1)
PY

if [ -f "$ROOT_DIR/frontend/package.json" ] && grep -q '"test:e2e"' "$ROOT_DIR/frontend/package.json"; then
  {
    echo
    echo "## Playwright"
    echo "Command: npm run test:e2e -- --max-failures=1"
  } >> "$DIAGNOSTIC"
  if (
    cd "$ROOT_DIR/frontend"
    E2E_BASE_URL="$FRONTEND_URL" npm run test:e2e -- --max-failures=1
  ) > "$WORK_DIR/playwright.log" 2>&1; then
    echo "E2E_STATUS=PASS_EXISTING_PLAYWRIGHT_OR_CYPRESS" | tee -a "$WORK_DIR/status.txt"
    echo "PLAYWRIGHT_STATUS=PASS" >> "$DIAGNOSTIC"
  else
    echo "E2E_STATUS=NO-GO_E2E_EXISTING_PLAYWRIGHT_FAILED" | tee -a "$WORK_DIR/status.txt"
    echo "PLAYWRIGHT_STATUS=FAIL" >> "$DIAGNOSTIC"
    python - <<PY >> "$DIAGNOSTIC"
from pathlib import Path
import re
text = Path("$WORK_DIR/playwright.log").read_text(errors="ignore")
text = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}", "<EMAIL>", text)
failed = next((line.strip() for line in text.splitlines() if "✘" in line or "failed" in line.lower()), "not detected")
print(f"FIRST_PLAYWRIGHT_FAILURE={failed}")
PY
    exit 1
  fi
else
  echo "E2E_STATUS=PASS_LOCAL_HTTP_SMOKE" | tee -a "$WORK_DIR/status.txt"
  echo "PLAYWRIGHT_STATUS=NOT_CONFIGURED" >> "$DIAGNOSTIC"
fi

echo "LOCAL_SMOKE_E2E_STATUS=PASS" | tee -a "$WORK_DIR/status.txt"
echo "- Decision: PASS" >> "$DIAGNOSTIC"
