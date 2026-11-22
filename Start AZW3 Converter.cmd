@echo off
where pythonw.exe >nul 2>&1
if errorlevel 1 (
    echo Python for Windows with Tcl/Tk is required.
    pause
    exit /b 1
)
start "" pythonw.exe "%~dp0azw3_converter.pyw"
