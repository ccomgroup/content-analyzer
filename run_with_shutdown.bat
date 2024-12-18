@echo off
setlocal EnableDelayedExpansion

echo Starting URL Content Analyzer...

REM Activate virtual environment
call venv\Scripts\activate

REM Start Streamlit and save its PID
start /B streamlit run app.py
for /f "tokens=2" %%a in ('tasklist /fi "IMAGENAME eq python.exe" /nh ^| findstr /i "python"') do (
    set PID=%%a
    goto :FOUND_PID
)
:FOUND_PID

echo Streamlit started with PID: !PID!
echo !PID! > streamlit_pid.txt

echo.
echo Press any key to shutdown the application...
pause >nul

REM Kill the process tree
taskkill /F /T /PID !PID!

REM Clean up
del streamlit_pid.txt 2>nul

REM Deactivate virtual environment
call deactivate

echo Application shutdown complete.
endlocal
exit /b 0
