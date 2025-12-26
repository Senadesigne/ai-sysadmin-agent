"""
Production safety guard tests for DEV_ADMIN_BYPASS.

Tests verify that the application hard-fails if DEV_ADMIN_BYPASS is enabled
in production mode (AUTH_MODE=prod).

Uses subprocess to test in isolated environment (avoids .env file interference).
"""

import pytest
import subprocess
import sys
from pathlib import Path


def test_prod_mode_with_bypass_raises():
    """
    CRITICAL TEST: Application must raise RuntimeError if DEV_ADMIN_BYPASS=1
    and AUTH_MODE=prod at startup.
    """
    # Test script that tries to import settings with prod + bypass
    test_script = """
import os
os.environ['AUTH_MODE'] = 'prod'
os.environ['DEV_ADMIN_BYPASS'] = '1'
# Prevent .env override
os.environ['DOTENV_OVERRIDE'] = '0'

try:
    import app.config.settings
    print("ERROR: Should have raised RuntimeError")
    exit(1)
except RuntimeError as e:
    if "SECURITY ERROR" in str(e) and "DEV_ADMIN_BYPASS" in str(e):
        print("PASS: Correctly raised RuntimeError")
        exit(0)
    else:
        print(f"ERROR: Wrong error message: {e}")
        exit(1)
"""
    
    result = subprocess.run(
        [sys.executable, "-c", test_script],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    assert result.returncode == 0, f"Test failed: {result.stdout}\n{result.stderr}"
    assert "PASS" in result.stdout


def test_prod_mode_with_bypass_true_string_raises():
    """
    Test that various truthy values for DEV_ADMIN_BYPASS are caught in prod mode.
    """
    truthy_values = ['true', 'TRUE', 'yes', 'YES']
    
    for value in truthy_values:
        test_script = f"""
import os
os.environ['AUTH_MODE'] = 'prod'
os.environ['DEV_ADMIN_BYPASS'] = '{value}'

try:
    import app.config.settings
    exit(1)  # Should not reach here
except RuntimeError as e:
    if "SECURITY ERROR" in str(e):
        exit(0)  # Pass
    exit(1)
"""
        
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0, f"Failed for value '{value}': {result.stderr}"


def test_dev_mode_with_bypass_allows():
    """
    Test that DEV_ADMIN_BYPASS=1 is allowed in dev mode but prints warning.
    """
    test_script = """
import os
os.environ['AUTH_MODE'] = 'dev'
os.environ['DEV_ADMIN_BYPASS'] = '1'

try:
    import app.config.settings
    
    # Should not raise
    if app.config.settings.DEV_ADMIN_BYPASS is True:
        print("PASS: DEV_ADMIN_BYPASS enabled in dev mode")
        exit(0)
    else:
        print("ERROR: DEV_ADMIN_BYPASS should be True")
        exit(1)
except Exception as e:
    print(f"ERROR: Should not raise in dev mode: {e}")
    exit(1)
"""
    
    result = subprocess.run(
        [sys.executable, "-c", test_script],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    assert result.returncode == 0, f"Test failed: {result.stdout}\n{result.stderr}"
    assert "PASS" in result.stdout
    # Check for security warning in stderr or stdout
    output = result.stdout + result.stderr
    assert "[SECURITY WARNING]" in output, "Expected security warning in output"


def test_prod_mode_without_bypass_succeeds():
    """
    Test that production mode works fine when DEV_ADMIN_BYPASS is not set or is 0.
    """
    test_script = """
import os
os.environ['AUTH_MODE'] = 'prod'
os.environ['DEV_ADMIN_BYPASS'] = '0'

try:
    import app.config.settings
    
    if app.config.settings.AUTH_MODE == 'prod' and app.config.settings.DEV_ADMIN_BYPASS is False:
        print("PASS: Production mode without bypass works")
        exit(0)
    else:
        print(f"ERROR: AUTH_MODE={app.config.settings.AUTH_MODE}, BYPASS={app.config.settings.DEV_ADMIN_BYPASS}")
        exit(1)
except Exception as e:
    print(f"ERROR: Should not raise: {e}")
    exit(1)
"""
    
    result = subprocess.run(
        [sys.executable, "-c", test_script],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    assert result.returncode == 0, f"Test failed: {result.stdout}\n{result.stderr}"
    assert "PASS" in result.stdout


def test_dev_mode_without_bypass_succeeds():
    """
    Test that dev mode works fine when DEV_ADMIN_BYPASS is not set or is 0.
    """
    test_script = """
import os
os.environ['AUTH_MODE'] = 'dev'
os.environ.pop('DEV_ADMIN_BYPASS', None)  # Not set

try:
    import app.config.settings
    
    if app.config.settings.AUTH_MODE == 'dev' and app.config.settings.DEV_ADMIN_BYPASS is False:
        print("PASS: Dev mode without bypass works")
        exit(0)
    else:
        print(f"ERROR: AUTH_MODE={app.config.settings.AUTH_MODE}, BYPASS={app.config.settings.DEV_ADMIN_BYPASS}")
        exit(1)
except Exception as e:
    print(f"ERROR: Should not raise: {e}")
    exit(1)
"""
    
    result = subprocess.run(
        [sys.executable, "-c", test_script],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    
    assert result.returncode == 0, f"Test failed: {result.stdout}\n{result.stderr}"
    assert "PASS" in result.stdout


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])

