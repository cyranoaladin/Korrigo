#!/bin/bash
set -e

# This script verifies that the Media Gate is correctly configured in Nginx
# It assumes the docker-compose environment is running.

URL="http://localhost:8080/media/test_gate_check.txt"

echo ">>> VERIFYING MEDIA GATE (NGINX)"

# 1. Direct Access -> MUST BE BLOCKED
echo " [1] Testing Direct Access to /media/..."
CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL")
if [[ "$CODE" == "403" || "$CODE" == "404" ]]; then
    echo "  -> DIRECT ACCESS BLOCKED ($CODE) [PASS]"
else
    echo "  -> DIRECT ACCESS ALLOWED ($CODE) [FAIL]"
    exit 1
fi

echo ">>> MEDIA GATE VERIFIED"
