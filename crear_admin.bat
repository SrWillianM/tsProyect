@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] No existe entorno virtual. Ejecuta primero instalar_lan.bat
  pause
  exit /b 1
)

call .venv\Scripts\python.exe manage.py createsuperuser

endlocal
