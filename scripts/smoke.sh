#!/bin/bash
set -e

BASE_URL="http://localhost:8080"
API_URL="$BASE_URL/api"

echo ">>> SMOKE TEST STARTED"

# 1. Health Check
echo " [1] Checking API Health..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $API_URL/health/)
if [ "$HTTP_CODE" == "200" ]; then
    echo "  -> OK (200)"
else
    echo "  -> FAIL ($HTTP_CODE)"
    exit 1
fi

# 2. Media Gate (Public Block)
echo " [2] Checking Public Media Block..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL/media/marker.txt)
if [[ "$HTTP_CODE" == "403" || "$HTTP_CODE" == "404" ]]; then
    echo "  -> OK ($HTTP_CODE - Blocked)"
else
    echo "  -> FAIL ($HTTP_CODE - Should be 403/404)"
    exit 1
fi

echo ">>> SMOKE TEST PASSED"
exit 0
