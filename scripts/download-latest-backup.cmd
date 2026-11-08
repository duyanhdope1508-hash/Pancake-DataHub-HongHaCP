@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0download-latest-backup.ps1" %*
if errorlevel 1 (
  echo.
  echo Tai backup that bai. Vui long xem loi phia tren.
  pause
  exit /b 1
)
echo.
echo Tai backup hoan tat.
pause
