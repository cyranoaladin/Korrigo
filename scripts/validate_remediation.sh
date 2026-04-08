#!/bin/bash
set -euo pipefail

echo "=== Validation post-remédiation Korrigo ==="
echo ""

PASS=0
FAIL=0

check() {
    if eval "$1"; then
        echo "✅ $2"
        PASS=$((PASS + 1))
    else
        echo "❌ $2"
        FAIL=$((FAIL + 1))
    fi
}

# 1. .dockerignore exists
check '[ -f .dockerignore ]' '.dockerignore exists'

# 2. backend/.dockerignore exists
check '[ -f backend/.dockerignore ]' 'backend/.dockerignore exists'

# 3. settings_prod does NOT overwrite LOGGING entirely
check '! grep -q "^LOGGING = {" backend/core/settings_prod.py' 'settings_prod.py does not overwrite LOGGING'

# 4. settings_prod uses copy.deepcopy for LOGGING
check 'grep -q "copy.deepcopy(LOGGING)" backend/core/settings_prod.py' 'settings_prod.py extends LOGGING via deepcopy'

# 5. DB lock_timeout protection in settings_prod
check 'grep -q "lock_timeout" backend/core/settings_prod.py' 'DB lock_timeout protection present'

# 6. CONN_HEALTH_CHECKS in settings_prod
check 'grep -q "CONN_HEALTH_CHECKS" backend/core/settings_prod.py' 'DB CONN_HEALTH_CHECKS present'

# 7. CONN_MAX_AGE aligned to 600
check 'grep -q "DB_CONN_MAX_AGE.*600" backend/core/settings_prod.py' 'CONN_MAX_AGE default is 600'

# 8. Rate limiting on login (already existed)
check 'grep -q "ratelimit" backend/core/views.py' 'Rate limiting on login'

# 9. Rate limiting on password reset (already existed)
check 'grep -q "ratelimit" backend/core/views_password_reset.py' 'Rate limiting on password reset'

# 10. No weak password fallbacks in docker-compose
check '! grep -q "viatique_password" infra/docker/docker-compose.prod.yml' 'No weak fallbacks in docker-compose'

# 11. API docs protected in production
check 'grep -q "ENABLE_API_DOCS" backend/core/urls.py' 'API docs protected in production'

# 12. gunicorn forwarded_allow_ips not hardcoded to 127.0.0.1
check '! grep -q "forwarded_allow_ips.*127.0.0.1" backend/gunicorn_config.py' 'gunicorn forwarded_allow_ips not hardcoded'

# 13. No X-XSS-Protection in nginx (except proxy_hide_header)
check '! grep -q "add_header X-XSS-Protection" infra/nginx/nginx.conf' 'No obsolete X-XSS-Protection header in nginx'

# 14. CSP includes unsafe-inline for style-src
check 'grep -q "unsafe-inline" infra/nginx/nginx.conf' 'CSP style-src includes unsafe-inline'

# 15. No ollama_net external network
check '! grep -q "infra_rag_net" infra/docker/docker-compose.prod.yml' 'No external ollama_net dependency'

# 16. Celery has DEFAULT_PASSWORD
check 'sed -n "/^  celery:/,/^  [a-z]/p" infra/docker/docker-compose.prod.yml | grep -q "DEFAULT_PASSWORD"' 'Celery has DEFAULT_PASSWORD'

# 17. CLEANUP_PROD.md exists
check '[ -f docs/CLEANUP_PROD.md ]' 'docs/CLEANUP_PROD.md exists'

echo ""
echo "=== Results: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] && echo "🎉 All checks passed!" || echo "⚠️  Some checks failed — review above."
exit "$FAIL"
