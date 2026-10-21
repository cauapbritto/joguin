#!/usr/bin/env bash
# Teste de ponta a ponta do INSTALAR.sh (usado no GitHub Actions; roda como usuário
# comum com sudo, numa pasta com espaço no nome). Precisa de: xvfb-run, xdotool e
# desktop-file-validate (veja linux/ver_janela.sh).
#   bash linux/teste_instalador.sh "/home/jogador/Soul Strike"
set -eu
JOGO="$1"
DADOS="$HOME/.local/share"
MENU="$DADOS/applications/soulstrike.desktop"
AREA="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
falha() { echo "FALHOU: $*" >&2; exit 1; }
passo() { printf '\n### %s\n' "$*"; }
export SOULSTRIKE_NO_TERMINAL=1

passo "1ª instalação"
bash "$JOGO/INSTALAR.sh" </dev/null || falha "instalador saiu com erro"
[ -x "$JOGO/.venv/bin/python" ] || falha "sem .venv"
[ -f "$MENU" ] || falha "sem atalho no menu"
[ -f "$DADOS/icons/hicolor/256x256/apps/soulstrike.png" ] || falha "sem ícone"
[ -f "$AREA/soulstrike.desktop" ] || falha "sem atalho na Área de Trabalho"
desktop-file-validate "$MENU" || falha "atalho inválido"
cat "$MENU"

passo "2ª instalação (reaproveita o que existe)"
bash "$JOGO/INSTALAR.sh" </dev/null | tee /tmp/segunda.txt || falha "reinstalação saiu com erro"
grep -q "reaproveitando" /tmp/segunda.txt || falha "não reaproveitou o .venv"

passo "Abrindo o jogo pelo comando do atalho"
# O ATUALIZAR do jogo regrava os arquivos sem a permissão de execução: o atalho tem
# que funcionar mesmo assim
chmod -x "$JOGO/SoulStrike.sh"
EXEC="$(sed -n 's/^Exec=//p' "$MENU" | head -1)"
bash "$JOGO/linux/ver_janela.sh" "$EXEC" || falha "o jogo não abriu"

passo "Remover atalhos"
bash "$JOGO/INSTALAR.sh" --remover </dev/null
[ ! -e "$MENU" ] && [ ! -e "$AREA/soulstrike.desktop" ] || falha "atalhos ficaram"
echo; echo "TUDO CERTO"
