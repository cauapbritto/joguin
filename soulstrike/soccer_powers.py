"""Poderes do futebol (botão SUPER). Cada personagem tem uma subclasse de SoccerPower."""
import math
import random
from abc import ABC, abstractmethod

import pygame

from . import config, theme
from .entities import Entity


class SoccerPower(ABC):
    name = ""
    description = ""
    cooldown = 12 * config.FPS
    needs_ball = False
    sound = "ability"

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
        return abs(match.goal_x(1 - user.team) - user.x) < 600


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
        return coming and abs(ball.x - home) < 500


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
        return abs(match.goal_x(1 - user.team) - user.x) < 700


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


SOCCER_POWERS = {
    "guerreiro": Carrinho,
    "atirador": ChuteCerteiro,
    "tanque": MuralhaDoGol,
    "ninja": Sombra,
    "velocista": Arrancada,
    "aryel": Bomba,
    "fantasma": BolaFantasma,
    "tita": Gigante,
}


def create_power(stats):
    return SOCCER_POWERS[stats.key]()
