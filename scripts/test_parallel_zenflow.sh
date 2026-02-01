#!/usr/bin/env bash
#
# test_parallel_zenflow.sh - Zenflow-aware test wrapper
#
# This script automatically detects Zenflow task context and sources
# task-specific environment variables to ensure test isolation.
#
# Features:
# - Auto-detect ZENFLOW_TASK_ID from environment
# - Load task-specific .env.task if available
# - Run pytest with appropriate worker count
# - Support both CI and local environments
#
# Usage:
#   ./scripts/test_parallel_zenflow.sh [pytest-args...]
#
# Examples:
#   ./scripts/test_parallel_zenflow.sh -n 4 -m api
#   ./scripts/test_parallel_zenflow.sh --verbose
#   ZENFLOW_TASK_ID=my-task-123 ./scripts/test_parallel_zenflow.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[Zenflow Test]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[Zenflow Test]${NC} $*"
}

log_error() {
    echo -e "${RED}[Zenflow Test]${NC} $*"
}

# Detect Zenflow context
if [[ -n "${ZENFLOW_TASK_ID:-}" ]]; then
    log_info "Zenflow task detected: ${ZENFLOW_TASK_ID}"
    
    # Construct path to task-specific .env.task
    TASK_ENV_FILE=".zenflow/tasks/${ZENFLOW_TASK_ID}/.env.task"
    
    if [[ -f "$TASK_ENV_FILE" ]]; then
        log_info "Loading task-specific environment from: ${TASK_ENV_FILE}"
        # Export variables from .env.task
        set -a
        source "$TASK_ENV_FILE"
        set +a
        
        # Display loaded configuration
        log_info "Port Configuration:"
        echo "  POSTGRES_PORT:  ${POSTGRES_PORT:-<not set>}"
        echo "  REDIS_PORT:     ${REDIS_PORT:-<not set>}"
        echo "  BACKEND_PORT:   ${BACKEND_PORT:-<not set>}"
        echo "  FRONTEND_PORT:  ${FRONTEND_PORT:-<not set>}"
    else
        log_warn "Task env file not found: ${TASK_ENV_FILE}"
        log_warn "Using default port configuration"
    fi
else
    log_info "Not running in Zenflow context (ZENFLOW_TASK_ID not set)"
    log_info "Using default port configuration"
fi

# Determine pytest worker count
PYTEST_WORKERS="${PYTEST_WORKERS:-auto}"
log_info "Pytest workers: ${PYTEST_WORKERS}"

# Change to backend directory if it exists
if [[ -d "backend" ]]; then
    log_info "Changing to backend directory"
    cd backend
fi

# Run pytest with isolation
log_info "Running pytest with parallel workers..."
log_info "Command: pytest -n ${PYTEST_WORKERS} $*"

# Execute pytest
if pytest -n "$PYTEST_WORKERS" "$@"; then
    log_info "Tests passed successfully ✓"
    exit 0
else
    log_error "Tests failed ✗"
    exit 1
fi
