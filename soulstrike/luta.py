"""Regras do modo LUTA (1 x 1 de lado): andar, pular, golpes, defesa, caixas de contato e rounds.

Aqui não se desenha nada (o desenho fica em scenes/luta.py); as caixas saem dos pontos do corpo
de cada quadro do esqueleto (luta_rig.py), então o golpe acerta onde a mão ou o pé estão de verdade.

Caixas:
  golpe (vermelha)    círculo na mão, no pé ou na arma, só nos quadros de contato
  corpo (azul)        cabeça, tronco e pernas, seguindo a pose
  empurrão (amarela)  faixa no chão: dois lutadores nunca ficam um dentro do outro

Botões (os nomes são os mesmos do futebol, então o controle e o teclado já sabem quais são):
  attack = SOCO   special = CHUTE   dodge ou ↑ = PULO   sprint = FORTE (ou frente + SOCO)
  dribble = ESPECIAL (1 carga)   super = SUPER (3 cargas)   trás ou mark = DEFESA   ↓ = agachar
"""
import math
import random
from dataclasses import dataclass, field

import pygame

from . import config, luta_poses, luta_rig as R

W = config.SCREEN_W
FLOOR = 474                     # chão na tela
WALL_L, WALL_R = 46, W - 46
GRAVITY = 0.8
JUMP_VY = -15.5
ROUND_FRAMES = 60 * 60          # 60 segundos
ROUNDS_TO_WIN = 2               # melhor de 3
MAX_ROUNDS = 5
MAX_ENERGY = 3.0                # 3 cargas: o ESPECIAL gasta 1 e o SUPER, 3
SPECIAL_COST, SUPER_COST = 1.0, 3.0
BASE_HP = 1000
BUFFER = 8                      # quadros que um aperto fica guardado (para emendar golpes)
INTRO_FRAMES = 110
KO_FRAMES = 150
SUPER_FREEZE = 40

# ── lutadores do modo (etapa 1: Aryel e Cauanzera) ────────────────────
FIGHTER_KEYS = ("aryel", "cauanzera")


@dataclass
class FighterSpec:
    key: str
    name: str
    hp: int
    walk: float
    color: tuple
    weapon: str                 # arma de perto (só no golpe FORTE)
    special: str
    special_desc: str
    super: str
    super_desc: str
    push_w: int                 # meia largura da caixa de empurrão (px)


SPECS = {
    "aryel": FighterSpec("aryel", "Aryel", 1050, 3.0, (234, 132, 64), "Capacete",
                         "APOSTA", "Gira a roleta: GREEN chove moeda no outro, RED estoura nele.",
                         "GRAU DE MOTO", "Atravessa a arena empinando.", 22),
    "cauanzera": FighterSpec("cauanzera", "Cauanzera", 1000, 3.4, (84, 162, 222), "Cabo de Rede",
                             "MULTIESPORTISTA", "Basquete, vôlei e 100 metros, em ordem.",
                             "ENTERRADA", "Voa e enterra a bola no outro.", 24),
}


# ── quadros (desenhados uma vez e guardados) ──────────────────────────
class Bank:
    """Quadros já desenhados de cada lutador: (imagem virada à direita, à esquerda, pontos)."""

    _cache = {}

    @classmethod
    def get(cls, char, name):
        key = (char, name)
        frame = cls._cache.get(key)
        if frame is None:
            img, points = R.draw_fighter(R.LOOKS[char], luta_poses.pose(char, name))
            frame = (img, pygame.transform.flip(img, True, False), points)
            cls._cache[key] = frame
        return frame

    @classmethod
    def preload(cls, char):
        for name in luta_poses.names(char):
            cls.get(char, name)
        q = luta_poses.QUARTERS
        walk = ("andar1", "andar2", "andar3", "andar4")
        for n in range(1, q):        # respirar e andar aparecem o tempo todo: já ficam prontos
            cls.get(char, luta_poses.mid("guarda", "guarda2", n))
            for i in range(4):
                cls.get(char, luta_poses.mid(walk[i], walk[(i + 1) % 4], n))


# ── golpes ────────────────────────────────────────────────────────────
@dataclass
class Move:
    name: str
    steps: list                 # [(pose, quadros)]
    active: tuple = ()          # índices dos passos com a caixa de golpe ligada
    point: str = "far_hand"     # de onde sai a caixa de golpe
    radius: int = 18
    reach: int = 0              # a caixa vai mais para a frente (arma comprida)
    damage: int = 50
    hitstun: int = 16
    blockstun: int = 11
    push: float = 6.0
    level: str = "alto"         # alto (defende em pé ou agachado), baixo (só agachado), aereo (só em pé)
    knockdown: bool = False
    cancel: tuple = ()          # golpes que dá para emendar quando este acerta
    hitstop: int = 6
    sound: str = "golpe"
    air: bool = False
    chip: float = 0.0           # dano que passa pela defesa
    weapon: bool = False

    @property
    def length(self):
        return sum(n for _, n in self.steps)


def _moves(key):
    weapon_reach = {"aryel": 6, "cauanzera": 34}[key]      # o cabo de rede vai longe
    weapon_damage = {"aryel": 125, "cauanzera": 105}[key]  # o capacete pesa mais
    return {
        "soco": Move("soco", [("soco1", 3), ("soco2", 4), ("soco3", 8)], active=(1,), point="far_hand",
                     radius=18, damage=45, hitstun=15, blockstun=10, push=6,
                     cancel=("chute", "forte", "especial", "super"), sound="golpe"),
        "chute": Move("chute", [("chute1", 7), ("chute2", 5), ("chute3", 11)], active=(1,), point="far_foot",
                      radius=20, damage=72, hitstun=19, blockstun=13, push=9, cancel=("especial", "super"),
                      sound="chute", hitstop=7),
        "forte": Move("forte", [("forte1", 13), ("forte2", 5), ("forte3", 16)], active=(1,), point="near_hand",
                      radius=24, reach=weapon_reach, damage=weapon_damage, hitstun=24, blockstun=17, push=14,
                      cancel=("super",), sound="soco_metal", hitstop=10, weapon=True),
        "soco_baixo": Move("soco_baixo", [("agachado", 2), ("soco_baixo", 4), ("agachado", 7)], active=(1,),
                           point="far_hand", radius=18, damage=35, hitstun=14, blockstun=9, push=5, level="baixo",
                           cancel=("rasteira", "especial", "super")),
        "rasteira": Move("rasteira", [("rasteira1", 7), ("rasteira2", 6), ("rasteira1", 15)], active=(1,),
                         point="far_foot", radius=22, damage=65, hitstun=20, blockstun=14, push=8, level="baixo",
                         knockdown=True, cancel=("super",), sound="chute"),
        "voadora": Move("voadora", [("voadora", 40)], active=(0,), point="far_foot", radius=22, damage=75,
                        hitstun=19, blockstun=13, push=7, level="aereo", air=True, sound="chute"),
        "soco_aereo": Move("soco_aereo", [("soco_aereo", 40)], active=(0,), point="far_hand", radius=20, damage=55,
                           hitstun=16, blockstun=11, push=6, level="aereo", air=True),
    }


@dataclass
class Projectile:
    owner: object
    kind: str                   # moeda, basquete, volei
    x: float
    y: float
    vx: float
    vy: float
    gravity: float = 0.0
    radius: int = 14
    damage: int = 80
    level: str = "alto"
    delay: int = 0              # quadros antes de aparecer (as moedas caem uma depois da outra)
    bounces: int = 0
    life: int = 240
    spin: float = 0.0
    dead: bool = False


@dataclass
class Effect:
    kind: str                   # faisca, defesa, poeira, texto, explosao, moeda, rastro
    x: float
    y: float
    life: int
    age: int = 0
    color: tuple = (255, 255, 255)
    text: str = ""
    size: float = 1.0
    vx: float = 0.0
    vy: float = 0.0
    dirx: int = 0               # para que lado o golpe foi (a faísca espirra para lá)


def _boxes_hit(circle, rects):
    cx, cy, r = circle
    for rect in rects:
        nx = max(rect.left, min(cx, rect.right))
        ny = max(rect.top, min(cy, rect.bottom))
        if (nx - cx) ** 2 + (ny - cy) ** 2 <= r * r:
            return True
    return False


class Fighter:
    """Um lutador na arena."""

    def __init__(self, key, slot, side, controls=None):
        self.key = key
        self.spec = SPECS[key]
        self.slot = slot
        self.side = side                    # 0 = começa na esquerda
        self.controls = controls
        self.moves = _moves(key)
        self.max_hp = self.spec.hp
        self.energy = 0.0
        self.wins = 0
        self.sport = 0                      # Cauanzera: basquete → vôlei → 100 metros
        self.reset_round()

    def reset_round(self):
        self.x = W * (0.32 if self.side == 0 else 0.68)
        self.y = 0.0
        self.vx = self.vy = 0.0
        self.facing = 1 if self.side == 0 else -1
        self.hp = self.max_hp
        self.state = "livre"            # livre, pulo, golpe, levou, defendeu, voando, caido, levantando, ko, vitoria
        self.pose = "guarda"
        self.t = 0                      # quadros no estado atual
        self.move = None
        self.move_t = 0
        self.move_hit = False           # o golpe atual já acertou (cada golpe acerta uma vez)
        self.hit_any = False            # acertou alguma coisa (para emendar)
        self.stun = 0
        self.crouch = False
        self.air_attack = False
        self.invuln = 0
        self.buffer = []                # [(ação, quadros que faltam)]
        self.combo = 0                  # golpes seguidos que o OUTRO levou
        self.flash = 0                  # pisca branco quando apanha
        self.walk_phase = 0.0
        self.view = "guarda"            # quadro que aparece na tela (pode ser um quadro de meio)
        self._view_from = None
        self._view_to = "guarda"
        self._view_d = 0
        self._view_last = "guarda"
        self.special = None             # estado do ESPECIAL/SUPER em andamento
        self.bet = None                 # Aryel: resultado da última roleta ("GREEN"/"RED")
        self.last_damage = 0

    # ── entrada ───────────────────────────
    def _held(self, action):
        return self.controls is not None and self.controls.held(action)

    def _pressed(self, action):
        return self.controls is not None and self.controls.pressed(action)

    def stick(self):
        if self.controls is None:
            return 0.0, 0.0
        dx, dy = self.controls.axis()
        return dx, dy

    def dirs(self):
        """(frente, trás, baixo, cima) no lado de quem está virado."""
        dx, dy = self.stick()
        fwd = dx * self.facing > 0.35
        back = dx * self.facing < -0.35
        down = dy > 0.5
        up = dy < -0.6 or self._pressed("dodge") or self._pressed("up")
        return fwd, back, down, up

    def read_buttons(self):
        for action in ("attack", "special", "sprint", "dribble", "super"):
            if self._pressed(action):
                self.buffer.append([action, BUFFER])
        for item in self.buffer:
            item[1] -= 1
        self.buffer = [b for b in self.buffer if b[1] > 0]

    def take_buffer(self, *actions):
        for item in self.buffer:
            if item[0] in actions:
                self.buffer.remove(item)
                return item[0]
        return None

    # ── estado ────────────────────────────
    @property
    def grounded(self):
        return self.y <= 0 and self.vy >= 0

    @property
    def busy(self):
        return self.state not in ("livre",)

    def set_state(self, state, pose=None):
        self.state = state
        self.t = 0
        if pose:
            self.pose = pose

    def start_move(self, name):
        self.move = self.moves[name]
        self.move_t = 0
        self.move_hit = False
        self.state = "golpe"
        self.t = 0
        self.pose = self.move.steps[0][0]
        if self.move.air:
            self.air_attack = True

    def move_step(self):
        """(índice do passo, pose) do golpe atual."""
        t = self.move_t
        for i, (pose, n) in enumerate(self.move.steps):
            if t < n:
                return i, pose
            t -= n
        return len(self.move.steps) - 1, self.move.steps[-1][0]

    def frame(self):
        return Bank.get(self.key, self.pose)

    # ── quadro da tela (com quadros de meio para o movimento ficar liso) ──
    IDLE = ("guarda", "guarda2")
    WALK = ("andar1", "andar2", "andar3", "andar4")

    def update_view(self):
        """Escolhe o quadro da tela. As regras (caixas) usam sempre a pose de verdade; a tela pode
        mostrar um quadro de meio: respirar, andar e a passagem de uma pose para outra."""
        pose = self.pose
        q = luta_poses.QUARTERS
        if pose in self.IDLE and self.state == "livre":
            fam = "idle"
            n = round((1 - math.cos(self.t * math.tau / 56)) / 2 * q)      # respira devagar, sem pulo
            base, target = "guarda", ("guarda" if n == 0 else "guarda2" if n == q else
                                      luta_poses.mid("guarda", "guarda2", n))
        elif pose in self.WALK:
            fam = "walk"
            ph = self.walk_phase % 4
            i = int(ph)
            n = round((ph - i) * q)
            i %= 4                          # -0.0000001 % 4 dá 4.0 no ponto flutuante
            a, b = self.WALK[i], self.WALK[(i + 1) % 4]
            base, target = a, (a if n == 0 else b if n == q else luta_poses.mid(a, b, n))
        else:
            fam, base, target = pose, pose, pose
        if fam != self._view_to:
            self._view_from, self._view_d, self._view_to = self._view_last, 0, fam
        else:
            self._view_d += 1
        frm = self._view_from
        if self._snaps(pose) or frm is None or self._view_d > 1 or not luta_poses.blendable(self.key, frm, base):
            self.view = target
        else:
            self.view = luta_poses.mid(frm, base, 2 + self._view_d)
        self._view_last = base

    def _snaps(self, pose):
        """Golpe saindo e apanhar aparecem na hora (sem quadro de meio): o impacto fica seco."""
        if pose in ("levou", "levou2", "levou_baixo", "voando", "caido"):
            return True
        if self.state == "golpe" and self.move is not None:
            i, _ = self.move_step()
            return i in self.move.active
        return False

    def view_frame(self):
        return Bank.get(self.key, self.view)

    def to_world(self, p):
        return (self.x + (p[0] - R.ROOT_X) * R.U * self.facing, FLOOR - self.y + (p[1] - R.GROUND) * R.U)

    def point(self, name):
        return self.to_world(self.frame()[2][name])

    # ── caixas ────────────────────────────
    def hurtboxes(self):
        if self.state in ("caido", "levantando", "ko") or self.invuln > 0:
            return []
        P = self.frame()[2]
        u = R.U
        out = []
        hx, hy = self.to_world(P["head"])
        out.append(pygame.Rect(hx - 11 * u, hy - 12 * u, 22 * u, 22 * u))
        pts = [self.to_world(P[k]) for k in ("neck", "hip")]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        out.append(pygame.Rect(min(xs) - 11 * u, min(ys) - 2 * u, max(xs) - min(xs) + 22 * u, max(ys) - min(ys) + 6 * u))
        pts = [self.to_world(P[k]) for k in ("hip", "near_knee", "far_knee", "near_ankle", "far_ankle")]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        out.append(pygame.Rect(min(xs) - 5 * u, min(ys), max(xs) - min(xs) + 10 * u, max(ys) - min(ys) + 3 * u))
        return out

    def hitbox(self):
        """(x, y, raio) da ponta do golpe agora, ou None."""
        boxes = self.hitboxes()
        return boxes[-1] if boxes else None

    def hitboxes(self):
        """Círculos de golpe agora: a mão ou o pé e, com arma comprida, o caminho até a ponta."""
        if self.state != "golpe" or self.move is None or self.move_hit:
            return []
        i, _ = self.move_step()
        if i not in self.move.active:
            return []
        x, y = self.point(self.move.point)
        r = self.move.radius
        # o meio do braço ou da perna também bate (de muito perto a mão passa do corpo do outro)
        joint = self.move.point.replace("_hand", "_elbow").replace("_foot", "_knee")
        jx, jy = self.point(joint)
        inner = [(jx, jy, r * 0.8), (jx + (x - jx) * 0.5, jy + (y - jy) * 0.5, r * 0.8)]
        if not self.move.reach:
            return inner + [(x, y, r)]
        ang = self.frame()[2].get(self.move.point + "_dir", 90)
        d = R.dirv(ang)
        return inner + [(x + d[0] * self.move.reach * k * self.facing, y + d[1] * self.move.reach * k, r)
                          for k in (0.0, 0.5, 1.0)]

    def pushbox(self):
        w = self.spec.push_w
        return pygame.Rect(self.x - w, FLOOR - self.y - 150, w * 2, 150)

    def blocking(self, attacker_x, level):
        """Defende este golpe? (segurando para trás ou DEFESA, no chão e sem estar atacando)."""
        if self.state not in ("livre", "defendeu") or not self.grounded:
            return False
        dx, dy = self.stick()
        away = 1 if attacker_x < self.x else -1             # trás = para longe de quem bate
        back = dx * away > 0.35 or self._held("mark")
        if not back:
            return False
        crouch = dy > 0.5
        if level == "baixo":
            return crouch
        if level == "aereo":
            return not crouch
        return True


class Fight:
    """Uma luta inteira (melhor de 3 rounds)."""

    def __init__(self, keys=("aryel", "cauanzera"), slots=(1, 2), controls=(None, None), seed=None,
                 sound=None, buzz=None):
        self.rng = random.Random(seed)
        self.fighters = [Fighter(keys[i], slots[i], i, controls[i]) for i in range(2)]
        self.sound = sound or (lambda name, volume=0.5, at=None: None)
        self.buzz = buzz or (lambda slot, pattern: None)
        self.round = 1
        self.state = "intro"            # intro, luta, ko, fim
        self.t = 0
        self.clock = ROUND_FRAMES
        self.freeze = 0                 # pausa de impacto
        self.super_freeze = 0
        self.super_user = None
        self.shake = 0
        self.projectiles = []
        self.effects = []
        self.round_winner = None        # None = empate
        self.winner = None
        self.results = []               # vencedor de cada round (índice ou None)
        self.frame = 0
        for f in self.fighters:
            Bank.preload(f.key)

    def other(self, f):
        return self.fighters[1 - self.fighters.index(f)]

    # ── laço ──────────────────────────────
    def update(self):
        moved = self._step()
        if moved is not False:
            for f in self.fighters:
                f.update_view()

    def _step(self):
        self.frame += 1
        self.effects = [e for e in self.effects if self._age(e)]
        if self.shake:
            self.shake -= 1
        if self.super_freeze:
            self.super_freeze -= 1
            if self.super_freeze == 0:
                self._super_go(self.super_user)
            return False
        if self.freeze:
            self.freeze -= 1
            return False
        self.t += 1
        if self.state == "intro":
            for f in self.fighters:
                f.pose = "guarda2" if (self.t // 30) % 2 else "guarda"
            if self.t >= INTRO_FRAMES:
                self.state = "luta"
                self.t = 0
            return
        if self.state == "fim":
            for f in self.fighters:
                self._update_fighter(f, inputs=False)
            return
        if self.state == "luta":
            self.clock -= 1
            for f in self.fighters:
                f.read_buttons()
        for f in self.fighters:
            self._update_fighter(f, inputs=self.state == "luta")
        self._push_apart()
        self._face()
        if self.state == "luta":
            self._hits()
        self._update_projectiles()
        if self.state == "luta":
            self._check_round_end()
        elif self.state == "ko":
            self.update_ko_poses()
            if self.t >= KO_FRAMES:
                self._next_round()

    @staticmethod
    def _age(e):
        e.age += 1
        e.x += e.vx
        e.y += e.vy
        if e.kind == "moeda":
            e.vy += 0.4
        elif e.kind == "lasca":
            e.vy += 0.5
            e.vx *= 0.92
        return e.age < e.life

    # ── cada lutador ──────────────────────
    def _update_fighter(self, f, inputs=True):
        f.t += 1
        if f.flash:
            f.flash -= 1
        if f.invuln:
            f.invuln -= 1
        opp = self.other(f)
        st = f.state
        if st in ("livre", "pulo", "golpe", "especial", "defendeu"):
            f.combo = 0                     # voltou a agir: a sequência que ele levou acabou
        if st == "livre":
            self._update_free(f, opp, inputs)
        elif st == "pulo":
            self._update_jump(f, opp, inputs)
        elif st == "golpe":
            self._update_move(f, opp)
        elif st == "especial":
            self._update_special(f, opp)
        elif st in ("levou", "defendeu"):
            f.stun -= 1
            f.x += f.vx
            f.vx *= 0.82
            if f.y > 0 or f.vy < 0:
                self._gravity(f)
            if f.stun <= 0 and f.grounded:
                f.set_state("livre", "guarda")
        elif st == "voando":
            f.x += f.vx
            self._gravity(f)
            if f.grounded and f.t > 4:
                f.y = 0
                f.vx = 0
                self.sound("passo_pesado", 0.5, f.x)
                self._dust(f.x)
                f.set_state("ko" if f.hp <= 0 else "caido", "caido")
        elif st == "caido":
            if f.t >= 38 and f.hp > 0:
                f.set_state("levantando", "levantando")
                f.invuln = 20
        elif st == "levantando":
            if f.t >= 16:
                f.set_state("livre", "guarda")
        elif st == "ko":
            f.pose = "caido"
        elif st == "vitoria":
            f.pose = "vitoria2" if (f.t // 24) % 2 else "vitoria"
        f.x = max(WALL_L, min(WALL_R, f.x))

    def _gravity(self, f):
        f.vy += GRAVITY
        f.y -= f.vy
        if f.y <= 0:
            f.y = 0
            f.vy = 0

    def _update_free(self, f, opp, inputs):
        fwd, back, down, up = f.dirs() if inputs else (False, False, False, False)
        f.crouch = down
        if inputs and self._try_specials(f):
            return
        if inputs:
            act = f.take_buffer("attack", "special", "sprint")
            if act:
                if act == "sprint" or act == "attack" and fwd and not down:
                    f.start_move("forte")
                elif act == "attack":
                    f.start_move("soco_baixo" if down else "soco")
                else:
                    f.start_move("rasteira" if down else "chute")
                self.sound("dash", 0.18, f.x)
                return
        if up and inputs:
            f.vy = JUMP_VY
            f.y = 0.1
            f.vx = (3.4 if fwd else -3.0 if back else 0.0) * f.facing
            f.air_attack = False
            f.set_state("pulo", "pulo")
            return
        f.vx = 0
        if down:
            blocking_now = back and self._threat(opp, f)
            f.pose = "defesa_baixa" if blocking_now else "agachado"
            return
        if fwd:
            f.x += f.spec.walk * f.facing
            f.walk_phase += f.spec.walk * 0.06
        elif back:
            f.x -= f.spec.walk * 0.8 * f.facing
            f.walk_phase -= f.spec.walk * 0.05
        if (back or f._held("mark")) and self._threat(opp, f):
            f.pose = "defesa"
        elif fwd or back:
            f.pose = ("andar1", "andar2", "andar3", "andar4")[int(f.walk_phase) % 4]
            step = int(f.walk_phase) // 2            # um passo a cada meia volta: levanta poeirinha
            if step != getattr(f, "_step", step):
                self.effects.append(Effect("poeira", f.x - 18 * f.facing * (1 if fwd else -1), FLOOR - 4, 22,
                                           color=(176, 150, 112), vx=-0.6 * f.facing * (1 if fwd else -1),
                                           vy=-0.3, size=0.8))
            f._step = step
        else:
            f.pose = "guarda2" if (f.t // 28) % 2 else "guarda"

    def _threat(self, opp, me):
        """O outro está atacando (ou vem projétil): a pose de defesa aparece antes do golpe chegar."""
        if opp.state in ("golpe", "especial") and abs(opp.x - me.x) < 330:
            return True
        return any(p.owner is opp and abs(p.x - me.x) < 260 for p in self.projectiles)

    def _update_jump(self, f, opp, inputs):
        f.x += f.vx
        self._gravity(f)
        f.pose = "pulo" if f.vy < 2 else "queda"
        if inputs and not f.air_attack:
            act = f.take_buffer("attack", "special", "sprint")
            if act:
                f.start_move("voadora" if act == "special" else "soco_aereo")
                return
        if f.y <= 0 and f.t > 2:
            self._land(f)

    def _land(self, f):
        f.y = 0
        f.vy = 0
        f.vx = 0
        f.set_state("livre", "guarda")
        self._dust(f.x)

    def _update_move(self, f, opp):
        m = f.move
        f.move_t += 1
        if m.air:
            f.x += f.vx
            self._gravity(f)
            i, pose = f.move_step()
            f.pose = pose
            if f.y <= 0 and f.move_t > 1:
                f.move = None
                self._land(f)
            return
        i, pose = f.move_step()
        f.pose = pose
        if f.move_hit or f.hit_any:
            # acertou: dá para emendar o próximo golpe
            nxt = f.take_buffer("attack", "special", "sprint", "dribble", "super")
            if nxt:
                fwd, back, down, up = f.dirs()
                name = {"attack": "soco_baixo" if down else "forte" if fwd else "soco",
                        "special": "rasteira" if down else "chute", "sprint": "forte",
                        "dribble": "especial", "super": "super"}[nxt]
                if name in m.cancel:
                    if name == "especial" and self._start_special(f):
                        return
                    if name == "super" and self._start_super(f):
                        return
                    if name in f.moves:
                        f.hit_any = False
                        f.start_move(name)
                        return
        if f.move_t >= m.length:
            f.move = None
            f.hit_any = False
            f.set_state("livre", "agachado" if f.crouch else "guarda")

    # ── ESPECIAL e SUPER ──────────────────
    def _try_specials(self, f):
        act = f.take_buffer("dribble", "super")
        if act == "dribble":
            return self._start_special(f)
        if act == "super":
            return self._start_super(f)
        return False

    def _start_special(self, f):
        if f.energy < SPECIAL_COST - 1e-6:
            self.sound("cancel", 0.3)
            return False
        f.energy -= SPECIAL_COST
        f.move = None
        f.move_hit = False
        f.state = "especial"
        f.t = 0
        if f.key == "aryel":
            f.special = {"kind": "aposta"}
            f.pose = "aposta1"
            self.sound("rolo", 0.5, f.x)
        else:
            kind = ("basquete", "volei", "corrida")[f.sport % 3]
            f.sport += 1
            f.special = {"kind": kind}
            if kind == "volei":
                f.vy = -14
                f.y = 0.1
                f.vx = 2.0 * f.facing
            self.sound("ability", 0.45, f.x)
        label = {"aposta": "APOSTA", "basquete": "BASQUETE", "volei": "VÔLEI", "corrida": "100 METROS"}
        self._text(f.x, FLOOR - 250, label[f.special["kind"]], f.spec.color)
        return True

    def _start_super(self, f):
        if f.energy < SUPER_COST - 1e-6:
            self.sound("cancel", 0.3)
            return False
        f.energy -= SUPER_COST
        f.move = None
        f.state = "especial"
        f.t = 0
        f.special = {"kind": "moto" if f.key == "aryel" else "enterrada", "super": True, "go": False}
        f.pose = "moto" if f.key == "aryel" else "basquete1"
        f.invuln = SUPER_FREEZE + 12
        self.super_freeze = SUPER_FREEZE
        self.super_user = f
        self.sound("carga", 0.6, f.x)
        self.buzz(f.slot, "super")
        return True

    def _super_go(self, f):
        if f is None or f.state != "especial":
            return
        f.special["go"] = True
        f.t = 0
        opp = self.other(f)
        if f.special["kind"] == "moto":
            self.sound("buzina", 0.6, f.x)
        else:
            f.special["from"] = f.x
            f.special["to"] = max(WALL_L, min(WALL_R, opp.x - 30 * f.facing))
            f.y = 0.1
            self.sound("dash", 0.6, f.x)

    def _update_special(self, f, opp):
        sp = f.special
        kind = sp["kind"]
        t = f.t
        if kind == "aposta":
            f.pose = "aposta1" if t < 10 else "aposta2"
            if t == 44:
                if self.rng.random() < 0.7:
                    f.bet = "GREEN"
                    self.sound("compra", 0.6, f.x)
                    self._text(f.x, FLOOR - 270, "GREEN!", (90, 230, 120))
                    for i, dx in enumerate((-46, 0, 46)):
                        self.projectiles.append(Projectile(f, "moeda", opp.x + dx, FLOOR - 470, 0, 2, gravity=0.45,
                                                           radius=16, damage=40, level="aereo", delay=i * 9))
                else:
                    f.bet = "RED"
                    self.sound("explosion", 0.6, f.x)
                    self._text(f.x, FLOOR - 270, "RED!", (240, 70, 70))
                    self._explosion(f.x, FLOOR - 160)
                    self._damage(f, 70, None)
                    f.vx = -5 * f.facing
                    f.stun = 24
                    f.set_state("levou" if f.hp > 0 else "voando", "levou2")
                    if f.hp <= 0:
                        f.vy = -6
                        f.y = 0.1
                    return
            if t >= 58:
                f.special = None
                f.set_state("livre", "guarda")
            return
        if kind == "basquete":
            f.pose = "basquete1" if t < 12 else "basquete2"
            if t == 12:
                x, y = f.point("far_hand")
                self.projectiles.append(Projectile(f, "basquete", x, y - 10, 7.5 * f.facing, -8.5, gravity=0.42,
                                                   radius=15, damage=95, bounces=1))
                self.sound("arremesso", 0.5, f.x)
            if t >= 30:
                f.special = None
                f.set_state("livre", "guarda")
            return
        if kind == "volei":
            f.x += f.vx
            self._gravity(f)
            f.pose = "volei1" if t < 16 else "volei2"
            if t == 16:
                x, y = f.point("near_hand")
                self.projectiles.append(Projectile(f, "volei", x + 10 * f.facing, y, 9 * f.facing, 5.5,
                                                   gravity=0.12, radius=15, damage=95, level="aereo"))
                self.sound("cravada", 0.5, f.x)
            if f.y <= 0 and t > 3:
                f.special = None
                self._land(f)
            return
        if kind == "corrida":
            if t < 8:
                f.pose = "corrida1" if (t // 4) % 2 == 0 else "corrida2"
                return
            if t < 34 and not sp.get("hit"):
                f.pose = ("corrida1", "corrida2")[(t // 4) % 2] if t < 30 else "ombrada"
                f.x += 11 * f.facing
                if t % 5 == 0:
                    self._dust(f.x - 30 * f.facing, small=True)
                hit = (f.x + 34 * f.facing, FLOOR - f.y - 120, 34)
                if self._special_hit(f, opp, hit, damage=105, knockdown=True, sound="chute_forte"):
                    sp["hit"] = True
                    sp["end"] = t
                return
            f.pose = "ombrada" if t < sp.get("end", 34) + 10 else "guarda"
            if t >= sp.get("end", 34) + 16:
                f.special = None
                f.set_state("livre", "guarda")
            return
        if kind == "moto":
            if not sp["go"]:
                f.pose = "moto"
                return
            f.pose = "moto_grau" if t > 6 else "moto"
            if not sp.get("hit"):
                f.x += 13 * f.facing
                if t % 3 == 0:
                    self._dust(f.x - 60 * f.facing, small=True)
                hit = (f.x + 60 * f.facing, FLOOR - 70, 56)
                if self._special_hit(f, opp, hit, damage=270, knockdown=True, sound="explosion", chip=0.15):
                    sp["hit"] = True
                    sp["end"] = t
            wall = f.x <= WALL_L + 1 or f.x >= WALL_R - 1
            if t >= 60 or wall or sp.get("hit") and t > sp["end"] + 14:
                f.special = None
                f.set_state("livre", "guarda")
            return
        if kind == "enterrada":
            if not sp["go"]:
                f.pose = "basquete1"
                return
            n = 40
            k = min(1.0, t / n)
            f.x = sp["from"] + (sp["to"] - sp["from"]) * k
            f.y = max(0.0, 4 * 250 * k * (1 - k)) if k < 1 else 0
            f.pose = "enterrada1" if k < 0.7 else "enterrada2"
            if k >= 1 and not sp.get("landed"):
                sp["landed"] = True
                self.shake = 14
                self.sound("cravada", 0.8, f.x)
                self._dust(f.x)
                self._dust(f.x + 40)
                self._dust(f.x - 40)
                hit = (f.x + 30 * f.facing, FLOOR - 90, 86)
                self._special_hit(f, opp, hit, damage=285, knockdown=True, sound="explosion", chip=0.15,
                                  level="aereo")
            if t >= n + 22:
                f.special = None
                f.y = 0
                f.set_state("livre", "guarda")

    def _special_hit(self, f, opp, circle, damage, knockdown=False, sound="golpe", chip=0.1, level="alto"):
        if not _boxes_hit(circle, opp.hurtboxes()):
            return False
        move = Move("especial", [], damage=damage, hitstun=24, blockstun=18, push=12, level=level,
                    knockdown=knockdown, hitstop=10, sound=sound, chip=chip)
        self._apply_hit(f, opp, move, circle[0], circle[1])
        return True

    # ── contato ───────────────────────────
    def _hits(self):
        for f in self.fighters:
            opp = self.other(f)
            hurt = opp.hurtboxes()
            for box in f.hitboxes():
                if _boxes_hit(box, hurt):
                    f.move_hit = True
                    f.hit_any = True
                    self._apply_hit(f, opp, f.move, box[0], box[1])
                    break

    def _apply_hit(self, f, opp, move, x, y):
        if opp.blocking(f.x, move.level):
            opp.set_state("defendeu", "defesa_baixa" if opp.stick()[1] > 0.5 else "defesa")
            opp.stun = move.blockstun
            opp.vx = move.push * 0.8 * (1 if opp.x > f.x else -1)
            chip = round(move.damage * move.chip)
            if chip:
                self._damage(opp, chip, f, ko_ok=False)
            f.energy = min(MAX_ENERGY, f.energy + move.damage / 900)
            opp.energy = min(MAX_ENERGY, opp.energy + move.damage / 1100)
            self.freeze = max(self.freeze, move.hitstop - 2)
            away = 1 if opp.x > f.x else -1
            self.effects.append(Effect("defesa", x, y, 14, color=(150, 200, 255), dirx=away))
            self._chips(x, y, -away, 4, (190, 226, 255))
            self.sound("toco", 0.45, x)
            self._push_off_wall(f, opp, move.push * 0.5)
            opp.combo = 0
            return
        opp.combo += 1
        scale = max(0.5, 1.0 - 0.1 * (opp.combo - 1))
        dmg = round(move.damage * scale)
        self._damage(opp, dmg, f)
        f.energy = min(MAX_ENERGY, f.energy + move.damage / 420)
        opp.energy = min(MAX_ENERGY, opp.energy + move.damage / 900)
        self.freeze = max(self.freeze, move.hitstop)
        self.shake = max(self.shake, 4 + move.hitstop // 2)
        away = 1 if opp.x > f.x else -1
        self.effects.append(Effect("faisca", x, y, 16, color=(255, 236, 160), size=1.0 + move.damage / 120, dirx=away))
        self._chips(x, y, away, 5 + move.damage // 40, (255, 214, 120))
        for i in range(2):                         # o pé de quem apanhou arrasta no chão
            self.effects.append(Effect("poeira", opp.x + away * (6 + i * 16), FLOOR - 4, 26 + i * 4,
                                       color=(176, 150, 112), vx=away * (1.4 + i * 0.6), vy=-0.4 - i * 0.3,
                                       size=1.0 + move.damage / 200))
        self.sound(move.sound, 0.55, x)
        self.buzz(opp.slot, "big_hit" if move.damage >= 100 else "hit")
        opp.flash = 6
        if opp.state in ("especial",) and opp.special and opp.special.get("super"):
            pass                                        # SUPER não é interrompido por golpe comum
        if opp.hp <= 0 or move.knockdown or opp.y > 0:
            opp.move = None
            opp.special = None
            opp.set_state("voando", "voando")
            opp.vx = (4.5 + move.push * 0.2) * away
            opp.vy = -9 if opp.hp > 0 else -11
            opp.y = max(opp.y, 0.1)
        else:
            opp.move = None
            opp.special = None
            crouched = opp.crouch and opp.state == "livre"
            opp.set_state("levou", "levou_baixo" if crouched else "levou2" if move.damage >= 90 else "levou")
            opp.stun = move.hitstun
            opp.vx = move.push * away
        self._push_off_wall(f, opp, move.push)

    def _push_off_wall(self, f, opp, amount):
        """Quem apanha encostado na parede não sai do lugar: quem bate é que volta."""
        if opp.x <= WALL_L + 2 or opp.x >= WALL_R - 2:
            f.x -= amount * 2 * (1 if opp.x > f.x else -1)

    def _damage(self, f, amount, by, ko_ok=True):
        f.hp = max(0 if ko_ok else 1, f.hp - amount)
        f.last_damage = amount

    # ── projéteis ─────────────────────────
    def _update_projectiles(self):
        for p in self.projectiles:
            if p.delay > 0:
                p.delay -= 1
                continue
            p.life -= 1
            p.vy += p.gravity
            p.x += p.vx
            p.y += p.vy
            p.spin += p.vx * 0.08 + 0.1
            if p.y >= FLOOR - p.radius:
                if p.bounces > 0:
                    p.bounces -= 1
                    p.y = FLOOR - p.radius
                    p.vy *= -0.55
                    self.sound("quique", 0.4, p.x)
                else:
                    p.dead = True
                    if p.kind == "moeda":
                        self.effects.append(Effect("moeda", p.x, FLOOR - 4, 30, color=(250, 210, 80), vy=-3,
                                                   vx=self.rng.uniform(-2, 2)))
                        self.sound("compra", 0.25, p.x)
                    else:
                        self._dust(p.x, small=True)
            if p.x < -60 or p.x > W + 60 or p.life <= 0:
                p.dead = True
            if p.dead or self.state != "luta":
                continue
            target = self.other(p.owner)
            if _boxes_hit((p.x, p.y, p.radius), target.hurtboxes()):
                p.dead = True
                move = Move(p.kind, [], damage=p.damage, hitstun=18, blockstun=14, push=8, level=p.level,
                            hitstop=7, sound="quique" if p.kind != "moeda" else "soco_metal", chip=0.12)
                self._apply_hit(p.owner, target, move, p.x, p.y)
        self.projectiles = [p for p in self.projectiles if not p.dead]

    # ── corpo a corpo: ninguém atravessa ninguém ───────
    def _push_apart(self):
        a, b = self.fighters
        if a.state == "caido" or b.state == "caido":
            return
        if a.y > 120 or b.y > 120:                      # um passa por cima do outro no pulo alto
            return
        ra, rb = a.pushbox(), b.pushbox()
        if not ra.colliderect(rb):
            return
        overlap = min(ra.right, rb.right) - max(ra.left, rb.left)
        left, right = (a, b) if a.x <= b.x else (b, a)
        if a.x == b.x:
            left, right = (a, b) if a.side == 0 else (b, a)
        left.x -= overlap / 2
        right.x += overlap / 2
        # na parede: o outro é que sai
        if left.x < WALL_L:
            right.x += WALL_L - left.x
            left.x = WALL_L
        if right.x > WALL_R:
            left.x -= right.x - WALL_R
            right.x = WALL_R

    def _face(self):
        a, b = self.fighters
        for f, o in ((a, b), (b, a)):
            if f.state in ("livre",) and f.grounded and abs(o.x - f.x) > 2:
                f.facing = 1 if o.x > f.x else -1

    # ── rounds ────────────────────────────
    def _check_round_end(self):
        a, b = self.fighters
        dead = [f for f in self.fighters if f.hp <= 0]
        if dead:
            winner = None if len(dead) == 2 else self.fighters.index(self.other(dead[0]))
            self._end_round(winner, "NOCAUTE!")
        elif self.clock <= 0:
            ra, rb = a.hp / a.max_hp, b.hp / b.max_hp
            winner = None if abs(ra - rb) < 1e-9 else (0 if ra > rb else 1)
            self._end_round(winner, "TEMPO!")

    def _end_round(self, winner, title):
        self.state = "ko"
        self.t = 0
        self.round_winner = winner
        self.results.append(winner)
        self.ko_title = title
        self.freeze = 30 if title == "NOCAUTE!" else 0
        self.projectiles = []
        self.sound("apito_longo" if title == "TEMPO!" else "explosion", 0.5)
        if winner is not None:
            self.fighters[winner].wins += 1
        for f in self.fighters:
            f.buffer = []

    def round_title(self):
        if self.round_winner is None:
            return "EMPATE"
        return f"{self.fighters[self.round_winner].spec.name.upper()} VENCE"

    def _next_round(self):
        a, b = self.fighters
        done = max(a.wins, b.wins) >= ROUNDS_TO_WIN or self.round >= MAX_ROUNDS
        if done:
            self.state = "fim"
            self.t = 0
            if a.wins == b.wins:
                self.winner = None
            else:
                self.winner = 0 if a.wins > b.wins else 1
                w = self.fighters[self.winner]
                if w.state not in ("caido", "voando", "ko"):
                    w.set_state("vitoria", "vitoria")
            return
        self.round += 1
        self.state = "intro"
        self.t = 0
        self.clock = ROUND_FRAMES
        self.round_winner = None
        for f in self.fighters:
            f.reset_round()

    def update_ko_poses(self):
        """No fim do round, quem venceu comemora (se estiver de pé)."""
        if self.state != "ko" or self.round_winner is None:
            return
        w = self.fighters[self.round_winner]
        if w.state == "livre" and self.t > 40:
            w.set_state("vitoria", "vitoria")

    # ── efeitos ───────────────────────────
    def _text(self, x, y, text, color):
        self.effects.append(Effect("texto", x, y, 60, color=color, text=text, vy=-0.6))

    def _chips(self, x, y, away, n, color):
        """Lascas de luz que espirram do ponto de contato, para o lado do golpe."""
        for _ in range(n):
            self.effects.append(Effect("lasca", x, y, self.rng.randint(12, 20), color=color,
                                       vx=away * self.rng.uniform(2.5, 8.0), vy=-self.rng.uniform(1.0, 6.5)))

    def _dust(self, x, small=False):
        for i in range(3 if small else 6):
            self.effects.append(Effect("poeira", x + self.rng.uniform(-20, 20), FLOOR - 4, 24 + i * 2,
                                       color=(196, 176, 140), vx=self.rng.uniform(-1.6, 1.6),
                                       vy=-self.rng.uniform(0.2, 1.2), size=0.6 if small else 1.0))

    def _explosion(self, x, y):
        self.effects.append(Effect("explosao", x, y, 30, color=(255, 120, 60)))
        self.shake = 12

    # ── o que o HUD mostra ────────────────
    def seconds(self):
        return max(0, math.ceil(self.clock / 60))
