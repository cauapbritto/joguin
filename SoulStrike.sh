#!/usr/bin/env bash
# Abre o Soul Strike no Linux (depois de rodar o INSTALAR.sh). Aceita as opções do main.py,
# por exemplo:  ./SoulStrike.sh --janela
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -x "$RAIZ/.venv/bin/python" ]; then
    echo "O jogo ainda não foi instalado. Rode o INSTALAR.sh primeiro."
    command -v notify-send >/dev/null && notify-send "Soul Strike" "Rode o INSTALAR.sh primeiro."
    exit 1
fi
cd "$RAIZ" && exec "$RAIZ/.venv/bin/python" "$RAIZ/main.py" "$@"
