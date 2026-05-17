@echo off
title ThoughtLens Launcher
cd /d "%~dp0"

:: Colors for Windows 10+ (ANSI)
for /f "tokens=1,2 delims=#" %%a in ('"prompt #$H#$E# & echo on & for %%b in (1) do rem"') do set "ESC=%%b"
set "GREEN=%ESC%[32m"
set "CYAN=%ESC%[36m"
set "YELLOW=%ESC%[33m"
set "RED=%ESC%[31m"
set "BOLD=%ESC%[1m"
set "NC=%ESC%[0m"

cls

:: Banner
echo.
echo %CYAN%%BOLD%
echo    ######## ##     ## ########  ##     ##  ######   ##     ## ########
echo        ##    ##     ## ##     ## ##     ## ##    ##  ##     ##    ##
echo        ##    ##     ## ##     ## ##     ## ##        ##     ##    ##
echo        ##    ######### ##     ## ##     ## ##   #### #########    ##
echo        ##    ##     ## ##     ## ##     ## ##    ##  ##     ##    ##
echo        ##    ##     ## ##     ## ##     ## ##    ##  ##     ##    ##
echo        ##    ##     ##  #######   #######   ######   ##     ##    ##
echo.
echo         ##       ######## ##    ##  ######
echo         ##       ##       ###   ## ##    ##
echo         ##       ##       ####  ## ##
echo         ##       ######   ## ## ##  ######
echo         ##       ##       ##  ####       ##
echo         ##       ##       ##   ### ##    ##
echo         ######## ########  ##    ##  ######
echo %NC%
echo %CYAN%           L I V E   A G E N T   F O R E N S I C S%NC%
echo.
echo %YELLOW%  v0.1.0  -  Agent Security and AI Governance%NC%
echo.
echo   --------------------------------------------------------------------------
echo.

:: Kill existing processes
echo %YELLOW%  Cleaning up previous instances...%NC%
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM node.exe >nul 2>&1
timeout /t 1 /nobreak >nul >nul
echo %GREEN%  + Done%NC%
echo.

:: Start Lobster Trap
echo %CYAN%  [1/3] Starting Lobster Trap...%NC%
if exist "%~dp0..\lobstertrap\lobstertrap.exe" (
    start "Lobster Trap" /min cmd /c "cd /d %~dp0..\lobstertrap && .\lobstertrap.exe serve --listen :8080 --backend https://integrate.api.nvidia.com/v1 --policy %~dp0configs\thoughtlens_policy.yaml"
    echo %GREEN%        + running on :8080%NC%
) else if exist "%~dp0lobstertrap\lobstertrap.exe" (
    start "Lobster Trap" /min cmd /c "cd /d %~dp0lobstertrap && .\lobstertrap.exe serve --listen :8080 --backend https://integrate.api.nvidia.com/v1 --policy %~dp0configs\thoughtlens_policy.yaml"
    echo %GREEN%        + running on :8080%NC%
) else (
    echo %YELLOW%        + binary not found - DPI layer disabled%NC%
)
echo.

:: Start Backend
echo %CYAN%  [2/3] Starting ThoughtLens backend...%NC%
start "ThoughtLens Backend" /min cmd /c "cd /d %~dp0 && python main.py"
echo %GREEN%        + running on :8000%NC%
echo.

:: Start UI
echo %CYAN%  [3/3] Starting React UI...%NC%
cd ui
start "ThoughtLens UI" /min cmd /c "cd /d %~dp0ui && npm run dev"
cd ..
echo %GREEN%        + running on :3000%NC%
echo.

:: Wait for services
timeout /t 3 /nobreak >nul

:: Ready message
echo   --------------------------------------------------------------------------
echo.
echo %BOLD%  ThoughtLens is ready!%NC%
echo.
echo %CYAN%  Dashboard -^>  http://localhost:3000%NC%
echo %CYAN%  API       -^>  http://localhost:8000%NC%
echo %CYAN%  Docs      -^>  http://localhost:8000/docs%NC%
echo.
echo %YELLOW%  Run the agent:%NC%
echo %YELLOW%    python demo/interactive_agent.py%NC%
echo.
echo   --------------------------------------------------------------------------
echo %RED%  Close this window to stop all services%NC%
echo.

:: Open browser
start http://localhost:3000

echo.
echo %GREEN%  Press any key to exit (services keep running)%NC%
pause >nul