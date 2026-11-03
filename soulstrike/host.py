"""O P1 é o dono da partida (a coroa): só ele pausa e mexe nas regras, a não ser no treino ou
quando joga sozinho. Aqui ficam as regras que dá para trocar com a bola rolando e a troca de um
lutador entre jogador e CPU (sair no meio vira CPU; um controle novo assume uma CPU)."""
from . import config
from .ai import BALL_DIFFICULTIES, DIFFICULTIES, DIFFICULTY_ORDER, BasketballAI, FighterAI, SoccerAI


class IdleInput:
    """Comandos parados: o lutador de quem está com o menu pessoal aberto fica quieto."""

    double_tap = None
    analog = None

    def __init__(self, real):
        self.real = real
        self.slot = real.slot
        self.layout = real.layout

    def held(self, action):
        return False

    def pressed(self, action):
        return False

    def axis(self):
        return 0.0, 0.0


def host_slot(session):
    """Quem tem a coroa: o jogador humano de menor número (se o P1 sair, passa adiante)."""
    if session is None:
        return 1
    humans = sorted(s.slot for s in session.slots if not s.cpu)
    return humans[0] if humans else 1


def anyone_pauses(session):
    """No treino ou com um jogador só, qualquer um pausa."""
    if session is None:
        return True
    training = session.mode.startswith("treino") or session.mode == "desafio_goleiro"
    return training or sum(1 for s in session.slots if not s.cpu) <= 1


def ai_class(match):
    from .basketball import BasketballMatch
    from .matches import SoccerMatch
    if isinstance(match, BasketballMatch):
        return BasketballAI
    if isinstance(match, SoccerMatch):
        return SoccerAI
    return FighterAI


def _ball_match(match):
    return ai_class(match) is not FighterAI


def fighter_of(match, slot):
    return next((f for f in match.fighters if f.slot == slot), None)


def setup_of(session, slot):
    return next((s for s in session.slots if s.slot == slot), None)


def make_cpu(game, match, slot):
    """Quem sai no meio vira CPU (a partida continua com o mesmo herói)."""
    fighter = fighter_of(match, slot)
    setup = setup_of(game.session, slot)
    if fighter is None or setup is None or setup.cpu:
        return False
    difficulty = game.session.difficulty
    match.controllers[fighter] = ai_class(match)(difficulty)
    fighter.is_cpu = True
    setup.cpu = True
    if _ball_match(match):
        fighter.speed *= BALL_DIFFICULTIES[difficulty]["speed"]
    return True


def make_human(game, match, slot):
    """Um controle (ou celular) novo assume a CPU daquela vaga sem reiniciar."""
    fighter = fighter_of(match, slot)
    setup = setup_of(game.session, slot)
    if fighter is None or setup is None or not setup.cpu:
        return False
    inp = game.inputs[slot]
    inp.set_layout("soccer" if _ball_match(match) else "battle")
    match.controllers[fighter] = inp
    fighter.is_cpu = False
    setup.cpu = False
    if _ball_match(match):
        fighter.speed /= BALL_DIFFICULTIES[game.session.difficulty]["speed"]
    return True


def set_difficulty(game, match, value):
    """Muda a dificuldade das CPUs com a partida rolando."""
    old = game.session.difficulty
    game.session.difficulty = value
    for fighter, ctrl in match.controllers.items():
        if isinstance(ctrl, (SoccerAI, BasketballAI)):
            ctrl.cfg = BALL_DIFFICULTIES[value]
            fighter.speed *= BALL_DIFFICULTIES[value]["speed"] / BALL_DIFFICULTIES[old]["speed"]
        elif isinstance(ctrl, FighterAI):
            ctrl.cfg = DIFFICULTIES[value]


LENGTH_LABELS = {"3": "3 GOLS", "5": "5 GOLS", "7": "7 GOLS", "tempo": "3 MIN", "penaltis": "3 MIN + PÊNALTIS"}


def set_length(match, value):
    """Futebol: troca o tamanho da partida. O placar continua; o tempo novo conta a partir de agora."""
    match.session.soccer_length = value
    timed = value in ("tempo", "penaltis")
    match.win_score = None if timed else int(value)
    if timed and not match.clock:
        match.clock = config.SOCCER_MINUTES * 60 * config.FPS
    elif not timed:
        match.clock = 0
    match.tiebreak = "penaltis" if value == "penaltis" else "gol de ouro"
    if match.win_score is not None and max(match.score) >= match.win_score:
        match.win_score = max(match.score) + 1          # ninguém ganha sem fazer o próximo gol


def rules(game, match):
    """Regras que o P1 pode trocar agora: [(chave, rótulo, [(valor, texto)], valor atual)]."""
    from .matches import SoccerMatch
    from .soccer_assist import ASSIST_LEVELS, ASSIST_ORDER
    session = game.session
    if session is None or session.campaign or session.mode.startswith("treino"):
        return []
    rows = []
    if isinstance(match, SoccerMatch) and ai_class(match) is SoccerAI and not getattr(match, "penalties", False):
        rows.append(("partida", "PARTIDA", [(v, LENGTH_LABELS[v]) for v in config.SOCCER_LENGTHS],
                     session.soccer_length))
        rows.append(("assist", "ASSISTÊNCIA", [(v, ASSIST_LEVELS[v].label) for v in ASSIST_ORDER],
                     getattr(session, "assist", "media")))
    if any(s.cpu for s in session.slots):
        rows.append(("cpu", "CPU", [(v, DIFFICULTIES[v]["label"]) for v in DIFFICULTY_ORDER], session.difficulty))
    return rows


def change_rule(game, match, key, value):
    from .soccer_assist import ASSIST_LEVELS
    if key == "partida":
        set_length(match, value)
    elif key == "assist":
        game.session.assist = value
        match.assist = ASSIST_LEVELS[value]
    elif key == "cpu":
        set_difficulty(game, match, value)
