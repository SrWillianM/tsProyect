@echo off
setlocal

cd /d "%~dp0"
echo ========================================
echo   Instalador simple - Chat LAN
echo ========================================
echo.

where py >nul 2>nul
if %errorlevel% neq 0 (
  echo [ERROR] No se encontro Python Launcher (py).
  echo Instala Python 3.13+ y marca "Add Python to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/4] Creando entorno virtual...
  py -3 -m venv .venv
  if %errorlevel% neq 0 (
    echo [ERROR] No se pudo crear el entorno virtual.
    pause
    exit /b 1
  )
) else (
  echo [1/4] Entorno virtual ya existe.
)

echo [2/4] Actualizando pip...
call .venv\Scripts\python.exe -m pip install --upgrade pip
if %errorlevel% neq 0 (
  echo [ERROR] Fallo al actualizar pip.
  pause
  exit /b 1
)

echo [3/4] Instalando dependencias...
call .venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 (
  echo [ERROR] Fallo al instalar dependencias.
  pause
  exit /b 1
)

echo [4/4] Aplicando migraciones...
call .venv\Scripts\python.exe manage.py migrate
if %errorlevel% neq 0 (
  echo [ERROR] Fallo al aplicar migraciones.
  pause
  exit /b 1
)

echo.
echo Instalacion completada.
echo.
echo Siguiente paso:
echo   1) (Opcional) Crear admin: crear_admin.bat
echo   2) Iniciar servidor LAN: iniciar_lan.bat
echo.
pause
exit /b 0
