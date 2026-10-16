"""Projéteis próprios de cada arma de tiro.

Cada arma de tiro tem um estilo (WeaponStats.style) e cada estilo é uma subclasse de
Projectile, que herda de Bullet. A partida só chama update(), draw(), can_hit(), on_hit(),
survives_hit() e on_wall(); cada classe responde do seu jeito (polimorfismo):

- Arrow (arco): tensionada atravessa um alvo; finca na parede.
- Tracer (rifle): risco de luz e a cápsula pulando para o lado.
- Spear (lança): atravessa, empurra forte e finca na parede.
- ShurikenStar (shuriken): gira e ricocheteia na parede.
- ThrowingStar (estrela): gira, solta faíscas e acertar dá embalo.
- Grenade (granada): vai pelo alto, por cima das paredes, e explode onde cai.
- Orb (orbe): persegue o alvo e atravessa paredes.
- ChainBall (corrente): bola de ferro presa na corrente; vai, acerta, atordoa e volta.
- LeadBall (pistola): bala de chumbo, fumaça na saída e empurrão forte.
- IceShard (cristal): deixa o alvo lento e estilhaça na parede.
- FloppyDisk (disquete), Pendrive (vírus que tira vida aos poucos) e PulseShot (Canhão de Pulso:
  segurar carrega um tiro maior que empurra).
"""
import math
import random

import pygame

from . import theme, weapon_art
from .entities import Bullet, Entity, Particle, push_circle_out


def _angle(vx, vy):
    return math.degrees(math.atan2(vy, vx))


def _unit(x, y):
    d = math.hypot(x, y) or 1.0
    return x / d, y / d


class Projectile(Bullet):
    """Base dos projéteis das armas: guarda a arma, o alvo e a força do tiro."""

    sprite = None            # sprite em assets/weapons desenhado girado na direção do voo
    muzzle = 18              # distância do centro do lutador até onde o tiro nasce

    def __init__(self, owner, weapon, x, y, dx, dy, speed, damage, target=None, power=1.0, explosive=False):
        super().__init__(owner, x, y, dx, dy, speed, damage, owner.stats.color, explosive)
        self.weapon = weapon
        self.target = target
        self.power = power
        self.age = 0

    @classmethod
    def launch(cls, match, owner, weapon, direction, damage, target=None, power=1.0, explosive=False):
        dx, dy = direction
        x, y = owner.x + dx * cls.muzzle, owner.y + dy * cls.muzzle - 4
        proj = cls(owner, weapon, x, y, dx, dy, cls.speed_for(weapon, power), damage, target, power, explosive)
        proj.on_launch(match)
        return proj

    @staticmethod
    def speed_for(weapon, power):
        return weapon.bullet_speed

    def on_launch(self, match):
        """Efeito na saída do tiro (fumaça, cápsula...)."""

    def update(self, match):
        self.age += 1
        super().update(match)

    def draw_sprite(self, surf, camera, angle=None, lift=0):
        if angle is None:
            angle = _angle(self.vx, self.vy)
        img = weapon_art.rotated(self.sprite, angle) if self.sprite else None
        if img is None:
            Bullet.draw(self, surf, camera)
            return
        surf.blit(img, img.get_rect(center=(round(self.x - camera.x), round(self.y - camera.y - lift))))

    def draw(self, surf, camera):
        if self.sprite:
            self.draw_sprite(surf, camera)
        else:
            Bullet.draw(self, surf, camera)


class Stuck(Entity):
    """Flecha ou lança fincada na parede: fica um tempo e some."""

    def __init__(self, sprite, x, y, angle, life=90):
        super().__init__(x, y)
        self.sprite = sprite
        self.angle = angle
        self.life = self.total = life

    def update(self, match):
        self.life -= 1
        if self.life <= 0:
            self.alive = False

    def draw(self, surf, camera):
        img = weapon_art.rotated(self.sprite, self.angle)
        if img is None:
            return
        if self.life < 30:
            img = img.copy()
            img.set_alpha(round(255 * self.life / 30))
        surf.blit(img, img.get_rect(center=(round(self.x - camera.x), round(self.y - camera.y))))


def _stick(match, proj, sprite, depth=6, life=90):
    """Deixa o projétil fincado um pouco para dentro da parede."""
    dx, dy = _unit(proj.vx, proj.vy)
    match.add_effect(Stuck(sprite, proj.x + dx * depth, proj.y + dy * depth, _angle(dx, dy), life))
    match.burst(proj.x, proj.y, (200, 180, 140), 4, speed=2)


# ── arco ─────────────────────────────────────
class Arrow(Projectile):
    sprite = "Flecha"
    muzzle = 16

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.charged = self.power >= 0.99
        if self.charged:
            self.pierce += 1                 # flecha tensa atravessa um alvo

    @staticmethod
    def speed_for(weapon, power):
        return weapon.bullet_speed * (0.85 + 0.6 * power)

    def on_wall(self, wall, match):
        _stick(match, self, self.sprite)
        return False

    def draw(self, surf, camera):
        if self.charged:
            # rastro de luz da flecha tensa
            dx, dy = _unit(self.vx, self.vy)
            for k in range(1, 4):
                px, py = self.x - dx * 8 * k - camera.x, self.y - dy * 8 * k - camera.y
                s = 4 - k
                surf.fill((255, 236, 170), (round(px) - s // 2, round(py) - s // 2, s, s))
        self.draw_sprite(surf, camera)


# ── rifle ────────────────────────────────────
class Tracer(Projectile):
    muzzle = 22

    def on_launch(self, match):
        # cápsula pulando para o lado da arma
        dx, dy = _unit(self.vx, self.vy)
        side = random.choice((-1, 1))
        match.particles.append(Particle(self.owner.x, self.owner.y - 8,
                                        -dy * side * 1.8 - dx * 0.6 + random.uniform(-0.4, 0.4),
                                        dx * side * 1.8 - dy * 0.6 - 1.6,
                                        (232, 186, 84), 24, 3, gravity=0.22))

    def draw(self, surf, camera):
        dx, dy = _unit(self.vx, self.vy)
        hx, hy = self.x - camera.x, self.y - camera.y
        tail = (round(hx - dx * 14), round(hy - dy * 14))
        head = (round(hx), round(hy))
        pygame.draw.line(surf, (110, 70, 30), tail, head, 4)
        pygame.draw.line(surf, (255, 206, 110), tail, head, 2)
        pygame.draw.line(surf, (255, 250, 230), (round(hx - dx * 6), round(hy - dy * 6)), head, 1)


# ── lança ────────────────────────────────────
class Spear(Projectile):
    sprite = "Lança"
    muzzle = 12

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pierce += 1                     # a lança atravessa o primeiro

    def on_hit(self, target, match):
        target.knock = [k * 1.7 for k in target.knock]

    def on_wall(self, wall, match):
        _stick(match, self, self.sprite, depth=10, life=110)
        match.camera.shake(2)
        return False


# ── shuriken ─────────────────────────────────
class ShurikenStar(Projectile):
    sprite = "Shuriken"
    BOUNCES = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bounces = self.BOUNCES

    def on_wall(self, wall, match):
        res = push_circle_out(self.x, self.y, self.radius + 1, wall.rect)
        if self.bounces <= 0 or res is None:
            match.burst(self.x, self.y, (220, 226, 236), 5, speed=3)
            return False
        self.x, self.y, nx, ny = res
        dot = self.vx * nx + self.vy * ny
        if dot < 0:
            self.vx -= 2 * dot * nx
            self.vy -= 2 * dot * ny
        self.bounces -= 1
        match.burst(self.x, self.y, (250, 240, 200), 6, speed=3)
        match.assets.play("click", 0.25)
        return True

    def draw(self, surf, camera):
        self.draw_sprite(surf, camera, angle=self.age * 45)


# ── estrela ──────────────────────────────────
class ThrowingStar(Projectile):
    sprite = "Estrela"
    HASTE = 70                               # quadros de embalo ao acertar

    def update(self, match):
        super().update(match)
        if self.age % 3 == 0:
            match.particles.append(Particle(self.x, self.y, random.uniform(-0.4, 0.4), random.uniform(-0.4, 0.4),
                                            random.choice(((255, 214, 90), (255, 244, 190))), 14, 3))

    def on_hit(self, target, match):
        owner = self.owner
        if owner.haste_timer < 20:
            match.popup(owner.x, owner.y - 60, "EMBALO", theme.BRASS)
        owner.haste_timer = self.HASTE

    def draw(self, surf, camera):
        self.draw_sprite(surf, camera, angle=self.age * 30)


# ── granada ──────────────────────────────────
class Grenade(Projectile):
    sprite = "Granada"
    lobbed = True
    MAX_RANGE = 420
    blast = 66                               # raio da explosão (um pouco maior que a bomba comum)

    @classmethod
    def launch(cls, match, owner, weapon, direction, damage, target=None, power=1.0, explosive=True):
        dx, dy = direction
        if target is not None:
            # mira um pouco à frente de quem está correndo (onde ele vai estar quando a granada cair)
            dist = math.hypot(target.x - owner.x, target.y - owner.y)
            lead = min(1.0, dist / (weapon.bullet_speed * 50)) * 22
            px = target.x + getattr(target, "vx", 0.0) * lead
            py = target.y + getattr(target, "vy", 0.0) * lead
            dx, dy = _unit(px - owner.x, py - owner.y)
            dist = min(cls.MAX_RANGE, math.hypot(px - owner.x, py - owner.y))
        else:
            dist = cls.MAX_RANGE * 0.7
        arena = match.arena
        tx = min(max(owner.x + dx * dist, 40), arena.width - 40)
        ty = min(max(owner.y + dy * dist, 40), arena.height - 40)
        tx, ty = arena.free_spot(tx, ty, 10)
        x, y = owner.x + dx * 14, owner.y + dy * 14 - 4
        proj = cls(owner, weapon, x, y, dx, dy, weapon.bullet_speed, damage, target, power, True)
        proj.start = (x, y)
        proj.end = (tx, ty)
        proj.flight = min(52, max(16, round(math.hypot(tx - x, ty - y) / max(1.0, weapon.bullet_speed))))
        proj.vx, proj.vy = (tx - x) / proj.flight, (ty - y) / proj.flight
        proj.peak = 34 + proj.flight
        proj.z = 0.0
        return proj

    def can_hit(self, fighter):
        return False                         # no ar não acerta ninguém: explode onde cair

    def update(self, match):
        self.age += 1
        t = min(1.0, self.age / self.flight)
        (x0, y0), (x1, y1) = self.start, self.end
        self.x, self.y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        self.z = 4 * self.peak * t * (1 - t)
        if t >= 1:
            self.alive = False               # a partida cria a explosão

    def draw(self, surf, camera):
        # onde vai cair (dá para fugir) e a sombra no chão
        ex, ey = round(self.end[0] - camera.x), round(self.end[1] - camera.y)
        pulse = 2 if (self.age // 4) % 2 else 1
        r = self.blast
        pygame.draw.ellipse(surf, (232, 108, 52), (ex - r, ey + 14 - r // 4, r * 2, r // 2), pulse)
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        shrink = max(4, 12 - round(self.z / 10))
        pygame.draw.ellipse(surf, (10, 8, 14), (sx - shrink // 2, sy + 12, shrink, max(2, shrink // 3)))
        self.draw_sprite(surf, camera, angle=self.age * 25, lift=self.z)
        if (self.age // 2) % 2:
            fx, fy = sx + 2, round(sy - self.z) - 9          # pavio aceso
            surf.fill((255, 220, 120), (fx, fy, 2, 2))


# ── orbe ─────────────────────────────────────
_GLOW = {}


def _glow(color, r):
    key = (color, r)
    if key not in _GLOW:
        s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        for k in range(r, 0, -2):
            a = round(110 * (1 - k / r) ** 1.5)
            pygame.draw.circle(s, (*color, a), (r, r), k)
        _GLOW[key] = s
    return _GLOW[key]


class Orb(Projectile):
    ghost = True                             # atravessa paredes
    TURN = 0.06
    LIFE = 120

    def update(self, match):
        t = self.target
        if t is not None and getattr(t, "alive_in_match", False) and self.age > 6:
            speed = math.hypot(self.vx, self.vy)
            dx, dy = _unit(t.x - self.x, t.y - 6 - self.y)
            self.vx += (dx * speed - self.vx) * self.TURN
            self.vy += (dy * speed - self.vy) * self.TURN
            k = speed / (math.hypot(self.vx, self.vy) or 1)
            self.vx, self.vy = self.vx * k, self.vy * k
        super().update(match)
        if self.age % 2 == 0:
            match.particles.append(Particle(self.x + random.uniform(-3, 3), self.y + random.uniform(-3, 3),
                                            random.uniform(-0.3, 0.3), random.uniform(-0.6, -0.1),
                                            random.choice(((170, 120, 240), (220, 196, 255))), 18, 3))
        if self.age > self.LIFE:
            self.alive = False
            match.burst(self.x, self.y, (190, 150, 250), 6, speed=2)

    def draw(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        glow = _glow((170, 110, 240), 14)
        surf.blit(glow, glow.get_rect(center=(sx, sy)))
        r = 5 + (1 if (self.age // 5) % 2 else 0)
        pygame.draw.circle(surf, (20, 10, 30), (sx, sy), r + 1)
        pygame.draw.circle(surf, (152, 98, 216), (sx, sy), r)
        pygame.draw.circle(surf, (230, 210, 255), (sx - 1, sy - 1), max(1, r - 3))


# ── corrente ─────────────────────────────────
class ChainBall(Projectile):
    OUT = 22                                 # quadros indo (~220 px)
    RETURN_SPEED = 15
    STUN = 10

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.radius = 7
        self.returning = False
        self.owner.chain_ball = self

    def can_hit(self, fighter):
        return not self.returning

    def survives_hit(self):
        self.returning = True                # acertou: a corrente puxa a bola de volta
        return True

    def on_hit(self, target, match):
        target.knock = [k * 1.3 for k in target.knock]
        if target.stun(self.STUN):
            match.popup(target.x, target.y - 62, "TONTO", theme.BRASS)
        match.camera.shake(3)

    def on_wall(self, wall, match):
        if not self.returning:
            self.returning = True
            match.burst(self.x, self.y, (200, 204, 216), 5, speed=3)
            match.assets.play("click", 0.3)
        return True                          # volta atravessando (a corrente só recolhe)

    def update(self, match):
        self.age += 1
        owner = self.owner
        if not self.returning:
            self.x += self.vx
            self.y += self.vy
            if self.age >= self.OUT:
                self.returning = True
            return
        hx, hy = owner.x, owner.y - 8
        dx, dy = hx - self.x, hy - self.y
        d = math.hypot(dx, dy)
        if d < self.RETURN_SPEED + 4 or owner.hp <= 0:
            self.alive = False
            return
        self.vx, self.vy = dx / d * self.RETURN_SPEED, dy / d * self.RETURN_SPEED
        self.x += self.vx
        self.y += self.vy

    def draw(self, surf, camera):
        owner = self.owner
        ox, oy = owner.x + owner.facing[0] * 10 - camera.x, owner.y - 8 - camera.y
        sx, sy = self.x - camera.x, self.y - camera.y
        steps = max(1, int(math.hypot(sx - ox, sy - oy) // 6))
        for i in range(steps):
            t = i / steps
            px, py = ox + (sx - ox) * t, oy + (sy - oy) * t
            color = (120, 124, 138) if i % 2 else (176, 180, 192)
            surf.fill((20, 14, 22), (round(px) - 2, round(py) - 2, 4, 4))
            surf.fill(color, (round(px) - 1, round(py) - 1, 2, 2))
        cx, cy = round(sx), round(sy)
        for a in range(4):                   # cravos girando
            ang = a * math.pi / 2 + self.age * 0.3
            px, py = cx + math.cos(ang) * 8, cy + math.sin(ang) * 8
            surf.fill((20, 14, 22), (round(px) - 2, round(py) - 2, 4, 4))
            surf.fill((222, 226, 236), (round(px) - 1, round(py) - 1, 2, 2))
        pygame.draw.circle(surf, (20, 14, 22), (cx, cy), 7)
        pygame.draw.circle(surf, (98, 102, 120), (cx, cy), 6)
        pygame.draw.circle(surf, (160, 166, 182), (cx - 2, cy - 2), 2)


# ── pistola ──────────────────────────────────
class LeadBall(Projectile):
    muzzle = 22

    def on_launch(self, match):
        dx, dy = _unit(self.vx, self.vy)
        for _ in range(9):                   # nuvem de pólvora
            match.particles.append(Particle(self.x + random.uniform(-4, 4), self.y + random.uniform(-4, 4),
                                            dx * random.uniform(0.3, 1.6) + random.uniform(-0.5, 0.5),
                                            dy * random.uniform(0.3, 1.6) - random.uniform(0.1, 0.7),
                                            random.choice(((150, 146, 150), (190, 186, 186), (110, 106, 112))),
                                            random.randint(26, 44), 6, -0.01))
        match.burst(self.x, self.y, (255, 220, 140), 5, speed=3)
        match.camera.shake(2)

    def on_hit(self, target, match):
        target.knock = [k * 1.6 for k in target.knock]

    def draw(self, surf, camera):
        for i, (tx, ty) in enumerate(self.trail):
            surf.fill((120, 116, 124), (round(tx - camera.x) - 1, round(ty - camera.y) - 1, 2, 2))
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        pygame.draw.circle(surf, (20, 14, 22), (sx, sy), 5)
        pygame.draw.circle(surf, (96, 98, 112), (sx, sy), 4)
        surf.fill((200, 204, 216), (sx - 2, sy - 2, 2, 2))


# ── cristal ──────────────────────────────────
class IceShard(Projectile):
    sprite = "Cristal"
    SLOW = 45

    def update(self, match):
        super().update(match)
        if self.age % 3 == 0:
            match.particles.append(Particle(self.x, self.y, random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3),
                                            (210, 240, 255), 16, 3))

    def on_hit(self, target, match):
        was_slow = target.slow_timer > 0
        if target.slow(self.SLOW) and not was_slow:
            match.popup(target.x, target.y - 62, "LENTO", (150, 212, 240))

    def on_wall(self, wall, match):
        match.burst(self.x, self.y, (200, 236, 250), 9, speed=3)
        return False


# ─────────────────────────────────────────────
#  Armas raras (baú da campanha)
# ─────────────────────────────────────────────
class Bolt(Arrow):
    """Virote da besta: pesado, rápido e atravessa dois."""

    sprite = "Virote"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.charged = False
        self.pierce = getattr(self.owner, "pierce", 0) + 2

    @staticmethod
    def speed_for(weapon, power):
        return weapon.bullet_speed


class Flame(Projectile):
    """Lança-chamas: labareda curta que cresce, perde força e atravessa todo mundo."""

    LIFE = 24
    muzzle = 24

    @classmethod
    def launch(cls, match, owner, weapon, direction, damage, target=None, power=1.0, explosive=False):
        a = math.atan2(direction[1], direction[0]) + random.uniform(-0.14, 0.14)
        speed = weapon.bullet_speed * random.uniform(0.85, 1.15)
        dx, dy = math.cos(a), math.sin(a)
        x, y = owner.x + direction[0] * cls.muzzle, owner.y + direction[1] * cls.muzzle - 4
        return cls(owner, weapon, x, y, dx, dy, speed, damage, target, power)

    def survives_hit(self):
        return True                          # o fogo passa por todos (cada um leva dano uma vez)

    def update(self, match):
        super().update(match)
        self.vx *= 0.93
        self.vy *= 0.93
        self.radius = 4 + self.age // 3
        if self.age >= self.LIFE:
            self.alive = False
            if random.random() < 0.4:
                match.particles.append(Particle(self.x, self.y, random.uniform(-0.3, 0.3), -0.6,
                                                (90, 84, 90), 20, 5, -0.01))

    def on_wall(self, wall, match):
        match.particles.append(Particle(self.x, self.y, 0, -0.5, (90, 84, 90), 16, 5, -0.01))
        return False

    def draw(self, surf, camera):
        t = self.age / self.LIFE
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        r = max(2, self.radius)
        outer = (226, 80, 40) if t < 0.6 else (150, 70, 50)
        pygame.draw.circle(surf, outer, (sx, sy), r)
        if t < 0.7:
            pygame.draw.circle(surf, (252, 170, 60), (sx, sy), max(1, r - 3))
        if t < 0.35:
            pygame.draw.circle(surf, (255, 240, 180), (sx, sy), max(1, r - 6))


class Boomerang(Projectile):
    """Bumerangue: vai girando, volta para a mão e acerta na ida e na volta."""

    sprite = "Bumerangue"
    OUT = 26
    RETURN_SPEED = 12

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.returning = False

    def survives_hit(self):
        return True

    def _turn(self):
        if not self.returning:
            self.returning = True
            self.hit = set()                 # na volta pode acertar de novo

    def on_wall(self, wall, match):
        if not self.returning:
            match.burst(self.x, self.y, (200, 160, 110), 4, speed=2)
            self._turn()
        return True

    def update(self, match):
        self.age += 1
        if not self.returning:
            self.x += self.vx
            self.y += self.vy
            self.vx *= 0.985
            self.vy *= 0.985
            if self.age >= self.OUT:
                self._turn()
            return
        owner = self.owner
        dx, dy = owner.x - self.x, owner.y - 8 - self.y
        d = math.hypot(dx, dy)
        if d < self.RETURN_SPEED + 6 or owner.hp <= 0 or self.age > self.OUT * 4:
            self.alive = False
            return
        self.vx, self.vy = dx / d * self.RETURN_SPEED, dy / d * self.RETURN_SPEED
        self.x += self.vx
        self.y += self.vy

    def draw(self, surf, camera):
        self.draw_sprite(surf, camera, angle=self.age * 35)


class LightningArc(Entity):
    """Desenho do raio: linhas tortas que piscam e somem."""

    LIFE = 12

    def __init__(self, points):
        super().__init__(*points[0])
        self.points = points
        self.life = self.LIFE
        rng = random.Random(len(points) * 7919 + int(points[0][0]))
        self.paths = []
        for a, b in zip(points, points[1:]):
            steps = max(3, int(math.hypot(b[0] - a[0], b[1] - a[1]) // 22))
            path = [a]
            for k in range(1, steps):
                t = k / steps
                path.append((a[0] + (b[0] - a[0]) * t + rng.uniform(-9, 9),
                             a[1] + (b[1] - a[1]) * t + rng.uniform(-9, 9)))
            path.append(b)
            self.paths.append(path)

    def update(self, match):
        self.life -= 1
        if self.life <= 0:
            self.alive = False

    def draw(self, surf, camera):
        if self.life < 4 and self.life % 2:
            return
        for path in self.paths:
            pts = [(round(x - camera.x), round(y - camera.y)) for x, y in path]
            pygame.draw.lines(surf, (120, 100, 30), False, pts, 5)
            pygame.draw.lines(surf, (246, 214, 70), False, pts, 3)
            pygame.draw.lines(surf, (255, 252, 230), False, pts, 1)


class Lightning(Projectile):
    """Cajado do Raio: acerta na hora o alvo (se a parede não tapar) e pula para mais dois."""

    RANGE = 460
    JUMP = 170
    JUMPS = 2

    def can_hit(self, fighter):
        return False                         # o dano sai todo no primeiro quadro

    def update(self, match):
        owner = self.owner
        start = (owner.x + owner.facing[0] * 16, owner.y - 10)
        points = [start]
        target = self.target if getattr(self.target, "alive_in_match", False) else None
        if target is not None and (owner.distance_to(target) > self.RANGE
                                   or match.arena.blocks_segment((owner.x, owner.y), (target.x, target.y))):
            target = None
        if target is None:
            dx, dy = _unit(self.vx, self.vy) if (self.vx or self.vy) else owner.facing
            points.append((owner.x + dx * 200, owner.y + dy * 200))
            match.add_effect(LightningArc(points))
            self.alive = False
            return
        damage = self.damage
        hit = []
        while target is not None and len(hit) <= self.JUMPS:
            hit.append(target)
            points.append((target.x, target.y - 16))
            target.take_damage(damage, owner.x, owner.y, attacker=owner, match=match)
            match.burst(target.x, target.y - 16, (246, 214, 70), 6, speed=3)
            damage = max(1, round(damage * 0.7))
            prev = target
            near = [f for f in match.fighters if f.alive_in_match and f not in hit
                    and match.hostile(owner, f) and prev.distance_to(f) < self.JUMP]
            target = min(near, key=prev.distance_to) if near else None
        match.add_effect(LightningArc(points))
        match.camera.shake(3)
        self.alive = False

    def draw(self, surf, camera):
        pass


class CannonBall(LeadBall):
    """Canhão de mão: bala grande que explode onde bate e empurra todo mundo."""

    blast = 84

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.explosive = True
        self.radius = 7

    def on_launch(self, match):
        super().on_launch(match)
        match.camera.shake(5)
        self.owner.knock = [-self.vx * 0.5, -self.vy * 0.5]      # coice

    def draw(self, surf, camera):
        for i, (tx, ty) in enumerate(self.trail):
            surf.fill((140, 136, 140), (round(tx - camera.x) - 2, round(ty - camera.y) - 2, 4, 4))
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        pygame.draw.circle(surf, (20, 14, 22), (sx, sy), 8)
        pygame.draw.circle(surf, (64, 66, 80), (sx, sy), 7)
        surf.fill((170, 174, 190), (sx - 3, sy - 3, 3, 3))


# ── armas do Cauanzera, do Albeguinio e do Borba Jr ──
class FloppyDisk(ShurikenStar):
    """Disquete do Cauanzera: gira como shuriken e quica uma vez na parede."""
    sprite = "Disquete"


class Pendrive(Projectile):
    """Pendrive do Albeguinio: gira no ar e passa um vírus — o alvo pisca verde e perde vida aos
    poucos por 2s."""
    sprite = "Pendrive"
    VIRUS = 2 * 60
    VIRUS_DAMAGE = 1

    def update(self, match):
        super().update(match)
        if self.age % 3 == 0:
            match.particles.append(Particle(self.x, self.y, random.uniform(-0.4, 0.4), random.uniform(-0.4, 0.4),
                                            random.choice(((110, 240, 130), (190, 255, 200))), 12, 2))

    def on_hit(self, target, match):
        was = target.virus_timer > 0
        if target.infect(self.owner, max(1, round(self.VIRUS_DAMAGE * self.owner.damage_bonus)), self.VIRUS) and not was:
            match.popup(target.x, target.y - 62, "VÍRUS", (110, 240, 130))

    def on_wall(self, wall, match):
        match.burst(self.x, self.y, (110, 240, 130), 5, speed=2)
        return False

    def draw(self, surf, camera):
        self.draw_sprite(surf, camera, angle=self.age * 30)


class PulseShot(Projectile):
    """Canhão de Pulso do Borba Jr: bola de energia azul. Segurando, carrega: sai maior, mais forte
    e empurra muito."""
    muzzle = 20
    CORE, GLOW = (210, 240, 255), (90, 170, 255)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.radius = 5 + round(5 * self.power)

    @staticmethod
    def speed_for(weapon, power):
        return weapon.bullet_speed * (0.9 + 0.3 * power)

    def on_launch(self, match):
        match.burst(self.x, self.y, self.GLOW, 4 + round(8 * self.power), speed=3)
        if self.power >= 0.99:
            match.camera.shake(3)
            self.owner.knock = [-self.vx * 0.25, -self.vy * 0.25]          # coice do tiro carregado

    def on_hit(self, target, match):
        target.knock = [k * (1.2 + 1.3 * self.power) for k in target.knock]
        match.burst(target.x, target.y - 16, self.GLOW, 6 + round(8 * self.power), speed=4)

    def on_wall(self, wall, match):
        match.burst(self.x, self.y, self.GLOW, 6, speed=3)
        return False

    def update(self, match):
        super().update(match)
        if self.age % 2 == 0:
            match.particles.append(Particle(self.x, self.y, -self.vx * 0.05, -self.vy * 0.05, self.GLOW, 10,
                                            2 + round(2 * self.power)))

    def draw(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        r = self.radius
        glow = _glow(self.GLOW, r * 3)
        surf.blit(glow, glow.get_rect(center=(sx, sy)))
        pygame.draw.circle(surf, (20, 30, 60), (sx, sy), r + 1)
        pygame.draw.circle(surf, self.GLOW, (sx, sy), r)
        pygame.draw.circle(surf, self.CORE, (sx - 1, sy - 1), max(1, r - 3))


# ── habilidade do Cauanzera (Multiesportista) ──
class Basketball(Bullet):
    """Basquete: arremesso alto que passa por cima das paredes e cai em cima do alvo (não erra)."""

    lobbed = True
    DAMAGE = 15
    FLIGHT = 38
    PEAK = 130
    color = (236, 128, 50)

    @classmethod
    def throw(cls, owner, target, damage):
        ball = cls(owner, owner.x, owner.y - 10, 0, 0, 0, damage, cls.color)
        ball.target = target
        ball.age = 0
        ball.radius = 7
        ball.start = (owner.x, owner.y - 10)
        if target is None:
            fx, fy = owner.facing
            ball.end = (owner.x + fx * 300, owner.y + fy * 300)
        else:
            ball.end = (target.x, target.y)
        ball.z = 0.0
        return ball

    def can_hit(self, fighter):
        return False                          # no ar não bate em ninguém: cai na cabeça do alvo

    def update(self, match):
        self.age += 1
        t = self.target
        if t is not None and t.alive_in_match:
            self.end = (t.x, t.y)             # segue o alvo: cesta garantida
        k = min(1.0, self.age / self.FLIGHT)
        (x0, y0), (x1, y1) = self.start, self.end
        self.x, self.y = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
        self.z = 4 * self.PEAK * k * (1 - k)
        if k < 1:
            return
        self.alive = False
        match.burst(self.x, self.y, self.color, 10, speed=4)
        if t is not None and t.alive_in_match and t.distance_to(self) < t.radius + 30:
            if t.take_damage(self.damage, self.x, self.y - 30, attacker=self.owner, match=match):
                match.popup(t.x, t.y - 80, "CESTA!", (240, 150, 60))
                match.camera.shake(4)

    def draw(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        shrink = max(4, 14 - round(self.z / 12))
        pygame.draw.ellipse(surf, (10, 8, 14), (sx - shrink // 2, sy + 12, shrink, max(2, shrink // 3)))
        draw_sport_ball(surf, sx, round(sy - self.z), 7, "basquete", self.age)


class Volleyball(Bullet):
    """Vôlei: saque rápido que quica de um adversário para o outro. Sozinho contra um, a bola
    sai dele, bate na parede e volta nele."""

    DAMAGE = 8
    SPEED = 14
    HITS = 3
    LIFE = 160
    TURN = 0.28

    def __init__(self, owner, target, dx, dy, damage):
        super().__init__(owner, owner.x + dx * 18, owner.y + dy * 18 - 4, dx, dy, self.SPEED, damage, (250, 230, 120))
        self.radius = 7
        self.target = target
        self.hits_left = self.HITS
        self.seeking = target is not None
        self.age = 0

    def update(self, match):
        self.age += 1
        t = self.target
        if self.seeking and t is not None and t.alive_in_match:
            dx, dy = _unit(t.x - self.x, t.y - 6 - self.y)
            self.vx += (dx * self.SPEED - self.vx) * self.TURN
            self.vy += (dy * self.SPEED - self.vy) * self.TURN
            k = self.SPEED / (math.hypot(self.vx, self.vy) or 1)
            self.vx, self.vy = self.vx * k, self.vy * k
        self.trail.append((self.x, self.y))
        if len(self.trail) > 5:
            self.trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        w, h = match.arena.width, match.arena.height
        if not (10 < self.x < w - 10):                # borda da arena também é "parede"
            self.vx = -self.vx
            self.x = min(max(self.x, 11), w - 11)
            self._rebound()
        if not (10 < self.y < h - 10):
            self.vy = -self.vy
            self.y = min(max(self.y, 11), h - 11)
            self._rebound()
        if self.age > self.LIFE:
            self.alive = False

    def _rebound(self):
        if not self.seeking:
            self.seeking = True
            self.hit = set()                          # volta para quem já tinha levado

    def survives_hit(self):
        self.hits_left -= 1
        return self.hits_left > 0

    def on_hit(self, target, match):
        match.burst(self.x, self.y, (250, 230, 120), 8, speed=3)
        others = [f for f in match.opponents_of(self.owner) if f.alive_in_match and f not in self.hit]
        if others:
            self.target = min(others, key=lambda f: math.hypot(f.x - self.x, f.y - self.y))
            self.seeking = True
            return
        # ninguém mais: quica na parede mais perto e volta nele
        dx, dy = self._nearest_wall(match, target)
        self.vx, self.vy = dx * self.SPEED, dy * self.SPEED
        self.target = target
        self.seeking = False

    def _nearest_wall(self, match, target):
        """Direção (saindo do alvo, não por cima dele) da parede ou borda mais perto."""
        away = _unit(self.x - target.x, self.y - target.y)
        if away == (0.0, 0.0):
            away = _unit(-self.vx, -self.vy)
        arena = match.arena
        best = (1e9, away[0], away[1])
        for k in range(16):
            a = k * math.tau / 16
            dx, dy = math.cos(a), math.sin(a)
            if dx * away[0] + dy * away[1] < 0.1:
                continue
            dist = 1e9
            for step in range(2, 60):
                px, py = self.x + dx * step * 14, self.y + dy * step * 14
                if not (10 < px < arena.width - 10 and 10 < py < arena.height - 10) or \
                        any(w.rect.collidepoint(px, py) for w in arena.walls):
                    dist = step * 14
                    break
            if dist < best[0]:
                best = (dist, dx, dy)
        return best[1], best[2]

    def on_wall(self, wall, match):
        res = push_circle_out(self.x, self.y, self.radius + 1, wall.rect)
        if res is not None:
            self.x, self.y, nx, ny = res
            dot = self.vx * nx + self.vy * ny
            if dot < 0:
                self.vx -= 2 * dot * nx
                self.vy -= 2 * dot * ny
        match.burst(self.x, self.y, (250, 230, 120), 4, speed=2)
        self._rebound()
        return True

    def draw(self, surf, camera):
        for i, (tx, ty) in enumerate(self.trail):
            surf.fill((200, 180, 90), (round(tx - camera.x) - 1, round(ty - camera.y) - 1, 2 + i // 2, 2 + i // 2))
        draw_sport_ball(surf, round(self.x - camera.x), round(self.y - camera.y), 7, "volei", self.age)


def draw_sport_ball(surf, x, y, r, kind, age):
    """Bola de basquete (laranja com gomos pretos) ou de vôlei (branca com faixas azul e amarela)."""
    pygame.draw.circle(surf, (20, 14, 22), (x, y), r + 1)
    if kind == "basquete":
        pygame.draw.circle(surf, (236, 128, 50), (x, y), r)
        pygame.draw.line(surf, (40, 24, 20), (x - r, y), (x + r, y), 1)
        pygame.draw.line(surf, (40, 24, 20), (x, y - r), (x, y + r), 1)
        surf.fill((255, 190, 130), (x - r // 2, y - r // 2, 2, 2))
        return
    pygame.draw.circle(surf, (244, 242, 232), (x, y), r)
    a = age * 0.4
    for k, color in enumerate(((60, 110, 200), (240, 200, 60))):
        ang = a + k * math.pi / 1.5
        pygame.draw.line(surf, color, (round(x + math.cos(ang) * r), round(y + math.sin(ang) * r)),
                         (round(x - math.cos(ang + 0.6) * r), round(y - math.sin(ang + 0.6) * r)), 2)


PROJECTILES = {
    "flecha": Arrow,
    "bala": Tracer,
    "lanca": Spear,
    "shuriken": ShurikenStar,
    "estrela": ThrowingStar,
    "granada": Grenade,
    "orbe": Orb,
    "corrente": ChainBall,
    "pistola": LeadBall,
    "cristal": IceShard,
    "virote": Bolt,
    "disquete": FloppyDisk,
    "pendrive": Pendrive,
    "pulso": PulseShot,
    "chama": Flame,
    "bumerangue": Boomerang,
    "raio": Lightning,
    "canhao": CannonBall,
}


def projectile_class(style):
    return PROJECTILES.get(style, Projectile)
