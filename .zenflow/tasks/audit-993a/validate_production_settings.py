#!/usr/bin/env python3
"""
Production Settings Validation Script
Tests all production security guards and configuration requirements.
"""

import os
import sys
import subprocess
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

class SettingsValidator:
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
        
    def test(self, name, condition, error_msg=""):
        if condition:
            self.passed.append(name)
            print(f"{GREEN}✓{RESET} {name}")
            return True
        else:
            self.failed.append(name)
            print(f"{RED}✗{RESET} {name}")
            if error_msg:
                print(f"  {error_msg}")
            return False
    
    def warn(self, name, message):
        self.warnings.append((name, message))
        print(f"{YELLOW}⚠{RESET} {name}: {message}")
    
    def report(self):
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)
        print(f"{GREEN}Passed:{RESET} {len(self.passed)}")
        print(f"{RED}Failed:{RESET} {len(self.failed)}")
        print(f"{YELLOW}Warnings:{RESET} {len(self.warnings)}")
        
        if self.failed:
            print(f"\n{RED}FAILED TESTS:{RESET}")
            for test in self.failed:
                print(f"  - {test}")
        
        if self.warnings:
            print(f"\n{YELLOW}WARNINGS:{RESET}")
            for name, msg in self.warnings:
                print(f"  - {name}: {msg}")
        
        return len(self.failed) == 0

def run_django_check(env_vars):
    """Run Django settings validation with given environment variables"""
    env = os.environ.copy()
    env.update(env_vars)
    
    try:
        result = subprocess.run(
            ['python', 'backend/manage.py', 'check', '--deploy'],
            env=env,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)

def main():
    validator = SettingsValidator()
    
    print("="*60)
    print("PRODUCTION SETTINGS VALIDATION")
    print("="*60)
    print()
    
    # Test 1: SECRET_KEY enforcement in production
    print("1. SECRET_KEY ENFORCEMENT")
    print("-" * 60)
    
    # Should FAIL: production without SECRET_KEY
    returncode, stdout, stderr = run_django_check({
        'DJANGO_ENV': 'production',
        'SECRET_KEY': '',
        'DEBUG': 'False',
        'ALLOWED_HOSTS': 'example.com'
    })
    validator.test(
        "SECRET_KEY required in production",
        returncode != 0 and "SECRET_KEY" in stderr,
        "Should raise ValueError when SECRET_KEY missing in production"
    )
    
    # Should PASS: production with SECRET_KEY
    returncode, stdout, stderr = run_django_check({
        'DJANGO_ENV': 'production',
        'SECRET_KEY': 'test-secret-key-for-validation-' + 'x' * 50,
        'DEBUG': 'False',
        'ALLOWED_HOSTS': 'example.com'
    })
    validator.test(
        "SECRET_KEY accepted when provided",
        returncode == 0,
        "Should accept valid SECRET_KEY"
    )
    
    print()
    
    # Test 2: DEBUG enforcement in production
    print("2. DEBUG ENFORCEMENT")
    print("-" * 60)
    
    # Should FAIL: production with DEBUG=True
    returncode, stdout, stderr = run_django_check({
        'DJANGO_ENV': 'production',
        'SECRET_KEY': 'test-secret-key-' + 'x' * 50,
        'DEBUG': 'True',
        'ALLOWED_HOSTS': 'example.com'
    })
    validator.test(
        "DEBUG=True blocked in production",
        returncode != 0 and "DEBUG" in stderr,
        "Should raise ValueError when DEBUG=True in production"
    )
    
    # Should PASS: production with DEBUG=False
    returncode, stdout, stderr = run_django_check({
        'DJANGO_ENV': 'production',
        'SECRET_KEY': 'test-secret-key-' + 'x' * 50,
        'DEBUG': 'False',
        'ALLOWED_HOSTS': 'example.com'
    })
    validator.test(
        "DEBUG=False enforced in production",
        returncode == 0,
        "Should accept DEBUG=False in production"
    )
    
    print()
    
    # Test 3: ALLOWED_HOSTS validation
    print("3. ALLOWED_HOSTS VALIDATION")
    print("-" * 60)
    
    # Should FAIL: production with wildcard
    returncode, stdout, stderr = run_django_check({
        'DJANGO_ENV': 'production',
        'SECRET_KEY': 'test-secret-key-' + 'x' * 50,
        'DEBUG': 'False',
        'ALLOWED_HOSTS': '*'
    })
    validator.test(
        "ALLOWED_HOSTS='*' blocked in production",
        returncode != 0 and "ALLOWED_HOSTS" in stderr,
        "Should raise ValueError when ALLOWED_HOSTS contains '*'"
    )
    
    # Should PASS: production with explicit hosts
    returncode, stdout, stderr = run_django_check({
        'DJANGO_ENV': 'production',
        'SECRET_KEY': 'test-secret-key-' + 'x' * 50,
        'DEBUG': 'False',
        'ALLOWED_HOSTS': 'example.com,www.example.com'
    })
    validator.test(
        "ALLOWED_HOSTS explicit list accepted",
        returncode == 0,
        "Should accept explicit host list"
    )
    
    print()
    
    # Test 4: RATELIMIT enforcement
    print("4. RATE LIMITING ENFORCEMENT")
    print("-" * 60)
    
    # Should FAIL: production with RATELIMIT disabled without E2E mode
    returncode, stdout, stderr = run_django_check({
        'DJANGO_ENV': 'production',
        'SECRET_KEY': 'test-secret-key-' + 'x' * 50,
        'DEBUG': 'False',
        'ALLOWED_HOSTS': 'example.com',
        'RATELIMIT_ENABLE': 'false',
        'E2E_TEST_MODE': 'false'
    })
    validator.test(
        "RATELIMIT cannot be disabled in production",
        returncode != 0 and "RATELIMIT" in stderr,
        "Should raise ValueError when RATELIMIT_ENABLE=false without E2E_TEST_MODE"
    )
    
    # Should PASS: production with RATELIMIT enabled
    returncode, stdout, stderr = run_django_check({
        'DJANGO_ENV': 'production',
        'SECRET_KEY': 'test-secret-key-' + 'x' * 50,
        'DEBUG': 'False',
        'ALLOWED_HOSTS': 'example.com',
        'RATELIMIT_ENABLE': 'true'
    })
    validator.test(
        "RATELIMIT enabled in production",
        returncode == 0,
        "Should accept RATELIMIT_ENABLE=true"
    )
    
    # Should PASS: production with RATELIMIT disabled but E2E_TEST_MODE
    returncode, stdout, stderr = run_django_check({
        'DJANGO_ENV': 'production',
        'SECRET_KEY': 'test-secret-key-' + 'x' * 50,
        'DEBUG': 'False',
        'ALLOWED_HOSTS': 'example.com',
        'RATELIMIT_ENABLE': 'false',
        'E2E_TEST_MODE': 'true'
    })
    validator.test(
        "RATELIMIT can be disabled in E2E_TEST_MODE",
        returncode == 0,
        "Should accept RATELIMIT_ENABLE=false when E2E_TEST_MODE=true"
    )
    
    print()
    
    # Test 5: Development mode validation
    print("5. DEVELOPMENT MODE VALIDATION")
    print("-" * 60)
    
    # Should PASS: development with DEBUG=True
    returncode, stdout, stderr = run_django_check({
        'DJANGO_ENV': 'development',
        'DEBUG': 'True'
    })
    validator.test(
        "Development mode allows DEBUG=True",
        returncode == 0,
        "Should accept DEBUG=True in development"
    )
    
    # Should PASS: development without SECRET_KEY (fallback)
    returncode, stdout, stderr = run_django_check({
        'DJANGO_ENV': 'development',
        'DEBUG': 'True',
        'SECRET_KEY': ''
    })
    validator.test(
        "Development mode has SECRET_KEY fallback",
        returncode == 0,
        "Should use fallback SECRET_KEY in development"
    )
    
    print()
    
    # Test 6: Settings file syntax validation
    print("6. SETTINGS FILE VALIDATION")
    print("-" * 60)
    
    # Check settings.py syntax
    result = subprocess.run(
        ['python', '-m', 'py_compile', 'backend/core/settings.py'],
        capture_output=True,
        text=True
    )
    validator.test(
        "settings.py syntax valid",
        result.returncode == 0,
        "Settings file should have valid Python syntax"
    )
    
    # Check for dangerous patterns
    settings_path = Path('backend/core/settings.py')
    if settings_path.exists():
        content = settings_path.read_text()
        
        # Check no hardcoded secrets
        has_hardcoded_secret = (
            'SECRET_KEY = "' in content and 
            'django-insecure-dev-only' not in content and
            'os.environ.get' not in content.split('SECRET_KEY = "')[0][-50:]
        )
        validator.test(
            "No hardcoded SECRET_KEY",
            not has_hardcoded_secret,
            "SECRET_KEY should come from environment variable"
        )
        
        # Check SSL configuration exists
        validator.test(
            "SSL configuration present",
            'SECURE_SSL_REDIRECT' in content and 'SSL_ENABLED' in content,
            "SSL settings should be configured"
        )
        
        # Check CSP configuration exists
        validator.test(
            "CSP configuration present",
            'CONTENT_SECURITY_POLICY' in content and 'CSPMiddleware' in content,
            "Content Security Policy should be configured"
        )
        
        # Check CORS configuration exists
        validator.test(
            "CORS configuration present",
            'CORS_ALLOWED_ORIGINS' in content and 'corsheaders' in content,
            "CORS should be configured"
        )
        
        # Check logging configuration exists
        validator.test(
            "Logging configuration present",
            'LOGGING' in content and 'audit' in content.lower(),
            "Logging with audit trail should be configured"
        )
        
        # Check REST Framework default permissions
        validator.test(
            "DRF defaults to authenticated",
            'IsAuthenticated' in content and 'DEFAULT_PERMISSION_CLASSES' in content,
            "REST Framework should default to authenticated only"
        )
    
    print()
    
    # Final report
    success = validator.report()
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
