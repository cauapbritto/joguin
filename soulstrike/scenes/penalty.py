"""Disputa de pênaltis com visão de frente: a câmera atrás de quem bate, o gol grande e o goleiro
no meio. As regras ficam em soulstrike/penalty.py; aqui ficam o desenho, a entrada e os extras
(ordem dos batedores, colinha, catimba, pressão, narração, comemorações e estatísticas).

A mira nunca aparece na TV: no teclado e no controle o canto é a direção do analógico na hora do
chute; no celular, quem bate toca numa grade 3x3 que só ele vê.
"""
import math
import random
from dataclasses import dataclass, field

import pygame

from .. import config, penalty as P, progress, theme
from ..data import CHARACTERS
from ..matches import Result
from ..net.remote import hub
from .base import Scene

W, H = config.SCREEN_W, config.SCREEN_H
GOAL_L, GOAL_R, BAR_Y, LINE_Y = 250, 710, 150, 318
SPOT = (W // 2, 466)
UP = 150                    # quanto a câmera sobe atrás da bola isolada
KEEPER_SCALE = 1.5          # as folhas já vêm 2x: o goleiro fica 3x e quem bate 5x
KICKER_SCALE = 2.5
RESULT_FRAMES = 170
SLOWMO_TAIL = 8             # últimos quadros do voo em câmera lenta
CATIMBA_FRAMES = 80
TEAM = theme.TEAM_COLORS
STATS_KEY = "penaltis"

STANDALONE_MODES = ("penaltis", "treino_penaltis", "desafio_goleiro")

# comemoração de cada herói: (frase, efeito, cor)
CELEBRATIONS = {
    "guerreiro": ("BATE A ESPADA NO ESCUDO!", "faisca", (240, 240, 250)),
    "atirador": ("SOPRA O DEDO", "fumaca", (200, 200, 210)),
    "tanque": ("BATE NO PEITO!", "tremor", (200, 170, 120)),
    "ninja": ("SUMIU NA FUMAÇA", "fumaca", (120, 110, 140)),
    "velocista": ("VOLTA OLÍMPICA!", "rastro", (250, 220, 90)),
    "aryel": ("GRAU NA FRENTE DA TORCIDA!", "poeira", (190, 160, 120)),
    "aryel_corrompido": ("HA HA HA...", "sombra", (150, 80, 200)),
    "fantasma": ("ACENA DE DENTRO DO GOL", "sombra", (200, 220, 255)),
    "tita": ("O ESTÁDIO TREMEU!", "tremor", (230, 200, 150)),
    "pirata": ("FINCOU A BANDEIRA!", "bandeira", (30, 30, 36)),
    "geada": ("DESLIZE NO GELO!", "gelo", (170, 220, 255)),
    "faisca": ("ESTRELINHAS!", "estrelas", (255, 230, 120)),
    "trovao": ("CAIU UM RAIO!", "raio", (255, 240, 120)),
    "ginga": ("DANCINHA!", "estrelas", (240, 120, 200)),
    "matador": ("MÃO NO OUVIDO PARA A TORCIDA", "fumaca", (230, 226, 206)),
    "cauanzera": ("CAMBALHOTA!", "poeira", (190, 160, 120)),
    "albeguinio": ("GOL.EXE", "telao", (110, 230, 140)),
    "borba": ("VAPOR DO EXO!", "vapor", (220, 220, 230)),
    "paredao": ("ABRAÇA A BOLA E ROLA!", "estrelas", (228, 170, 76)),
}
NAME = {c.key: c.name.upper() for c in CHARACTERS}


@dataclass(eq=False)
class Taker:
    """Um jogador na disputa (bate e defende)."""
    key: str
    team: int
    slot: int = None
    cpu: bool = True
    sprites: object = None
    fighter: object = None          # o lutador da partida, quando a disputa vem depois do jogo
    goals: int = 0
    kicks: int = 0
    saves: int = 0
    faced: int = 0
    catimbas: int = 0
    yellows: int = 0

    @property
    def name(self):
        return NAME.get(self.key, self.key.upper())

    @property
    def label(self):
        return "CPU" if self.cpu else f"P{self.slot}"


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: tuple
    life: int
    size: int = 4
    gravity: float = 0.2
    age: int = 0

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.age += 1
        return self.age < self.life


@dataclass
class Shout:
    """Frase da narração que entra batendo e tremendo."""
    text: str
    color: tuple = theme.BONE
    size: int = theme.L
    y: int = 210
    age: int = 0
    life: int = 110
    sub: str = ""


@dataclass
class Kick:
    """Estado da cobrança em andamento."""
    kicker: Taker
    keeper: Taker
    decisive: bool = False
    power: float = 0.0
    charging: bool = False
    chip: bool = False
    cell: tuple = (0, 1)
    run: int = 0
    contact_at: int = 0          # quadro (de self.t) do contato
    dive: P.Dive = None
    dive_frame: int = None       # quadro (de self.t) em que o goleiro pulou
    shot: P.Shot = None
    outcome: P.Outcome = None
    flight: int = 0
    cpu_plan: dict = field(default_factory=dict)
    shake: float = 0.0           # provocação do goleiro: a barrinha treme
    hacked_keeper: bool = False  # Albeguinio batendo: pulo travado no fim da corrida
    keeper_x: float = 0.0
    catimba: int = 0             # quadros da catimba em andamento
    card: bool = False           # a catimba virou amarelo
    provoking: bool = False
    retake: bool = False


def taker_sprites(assets, key, team):
    return assets.kit_sprites(key, team)


def _scaled(img, factor):
    return pygame.transform.scale(img, (round(img.get_width() * factor), round(img.get_height() * factor)))


def goal_to_screen(x, y):
    return W // 2 + x * (GOAL_R - GOAL_L) / 2, LINE_Y - y * (LINE_Y - BAR_Y)


class PenaltyScene(Scene):
    """Disputa (mode="penaltis"), treino sem fim (mode="treino_penaltis") ou desafio do goleiro."""

    music = None
    phase = "penalty"
    show_cursor = False

    def __init__(self, game, teams, mode="penaltis", difficulty="normal", match=None, seed=None):
        super().__init__(game)
        self.mode = mode
        self.difficulty = difficulty
        self.match = match
        self.rng = random.Random(seed)
        self.teams = teams
        for team in teams:
            for t in team:
                if t.sprites is None:
                    t.sprites = taker_sprites(self.assets, t.key, t.team)
        self.orders = [self._default_order(team) for team in teams]
        self.shootout = None
        self.kick = None
        self.state = "ordem" if mode == "penaltis" and any(len(t) > 1 for t in teams) else "entrada"
        self.t = 0
        self.cursor = [0, 0]
        self.picked = [None, None]
        self.ready = [all(t.cpu for t in team) or len(team) < 2 for team in teams]
        self.used = {0: set(), 1: set()}     # truques de uma vez na disputa, por time
        self.shouts = []
        self.particles = []
        self.flashes = []
        self.bulge = None                    # (x, y, força) da rede estufando
        self.cam_up = 0.0
        self.shake = 0
        self.records = []
        self.count_t = 0
        self.paused = False
        self.challenge = {"round": 1, "streak": 0, "lives": 3, "best": 0} if mode == "desafio_goleiro" else None
        self.replaying = False
        self._stands = None
        self._grass = None
        if self.state != "ordem":
            self._begin()

    # ── montagem ─────────────────────────────
    @staticmethod
    def _default_order(team):
        """Fila das 5 cobranças: os jogadores se revezam, e o melhor batedor fecha a 5ª."""
        if len(team) == 1:
            return [team[0]] * P.REGULAR_KICKS
        best = max(team, key=lambda t: P.kick_style(t.key).calm + P.kick_style(t.key).band)
        order = [team[i % len(team)] for i in range(P.REGULAR_KICKS)]
        if order[-1] is not best:
            i = order.index(best)
            order[i], order[-1] = order[-1], order[i]
        return order

    def _begin(self):
        self.shootout = P.Shootout(self.orders, [list(team) for team in self.teams],
                                   first=self.rng.randrange(2) if self.mode == "penaltis" else 0)
        if self.challenge:
            self.shootout.first = 1           # no desafio a CPU sempre bate
        self._next_kick()

    def enter(self):
        super().enter()
        self.assets.stop_music(600)
        self._publish()

    def phone_mode(self):
        return "soccer"

    def hud_layout(self):
        return "soccer"

    def active_slots(self):
        return tuple(t.slot for team in self.teams for t in team if not t.cpu)

    @property
    def humans(self):
        return [t for team in self.teams for t in team if not t.cpu]

    def _input(self, taker):
        return self.game.inputs[taker.slot] if taker is not None and not taker.cpu else None

    # ── cobrança ─────────────────────────────
    def _next_kick(self):
        s = self.shootout
        if self.challenge:
            # desafio: a CPU sempre bate e o jogador sempre defende
            kicker = self.teams[1][(sum(len(k) for k in s.kicks)) % len(self.teams[1])]
            keeper = self.teams[0][(sum(len(k) for k in s.kicks)) % len(self.teams[0])]
        else:
            kicker, keeper = s.kicker(), s.keeper()
        decisive = s.decisive() if self.mode == "penaltis" else False
        self.kick = Kick(kicker, keeper, decisive=decisive)
        if not kicker.cpu:
            self.game.inputs[kicker.slot].set_layout("soccer")
        if not keeper.cpu:
            self.game.inputs[keeper.slot].set_layout("soccer")
        style = P.kick_style(kicker.key)
        self.kick.run = round(P.RUN_FRAMES * style.run)
        if kicker.cpu:
            diff = self._cpu_level()
            cell, power, chip = P.cpu_kick(style, diff, self.rng)
            self.kick.cpu_plan = {"cell": cell, "power": power, "chip": chip,
                                  "wait": self.rng.randint(40, 90)}
        self.state = "entrada"
        self.t = 0
        self.cam_up = 0
        self.bulge = None
        self.celebration = None
        self.assets.play("apito", 0.35)
        self._publish()

    def _cpu_level(self):
        if self.challenge:
            return ("facil", "normal", "dificil")[min(2, self.challenge["round"] - 1)]
        return self.difficulty

    def _keeper_style(self):
        return P.save_style(self.kick.keeper.key)

    def _kicker_style(self):
        return P.kick_style(self.kick.kicker.key)

    def _team_used(self, taker, trick):
        return trick in self.used[taker.team]

    # ── atualização ──────────────────────────
    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.paused or self.state == "fim":
                self._leave()
            else:
                self.paused = True
                self.sfx("click", 0.4)
        elif self.paused and event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.paused = False

    def update(self):
        super().update()
        if self.paused:
            if any(self.game.inputs[s].pressed("attack") for s in self.active_slots()):
                self.paused = False
            return
        if any(self.game.inputs[s].pressed("pause") for s in self.active_slots()):
            self.paused = True
            return
        self.particles = [p for p in self.particles if p.update()]
        for s in self.shouts:
            s.age += 1
        self.shouts = [s for s in self.shouts if s.age < s.life]
        self.flashes = [(x, y, a + 1) for x, y, a in self.flashes if a < 12]
        if self.shake:
            self.shake -= 1
        if self.bulge:
            bx, by, amp = self.bulge
            self.bulge = (bx, by, amp * 0.94) if amp > 0.05 else None
        getattr(self, "_update_" + self.state)()

    def _update_ordem(self):
        """Antes da disputa, cada time arruma a fila das 5 cobranças."""
        self.t += 1
        for team in (0, 1):
            if self.ready[team]:
                continue
            for taker in self.teams[team]:
                inp = self._input(taker)
                if inp is None:
                    continue
                if inp.pressed("left"):
                    self.cursor[team] = (self.cursor[team] - 1) % P.REGULAR_KICKS
                    self.sfx("click", 0.3)
                if inp.pressed("right"):
                    self.cursor[team] = (self.cursor[team] + 1) % P.REGULAR_KICKS
                    self.sfx("click", 0.3)
                if inp.pressed("attack"):
                    self._pick_order(team)
                if inp.pressed("special") or inp.pressed("confirm") and not inp.pressed("attack"):
                    self.ready[team] = True
                    self.sfx("confirm", 0.5)
        if all(self.ready) and self.t > 20:
            self._begin()

    def _pick_order(self, team):
        i = self.cursor[team]
        if self.picked[team] is None:
            self.picked[team] = i
            self.sfx("select", 0.4)
            return
        j = self.picked[team]
        order = self.orders[team]
        order[i], order[j] = order[j], order[i]
        self.picked[team] = None
        self.sfx("confirm", 0.4)

    def _update_entrada(self):
        """Quem bate sai da fila e caminha até a bola; o goleiro lê a colinha."""
        self.t += 1
        if self.t >= 60:
            self.state = "mira"
            self.t = 0
            if self.kick.decisive:
                self._shout("COBRANÇA DECISIVA", theme.BONE, theme.M, y=230, sub="SE PERDER, ACABOU")
                self.assets.play("coracao", 0.5)

    def _update_mira(self):
        k = self.kick
        self.t += 1
        self._keeper_waiting()
        if k.catimba:
            self._update_catimba()
            return
        kstyle = self._kicker_style()
        inp = self._input(k.kicker)
        if inp is not None:
            if inp.pressed("special") and not k.charging:
                self._start_run(chip=True)
                return
            if inp.held("attack"):
                k.charging = True
                k.power = min(1.0, k.power + 1 / P.POWER_FRAMES)
            elif k.charging:
                self._start_run()
                return
        else:
            plan = k.cpu_plan
            if plan["chip"] and self.t > plan["wait"]:
                self._start_run(chip=True)
                return
            if self.t > plan["wait"]:
                k.charging = True
                k.power = min(1.0, k.power + 1 / P.POWER_FRAMES)
                if k.power >= plan["power"]:
                    self._start_run()
                    return
        k.power = min(k.power, kstyle.max_power)

    def _keeper_waiting(self):
        """Antes do chute o goleiro anda na linha, provoca (ATACAR) ou faz catimba (MARCAR)."""
        k = self.kick
        inp = self._input(k.keeper)
        keeper = self._keeper_style()
        kicker = self._kicker_style()
        provoking = False
        if inp is not None:
            ax, _ = inp.axis()
            k.keeper_x = max(-60.0, min(60.0, k.keeper_x + ax * 2.2))
            provoking = inp.held("attack")
            if inp.pressed("mark") and self.state == "mira" and not k.charging and not k.catimba:
                self._catimba()
        elif self.state == "mira":
            k.keeper_x += math.sin(self.ticks * 0.05) * 0.8
            provoking = (self.ticks // 40) % 3 == 0
        k.provoking = provoking
        if provoking and k.charging:
            k.shake = 0.05 * keeper.shake * (1 - kicker.calm)
        else:
            k.shake *= 0.9

    def _catimba(self):
        """O goleiro demora, vai até quem bate e encara. Na 3ª leva amarelo; no 2º amarelo, a
        cobrança é repetida se ele defender."""
        k = self.kick
        keeper = k.keeper
        keeper.catimbas += 1
        k.catimba = CATIMBA_FRAMES
        self._shout("CATIMBA!", (250, 214, 60), theme.L)
        self.assets.play("apito", 0.45)
        if keeper.catimbas % 3 == 0:
            keeper.yellows += 1
            k.card = True
            self.assets.play("ooh", 0.5)
            if keeper.yellows >= 2:
                k.retake = True
                self._shout("2º AMARELO!", (250, 214, 60), theme.M, y=250, sub="SE DEFENDER, VAI REPETIR")
            else:
                self._shout("AMARELO!", (250, 214, 60), theme.M, y=250, sub="NA PRÓXIMA, A COBRANÇA É REPETIDA")
        k.shake = 0.06

    def _update_catimba(self):
        k = self.kick
        k.catimba -= 1

    def _start_run(self, chip=False):
        k = self.kick
        k.chip = chip
        k.charging = False
        jitter = self.rng.uniform(-1, 1) * k.shake
        k.power = max(0.0, min(1.0, k.power + jitter))
        style = self._kicker_style()
        if style.trick == "hack" and not self._team_used(k.kicker, "hack"):
            k.hacked_keeper = True
            self.used[k.kicker.team].add("hack")
            self._shout("HACKEADO!", (110, 230, 140), theme.M, y=250, sub="O PULO DO GOLEIRO TRAVA NO FIM")
        if style.trick == "paradinha" and not chip:
            k.run = round(P.RUN_FRAMES * style.run) + 14
        self.state = "corrida"
        self.t = 0
        k.contact_at = k.run
        self._shout("LÁ VAI ELE...", theme.BONE, theme.M, y=120, life=60)
        self.assets.play("torcida_abafa", 0.4)

    def _update_corrida(self):
        k = self.kick
        self.t += 1
        self._keeper_dive_input()
        self._kicker_aim()
        style = self._kicker_style()
        if style.trick == "pisao" and self.t == k.run - 10:
            if self._keeper_style().calm < 1:
                self.shake = 14
            self.assets.play("passo_pesado", 0.6)
        if style.trick == "fumaca" and self.t == k.run // 2:
            self._burst(W // 2 - 60, 470, (120, 110, 140), 26, speed=3, gravity=-0.05, size=8)
        if self.t >= k.run:
            self._contact()

    def _kicker_aim(self):
        """O canto segue o analógico até o contato. A CPU pode trocar se o goleiro pular cedo."""
        k = self.kick
        inp = self._input(k.kicker)
        if inp is not None:
            k.cell = P.aim_from_axis(*inp.axis())
            return
        k.cell = k.cpu_plan["cell"]
        if k.dive_frame is not None and k.dive is not None and k.dive.cell and not k.cpu_plan.get("swapped"):
            k.cpu_plan["swapped"] = True
            if self.rng.random() < 0.6 and k.dive.cell[0] == k.cell[0]:
                col = -k.cell[0] if k.cell[0] else self.rng.choice((-1, 1))
                k.cpu_plan["cell"] = (col, k.cell[1])
                k.cell = k.cpu_plan["cell"]

    def _keeper_dive_input(self):
        k = self.kick
        now = self.t if self.state == "corrida" else k.contact_at + k.flight
        rel = now - k.contact_at
        if k.hacked_keeper and -P.HACK_FRAMES <= rel < 0:
            return                                  # Hackear: o pulo está travado
        inp = self._input(k.keeper)
        if inp is not None:
            if inp.pressed("dodge"):
                cell = P.aim_from_axis(*inp.axis())
                cell = None if cell == (0, 1) else cell
                if k.dive is None:
                    k.dive = P.Dive(cell, rel)
                    k.dive_frame = now
                    self.assets.play("dash", 0.4)
                elif (self._keeper_style().trick == "troca" and not k.dive.switched and cell != k.dive.cell
                      and self.state == "voo"):
                    k.dive.cell, k.dive.switched = cell, True      # Fantasma troca de lado no ar
            return
        # CPU: decide quando a corrida mostra o sinal e pula na hora planejada
        if "dive" not in k.cpu_plan and self.state == "corrida" and self.t >= int(k.run * 0.7):
            history = self.shootout.corners.get(id(k.kicker), ()) if self.shootout else ()
            k.cpu_plan["dive"] = P.cpu_dive(k.cell, self._kicker_style(), self._keeper_style(),
                                            self._cpu_level(), self.rng, history)
        plan = k.cpu_plan.get("dive")
        if plan is not None and k.dive is None and rel >= plan.t:
            k.dive = P.Dive(plan.cell, rel)
            k.dive_frame = now

    def _contact(self):
        k = self.kick
        kstyle, sstyle = self._kicker_style(), self._keeper_style()
        early = k.dive.cell if k.dive is not None and k.dive.t < -P.EARLY_FRAMES and k.dive.cell else None
        if k.dive is not None and k.dive.t < -P.EARLY_FRAMES and k.dive.cell is None:
            early = (0, 1)
        hacked = False
        if (sstyle.trick == "hack" and kstyle.trick in ("paradinha", "troca", "gancho")
                and not self._team_used(k.keeper, "hack")):
            hacked = True
            self.used[k.keeper.team].add("hack")
            self._shout("HACK DO GOLEIRO!", (110, 230, 140), theme.M, y=250, sub="SEM TROCA DE CANTO")
        k.shot = P.make_shot(k.cell, k.power, kstyle, self.rng, decisive=k.decisive, chip=k.chip,
                             early_dive=early, hacked=hacked)
        k.flight = 0
        self.state = "voo"
        self.shake = 6 if k.shot.power > 0.75 else 3
        self.assets.play("chute", 0.6)
        if kstyle.trick == "raio":
            self.assets.play("eletrico", 0.5)
        if kstyle.trick == "exo":
            self.assets.play("passo_pesado", 0.6)
        if k.shot.note == "paradinha":
            self._shout("PARADINHA!", theme.BRASS, theme.M, y=250, life=60)

    def _update_voo(self):
        k = self.kick
        tail = k.shot.frames - k.flight <= SLOWMO_TAIL or self.replaying
        if tail and self.ticks % 2:
            return                                 # câmera lenta nos últimos quadros
        k.flight += 1
        if not self.replaying:
            self._keeper_dive_input()
        if k.shot.kind == "isolou" and k.flight > k.shot.frames * 0.4:
            self.cam_up = min(UP, self.cam_up + 6)
        if k.flight >= k.shot.frames:
            if self.replaying:
                self.replaying = False
                self.state = "fim_replay"
                self.t = 0
                return
            self._resolve()

    def _resolve(self):
        k = self.kick
        tricks = tuple(self.used[k.keeper.team])
        k.outcome = out = P.resolve(k.shot, k.dive, self._kicker_style(), self._keeper_style(), self.rng, tricks)
        for trick in out.used:
            self.used[k.keeper.team].add(trick)
        bx, by = goal_to_screen(k.shot.x, min(k.shot.y, 1.0))
        k.retake = k.retake and not out.goal and out.result in ("defesa", "espalmou", "segurou")
        if out.goal:
            self.bulge = (bx, by, 1.0)
            self.assets.play("rede", 0.6)
            self.assets.play("torcida", 0.55)
            self._burst(bx, by, TEAM[k.kicker.team], 30, speed=6)
            self._celebrate(k.kicker)
        elif out.result in ("defesa", "espalmou", "segurou"):
            self.assets.play("toco", 0.6)
            self.flashes.append((bx, by, 0))
            self._celebrate(k.keeper)
        elif out.result == "trave":
            self.assets.play("tabela", 0.7)
            self.assets.play("uuuh", 0.5)
            self.shake = 8
        else:
            self.assets.play("uuuh", 0.5)
            self.assets.play("vaia", 0.4)
        color = theme.BRASS if out.goal else theme.BLOOD if out.result in ("isolou", "fora", "trave") else theme.SKY
        big = "GOOOL!" if out.goal else out.text
        sub = out.text if out.goal else ""
        if out.result == "isolou":
            sub = "A TORCIDA FICOU COM A BOLA"
        if k.retake:
            sub = "2º AMARELO: VAI REPETIR!"
        self._shout(big, color, theme.XL, y=220, sub=sub, life=RESULT_FRAMES)
        self.state = "resultado"
        self.t = 0
        self._record(out)

    def _record(self, out):
        k = self.kick
        if k.retake:
            return
        k.kicker.kicks += 1
        k.keeper.faced += 1
        if out.goal:
            k.kicker.goals += 1
        elif out.result in ("defesa", "espalmou", "segurou"):
            k.keeper.saves += 1
        if self.challenge:
            ch = self.challenge
            if out.goal:
                ch["streak"] = 0
                ch["lives"] -= 1
            else:
                ch["streak"] += 1
                if ch["streak"] >= 3:
                    ch["best"] = ch["round"]
                    ch["round"] += 1
                    ch["streak"] = 0
                    self._confetti()
                    self._shout("3 SEGUIDAS!", theme.BRASS, theme.L, y=280, sub="A CPU FICA MAIS DIFÍCIL")
        self.shootout.record(out.goal, k.cell if not k.chip else (0, 1), id(k.kicker))

    def _update_resultado(self):
        self.t += 1
        if self.t < RESULT_FRAMES:
            return
        k = self.kick
        if k.retake:
            self._shout("REPETE!", (250, 214, 60), theme.L)
            self._repeat_kick()
            return
        if self.challenge:
            if self.challenge["lives"] <= 0:
                self._finish()
            else:
                self._next_kick()
            return
        if self.mode == "penaltis" and self.shootout.winner is not None:
            self._confetti()
            self.replaying = True
            self.kick.flight = 0
            self.kick.outcome = None
            self.state = "voo"
            return
        self._next_kick()

    def _repeat_kick(self):
        k = self.kick
        kicker, keeper = k.kicker, k.keeper
        keeper.yellows = 0
        self.kick = Kick(kicker, keeper, decisive=k.decisive, run=k.run, cpu_plan=dict(k.cpu_plan))
        self.kick.cpu_plan.pop("dive", None)
        self.kick.cpu_plan.pop("swapped", None)
        self.state = "entrada"
        self.t = 30

    def _update_fim_replay(self):
        self.t += 1
        if self.t > 30:
            self._finish()

    def _finish(self):
        self.state = "fim"
        self.t = 0
        self.records = self._save_stats()
        self.assets.play("victory", 0.5)
        self._publish()

    def _update_fim(self):
        self.t += 1
        if self.t < 40:
            return
        if any(self.game.inputs[s].pressed("attack") or self.game.inputs[s].pressed("confirm")
               for s in self.active_slots()) or not self.active_slots() and self.t > 300:
            self._leave()

    # ── estatísticas ─────────────────────────
    def _save_stats(self):
        """Soma o acerto de cada herói e as defesas de cada goleiro, e guarda os recordes."""
        data = progress.load()
        stats = data.setdefault(STATS_KEY, {})
        kickers = stats.setdefault("batedores", {})
        keepers = stats.setdefault("goleiros", {})
        best = stats.setdefault("recordes", {})
        new = []
        for team in self.teams:
            for t in team:
                g, n = kickers.get(t.key, [0, 0])
                kickers[t.key] = [g + t.goals, n + t.kicks]
                s, f = keepers.get(t.key, [0, 0])
                keepers[t.key] = [s + t.saves, f + t.faced]
        checks = [("gols_numa_disputa", max((t.goals for team in self.teams for t in team), default=0)),
                  ("defesas_numa_disputa", max((t.saves for team in self.teams for t in team), default=0))]
        if self.challenge:
            checks.append(("desafio_goleiro", self.challenge["best"]))
        for name, value in checks:
            if value and value > best.get(name, 0):
                best[name] = value
                new.append(name)
        progress.save(data)
        return new

    def _leave(self):
        from .play import ResultsScene
        from .menus import TitleScene
        for t in self.humans:
            self.game.inputs[t.slot].set_layout("soccer" if self.match is not None else "battle")
        if self.state != "fim" or self.mode != "penaltis":
            self.game.change(TitleScene(self.game))
            return
        team = self.shootout.winner
        winners = [t.fighter or t for t in self.teams[team]]
        s = self.shootout
        lines = []
        if self.match is not None:
            lines.append(("PLACAR", f"{self.match.score[0]} x {self.match.score[1]}"))
        lines.append(("PÊNALTIS", f"{s.goals(0)} x {s.goals(1)}"))
        for side in self.teams:
            for t in side:
                lines.append((f"{t.label} {t.name}", f"{t.goals}/{t.kicks} · {t.saves} DEF"))
        result = Result(f"TIME {theme.TEAM_NAMES[team]} VENCEU", TEAM[team], winners, lines,
                        score=(s.goals(0), s.goals(1)))
        self.game.change(ResultsScene(self.game, result))

    # ── celular ──────────────────────────────
    def _publish(self):
        k = self.kick
        for t in self.humans:
            role = "espera"
            if self.state == "fim" or k is None:
                role = "espera"
            elif t is k.kicker:
                role = "bate"
            elif t is k.keeper:
                role = "defende"
            hub.publish_slot(t.slot, penalty={"role": role, "hero": t.name})
        hub.set_phase("penalty", mode="soccer", active=self.active_slots())

    # ── efeitos ──────────────────────────────
    def _shout(self, text, color, size, y=210, sub="", life=110):
        self.shouts = [s for s in self.shouts if s.y != y]
        self.shouts.append(Shout(text, color, size, y, life=life, sub=sub))

    def _burst(self, x, y, color, n, speed=4, gravity=0.2, size=4, life=40):
        for _ in range(n):
            a = self.rng.uniform(0, math.tau)
            v = self.rng.uniform(0.3, 1) * speed
            self.particles.append(Particle(x, y, math.cos(a) * v, math.sin(a) * v, color,
                                           self.rng.randint(life // 2, life), size, gravity))

    def _confetti(self):
        for _ in range(90):
            self.particles.append(Particle(self.rng.uniform(0, W), self.rng.uniform(-60, 0),
                                           self.rng.uniform(-1, 1), self.rng.uniform(1, 3),
                                           self.rng.choice((theme.BRASS, TEAM[0], TEAM[1], theme.BONE, theme.MOSS)),
                                           self.rng.randint(80, 140), 4, 0.03))

    def _celebrate(self, taker):
        caption, effect, color = CELEBRATIONS.get(taker.key, ("", "estrelas", theme.BRASS))
        self.celebration = (taker, caption, effect, color)
        x, y = (W // 2 - 60, 440) if taker is self.kick.kicker else (W // 2 + self.kick.keeper_x, LINE_Y - 50)
        if effect in ("fumaca", "sombra", "vapor"):
            self._burst(x, y, color, 30, speed=2.5, gravity=-0.06, size=8, life=60)
        elif effect in ("estrelas", "faisca"):
            self._burst(x, y - 60, color, 34, speed=5, gravity=0.05, size=3, life=50)
        elif effect == "gelo":
            self._burst(x, y + 20, color, 40, speed=4, gravity=0.0, size=3, life=60)
        elif effect == "poeira":
            self._burst(x, y + 30, (150, 130, 100), 30, speed=3, gravity=-0.02, size=6, life=50)
        elif effect == "tremor":
            self.shake = 20
        self.assets.play("comemora_" + taker.key, 0.6)

    # ── desenho ──────────────────────────────
    def draw(self, screen):
        view = pygame.Surface((W, H))
        self._draw_world(view)
        ox = self.rng.randint(-self.shake, self.shake) // 2 if self.shake else 0
        oy = self.rng.randint(-self.shake, self.shake) // 2 if self.shake else 0
        screen.fill(theme.INK)
        screen.blit(view, (ox, oy))
        self._draw_hud(screen)
        if self.state == "ordem":
            self._draw_order(screen)
        if self.state == "fim":
            self._draw_stats(screen)
        if self.paused:
            veil = pygame.Surface((W, H), pygame.SRCALPHA)
            veil.fill((0, 0, 0, 170))
            screen.blit(veil, (0, 0))
            self.ui.text(screen, "PAUSADO", theme.L, theme.BONE, (W // 2, H // 2 - 20))
            self.ui.text(screen, "ATACAR CONTINUA · ESC SAI", theme.XS, theme.MUTED, (W // 2, H // 2 + 20))

    def _draw_world(self, s):
        up = int(self.cam_up)
        self._draw_stands(s, up)
        s.blit(self._grass_surface(), (0, LINE_Y + up))
        k = self.kick
        if k is None:
            return
        if k.decisive and self.state in ("mira", "corrida", "voo"):
            self._draw_flags(s, up)
        self._draw_goal(s, up)
        self._draw_keeper(s, up)
        self._draw_ball(s, up)
        self._draw_kicker(s, up)
        for p in self.particles:
            s.fill(p.color, (round(p.x), round(p.y) + up, p.size, p.size))
        for x, y, a in self.flashes:
            r = 10 + a * 3
            pygame.draw.circle(s, (255, 255, 255), (round(x), round(y) + up), r, 2)
        if k.decisive and self.state in ("mira", "corrida"):
            self._draw_pressure(s)
        self._draw_celebration(s, up)

    def _draw_stands(self, s, up):
        if self._stands is None:
            self._stands = [self._render_stands(seed) for seed in (4, 5)]
        crowd = self._stands[(self.ticks // 12) % 2 if self.state in ("resultado", "fim") else 0]
        s.blit(crowd, (0, up - UP))

    def _render_stands(self, seed):
        rng = random.Random(seed)
        surf = pygame.Surface((W, LINE_Y + UP))
        surf.fill((16, 14, 26))
        for row in range((LINE_Y + UP) // 14):
            y = -10 + row * 14
            if y > LINE_Y + UP - 30:
                break
            surf.fill((34 + row % 14, 30 + row % 14, 48 + row % 14), (0, y, W, 14))
            for x in range(4, W, 9):
                if rng.random() < 0.82:
                    col = rng.choice([TEAM[0], TEAM[1], (240, 220, 120), theme.BONE, (70, 60, 90), TEAM[1], TEAM[0]])
                    bob = rng.choice((0, 0, -1, -2))
                    surf.fill((200, 150, 120), (x, y + 3 + bob, 5, 4))
                    surf.fill(col, (x - 1, y + 7 + bob, 7, 6))
                    if rng.random() < 0.15:
                        surf.fill(col, (x - 2, y - 1 + bob, 2, 6))
        surf.fill((22, 20, 34), (0, LINE_Y + UP - 34, W, 22))
        for i, label in enumerate(("SOUL STRIKE", "LOGLAB", "SOUL STRIKE", "LOGLAB")):
            self.ui.text(surf, label, theme.XS, (90, 84, 120), (120 + i * 240, LINE_Y + UP - 23), shadow=False)
        for x in (40, W - 40):
            pygame.draw.circle(surf, (255, 250, 220), (x, UP + 18), 10)
        return surf

    def _grass_surface(self):
        if self._grass is None:
            g = pygame.Surface((W, H - LINE_Y + UP))
            top = 0
            h = H - LINE_Y
            for i in range(12):
                y0 = int((i / 12) ** 1.6 * h)
                y1 = int(((i + 1) / 12) ** 1.6 * h)
                g.fill((52, 128, 60) if i % 2 else (60, 140, 68), (0, y0, W, y1 - y0 + 1))
            g.fill((60, 140, 68), (0, h, W, UP))
            white = (226, 232, 220)
            pygame.draw.line(g, white, (0, top), (W, top), 2)
            pygame.draw.lines(g, white, False, [(GOAL_L - 60, 0), (GOAL_L - 120, 70),
                                                (GOAL_R + 120, 70), (GOAL_R + 60, 0)], 2)
            pygame.draw.ellipse(g, white, (W // 2 - 8, SPOT[1] - LINE_Y, 16, 6))
            self._grass = g
        return self._grass

    def _draw_goal(self, s, up):
        net = (200, 204, 214)
        back = pygame.Rect(GOAL_L + 34, BAR_Y + 26 + up, GOAL_R - GOAL_L - 68, LINE_Y - BAR_Y - 30)
        bulge = self.bulge

        def warp(x, y):
            if bulge is None:
                return x, y
            bx, by, amp = bulge
            by += up
            d = math.hypot(x - bx, y - by)
            if d > 80:
                return x, y
            k = (1 - d / 80) ** 2 * amp * (1 + 0.3 * math.sin(self.ticks * 0.6))
            return x + (x - bx) * 0.25 * k, y + (y - by) * 0.25 * k - 8 * k

        for gx in range(back.left, back.right + 1, 12):
            pygame.draw.lines(s, net, False, [warp(gx, y) for y in range(back.top, back.bottom + 1, 6)], 1)
        for gy in range(back.top, back.bottom + 1, 12):
            pygame.draw.lines(s, net, False, [warp(x, gy) for x in range(back.left, back.right + 1, 6)], 1)
        for i in range(11):
            t = i / 10
            y = BAR_Y + up + t * (LINE_Y - BAR_Y)
            pygame.draw.line(s, net, (GOAL_L, y), (back.left, back.top + t * back.h), 1)
            pygame.draw.line(s, net, (GOAL_R, y), (back.right, back.top + t * back.h), 1)
            pygame.draw.line(s, net, (GOAL_L + t * (GOAL_R - GOAL_L), BAR_Y + up), (back.left + t * back.w, back.top), 1)
        post = (246, 246, 240)
        wobble = 0
        if self.kick and self.kick.outcome and self.kick.outcome.result == "trave" and self.t < 20:
            wobble = round(math.sin(self.t * 1.5) * 3)
        s.fill(post, (GOAL_L - 8 + wobble, BAR_Y - 8 + up, GOAL_R - GOAL_L + 16, 8))
        s.fill(post, (GOAL_L - 8 + wobble, BAR_Y - 8 + up, 8, LINE_Y - BAR_Y + 8))
        s.fill(post, (GOAL_R + wobble, BAR_Y - 8 + up, 8, LINE_Y - BAR_Y + 8))

    def _dive_progress(self):
        """Quanto o goleiro já andou no pulo (0..1), no tempo da tela."""
        k = self.kick
        if k.dive is None or k.dive_frame is None:
            return 0.0
        now = self.t if self.state == "corrida" else k.contact_at + k.flight
        if self.state in ("resultado", "fim", "fim_replay"):
            now = k.contact_at + (k.shot.frames if k.shot else 0)
        frames = P.DIVE_FRAMES / self._keeper_style().dive
        return max(0.0, min(1.0, (now - k.dive_frame) / frames))

    def _draw_keeper(self, s, up):
        k = self.kick
        keeper = k.keeper
        sprites = keeper.sprites
        base_x = W // 2 + k.keeper_x
        ground = LINE_Y + 2 + up
        if k.catimba:
            # catimba: o goleiro anda até a marca e encara quem bate
            p = 1 - abs(k.catimba - CATIMBA_FRAMES / 2) / (CATIMBA_FRAMES / 2)
            x = base_x + (W // 2 + 40 - base_x) * p
            y = ground + (470 - ground) * p
            scale = KEEPER_SCALE * (1 + p * 0.8)
            img = _scaled(sprites.frame("frente", self.ticks // 6), scale)
            pygame.draw.ellipse(s, (0, 0, 0), (x - 30 * scale / 1.5, y - 8, 60 * scale / 1.5, 14))
            s.blit(img, img.get_rect(midbottom=(x, y)))
            if p > 0.6:
                self.ui.text(s, "!", theme.L, theme.BLOOD, (x - 40, y - img.get_height() - 10))
                if getattr(k, "card", False):
                    s.fill(theme.INK, (W - 268, 318 + up, 30, 40))
                    s.fill((250, 214, 60), (W - 270, 316 + up, 28, 38))
            return
        progress = self._dive_progress()
        pygame.draw.ellipse(s, (0, 0, 0), (base_x - 30, ground - 8, 60, 14))
        if k.dive is not None and progress > 0:
            cell = k.dive.cell or (0, 1)
            tx, ty = goal_to_screen(*P.cell_point(*cell))
            x = base_x + (tx - base_x) * progress
            y = ground - 50 + (ty + up - (ground - 50)) * progress
            if cell[0] == 0:
                img = _scaled(sprites.pose("frente", "pulo", 1), KEEPER_SCALE)
                s.blit(img, img.get_rect(center=(x, y)))
            else:
                angle = cell[0] * -70 * progress
                if cell[1] == 0:
                    angle *= 1.25
                img = pygame.transform.rotate(_scaled(sprites.pose("frente", "esquiva", 0), KEEPER_SCALE), angle)
                s.blit(img, img.get_rect(center=(x, y)))
            if self.state == "resultado" and k.outcome and k.outcome.result == "defesa" and self.t > 20:
                self._draw_mini_ball(s, x, y - 10)
            if self._keeper_style().trick == "clone" and k.dive.cell:
                ghost = _scaled(sprites.pose("frente", "parado", 0), KEEPER_SCALE).copy()
                ghost.set_alpha(110)
                s.blit(ghost, ghost.get_rect(midbottom=(base_x, ground)))
            return
        if self.state == "resultado" and k.outcome and k.outcome.result in ("segurou",):
            img = _scaled(sprites.pose("frente", "comemora", (self.t // 10) % 2), KEEPER_SCALE)
        elif getattr(k, "provoking", False):
            img = _scaled(sprites.pose("frente", "comemora", (self.ticks // 8) % 2), KEEPER_SCALE)
        else:
            img = _scaled(sprites.pose("frente", "parado", (self.ticks // 30) % 2), KEEPER_SCALE)
        s.blit(img, img.get_rect(midbottom=(base_x, ground)))
        if k.hacked_keeper and self.state == "corrida" and k.run - self.t <= P.HACK_FRAMES:
            self.ui.text(s, "TRAVADO", theme.XS, (110, 230, 140), (base_x, ground - img.get_height() - 12))
        if self.state == "entrada" and self.t > 10 and self._history():
            s.fill((90, 200, 240), (base_x + 30, ground - 66, 8, 18))     # garrafinha na mão
            s.fill((240, 240, 250), (base_x + 31, ground - 70, 6, 4))

    def _history(self):
        if self.shootout is None or self.kick is None:
            return []
        return self.shootout.corners.get(id(self.kick.kicker), [])

    def _ball_screen(self):
        """Posição (x, y) e raio da bola na tela durante o voo."""
        k = self.kick
        shot = k.shot
        t = min(1.0, k.flight / shot.frames)
        sx, sy = SPOT
        if shot.kind == "isolou":
            gx, gy = goal_to_screen(shot.x, shot.y)
        else:
            gx, gy = goal_to_screen(shot.x, shot.y)
        if shot.swap_at and k.flight < shot.swap_at:
            mid = goal_to_screen(-shot.x, shot.y)[0]
            gx = sx + (mid - sx) * 1.0
            t_side = k.flight / shot.swap_at
            x = sx + (gx - sx) * t_side * 0.5
        elif shot.swap_at:
            x0 = sx + (goal_to_screen(-shot.x, shot.y)[0] - sx) * 0.5
            t_side = (k.flight - shot.swap_at) / max(1, shot.frames - shot.swap_at)
            x = x0 + (gx - x0) * t_side
        elif shot.from_x:
            fx = goal_to_screen(shot.from_x, shot.y)[0]
            x = (1 - t) ** 2 * sx + 2 * (1 - t) * t * fx + t * t * gx
        else:
            x = sx + (gx - sx) * t
        arc = 110 if shot.chip else 40
        y = sy + (gy - sy) * t - arc * math.sin(math.pi * t)
        r = 12 - 5 * t
        return x, y, r

    def _draw_ball(self, s, up):
        k = self.kick
        if k.shot is None or self.state in ("entrada", "mira", "corrida"):
            pygame.draw.ellipse(s, (0, 0, 0), (SPOT[0] - 18, SPOT[1] + 2 + up, 36, 10))
            self._draw_mini_ball(s, SPOT[0], SPOT[1] - 4 + up, 12)
            return
        if self.state == "resultado" and k.outcome and k.outcome.result == "defesa" and self.t > 20:
            return
        x, y, r = self._ball_screen()
        if self.state == "resultado":
            x, y, r = self._ball_after(x, y, r)
        if self._kicker_style().trick == "some" and 0.35 < k.flight / k.shot.frames < 0.75 and self.state == "voo":
            pygame.draw.circle(s, (200, 220, 255), (round(x), round(y) + up), round(r), 1)
            return
        shade = max(8, int(36 * (1 - k.flight / k.shot.frames)))
        pygame.draw.ellipse(s, (0, 0, 0), (x - shade / 2, SPOT[1] + (LINE_Y - SPOT[1]) * min(1, k.flight / k.shot.frames)
                                           + up, shade, 6))
        if k.shot.power > 0.75 or self._kicker_style().trick in ("raio", "exo"):
            color = (255, 240, 120) if self._kicker_style().trick == "raio" else (240, 220, 160)
            for i in range(1, 6):
                tx, ty, tr = self._ball_trail(i)
                pygame.draw.circle(s, color, (round(tx), round(ty) + up), max(2, round(tr * 0.6)))
        self._draw_mini_ball(s, x, y + up, r)
        if self.state == "resultado" and k.outcome.result == "isolou" and self.t > 24:
            fan = TEAM[1 - k.kicker.team]                  # um torcedor rival pega a bola
            fx, fy = round(x), round(y + up)
            s.fill((200, 150, 120), (fx - 4, fy + 6, 8, 7))
            s.fill(fan, (fx - 7, fy + 13, 14, 12))
            s.fill(fan, (fx - 12, fy - 6, 4, 18))
            s.fill(fan, (fx + 8, fy - 6, 4, 18))

    def _ball_trail(self, back):
        k = self.kick
        flight = k.flight
        k.flight = max(0, flight - back * 2)
        pos = self._ball_screen()
        k.flight = flight
        return pos

    def _ball_after(self, x, y, r):
        """Depois do resultado: a bola espalmada sai para o lado, a isolada vai para a torcida."""
        k = self.kick
        t = self.t
        result = k.outcome.result
        if result in ("espalmou", "trave"):
            side = 1 if k.shot.x >= 0 else -1
            return x + side * t * 3, y + min(60, t * t * 0.08) - t * 1.2, r
        if result == "isolou":
            return x + t * 0.6, y - min(t * 2, 60), r
        if result == "segurou":
            return W // 2 + k.keeper_x, LINE_Y - 60, 6
        return x, y, r

    @staticmethod
    def _draw_mini_ball(s, x, y, r=7):
        x, y, r = round(x), round(y), max(3, round(r))
        pygame.draw.circle(s, (240, 240, 236), (x, y), r)
        pygame.draw.circle(s, (30, 28, 36), (x, y), max(1, r // 3))
        pygame.draw.circle(s, theme.INK, (x, y), r, 2)

    def _draw_kicker(self, s, up):
        k = self.kick
        kicker = k.kicker
        sprites = kicker.sprites
        start = (W // 2 - 150, H - 4)
        foot = (W // 2 - 40, 534)
        style = self._kicker_style()
        if self.state == "entrada":
            p = min(1.0, self.t / 50)
            x = W // 2 - 360 + (start[0] - (W // 2 - 360)) * p
            img = sprites.frame("costas", self.ticks // 5) if p < 1 else sprites.pose("costas", "parado", 0)
            pos = (x, start[1])
        elif self.state == "mira":
            img = sprites.pose("costas", "parado", (self.ticks // 30) % 2)
            pos = start
            if k.catimba:
                pos = (start[0] + 20, start[1])
        elif self.state == "corrida":
            p = self.t / max(1, k.run)
            paradinha = style.trick == "paradinha" and not k.chip and k.run - self.t < 14
            if paradinha:
                p = (k.run - 14) / max(1, k.run)
            img = sprites.frame("costas", self.t // 3) if not paradinha else sprites.pose("costas", "pulo", 0)
            hop = 12 * math.sin(math.pi * (14 - (k.run - self.t)) / 14) if paradinha else 0
            pos = (start[0] + (foot[0] - start[0]) * p, start[1] + (foot[1] - start[1]) * p - hop)
            if style.trick == "moto":
                pos = (pos[0], pos[1] - 6 * abs(math.sin(self.t * 0.3)))
            self._draw_tell(s, pos, p)
        elif self.state == "voo":
            idx = min(2, k.flight // 3)
            img = sprites.pose("costas", "chute", idx)
            pos = foot
        else:
            out = k.outcome
            if out is not None and out.goal:
                img = sprites.pose("frente" if self.t > 40 else "costas", "comemora", (self.t // 8) % 2)
                pos = (foot[0] - min(self.t, 60), foot[1] - abs(math.sin(self.t * 0.2)) * 10)
            elif out is not None:
                img = sprites.pose("costas", "dano", 0)
                pos = foot
            else:
                img = sprites.pose("costas", "parado", 0)
                pos = foot
        if style.trick == "fumaca" and self.state == "corrida" and 0.4 < self.t / max(1, k.run) < 0.7:
            return                                 # sumiu na fumaça
        img = _scaled(img, KICKER_SCALE)
        pygame.draw.ellipse(s, (0, 0, 0), (pos[0] - 45, pos[1] - 10, 90, 18))
        s.blit(img, img.get_rect(midbottom=(round(pos[0]), round(pos[1]))))
        if self.state == "mira" and k.charging:
            self._draw_power(s)

    def _draw_tell(self, s, pos, p):
        """O sinal da corrida: o ombro abre e o pé de apoio vira para o lado do chute."""
        k = self.kick
        side = P.tell_side(k.cell, self._kicker_style())
        if side is None or not 0.55 < p < 0.88:
            return
        keeper = self._keeper_style()
        strength = min(1.0, 0.55 * keeper.read)
        x, y = pos
        width = 3 if keeper.read > 1.2 else 2
        color = (255, 255, 255) if keeper.trick != "" or keeper.read > 1 else (230, 230, 220)
        if side:
            sx = x + side * 34
            pygame.draw.arc(s, color, (sx - 14, y - 150, 28, 24), 0.3, 2.8, width)       # ombro abrindo
            pygame.draw.line(s, color, (x, y - 2), (x + side * 26 * strength + side * 8, y - 8), width)  # pé de apoio
        else:
            pygame.draw.line(s, color, (x - 10, y - 156), (x + 10, y - 156), width)
        if keeper.read > 1.25 and (self.ticks // 3) % 2:
            pygame.draw.circle(s, (255, 240, 140), (round(x + side * 34), round(y - 140)), 6, 1)

    def _draw_power(self, s):
        k = self.kick
        style = self._kicker_style()
        lo, hi, over = P.sweet_band(style, (1, 1))
        x, y, h = W - 70, 150, 220
        jitter = self.rng.uniform(-1, 1) * k.shake * h if k.shake > 0.005 else 0
        value = max(0.0, min(1.0, k.power))
        s.fill(theme.INK, (x - 4, y - 4, 32, h + 8))
        s.fill((60, 56, 76), (x, y, 24, h))
        s.fill((70, 150, 80), (x, y + h - int(hi * h), 24, int((hi - lo) * h)))
        s.fill((190, 60, 50), (x, y, 24, int((1 - over) * h)))
        s.fill(theme.BRASS, (x, y + h - int(value * h), 24, int(value * h)))
        pygame.draw.rect(s, theme.BONE, (x - 4, y + h - int(value * h) - 2 + jitter, 32, 4))
        self.ui.text(s, "FORÇA", theme.XS, theme.BONE, (x + 12, y + h + 18))
        self.ui.text(s, "ISOLA", theme.XS, (230, 120, 110), (x + 12, y - 14))

    def _draw_flags(self, s, up):
        rival = TEAM[1 - self.kick.kicker.team]
        for x in range(30, W, 70):
            wave = 6 * math.sin(x * 0.07 + self.ticks * 0.15)
            pygame.draw.line(s, (120, 100, 80), (x, 150 + wave + up), (x, 120 + wave + up), 2)
            s.fill(rival, (x + 1, 120 + wave + up, 22, 14))

    def _draw_pressure(self, s):
        beat = (math.sin(self.ticks * 0.2) + 1) / 2
        calm = self._kicker_style().calm
        edge = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(0, 40, 2):
            a = int((90 + 80 * beat) * (1 - i / 40) ** 2 * (1 - 0.6 * calm))
            pygame.draw.rect(edge, (200, 20, 30, a), (i, i, W - 2 * i, H - 2 * i), 2)
        s.blit(edge, (0, 0))
        hx, hy, r = W // 2, 92, 9 + round(beat * 3)
        for dx in (-r * 0.75, r * 0.75):
            pygame.draw.circle(s, (220, 40, 50), (round(hx + dx), hy), r)
        pygame.draw.polygon(s, (220, 40, 50), [(hx - r * 1.7, hy + 3), (hx + r * 1.7, hy + 3), (hx, hy + r * 2.2)])
        if calm and self.state == "mira":
            self.ui.text(s, "FRIEZA: SENTE MENOS", theme.XS, theme.BRASS, (W // 2 - 110, 340))

    def _draw_celebration(self, s, up):
        if self.state != "resultado" or getattr(self, "celebration", None) is None:
            return
        taker, caption, effect, color = self.celebration
        if self.t < 30:
            return
        if effect == "raio" and self.t < 60:
            rng = random.Random(self.t // 4)
            pts, x = [], W // 2 - 60 + rng.randint(-20, 20)
            for y in range(-10, 440, 30):
                pts.append((x, y + up))
                x += rng.choice((-26, 22, -14, 30))
            pygame.draw.lines(s, (255, 250, 200), False, pts, 8)
            pygame.draw.lines(s, (246, 214, 70), False, pts, 3)
        elif effect == "telao":
            box = pygame.Rect(W // 2 - 110, 30 + up, 220, 50)
            s.fill(theme.INK, box)
            pygame.draw.rect(s, color, box, 2)
            self.ui.text(s, "GOL.EXE" if self.t % 20 < 14 else "GOL.EXE_", theme.M, color, box.center, shadow=False)
        elif effect == "bandeira":
            x, y = W // 2 - 140, 520 + up
            pygame.draw.line(s, (120, 90, 60), (x, y), (x, y - 70), 3)
            s.fill(color, (x + 2, y - 70, 34, 22))
            self.ui.text(s, "X", theme.XS, theme.BONE, (x + 19, y - 59), shadow=False)
        elif effect == "rastro":
            for i in range(8):
                s.fill(color, (W // 2 - 60 - self.t * 2 + i * 10, 500 + up, 6, 4))
        if caption:
            self.ui.text(s, caption, theme.XS, color, (W // 2, 292 + up))

    def _draw_hud(self, s):
        if self.shootout is None:
            return
        k = self.kick
        band = pygame.Surface((W, 66), pygame.SRCALPHA)
        band.fill((0, 0, 0, 120))
        s.blit(band, (0, 0))
        title = "PÊNALTIS"
        if self.mode == "treino_penaltis":
            title = "TREINO DE PÊNALTIS"
        if self.challenge:
            ch = self.challenge
            title = f"DESAFIO DO GOLEIRO · RODADA {ch['round']}"
        elif k is not None and self.state != "fim":
            number = self.shootout.number
            title += f" · {number}ª COBRANÇA · {theme.TEAM_NAMES[k.kicker.team]}"
            if self.shootout.sudden_death and self.mode == "penaltis":
                title += " · MORTE SÚBITA"
        self.ui.text(s, title, theme.XS, theme.BONE, (W // 2, 18))
        if self.challenge:
            self._draw_gloves(s)
        else:
            for team in (0, 1):
                kicks = self.shootout.kicks[team]
                y = 40 + team * 16
                s.fill(TEAM[team], (W // 2 - 110, y - 5, 10, 10))
                shown = max(P.REGULAR_KICKS, len(kicks))
                first = max(0, shown - 8)
                for i in range(first, shown):
                    r = kicks[i] if i < len(kicks) else None
                    c = theme.MOSS if r is True else theme.BLOOD if r is False else (60, 56, 76)
                    cx = W // 2 - 80 + (i - first) * 18
                    pygame.draw.circle(s, c, (cx, y), 6)
                    pygame.draw.circle(s, theme.INK, (cx, y), 6, 1)
        if k is not None and self.state != "fim":
            self.ui.text(s, f"{k.kicker.label} {k.kicker.name} BATE", theme.XS, TEAM[k.kicker.team],
                         (16, H - 34), anchor="midleft")
            self.ui.text(s, f"{k.keeper.label} {k.keeper.name} NO GOL", theme.XS, TEAM[k.keeper.team],
                         (W - 16, H - 34), anchor="midright")
            if self.state == "mira":
                hint = self._hint()
                if hint:
                    self.ui.text(s, hint, theme.XS, theme.MUTED, (W // 2, H - 14))
        if self.state == "entrada" and self._history() and k is not None and self.t > 10:
            self._draw_note(s)
        for sh in self.shouts:
            self._draw_shout(s, sh)

    def _hint(self):
        k = self.kick
        parts = []
        if not k.kicker.cpu:
            parts.append("BATE: SEGURE CHUTE E SOLTE COM O CANTO NO ANALÓGICO · PASSE = CAVADINHA")
        if not k.keeper.cpu:
            parts.append("GOLEIRO: ESQUIVA PULA PARA O LADO · ATACAR PROVOCA · MARCAR = CATIMBA")
        return "   ".join(parts) if len(parts) == 1 else "O CANTO NÃO APARECE: SÓ QUEM BATE SABE"

    def _draw_note(self, s):
        """A colinha do goleiro: os cantos que esse batedor já escolheu na disputa."""
        paper = pygame.Rect(W - 300, 90, 250, 60 + 26 * len(self._history()[-4:]))
        pygame.draw.rect(s, theme.INK, paper.move(4, 4))
        pygame.draw.rect(s, (236, 228, 196), paper)
        self.ui.text(s, "COLINHA DO GOLEIRO", theme.XS, theme.INK, (paper.centerx, paper.y + 18), shadow=False)
        self.ui.text(s, self.kick.kicker.name, theme.XS, (60, 40, 30), (paper.x + 14, paper.y + 40),
                     anchor="midleft", shadow=False)
        for i, cell in enumerate(self._history()[-4:]):
            y = paper.y + 64 + i * 26
            self.ui.text(s, f"{i + 1}ª", theme.XS, (60, 40, 30), (paper.x + 14, y), anchor="midleft", shadow=False)
            self.ui.text(s, _cell_name(cell), theme.XS, (170, 40, 40), (paper.right - 14, y), anchor="midright",
                         shadow=False)

    def _draw_gloves(self, s):
        ch = self.challenge
        for i in range(3):
            lit = i < ch["streak"]
            c = theme.BRASS if lit else (60, 56, 76)
            r = pygame.Rect(W // 2 - 60 + i * 44, 34, 30, 26)
            s.fill(theme.INK, r.move(2, 2))
            s.fill(c, r)
            if lit:
                pygame.draw.rect(s, (255, 240, 180), r.inflate(6, 6), 2)
        self.ui.text(s, f"VIDAS {ch['lives']}", theme.XS, theme.BLOOD, (W // 2 + 120, 47), anchor="midleft")

    def _draw_shout(self, s, sh):
        slam = max(0.0, 1 - sh.age / 8)
        size = sh.size
        dx = round(math.sin(sh.age * 1.7) * 4 * max(0.0, 1 - sh.age / 20))
        y = sh.y - round(slam * 30)
        if sh.age > sh.life - 10 and (sh.age // 2) % 2:
            return
        self.ui.text(s, sh.text, size, sh.color, (W // 2 + dx, y))
        if sh.sub:
            self.ui.text(s, sh.sub, theme.XS, theme.BONE, (W // 2, y + size // 2 + 20))

    def _draw_order(self, s):
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        s.blit(veil, (0, 0))
        self.ui.text(s, "QUEM BATE PRIMEIRO?", theme.M, theme.BRASS, (W // 2, 90))
        self.ui.text(s, "← → ESCOLHE · ATACAR TROCA DOIS DE LUGAR · PASSE: PRONTO", theme.XS, theme.BONE,
                     (W // 2, 116))
        for team in (0, 1):
            x0 = 40 + team * 460
            self.ui.text(s, theme.TEAM_NAMES[team] + (" · PRONTO" if self.ready[team] else ""), theme.XS,
                         TEAM[team], (x0 + 200, 150))
            for i, taker in enumerate(self.orders[team]):
                r = pygame.Rect(x0 + i * 82, 170, 72, 150)
                border = TEAM[team]
                if not self.ready[team] and self.cursor[team] == i:
                    border = theme.BRASS
                if self.picked[team] == i:
                    border = theme.BONE
                pygame.draw.rect(s, theme.INK, r.move(3, 3))
                pygame.draw.rect(s, (28, 24, 40), r)
                pygame.draw.rect(s, border, r, 2)
                img = taker.sprites.pose("frente", "parado", 0)
                s.blit(img, img.get_rect(midbottom=(r.centerx, r.bottom - 22)))
                self.ui.text(s, f"{i + 1}ª", theme.XS, theme.BONE, (r.centerx, r.y + 16))
                self.ui.text(s, taker.name[:8], theme.XS, theme.BONE, (r.centerx, r.bottom - 10), shadow=False)

    def _draw_stats(self, s):
        veil = pygame.Surface((W, H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 170))
        s.blit(veil, (0, 0))
        panel = pygame.Rect(W // 2 - 260, 90, 520, 360)
        self.ui.panel(s, panel)
        if self.challenge:
            title = f"CHEGOU NA RODADA {self.challenge['round']}"
            color = theme.BRASS
        elif self.mode == "penaltis" and self.shootout.winner is not None:
            team = self.shootout.winner
            title, color = f"{theme.TEAM_NAMES[team]} CAMPEÃO", TEAM[team]
        else:
            title, color = "FIM DO TREINO", theme.BONE
        self.ui.text(s, title, theme.M, color, (W // 2, panel.y + 30))
        if not self.challenge:
            self.ui.text(s, f"PÊNALTIS {self.shootout.goals(0)} x {self.shootout.goals(1)}", theme.XS, theme.BONE,
                         (W // 2, panel.y + 58))
        y = panel.y + 84
        grow = min(1.0, self.t / 60)
        for team in self.teams:
            for t in team:
                goals = round(t.goals * grow)
                saves = round(t.saves * grow)
                acc = f"{goals}/{t.kicks}" if t.kicks else "-"
                self.ui.text(s, f"{t.label} {t.name}", theme.XS, TEAM[t.team], (panel.x + 24, y), anchor="midleft")
                self.ui.text(s, f"GOLS {acc}   DEFESAS {saves}/{t.faced}", theme.XS, theme.BONE,
                             (panel.right - 24, y), anchor="midright")
                y += 24
        names = {"gols_numa_disputa": "MAIS GOLS NUMA DISPUTA", "defesas_numa_disputa": "MAIS DEFESAS NUMA DISPUTA",
                 "desafio_goleiro": "MELHOR RODADA NO DESAFIO"}
        y += 10
        for name in self.records:
            if self.t < 60:
                break
            badge = pygame.Rect(panel.x + 24, y - 10, 20, 20)
            pygame.draw.circle(s, theme.BRASS, badge.center, 10)
            pygame.draw.circle(s, (255, 240, 180), badge.center, 10, 2)
            self.ui.text(s, "RECORDE NOVO: " + names.get(name, name), theme.XS, theme.BRASS,
                         (panel.x + 54, y), anchor="midleft")
            y += 26
        if self.t > 40:
            self.ui.text(s, "ATACAR / ENTER PARA CONTINUAR", theme.XS, theme.MUTED, (W // 2, panel.bottom - 20))


def _cell_name(cell):
    col, row = cell
    side = {-1: "ESQ.", 0: "MEIO", 1: "DIR."}[col]
    height = {0: "BAIXO", 1: "", 2: "ALTO"}[row]
    return f"{side} {height}".strip() if col or row != 1 else "MEIO"


def takers_from_session(game, session):
    """Monta os times da disputa a partir das vagas escolhidas no menu."""
    teams = [[], []]
    for setup in session.slots:
        key = _char_key(setup.char)
        team = session.team_of(setup.slot) if session.team_mode else (0 if setup.slot == 1 else 1)
        teams[team].append(Taker(key, team, slot=None if setup.cpu else setup.slot, cpu=setup.cpu))
    for team in (0, 1):
        if not teams[team]:
            teams[team].append(Taker("paredao" if team else "matador", team))
    return teams


def _char_key(index):
    return CHARACTERS[index].key if 0 <= index < len(CHARACTERS) else CHARACTERS[0].key


def takers_from_match(match):
    teams = [[], []]
    for f in match.fighters:
        teams[f.team].append(Taker(f.stats.key, f.team, slot=None if f.is_cpu else f.slot, cpu=f.is_cpu,
                                   fighter=f))
    return teams


def start_penalties(game):
    """Disputa direto do menu (DISPUTA DE PÊNALTIS, treino ou desafio do goleiro)."""
    session = game.session
    teams = takers_from_session(game, session)
    if session.mode == "desafio_goleiro":
        human = [t for team in teams for t in team if not t.cpu][:1] or teams[0][:1]
        keeper = Taker(human[0].key, 0, slot=human[0].slot, cpu=human[0].cpu)
        rng = random.Random()
        kickers = [Taker(k, 1) for k in rng.sample([c.key for c in CHARACTERS], 5)]
        teams = [[keeper], kickers]
    return PenaltyScene(game, teams, mode=session.mode, difficulty=session.difficulty)
