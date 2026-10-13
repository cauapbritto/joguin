@echo off
if not exist "%~dp0.venv\Scripts\pythonw.exe" (
    echo.
    echo  O jogo ainda nao foi instalado. De dois cliques em INSTALAR.bat primeiro.
    echo.
    pause
    exit /b 1
)
start "" /D "%~dp0" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0main.py" %*
