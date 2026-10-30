"""Poderes do basquete (botão SUPER): um por personagem, adaptado do futebol.

São 7 de defesa e 12 de ataque, e cada ataque tem pelo menos um contra (a tabela está no doc
"Modo basquete: poderes"). Os efeitos que duram ficam em timers do lutador ou da partida, e a
BasketballMatch é quem aplica as regras de cada um (roubo, toco, cesta, rebote).
"""
import math
import random
from abc import ABC, abstractmethod

from . import config, theme
from .soccer_assist import unit

COOLDOWN = 8 * config.FPS                   # no caos alto do basquete, o SUPER volta rápido


class BasketPower(ABC):
    name = ""
    description = ""
    kind = "ataque"                          # "defesa" ou "ataque"
    cooldown = COOLDOWN
    needs_ball = False
    sound = "ability"
    # passivas (só os craques do futebol têm; o texto delas fica em `passive`)
    passive = ""
    steal_mult = 1.0                         # Faísca: a bola dele é mais difícil de roubar
    block_bonus = 0                          # Paredão: dá toco de mais longe
    ghost_proof = False                      # Paredão: a bola fantasma não passa por ele
    pass_speed = 1.0                         # Trovão: passe mais forte
    feint_bonus = 0                          # Ginga: a finta engana por mais tempo
    green_bonus = 0.0                        # Matador: faixa verde um pouco maior
    glued_carry = False                      # (o lutador pergunta isso no futebol)

    def use(self, user, match):
        if user.super_cd > 0 or user.stunned or user.hacked or user.dunking:
            return False
        if self.needs_ball and match.holder is not user:
            return False
        if not self.activate(user, match):
            return False
        user.super_cd = self.cooldown
        match.popup(user.x, user.y - 96, self.name, theme.BRASS)
        match.assets.play(self.sound, 0.5)
        return True

    @abstractmethod
    def activate(self, user, match):
        """Aplica o efeito. Devolve False se não deu para usar agora."""

    def worth_using(self, user, match):
        """Dica para a CPU."""
        return False


def _foe_holder(user, match):
    owner = match.holder
    return owner if owner is not None and owner.team != user.team else None


def _own_hoop(user, match):
    return match.hoop_pos(1 - match.hoop_of(user.team))


def _attack_hoop(user, match):
    return match.hoop_pos(match.hoop_of(user.team))


def _foe_ahead(user, match, reach):
    """Adversário mais perto, na frente de quem está com a bola (ou None)."""
    fx, fy = user.facing
    best, best_d = None, reach
    for foe in match.foes_of(user):
        dx, dy = foe.x - user.x, foe.y - user.y
        d = math.hypot(dx, dy)
        if 1 < d < best_d and (dx * fx + dy * fy) / d > 0.35 and not foe.stunned:
            best, best_d = foe, d
    return best


# ── defesa ───────────────────────────────────

class MarcacaoColada(BasketPower):
    """Guerreiro: gruda em quem está com a bola, rouba encostando e não deixa enterrar."""
    name = "MARCAÇÃO COLADA"
    description = "5s grudado em quem tem a bola: rouba encostando e ele não enterra."
    kind = "defesa"
    sound = "barrier"
    FRAMES = 5 * config.FPS

    def activate(self, user, match):
        user.glue_timer = self.FRAMES
        match.burst(user.x, user.y - 10, (150, 196, 255), 16, speed=4)
        return True

    def worth_using(self, user, match):
        owner = _foe_holder(user, match)
        if owner is None or user.distance_to(owner) > 300:
            return False
        hx, hy = _own_hoop(user, match)
        return math.hypot(owner.x - hx, owner.y - hy) < 700      # só quando ele já ameaça a cesta


class TocoVoador(BasketPower):
    """Paredão: aparece embaixo do próprio aro e o próximo arremesso ou enterrada leva toco."""
    name = "TOCO VOADOR"
    description = "Teleporta para o seu aro e, por 4s, dá toco no próximo arremesso ou enterrada."
    kind = "defesa"
    passive = "Corpo fechado: dá toco de mais longe e a bola fantasma não passa por ele."
    block_bonus = 6
    ghost_proof = True
    FRAMES = 4 * config.FPS

    def activate(self, user, match):
        hx, hy = _own_hoop(user, match)
        inward = 1 if hx < match.arena.width / 2 else -1
        x, y = match.arena.free_spot(hx + inward * 46, hy + random.uniform(-20, 20), user.radius)
        match.burst(user.x, user.y - 16, user.stats.color, 14)
        user.x, user.y = x, y
        user.prev_pos = (x, y)
        user.vx = user.vy = 0.0
        user.facing = (float(inward), 0.0)
        user.teleport_flash = 20
        user.wall_timer = self.FRAMES
        match.burst(x, y - 16, user.stats.color, 14)
        return True

    def worth_using(self, user, match):
        owner = _foe_holder(user, match)
        if owner is None:
            return False
        hx, hy = _own_hoop(user, match)
        return math.hypot(owner.x - hx, owner.y - hy) < 600 and user.distance_to(owner) > 120


class TampaNoAro(BasketPower):
    """Tanque: tampa o próprio aro por 4s e a bola bate e volta. A enterrada do Exo arranca a tampa."""
    name = "TAMPA NO ARO"
    description = "Tampa o seu aro por 4s: a bola bate e volta."
    kind = "defesa"
    sound = "barrier"
    FRAMES = 4 * config.FPS

    def activate(self, user, match):
        side = 1 - match.hoop_of(user.team)
        match.lids[side] = self.FRAMES
        hx, hy = match.hoop_pos(side)
        match.burst(hx, hy - match.RIM_Z, (150, 226, 240), 20, speed=4)
        return True

    def worth_using(self, user, match):
        hx, hy = _own_hoop(user, match)
        owner = _foe_holder(user, match)
        if owner is not None:
            # a CPU tampa só na hora: arremesso subindo ou enterrada a caminho
            return (owner.jump_shot or owner.dunking) and math.hypot(owner.x - hx, owner.y - hy) < 600
        shot = match.shot
        return shot is not None and shot["team"] != user.team and not shot.get("touched")


class Gigante(BasketPower):
    """Titã: fica enorme, empurra todo mundo, dá toco em quem chega perto e pega todo rebote."""
    name = "GIGANTE"
    description = "Enorme por 5s: empurra, dá toco em quem chega perto e pega todo rebote."
    kind = "defesa"
    FRAMES = 5 * config.FPS

    def activate(self, user, match):
        user.giant_timer = self.FRAMES
        user.radius = 24
        match.camera.shake(5)
        return True

    def worth_using(self, user, match):
        owner = _foe_holder(user, match)
        if owner is not None:
            return user.distance_to(owner) < 220
        ball = match.ball
        return match.shot is not None and math.hypot(ball.x - user.x, ball.y - user.y) < 220


class Congelar(BasketPower):
    """Geada: os adversários perto ficam lentos e a faixa verde deles fica estreita."""
    name = "CONGELAR"
    description = "Adversários perto ficam lentos por 3s, com a faixa verde estreita."
    kind = "defesa"
    sound = "barrier"
    RADIUS = 230
    FRAMES = 3 * config.FPS

    def activate(self, user, match):
        for foe in match.foes_of(user):
            if user.distance_to(foe) < self.RADIUS and match.freeze_foe(foe, self.FRAMES):
                match.burst(foe.x, foe.y - 10, (200, 236, 250), 10, speed=3)
        match.burst(user.x, user.y - 6, (200, 236, 250), 30, speed=7)
        match.burst(user.x, user.y - 6, (150, 212, 240), 16, speed=4)
        match.camera.shake(4)
        return True

    def worth_using(self, user, match):
        owner = _foe_holder(user, match)
        return owner is not None and user.distance_to(owner) < self.RADIUS * 0.8


class Gancho(BasketPower):
    """Pirata: puxa a bola de longe até a mão, até da mão do adversário (não no meio da enterrada,
    nem do Drible Mágico ou do Exo). Bola no ar (arremesso, passe ou rebote) não dá para fisgar,
    e quem protege a bola (MARCAR) segura o puxão: o gancho bate e volta vazio."""
    name = "GANCHO"
    description = "Puxa a bola de longe para a mão, até da mão do adversário. Quem protege segura."
    kind = "defesa"
    sound = "dash"
    RANGE = 280

    def activate(self, user, match):
        ball = match.ball
        owner = match.holder
        d = math.hypot(ball.x - user.x, ball.y - user.y)
        if d > self.RANGE or owner is user or (owner is not None and owner.team == user.team):
            return False
        if owner is not None and (owner.dunking or owner.magic_timer > 0 or owner.exo_timer > 0):
            return False
        if owner is None and ball.airborne:
            return False
        steps = int(d // 14)
        for i in range(steps):                      # a corrente até a bola
            t = i / max(1, steps)
            match.burst(user.x + (ball.x - user.x) * t, user.y - 20 + (ball.y - ball.z - user.y) * t,
                        (176, 180, 192), 1, speed=0.5)
        if owner is not None and owner.protecting:
            match.popup(owner.x, owner.y - 74, "SEGUROU", theme.BONE)     # o contra do Gancho
            return True
        if owner is not None:
            match.release_ball(owner, 30)
        match.grab(user)
        match.popup(user.x, user.y - 74, "PUXOU", theme.BONE)
        return True

    def worth_using(self, user, match):
        ball = match.ball
        owner = match.holder
        d = math.hypot(ball.x - user.x, ball.y - user.y)
        if owner is not None and owner.team != user.team:
            return (90 < d < self.RANGE and not owner.protecting
                    and not (owner.magic_timer > 0 or owner.exo_timer > 0))
        return owner is None and not ball.airborne and 140 < d < self.RANGE


class Hack(BasketPower):
    """Albeguinio: digita e trava os adversários por 2,5s; quem está com a bola perde ela."""
    name = "HACK"
    description = "Digita e trava os adversários por 2,5s; quem tem a bola perde."
    kind = "defesa"
    cooldown = 14 * config.FPS              # trava o time todo: recarga mais longa
    sound = "barrier"
    TYPING = round(0.6 * config.FPS)
    FREEZE = round(2.5 * config.FPS)

    def activate(self, user, match):
        from .entities import Hack as HackEffect
        match.add_effect(HackEffect(user, self.TYPING, self.FREEZE))
        return True

    def worth_using(self, user, match):
        owner = _foe_holder(user, match)
        if owner is None:
            return False
        hx, hy = _own_hoop(user, match)
        return math.hypot(owner.x - hx, owner.y - hy) < 520 and owner.moto_timer <= 0


# ── ataque ───────────────────────────────────

class MaoQuente(BasketPower):
    """Atirador: por 5s a faixa verde fica inteira, até no de 3."""
    name = "MÃO QUENTE"
    description = "Por 5s a faixa verde do arremesso fica inteira, até no de 3."
    FRAMES = 5 * config.FPS

    def activate(self, user, match):
        user.hot_timer = self.FRAMES
        match.burst(user.x, user.y - 30, (255, 170, 60), 16, speed=4)
        return True

    def worth_using(self, user, match):
        if match.holder is not user:
            return False
        hx, hy = _attack_hoop(user, match)
        return 300 < math.hypot(hx - user.x, hy - user.y) < 760


class EnterradaVoadora(BasketPower):
    """Cauanzera: da linha de 3, voa por cima de todo mundo e crava. Só o Toco Voador e a Tampa no
    Aro seguram."""
    name = "ENTERRADA VOADORA"
    description = "Da linha de 3, voa por cima de todos e crava (ninguém toca nele no ar)."
    needs_ball = True
    sound = "dash"
    RANGE = 560                             # um pouco além da linha de 3

    def activate(self, user, match):
        hx, hy = _attack_hoop(user, match)
        if math.hypot(hx - user.x, hy - user.y) > self.RANGE or user.jump:
            return False
        match.dunk(user, flying=True)
        match.burst(user.x, user.y + 10, (84, 162, 222), 16, speed=5)
        return True

    def worth_using(self, user, match):
        if match.holder is not user:
            return False
        hx, hy = _attack_hoop(user, match)
        return math.hypot(hx - user.x, hy - user.y) < self.RANGE - 30


class Arrancada(BasketPower):
    """Velocista: corre muito mais rápido por 3s."""
    name = "ARRANCADA"
    description = "Corre muito mais rápido por 3s com a bola."
    sound = "dash"

    def activate(self, user, match):
        user.sprint_timer = 3 * config.FPS
        return True

    def worth_using(self, user, match):
        if match.holder is not user:
            return False
        hx, hy = _attack_hoop(user, match)
        return math.hypot(hx - user.x, hy - user.y) > 520


class GrauDeMoto(BasketPower):
    """Aryel: 3s de moto. Corre muito, não perde a bola e quem ele atropela cai. Contra o Gigante a
    moto bate e para."""
    name = "GRAU DE MOTO"
    description = "3s de moto: corre muito, não perde a bola e quem ele atropela cai."
    sound = "dash"
    FRAMES = 3 * config.FPS

    def activate(self, user, match):
        user.moto_timer = self.FRAMES
        match.burst(user.x, user.y + 16, (150, 146, 150), 14, speed=3)
        match.camera.shake(3)
        return True

    def worth_using(self, user, match):
        owner = match.holder
        if owner is user:
            hx, hy = _attack_hoop(user, match)
            return math.hypot(hx - user.x, hy - user.y) > 480
        if owner is not None and owner.team != user.team:
            return 120 < user.distance_to(owner) < 360
        return False


class BolaFantasma(BasketPower):
    """Fantasma: o próximo arremesso atravessa mãos e tocos (menos o Paredão) até o aro, mas ainda
    depende do tempo certo."""
    name = "BOLA FANTASMA"
    description = "O próximo arremesso atravessa mãos e tocos, mas ainda depende do tempo."
    needs_ball = True
    FRAMES = 5 * config.FPS

    def activate(self, user, match):
        user.ghost_timer = self.FRAMES
        match.burst(user.x, user.y - 30, (200, 200, 255), 16, speed=3)
        return True

    def worth_using(self, user, match):
        if match.holder is not user:
            return False
        hx, hy = _attack_hoop(user, match)
        near = any(user.distance_to(f) < 120 for f in match.foes_of(user))
        return near and math.hypot(hx - user.x, hy - user.y) < 620


class DribleMagico(BasketPower):
    """Faísca: por 3s ninguém toma a bola dele e ele atravessa os marcadores."""
    name = "DRIBLE MÁGICO"
    description = "Por 3s ninguém toma a bola dele e ele atravessa os marcadores."
    needs_ball = True
    sound = "dash"
    passive = "Bola grudada: é mais difícil roubar a bola dele."
    steal_mult = 0.6
    FRAMES = 3 * config.FPS

    def activate(self, user, match):
        user.magic_timer = self.FRAMES
        match.burst(user.x, user.y - 10, (255, 226, 120), 18, speed=4)
        return True

    def worth_using(self, user, match):
        return match.holder is user and _foe_ahead(user, match, 130) is not None


class AlleyOopTrovao(BasketPower):
    """Trovão: passe alto e forte para o companheiro, que já sobe e crava. Quem entra na frente do
    passe cai; o Gancho e o Gigante interceptam."""
    name = "ALLEY-OOP TROVÃO"
    description = "Passe alto para o companheiro, que já sobe e crava; quem entra na frente cai."
    needs_ball = True
    sound = "explosion"
    passive = "Passe trovão: os passes dele saem mais fortes."
    pass_speed = 1.3

    def activate(self, user, match):
        mates = match.mates_of(user)
        if not mates:
            return False
        hx, hy = _attack_hoop(user, match)
        mate = min(mates, key=lambda m: math.hypot(m.x - hx, m.y - hy))
        return match.alley_oop(user, mate)

    def worth_using(self, user, match):
        if match.holder is not user:
            return False
        hx, hy = _attack_hoop(user, match)
        mine = math.hypot(hx - user.x, hy - user.y)
        return any(math.hypot(hx - m.x, hy - m.y) < min(mine, 470) for m in match.mates_of(user))


class Caneta(BasketPower):
    """Ginga: a bola passa entre as pernas do marcador, que fica tonto, e ele sai livre. Não dá
    caneta em gigante."""
    name = "CANETA"
    description = "A bola passa entre as pernas do marcador, que fica tonto, e ele sai livre."
    needs_ball = True
    sound = "dash"
    passive = "Ginga: a finta dele engana por mais tempo."
    feint_bonus = 10
    REACH = 150
    DIZZY = 70

    def activate(self, user, match):
        foe = _foe_ahead(user, match, self.REACH)
        if foe is None:
            return False
        if foe.giant_timer > 0:
            # no gigante não tem caneta: ele fica com a bola
            match.release_ball(user, 30)
            match.grab(foe)
            match.popup(foe.x, foe.y - 90, "NÃO PASSOU", theme.BONE)
            return True
        foe.stun(self.DIZZY)
        foe.glue_timer = 0
        dx, dy = unit(foe.x - user.x, foe.y - user.y)
        user.magic_timer = max(user.magic_timer, 24)      # passa por dentro do marcador
        user.dash((dx, dy), frames=12, cooldown=24)
        user.facing = (dx, dy)
        match.popup(foe.x, foe.y - 74, "TONTO", theme.BONE)
        match.burst(foe.x, foe.y - 40, (255, 236, 140), 10, speed=2)
        return True

    def worth_using(self, user, match):
        return match.holder is user and _foe_ahead(user, match, 110) is not None


class FaroDeCesta(BasketPower):
    """Matador: corre mais, e todo rebote e bola solta perto vem para a mão dele."""
    name = "FARO DE CESTA"
    description = "Por 5s corre mais, e rebote e bola solta perto vêm para a mão dele."
    passive = "Matador: a faixa verde dele é um pouco maior."
    green_bonus = 0.04
    FRAMES = 5 * config.FPS

    def activate(self, user, match):
        user.nose_timer = self.FRAMES
        user.slow_timer = 0
        match.burst(user.x, user.y - 10, (150, 236, 150), 16, speed=4)
        return True

    def worth_using(self, user, match):
        shot = match.shot
        if shot is not None and shot["team"] == user.team:
            return True                              # vai buscar o rebote
        return match.holder is None and user.distance_to(match.ball) < 420


class BombaSombria(BasketPower):
    """Aryel Corrompido: explosão que empurra, atordoa e deixa lento quem estiver perto. O
    Gigante encolhe na hora; o Exo nem se mexe."""
    name = "BOMBA SOMBRIA"
    description = "Explosão que empurra, atordoa e deixa lento quem estiver perto."
    sound = "explosion"
    RADIUS = 150

    def activate(self, user, match):
        for foe in match.foes_of(user):
            dx, dy = foe.x - user.x, foe.y - user.y
            d = math.hypot(dx, dy)
            if d >= self.RADIUS:
                continue
            if foe.giant_timer > 0:
                foe.giant_timer = 0
                foe.radius = foe.base_radius
                match.popup(foe.x, foe.y - 90, "ENCOLHEU", theme.BONE)
            if foe.stun(45):
                foe.slow(int(1.5 * config.FPS))
                if d:
                    foe.knock = [dx / d * 9, dy / d * 9]
                if match.holder is foe:
                    match.release_ball(foe, 30)
                    ball = match.ball
                    ux, uy = unit(dx, dy) if d else (1.0, 0.0)
                    ball.vx, ball.vy, ball.vz = ux * 6, uy * 6, 3.0
        match.burst(user.x, user.y - 6, (150, 70, 210), 30, speed=8)
        match.burst(user.x, user.y - 6, (232, 108, 52), 20, speed=6)
        match.camera.shake(8)
        return True

    def worth_using(self, user, match):
        return any(user.distance_to(f) < 100 for f in match.foes_of(user))


class Sombra(BasketPower):
    """Ninja: teleporta para o lado da cesta adversária, livre. Sem a bola, o companheiro já passa."""
    name = "SOMBRA"
    description = "Teleporta livre para o lado da cesta adversária; o companheiro já passa."

    def activate(self, user, match):
        hx, hy = _attack_hoop(user, match)
        inward = 1 if hx < match.arena.width / 2 else -1
        spots = [(hx + inward * 200, hy + dy) for dy in (-170, 170, -60, 60)]
        foes = match.foes_of(user)
        x, y = max(spots, key=lambda p: min((math.hypot(p[0] - f.x, p[1] - f.y) for f in foes), default=999))
        x, y = match.arena.free_spot(x, y, user.radius)
        match.burst(user.x, user.y - 16, user.stats.color, 14)
        user.x, user.y = x, y
        user.prev_pos = (x, y)
        user.vx = user.vy = 0.0
        user.facing = unit(hx - x, hy - y)
        user.teleport_flash = 20
        match.burst(x, y - 16, user.stats.color, 14)
        owner = match.holder
        if owner is not None and owner is not user and owner.team == user.team:
            match.pass_ball(owner, (x - owner.x, y - owner.y))
        return True

    def worth_using(self, user, match):
        owner = match.holder
        if owner is None or owner.team != user.team:
            return False
        hx, hy = _attack_hoop(user, match)
        return math.hypot(hx - user.x, hy - user.y) > 520


class Exo(BasketPower):
    """Borba Jr: por 5s ninguém toma a bola dele, ele não cai, e a enterrada dele arranca a Tampa
    no Aro."""
    name = "EXO"
    description = "5s: ninguém toma a bola, ele não cai e a enterrada arranca a tampa do aro."
    sound = "barrier"
    FRAMES = 5 * config.FPS

    def activate(self, user, match):
        from .abilities import start_exo
        start_exo(user, match, self.FRAMES)
        return True

    def worth_using(self, user, match):
        return match.holder is user and any(user.distance_to(f) < 140 for f in match.foes_of(user))


BASKET_POWERS = {
    "guerreiro": MarcacaoColada,
    "paredao": TocoVoador,
    "tanque": TampaNoAro,
    "tita": Gigante,
    "geada": Congelar,
    "pirata": Gancho,
    "albeguinio": Hack,
    "atirador": MaoQuente,
    "cauanzera": EnterradaVoadora,
    "velocista": Arrancada,
    "aryel": GrauDeMoto,
    "fantasma": BolaFantasma,
    "faisca": DribleMagico,
    "trovao": AlleyOopTrovao,
    "ginga": Caneta,
    "matador": FaroDeCesta,
    "aryel_corrompido": BombaSombria,
    "ninja": Sombra,
    "borba": Exo,
    "borba_corrompido": Exo,
}


def create_basket_power(stats):
    return BASKET_POWERS[stats.key]()
