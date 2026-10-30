"""Regras da disputa de pênaltis (sem desenho): o canto e a força de quem bate, o pulo de quem
defende, o jeito de cada herói e a contagem das cobranças com morte súbita.

O gol é medido de -1 (trave esquerda, vista de quem bate) a 1 (trave direita) e de 0 (chão) a 1
(travessão). A mira é uma casa da grade 3x3: coluna -1, 0 ou 1 e linha 0 (baixo), 1 (meio) ou 2 (alto).
"""
import math
import random
from dataclasses import dataclass, field

REGULAR_KICKS = 5          # cobranças de cada time antes da morte súbita
POWER_FRAMES = 54          # quadros para a barrinha ir de 0 a 1 segurando CHUTE
RUN_FRAMES = 46            # corrida até a bola (cada herói muda)
DIVE_FRAMES = 16           # quadros para o goleiro chegar ao canto
EARLY_FRAMES = 12          # pular mais cedo que isso antes do chute aparece na TV e o batedor pode trocar
CHIP_FRAMES = 46           # a cavadinha vai devagar
SWEET = (0.5, 0.82)        # faixa verde da barrinha
OVER_LINE = 0.92           # passou disso, isola
BASE_RADIUS = 0.27         # alcance do goleiro (em unidades do gol)
STAND = (0.0, 0.45)        # onde o goleiro parado cobre
HACK_FRAMES = 18           # Hackear do Albeguinio: o pulo do goleiro trava nos últimos 0,3 s da corrida


def cell_point(col, row):
    """Centro de uma casa da grade 3x3, em unidades do gol."""
    return col * 0.7, 0.18 + row * 0.33


def aim_from_axis(ax, ay):
    """Direção do analógico (ou toque na grade do celular) → casa da grade. Sem direção: o meio."""
    col = 0 if abs(ax) < 0.4 else (1 if ax > 0 else -1)
    row = 1 if abs(ay) < 0.4 else (2 if ay < 0 else 0)
    return col, row


def axis_of(cell):
    """Casa da grade → direção do analógico (o caminho de volta, usado pela CPU e pelo celular)."""
    col, row = cell
    return float(col), float(1 - row)


# ── jeito de bater ───────────────────────────
@dataclass(frozen=True)
class KickStyle:
    name: str
    desc: str
    speed: float = 1.0       # velocidade da bola
    band: float = 1.0        # largura da faixa verde
    over: float = 0.0        # muda a linha do isola (negativo: isola mais fácil)
    max_power: float = 1.0   # até onde a barrinha sobe
    run: float = 1.0         # tamanho da corrida
    tell: float = 1.0        # sinal da corrida: 1 normal, 0 escondido, -1 mostra o lado errado
    deviation: float = 1.0   # quanto o chute torto desvia
    calm: float = 0.0        # 0..1: quanto ignora a pressão e a provocação
    trick: str = ""


KICK_STYLES = {
    "guerreiro": KickStyle("Pancada", "corre reto e enche o pé", speed=1.18, band=0.8, over=-0.05),
    "atirador": KickStyle("Chute Certeiro", "corrida curta e calma", speed=0.88, band=1.35, run=0.8),
    "tanque": KickStyle("Bomba no meio", "só bate no meio, alto ou baixo", speed=1.1, trick="meio"),
    "ninja": KickStyle("Fumaça", "some numa fumaça no meio da corrida", tell=0.0, max_power=0.86, trick="fumaca"),
    "velocista": KickStyle("Arrancada", "corrida longa e rapidíssima", band=0.78, run=0.6),
    "aryel": KickStyle("Grau de moto", "chega empinando a moto e desce para chutar", tell=0.0, band=0.8,
                       trick="moto"),
    "aryel_corrompido": KickStyle("Bomba Sombria", "a bola vira bomba e pode entrar no rebote", band=0.8,
                                  trick="bomba"),
    "fantasma": KickStyle("Bola Fantasma", "a bola some no meio do caminho", speed=0.86, trick="some"),
    "tita": KickStyle("Pisão", "pisão gigante que treme a tela antes do chute", run=1.3, trick="pisao"),
    "pirata": KickStyle("Gancho", "a bola sai para um lado e curva para o outro", trick="gancho"),
    "geada": KickStyle("Gramado de gelo", "o pulo do goleiro sai mais curto", speed=0.86, trick="gelo"),
    "faisca": KickStyle("Drible Mágico", "a bola troca de canto uma vez no ar", speed=0.84, trick="troca"),
    "trovao": KickStyle("Chute Trovão", "a bola vira raio", speed=1.32, over=-0.08, trick="raio"),
    "ginga": KickStyle("Paradinha", "pulinho antes da bola, esperando o goleiro", run=1.25, trick="paradinha"),
    "matador": KickStyle("Frieza", "corrida sem pressa, nunca treme na decisiva", calm=1.0),
    "cauanzera": KickStyle("De calcanhar", "de costas para o gol: a corrida mostra o lado errado", speed=0.82,
                           tell=-1.0, trick="calcanhar"),
    "albeguinio": KickStyle("Hackear", "trava o pulo do goleiro por 0,3 s, uma vez na disputa", trick="hack"),
    "borba": KickStyle("Chute de exo", "força enorme: na trave ela entorta e pode entrar", speed=1.16, run=1.4,
                       trick="exo"),
    "paredao": KickStyle("De bico", "bate como goleiro", band=0.6, deviation=1.8),
    "borba_corrompido": KickStyle("Pulso Sombrio", "exo com veios roxos: força enorme, na trave ela entorta",
                                  speed=1.18, run=1.4, trick="exo"),
}


# ── jeito de defender ────────────────────────
@dataclass(frozen=True)
class SaveStyle:
    name: str
    desc: str
    radius: float = 1.0      # alcance
    dive: float = 1.0        # velocidade do pulo (chega antes no canto)
    late: float = 1.0        # tolerância de pular depois do chute
    high: float = 1.0        # alcance nos cantos altos
    low: float = 1.0         # alcance nos cantos baixos
    center: float = 1.0      # alcance no meio
    read: float = 1.0        # lê melhor o sinal da corrida
    hold: str = ""           # "segura" (nunca rebote), "espalma" (sempre rebote)
    rebound: float = 0.15    # chance da bola espalmada entrar
    calm: float = 0.0        # ignora provocação e tremor de tela
    shake: float = 1.0       # quanto a provocação dele treme a barrinha de quem bate
    trick: str = ""


SAVE_STYLES = {
    "guerreiro": SaveStyle("Escudo", "a defesa nunca vira rebote", radius=0.88, hold="segura", rebound=0.0),
    "atirador": SaveStyle("Olho de mira", "vê o sinal da corrida mais nítido", read=1.4, dive=0.8),
    "tanque": SaveStyle("Muralha do Gol", "meio alto e baixo sempre defende", center=1.5, high=0.7),
    "ninja": SaveStyle("Clone", "deixa um clone no meio que pega a cavadinha", trick="clone"),
    "velocista": SaveStyle("Reflexo", "pode pular mais tarde que todos", late=1.7, radius=0.85),
    "aryel": SaveStyle("Sai de moto", "fecha os cantos altos, mas o rasteiro passa", high=1.3, low=0.75),
    "aryel_corrompido": SaveStyle("Braços de sombra", "alcance maior nos cantos altos", high=1.35, low=0.8),
    "fantasma": SaveStyle("Atravessa o pulo", "troca de lado no ar uma vez", hold="espalma", rebound=0.2,
                          trick="troca"),
    "tita": SaveStyle("Gigante", "ocupa boa parte do gol", radius=1.2, dive=0.75, low=0.8),
    "pirata": SaveStyle("Gancho", "puxa a bola que passa perto, uma vez na disputa", trick="gancho"),
    "geada": SaveStyle("Congelar", "a bola perde velocidade perto dele", late=1.4, trick="gelo"),
    "faisca": SaveStyle("Faísca de aviso", "o sinal da corrida brilha um instante", read=1.3, radius=0.88),
    "trovao": SaveStyle("Pulo-relâmpago", "chega no canto antes de todos, mas sempre espalma", dive=1.6,
                        hold="espalma"),
    "ginga": SaveStyle("Dança na linha", "a barrinha de quem bate treme mais", shake=2.0),
    "matador": SaveStyle("Frieza", "não liga para provocação nem tremor de tela", calm=1.0),
    "cauanzera": SaveStyle("Voadora", "o pulo mais longo do jogo, mas perde o rebote", radius=1.15, rebound=0.35),
    "albeguinio": SaveStyle("Hackear", "anula a troca de canto do batedor, uma vez", trick="hack"),
    "borba": SaveStyle("Exoesqueleto", "segura chute forte sem espalmar", hold="segura", dive=0.8),
    "borba_corrompido": SaveStyle("Blindagem", "segura chute forte e alcança mais embaixo", hold="segura", dive=0.8,
                                  low=1.2),
    "paredao": SaveStyle("Antecipação", "o melhor alcance e a melhor leitura", radius=1.2, read=1.5, late=1.2),
}


def kick_style(key):
    return KICK_STYLES.get(key, KickStyle("Chute", "bate normal"))


def save_style(key):
    return SAVE_STYLES.get(key, SaveStyle("Goleiro", "defende normal"))


def sweet_band(style, cell):
    """Faixa verde (lo, hi) e linha do isola para essa mira. Mirar no ângulo deixa a faixa menor."""
    lo, hi = SWEET
    mid, half = (lo + hi) / 2, (hi - lo) / 2 * style.band
    col, row = cell
    if row == 2 and col != 0:
        half *= 0.72
    over = OVER_LINE + style.over
    return max(0.2, mid - half), min(over - 0.02, mid + half), over


# ── o chute ──────────────────────────────────
@dataclass
class Shot:
    """O que acontece com a bola depois do contato."""
    x: float
    y: float
    frames: int              # quadros do pé até a linha do gol
    kind: str = "alvo"       # alvo, isolou, fora, trave
    chip: bool = False       # cavadinha
    swap_at: int = 0         # Drible Mágico: no quadro em que a bola troca de canto
    from_x: float = 0.0      # Gancho: de onde a curva começa (lado errado)
    power: float = 0.0
    cell: tuple = (0, 1)
    note: str = ""           # o que aconteceu de especial (para a narração)


def make_shot(cell, power, style, rng, decisive=False, chip=False, early_dive=None, hacked=False):
    """Calcula o chute no quadro do contato. early_dive é o canto (col, linha) para onde o goleiro já
    pulou antes do chute (a Paradinha e o Drible usam isso); hacked: o Albeguinio goleiro anulou a troca."""
    if chip:
        return Shot(0.0, 0.62, CHIP_FRAMES, chip=True, power=power, cell=(0, 1))
    col, row = cell
    note = ""
    if style.trick == "meio":
        col = 0
    if style.trick == "paradinha" and not hacked:
        if early_dive is not None:
            # o goleiro se mexeu: toca devagar no outro canto
            other = -early_dive[0] if early_dive[0] else rng.choice((-1, 1))
            col, row, power, note = other, 0, (SWEET[0] + SWEET[1]) / 2, "paradinha"
        else:
            power *= 0.72                 # esperou e o goleiro não caiu: o chute sai fraco
    power = min(power, style.max_power)
    lo, hi, over = sweet_band(style, (col, row))
    x, y = cell_point(col, row)
    dev = 0.0
    if power > over:
        return Shot(x * 0.6 + rng.uniform(-0.2, 0.2), 1.35 + rng.uniform(0, 0.4), 24, "isolou", power=power,
                    cell=(col, row))
    if power < lo:
        k = (lo - power) / lo
        x *= 1 - 0.6 * k
        y += (0.35 - y) * 0.6 * k
    elif power > hi:
        dev = (power - hi) / max(0.01, over - hi) * 0.32
    if decisive:
        dev += 0.12 * (1 - style.calm)
    dev *= style.deviation
    if dev:
        x += rng.uniform(-1, 1) * dev * 0.7
        y += rng.uniform(0.2, 1.0) * dev
    frames = (34 - 16 * power) / style.speed
    shot = Shot(x, y, max(10, round(frames)), power=power, cell=(col, row), note=note)
    if style.trick == "troca" and not hacked and col:
        shot.swap_at = shot.frames // 2
        shot.x = -x
        shot.frames = round(shot.frames * 1.1)
    if style.trick == "gancho" and not hacked and col:
        shot.from_x = x * 1.35
        shot.x = x * 0.86             # só curva para dentro
    _classify(shot)
    return shot


def _classify(shot):
    ax, y = abs(shot.x), shot.y
    if ax > 1.05 or y > 1.06:
        shot.kind = "isolou" if y > 1.06 and ax <= 1.05 else "fora"
    elif ax > 0.93 or y > 0.95:
        shot.kind = "trave"


# ── o pulo ───────────────────────────────────
@dataclass
class Dive:
    cell: tuple = None       # None: ficou parado no meio
    t: int = 0               # quadro do pulo em relação ao chute (negativo: antes)
    switched: bool = False   # Fantasma trocou de lado no ar


def keeper_point(dive, shot, style, kicker=None):
    """Onde o goleiro está quando a bola chega."""
    if dive is None or dive.cell is None:
        return STAND, 0.0
    dive_frames = DIVE_FRAMES / style.dive
    if kicker is not None and kicker.trick == "gelo":
        dive_frames *= 1.25           # gramado de gelo: o pulo sai mais curto
    start = dive.t + (4 if dive.switched else 0)
    late = max(0, start)
    reach_time = shot.frames - start
    if late:
        reach_time = shot.frames - late / style.late
    progress = max(0.0, min(1.0, reach_time / dive_frames))
    tx, ty = cell_point(*dive.cell)
    return (STAND[0] + (tx - STAND[0]) * progress, STAND[1] + (ty - STAND[1]) * progress), progress


@dataclass
class Outcome:
    goal: bool
    result: str              # gol, defesa, espalmou, rebote, trave, fora, isolou, cavadinha, segurou
    text: str
    used: tuple = ()         # truques de uma vez só gastos aqui ("gancho", "hack")


def resolve(shot, dive, kicker, keeper, rng, keeper_tricks=()):
    """Resultado da cobrança quando a bola chega no gol."""
    if shot.kind == "isolou":
        return Outcome(False, "isolou", "ISOLOU!")
    if shot.kind == "fora":
        return Outcome(False, "fora", "PRA FORA!")
    dived = dive is not None and dive.cell is not None
    if shot.chip:
        moved = dived and dive.cell[0] != 0 and dive.t < shot.frames - 6
        if keeper.trick == "clone":
            return Outcome(False, "segurou", "O CLONE PEGOU!")
        if moved:
            return Outcome(True, "cavadinha", "CAVADINHA!")
        return Outcome(False, "segurou", "SEGUROU A CAVADINHA")
    if shot.kind == "trave":
        if kicker.trick == "exo" and rng.random() < 0.5:
            return Outcome(True, "gol", "ENTORTOU A TRAVE!")
        return Outcome(False, "trave", "NA TRAVE!")
    (kx, ky), progress = keeper_point(dive, shot, keeper, kicker)
    r = BASE_RADIUS * keeper.radius
    col, row = round(shot.x / 0.7) if abs(shot.x) > 0.35 else 0, (2 if shot.y > 0.67 else 0 if shot.y < 0.34 else 1)
    if row == 2 and col:
        r *= keeper.high
    if row == 0 and col:
        r *= keeper.low
    if col == 0:
        r *= keeper.center
    if keeper.trick == "gancho" and dived and dive.t < 0 and kicker.trick == "gancho":
        pass                          # ganchos se anulam
    elif kicker.trick == "gancho" and dived and dive.t < 0 and shot.from_x:
        r *= 0.75                     # pulou cedo e foi enganado pela curva
    stand_tall = 1.0 if dived else 1.5
    d = math.hypot((shot.x - kx) / r, (shot.y - ky) / (r * 1.3 * stand_tall))
    used = ()
    if d >= 1.0 and keeper.trick == "gancho" and "gancho" not in keeper_tricks and dived and d < 2.0:
        d, used = 0.9, ("gancho",)
    if d >= 1.0:
        if dived and progress < 1 and d < 1.6:
            return Outcome(True, "gol", "NÃO ALCANÇOU!")
        return Outcome(True, "gol", _goal_text(shot))
    strong = shot.power > 0.78 or kicker.speed > 1.15
    catch = d < 0.65 and not (strong and keeper.hold != "segura")
    if keeper.hold == "espalma":
        catch = False
    if keeper.hold == "segura" or catch:
        return Outcome(False, "defesa", "QUE DEFESA!" if not used else "PUXOU NO GANCHO!", used)
    rebound = keeper.rebound + (0.35 if kicker.trick == "bomba" else 0.0)
    if keeper.trick == "gelo" and kicker.trick in ("raio", "exo"):
        rebound += 0.3                # o gelo não segura raio nem exo
    if rng.random() < rebound:
        return Outcome(True, "rebote", "ENTROU NO REBOTE!", used)
    return Outcome(False, "espalmou", "ESPALMOU!", used)


def _goal_text(shot):
    if shot.note == "paradinha":
        return "PARADINHA!"
    if shot.y > 0.7 and abs(shot.x) > 0.5:
        return "NO ÂNGULO!"
    if abs(shot.x) > 0.5:
        return "NO CANTINHO!"
    return "NO MEIO!"


# ── CPU ──────────────────────────────────────
CPU_READ = {"facil": 0.2, "normal": 0.38, "dificil": 0.55}
CPU_AIM = {"facil": 0.09, "normal": 0.055, "dificil": 0.03}


def tell_side(cell, style):
    """Lado que a corrida mostra (o ombro abrindo): -1, 0 ou 1. None: sem sinal."""
    if style.tell == 0:
        return None
    side = cell[0]
    return -side if style.tell < 0 else side


def cpu_kick(style, difficulty, rng):
    """Mira e força da CPU batendo: (casa, força, cavadinha)."""
    if rng.random() < 0.06:
        return (0, 1), 0.5, True
    col = rng.choice((-1, -1, 0, 1, 1))
    row = rng.choice((0, 0, 1, 2))
    if style.trick == "meio":
        col = 0
    lo, hi, _ = sweet_band(style, (col, row))
    power = rng.uniform(lo + 0.04, hi - 0.02) + rng.gauss(0, CPU_AIM.get(difficulty, 0.055))
    return (col, row), max(0.2, min(style.max_power, power)), False


def cpu_dive(kick_cell, kicker, keeper, difficulty, rng, history=()):
    """Pulo da CPU no gol: lê o sinal da corrida (nunca o canto escolhido de verdade) ou chuta um lado.
    history é a colinha: os cantos que esse batedor já escolheu na disputa."""
    side = tell_side(kick_cell, kicker)
    read = CPU_READ.get(difficulty, 0.38) * keeper.read
    if kicker.trick in ("some", "pisao") and keeper.calm < 1:
        read *= 0.6
    t = rng.randint(-8, 3)
    if side is not None and rng.random() < read:
        col = side
    elif history and rng.random() < 0.35:
        col = rng.choice([c for c, _ in history])
    else:
        col = rng.choice((-1, -1, 0, 1, 1))
    if col == 0 and rng.random() < 0.6:
        return Dive(None, t)
    return Dive((col, rng.choice((0, 1, 1, 2))), t)


# ── a disputa ────────────────────────────────
@dataclass
class Shootout:
    """5 cobranças alternadas e depois morte súbita. orders[time] é a fila de quem bate (repete
    quando acaba); keepers[time] são os goleiros do time (revezam a cada cobrança)."""
    orders: list
    keepers: list
    first: int = 0
    kicks: list = field(default_factory=lambda: [[], []])
    corners: dict = field(default_factory=dict)      # batedor → casas já escolhidas (a colinha)

    @property
    def team(self):
        """Time que bate agora."""
        a, b = len(self.kicks[self.first]), len(self.kicks[1 - self.first])
        return self.first if a == b else 1 - self.first

    @property
    def number(self):
        """Número da cobrança do time da vez (1, 2, 3...)."""
        return len(self.kicks[self.team]) + 1

    @property
    def sudden_death(self):
        return self.number > REGULAR_KICKS

    def kicker(self):
        order = self.orders[self.team]
        return order[len(self.kicks[self.team]) % len(order)]

    def keeper(self):
        keepers = self.keepers[1 - self.team]
        return keepers[len(self.kicks[self.team]) % len(keepers)]

    def goals(self, team):
        return sum(self.kicks[team])

    def record(self, goal, cell=None, who=None):
        if who is not None and cell is not None:
            self.corners.setdefault(who, []).append(cell)
        self.kicks[self.team].append(bool(goal))

    @staticmethod
    def _winner(kicks):
        a, b = sum(kicks[0]), sum(kicks[1])
        na, nb = len(kicks[0]), len(kicks[1])
        if na <= REGULAR_KICKS and nb <= REGULAR_KICKS:
            if a > b + (REGULAR_KICKS - nb):
                return 0
            if b > a + (REGULAR_KICKS - na):
                return 1
            if na < REGULAR_KICKS or nb < REGULAR_KICKS:
                return None
        if na == nb and a != b:
            return 0 if a > b else 1
        return None

    @property
    def winner(self):
        return self._winner(self.kicks)

    def decisive(self):
        """A cobrança da vez decide: perder (ou fazer) acaba a disputa."""
        team = self.team
        for goal in (True, False):
            kicks = [list(self.kicks[0]), list(self.kicks[1])]
            kicks[team].append(goal)
            if self._winner(kicks) is not None:
                return True
        return False
