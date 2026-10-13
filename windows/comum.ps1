# Funções usadas pelo instalador do Soul Strike.
$ErrorActionPreference = "Continue"
$Raiz = Split-Path -Parent $PSScriptRoot
Set-Location $Raiz

$NoWindows = ($PSVersionTable.PSEdition -eq "Desktop") -or $IsWindows
if ($NoWindows) {
    $PythonVenv  = Join-Path $Raiz ".venv\Scripts\python.exe"
    $PythonwVenv = Join-Path $Raiz ".venv\Scripts\pythonw.exe"
} else {
    $PythonVenv  = Join-Path $Raiz ".venv/bin/python"
    $PythonwVenv = $PythonVenv
}

function Titulo([string]$texto) {
    Write-Host ""
    Write-Host ("=" * 60) -ForegroundColor DarkYellow
    Write-Host "  $texto" -ForegroundColor Yellow
    Write-Host ("=" * 60) -ForegroundColor DarkYellow
}
function Ok([string]$texto)    { Write-Host "   [OK]    $texto" -ForegroundColor Green }
function Aviso([string]$texto) { Write-Host "   [AVISO] $texto" -ForegroundColor Yellow }
function Erro([string]$texto)  { Write-Host "   [ERRO]  $texto" -ForegroundColor Red }
function Pausar { [void](Read-Host "`nPressione Enter para continuar") }
