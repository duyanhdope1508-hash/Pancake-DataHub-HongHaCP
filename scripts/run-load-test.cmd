@echo off
setlocal
chcp 65001 >nul
set "PROJECT_DIR=%~dp0.."
set "PYTHON=%PROJECT_DIR%\.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo Khong tim thay Python trong .venv. Hay chay setup-env.cmd truoc.
  exit /b 1
)

"%PYTHON%" "%~dp0load_test.py" %*
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo Kiem thu da dung hoac co muc tai khong dat.
)

exit /b %EXIT_CODE%
