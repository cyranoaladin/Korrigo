#!/usr/bin/env bash
set -euo pipefail

# =========================
# CONFIG
# =========================
DOMAIN="${DOMAIN:-korrigo.labomaths.tn}"
BASE="https://${DOMAIN}"
API="${BASE}/api"

# credentials
USERNAME="alaeddine.benrhouma@ert.tn"
PASSWORD="passe123"

WORKDIR="${WORKDIR:-/tmp/korrigo_diag_$$}"
mkdir -p "${WORKDIR}"
COOKIEJAR="${WORKDIR}/cookies.txt"
HDR_LOGIN="${WORKDIR}/login_headers.txt"
HDR_ME="${WORKDIR}/me_headers.txt"
BODY_LOGIN="${WORKDIR}/login_body.txt"
BODY_ME="${WORKDIR}/me_body.txt"

echo "============================================================"
echo "KORRIGO 403 DIAG — $(date -Is)"
echo "DOMAIN=${DOMAIN}"
echo "BASE=${BASE}"
echo "WORKDIR=${WORKDIR}"
echo "============================================================"
echo

# =========================
# HELPERS
# =========================
section () { echo; echo "==================== $* ===================="; }
hr () { echo "------------------------------------------------------------"; }

curl_full () {
  local method="$1"; shift
  local url="$1"; shift
  local hdr_out="$1"; shift
  local body_out="$1"; shift
  curl -sk -D "${hdr_out}" -o "${body_out}" -X "${method}" "$@" "${url}"
}

show_cookiejar () {
  section "COOKIEJAR (après login)"
  if [[ -f "${COOKIEJAR}" ]]; then
    grep -v '^\s*#' "${COOKIEJAR}" || true
  else
    echo "Cookie jar absent."
  fi
}

extract_set_cookie () {
  local hdr="$1"
  grep -i '^Set-Cookie:' "${hdr}" || true
}

# =========================
# 1) Basic connectivity / TLS / redirects
# =========================
section "1) TLS / Redirect chain"
echo "▶ HEAD ${BASE}"
curl -skI "${BASE}" | sed -n '1,15p'
hr
echo "▶ HEAD ${API}/me/ (sans cookies)"
curl -skI "${API}/me/" | sed -n '1,25p'

# =========================
# 2) Login with curl: capture Set-Cookie
# =========================
section "2) LOGIN (curl) + capture Set-Cookie"
echo "▶ POST ${API}/login/  (avec jar cookies)"
curl_full "POST" "${API}/login/" "${HDR_LOGIN}" "${BODY_LOGIN}" \
  -c "${COOKIEJAR}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  --data "{\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}"

echo "▶ Status line:"
head -n 1 "${HDR_LOGIN}" || true
hr
echo "▶ Set-Cookie returned by /api/login/:"
extract_set_cookie "${HDR_LOGIN}"
hr
echo "▶ Body (first 300 chars):"
head -c 300 "${BODY_LOGIN}" || true
echo
show_cookiejar

# =========================
# 3) Call /api/me/ using the jar
# =========================
section "3) /api/me/ with cookies jar"
curl_full "GET" "${API}/me/" "${HDR_ME}" "${BODY_ME}" \
  -b "${COOKIEJAR}" \
  -H "Accept: application/json"

echo "▶ Status line:"
head -n 1 "${HDR_ME}" || true
hr
echo "▶ Response headers (first 40 lines):"
sed -n '1,40p' "${HDR_ME}" || true
hr
echo "▶ Body (first 600 chars):"
head -c 600 "${BODY_ME}" || true
echo

# Quick interpretation
section "3bis) Interprétation rapide"
ME_STATUS="$(head -n 1 "${HDR_ME}" | awk '{print $2}' || true)"
if [[ "${ME_STATUS}" == "200" ]]; then
  echo "✅ /api/me/ fonctionne avec curl + cookie jar."
  echo "=> La session fonctionne côté backend. Le problème est navigateur (Secure/SameSite/Domain/Host)."
else
  echo "❌ /api/me/ échoue aussi en curl (status=${ME_STATUS})."
  echo "=> Problème côté backend/proxy (cookie non accepté, host/proto, ou session backend)."
fi

# =========================
# 4) Red flags in Set-Cookie
# =========================
section "4) Red flags in Set-Cookie"
echo "Cherche 'Domain=localhost' / 'Secure' / 'SameSite':"
grep -iE 'Set-Cookie:|domain=|path=|secure|samesite' "${HDR_LOGIN}" || true

# =========================
# 5) Django settings check
# =========================
section "5) Django settings"
docker exec korrigo-backend-1 python -c "
from django.conf import settings
keys = [
  'DEBUG','ALLOWED_HOSTS','CSRF_TRUSTED_ORIGINS',
  'SESSION_COOKIE_SECURE','CSRF_COOKIE_SECURE',
  'SESSION_COOKIE_SAMESITE','CSRF_COOKIE_SAMESITE',
  'SESSION_COOKIE_DOMAIN','CSRF_COOKIE_DOMAIN',
  'SECURE_SSL_REDIRECT','SECURE_PROXY_SSL_HEADER','USE_X_FORWARDED_HOST'
]
for k in keys:
  print(f'{k} = {getattr(settings,k,None)}')
" || true

# =========================
# 6) Conclusion
# =========================
section "6) Conclusion"
echo "Fichiers de sortie:"
echo "  ${HDR_LOGIN}"
echo "  ${BODY_LOGIN}"
echo "  ${COOKIEJAR}"
echo "  ${HDR_ME}"
echo "  ${BODY_ME}"
echo
echo "✅ FIN DIAG."
