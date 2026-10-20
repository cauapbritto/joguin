#!/usr/bin/env bash
# Abre o jogo numa tela virtual e confere que a janela aparece (com a classe
# "soulstrike", a mesma do atalho) e continua aberta. Usado pelos testes do Linux.
#   bash linux/ver_janela.sh 'comando que abre o jogo'
# Precisa de: xvfb-run e xdotool.
[ -n "${DISPLAY:-}" ] || exec xvfb-run -a -s "-screen 0 1280x720x24" bash "$0" "$@"
sh -c "$1 --janela" > /tmp/jogo.log 2>&1 &
jogo=$!
for i in $(seq 1 60); do
    sleep 1
    if xdotool search --class "^soulstrike$" >/dev/null 2>&1; then
        echo "Janela aberta (classe soulstrike) após ${i}s"
        sleep 5
        if ! kill -0 "$jogo" 2>/dev/null; then echo "O jogo fechou sozinho"; cat /tmp/jogo.log; exit 1; fi
        kill "$jogo"
        exit 0
    fi
    kill -0 "$jogo" 2>/dev/null || break
done
echo "A janela do jogo não apareceu"; cat /tmp/jogo.log; exit 1
