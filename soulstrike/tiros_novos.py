"""Tiros e efeitos das armas novas (os números ficam em armas_novas.py).

Os tiros novos usam uma classe só (NewShot), configurada por estilo em SHOTS: quantos tiros saem
de uma vez, se atravessam, se quicam na parede, o que fazem em quem leva (gelo, tontura, raiz,
medo, fogo, empurrão, energia). O sino e o flash do espelho acertam na hora, numa área. As de
perto têm um efeito por golpe em MELEE_FX.
"""
import math
import random
from dataclasses import dataclass

import pygame

from . import energia
from .armas_novas import BATTERY_KILL, HEAVY
from .entities import Particle

ICE = (150, 212, 240)


# ── tiros ─────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Shot:
    color: tuple = (236, 230, 220)
    radius: int = 4
    count: int = 1            # quantos saem de uma vez
    spread: float = 0.0       # abertura do leque (radianos entre um e outro)
    pierce: int = 0           # atravessa quantos (99 = todos)
    life: int = 90            # quadros até sumir
    bounce: int = 0           # quica na parede quantas vezes
    effect: str = ""          # slow, stun, root, fear, burn, freeze, knock, energy
    power: int = 0            # força do efeito (quadros, empurrão ou energia)
    blast: int = 0            # explode com este raio ao acabar
    drag: float = 1.0         # freia no ar (vento, jato)
    sprite: str = ""          # arte da arma (gira no voo)
    area: str = ""            # "ring" (em volta do dono) ou "cone" (na frente): acerta na hora
    jitter: float = 0.0       # tremidinha na mira


SHOTS = {
    "n_pedra": Shot((150, 146, 140), 5, effect="knock", power=5),
    "n_dardo": Shot((120, 200, 90), 3, effect="burn", power=90),
    "n_sino": Shot((230, 200, 120), area="ring", power=170, effect="fear"),
    "n_grampo": Shot((200, 204, 214), 3, jitter=0.08),
    "n_choque": Shot((255, 236, 90), 5, effect="stun", power=40),
    "n_papel": Shot((240, 236, 222), 5, count=3, spread=0.22, life=60),
    "n_bala": Shot((250, 220, 120), 3),
    "n_spawner": Shot((120, 240, 200), 3, jitter=0.06),
    "n_vento": Shot((240, 236, 230), 7, pierce=99, life=22, drag=0.93, effect="knock", power=3, jitter=0.15),
    "n_agua": Shot((70, 168, 236), 4, effect="slow", power=40),
    "n_botox": Shot((232, 122, 172), 4, effect="freeze", power=30),
    "n_flash": Shot((255, 255, 240), area="cone", power=230, effect="stun", ),
    "n_gelo": Shot(ICE, 6, effect="freeze", power=50),
    "n_laser": Shot((255, 80, 90), 3, pierce=99, life=40),
    "n_boleto": Shot(),               # usa o bumerangue (BoletoShot)
    "n_tinta": Shot((40, 40, 90), 4, pierce=1, effect="slow", power=50),
    "n_caca": Shot((250, 230, 170), 4, pierce=1, life=110),
    "n_fax": Shot((240, 236, 222), 5, count=5, spread=0.18, life=50),
    "n_pasta": Shot((176, 120, 74), 7, effect="knock", power=10),
    "n_sugador": Shot((150, 120, 255), 4, pierce=99, life=30, effect="energy", power=1),
    "n_escopeta": Shot((250, 220, 120), 3, count=5, spread=0.12, life=30, effect="knock", power=4),
    "n_carabina": Shot((250, 220, 120), 3, count=3, spread=0.04),
    "n_prego": Shot((200, 204, 214), 3, effect="root", power=30),
}


def _apply(effect, power, owner, target, match):
    """O efeito do tiro (ou do golpe) em quem levou."""
    if not effect or not target.alive_in_match:
        return
    if effect == "slow":
        target.slow(power)
    elif effect == "stun":
        target.stun(power)
    elif effect == "root":
        target.root(power)
    elif effect == "fear":
        target.scare(power, owner.x, owner.y)
    elif effect == "freeze":
        target.freeze(power)
    elif effect == "burn":
        target.burn(owner, 2, power)
    elif effect == "knock":
        dx, dy = target.x - owner.x, target.y - owner.y
        d = math.hypot(dx, dy) or 1
        force = power * (1 - target.knock_resist)
        target.knock = [dx / d * force, dy / d * force]
    elif effect == "energy":
        energia.gain(owner, power)
        match.particles.append(Particle(target.x, target.y - 20, (owner.x - target.x) / 18,
                                        (owner.y - target.y) / 18, energia.ENERGY_COLOR, 18, 3))


from .projectiles import Boomerang, Projectile  # noqa: E402


class NewShot(Projectile):
    """Tiro das armas novas: tudo vem de SHOTS[estilo]."""

    @classmethod
    def launch(cls, match, owner, weapon, direction, damage, target=None, power=1.0, explosive=False):
        spec = SHOTS.get(weapon.style, Shot())
        if spec.area:
            _area_hit(match, owner, weapon, direction, damage, spec)
            return cls._dud(owner, weapon, damage)
        base = math.atan2(direction[1], direction[0])
        shots = []
        for k in range(spec.count):
            a = base + (k - (spec.count - 1) / 2) * spec.spread + random.uniform(-spec.jitter, spec.jitter)
            dx, dy = math.cos(a), math.sin(a)
            x, y = owner.x + dx * cls.muzzle, owner.y + dy * cls.muzzle - 4
            shot = cls(owner, weapon, x, y, dx, dy, weapon.bullet_speed, damage, target, power, explosive)
            shot.spec = spec
            shot.radius = spec.radius
            shot.color = spec.color
            shot.pierce += spec.pierce
            shot.life = spec.life
            shot.bounces = spec.bounce
            shot.on_launch(match)
            shots.append(shot)
        if weapon.style == "n_spawner":
            _spawner_tick(owner, match)
        return shots if len(shots) > 1 else shots[0]

    @classmethod
    def _dud(cls, owner, weapon, damage):
        shot = cls(owner, weapon, owner.x, owner.y, 1, 0, 0, damage)
        shot.spec = Shot()
        shot.life = 0
        shot.alive = False
        return shot

    def update(self, match):
        super().update(match)
        if self.spec.drag != 1.0:
            self.vx *= self.spec.drag
            self.vy *= self.spec.drag
            self.radius = min(14, self.spec.radius + self.age // 4)
        self.life -= 1
        if self.life <= 0:
            self.alive = False

    def survives_hit(self):
        if self.pierce >= 90:
            return True
        return super().survives_hit()

    def on_hit(self, target, match):
        _apply(self.spec.effect, self.spec.power, self.owner, target, match)

    def on_wall(self, wall, match):
        if self.bounces > 0:
            self.bounces -= 1
            r = wall.rect
            if r.left <= self.x <= r.right:
                self.vy = -self.vy
            else:
                self.vx = -self.vx
            return True
        match.burst(self.x, self.y, self.color, 3, speed=2, size=3)
        return False

    def draw(self, surf, camera):
        if self.spec.sprite:
            self.draw_sprite(surf, camera)
            return
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        if self.pierce >= 90 and self.spec.life <= 40:          # feixe (laser, sugador)
            dx, dy = self.vx, self.vy
            d = math.hypot(dx, dy) or 1
            tail = (round(sx - dx / d * 18), round(sy - dy / d * 18))
            pygame.draw.line(surf, self.color, tail, (sx, sy), self.radius + 1)
            pygame.draw.line(surf, (255, 255, 255), tail, (sx, sy), 1)
            return
        r = self.radius
        pygame.draw.circle(surf, (20, 14, 22), (sx, sy), r + 1)
        pygame.draw.circle(surf, self.color, (sx, sy), r)
        if r > 2:
            surf.fill((255, 255, 255), (sx - 1, sy - r // 2, 2, 2))


class BoletoShot(Boomerang):
    """Boleto Bumerangue: o bumerangue com a cara do boleto (sempre volta)."""

    sprite = "Boleto Bumerangue"


def _area_hit(match, owner, weapon, direction, damage, spec):
    """Sino (em volta) e flash do espelho (na frente): acerta na hora quem está na área."""
    fx, fy = direction
    for other in match.opponents_of(owner):
        if not other.alive_in_match:
            continue
        dx, dy = other.x - owner.x, other.y - owner.y
        d = math.hypot(dx, dy)
        if d > spec.power:
            continue
        if spec.area == "cone" and d > 1 and (dx * fx + dy * fy) / d < 0.45:
            continue
        if other.take_damage(damage, owner.x, owner.y, attacker=owner, match=match):
            _apply(spec.effect, 60 if spec.effect == "fear" else 40, owner, other, match)
    if spec.area == "ring":
        for k in range(24):
            a = k * math.tau / 24
            match.particles.append(Particle(owner.x + math.cos(a) * 20, owner.y - 10 + math.sin(a) * 12,
                                            math.cos(a) * 5, math.sin(a) * 3, spec.color, 22, 4))
        match.assets.play("explosion", 0.25)
    else:
        a0 = math.atan2(fy, fx)
        for _ in range(18):
            a = a0 + random.uniform(-0.5, 0.5)
            s = random.uniform(3, 8)
            match.particles.append(Particle(owner.x + fx * 20, owner.y - 14 + fy * 20, math.cos(a) * s,
                                            math.sin(a) * s, spec.color, 14, 4))
        match.assets.play("click", 0.5)


def _spawner_tick(owner, match):
    """Rifle Spawner: a cada 15 tiros nasce um drone aliado do lado do dono."""
    owner.spawner_shots = getattr(owner, "spawner_shots", 0) + 1
    if owner.spawner_shots % 15:
        return
    from .gadgets import AllyDrone
    match.add_effect(AllyDrone(owner, 5))
    match.popup(owner.x, owner.y - 70, "SPAWN!", (120, 240, 200))


# ── golpes de perto ──────────────────────────────────────────────────
MELEE_FX = {
    "queima": ("burn", 120), "sangra": ("burn", 60), "atordoa": ("stun", 24), "gelo": ("slow", 60),
    "empurra": ("knock", 12), "puxa": ("pull", 0),
}


def on_melee_hit(fighter, weapon, other, match, special=True):
    """Efeito por golpe das armas novas de perto (só se o efeito foi pago)."""
    if not special or weapon.special not in MELEE_FX:
        return
    effect, power = MELEE_FX[weapon.special]
    if effect == "pull":
        fx, fy = fighter.facing
        other.pull(fighter.x + fx * 44, fighter.y + fy * 44, frames=10)
        return
    _apply(effect, power, fighter, other, match)


def on_kill(attacker, victim, match):
    """Bateria Portátil: inimigo derrubado com ela na mão dá energia."""
    if match is None or getattr(attacker.weapon, "special", "") != "bateria" or not energia.enabled(attacker):
        return
    if energia.gain(attacker, BATTERY_KILL):
        match.popup(attacker.x, attacker.y - 78, f"+{BATTERY_KILL} ENERGIA", energia.ENERGY_COLOR)


def speed_mult(fighter):
    """Arma pesada na mão deixa o herói mais lento (Excalitora)."""
    weapon = fighter.weapon
    return HEAVY.get(weapon.name, 1.0) if weapon is not None else 1.0


def register_projectiles(table):
    for style in SHOTS:
        table[style] = NewShot
    table["n_boleto"] = BoletoShot
