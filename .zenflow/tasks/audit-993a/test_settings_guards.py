#!/usr/bin/env python3
"""
Direct Settings Guards Validation
Tests production guards by importing settings with different env vars.
"""

import os
import sys
import importlib

# Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def test_guard(name, env_vars, should_fail=True):
    """Test a settings guard with given environment variables"""
    
    # Clear Django settings module from cache
    if 'core.settings' in sys.modules:
        del sys.modules['core.settings']
    if 'django.conf' in sys.modules:
        del sys.modules['django.conf']
    
    # Set environment
    original_env = {}
    for key, value in env_vars.items():
        original_env[key] = os.environ.get(key)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    
    # Try to import settings
    try:
        sys.path.insert(0, 'backend')
        from core import settings
        
        # Success - settings loaded
        if should_fail:
            print(f"{RED}✗{RESET} {name} - Expected error but settings loaded successfully")
            result = False
        else:
            print(f"{GREEN}✓{RESET} {name}")
            result = True
            
    except ValueError as e:
        # ValueError raised (expected for production guards)
        if should_fail:
            print(f"{GREEN}✓{RESET} {name} - Guard triggered: {str(e)[:60]}...")
            result = True
        else:
            print(f"{RED}✗{RESET} {name} - Unexpected error: {str(e)}")
            result = False
            
    except Exception as e:
        # Other exception
        print(f"{RED}✗{RESET} {name} - Unexpected exception: {type(e).__name__}: {str(e)[:60]}")
        result = False
    
    finally:
        # Restore environment
        for key, value in original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        
        # Clean up
        if sys.path and sys.path[0] == 'backend':
            sys.path.pop(0)
    
    return result

def main():
    print("="*70)
    print("PRODUCTION SETTINGS GUARDS VALIDATION")
    print("="*70)
    print()
    
    passed = 0
    failed = 0
    
    # Test 1: SECRET_KEY enforcement
    print("1. SECRET_KEY ENFORCEMENT")
    print("-" * 70)
    
    result = test_guard(
        "SECRET_KEY missing in production → ValueError",
        {'DJANGO_ENV': 'production', 'SECRET_KEY': '', 'DEBUG': 'False', 'ALLOWED_HOSTS': 'example.com'},
        should_fail=True
    )
    if result: passed += 1
    else: failed += 1
    
    result = test_guard(
        "SECRET_KEY provided in production → Success",
        {'DJANGO_ENV': 'production', 'SECRET_KEY': 'test-key-' + 'x'*50, 'DEBUG': 'False', 'ALLOWED_HOSTS': 'example.com'},
        should_fail=False
    )
    if result: passed += 1
    else: failed += 1
    
    result = test_guard(
        "SECRET_KEY missing in development → Fallback (Success)",
        {'DJANGO_ENV': 'development', 'SECRET_KEY': '', 'DEBUG': 'True'},
        should_fail=False
    )
    if result: passed += 1
    else: failed += 1
    
    print()
    
    # Test 2: DEBUG enforcement
    print("2. DEBUG ENFORCEMENT")
    print("-" * 70)
    
    result = test_guard(
        "DEBUG=True in production → ValueError",
        {'DJANGO_ENV': 'production', 'SECRET_KEY': 'test-' + 'x'*50, 'DEBUG': 'True', 'ALLOWED_HOSTS': 'example.com'},
        should_fail=True
    )
    if result: passed += 1
    else: failed += 1
    
    result = test_guard(
        "DEBUG=False in production → Success",
        {'DJANGO_ENV': 'production', 'SECRET_KEY': 'test-' + 'x'*50, 'DEBUG': 'False', 'ALLOWED_HOSTS': 'example.com'},
        should_fail=False
    )
    if result: passed += 1
    else: failed += 1
    
    result = test_guard(
        "DEBUG=True in development → Success",
        {'DJANGO_ENV': 'development', 'DEBUG': 'True'},
        should_fail=False
    )
    if result: passed += 1
    else: failed += 1
    
    print()
    
    # Test 3: ALLOWED_HOSTS validation
    print("3. ALLOWED_HOSTS VALIDATION")
    print("-" * 70)
    
    result = test_guard(
        "ALLOWED_HOSTS='*' in production → ValueError",
        {'DJANGO_ENV': 'production', 'SECRET_KEY': 'test-' + 'x'*50, 'DEBUG': 'False', 'ALLOWED_HOSTS': '*'},
        should_fail=True
    )
    if result: passed += 1
    else: failed += 1
    
    result = test_guard(
        "ALLOWED_HOSTS='*' in development → Success",
        {'DJANGO_ENV': 'development', 'DEBUG': 'True', 'ALLOWED_HOSTS': '*'},
        should_fail=False
    )
    if result: passed += 1
    else: failed += 1
    
    result = test_guard(
        "ALLOWED_HOSTS explicit in production → Success",
        {'DJANGO_ENV': 'production', 'SECRET_KEY': 'test-' + 'x'*50, 'DEBUG': 'False', 'ALLOWED_HOSTS': 'example.com,www.example.com'},
        should_fail=False
    )
    if result: passed += 1
    else: failed += 1
    
    print()
    
    # Test 4: RATELIMIT enforcement
    print("4. RATE LIMITING ENFORCEMENT")
    print("-" * 70)
    
    result = test_guard(
        "RATELIMIT=false in production (no E2E mode) → ValueError",
        {'DJANGO_ENV': 'production', 'SECRET_KEY': 'test-' + 'x'*50, 'DEBUG': 'False', 
         'ALLOWED_HOSTS': 'example.com', 'RATELIMIT_ENABLE': 'false', 'E2E_TEST_MODE': 'false'},
        should_fail=True
    )
    if result: passed += 1
    else: failed += 1
    
    result = test_guard(
        "RATELIMIT=false in production with E2E mode → Success",
        {'DJANGO_ENV': 'production', 'SECRET_KEY': 'test-' + 'x'*50, 'DEBUG': 'False',
         'ALLOWED_HOSTS': 'example.com', 'RATELIMIT_ENABLE': 'false', 'E2E_TEST_MODE': 'true'},
        should_fail=False
    )
    if result: passed += 1
    else: failed += 1
    
    result = test_guard(
        "RATELIMIT=true in production → Success",
        {'DJANGO_ENV': 'production', 'SECRET_KEY': 'test-' + 'x'*50, 'DEBUG': 'False',
         'ALLOWED_HOSTS': 'example.com', 'RATELIMIT_ENABLE': 'true'},
        should_fail=False
    )
    if result: passed += 1
    else: failed += 1
    
    print()
    
    # Summary
    print("="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    print(f"{GREEN}Passed:{RESET} {passed}/12")
    print(f"{RED}Failed:{RESET} {failed}/12")
    print()
    
    if failed == 0:
        print(f"{GREEN}✓ ALL PRODUCTION GUARDS ARE WORKING CORRECTLY{RESET}")
        return 0
    else:
        print(f"{RED}✗ SOME PRODUCTION GUARDS FAILED{RESET}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
