@echo off
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0empaquetar_lan.ps1"
if %errorlevel% neq 0 (
  echo [ERROR] Fallo el empaquetado.
  pause
  exit /b 1
)

echo.
echo Empaquetado completado.
pause
exit /b 0
