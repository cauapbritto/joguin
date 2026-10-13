"""Habilidades especiais. Cada personagem tem uma subclasse de Ability (polimorfismo):
o lutador só chama ``ability.use(...)`` e não precisa saber qual habilidade é."""
import math
from abc import ABC, abstractmethod

from . import config
from .entities import Barrier, FrostNova, Hook


class Ability(ABC):
    sound = "ability"

    def __init__(self, stats):
        self.name = stats.ability_name
        self.description = stats.ability_desc

    def use(self, user, match, target):
        match.assets.play(self.sound, 0.4)
        self.activate(user, match, target)

    @abstractmethod
    def activate(self, user, match, target):
        """Efeito da habilidade."""

    def worth_using(self, user, target, dist):
        """Dica para a CPU: vale a pena usar agora?"""
        return True


def _aim(user, target):
    if target is not None:
        dx, dy = user.direction_to(target)
        if dx or dy:
            return dx, dy
    return user.facing


def _fan(user, match, target, count, spread_deg, speed, damage):
    dx, dy = _aim(user, target)
    base = math.atan2(dy, dx)
    for i in range(count):
        t = i / (count - 1) - 0.5 if count > 1 else 0
        a = base + math.radians(spread_deg) * t
        match.spawn_bullet(user, math.cos(a), math.sin(a), speed, damage)


class Investida(Ability):
    DAMAGE = 30

    def activate(self, user, match, target):
        user.start_charge(_aim(user, target), self.DAMAGE)

    def worth_using(self, user, target, dist):
        return 100 < dist < 360


class Rajada(Ability):
    def activate(self, user, match, target):
        _fan(user, match, target, 5, 30, user.weapons[0].bullet_speed, user.stats.weapons[0].damage)

    def worth_using(self, user, target, dist):
        return dist < 420


class Muralha(Ability):
    sound = "barrier"

    def activate(self, user, match, target):
        dx, dy = _aim(user, target)
        match.add_effect(Barrier(user, user.x + dx * 44, user.y + dy * 44, dx, dy, 4 * config.FPS))

    def worth_using(self, user, target, dist):
        return dist > 160


class ShurikenTripla(Ability):
    def activate(self, user, match, target):
        _fan(user, match, target, 3, 45, user.weapons[0].bullet_speed + 2, 12)

    def worth_using(self, user, target, dist):
        return dist < 380


class Turbo(Ability):
    def activate(self, user, match, target):
        user.speed_timer = 4 * config.FPS

    def worth_using(self, user, target, dist):
        return dist > 260 or user.hp < user.stats.max_hp * 0.4


class Explosao(Ability):
    sound = "explosion"

    def activate(self, user, match, target):
        for k in range(8):
            a = k * math.pi / 4
            match.spawn_bullet(user, math.cos(a), math.sin(a), user.weapons[0].bullet_speed, 25, explosive=True)

    def worth_using(self, user, target, dist):
        return dist < 220


class Teletransporte(Ability):
    def activate(self, user, match, target):
        match.burst(user.x, user.y - 16, user.stats.color, 18)
        x, y = match.arena.random_free_spot(user.radius)
        user.x, user.y = x, y
        user.vx = user.vy = 0
        user.teleport_flash = 20
        match.burst(x, y - 16, user.stats.color, 18)

    def worth_using(self, user, target, dist):
        return dist < 110 or user.hp < user.stats.max_hp * 0.3


class Invulneravel(Ability):
    def activate(self, user, match, target):
        user.invulnerable_timer = 3 * config.FPS

    def worth_using(self, user, target, dist):
        return user.hp < user.stats.max_hp * 0.6 and dist < 400


class Gancho(Ability):
    """Pirata: o gancho puxa o inimigo para a frente do sabre."""
    sound = "shoot"

    def activate(self, user, match, target):
        dx, dy = _aim(user, target)
        user.facing = (dx, dy)
        user.shoot_flash = 4
        match.bullets.append(Hook(user, user.x + dx * 18, user.y + dy * 18 - 4, dx, dy))

    def worth_using(self, user, target, dist):
        return 130 < dist < Hook.SPEED * Hook.RANGE_FRAMES - 30


class Nevasca(Ability):
    """Geada: onda de gelo em volta dela."""
    sound = "barrier"

    def activate(self, user, match, target):
        match.add_effect(FrostNova(user, user.x, user.y))

    def worth_using(self, user, target, dist):
        return dist < 170


ABILITIES = {
    "guerreiro": Investida,
    "atirador": Rajada,
    "tanque": Muralha,
    "ninja": ShurikenTripla,
    "velocista": Turbo,
    "aryel": Explosao,
    "fantasma": Teletransporte,
    "tita": Invulneravel,
    "pirata": Gancho,
    "geada": Nevasca,
}


def create_ability(stats):
    return ABILITIES[stats.key](stats)
