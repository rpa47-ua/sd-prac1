@echo off
setlocal enabledelayedexpansion

REM Verificar argumentos
if "%1"=="" (
    echo Uso: create_cps.bat [cantidad] [numero_inicial] [puerto_inicial] [ip_central]
    echo.
    echo Ejemplos:
    echo   create_cps.bat 5 1 5050 localhost
    echo   create_cps.bat 3 11 6000 192.168.1.10
    echo   create_cps.bat 10 1 5050
    echo.
    pause
    exit /b 1
)

set CANTIDAD=%1
set NUM_INICIAL=%2
set PUERTO_INICIAL=%3
set IP_CENTRAL=%4

REM Valores por defecto
if "%CANTIDAD%"=="" set CANTIDAD=5
if "%NUM_INICIAL%"=="" set NUM_INICIAL=1
if "%PUERTO_INICIAL%"=="" set PUERTO_INICIAL=5050
if "%IP_CENTRAL%"=="" set IP_CENTRAL=localhost

set /a NUM_FINAL=%NUM_INICIAL%+%CANTIDAD%-1
set /a PUERTO_FINAL=%PUERTO_INICIAL%+%CANTIDAD%-1

echo ========================================
echo Creando %CANTIDAD% CPs (Engine + Monitor)
echo CPs: CP%NUM_INICIAL% a CP%NUM_FINAL%
echo Puertos: %PUERTO_INICIAL% a %PUERTO_FINAL%
echo ========================================
echo.

REM Lanzar CPs Engine
echo Lanzando %CANTIDAD% CPs Engine...
set /a puerto=%PUERTO_INICIAL%
set /a num=%NUM_INICIAL%

for /l %%i in (1,1,%CANTIDAD%) do (
    if !num! LSS 10 (
        set cp_id=CP0!num!
    ) else (
        set cp_id=CP!num!
    )

    echo Lanzando Engine !cp_id! en puerto !puerto!
    start "!cp_id!" cmd /k "cd /d EV_CP_E && python main.py %IP_CENTRAL%:9092 localhost:!puerto! !cp_id!"
    timeout /t 2 /nobreak >nul

    set /a puerto=!puerto!+1
    set /a num=!num!+1
)

echo.
echo Esperando 3 segundos antes de lanzar Monitors...
timeout /t 3 /nobreak >nul
echo.

REM Lanzar CPs Monitor
echo Lanzando %CANTIDAD% CPs Monitor...
set /a puerto=%PUERTO_INICIAL%
set /a num=%NUM_INICIAL%

for /l %%i in (1,1,%CANTIDAD%) do (
    if !num! LSS 10 (
        set cp_id=CP0!num!
    ) else (
        set cp_id=CP!num!
    )

    echo Lanzando Monitor !cp_id! en puerto !puerto!
    start "!cp_id!_MON" cmd /k "cd /d EV_CP_M && python main.py localhost:!puerto! %IP_CENTRAL%:5000 !cp_id!"
    timeout /t 2 /nobreak >nul

    set /a puerto=!puerto!+1
    set /a num=!num!+1
)

echo.
echo ========================================
echo CPs lanzados correctamente!
echo ========================================
echo.
echo %CANTIDAD% CPs creados (Engine + Monitor)
echo IDs: CP%NUM_INICIAL% a CP%NUM_FINAL%
echo Puertos: %PUERTO_INICIAL% a %PUERTO_FINAL%
echo.
pause