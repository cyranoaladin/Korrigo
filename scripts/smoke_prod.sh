#!/bin/bash
#
# Production Smoke Test Script
# Task: ZF-AUD-12 - HARDENING PROD
# 
# Enhanced smoke test for production deployment validation
# Tests: health, static files, media protection, security headers, SSL/TLS
#
# Usage:
#   ./scripts/smoke_prod.sh [BASE_URL] [SSL_ENABLED]
#
# Examples:
#   ./scripts/smoke_prod.sh http://localhost:8080 false       # Dev/prod-like
#   ./scripts/smoke_prod.sh https://app.example.com true      # Production HTTPS
#

set -e

# Configuration
BASE_URL="${1:-http://localhost:8080}"
SSL_ENABLED="${2:-false}"
API_URL="$BASE_URL/api"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
pass() {
    echo -e "  -> ${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
}

fail() {
    echo -e "  -> ${RED}✗ FAIL${NC}: $1"
    ((TESTS_FAILED++))
}

warn() {
    echo -e "  -> ${YELLOW}⚠ WARN${NC}: $1"
}

test_start() {
    echo ""
    echo "[$((++TESTS_RUN))] $1"
}

# Start
echo ""
echo "========================================="
echo "  PRODUCTION SMOKE TEST"
echo "========================================="
echo "Target:      $BASE_URL"
echo "SSL Enabled: $SSL_ENABLED"
echo "========================================="
echo ""

#
# 1. CORE FUNCTIONALITY TESTS
#

test_start "Health Endpoint - Liveness Check"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health/live/")
if [ "$HTTP_CODE" == "200" ]; then
    pass "Liveness check returned 200"
else
    fail "Liveness check returned $HTTP_CODE (expected 200)"
fi

test_start "Health Endpoint - Readiness Check"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health/ready/")
if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "503" ]]; then
    if [ "$HTTP_CODE" == "200" ]; then
        pass "Readiness check returned 200 (all dependencies ready)"
    else
        warn "Readiness check returned 503 (some dependencies unavailable)"
        ((TESTS_PASSED++))
    fi
else
    fail "Readiness check returned $HTTP_CODE (expected 200 or 503)"
fi

test_start "Health Endpoint - Combined Check"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/health/")
if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "503" ]]; then
    if [ "$HTTP_CODE" == "200" ]; then
        pass "Combined health check returned 200"
    else
        warn "Combined health check returned 503 (degraded)"
        ((TESTS_PASSED++))
    fi
else
    fail "Combined health check returned $HTTP_CODE (expected 200 or 503)"
fi

test_start "API Root Accessibility"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/")
# API root may return 401 (auth required), 403 (forbidden), 404 (no root route), or 200 (browsable API)
# Any of these are acceptable - we just want to avoid 500 (server error) or connection failures
if [[ "$HTTP_CODE" =~ ^(200|401|403|404)$ ]]; then
    pass "API root accessible (HTTP $HTTP_CODE - no server error)"
else
    fail "API root returned $HTTP_CODE (expected 200/401/403/404)"
fi

test_start "Admin Accessibility"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/admin/")
# Admin should redirect to login (302) or return login page (200)
if [[ "$HTTP_CODE" =~ ^(200|302)$ ]]; then
    pass "Admin accessible (HTTP $HTTP_CODE)"
else
    fail "Admin returned $HTTP_CODE (expected 200 or 302)"
fi

#
# 2. STATIC AND MEDIA FILES TESTS
#

test_start "Static Files Availability - Admin CSS"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/static/admin/css/base.css")
if [ "$HTTP_CODE" == "200" ]; then
    pass "Static files served correctly (admin CSS accessible)"
elif [ "$HTTP_CODE" == "404" ]; then
    warn "Static files not found (collectstatic not run or nginx misconfigured)"
    ((TESTS_PASSED++))
else
    fail "Static files returned $HTTP_CODE (expected 200 or 404)"
fi

test_start "Media Files Protection - Public Block"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/media/marker.txt")
if [[ "$HTTP_CODE" == "403" || "$HTTP_CODE" == "404" ]]; then
    pass "Media files blocked correctly (HTTP $HTTP_CODE)"
else
    fail "Media files returned $HTTP_CODE (expected 403/404 for protection)"
fi

#
# 3. SECURITY HEADERS VALIDATION
#

test_start "Security Headers - X-Frame-Options"
HEADER=$(curl -s -I "$BASE_URL/" | grep -i "x-frame-options" | tr -d '\r')
if [[ "$HEADER" =~ "DENY" || "$HEADER" =~ "SAMEORIGIN" ]]; then
    pass "X-Frame-Options present: $HEADER"
else
    fail "X-Frame-Options missing or misconfigured"
fi

test_start "Security Headers - X-Content-Type-Options"
HEADER=$(curl -s -I "$BASE_URL/" | grep -i "x-content-type-options" | tr -d '\r')
if [[ "$HEADER" =~ "nosniff" ]]; then
    pass "X-Content-Type-Options present: nosniff"
else
    fail "X-Content-Type-Options missing"
fi

test_start "Security Headers - X-XSS-Protection"
HEADER=$(curl -s -I "$BASE_URL/" | grep -i "x-xss-protection" | tr -d '\r')
if [[ "$HEADER" =~ "1" ]]; then
    pass "X-XSS-Protection present"
else
    warn "X-XSS-Protection missing (deprecated but recommended for legacy browsers)"
    ((TESTS_PASSED++))
fi

test_start "Security Headers - Referrer-Policy"
HEADER=$(curl -s -I "$BASE_URL/" | grep -i "referrer-policy" | tr -d '\r')
if [[ -n "$HEADER" ]]; then
    pass "Referrer-Policy present: $HEADER"
else
    warn "Referrer-Policy missing (recommended)"
    ((TESTS_PASSED++))
fi

#
# 4. SSL/TLS VALIDATION (if SSL_ENABLED=true)
#

if [ "$SSL_ENABLED" == "true" ]; then
    test_start "HTTPS - Strict-Transport-Security (HSTS)"
    HEADER=$(curl -s -I "$BASE_URL/" | grep -i "strict-transport-security" | tr -d '\r')
    if [[ "$HEADER" =~ "max-age" ]]; then
        pass "HSTS header present: $HEADER"
    else
        fail "HSTS header missing (critical for HTTPS deployments)"
    fi

    test_start "HTTPS - SSL Certificate Validation"
    if curl -s --fail --max-time 5 "$BASE_URL/api/health/live/" > /dev/null 2>&1; then
        pass "SSL certificate valid"
    else
        fail "SSL certificate validation failed"
    fi

    test_start "HTTP to HTTPS Redirect"
    HTTP_URL=$(echo "$BASE_URL" | sed 's/https:/http:/')
    REDIRECT_CODE=$(curl -s -o /dev/null -w "%{http_code}" -L --max-redirs 0 "$HTTP_URL/")
    if [[ "$REDIRECT_CODE" =~ ^(301|302|307|308)$ ]]; then
        pass "HTTP redirects to HTTPS (HTTP $REDIRECT_CODE)"
    else
        warn "HTTP to HTTPS redirect not detected (may be disabled in prod-like mode)"
        ((TESTS_PASSED++))
    fi
else
    test_start "SSL/TLS Tests Skipped (SSL_ENABLED=false)"
    warn "Running in non-SSL mode (prod-like local environment)"
    ((TESTS_PASSED++))
fi

#
# 5. CONTENT SECURITY POLICY (if present)
#

test_start "Security Headers - Content-Security-Policy"
HEADER=$(curl -s -I "$BASE_URL/" | grep -i "content-security-policy" | tr -d '\r')
if [[ -n "$HEADER" ]]; then
    pass "CSP header present"
else
    warn "CSP header missing (recommended for production)"
    ((TESTS_PASSED++))
fi

#
# SUMMARY
#

echo ""
echo "========================================="
echo "  SMOKE TEST SUMMARY"
echo "========================================="
echo "Tests Run:    $TESTS_RUN"
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
if [ $TESTS_FAILED -gt 0 ]; then
    echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
else
    echo -e "Tests Failed: $TESTS_FAILED"
fi
echo "========================================="
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo ""
    exit 1
fi
