@echo off
:: IBSimion Windows Launcher
echo Starting IBSimion...
cd /d "%~dp0"

if exist "D\dist\IBSimion\IBSimion.exe" (
    echo Launching packaged standalone executable...
    start "" "D\dist\IBSimion\IBSimion.exe"
) else (
    echo Standalone executable not found in D/dist. 
    echo Launching via Python virtual environment in D/.venv...
    start "" "D\.venv\Scripts\pythonw.exe" "D\frontend\main.py"
)
exit
