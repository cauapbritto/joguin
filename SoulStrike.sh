#!/usr/bin/env bash
# Abre o Soul Strike (instale antes com o INSTALAR.sh).
RAIZ="$(dirname "$(readlink -f "$0")")"
if [ ! -x "$RAIZ/.venv/bin/python" ]; then
    echo "O jogo ainda não foi instalado. Rode o INSTALAR.sh primeiro." >&2
    exit 1
fi
# Nome da janela igual ao do atalho: o painel agrupa o ícone certo
export SDL_VIDEO_X11_WMCLASS=soulstrike SDL_APP_ID=soulstrike
cd "$RAIZ" && exec "$RAIZ/.venv/bin/python" "$RAIZ/main.py" "$@"
