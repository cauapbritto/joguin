#!/usr/bin/env bash
# Instalador do Soul Strike para Linux (chamado pelo INSTALAR.sh).
# Pode ser executado de novo quantas vezes quiser: o que já existe é aproveitado.
#   bash INSTALAR.sh             instala
#   bash INSTALAR.sh --remover   tira os atalhos (a pasta do jogo e o progresso ficam)
set -u
RAIZ="$(dirname "$(dirname "$(readlink -f "$0")")")"
cd "$RAIZ" || exit 1
LOG="$RAIZ/instalar.log"
PY_VENV="$RAIZ/.venv/bin/python"
# Versões do Python com pygame pronto para instalar (sem precisar compilar)
VERSOES_ACEITAS="3.13 3.12 3.11 3.10"

DADOS="${XDG_DATA_HOME:-$HOME/.local/share}"
MENU="$DADOS/applications/soulstrike.desktop"
ICONE="$DADOS/icons/hicolor/256x256/apps/soulstrike.png"
AREA="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
ATALHO="$AREA/soulstrike.desktop"

# Aberto com dois cliques (sem terminal): abre de novo dentro de um terminal, para
# mostrar o progresso e poder pedir a senha. O comando vai em argumentos separados
# (nunca numa linha só): cada terminal entende a linha de um jeito diferente.
if [ ! -t 0 ] && [ -z "${SOULSTRIKE_NO_TERMINAL:-}" ]; then
    export SOULSTRIKE_NO_TERMINAL=1
    eu="$(readlink -f "$0")"
    for term in x-terminal-emulator gnome-terminal mate-terminal xfce4-terminal konsole xterm; do
        command -v "$term" >/dev/null 2>&1 || continue
        case "$term" in
            gnome-terminal)                exec "$term" -- bash "$eu" "$@" ;;
            mate-terminal|xfce4-terminal)  exec "$term" -x bash "$eu" "$@" ;;
            *)                             exec "$term" -e bash "$eu" "$@" ;;
        esac
    done
fi

titulo() { printf '\n\033[33m%s\n  %s\n%s\033[0m\n' "$(printf '=%.0s' {1..60})" "$1" "$(printf '=%.0s' {1..60})"; }
ok()     { printf '   \033[32m[OK]\033[0m    %s\n' "$1"; }
aviso()  { printf '   \033[33m[AVISO]\033[0m %s\n' "$1"; }
erro()   { printf '   \033[31m[ERRO]\033[0m  %s\n' "$1"; }
encerrar() {
    [ "$1" -ne 0 ] && printf '\nDetalhes em: %s\n' "$LOG"
    [ -t 0 ] && read -r -p $'\nPressione Enter para fechar ' _
    exit "$1"
}

if [ "${1:-}" = "--remover" ]; then
    rm -f "$MENU" "$ATALHO" "$ICONE"
    command -v update-desktop-database >/dev/null && update-desktop-database "$DADOS/applications" 2>/dev/null
    ok "Atalhos removidos. Para apagar o jogo, apague a pasta $RAIZ"
    echo "   (o progresso fica em ~/.soulstrike)"
    encerrar 0
fi

# Tudo o que aparece na tela também vai para o log
exec > >(tee "$LOG") 2>&1

titulo "Soul Strike - Instalação"
echo "   Pasta: $RAIZ"

# 1. Python ------------------------------------------------------------------
titulo "[1/5] Python 3.10 a 3.13"
# Todos os Pythons aceitos, o do sistema (python3) primeiro
PYTHONS=()
for cand in python3 $(for v in $VERSOES_ACEITAS; do echo "python$v"; done); do
    command -v "$cand" >/dev/null 2>&1 || continue
    versao="$("$cand" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)" || continue
    case " $VERSOES_ACEITAS " in *" $versao "*) PYTHONS+=("$cand") ;; esac
done
if [ ${#PYTHONS[@]} -eq 0 ]; then
    erro "Não achei o Python 3.10 a 3.13."
    echo "   No Linux Mint ele já vem instalado; se tiver sido removido:"
    echo "   sudo apt install python3 python3-venv"
    encerrar 1
fi
PYTHON="${PYTHONS[0]}"
VERSAO="$("$PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
ok "Python encontrado: $PYTHON ($VERSAO)"

# 2. Ambiente virtual --------------------------------------------------------
titulo "[2/5] Ambiente virtual (.venv)"
# Tenta cada Python aceito até um conseguir criar o ambiente com pip
criar_venv() {
    for PYTHON in "${PYTHONS[@]}"; do
        rm -rf "$RAIZ/.venv"
        "$PYTHON" -m venv "$RAIZ/.venv" >/dev/null 2>&1 && "$PY_VENV" -m pip --version >/dev/null 2>&1 && return 0
    done
    rm -rf "$RAIZ/.venv"
    return 1
}
if [ -x "$PY_VENV" ] && "$PY_VENV" -m pip --version >/dev/null 2>&1; then
    ok "Ambiente já existe, reaproveitando"
elif criar_venv; then
    ok "Ambiente criado com $PYTHON"
else
    # No Mint/Ubuntu o módulo venv vem num pacote à parte
    aviso "Falta o pacote python$VERSAO-venv. Vou instalar pelo apt (pede a sua senha)."
    SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO=sudo
    instalar_venv() { $SUDO apt-get install -y "python$VERSAO-venv" || $SUDO apt-get install -y python3-venv; }
    # Lista de pacotes velha dá "não encontrado": atualiza e tenta de novo
    if instalar_venv || { $SUDO apt-get update && instalar_venv; }; then
        criar_venv || { erro "Não foi possível criar o ambiente virtual."; encerrar 1; }
        ok "Ambiente criado com $PYTHON"
    else
        erro "Não foi possível instalar o python$VERSAO-venv. Rode:  sudo apt install python3-venv"
        encerrar 1
    fi
fi

# 3. pip atualizado -------------------------------------------------------------
titulo "[3/5] Atualizando o pip"
"$PY_VENV" -m pip install --upgrade pip \
    || "$PY_VENV" -m pip install --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org \
    || aviso "Não deu para atualizar o pip; seguindo com a versão atual."
ok "pip $("$PY_VENV" -c 'import pip; print(pip.__version__)')"

# 4. Bibliotecas ---------------------------------------------------------------
titulo "[4/5] Instalando as bibliotecas"
if ! "$PY_VENV" -m pip install -r requirements.txt; then
    aviso "Falhou. Tentando de novo sem verificar o certificado do PyPI (redes com proxy)..."
    if ! "$PY_VENV" -m pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org; then
        erro "A instalação das bibliotecas falhou. Verifique a internet ou use outra rede"
        echo "   (ex.: roteador do celular) e rode de novo."
        encerrar 1
    fi
fi
if ! PYGAME_HIDE_SUPPORT_PROMPT=1 "$PY_VENV" -c "import pygame, flask, qrcode, PIL"; then
    erro "As bibliotecas foram instaladas, mas não carregam. Veja o erro acima."
    echo "   Apague a pasta .venv do projeto e rode o INSTALAR.sh de novo."
    encerrar 1
fi
ok "Bibliotecas instaladas e funcionando"

# 5. Atalhos no menu e na Área de Trabalho ---------------------------------------
titulo "[5/5] Atalhos"
chmod +x "$RAIZ/SoulStrike.sh" "$RAIZ/INSTALAR.sh" 2>/dev/null
mkdir -p "$(dirname "$MENU")" "$(dirname "$ICONE")"
if SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYGAME_HIDE_SUPPORT_PROMPT=1 "$PY_VENV" - "$ICONE" <<'PYEOF'
import sys
sys.path.insert(0, "tools")
from pathlib import Path
from build_exe import make_icon
make_icon(Path(sys.argv[1]))
PYEOF
then
    ok "Ícone criado"
else
    aviso "Não deu para gerar o ícone; o atalho fica sem figura."
fi

# Caminho entre aspas: funciona mesmo com espaços no nome da pasta. Chama pelo bash
# porque o ATUALIZAR do jogo troca os arquivos e pode tirar a permissão de execução.
cat > "$MENU" <<DESKTOP
[Desktop Entry]
Type=Application
Version=1.0
Name=Soul Strike
GenericName=Jogo de luta e aventura
Comment=Campanha cooperativa, duelo de arena e futebol em pixel art, para 1 a 4 jogadores
Exec=bash "$RAIZ/SoulStrike.sh"
Path=$RAIZ
Icon=$ICONE
Terminal=false
Categories=Game;ActionGame;
Keywords=jogo;game;pixel;arena;futebol;
StartupWMClass=soulstrike
Actions=Janela;

[Desktop Action Janela]
Name=Jogar em janela
Exec=bash "$RAIZ/SoulStrike.sh" --janela
DESKTOP
chmod +x "$MENU"
command -v update-desktop-database >/dev/null && update-desktop-database "$(dirname "$MENU")" 2>/dev/null
ok "Atalho 'Soul Strike' criado no menu (seção Jogos)"

if [ -d "$AREA" ]; then
    cp "$MENU" "$ATALHO" && chmod +x "$ATALHO"
    # O Cinnamon só abre atalhos da Área de Trabalho marcados como confiáveis
    command -v gio >/dev/null && gio set "$ATALHO" metadata::trusted true 2>/dev/null
    ok "Atalho criado na Área de Trabalho"
fi

titulo "Pronto!"
echo "   Abra o Soul Strike pelo menu (Jogos) ou pelo atalho na Área de Trabalho."
echo "   Controle pelo celular: o PC e o celular precisam estar na mesma rede Wi-Fi."
if command -v ufw >/dev/null && sudo -n ufw status 2>/dev/null | grep -q "Status: active"; then
    aviso "O firewall (ufw) está ligado. Para o celular conectar, rode:  sudo ufw allow 5000/tcp"
fi
encerrar 0
