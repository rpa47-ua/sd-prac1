@echo off
setlocal enabledelayedexpansion

REM Verificar argumentos
if "%1"=="" (
    echo Uso: create_drivers.bat [cantidad] [numero_inicial] [ip_central]
    echo.
    echo Ejemplos:
    echo   create_drivers.bat 5 1 localhost
    echo   create_drivers.bat 3 11 192.168.1.10
    echo   create_drivers.bat 10 1
    echo.
    pause
    exit /b 1
)

set CANTIDAD=%1
set NUM_INICIAL=%2
set IP_CENTRAL=%3

REM Valores por defecto
if "%CANTIDAD%"=="" set CANTIDAD=5
if "%NUM_INICIAL%"=="" set NUM_INICIAL=1
if "%IP_CENTRAL%"=="" set IP_CENTRAL=localhost

set /a NUM_FINAL=%NUM_INICIAL%+%CANTIDAD%-1

echo ========================================
echo Creando %CANTIDAD% Drivers
echo Drivers: DRV%NUM_INICIAL% a DRV%NUM_FINAL%
echo ========================================
echo.

REM Lanzar Drivers
echo Lanzando %CANTIDAD% Drivers...
set /a num=%NUM_INICIAL%

for /l %%i in (1,1,%CANTIDAD%) do (
    if !num! LSS 10 (
        set drv_id=DRV00!num!
    ) else (
        if !num! LSS 100 (
            set drv_id=DRV0!num!
        ) else (
            set drv_id=DRV!num!
        )
    )

    echo Lanzando Driver !drv_id!
    start "!drv_id!" cmd /k "cd /d EV_DRIVER && python main.py %IP_CENTRAL%:9092 !drv_id!"
    timeout /t 2 /nobreak >nul

    set /a num=!num!+1
)

echo.
echo ========================================
echo Drivers lanzados correctamente!
echo ========================================
echo.
echo %CANTIDAD% Drivers creados
echo IDs: DRV%NUM_INICIAL% a DRV%NUM_FINAL%
echo.
pause