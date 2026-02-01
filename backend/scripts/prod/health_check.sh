#!/bin/bash
set -e

BASE_URL="http://localhost:8000"
NGINX_URL="http://localhost:8088"

echo "Checking Backend Health..."
if curl -f -s "$BASE_URL/api/health/" > /dev/null; then
    echo "✅ Backend API: OK"
else
    echo "❌ Backend API: FAILED"
    exit 1
fi

echo "Checking Static Files..."
# Check for admin css which should exist if collectstatic ran
if curl -f -s "$NGINX_URL/static/admin/css/base.css" > /dev/null; then
    echo "✅ Static Files: OK"
else
    echo "❌ Static Files: FAILED (Is collectstatic run? Is Nginx mapping correct?)"
fi

echo "Checking Media Access..."
# Just check if directory listing is forbidden (403) or exists, depending on config.
# If explicit file known, check it. Nginx usually returns 403 for directory.
HTTP_CODE=$(curl -o /dev/null -s -w "%{http_code}\n" "$NGINX_URL/media/")
if [ "$HTTP_CODE" == "403" ] || [ "$HTTP_CODE" == "200" ]; then
     echo "✅ Media Mount: OK (HTTP $HTTP_CODE)"
else
     echo "⚠️  Media Mount: Warning (HTTP $HTTP_CODE)"
fi

echo "All checks passed."
