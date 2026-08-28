@echo off
title MCP Automated Test Suites
echo ===================================================================
echo   Running MCP Automated Test Suites (Easy, Medium, Hard)
echo ===================================================================
cd /d "%~dp0"

echo.
echo [TEST 1/3] Running Python MCP Client (Tools & Resources Check)...
python client.py
if errorlevel 1 (
    echo [ERROR] client.py failed.
)

echo.
echo ===================================================================
echo [TEST 2/3] Running Versioning & Backward Compatibility Tests (Hard)...
python test_versioning.py
if errorlevel 1 (
    echo [ERROR] test_versioning.py failed.
)

echo.
echo ===================================================================
echo [TEST 3/3] Running Authentication Tests (Medium)...
echo (Note: Requires server running on http://localhost:8088/mcp)
python test_auth.py
echo.

pause
