@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Execute iniciar.bat primeiro.
  pause
  exit /b 1
)
if not exist backups mkdir backups
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "STAMP=%%i"
".venv\Scripts\python.exe" -m backend.backup "backups\ponto-%STAMP%.zip"
pause
