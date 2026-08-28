@echo off
echo =========================================================
echo  Starting Weather Agent Lab (MCP Server + ADK Web Client)
echo =========================================================

echo 1. Launching FastMCP Weather Server on Port 8085...
start "MCP Weather Server" cmd /k "cd /d %~dp0mcp-server && start.bat"

timeout /t 2 /nobreak >nul

echo 2. Launching ADK Web Agent UI on Port 8000...
start "ADK Weather Agent" cmd /k "cd /d %~dp0mcp-client && start.bat"

echo 3. Waiting for servers to initialize...
timeout /t 3 /nobreak >nul

echo 4. Opening Dev UI in your default browser...
start http://localhost:8000/dev-ui/

echo.
echo =========================================================
echo  Web UI is ready at: http://localhost:8000/dev-ui/
echo =========================================================
