"""Poderes do futebol (botão SUPER). Cada personagem tem uma subclasse de SoccerPower."""
import math
import random
from abc import ABC, abstractmethod

import pygame

from . import config, theme
from .entities import Entity, Particle


class SoccerPower(ABC):
    name = ""
    description = ""
    cooldown = 12 * config.FPS
    needs_ball = False
    sound = "ability"
    release_frames = 20       # depois de um poder com a bola, demora isso para dominar de novo
    keeps_receiver = False    # o poder já escolheu quem recebe a bola (não apaga ao soltar)
    # habilidade que vale o jogo todo (só os craques do futebol têm; nome e texto em data.py)
    steal_mult = 1.0          # tomar a bola dele demora tanto mais
    head_reach = 0            # cabeceia bola até essa altura a mais
    head_power = 1.0          # força da cabeçada
    glued_carry = False       # bola sempre colada no pé, até correndo, sem perder velocidade
    finisher = False          # dentro da área adversária o chute vai no gol e sai mais forte

    def use(self, user, match):
        if user.super_cd > 0 or user.stunned:
            return False
        if self.needs_ball and not match.touching(user, 20):
            return False
        if not self.activate(user, match):
            return False
        user.super_cd = self.cooldown
        match.popup(user.x, user.y - 74, self.name, theme.BRASS)
        match.assets.play(self.sound, 0.5)
        return True

    @abstractmethod
    def activate(self, user, match):
        """Aplica o efeito. Devolve False se não deu para usar agora."""

    def worth_using(self, user, match):
        """Dica para a CPU."""
        return False


def _goal_dir(user, match, spread=0):
    gx, gy = match.goal_x(1 - user.team), match.arena.height / 2 + spread
    dx, dy = gx - user.x, gy - user.y
    d = math.hypot(dx, dy) or 1
    return dx / d, dy / d


class Carrinho(SoccerPower):
    name = "CARRINHO"
    description = "Desliza para a frente, derruba quem acertar e rouba a bola."
    cooldown = 8 * config.FPS
    sound = "dash"

    def activate(self, user, match):
        if not user.dash(user.facing, frames=16, cooldown=30):
            return False
        user.tackle_timer = 16
        return True

    def worth_using(self, user, match):
        ball = match.ball
        for foe in match.foes_of(user):
            if math.hypot(foe.x - ball.x, foe.y - ball.y) < 40 and user.distance_to(foe) < 150:
                user.face(foe)
                return True
        return False


class ChuteCerteiro(SoccerPower):
    name = "CHUTE CERTEIRO"
    description = "Chute fortíssimo que faz curva em direção ao gol."
    cooldown = 15 * config.FPS
    needs_ball = True

    def activate(self, user, match):
        gx, gy = match.goal_x(1 - user.team), match.arena.height / 2
        user.facing = _goal_dir(user, match)
        ball = match.ball
        ball.vx, ball.vy = user.facing[0] * config.SUPER_SHOT_POWER, user.facing[1] * config.SUPER_SHOT_POWER
        ball.homing_timer = config.SUPER_HOMING_FRAMES
        ball.homing_player = None
        ball.homing_target = (gx, gy)
        ball.homing_force = config.SUPER_HOMING_FORCE
        match.last_touch = user
        match.camera.shake(6)
        match.burst(ball.x, ball.y, theme.BRASS, 14, speed=5)
        return True

    def worth_using(self, user, match):
        return abs(match.goal_x(1 - user.team) - user.x) < 800


class BallWall(Entity):
    """Muralha do Tanque no futebol: a bola bate e volta."""

    def __init__(self, x, y, team, frames):
        super().__init__(x, y)
        self.rect = pygame.Rect(0, 0, 18, 150)
        self.rect.center = (round(x), round(y))
        self.team = team
        self.timer = frames

    def update(self, match):
        self.timer -= 1
        if self.timer <= 0:
            self.alive = False

    def draw(self, surf, camera):
        r = self.rect.move(-camera.x, -camera.y)
        fading = self.timer < 40 and (self.timer // 4) % 2 == 0
        edge = (150, 226, 240) if not fading else (80, 120, 140)
        surf.fill((20, 40, 56), r)
        pygame.draw.rect(surf, edge, r, 2)
        for y in range(r.y + 4, r.bottom - 2, 6):
            surf.fill((70, 140, 170), (r.x + 4, y, r.w - 8, 2))


class MuralhaDoGol(SoccerPower):
    name = "MURALHA"
    description = "Ergue uma barreira na frente do próprio gol por 5s."
    cooldown = 15 * config.FPS
    sound = "barrier"

    def activate(self, user, match):
        home = match.goal_x(user.team)
        x = home + (70 if user.team == 0 else -70)
        match.add_ball_wall(BallWall(x, match.arena.height / 2, user.team, 5 * config.FPS))
        return True

    def worth_using(self, user, match):
        ball = match.ball
        home = match.goal_x(user.team)
        coming = (ball.vx < -3) if user.team == 0 else (ball.vx > 3)
        return coming and abs(ball.x - home) < 650


class Sombra(SoccerPower):
    name = "SOMBRA"
    description = "Teleporta para trás da bola, já virado para o gol."
    cooldown = 10 * config.FPS

    def activate(self, user, match):
        ball = match.ball
        gx, gy = _goal_dir(user, match)
        x, y = ball.x - gx * 30, ball.y - gy * 30
        x, y = match.arena.free_spot(x, y, user.radius)
        match.burst(user.x, user.y - 16, user.stats.color, 14)
        user.x, user.y = x, y
        user.vx = user.vy = 0
        user.facing = (gx, gy)
        user.teleport_flash = 20
        match.burst(x, y - 16, user.stats.color, 14)
        return True

    def worth_using(self, user, match):
        ball = match.ball
        mates_near = any(math.hypot(m.x - ball.x, m.y - ball.y) < 60 for m in match.mates_of(user))
        return not mates_near and user.distance_to(ball) > 260


class Arrancada(SoccerPower):
    name = "ARRANCADA"
    description = "Corre muito mais rápido por 3s com a bola colada no pé."
    cooldown = 10 * config.FPS
    sound = "dash"

    def activate(self, user, match):
        user.sprint_timer = 3 * config.FPS
        return True

    def worth_using(self, user, match):
        return match.touching(user, 10)


class Bomba(SoccerPower):
    name = "BOMBA"
    description = "Explosão que empurra e atordoa quem estiver perto."
    cooldown = 12 * config.FPS
    sound = "explosion"
    RADIUS = 130

    def activate(self, user, match):
        for foe in match.foes_of(user):
            dx, dy = foe.x - user.x, foe.y - user.y
            d = math.hypot(dx, dy)
            if d < self.RADIUS:
                if d:
                    foe.knock = [dx / d * 9, dy / d * 9]
                foe.stun(45)
        ball = match.ball
        dx, dy = ball.x - user.x, ball.y - user.y
        d = math.hypot(dx, dy)
        if 0 < d < self.RADIUS:
            ball.vx, ball.vy = dx / d * 11, dy / d * 11
            match.last_touch = user
        match.burst(user.x, user.y - 6, (232, 108, 52), 30, speed=7)
        match.burst(user.x, user.y - 6, (255, 220, 140), 14, speed=4)
        match.camera.shake(8)
        return True

    def worth_using(self, user, match):
        return sum(user.distance_to(f) < 100 for f in match.foes_of(user)) >= 1


class BombaSombria(Bomba):
    """Aryel Corrompido: a bomba é maior e quem é pego ainda fica lento."""
    name = "BOMBA SOMBRIA"
    description = "Explosão sombria maior: empurra, atordoa e deixa lento quem estiver perto."
    RADIUS = 150

    def activate(self, user, match):
        for foe in match.foes_of(user):
            if user.distance_to(foe) < self.RADIUS:
                foe.slow(int(1.5 * config.FPS))
        super().activate(user, match)
        match.burst(user.x, user.y - 6, (150, 70, 210), 30, speed=8)
        return True


class BolaFantasma(SoccerPower):
    name = "BOLA FANTASMA"
    description = "Chute que atravessa os adversários a caminho do gol."
    cooldown = 15 * config.FPS
    needs_ball = True

    def activate(self, user, match):
        user.facing = _goal_dir(user, match, spread=random.choice((-40, 0, 40)))
        ball = match.ball
        ball.vx, ball.vy = user.facing[0] * 13, user.facing[1] * 13
        ball.homing_timer = 0
        ball.ghost_timer = 75
        ball.ghost_team = user.team
        match.last_touch = user
        return True

    def worth_using(self, user, match):
        return abs(match.goal_x(1 - user.team) - user.x) < 900


class Gigante(SoccerPower):
    name = "GIGANTE"
    description = "Fica enorme por 5s e empurra todo mundo."
    cooldown = 15 * config.FPS

    def activate(self, user, match):
        user.giant_timer = 5 * config.FPS
        user.radius = 24
        match.camera.shake(5)
        return True

    def worth_using(self, user, match):
        ball = match.ball
        return any(math.hypot(f.x - ball.x, f.y - ball.y) < 80 for f in match.foes_of(user)) \
            and user.distance_to(ball) < 140


class GanchoNaBola(SoccerPower):
    """Pirata: lança o gancho na bola e a traz para o pé (tira até do pé do adversário)."""
    name = "GANCHO"
    description = "Puxa a bola para o pé, até do pé do adversário, de longe."
    cooldown = 12 * config.FPS
    sound = "dash"
    RANGE = 380

    def activate(self, user, match):
        ball = match.ball
        d = math.hypot(ball.x - user.x, ball.y - user.y)
        owner = match.possessor
        if d > self.RANGE or ball.z > config.HEAD_RANGE[1] or (owner is not None and owner.team == user.team):
            return False
        if owner is not None and (owner.magic_timer > 0 or owner.exo_timer > 0):
            return False                            # drible mágico / exoesqueleto: nem o gancho tira
        if owner is not None:
            match._release(owner, 30)               # arranca a bola do adversário
        if d < 40:
            match._take(user)                       # bola colada: domina na hora
            return True
        dx, dy = (user.x - ball.x) / d, (user.y - ball.y) / d
        speed = min(10.0, 5 + d / 40)
        ball.vx, ball.vy = dx * speed, dy * speed
        ball.z = ball.vz = 0.0
        ball.homing_timer = 40
        ball.homing_player = user
        ball.homing_target = (user.x, user.y)
        ball.homing_force = 0.6
        ball.hook_timer = 60
        ball.hook_owner = user
        user.face(ball)
        match.last_touch = user
        steps = int(d // 14)
        for i in range(steps):                      # a corrente até a bola
            t = i / max(1, steps)
            match.burst(user.x + (ball.x - user.x) * t, user.y - 8 + (ball.y - user.y) * t,
                        (176, 180, 192), 1, speed=0.5)
        return True

    def worth_using(self, user, match):
        ball = match.ball
        owner = match.possessor
        d = math.hypot(ball.x - user.x, ball.y - user.y)
        if owner is not None and owner.team != user.team:
            return 90 < d < self.RANGE
        return owner is None and 140 < d < self.RANGE and not ball.airborne


class Congelar(SoccerPower):
    """Geada: os adversários em volta ficam lentos."""
    name = "CONGELAR"
    description = "Os adversários perto dela ficam lentos por 3s."
    cooldown = 13 * config.FPS
    sound = "barrier"
    RADIUS = 230

    def activate(self, user, match):
        hit = False
        for foe in match.foes_of(user):
            if user.distance_to(foe) < self.RADIUS and foe.slow(3 * config.FPS):
                hit = True
                match.burst(foe.x, foe.y - 10, (200, 236, 250), 10, speed=3)
        match.burst(user.x, user.y - 6, (200, 236, 250), 30, speed=7)
        match.burst(user.x, user.y - 6, (150, 212, 240), 16, speed=4)
        match.camera.shake(4)
        return hit or True

    def worth_using(self, user, match):
        ball = match.ball
        return any(user.distance_to(f) < self.RADIUS * 0.8
                   and math.hypot(f.x - ball.x, f.y - ball.y) < 120 for f in match.foes_of(user))


# ── craques do futebol ─────────────────────────

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


class DribleMagico(SoccerPower):
    """Faísca: por 3s ninguém tira a bola dele, e ele atravessa os marcadores."""
    name = "DRIBLE MÁGICO"
    description = "Por 3s ninguém toma e ele atravessa todos."
    cooldown = 12 * config.FPS
    needs_ball = True
    sound = "dash"
    release_frames = 0
    steal_mult = 1.6
    FRAMES = 3 * config.FPS

    def use(self, user, match):
        if match.possessor is not user:
            return False                             # é drible: precisa estar com a bola no pé
        return super().use(user, match)

    def activate(self, user, match):
        user.magic_timer = self.FRAMES
        match.burst(user.x, user.y - 10, (255, 226, 120), 18, speed=4)
        return True

    def worth_using(self, user, match):
        return match.possessor is user and _foe_ahead(user, match, 130) is not None


class ChuteTrovao(SoccerPower):
    """Trovão: bomba reta e fortíssima; quem entrar na frente é derrubado e ela segue."""
    name = "CHUTE TROVÃO"
    description = "Bomba que derruba quem entra na frente."
    cooldown = 14 * config.FPS
    needs_ball = True
    sound = "explosion"
    head_reach = 30
    head_power = 1.45
    SPEED = config.THUNDER_SPEED
    FRAMES = 55

    def activate(self, user, match):
        fx, fy = user.facing
        gx, gy = _goal_dir(user, match)
        # virado mais ou menos para o gol: vai no gol; senão, para onde ele olha
        dx, dy = (gx, gy) if fx * gx + fy * gy > 0.3 else (fx, fy)
        ball = match.ball
        ball.z = ball.vz = 0.0
        ball.vx, ball.vy = dx * self.SPEED, dy * self.SPEED
        ball.thunder_timer = self.FRAMES
        ball.thunder_owner = user
        ball.thunder_hit = set()
        ball.homing_timer = 0
        user.facing = (dx, dy)
        match.last_touch = user
        match.camera.shake(8)
        match.burst(ball.x, ball.y, (255, 236, 120), 16, speed=6)
        match.burst(ball.x, ball.y, (255, 255, 255), 8, speed=4)
        return True

    def worth_using(self, user, match):
        gx, gy = _goal_dir(user, match)
        fx, fy = user.facing
        return abs(match.goal_x(1 - user.team) - user.x) < 900 and fx * gx + fy * gy > 0.5


class Caneta(SoccerPower):
    """Ginga: a bola passa entre as pernas do marcador, que fica tonto, e ele sai com ela."""
    name = "CANETA"
    description = "Caneta no marcador, que fica tonto."
    cooldown = 10 * config.FPS
    needs_ball = True
    sound = "dash"
    release_frames = 0
    keeps_receiver = True
    glued_carry = True
    REACH = 150
    DIZZY = 70

    def activate(self, user, match):
        foe = _foe_ahead(user, match, self.REACH)
        if foe is None:
            return False                             # sem marcador na frente não tem caneta
        dx, dy = foe.x - user.x, foe.y - user.y
        d = math.hypot(dx, dy) or 1
        dx, dy = dx / d, dy / d
        ball = match.ball
        bx, by = match.arena.free_spot(foe.x + dx * 42, foe.y + dy * 42, ball.radius)
        ball.x, ball.y = bx, by
        ball.z = ball.vz = 0.0
        ball.vx, ball.vy = dx * 2.5, dy * 2.5
        ball.homing_timer = 0
        ball.receiver, ball.receiver_timer = user, 45
        foe.stun(self.DIZZY)
        match.no_trap[foe] = self.DIZZY
        user.magic_timer = max(user.magic_timer, 22)      # passa por dentro do marcador
        user.dash((dx, dy), frames=10, cooldown=24)
        user.facing = (dx, dy)
        match.last_touch = user
        match.popup(foe.x, foe.y - 74, "TONTO", theme.BONE)
        match.burst(foe.x, foe.y - 40, (255, 236, 140), 10, speed=2)
        return True

    def worth_using(self, user, match):
        return match.possessor is user and _foe_ahead(user, match, 110) is not None


class FaroDeGol(SoccerPower):
    """Matador: corre mais e a bola solta perto dele vem para o pé."""
    name = "FARO DE GOL"
    description = "Por 5s corre mais e puxa a bola solta."
    cooldown = 14 * config.FPS
    finisher = True
    FRAMES = 5 * config.FPS
    RANGE = 280

    def activate(self, user, match):
        user.nose_timer = self.FRAMES
        match.burst(user.x, user.y - 10, (150, 236, 150), 16, speed=4)
        return True

    def worth_using(self, user, match):
        ball = match.ball
        return match.possessor is None and user.distance_to(ball) < 420 and ball.z < 30


# ── Cauanzera, Albeguinio e Borba Jr ───────────

class Dunk(Entity):
    """Enterrada do Cauanzera: pula por cima de todo mundo com a bola nas mãos (ninguém toca nele
    nem na bola no ar), cai na frente do gol e crava a bola lá dentro."""

    FRAMES = 44
    PEAK = 150

    def __init__(self, user, match):
        super().__init__(user.x, user.y)
        self.user = user
        self.age = 0
        self.start = (user.x, user.y)
        team = 1 - user.team
        gx = match.goal_x(team)
        self.inward = 1 if team == 0 else -1          # do gol para dentro do campo
        h = match.arena.height
        y = min(max(user.y, h / 2 - 50), h / 2 + 50)
        self.land = (gx + self.inward * 64, y)
        self.goal = (gx, y)
        match.dunk = self
        user.vx = user.vy = 0.0
        user.facing = (-float(self.inward), 0.0)

    def _hold(self, match):
        user, ball = self.user, match.ball
        user.magic_timer = max(user.magic_timer, 3)                   # passa por dentro de todos
        user.kick_cd = max(user.kick_cd, 3)
        user.knock = [0.0, 0.0]
        ball.x, ball.y = user.x - self.inward * 10, user.y - 1
        ball.vx = ball.vy = ball.vz = 0.0
        ball.z = user.lift + 44                                       # a bola lá em cima, nas mãos
        ball.held = True

    def update(self, match):
        user = self.user
        self.age += 1
        t = min(1.0, self.age / self.FRAMES)
        (x0, y0), (x1, y1) = self.start, self.land
        user.x, user.y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        user.lift = max(1.0, 4 * self.PEAK * t * (1 - t)) if t < 1 else 0   # no ar: ninguém derruba nem hackeia
        self._hold(match)
        if self.age % 3 == 0:
            match.particles.append(Particle(user.x, user.y + 18, 0, 0, (84, 162, 222), 14, 3))
        if t < 1:
            return
        # crava: a bola desce direto para dentro do gol (nem o goleiro alcança)
        user.lift = 0
        self.alive = False
        match.dunk = None
        ball = match.ball
        gx, gy = self.goal
        ball.x, ball.y = gx + self.inward * 24, gy
        ball.z, ball.vz = 0.0, 0.0
        ball.held = False
        ball.vx, ball.vy = -self.inward * 9.0, 0.0
        ball.homing_timer = 0
        ball.ghost_timer = 40
        ball.ghost_team = user.team
        match.last_touch = user
        match.possessor = None
        match.no_trap[user] = 30
        match.popup(user.x, user.y - 90, "ENTERRADA!", theme.BRASS)
        match.burst(ball.x, ball.y, (255, 236, 120), 22, speed=6)
        match.dust(user.x, user.y + 20, 10)
        match.camera.shake(9)
        match.assets.play("explosion", 0.5)

    def draw(self, surf, camera):
        pass


class Enterrada(SoccerPower):
    """Cauanzera: perto da área adversária, pula todo mundo e crava a bola no gol — não dá para
    defender, por isso a recarga é bem longa. Passiva de alto: cabeceia bolas mais altas."""
    name = "ENTERRADA"
    description = "Perto da área, pula todos e crava a bola no gol."
    cooldown = 25 * config.FPS
    needs_ball = True
    sound = "dash"
    release_frames = 0
    head_reach = 36
    RANGE = 600                                     # distância máxima da linha do gol adversário

    def use(self, user, match):
        if match.possessor is not user or getattr(match, "dunk", None) is not None:
            return False
        return super().use(user, match)

    def activate(self, user, match):
        if abs(match.goal_x(1 - user.team) - user.x) > self.RANGE:
            return False
        match.add_effect(Dunk(user, match))
        match.burst(user.x, user.y + 10, (84, 162, 222), 16, speed=5)
        return True

    def worth_using(self, user, match):
        return match.possessor is user and abs(match.goal_x(1 - user.team) - user.x) < self.RANGE - 40


class Hackear(SoccerPower):
    """Albeguinio: digita no notebook e os adversários ficam travados (e perdem a bola)."""
    name = "HACK"
    description = "Digita e trava os adversários por 2,5s."
    cooldown = 16 * config.FPS
    sound = "barrier"
    TYPING = round(0.6 * config.FPS)
    FREEZE = round(2.5 * config.FPS)

    def activate(self, user, match):
        from .entities import Hack
        match.add_effect(Hack(user, self.TYPING, self.FREEZE))
        return True

    def worth_using(self, user, match):
        owner = match.possessor
        ball = match.ball
        if owner is not None and owner.team != user.team:
            return abs(ball.x - match.goal_x(user.team)) < 900
        return owner is None and any(f.distance_to(ball) < 120 for f in match.foes_of(user)) \
            and user.distance_to(ball) > 200


class ExoBola(SoccerPower):
    """Borba Jr: com o exoesqueleto ninguém toma a bola dele, quem trombar nele cai e o corpo
    blindado segura qualquer chute."""
    name = "EXOESQUELETO"
    description = "4s: ninguém toma a bola, quem tromba cai e o chute para nele."
    cooldown = 15 * config.FPS
    sound = "barrier"
    FRAMES = 4 * config.FPS

    def activate(self, user, match):
        from .abilities import start_exo
        start_exo(user, match, self.FRAMES)
        return True

    def worth_using(self, user, match):
        ball = match.ball
        if match.possessor is user:
            return any(user.distance_to(f) < 140 for f in match.foes_of(user))
        coming = (ball.vx < -5) if user.team == 0 else (ball.vx > 5)
        return coming and abs(ball.x - match.goal_x(user.team)) < 700 and user.distance_to(ball) < 300


SOCCER_POWERS = {
    "guerreiro": Carrinho,
    "atirador": ChuteCerteiro,
    "tanque": MuralhaDoGol,
    "ninja": Sombra,
    "velocista": Arrancada,
    "aryel": Bomba,
    "fantasma": BolaFantasma,
    "tita": Gigante,
    "pirata": GanchoNaBola,
    "geada": Congelar,
    "aryel_corrompido": BombaSombria,
    "faisca": DribleMagico,
    "trovao": ChuteTrovao,
    "ginga": Caneta,
    "matador": FaroDeGol,
    "cauanzera": Enterrada,
    "albeguinio": Hackear,
    "borba": ExoBola,
}


def create_power(stats):
    return SOCCER_POWERS[stats.key]()
