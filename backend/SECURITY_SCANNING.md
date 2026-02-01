# Security Scanning Policy - Viatique Backend

## Bandit Static Analysis

### Configuration

Bandit is configured via `.bandit` file in the backend root directory.

**Scan Scope**:
- ✅ **Production code**: `core/`, `grading/`, `exams/`, `students/`, `processing/`
- ✅ **Management commands**: Scanned with strict validation
- ✅ **Test code**: Scanned but false positives suppressed via `# nosec`
- ❌ **Excluded**: migrations, .venv, staticfiles, __pycache__

### CI Gate

**Blocking Severity**: Medium and High
**Non-blocking**: Low (informational only)

The Bandit job in CI will **FAIL** if:
- Any **High** severity issue is detected
- Any **Medium** severity issue is detected

### False Positive Suppression

When Bandit reports a false positive (e.g., test fixture passwords, hardcoded /tmp in tests):

1. **Verify it's truly a false positive** (not a real security issue)
2. **Add targeted suppression** with clear justification:
   ```python
   password="testpass123",  # nosec B106 - Test fixture password, not used in production
   ```
3. **Never suppress globally** - always target specific lines

### Real Security Issues

If Bandit detects a real issue (e.g., hardcoded production password, SQL injection):

1. **Do NOT suppress it** - fix the underlying issue
2. **Use environment variables** for secrets
3. **Use parameterized queries** for SQL
4. **Follow Django security best practices**

### Example: Management Command Passwords

**BAD** (detected by Bandit B105):
```python
admin_pass = 'hardcoded_password'  # ❌ CRITICAL - Exposed in Git
```

**GOOD** (secure):
```python
import os

# Security: Use environment variable
admin_pass = os.environ.get('ADMIN_DEFAULT_PASSWORD', 'CHANGE_ME')

if admin_pass == 'CHANGE_ME':  # nosec B105 - Checking for default, not hardcoding
    print('WARNING: Set ADMIN_DEFAULT_PASSWORD environment variable')
```

### Current Suppressions

All suppressions are documented and justified in the code. See:
- `conftest.py`: Test fixture passwords (B106 - 3x)
- `core/utils/audit.py`: Fallback IP value (B104 - 1x)
- `grading/tests/test_tasks.py`: Test /tmp paths (B108 - 2x)
- `core/management/commands/backup_restore.py`: ORM-controlled SQL (B608 - 2x)
- `core/management/commands/init_pmf.py`: Default value checks (B105 - 2x)

**Total**: 10 targeted suppressions (all with clear justifications)

### Running Locally

```bash
cd backend
source venv/bin/activate

# Full scan with config
bandit -r . -c .bandit -q

# Only Medium/High issues
bandit -r . -c .bandit -ll

# Specific directory
bandit -r core/ -c .bandit
```

### Updating Policy

To modify the Bandit configuration:

1. Edit `backend/.bandit`
2. Test locally with `bandit -r . -c .bandit -q`
3. Verify CI still passes
4. Document changes in this file
5. Never weaken security requirements without review

### References

- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Bandit Plugins](https://bandit.readthedocs.io/en/latest/plugins/index.html)
- [Django Security](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
