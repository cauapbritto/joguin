# Instalador de um clique do Soul Strike (chamado pelo INSTALAR.bat).
# Pode ser executado de novo quantas vezes quiser: o que já existe é aproveitado.
. (Join-Path $PSScriptRoot "comum.ps1")
$Log = Join-Path $Raiz "instalar.log"
$env:PYTHONUTF8 = "1"
try { Start-Transcript -Path $Log -Force | Out-Null } catch {}

function Encerrar([int]$codigo) {
    try { Stop-Transcript | Out-Null } catch {}
    if ($codigo -ne 0) { Write-Host "`nDetalhes em: $Log" -ForegroundColor Yellow }
    Pausar
    exit $codigo
}

# Versões do Python com pygame pronto para instalar (sem precisar compilar)
$VersoesAceitas = "3.11", "3.12", "3.13", "3.10"

function Encontrar-Python {
    $candidatos = @()
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($versao in $VersoesAceitas) { $candidatos += ,@("py", "-$versao") }
    }
    foreach ($nome in "python", "python3") {
        if (Get-Command $nome -ErrorAction SilentlyContinue) { $candidatos += ,@($nome) }
    }
    foreach ($comando in $candidatos) {
        $programa = $comando[0]
        $extras = @($comando | Select-Object -Skip 1)
        $saida = & $programa @extras -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $saida) { continue }
        if (@($saida)[0] -notin $VersoesAceitas) { continue }
        return $comando
    }
    return $null
}

function Executar-Python([string[]]$comando, [string[]]$argumentos) {
    $programa = $comando[0]
    $extras = @($comando | Select-Object -Skip 1)
    & $programa @extras @argumentos
    return $LASTEXITCODE
}

Titulo "Soul Strike - Instalação"
Write-Host "   Pasta: $Raiz"

# 1. Python ------------------------------------------------------------------
Titulo "[1/5] Python 3.10 a 3.13"
$python = Encontrar-Python
if (-not $python -and $NoWindows -and (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "   Instalando o Python 3.11 do python.org pelo winget..."
    winget install -e --id Python.Python.3.11 --source winget --silent `
        --accept-package-agreements --accept-source-agreements
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
    $python = Encontrar-Python
}
if (-not $python) {
    Erro "Python 3.10 a 3.13 não encontrado."
    Write-Host "   Instale o Python 3.11 pelo site (vou abrir a página). Na primeira tela do"
    Write-Host "   instalador, MARQUE 'Add python.exe to PATH'. Depois rode o INSTALAR.bat de novo."
    if ($NoWindows) { Start-Process "https://www.python.org/downloads/windows/" }
    Encerrar 1
}
Ok ("Python encontrado: " + ($python -join " "))

# 2. Ambiente virtual --------------------------------------------------------
Titulo "[2/5] Ambiente virtual (.venv)"
if (Test-Path $PythonVenv) {
    Ok "Ambiente já existe, reaproveitando"
} else {
    if ((Executar-Python $python @("-m", "venv", ".venv")) -ne 0 -or -not (Test-Path $PythonVenv)) {
        Erro "Não foi possível criar o ambiente virtual."
        Encerrar 1
    }
    Ok "Ambiente criado"
}

# 3. pip atualizado (usa os certificados do Windows: resolve redes com proxy) --
Titulo "[3/5] Atualizando o pip"
# O pip 24.2 ou mais novo usa os certificados do Windows, o que resolve as redes que
# interceptam HTTPS (faculdade, empresa). Sem internet o pip diz "já instalado" e
# termina SEM erro, então conferimos a versão.
function Pip-Atualizado {
    & $PythonVenv -c "import pip, sys; v = tuple(int(x) for x in pip.__version__.split('.')[:2]); sys.exit(0 if v >= (24, 2) else 1)"
    return $LASTEXITCODE -eq 0
}
& $PythonVenv -m pip install --upgrade pip
if (-not (Pip-Atualizado)) {
    Aviso "A rede bloqueou a atualização (comum em redes que interceptam HTTPS). Tentando de novo..."
    & $PythonVenv -m pip install --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org
}
if (-not (Pip-Atualizado)) {
    Erro "Não foi possível atualizar o pip. Verifique a internet ou use outra rede (ex.: roteador do celular)."
    Encerrar 1
}
$versaoPip = & $PythonVenv -c "import pip; print(pip.__version__)"
Ok "pip atualizado (versão $versaoPip)"

# 4. Bibliotecas ---------------------------------------------------------------
Titulo "[4/5] Instalando as bibliotecas"
& $PythonVenv -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Aviso "Falhou. Tentando de novo sem verificar o certificado do PyPI (redes com proxy)..."
    & $PythonVenv -m pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
}
if ($LASTEXITCODE -ne 0) {
    Erro "A instalação das bibliotecas falhou. Se o erro fala em CERTIFICATE_VERIFY_FAILED,"
    Write-Host "   a rede está bloqueando: conecte em outra rede (ex.: roteador do celular) e rode de novo."
    Encerrar 1
}
& $PythonVenv -c "import pygame, flask, qrcode, PIL"
if ($LASTEXITCODE -ne 0) {
    Erro "As bibliotecas foram instaladas, mas não carregam. Veja o erro acima."
    Write-Host "   Apague a pasta .venv do projeto e rode o INSTALAR.bat de novo."
    Encerrar 1
}
Ok "Bibliotecas instaladas e funcionando"

# 5. Atalho na Área de Trabalho --------------------------------------------------
Titulo "[5/5] Atalho"
if ($NoWindows) {
    try {
        $area = [Environment]::GetFolderPath("Desktop")
        $atalho = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $area "Soul Strike.lnk"))
        $atalho.TargetPath = $PythonwVenv
        $atalho.Arguments = "`"$(Join-Path $Raiz 'main.py')`""
        $atalho.WorkingDirectory = $Raiz
        $atalho.Description = "Soul Strike - Um duelo de heróis!"
        $icone = Join-Path $Raiz "assets\icone.ico"
        if (Test-Path $icone) { $atalho.IconLocation = "$icone,0" }
        $atalho.Save()
        Ok "Atalho 'Soul Strike' criado na Área de Trabalho"
    } catch {
        Aviso "Não foi possível criar o atalho. Use o arquivo SoulStrike.bat da pasta do projeto."
    }
} else {
    Aviso "Fora do Windows: rode o jogo com  .venv/bin/python main.py"
}

Titulo "Instalação concluída!"
Write-Host "   Abra o 'Soul Strike' (atalho na Área de Trabalho ou SoulStrike.bat)."
Write-Host "   Na primeira vez o Windows pode perguntar se libera o acesso à rede:"
Write-Host "   libere, é o servidor do controle pelo celular."
Encerrar 0
