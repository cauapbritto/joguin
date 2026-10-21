#!/usr/bin/env bash
# Instalador do Soul Strike para Linux (Linux Mint, Ubuntu, Debian...).
# Dê dois cliques e escolha "Executar no terminal", ou rode:  bash INSTALAR.sh
exec bash "$(dirname "$(readlink -f "$0")")/linux/instalar.sh" "$@"
