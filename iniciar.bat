@echo off
setlocal
cd /d "%~dp0"
title Livro-Ponto
if exist ".venv\Scripts\python.exe" goto deps
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -m venv .venv
  goto checkvenv
)
where python >nul 2>nul
if not errorlevel 1 (
  python -m venv .venv
  goto checkvenv
)
if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
  "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m venv .venv
  goto checkvenv
)
echo Instale Python 3.12 ou superior e execute este arquivo novamente.
echo https://www.python.org/downloads/windows/
pause
exit /b 1
:checkvenv
if not exist ".venv\Scripts\python.exe" (
  echo Nao foi possivel preparar o Python.
  pause
  exit /b 1
)
:deps
if not exist ".env" copy /y ".env.example" ".env" >nul
".venv\Scripts\python.exe" -c "import fastapi,uvicorn,sqlalchemy,openpyxl,dotenv,psycopg; import zoneinfo; zoneinfo.ZoneInfo('America/Sao_Paulo')" >nul 2>nul
if errorlevel 1 (
  echo Preparando dependencias. Aguarde...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Falha ao instalar dependencias. Confira o erro acima.
    pause
    exit /b 1
  )
)
if not exist "frontend\dist\index.html" (
  call preparar_frontend.bat
  if errorlevel 1 exit /b 1
)
".venv\Scripts\python.exe" start.py
if errorlevel 1 pause
