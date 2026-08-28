@echo off
title Incident Diagnostics & Order MCP Server
echo ===================================================================
echo   Incident Diagnostics & Order Management FastMCP Server (Port 8088)
echo ===================================================================
cd /d "%~dp0"

echo Choose mode:
echo [1] Streamable HTTP Mode with Authentication (Port 8088)
echo [2] Stdio Mode (for MCP Clients / Subprocess)
set /p choice="Enter choice [1 or 2, default=1]: "

if "%choice%"=="2" (
    echo Starting FastMCP in stdio mode...
    python server.py
) else (
    echo Starting FastMCP on http://localhost:8088/mcp ...
    python server.py --http
)

pause
