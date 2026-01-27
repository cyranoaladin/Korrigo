#!/bin/bash
# Production Environment Validation Script
# Ensures all critical environment variables are set before deployment
# Usage: ./scripts/validate-prod-env.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "Production Environment Validation"
echo "========================================="
echo ""

ERRORS=0
WARNINGS=0

# Function to check required variable
check_required() {
    local var_name=$1
    local var_value="${!var_name}"
    
    if [ -z "$var_value" ]; then
        echo -e "${RED}✗ CRITICAL: $var_name is not set${NC}"
        ((ERRORS++))
        return 1
    else
        echo -e "${GREEN}✓ $var_name is set${NC}"
        return 0
    fi
}

# Function to check insecure defaults
check_not_default() {
    local var_name=$1
    local var_value="${!var_name}"
    local bad_pattern=$2
    
    if [[ "$var_value" == *"$bad_pattern"* ]] || [[ "$var_value" == "$bad_pattern" ]]; then
        echo -e "${RED}✗ CRITICAL: $var_name contains insecure default value${NC}"
        ((ERRORS++))
        return 1
    fi
    return 0
}

echo "1. Critical Secrets"
echo "-------------------"
check_required "SECRET_KEY"
check_not_default "SECRET_KEY" "django-insecure"
check_not_default "SECRET_KEY" "change-it"
check_not_default "SECRET_KEY" "prod-secret"

check_required "DB_PASSWORD"
check_not_default "DB_PASSWORD" "viatique_password"
check_not_default "DB_PASSWORD" "password"

echo ""
echo "2. Database Configuration"
echo "-------------------------"
check_required "DB_NAME"
check_required "DB_USER"
check_required "DB_HOST"

echo ""
echo "3. Django Configuration"
echo "-----------------------"
check_required "DJANGO_ALLOWED_HOSTS"
check_required "DJANGO_ENV"

if [ "${DJANGO_ENV}" != "production" ]; then
    echo -e "${YELLOW}⚠ WARNING: DJANGO_ENV is not 'production' (found: $DJANGO_ENV)${NC}"
    ((WARNINGS++))
fi

if [ "${DEBUG:-False}" = "True" ]; then
    echo -e "${RED}✗ CRITICAL: DEBUG is True in production${NC}"
    ((ERRORS++))
fi

echo ""
echo "4. Security Settings"
echo "--------------------"
if [ "${RATELIMIT_ENABLE:-true}" != "true" ]; then
    echo -e "${RED}✗ CRITICAL: RATELIMIT_ENABLE must be true in production${NC}"
    ((ERRORS++))
else
    echo -e "${GREEN}✓ RATELIMIT_ENABLE is enabled${NC}"
fi

if [ "${SSL_ENABLED:-false}" != "true" ]; then
    echo -e "${YELLOW}⚠ WARNING: SSL_ENABLED is not true${NC}"
    ((WARNINGS++))
fi

echo ""
echo "========================================="
echo "Validation Summary"
echo "========================================="
echo -e "Errors: ${RED}$ERRORS${NC}"
echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
echo ""

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}❌ VALIDATION FAILED - Cannot deploy to production${NC}"
    echo "Please fix all errors before deployment."
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  WARNINGS DETECTED - Review before deployment${NC}"
    exit 0
else
    echo -e "${GREEN}✅ VALIDATION PASSED - Ready for production deployment${NC}"
    exit 0
fi
