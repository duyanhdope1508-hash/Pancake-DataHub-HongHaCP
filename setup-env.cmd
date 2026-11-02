@echo off
setlocal
cd /d "%~dp0"

echo Pancake Data Hub - local environment setup
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Python environment was not found at .venv\Scripts\python.exe
    echo Ask Codex to recreate the local Python environment.
    pause
    exit /b 1
)

echo The API key will be saved only in the local .env file.
echo It will not be displayed while you paste or type it.
echo.

".venv\Scripts\python.exe" -m app.setup_env
if errorlevel 1 (
    echo.
    echo Setup failed. Read the error above before trying again.
    pause
    exit /b 1
)

echo.
echo Setup completed successfully.
pause

