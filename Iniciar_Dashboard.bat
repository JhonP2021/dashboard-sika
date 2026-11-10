@echo off
setlocal
cd /d "%~dp0"

rem Ruta de la base de Access de produccion. Es lo unico que hay que configurar.
rem Ejemplo: set "RUTA_ACCESS=C:\Datos\Produccion.accdb"
set "RUTA_ACCESS="
if defined RUTA_ACCESS set "ACCESS_DB_PATH=%RUTA_ACCESS%"

if not defined ACCESS_DB_PATH (
    echo.
    echo ERROR: Debes ingresar la ruta del archivo .accdb en RUTA_ACCESS.
    echo Ejemplo: set "RUTA_ACCESS=C:\Datos\Produccion.accdb"
    pause
    exit /b 1
)

if not exist "%ACCESS_DB_PATH%" (
    echo.
    echo ERROR: No existe la base de Access:
    echo %ACCESS_DB_PATH%
    pause
    exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python no esta instalado o no esta en PATH.
    pause
    exit /b 1
)

echo Iniciando Dashboard SIKA...
echo La ruta de Access configurada es:
echo %ACCESS_DB_PATH%
echo.

python -m streamlit run app.py --server.address=localhost --server.port=8501 --server.headless=false
pause
