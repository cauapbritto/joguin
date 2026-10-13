@echo off
if not exist "%~dp0windows\instalar.ps1" (
    echo.
    echo  Extraia o zip antes de usar: clique com o botao direito no zip,
    echo  "Extrair tudo...", e rode o INSTALAR.bat da pasta extraida.
    echo.
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows\instalar.ps1"
