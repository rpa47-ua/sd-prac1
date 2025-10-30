@echo off
echo ========================================
echo Lanzando 10 CPs y 10 Drivers
echo ========================================
echo.

REM Lanzar 10 Engine
echo Lanzando CPs Engine...
start "CP01" cmd /k "cd /d EV_CP_E && python main.py localhost:9092 localhost:5050 CP01"
timeout /t 2 /nobreak >nul
start "CP02" cmd /k "cd /d EV_CP_E && python main.py localhost:9092 localhost:5051 CP02"
timeout /t 2 /nobreak >nul
start "CP03" cmd /k "cd /d EV_CP_E && python main.py localhost:9092 localhost:5052 CP03"
timeout /t 2 /nobreak >nul
start "CP04" cmd /k "cd /d EV_CP_E && python main.py localhost:9092 localhost:5053 CP04"
timeout /t 2 /nobreak >nul
start "CP05" cmd /k "cd /d EV_CP_E && python main.py localhost:9092 localhost:5054 CP05"
timeout /t 2 /nobreak >nul
start "CP06" cmd /k "cd /d EV_CP_E && python main.py localhost:9092 localhost:5055 CP06"
timeout /t 2 /nobreak >nul
start "CP07" cmd /k "cd /d EV_CP_E && python main.py localhost:9092 localhost:5056 CP07"
timeout /t 2 /nobreak >nul
start "CP08" cmd /k "cd /d EV_CP_E && python main.py localhost:9092 localhost:5057 CP08"
timeout /t 2 /nobreak >nul
start "CP09" cmd /k "cd /d EV_CP_E && python main.py localhost:9092 localhost:5058 CP09"
timeout /t 2 /nobreak >nul
start "CP10" cmd /k "cd /d EV_CP_E && python main.py localhost:9092 localhost:5059 CP10"
timeout /t 3 /nobreak >nul

REM Lanzar 10 Monitor
echo Lanzando CPs Monitor...
start "CP01" cmd /k "cd /d EV_CP_M && python main.py localhost:5050 localhost:5000 CP01"
timeout /t 2 /nobreak >nul
start "CP02" cmd /k "cd /d EV_CP_M && python main.py localhost:5051 localhost:5000 CP02"
timeout /t 2 /nobreak >nul
start "CP03" cmd /k "cd /d EV_CP_M && python main.py localhost:5052 localhost:5000 CP03"
timeout /t 2 /nobreak >nul
start "CP04" cmd /k "cd /d EV_CP_M && python main.py localhost:5053 localhost:5000 CP04"
timeout /t 2 /nobreak >nul
start "CP05" cmd /k "cd /d EV_CP_M && python main.py localhost:5054 localhost:5000 CP05"
timeout /t 2 /nobreak >nul
start "CP06" cmd /k "cd /d EV_CP_M && python main.py localhost:5055 localhost:5000 CP06"
timeout /t 2 /nobreak >nul
start "CP07" cmd /k "cd /d EV_CP_M && python main.py localhost:5056 localhost:5000 CP07"
timeout /t 2 /nobreak >nul
start "CP08" cmd /k "cd /d EV_CP_M && python main.py localhost:5057 localhost:5000 CP08"
timeout /t 2 /nobreak >nul
start "CP09" cmd /k "cd /d EV_CP_M && python main.py localhost:5058 localhost:5000 CP09"
timeout /t 2 /nobreak >nul
start "CP10" cmd /k "cd /d EV_CP_M && python main.py localhost:5059 localhost:5000 CP10"
timeout /t 3 /nobreak >nul

REM Lanzar 10 Drivers
echo Lanzando Drivers...
start "DRV001" cmd /k "cd /d EV_DRIVER && python main.py localhost:9092 DRV001"
timeout /t 2 /nobreak >nul
start "DRV002" cmd /k "cd /d EV_DRIVER && python main.py localhost:9092 DRV002"
timeout /t 2 /nobreak >nul
start "DRV003" cmd /k "cd /d EV_DRIVER && python main.py localhost:9092 DRV003"
timeout /t 2 /nobreak >nul
start "DRV004" cmd /k "cd /d EV_DRIVER && python main.py localhost:9092 DRV004"
timeout /t 2 /nobreak >nul
start "DRV005" cmd /k "cd /d EV_DRIVER && python main.py localhost:9092 DRV005"
timeout /t 2 /nobreak >nul
start "DRV006" cmd /k "cd /d EV_DRIVER && python main.py localhost:9092 DRV006"
timeout /t 2 /nobreak >nul
start "DRV007" cmd /k "cd /d EV_DRIVER && python main.py localhost:9092 DRV007"
timeout /t 2 /nobreak >nul
start "DRV008" cmd /k "cd /d EV_DRIVER && python main.py localhost:9092 DRV008"
timeout /t 2 /nobreak >nul
start "DRV009" cmd /k "cd /d EV_DRIVER && python main.py localhost:9092 DRV009"
timeout /t 2 /nobreak >nul
start "DRV010" cmd /k "cd /d EV_DRIVER && python main.py localhost:9092 DRV010"

echo.
echo ========================================
echo Todos los componentes lanzados!
echo ========================================
echo.
echo 10 CPs Engine (CP01 - CP10)
echo 10 CPs Monitor (CP01 - CP10)
echo 10 Drivers (DRV001 - DRV010)
echo.
pause