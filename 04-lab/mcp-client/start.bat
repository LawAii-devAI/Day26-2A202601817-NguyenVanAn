@echo off
title ADK Weather Agent Client (Port 8000)
echo ===================================================
echo Starting ADK Weather Agent Web UI on http://localhost:8000
echo ===================================================
cd /d "%~dp0"
python -m google.adk.cli web
pause
