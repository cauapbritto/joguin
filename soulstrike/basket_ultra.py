"""Basquete 1 x 1 com poder demais: ULTRA de cada herói, orbes de poder e as regras do modo.

No 1 x 1 (modo "basket1") o SUPER volta em 4 s, a barra de ULTRA de cada herói enche com cesta, toco
e roubo (e um pouco ao levar cesta), quem faz 2 cestas seguidas pega fogo e a cada 12 s aparece um
orbe na quadra. A partida é um tempo de 3 minutos ou 21 pontos, o que vier primeiro.

O ULTRA sai apertando SUPER com a barra cheia. Os de ataque que pegam no adversário têm um aviso
curto (CAST_FRAMES): quem faz a ESQUIVA (CORTE) bem nessa hora anula o ULTRA, e quem está com um
ULTRA de defesa ligado (Guerreiro, Paredão, Tanque) também segura. A BasketballMatch chama os
ganchos daqui; os efeitos que duram ficam em timers do lutador (zerados em setup_fighter).
"""
import math
import random

import pygame

from . import config, theme
from .soccer_assist import unit

FPS = config.FPS
SOLO_SECONDS = 180                 # um tempo só de 3 minutos
SOLO_TARGET = 21                   # ou 21 pontos
SOLO_SUPER = 4 * FPS               # o SUPER volta 4 s depois que o efeito acaba (no 2 x 2, 8 s fixos)
SOLO_HACK_FREEZE = 2 * FPS         # o Hack trava o único adversário por 2 s
SOLO_FIRE_STREAK = 2               # 2 cestas seguidas pegam fogo (no 2 x 2, 3)
GAIN = {"cesta": 0.3, "toco": 0.3, "roubo": 0.3, "levou": 0.1}
CAST_FRAMES = 24                   # 0,4 s de aviso antes do ULTRA que pega no adversário
DODGE_WINDOW = 14                  # a esquiva vale para anular por tantos quadros
ORB_EVERY = 12 * FPS
ORB_LIFE = 10 * FPS                # o orbe some se ninguém pegar
ORB_RADIUS = 14

# orbes: (rótulo, cor, quadros do efeito)
ORBS = {
    "fogo": ("FOGO", (255, 140, 40), 10 * FPS),
    "ima": ("ÍMÃ", (210, 80, 220), 8 * FPS),
    "turbo": ("TURBO", (90, 220, 250), 4 * FPS),
    "escudo": ("ESCUDO", (236, 230, 220), 12 * FPS),
}
ORB_ORDER = ("fogo", "ima", "turbo", "escudo")

TIMERS = ("dodge_t", "guard_timer", "royal_timer", "wall_ultra", "rain_timer", "light_timer",
          "spark_timer", "capo_timer", "capo_cd", "killer_timer", "invert_timer", "clone_timer",
          "exo_max", "turbo_moto", "shield_timer", "magnet_timer", "eclipsed", "touch_cd")


def effect_frames(power):
    """Quanto dura o efeito do SUPER (0 para os que são na hora)."""
    if hasattr(power, "FREEZE"):
        return power.TYPING + SOLO_HACK_FREEZE          # Hack: digitar e travar
    return getattr(power, "FRAMES", 0) + getattr(power, "SOLO_EXTRA", 0)


def setup_fighter(f):
    f.ultra = 0.0                  # barra de ULTRA (1.0 = pronta)
    f.haunt_shots = 0              # Assombração: arremessos que atravessam tudo
    f.capo_left = 0                # Roda de Capoeira: canetas que faltam
    f.ice_v = (0.0, 0.0)           # Inverno: o embalo de quem escorrega
    f.ultra_dunk_value = 0         # enterrada que vale 3 (Enterrada do Meio, Exo Máximo)
    f.thunder = False              # a enterrada é a do Trovão Divino (derruba quem está embaixo)
    f.super_total = SOLO_SUPER
    f.titan = False                # Titã Colossal: derruba quem chega perto
    for name in TIMERS:
        setattr(f, name, 0)


def tick_fighter(f):
    for name in TIMERS:
        value = getattr(f, name)
        if value > 0:
            setattr(f, name, value - 1)
    if f.capo_timer == 0:
        f.capo_left = 0


def gain(match, f, kind):
    """Enche a barra de ULTRA (só no 1 x 1)."""
    if not match.solo or f is None or match.warmup:
        return
    before = f.ultra
    f.ultra = min(1.0, f.ultra + GAIN[kind])
    if before < 1.0 <= f.ultra:
        match.popup(f.x, f.y - 110, "ULTRA PRONTO!", theme.BRASS)
        match.assets.play("confirm", 0.4)


# ── esquiva anula, defesa segura ─────────────
def mark_dodge(f):
    f.dodge_t = DODGE_WINDOW


def lands(match, user, foe):
    """O ULTRA de ataque pega em `foe`? A esquiva na hora certa anula; um ULTRA de defesa segura."""
    if foe.dodge_t > 0:
        foe.dodge_t = 0
        foe.perfect_flash = 18
        match.popup(foe.x, foe.y - 96, "ANULOU!", (240, 248, 255))
        match.burst(foe.x, foe.y - 14, (230, 244, 255), 14, speed=4)
        match.assets.play("click", 0.5)
        return False
    if foe.guard_timer > 0:
        match.popup(foe.x, foe.y - 96, "SEGUROU O ULTRA", theme.BONE)
        match.burst(foe.x, foe.y - 20, (236, 230, 220), 10, speed=3)
        return False
    return True


# ── os ULTRAs ────────────────────────────────
class Ultra:
    name = ""
    description = ""
    kind = "ataque"
    needs_ball = False
    targets = False                 # pega no adversário: a esquiva na hora certa anula
    instant = False                 # pega na hora em que sai: antes, um aviso curto (CAST_FRAMES)
    color = theme.BRASS

    def ready(self, user, match):
        return not self.needs_ball or match.holder is user

    def activate(self, user, match):
        raise NotImplementedError

    def worth(self, user, match):
        return True


def _foe(user, match):
    foes = match.foes_of(user)
    return min(foes, key=user.distance_to) if foes else None


def _dist_hoop(user, match):
    hx, hy = match.hoop_pos(match.hoop_of(user.team))
    return math.hypot(hx - user.x, hy - user.y)


class MarcacaoReal(Ultra):
    name = "MARCAÇÃO REAL"
    description = "Gruda por 6 s, e cada roubo deixa o adversário tonto."
    kind = "defesa"
    color = (150, 196, 255)

    def activate(self, user, match):
        user.glue_timer = user.royal_timer = user.guard_timer = 6 * FPS
        match.burst(user.x, user.y - 10, self.color, 26, speed=5)

    def worth(self, user, match):
        owner = match.holder
        return owner is not None and owner.team != user.team


class MuralhaDoAro(Ultra):
    name = "MURALHA DO ARO"
    description = "Por 6 s, toda bola no aro dele leva toco, até enterrada."
    kind = "defesa"
    color = (236, 230, 220)

    def activate(self, user, match):
        from .basket_powers import TocoVoador
        TocoVoador().activate(user, match)            # vai para o aro
        user.wall_timer = user.wall_ultra = user.guard_timer = 6 * FPS

    def worth(self, user, match):
        owner = match.holder
        return owner is not None and owner.team != user.team and _dist_hoop(owner, match) < 700


class Cofre(Ultra):
    name = "COFRE"
    description = "Tampa o aro por 8 s, e a bola que bate volta para a mão dele."
    kind = "defesa"
    color = (150, 226, 240)

    def activate(self, user, match):
        side = 1 - match.hoop_of(user.team)
        match.lids[side] = 8 * FPS
        match.vault[side] = user
        user.guard_timer = 8 * FPS
        hx, hy = match.hoop_pos(side)
        match.burst(hx, hy - match.RIM_Z, self.color, 30, speed=5)

    def worth(self, user, match):
        owner = match.holder
        return owner is not None and owner.team != user.team


class TitaColossal(Ultra):
    name = "TITÃ COLOSSAL"
    description = "Gigante por 6 s, a quadra treme e quem chega perto cai."
    color = (200, 160, 110)

    def activate(self, user, match):
        user.giant_timer = 6 * FPS
        user.radius = 30
        user.titan = True
        match.camera.shake(10)

    def worth(self, user, match):
        foe = _foe(user, match)
        return foe is not None and user.distance_to(foe) < 260


class Inverno(Ultra):
    instant = True
    name = "INVERNO"
    description = "A quadra congela por 5 s: o adversário escorrega e a faixa verde dele quase some."
    targets = True
    color = (200, 236, 250)

    def activate(self, user, match):
        hit = False
        for foe in match.foes_of(user):
            if lands(match, user, foe):
                foe.slow_timer = max(foe.slow_timer, 5 * FPS)
                foe.frost_timer = max(foe.frost_timer, 5 * FPS)
                hit = True
        if hit:
            match.winter = [user, 5 * FPS]
        match.burst(user.x, user.y - 6, self.color, 40, speed=9)
        match.camera.shake(5)


class Ancora(Ultra):
    instant = True
    name = "ÂNCORA"
    description = "Puxa a bola e o adversário junto, que fica preso por 2 s."
    targets = True
    color = (176, 180, 192)

    def ready(self, user, match):
        return match.holder is not user

    def activate(self, user, match):
        foe = _foe(user, match)
        if foe is None or not lands(match, user, foe):
            return
        ux, uy = unit(foe.x - user.x, foe.y - user.y)
        x, y = match.arena.free_spot(user.x + ux * 40, user.y + uy * 40, foe.radius)
        steps = int(user.distance_to(foe) // 14)
        for i in range(steps):                         # a corrente
            t = i / max(1, steps)
            match.burst(user.x + (foe.x - user.x) * t, user.y - 20 + (foe.y - user.y) * t,
                        self.color, 1, speed=0.5)
        foe.x, foe.y = x, y
        foe.prev_pos = (x, y)
        foe.vx = foe.vy = 0.0
        foe.stun_timer = max(foe.stun_timer, 2 * FPS)     # preso (a âncora segura até no exo)
        if match.holder is not None:
            match.release_ball(match.holder, 40)
        match.grab(user)                               # a bola vem junto, até do ar
        match.popup(foe.x, foe.y - 80, "PRESO", theme.BONE)

    def worth(self, user, match):
        foe = _foe(user, match)
        return foe is not None and match.holder is foe and user.distance_to(foe) < 500


class TelaAzul(Ultra):
    instant = True
    name = "TELA AZUL"
    description = "O adversário trava por 3 s e depois joga 3 s com o controle invertido."
    targets = True
    color = (60, 110, 230)

    def activate(self, user, match):
        for foe in match.foes_of(user):
            if not lands(match, user, foe):
                continue
            foe.hack_timer = max(foe.hack_timer, 3 * FPS)
            foe.invert_timer = 6 * FPS
            if match.holder is foe:
                match.release_ball(foe, 40)
                match.ball.vz = 2.0
            match.popup(foe.x, foe.y - 90, "TELA AZUL", (120, 170, 255))
        match.burst(user.x, user.y - 30, self.color, 24, speed=5)

    def worth(self, user, match):
        owner = match.holder
        return owner is not None and owner.team != user.team


class ChuvaDeTres(Ultra):
    name = "CHUVA DE TRÊS"
    description = "Faixa verde inteira por 6 s, e cesta de 3 vale 4."
    color = (255, 170, 60)

    def activate(self, user, match):
        user.hot_timer = user.rain_timer = 6 * FPS
        match.burst(user.x, user.y - 30, self.color, 26, speed=5)

    def worth(self, user, match):
        return match.holder is user


class EnterradaDoMeio(Ultra):
    name = "ENTERRADA DO MEIO"
    description = "Voa do meio da quadra e crava valendo 3."
    needs_ball = True
    color = (84, 162, 222)

    def ready(self, user, match):
        return match.holder is user and not user.jump and not user.dunking

    def activate(self, user, match):
        user.ultra_dunk_value = 3
        match.dunk(user, flying=True)
        match.burst(user.x, user.y + 10, self.color, 30, speed=7)

    def worth(self, user, match):
        return match.holder is user and _dist_hoop(user, match) < 1100


class VelocidadeDaLuz(Ultra):
    name = "VELOCIDADE DA LUZ"
    description = "4 s tão rápido que o rastro dele deixa tonto quem encosta."
    targets = True
    color = (255, 240, 150)

    def activate(self, user, match):
        user.speed_timer = user.light_timer = 4 * FPS
        user.magic_timer = max(user.magic_timer, 4 * FPS)


class MotoTurbo(Ultra):
    name = "MOTO TURBO"
    description = "5 s de moto com nitro: atropela e enterra direto."
    color = (150, 146, 150)

    def activate(self, user, match):
        user.moto_timer = user.turbo_moto = 5 * FPS
        user.speed_timer = 5 * FPS
        match.camera.shake(5)


class Assombracao(Ultra):
    name = "ASSOMBRAÇÃO"
    description = "Os próximos 2 arremessos atravessam tudo, até o Paredão."
    color = (210, 210, 255)

    def activate(self, user, match):
        user.haunt_shots = 2
        match.burst(user.x, user.y - 30, self.color, 26, speed=4)


class CurtoCircuito(Ultra):
    name = "CURTO-CIRCUITO"
    description = "5 s intocável, e quem encosta leva choque e cai."
    targets = True
    color = (255, 226, 120)

    def activate(self, user, match):
        user.magic_timer = max(user.magic_timer, 5 * FPS)
        user.spark_timer = user.invulnerable_timer = 5 * FPS


class TrovaoDivino(Ultra):
    name = "TROVÃO DIVINO"
    description = "Joga na tabela, sobe sozinho e crava com raio; quem está embaixo do aro cai."
    needs_ball = True
    targets = True
    color = (255, 236, 120)

    def ready(self, user, match):
        return match.holder is user and not user.jump and not user.dunking

    def activate(self, user, match):
        user.thunder = True
        match.popup(user.x, user.y - 110, "NA TABELA!", theme.BRASS)
        match.dunk(user, alley=True)
        match.camera.shake(6)

    def worth(self, user, match):
        return match.holder is user and _dist_hoop(user, match) < 900


class RodaDeCapoeira(Ultra):
    name = "RODA DE CAPOEIRA"
    description = "3 canetas seguidas, e cada uma deixa o adversário tonto."
    targets = True
    color = (255, 236, 140)

    def activate(self, user, match):
        user.capo_left = 3
        user.capo_timer = 8 * FPS
        user.capo_cd = 0

    def worth(self, user, match):
        return match.holder is user


class MatadorDeJogo(Ultra):
    name = "MATADOR DE JOGO"
    description = "Por 6 s toda bola solta é dele, e acertar no verde vale 1 ponto a mais."
    color = (150, 236, 150)

    def activate(self, user, match):
        user.nose_timer = user.killer_timer = 6 * FPS
        user.slow_timer = 0


class Eclipse(Ultra):
    instant = True
    name = "ECLIPSE"
    description = "A quadra escurece por 5 s e o adversário só enxerga perto."
    targets = True
    color = (150, 70, 210)

    def activate(self, user, match):
        blind = [foe for foe in match.foes_of(user) if lands(match, user, foe)]
        for foe in blind:
            foe.eclipsed = 5 * FPS
        if blind:
            match.eclipse = [user, blind, 5 * FPS]
        match.burst(user.x, user.y - 20, self.color, 34, speed=7)


class Clones(Ultra):
    name = "CLONES"
    description = "2 sombras iguais por 4 s, e o adversário não sabe qual está com a bola."
    color = (90, 90, 120)

    def activate(self, user, match):
        user.clone_timer = 4 * FPS
        match.add_effect(CloneShadows(user))
        match.burst(user.x, user.y - 20, user.stats.color, 20, speed=5)

    def worth(self, user, match):
        return match.holder is user


class ExoMaximo(Ultra):
    name = "EXO MÁXIMO"
    description = "Impossível de parar por 6 s, e a enterrada arranca a tampa e vale 3."
    color = (200, 200, 210)

    def activate(self, user, match):
        from .abilities import start_exo
        start_exo(user, match, 6 * FPS)
        user.exo_max = 6 * FPS


ULTRAS = {
    "guerreiro": MarcacaoReal,
    "paredao": MuralhaDoAro,
    "tanque": Cofre,
    "tita": TitaColossal,
    "geada": Inverno,
    "pirata": Ancora,
    "albeguinio": TelaAzul,
    "atirador": ChuvaDeTres,
    "cauanzera": EnterradaDoMeio,
    "velocista": VelocidadeDaLuz,
    "aryel": MotoTurbo,
    "fantasma": Assombracao,
    "faisca": CurtoCircuito,
    "trovao": TrovaoDivino,
    "ginga": RodaDeCapoeira,
    "matador": MatadorDeJogo,
    "aryel_corrompido": Eclipse,
    "ninja": Clones,
    "borba": ExoMaximo,
    "borba_corrompido": ExoMaximo,
    "albeguinio_corrompido": TelaAzul,
}


def create_ultra(stats):
    cls = ULTRAS.get(stats.key)
    return cls() if cls else None


# ── ULTRA: usar, aviso e regras de cada quadro ──
def try_ultra(match, f):
    """SUPER com a barra cheia solta o ULTRA. Devolve True se usou."""
    ultra = getattr(f, "ultra_power", None)
    if (not match.solo or ultra is None or f.ultra < 1.0 or f.stunned or f.hacked or f.dunking
            or match.casting is not None or not ultra.ready(f, match)):
        return False
    f.ultra = 0.0
    match.banner = ("ULTRA!", ultra.name, f.team)
    match.banner_age = 0
    match.assets.play("explosion" if ultra.kind == "ataque" else "barrier", 0.55)
    match.burst(f.x, f.y - 30, ultra.color, 30, speed=7)
    match.camera.shake(4)
    if ultra.instant:
        match.casting = {"user": f, "ultra": ultra, "t": CAST_FRAMES}   # aviso: dá para esquivar
        match.popup(f.x, f.y - 120, "ESQUIVA!", (240, 248, 255))
    else:
        ultra.activate(f, match)
    return True


def update(match):
    """Regras do 1 x 1 a cada quadro: aviso do ULTRA, contatos, inverno, eclipse e orbes."""
    cast = match.casting
    if cast is not None:
        cast["t"] -= 1
        user = cast["user"]
        if match.frame % 2 == 0:
            match.burst(user.x + random.uniform(-14, 14), user.y - random.uniform(0, 50), cast["ultra"].color, 1,
                        speed=1.5, gravity=-0.06, size=4)
        if cast["t"] <= 0:
            match.casting = None
            if not user.stunned:
                cast["ultra"].activate(user, match)
    if match.winter is not None:
        match.winter[1] -= 1
        if match.winter[1] <= 0:
            match.winter = None
    if match.eclipse is not None:
        match.eclipse[2] -= 1
        if match.eclipse[2] <= 0:
            match.eclipse = None
    for f in match.fighters:
        _contact_rules(match, f)
    _update_orbs(match)


def _contact_rules(match, f):
    if f.stunned:
        return
    touching = [o for o in match.foes_of(f) if f.distance_to(o) < f.radius + o.radius + 8 and o.touch_cd <= 0]
    hits = []
    if f.light_timer > 0 and match.frame % 2 == 0:
        match.burst(f.x, f.y - 20, (255, 240, 150), 2, speed=1, size=3)           # o rastro
        hits = [(o, "TONTO", 50) for o in touching]
    elif f.spark_timer > 0:
        if match.frame % 3 == 0:
            match.burst(f.x + random.uniform(-14, 14), f.y - random.uniform(0, 50), (255, 226, 120), 1, speed=2)
        hits = [(o, "CHOQUE", 50) for o in touching]
    elif getattr(f, "titan", False) and f.giant_timer > 0:
        if match.frame % 20 == 0:
            match.camera.shake(3)
            match.dust(f.x, f.y + 16, 4)
        near = [o for o in match.foes_of(f) if f.distance_to(o) < f.radius + o.radius + 30 and o.touch_cd <= 0]
        hits = [(o, "CAIU", 40) for o in near]
    elif getattr(f, "titan", False):
        f.titan = False
    for foe, text, frames in hits:
        foe.touch_cd = FPS                      # uma vez por segundo, no máximo
        if not lands(match, f, foe):
            continue
        if foe.stun(frames):
            match.popup(foe.x, foe.y - 80, text, theme.BONE)
            if match.holder is foe:
                match.release_ball(foe, 30)
                match.grab(f)
    # Roda de Capoeira: caneta automática em quem fica na frente
    if f.capo_left > 0 and match.holder is f and f.capo_cd <= 0:
        from .basket_powers import Caneta, _foe_ahead
        foe = _foe_ahead(f, match, 110)
        if foe is not None:
            f.capo_cd = 20
            if lands(match, f, foe):
                Caneta().activate(f, match)
                f.capo_left -= 1
                match.popup(f.x, f.y - 110, f"CANETA {3 - f.capo_left}/3", theme.BRASS)
            else:
                f.capo_left = 0
    # Moto Turbo: perto da cesta, enterra direto
    if f.turbo_moto > 0 and match.holder is f and not f.dunking and not f.jump and _dist_hoop(f, match) < 520:
        f.turbo_moto = 0
        match.dunk(f, flying=True)


def slide(match, f):
    """Inverno: quem foi congelado escorrega (o embalo continua um pouco)."""
    if match.winter is None or f.team == match.winter[0].team or f.stunned:
        f.ice_v = (0.0, 0.0)
        return
    vx, vy = f.ice_v
    f.x += vx
    f.y += vy
    match.arena.resolve(f)
    mx, my = f.x - f.prev_pos[0], f.y - f.prev_pos[1]
    f.ice_v = (vx * 0.86 + mx * 0.12, vy * 0.86 + my * 0.12)


def thunder_strike(match, f):
    """Trovão Divino cravou: o raio derruba quem está embaixo do aro."""
    f.thunder = False
    side = match.hoop_of(f.team)
    hx, hy = match.hoop_pos(side)
    for foe in match.foes_of(f):
        if math.hypot(foe.x - hx, foe.y - hy) < 180 and lands(match, f, foe) and foe.stun(60):
            match.popup(foe.x, foe.y - 80, "RAIO!", theme.BRASS)
    for i in range(10):
        match.burst(hx + random.uniform(-6, 6), hy - match.RIM_Z - 30 * i, (255, 246, 170), 2, speed=1, size=4)
    match.white_flash = 3
    match.camera.shake(8)


# ── orbes ────────────────────────────────────
class Orb:
    def __init__(self, kind, x, y):
        self.kind = kind
        self.x, self.y = float(x), float(y)
        self.age = 0
        self.alive = True

    @property
    def sort_y(self):
        return self.y

    def update(self, match):
        pass

    def draw(self, surf, camera):
        label, color, _ = ORBS[self.kind]
        bob = math.sin(self.age * 0.12) * 4
        sx, sy = round(self.x - camera.x), round(self.y - camera.y - 22 + bob)
        if self.age > ORB_LIFE - 2 * FPS and (self.age // 5) % 2:
            return                                  # piscando: vai sumir
        shadow = pygame.Rect(0, 0, 22, 8)
        shadow.center = (round(self.x - camera.x), round(self.y - camera.y + 8))
        pygame.draw.ellipse(surf, (0, 0, 0), shadow)
        glow = pygame.Surface((48, 48), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*color, 70), (24, 24), 22)
        surf.blit(glow, (sx - 24, sy - 24))
        pygame.draw.circle(surf, (20, 18, 24), (sx, sy), ORB_RADIUS + 1)
        pygame.draw.circle(surf, color, (sx, sy), ORB_RADIUS)
        pygame.draw.circle(surf, (255, 255, 255), (sx - 4, sy - 5), 3)
        _orb_icon(surf, self.kind, sx, sy)


def _orb_icon(surf, kind, x, y):
    ink = (30, 24, 34)
    if kind == "fogo":
        pygame.draw.polygon(surf, ink, [(x, y - 8), (x + 6, y + 2), (x + 3, y + 7), (x - 3, y + 7), (x - 6, y + 2)])
        pygame.draw.polygon(surf, (255, 220, 120), [(x, y - 2), (x + 3, y + 3), (x, y + 6), (x - 3, y + 3)])
    elif kind == "ima":
        pygame.draw.arc(surf, ink, (x - 7, y - 7, 14, 14), math.pi, math.tau, 4)
        surf.fill(ink, (x - 7, y - 1, 4, 7))
        surf.fill(ink, (x + 3, y - 1, 4, 7))
    elif kind == "turbo":
        for dx in (-4, 2):
            pygame.draw.polygon(surf, ink, [(x + dx, y - 6), (x + dx + 6, y), (x + dx, y + 6)])
    else:
        pygame.draw.polygon(surf, ink, [(x - 6, y - 6), (x + 6, y - 6), (x + 5, y + 2), (x, y + 8), (x - 5, y + 2)])


def _update_orbs(match):
    for orb in match.orbs:
        orb.age += 1
        if orb.age >= ORB_LIFE:
            orb.alive = False
            continue
        for f in match.fighters:
            if not f.stunned and f.lift <= 0 and math.hypot(f.x - orb.x, f.y - orb.y) < f.radius + ORB_RADIUS + 6:
                take_orb(match, f, orb.kind)
                orb.alive = False
                break
    match.orbs = [o for o in match.orbs if o.alive]
    match.orb_clock -= 1
    if match.orb_clock <= 0:
        match.orb_clock = ORB_EVERY
        if not match.orbs:
            spawn_orb(match)


def spawn_orb(match, kind=None):
    from .arena import Court
    kind = kind or random.choice(ORB_ORDER)
    best = None
    for _ in range(12):
        x = random.uniform(Court.W * 0.3, Court.W * 0.7)
        y = random.uniform(Court.MID_Y - 200, Court.MID_Y + 200)
        far = min((math.hypot(f.x - x, f.y - y) for f in match.fighters), default=999)
        if best is None or far > best[0]:
            best = (far, x, y)
    _, x, y = best
    x, y = match.arena.free_spot(x, y, ORB_RADIUS)
    match.orbs.append(Orb(kind, x, y))
    match.burst(x, y - 22, ORBS[kind][1], 14, speed=3)
    return match.orbs[-1]


def take_orb(match, f, kind):
    label, color, frames = ORBS[kind]
    if kind == "fogo":
        f.fire_timer = max(f.fire_timer, frames)
        match.assets.play("fogo", 0.5)
    elif kind == "ima":
        f.magnet_timer = frames
    elif kind == "turbo":
        f.speed_timer = max(f.speed_timer, frames)
        f.stamina = 1.0
        f.exhausted = False
    else:
        f.shield_timer = frames
    match.popup(f.x, f.y - 100, label, color)
    match.burst(f.x, f.y - 30, color, 20, speed=5)
    match.assets.play("select", 0.5)


def magnet_owner(match):
    return next((f for f in match.fighters if f.magnet_timer > 0 and not f.stunned), None)


# ── efeitos visuais ──────────────────────────
class CloneShadows:
    """Clones do Ninja: duas cópias que andam junto, cada uma com uma bola falsa."""

    def __init__(self, owner):
        self.owner = owner
        self.alive = True
        self.x, self.y = owner.x, owner.y

    def offsets(self):
        fx, fy = self.owner.facing
        px, py = -fy, fx
        return [(px * 70, py * 70), (-px * 70, -py * 70)]

    def update(self, match):
        if self.owner.clone_timer <= 0:
            self.alive = False
            match.burst(self.owner.x, self.owner.y - 20, self.owner.stats.color, 10, speed=3)

    def draw(self, surf, camera):
        pass

    def draw_over(self, surf, camera):
        f = self.owner
        x, y = f.x, f.y
        for dx, dy in self.offsets():
            f.x, f.y = x + dx, y + dy
            try:
                f.draw(surf, camera)
            finally:
                f.x, f.y = x, y
            bx, by = round(x + dx + f.facing[0] * 16 - camera.x), round(y + dy + 6 - camera.y)
            pygame.draw.circle(surf, (60, 24, 8), (bx, by), 10)
            pygame.draw.circle(surf, (226, 112, 36), (bx, by), 9)


def draw_eclipse(match, view, cam):
    """O adversário do Eclipse só enxerga perto dele: o resto da quadra fica escuro."""
    if match.eclipse is None:
        return
    _, blind, left = match.eclipse
    veil = pygame.Surface(view.get_size(), pygame.SRCALPHA)
    alpha = 230 if left > 20 else round(230 * left / 20)
    veil.fill((6, 2, 12, alpha))
    for foe in blind:
        cx, cy = round(foe.x - cam.x), round(foe.y - cam.y - 20)
        for r, a in ((150, alpha // 2), (110, 0)):
            pygame.draw.circle(veil, (6, 2, 12, a), (cx, cy), r)
    view.blit(veil, (0, 0))


def draw_winter(match, view):
    if match.winter is None:
        return
    veil = pygame.Surface(view.get_size(), pygame.SRCALPHA)
    veil.fill((190, 230, 255, 46))
    view.blit(veil, (0, 0))
