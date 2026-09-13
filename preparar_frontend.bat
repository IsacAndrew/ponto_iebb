@echo off
setlocal
cd /d "%~dp0frontend"
where npm >nul 2>nul
if errorlevel 1 (
  echo Instale Node.js LTS para reconstruir a interface.
  pause
  exit /b 1
)
call npm ci
if errorlevel 1 exit /b 1
call npm run build
exit /b %errorlevel%
