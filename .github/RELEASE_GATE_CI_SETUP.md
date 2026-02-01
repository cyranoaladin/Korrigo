# Release Gate CI Setup

## Overview

The Release Gate workflow (`.github/workflows/release-gate.yml`) runs a complete production-like validation in CI, executing all phases from build to E2E testing with **zero-tolerance** requirements.

## GitHub Secrets (Optional)

The workflow can use GitHub Secrets for production-like security configuration. These are **optional** - if not set, the seed script will generate random passwords.

### Setting Up Secrets

Go to: `Settings > Secrets and variables > Actions > New repository secret`

**Recommended secrets**:

1. **`METRICS_TOKEN`** (optional)
   - **Purpose**: Secure the `/metrics` Prometheus endpoint
   - **Value**: Strong random string (64+ characters)
   - **If not set**: Metrics endpoint will be public (warning logged)
   - **Generate**: `openssl rand -base64 48`

2. **`ADMIN_PASSWORD`** (optional)
   - **Purpose**: Admin user password for seeded data
   - **Value**: Strong password for admin user
   - **If not set**: Seed script generates random password
   - **Generate**: `openssl rand -base64 24`

3. **`TEACHER_PASSWORD`** (optional)
   - **Purpose**: Professor user password for seeded data
   - **Value**: Strong password for prof1 user
   - **If not set**: Seed script generates random password
   - **Generate**: `openssl rand -base64 24`

## Workflow Behavior

### Triggers

- **Pull Requests**: On changes to `backend/`, `infra/`, `scripts/`, or workflow file
- **Push to main**: Validates main branch
- **Manual**: Via GitHub Actions UI (`workflow_dispatch`)

### Phases Executed

1. **Phase 0**: Clean environment
2. **Phase A**: Build (no-cache)
3. **Phase B**: Boot & Stability (0 restarts)
4. **Phase C**: Migrations
5. **Phase D**: Seed (2x idempotent) + pages_images validation
6. **Phase E**: E2E (3 runs with annotations)
7. **Phase F**: Tests (pytest zero-tolerance)
8. **Phase G**: Logs capture
9. **Phase H**: Validation summary

### Zero-Tolerance Criteria

The workflow **FAILS** if any of these occur:

- ❌ Any pytest test fails
- ❌ Any pytest test is skipped
- ❌ Any pytest warning
- ❌ E2E runs != 3/3 passed
- ❌ Annotation POST != 201
- ❌ Any READY copy has pages = 0
- ❌ Build fails
- ❌ Any service unhealthy
- ❌ Any container restarts during validation

### Artifacts

After each run (success or failure), the following artifacts are uploaded:

1. **`release-gate-logs`**: Complete tarball with all 17 log files
2. **`release-gate-critical-logs`**: Individual critical logs:
   - `08_seed_run1.log` - Seed creation with pages validation
   - `12_e2e_3runs.log` - E2E 3 runs complete
   - `13_pytest_full.log` - All pytest results
   - `17_validation_summary.log` - Final summary

**Retention**: 30 days

## Local Testing

Before pushing, test the exact same validation locally:

```bash
# Basic run
./scripts/release_gate_oneshot.sh

# With production-like secrets
METRICS_TOKEN="$(openssl rand -base64 48)" \
ADMIN_PASSWORD="$(openssl rand -base64 24)" \
TEACHER_PASSWORD="$(openssl rand -base64 24)" \
./scripts/release_gate_oneshot.sh
```

Logs will be in `/tmp/release_gate_{timestamp}/`

## Troubleshooting

### Workflow fails at Phase A (Build)

**Cause**: Docker build issues or insufficient resources

**Fix**: Check build logs in artifacts, ensure Docker cache is not corrupted

### Workflow fails at Phase E (E2E)

**Cause**: Annotation API format mismatch or authentication issues

**Fix**:
- Check `12_e2e_3runs.log` in artifacts
- Verify annotation format: `x`, `y`, `w`, `h` (bounding box, not vector path)
- Verify CSRF token handling

### Workflow fails at Phase F (Tests)

**Cause**: Test failures or skipped tests

**Fix**:
- Check `13_pytest_full.log` for details
- If rate limiting tests fail: verify Redis is running
- If tests are skipped: investigate why (zero-tolerance requires 0 skipped)

### "No release_gate_* directory found"

**Cause**: Script failed early before creating log directory

**Fix**: Check GitHub Actions console output for error messages

## CI vs Local Differences

The CI environment differs from local in these ways:

1. **Fresh environment**: No cached data, clean Docker volumes
2. **Ubuntu runner**: May have different resource limits
3. **GitHub network**: Slightly different network configuration
4. **Secrets**: Uses GitHub Secrets instead of local `.env`

The one-shot script is designed to handle these differences automatically.

## Success Criteria

A successful Release Gate run shows:

```
✅ ZERO-TOLERANCE VALIDATION COMPLETE
✅ PASS: 205 tests passed, 0 failed, 0 skipped
✅ PASS: E2E 3/3 runs with annotations (POST 201, GET 200)
✅ PASS: All READY copies have pages > 0
```

## Questions?

See:
- Script documentation: `scripts/RELEASE_GATE_ONESHOT.md`
- Validation report: `/tmp/RELEASE_GATE_ONESHOT_VALIDATION_REPORT.md` (after local run)
- CI run artifacts: GitHub Actions > Workflow run > Artifacts
