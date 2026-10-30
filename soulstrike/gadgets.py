"""Armas da Lag Lobby (capítulo 2 da campanha): o que cada uma faz de especial.

- Taser de Rede: a rede elétrica prende quem leva por 1 s.
- Rifle de Plasma: segurar carrega; o tiro carregado atravessa a fila inteira.
- Drone de Bolso: solta um drone aliado que fica 6 s em volta do dono atirando sozinho.
- Teclado Mecânico: combo rápido; o 3º golpe espalha teclas que machucam.
- Escudo de Choque: segurando, segura os tiros que vêm pela frente; ao soltar, empurrão elétrico.
- Manopla do Exo (roubada): o 3º soco abre uma onda de choque no chão.
"""
import math
import random

import pygame

from .entities import Bullet, Entity, Particle, hostile
from .projectiles import Projectile, _unit

COMBO_WINDOW = 45             # quadros entre um golpe e outro para continuar o combo
PLASMA = (110, 255, 200)
SHOCK = (130, 200, 255)


# ─────────────────────────────────────────────
#  Projéteis
# ─────────────────────────────────────────────
class NetShot(Projectile):
    """Taser de Rede: a rede abre no voo e, no alvo, prende por 1 s com faíscas."""
    sprite = "Rede"
    ROOT = 60

    def on_hit(self, target, match):
        if target.root(self.ROOT):
            match.popup(target.x, target.y - 62, "PRESO NA REDE", SHOCK)
        match.burst(target.x, target.y - 18, SHOCK, 8, speed=3)

    def draw(self, surf, camera):
        self.draw_sprite(surf, camera, angle=self.age * 12)


class PlasmaShot(Projectile):
    """Rifle de Plasma: bolinha verde; carregado, vira um feixe grosso que atravessa todo mundo."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.charged = self.power >= 0.99
        if self.charged:
            self.pierce = 99
            self.radius = 7

    @staticmethod
    def speed_for(weapon, power):
        return weapon.bullet_speed * (0.8 + 0.6 * power)

    def on_launch(self, match):
        if self.charged:
            match.burst(self.x, self.y, PLASMA, 10, speed=3)
            match.camera.shake(2)

    def update(self, match):
        super().update(match)
        if self.charged and self.age % 2 == 0:
            match.particles.append(Particle(self.x, self.y, 0, 0, PLASMA, 10, 3))

    def draw(self, surf, camera):
        dx, dy = _unit(self.vx, self.vy)
        hx, hy = self.x - camera.x, self.y - camera.y
        length = 22 if self.charged else 10
        width = 7 if self.charged else 3
        tail = (round(hx - dx * length), round(hy - dy * length))
        pygame.draw.line(surf, (20, 90, 70), tail, (round(hx), round(hy)), width + 2)
        pygame.draw.line(surf, PLASMA, tail, (round(hx), round(hy)), width)
        pygame.draw.line(surf, (240, 255, 250), tail, (round(hx), round(hy)), max(1, width // 3))


class PocketDroneShot(Projectile):
    """Drone de Bolso: o "tiro" só solta o drone aliado do lado do dono."""

    def on_launch(self, match):
        match.add_effect(AllyDrone(self.owner, self.damage))
        match.burst(self.owner.x, self.owner.y - 30, SHOCK, 8, speed=2)
        self.alive = False

    def update(self, match):
        self.alive = False

    def draw(self, surf, camera):
        pass


class KeyCap(Projectile):
    """Tecla que voa do Teclado Mecânico."""
    COLORS = ((230, 230, 236), (60, 200, 230), (240, 90, 80), (250, 210, 80))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.color = random.choice(self.COLORS)
        self.life = 26

    def update(self, match):
        super().update(match)
        self.life -= 1
        if self.life <= 0:
            self.alive = False

    def draw(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        surf.fill((24, 20, 28), (sx - 4, sy - 4, 9, 9))
        surf.fill(self.color, (sx - 3, sy - 3, 7, 7))
        surf.fill((255, 255, 255), (sx - 3, sy - 3, 7, 1))


def register_projectiles(table):
    table.update({"rede": NetShot, "plasma": PlasmaShot, "drone_bolso": PocketDroneShot, "tecla": KeyCap})


# ─────────────────────────────────────────────
#  Drone aliado
# ─────────────────────────────────────────────
class AllyDrone(Entity):
    """Drone de Bolso: voa em volta do dono por 6 s e atira no inimigo mais perto."""

    LIFE = 6 * 60
    FIRE = 26
    REACH = 430
    SPEED = 10

    def __init__(self, owner, damage):
        super().__init__(owner.x, owner.y - 40)
        self.owner = owner
        self.damage = max(1, damage)
        self.age = 0
        self.angle = random.uniform(0, math.tau)

    def update(self, match):
        self.age += 1
        owner = self.owner
        if self.age >= self.LIFE or not owner.alive_in_match:
            self.alive = False
            match.burst(self.x, self.y, SHOCK, 6, speed=2)
            return
        self.angle += 0.06
        tx, ty = owner.x + math.cos(self.angle) * 46, owner.y - 46 + math.sin(self.angle) * 18
        self.x += (tx - self.x) * 0.2
        self.y += (ty - self.y) * 0.2
        if self.age % self.FIRE:
            return
        foes = [f for f in match.fighters if f.alive_in_match and hostile(owner, f)
                and math.hypot(f.x - self.x, f.y - self.y) < self.REACH
                and not match.arena.blocks_segment((self.x, self.y + 40), (f.x, f.y))]
        if not foes:
            return
        t = min(foes, key=lambda f: math.hypot(f.x - self.x, f.y - self.y))
        dx, dy = _unit(t.x - self.x, t.y - 10 - self.y)
        match.bullets.append(Bullet(owner, self.x, self.y + 6, dx, dy, self.SPEED, self.damage, SHOCK))
        match.assets.play("bip", 0.15)

    def draw(self, surf, camera):
        pass

    def draw_over(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        blink = self.age > self.LIFE - 60 and (self.age // 5) % 2
        spin = (self.age // 2) % 2
        for hx in (-7, 7):
            surf.fill((200, 210, 220), (sx + hx - (3 if spin else 2), sy - 6, 6 if spin else 4, 1))
        surf.fill((20, 22, 30), (sx - 7, sy - 5, 14, 9))
        surf.fill((70, 90, 110) if not blink else (40, 50, 60), (sx - 6, sy - 4, 12, 7))
        surf.fill(SHOCK, (sx - 2, sy - 2, 4, 3))
        surf.fill((240, 250, 255), (sx - 1, sy - 2, 1, 1))


# ─────────────────────────────────────────────
#  Golpes de perto (chamado a cada golpe)
# ─────────────────────────────────────────────
def on_melee(fighter, weapon, match, damage):
    """Combo das armas de perto da Lag Lobby: o 3º golpe seguido tem o efeito especial."""
    if not weapon.special or weapon.special == "escudo":
        return
    if fighter.combo_timer > 0:
        fighter.combo_count += 1
    else:
        fighter.combo_count = 1
    fighter.combo_timer = COMBO_WINDOW
    if fighter.combo_count < 3:
        return
    fighter.combo_count = 0
    fx, fy = fighter.facing
    if weapon.special == "teclas":
        base = math.atan2(fy, fx)
        for k in range(-2, 3):
            a = base + k * 0.28
            dx, dy = math.cos(a), math.sin(a)
            match.bullets.append(KeyCap(fighter, weapon, fighter.x + dx * 20, fighter.y - 8 + dy * 20, dx, dy,
                                        9, max(1, round(damage * 0.4))))
        match.assets.play("teclado", 0.5)
        match.popup(fighter.x, fighter.y - 60, "CTRL+ALT+DEL!", (60, 200, 230))
    elif weapon.special == "onda":
        from .enemies import Shockwave
        x, y = fighter.x + fx * 50, fighter.y + fy * 50
        match.add_effect(Shockwave(fighter, x, y, 110, round(damage * 0.7), stun=22, color=(90, 170, 255)))
        match.assets.play("soco_metal", 0.5)


# ─────────────────────────────────────────────
#  Escudo de Choque
# ─────────────────────────────────────────────
GUARD_FULL = 40               # segurando tanto assim, o empurrão sai no máximo


def shield_hold(fighter, match):
    """Segurando ATACAR com o escudo: segura os tiros que chegam pela frente."""
    fighter.guard_frames += 1
    fighter.aim_timer = max(fighter.aim_timer, 4)
    if fighter.guard_frames % 3 == 0:
        fighter.deflect_front(match, fighter.weapon.reach + 30)
    return True


def shield_release(fighter, match):
    """Soltou: empurrão elétrico na frente (mais forte quanto mais tempo segurou)."""
    weapon = fighter.weapon
    power = min(1.0, fighter.guard_frames / GUARD_FULL)
    fighter.guard_frames = 0
    fighter.attack_cd = weapon.cooldown
    fighter.melee_flash = 12
    fx, fy = fighter.facing
    damage = round(weapon.damage * (0.6 + 0.8 * power) * fighter.damage_mult * fighter.weapon_mult(weapon))
    reach = weapon.reach + 30
    for other in match.opponents_of(fighter):
        if not other.alive_in_match:
            continue
        dx, dy = other.x - fighter.x, other.y - fighter.y
        d = math.hypot(dx, dy)
        if d <= reach + other.radius and (dx * fx + dy * fy) > -0.1 * d:
            if other.take_damage(damage, fighter.x, fighter.y, attacker=fighter, match=match):
                force = (8 + 8 * power) * (1 - other.knock_resist)
                ux, uy = _unit(dx, dy) if d > 1 else (fx, fy)
                other.knock = [ux * force, uy * force]
                if power >= 0.99:
                    other.stun(20)
    for k in range(10):
        a = math.atan2(fy, fx) + random.uniform(-0.7, 0.7)
        r = random.uniform(20, reach)
        match.particles.append(Particle(fighter.x + math.cos(a) * r, fighter.y - 14 + math.sin(a) * r,
                                        math.cos(a) * 2, math.sin(a) * 2, SHOCK, 14, 3))
    match.assets.play("choque", 0.5)


def draw_guard(surf, camera, fighter):
    """Arco azul na frente de quem está segurando o escudo."""
    if fighter.guard_frames <= 0:
        return
    fx, fy = fighter.facing
    cx, cy = round(fighter.x - camera.x + fx * 26), round(fighter.y - 16 - camera.y + fy * 18)
    base = math.atan2(fy, fx)
    pts = [(cx + math.cos(base + a) * 6 - math.cos(base) * 6 + math.cos(base + a) * 16,
            cy + math.sin(base + a) * 6 + math.sin(base + a) * 16) for a in (-1.0, -0.5, 0.0, 0.5, 1.0)]
    t = min(1.0, fighter.guard_frames / GUARD_FULL)
    color = tuple(round(c * (0.6 + 0.4 * t)) for c in SHOCK)
    pygame.draw.lines(surf, color, False, pts, 3 if t < 1 else 4)
