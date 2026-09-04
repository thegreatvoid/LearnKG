@echo off
echo ==========================================
echo  Knowledge Graph - Directed Pipeline
echo ==========================================
echo.
cd /d "%~dp0"
echo [*] Installing missing packages...
python -m pip install seaborn pyvis networkx pandas numpy matplotlib scipy -q
echo.
echo [*] Running directed graph pipeline...
python run_directed.py
echo.
echo [*] Opening output in browser...
start "" docs\index.html
echo.
pause
