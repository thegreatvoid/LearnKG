@echo off
echo ==========================================
echo  Educational Dataset Construction Pipeline
echo ==========================================
echo.
cd /d "%~dp0"
echo [*] Running Educational Dataset Construction Pipeline...
python test_educational_pipeline.py
echo.
echo [*] Opening Educational Knowledge Graph in browser...
start "" docs\index.html
echo.
pause
