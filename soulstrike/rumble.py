"""Vibração do controle e do celular: apanhou, fez gol ou cesta, soltou o SUPER e, na campanha,
os avisos da passagem coletiva (falta você na porta, a contagem e a ida do grupo).

Só vibra quem está envolvido (pela vaga), e dá para desligar nas opções. O controle USB ou
Bluetooth vibra pelo SDL; o celular recebe o nome do padrão no status e vibra pelo navegador
(Android; o iPhone não deixa a página vibrar e simplesmente ignora). Controles sem motor também
ignoram."""
from . import settings

_pads = None        # o Gamepads do jogo (game.py registra)

# (forte, fraco, milissegundos)
HIT = (0.5, 0.7, 140)
BIG_HIT = (0.7, 0.9, 200)
SCORE = (0.5, 0.9, 380)
SUPER = (0.25, 0.6, 160)
CALL = (0.45, 0.65, 260)        # campanha: o grupo está na porta e falta você
TICK = (0.0, 0.35, 60)          # cada segundo da contagem da passagem
GO = (0.6, 0.9, 320)            # o grupo foi (porta ou portal)

# nome de cada padrão para o celular (web/static/controller.js tem o desenho de cada um)
PHONE = {HIT: "hit", BIG_HIT: "big_hit", SCORE: "score", SUPER: "super", CALL: "call", TICK: "tick", GO: "go"}
URGENT = {CALL, GO}             # passam por cima do limite de uma vibração a cada 250 ms


def register(gamepads):
    global _pads
    _pads = gamepads


def buzz(slot, kind):
    if slot is None or not settings.get("vibracao"):
        return False
    phone = _phone(slot, kind)
    pad = _pads.rumble(slot, *kind) if _pads is not None else False
    return bool(phone or pad)


def _phone(slot, kind):
    from .net.remote import hub
    name = PHONE.get(kind)
    return name is not None and hub.buzz(slot, name, force=kind in URGENT)


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
