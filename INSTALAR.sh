#!/usr/bin/env bash
# Instalador do Soul Strike para Linux (testado no Linux Mint 21 e 22, serve no Ubuntu e no Debian).
# Pode ser executado de novo quantas vezes quiser: o que já existe é aproveitado.
#
#   ./INSTALAR.sh               instala (ou conserta) e cria os atalhos
#   ./INSTALAR.sh --desinstalar tira os atalhos e o .venv (a pasta do jogo e o progresso ficam)

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$RAIZ" || exit 1
LOG="$RAIZ/instalar.log"
VENV="$RAIZ/.venv"
PYTHON_VENV="$VENV/bin/python"
APP_ID="soulstrike"
APPS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/256x256/apps"
DESKTOP_FILE="$APPS_DIR/$APP_ID.desktop"
VERSOES_ACEITAS="3.12 3.11 3.13 3.10"     # versões com pygame pronto para instalar (sem compilar)

# tudo o que aparece na tela vai também para o log
exec > >(tee "$LOG") 2>&1

titulo() { printf '\n\033[33m%s\n  %s\n%s\033[0m\n' "$(printf '=%.0s' {1..60})" "$1" "$(printf '=%.0s' {1..60})"; }
ok()     { printf '   \033[32m[OK]\033[0m    %s\n' "$1"; }
aviso()  { printf '   \033[33m[AVISO]\033[0m %s\n' "$1"; }
erro()   { printf '   \033[31m[ERRO]\033[0m  %s\n' "$1"; }

encerrar() {
    [ "$1" -ne 0 ] && printf '\n\033[33mDetalhes em: %s\033[0m\n' "$LOG"
    # aberto com dois cliques, o terminal fecharia antes de dar para ler
    [ -t 0 ] && read -r -p $'\nPressione Enter para fechar ' _
    exit "$1"
}

area_de_trabalho() {
    local pasta=""
    command -v xdg-user-dir >/dev/null && pasta="$(xdg-user-dir DESKTOP 2>/dev/null)"
    if [ -n "$pasta" ] && [ "$pasta" != "$HOME" ] && [ -d "$pasta" ]; then
        echo "$pasta"
        return
    fi
    for pasta in "$HOME/Área de Trabalho" "$HOME/Desktop"; do
        [ -d "$pasta" ] && echo "$pasta" && return
    done
}

if [ "$1" = "--desinstalar" ]; then
    titulo "Soul Strike - Desinstalação"
    rm -f "$DESKTOP_FILE" "$ICON_DIR/$APP_ID.png"
    desk="$(area_de_trabalho)"
    [ -n "$desk" ] && rm -f "$desk/$APP_ID.desktop"
    rm -rf "$VENV"
    command -v update-desktop-database >/dev/null && update-desktop-database "$APPS_DIR" 2>/dev/null
    ok "Atalhos e .venv removidos. O progresso salvo continua em ~/.soulstrike"
    encerrar 0
fi

titulo "Soul Strike - Instalação"
echo "   Pasta: $RAIZ"

# 1. Python ------------------------------------------------------------------
titulo "[1/6] Python 3.10 a 3.13"
encontrar_python() {
    local nome versao
    for nome in python3 $(for v in $VERSOES_ACEITAS; do echo "python$v"; done); do
        command -v "$nome" >/dev/null || continue
        versao="$("$nome" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null)" || continue
        case " $VERSOES_ACEITAS " in *" $versao "*) echo "$nome"; return 0 ;; esac
    done
    return 1
}
PYTHON="$(encontrar_python)"
if [ -z "$PYTHON" ]; then
    erro "Python 3.10 a 3.13 não encontrado."
    echo "   No Linux Mint ele já vem instalado; instale com:  sudo apt install python3"
    encerrar 1
fi
PY_VERSAO="$("$PYTHON" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
ok "Python encontrado: $PYTHON ($PY_VERSAO)"

# 2. Ambiente virtual --------------------------------------------------------
titulo "[2/6] Ambiente virtual (.venv)"
if [ -x "$PYTHON_VENV" ] && "$PYTHON_VENV" -m pip --version >/dev/null 2>&1; then
    ok "Ambiente já existe, reaproveitando"
else
    rm -rf "$VENV"
    if ! "$PYTHON" -m venv "$VENV" 2>/dev/null; then
        # no Mint/Ubuntu o venv vem num pacote separado (python3.12-venv, por exemplo)
        rm -rf "$VENV"
        aviso "Falta o pacote python$PY_VERSAO-venv. Vou instalar pelo apt (pede a sua senha)."
        if ! sudo apt-get install -y "python$PY_VERSAO-venv"; then
            sudo apt-get update && sudo apt-get install -y "python$PY_VERSAO-venv" python3-venv
        fi
        if ! "$PYTHON" -m venv "$VENV"; then
            erro "Não foi possível criar o ambiente virtual."
            echo "   Rode:  sudo apt install python$PY_VERSAO-venv   e abra o instalador de novo."
            encerrar 1
        fi
    fi
    ok "Ambiente criado"
fi

# 3. pip ---------------------------------------------------------------------
titulo "[3/6] Atualizando o pip"
PIP_REDE=()
if ! "$PYTHON_VENV" -m pip install --upgrade pip; then
    aviso "A rede bloqueou a atualização (comum em redes que interceptam HTTPS). Tentando de novo..."
    PIP_REDE=(--trusted-host pypi.org --trusted-host files.pythonhosted.org)
    "$PYTHON_VENV" -m pip install --upgrade pip "${PIP_REDE[@]}" || aviso "Seguindo com o pip que já veio."
fi
ok "pip $("$PYTHON_VENV" -c 'import pip; print(pip.__version__)')"

# 4. Bibliotecas ---------------------------------------------------------------
titulo "[4/6] Instalando as bibliotecas"
if ! "$PYTHON_VENV" -m pip install -r requirements.txt "${PIP_REDE[@]}"; then
    aviso "Falhou. Tentando de novo sem verificar o certificado do PyPI (redes com proxy)..."
    if ! "$PYTHON_VENV" -m pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org; then
        erro "A instalação das bibliotecas falhou. Verifique a internet ou use outra rede"
        echo "   (ex.: roteador do celular) e rode de novo."
        encerrar 1
    fi
fi
if ! "$PYTHON_VENV" -c "import pygame, flask, qrcode, PIL" 2>/dev/null; then
    erro "As bibliotecas foram instaladas, mas não carregam. Veja o erro acima."
    echo "   Rode:  ./INSTALAR.sh --desinstalar   e depois  ./INSTALAR.sh"
    encerrar 1
fi
ok "Bibliotecas instaladas e funcionando"

# 5. Atalhos -------------------------------------------------------------------
titulo "[5/6] Atalhos no menu e na Área de Trabalho"
chmod +x "$RAIZ/SoulStrike.sh" "$RAIZ/INSTALAR.sh" 2>/dev/null
mkdir -p "$APPS_DIR" "$ICON_DIR"
ICONE="$ICON_DIR/$APP_ID.png"
"$PYTHON_VENV" - "$RAIZ/assets/icone.ico" "$ICONE" <<'PY' || aviso "Não consegui gerar o ícone (o atalho fica sem figura)."
import sys
from PIL import Image
icon = Image.open(sys.argv[1])
icon.size = max(icon.info.get("sizes", [icon.size]))
icon.save(sys.argv[2])
PY
# Exec entre aspas: a pasta pode ter espaço no nome
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=Soul Strike
Comment=Campanha, duelo de arena e futebol em pixel art
Exec="$RAIZ/SoulStrike.sh"
Path=$RAIZ
Icon=$ICONE
Terminal=false
Categories=Game;ActionGame;
Keywords=jogo;game;duelo;futebol;
StartupNotify=true
EOF
chmod +x "$DESKTOP_FILE"
command -v update-desktop-database >/dev/null && update-desktop-database "$APPS_DIR" 2>/dev/null
ok "Soul Strike no menu de aplicativos (categoria Jogos)"
desk="$(area_de_trabalho)"
if [ -n "$desk" ]; then
    cp "$DESKTOP_FILE" "$desk/$APP_ID.desktop"
    chmod +x "$desk/$APP_ID.desktop"
    # sem isso o Mint mostra o atalho como "não confiável" e não abre com dois cliques
    command -v gio >/dev/null && gio set "$desk/$APP_ID.desktop" metadata::trusted true 2>/dev/null
    ok "Atalho 'Soul Strike' criado na Área de Trabalho"
else
    aviso "Área de Trabalho não encontrada; use o menu de aplicativos ou ./SoulStrike.sh"
fi

# 6. Controle pelo celular (firewall) -------------------------------------------
titulo "[6/6] Controle pelo celular"
PORTA=5000
if command -v ufw >/dev/null && systemctl is-active --quiet ufw 2>/dev/null; then
    aviso "O firewall está ligado. Vou liberar a porta $PORTA (pede a sua senha)."
    if sudo ufw allow "$PORTA/tcp" comment "Soul Strike"; then
        ok "Porta $PORTA liberada"
    else
        aviso "Não liberou. Se o celular não conectar: sudo ufw allow $PORTA/tcp"
    fi
else
    ok "Firewall desligado, nada a fazer"
fi

titulo "Instalação concluída!"
echo "   Abra o 'Soul Strike' pelo menu (Jogos), pelo atalho na Área de Trabalho"
echo "   ou pelo terminal:  ./SoulStrike.sh   (em janela: ./SoulStrike.sh --janela)"
encerrar 0
