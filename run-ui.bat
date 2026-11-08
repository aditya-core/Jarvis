@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

rem ---- Jarvis web UI launcher (movie-style HUD in browser) ----
set "PY=%~dp0venv\Scripts\python.exe"
if not exist "!PY!" set "PY=%~dp0..\venv\Scripts\python.exe"

if not exist "!PY!" (
    echo [Jarvis] No virtual environment found - creating one now...
    where python >nul 2>nul || (echo [Jarvis] Python not found on PATH! Install from python.org ^(check "Add to PATH"^). & pause & exit /b 1)
    python -m venv venv
    set "PY=%~dp0venv\Scripts\python.exe"
    echo [Jarvis] Installing dependencies ^(first run, may take a minute...^)
    "!PY!" -m pip install -q -r requirements.txt
)

echo [Jarvis] Starting web UI on http://localhost:8765 ...
"!PY!" main.py --ui %*
