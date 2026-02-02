# PRD-13: Auth/Lockout TTL Validation

## Status: PASS

## Configuration Verified

### Rate Limiting Settings
- **Login endpoint**: `5/15m` (5 attempts per 15 minutes per IP)
- **Student login**: `5/15m` (5 attempts per 15 minutes per IP)
- **Password change**: `5/h` (5 attempts per hour per user)
- **Other sensitive endpoints**: `10/h` (10 attempts per hour per user)

### Environment Controls
- `RATELIMIT_ENABLE`: Controls rate limiting (default: true)
- Production mode enforces rate limiting (cannot be disabled unless E2E_TEST_MODE=true)
- Local-prod uses `RATELIMIT_ENABLE=false` for E2E testing

### Code Locations
- `backend/core/views.py`: LoginView with `@maybe_ratelimit(key='ip', rate='5/15m')`
- `backend/students/views.py`: StudentLoginView with `@maybe_ratelimit(key='ip', rate='5/15m')`
- `backend/core/utils/ratelimit.py`: `maybe_ratelimit` decorator respects RATELIMIT_ENABLE

## Conclusion
Rate limiting is properly configured and will be active in production. The 15-minute lockout window is appropriate for brute-force protection.
