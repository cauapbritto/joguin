"""Vibração do controle: apanhou, fez gol ou cesta, soltou o SUPER.

Só vibra o controle do jogador envolvido (pela vaga), e dá para desligar nas opções. Controles sem
motor (ou o SDL sem suporte) simplesmente ignoram."""
from . import settings

_pads = None        # o Gamepads do jogo (game.py registra)

# (forte, fraco, milissegundos)
HIT = (0.5, 0.7, 140)
BIG_HIT = (0.7, 0.9, 200)
SCORE = (0.5, 0.9, 380)
SUPER = (0.25, 0.6, 160)


def register(gamepads):
    global _pads
    _pads = gamepads


def buzz(slot, kind):
    if _pads is None or slot is None or not settings.get("vibracao"):
        return False
    return _pads.rumble(slot, *kind)


def fighter(f, kind):
    """Vibra o controle de quem controla o lutador (CPU não tem controle)."""
    if f is None or getattr(f, "is_cpu", True):
        return False
    return buzz(getattr(f, "slot", None), kind)


def hit(f, dealt):
    return fighter(f, BIG_HIT if dealt >= 20 else HIT)


def team(match, team_index, kind=SCORE):
    for f in match.fighters:
        if getattr(f, "team", None) == team_index:
            fighter(f, kind)
