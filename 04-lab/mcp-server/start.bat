@echo off
title MCP Weather Server (Port 8085)
echo ===================================================
echo Starting FastMCP Weather Server on http://localhost:8085/mcp
echo ===================================================
cd /d "%~dp0"
python weather.py
if errorlevel 1 (
    uv run python weather.py
)
pause
