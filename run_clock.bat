@echo off
cd /d "%~dp0"

if exist "%~dp0FloatingClock.exe" (
    start "" "%~dp0FloatingClock.exe"
    exit /b 0
)

if exist "%~dp0dist\FloatingClock.exe" (
    start "" "%~dp0dist\FloatingClock.exe"
    exit /b 0
)

if exist "%~dp0.venv\Scripts\pythonw.exe" (
    start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0main.py"
    exit /b 0
)

if exist "%~dp0.venv\Scripts\python.exe" (
    start "" "%~dp0.venv\Scripts\python.exe" "%~dp0main.py"
    exit /b 0
)

if exist "%~dp0venv\Scripts\pythonw.exe" (
    start "" "%~dp0venv\Scripts\pythonw.exe" "%~dp0main.py"
    exit /b 0
)

if exist "%~dp0venv\Scripts\python.exe" (
    start "" "%~dp0venv\Scripts\python.exe" "%~dp0main.py"
    exit /b 0
)

if exist "%~dp0.venv\bin\pythonw.exe" (
    start "" "%~dp0.venv\bin\pythonw.exe" "%~dp0main.py"
    exit /b 0
)

if exist "%~dp0.venv\bin\python.exe" (
    start "" "%~dp0.venv\bin\python.exe" "%~dp0main.py"
    exit /b 0
)

if exist "D:\msys2\mingw64\bin\pythonw.exe" (
    start "" "D:\msys2\mingw64\bin\pythonw.exe" "%~dp0main.py"
    exit /b 0
)

where pythonw >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    start "" pythonw "%~dp0main.py"
    exit /b 0
)

where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    start "" python "%~dp0main.py"
    exit /b 0
)

start "" "%~dp0main.py"
exit /b 0

