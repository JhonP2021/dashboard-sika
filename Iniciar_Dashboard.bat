@echo off
setlocal
cd /d "%~dp0"

rem Ruta de la base de Access de produccion. Es lo unico que hay que configurar,
rem por ejemplo: set "RUTA_ACCESS=C:\Datos\Produccion.accdb"
rem Si se deja vacia se respeta ACCESS_DB_PATH del sistema, y si tampoco existe
rem el dashboard lee los CSV de prueba de esta carpeta.
set "RUTA_ACCESS="
if defined RUTA_ACCESS set "ACCESS_DB_PATH=%RUTA_ACCESS%"

python -m streamlit run app.py
pause
