@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] No existe entorno virtual. Ejecuta primero instalar_lan.bat
  pause
  exit /b 1
)

set "ALLOWED_HOSTS=*"
set "USE_INMEMORY_CHANNEL_LAYER=1"

echo ========================================
echo   Iniciando Chat LAN en puerto 8000
echo ========================================
for /f "tokens=*" %%i in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 ^| Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254*' } ^| Select-Object -First 1 -ExpandProperty IPAddress)"') do set LAN_IP=%%i
if "%LAN_IP%"=="" set LAN_IP=TU_IP_LOCAL
echo URL local:  http://127.0.0.1:8000
echo URL en red: http://%LAN_IP%:8000
echo.
echo Nota: este modo usa canal en memoria (sin Redis) para instalacion simple.
echo.
call .venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000

endlocal
