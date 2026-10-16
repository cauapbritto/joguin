"""Classe base das entidades e os objetos mais simples do mundo."""
import math
import random
from abc import ABC, abstractmethod

import pygame

from . import config, theme


class Entity(ABC):
    """Tudo que existe na arena: tem posição, atualiza a cada quadro e se desenha."""

    radius = 0

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.alive = True

    def distance_to(self, other):
        return math.hypot(self.x - other.x, self.y - other.y)

    def direction_to(self, other):
        dx, dy = other.x - self.x, other.y - self.y
        d = math.hypot(dx, dy)
        return (dx / d, dy / d) if d else (0.0, 0.0)

    @abstractmethod
    def update(self, match):
        """Avança um quadro de simulação."""

    @abstractmethod
    def draw(self, surf, camera):
        """Desenha no espaço do mundo (já deslocado pela câmera)."""


def hostile(a, b):
    """a e b são inimigos? Sem time (duelo), todo mundo é inimigo de todo mundo."""
    if a is None or b is None:
        return a is not b
    return a is not b and (a.team is None or a.team != b.team)


def push_circle_out(x, y, r, rect):
    """Se o círculo invade o retângulo, devolve a posição empurrada para fora e a normal."""
    nx = min(max(x, rect.left), rect.right)
    ny = min(max(y, rect.top), rect.bottom)
    dx, dy = x - nx, y - ny
    d2 = dx * dx + dy * dy
    if d2 >= r * r:
        return None
    if d2 > 1e-9:
        d = math.sqrt(d2)
        return x + dx / d * (r - d), y + dy / d * (r - d), dx / d, dy / d
    # centro dentro do retângulo: sai pelo lado mais próximo
    gaps = (
        (x - rect.left, rect.left - r, y, -1, 0),
        (rect.right - x, rect.right + r, y, 1, 0),
        (y - rect.top, x, rect.top - r, 0, -1),
        (rect.bottom - y, x, rect.bottom + r, 0, 1),
    )
    gap = min(gaps, key=lambda g: g[0])
    if gap[3]:
        return gap[1], y, gap[3], 0
    return x, gap[2], 0, gap[4]


class Wall(Entity):
    def __init__(self, x, y, w, h, visible=True):
        super().__init__(x, y)
        self.rect = pygame.Rect(x, y, w, h)
        self.visible = visible
        self.image = None          # textura definida pela arena
        self._drawn = None         # parede desenhada no código, guardada pronta (com a sombra embaixo)

    def update(self, match):
        pass

    @property
    def area(self):
        """Retângulo que o desenho ocupa (sombra e enfeites passam um pouco da base)."""
        if self.image is not None:
            return self.rect
        below = getattr(self.style, "below", 6)
        return pygame.Rect(self.rect.x, self.rect.y, self.rect.w, self.rect.h + below)

    def prepare(self):
        """Desenha a parede uma vez só (tijolos e folhas custam centenas de retângulos)."""
        if self._drawn is not None or self.image is not None or not self.visible:
            return
        if hasattr(self.style, "render"):
            self._drawn = self.style.render(self.rect.w, self.rect.h, (self.rect.x, self.rect.y))
        else:
            self._drawn = pygame.Surface((self.rect.w, self.rect.h + 6), pygame.SRCALPHA)
            self.style.draw(self._drawn, pygame.Rect(0, 0, self.rect.w, self.rect.h))

    def draw(self, surf, camera):
        if not self.visible:
            return
        r = self.rect.move(-camera.x, -camera.y)
        if self.image is not None:
            surf.blit(self.image, r)
            return
        if self._drawn is None:
            self.prepare()
        surf.blit(self._drawn, r)

    def overlaps_circle(self, x, y, radius):
        return push_circle_out(x, y, radius, self.rect) is not None


class WallStyle:
    """Parede desenhada no código, nas cores do mapa (quando não há textura)."""

    def __init__(self, fill, edge, shadow):
        self.fill, self.edge, self.shadow = fill, edge, shadow

    def draw(self, surf, r):
        surf.fill(self.shadow, r.move(0, 6))
        surf.fill(self.edge, r)
        surf.fill(self.fill, r.inflate(-4, -4))
        top = tuple(min(255, c + 36) for c in self.edge)
        surf.fill(top, (r.x + 2, r.y + 2, r.w - 4, 2))
        # fiadas de pedra
        for row, ly in enumerate(range(r.y + 12, r.bottom - 4, 12)):
            surf.fill(self.shadow, (r.x + 3, ly, r.w - 6, 1))
            off = 10 if row % 2 else 0
            for lx in range(r.x + 8 + off, r.right - 4, 22):
                surf.fill(self.shadow, (lx, ly - 11, 1, 11))


class Bullet(Entity):
    ghost = False         # atravessa paredes (orbe do Fantasma)
    lobbed = False        # vai pelo alto: passa por cima de paredes, barreiras e lutadores (granada)

    def __init__(self, owner, x, y, dx, dy, speed, damage, color, explosive=False):
        super().__init__(x, y)
        self.owner = owner
        self.vx, self.vy = dx * speed, dy * speed
        self.damage = damage
        self.color = color
        self.explosive = explosive
        self.radius = 5 if explosive else 4
        self.trail = []
        self.pierce = getattr(owner, "pierce", 0)     # quantos inimigos ainda atravessa
        self.hit = set()                              # quem já foi atingido por este tiro

    def update(self, match):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 4:
            self.trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        if not (0 < self.x < match.arena.width and 0 < self.y < match.arena.height):
            self.alive = False

    def on_hit(self, target, match):
        """Efeito extra ao acertar alguém (o dano já foi aplicado)."""

    def can_hit(self, fighter):
        """Pode acertar este lutador agora? (a granada só no chão, a corrente só na ida)"""
        return True

    def survives_hit(self):
        """Depois de acertar alguém: continua voando? Por padrão só se ainda atravessa."""
        if self.pierce > 0 and not self.explosive:
            self.pierce -= 1
            return True
        return False

    def on_wall(self, wall, match):
        """Bateu numa parede: devolve True se continua (ricochete, corrente voltando...)."""
        return False

    @property
    def rect(self):
        r = self.radius
        return pygame.Rect(self.x - r, self.y - r, r * 2, r * 2)

    def draw(self, surf, camera):
        for i, (tx, ty) in enumerate(self.trail):
            size = 1 + i
            surf.fill(_dim(self.color, 0.45), (tx - camera.x - size // 2, ty - camera.y - size // 2, size, size))
        sx, sy = int(self.x - camera.x), int(self.y - camera.y)
        strong = self.damage >= config.MAX_BULLET_DAMAGE * 0.6
        core = (255, 236, 160) if strong else (250, 246, 236)
        pygame.draw.circle(surf, (20, 14, 22), (sx, sy), self.radius + 1)
        pygame.draw.circle(surf, self.color if not self.explosive else (232, 108, 52), (sx, sy), self.radius)
        pygame.draw.circle(surf, core, (sx - 1, sy - 1), max(1, self.radius - 2))


class Hook(Bullet):
    """Gancho do Pirata: voa reto preso a uma corrente e puxa quem acertar."""

    SPEED = 15
    RANGE_FRAMES = 30            # ~450 px
    DAMAGE = 8

    def __init__(self, owner, x, y, dx, dy):
        super().__init__(owner, x, y, dx, dy, self.SPEED, self.DAMAGE, (176, 180, 192))
        self.radius = 6
        self.life = self.RANGE_FRAMES
        self.dir = (dx, dy)

    def update(self, match):
        super().update(match)
        self.life -= 1
        if self.life <= 0:
            self.alive = False

    def on_hit(self, target, match):
        owner = self.owner
        dx, dy = owner.x - target.x, owner.y - target.y
        d = math.hypot(dx, dy)
        if d > 60:
            # para logo na frente do pirata, no alcance do sabre
            target.pull(owner.x - dx / d * 48, owner.y - dy / d * 48, frames=10)
        target.stun(26)
        match.popup(target.x, target.y - 62, "PUXOU", theme.BRASS)
        match.assets.play("dash", 0.4)

    def draw(self, surf, camera):
        ox, oy = self.owner.x - camera.x, self.owner.y - 10 - camera.y
        sx, sy = self.x - camera.x, self.y - camera.y
        # corrente: elos alternados entre o pirata e o gancho
        steps = max(1, int(math.hypot(sx - ox, sy - oy) // 6))
        for i in range(steps):
            t = i / steps
            px, py = ox + (sx - ox) * t, oy + (sy - oy) * t
            color = (120, 124, 138) if i % 2 else (176, 180, 192)
            surf.fill((20, 14, 22), (round(px) - 2, round(py) - 2, 4, 4))
            surf.fill(color, (round(px) - 1, round(py) - 1, 2, 2))
        dx, dy = self.dir
        tip = (round(sx), round(sy))
        back = (round(sx - dx * 7 - dy * 5), round(sy - dy * 7 + dx * 5))
        pygame.draw.line(surf, (20, 14, 22), tip, back, 5)
        pygame.draw.line(surf, (214, 218, 228), tip, back, 3)
        pygame.draw.circle(surf, (20, 14, 22), tip, 4)
        pygame.draw.circle(surf, (214, 218, 228), tip, 3)


class Hack(Entity):
    """Hacker do Albeguinio: abre o notebook e digita (parado). Se apanhar ou ficar tonto enquanto
    digita, o hack falha. Terminando, o sinal de Wi-Fi sai dele e todos os adversários em jogo
    ficam HACKEADOS (travados)."""

    WAVE = 34                       # quadros da onda de Wi-Fi se espalhando
    GREEN = (110, 240, 130)

    def __init__(self, owner, typing, freeze):
        super().__init__(owner.x, owner.y)
        self.owner = owner
        self.typing = typing
        self.freeze = freeze
        self.age = 0
        self.hp = owner.hp
        self.state = "typing"
        owner.type_timer = typing
        owner.steer(0, 0)
        owner.vx = owner.vy = 0.0

    def update(self, match):
        owner = self.owner
        self.age += 1
        if self.state == "typing":
            self.x, self.y = owner.x, owner.y
            if owner.hp < self.hp or owner.stunned or not owner.alive_in_match:
                owner.type_timer = 0
                self.alive = False
                match.popup(owner.x, owner.y - 80, "HACK FALHOU", (230, 110, 90))
                match.burst(owner.x, owner.y - 30, (230, 110, 90), 8, speed=3)
                match.assets.play("cancel", 0.4)
                return
            if self.age % 6 == 0:
                match.assets.play("click", 0.15)          # teclas
            if self.age >= self.typing:
                owner.type_timer = 0
                self.state = "wave"
                self.age = 0
                hit = 0
                for f in match.opponents_of(owner):
                    if f.alive_in_match and f.hack(self.freeze):
                        hit += 1
                        match.popup(f.x, f.y - 80, "HACKEADO", self.GREEN)
                        match.burst(f.x, f.y - 30, self.GREEN, 10, speed=3, size=3)
                if hit:
                    match.camera.shake(4)
                match.assets.play("barrier", 0.5)
            return
        if self.age >= self.WAVE:
            self.alive = False

    def draw(self, surf, camera):
        if self.state != "wave":
            return
        t = self.age / self.WAVE
        cx, cy = round(self.x - camera.x), round(self.y - 40 - camera.y)
        alpha = round(220 * (1 - t))
        reach = 80 + 900 * t
        for k in range(3):                              # arcos de Wi-Fi se abrindo em todas as direções
            r = round(reach - k * 60)
            if r <= 10:
                continue
            ring = pygame.Surface((r * 2 + 6, r * 2 + 6), pygame.SRCALPHA)
            pygame.draw.circle(ring, (*self.GREEN, max(0, alpha - k * 50)), (r + 3, r + 3), r, 3)
            surf.blit(ring, (cx - r - 3, cy - r - 3))
        if t < 0.5:                                     # simbolo de Wi-Fi em cima dele
            for k, rr in enumerate((6, 12, 18)):
                rect = pygame.Rect(0, 0, rr * 2, rr * 2)
                rect.center = (cx, cy - 20 + rr)
                pygame.draw.arc(surf, self.GREEN, rect, math.radians(45), math.radians(135), 3)
            surf.fill(self.GREEN, (cx - 2, cy - 2 + 18, 4, 4))


class BetSlip(Entity):
    """Aposta do Aryel: três símbolos giram num bilhete em cima da cabeça dele e vão parando um
    por um; no fim aparece o resultado (GREEN, meio green ou RED) e a habilidade paga."""

    SYMBOLS = ("bola", "moeda", "trevo")
    HOLD = 18                       # o resultado fica um pouco na tela depois de parar

    def __init__(self, owner, outcome, spin, ability):
        super().__init__(owner.x, owner.y)
        self.owner = owner
        self.outcome = outcome
        self.spin = spin
        self.ability = ability
        self.age = 0
        rng = random.Random()
        win = rng.randrange(3)
        if outcome == "green":
            self.final = (win, win, win)
        elif outcome == "meio":
            other = (win + rng.randrange(1, 3)) % 3
            final = [win, win, other]
            rng.shuffle(final)
            self.final = tuple(final)
        else:
            self.final = (0, 1, 2) if rng.random() < 0.5 else (2, 0, 1)
        self.paid = False

    def update(self, match):
        self.age += 1
        self.x, self.y = self.owner.x, self.owner.y
        stop = [self.spin * k // 3 for k in (1, 2, 3)]
        if self.age in stop:
            match.assets.play("click", 0.3)
        if self.age >= self.spin and not self.paid:
            self.paid = True
            if self.owner.alive_in_match:
                self.ability.payout(self.owner, match, self.outcome)
        if self.age >= self.spin + self.HOLD:
            self.alive = False

    def _symbol(self, surf, kind, cx, cy):
        if kind == 0:                                   # bola de futebol
            pygame.draw.circle(surf, (20, 14, 22), (cx, cy), 5)
            pygame.draw.circle(surf, (240, 238, 230), (cx, cy), 4)
            surf.fill((40, 38, 48), (cx - 1, cy - 1, 2, 2))
        elif kind == 1:                                 # moeda
            pygame.draw.circle(surf, (90, 60, 10), (cx, cy), 5)
            pygame.draw.circle(surf, (240, 196, 60), (cx, cy), 4)
            surf.fill((255, 240, 160), (cx - 1, cy - 2, 1, 4))
        else:                                           # trevo
            for dx, dy in ((-2, -2), (2, -2), (-2, 2), (2, 2)):
                pygame.draw.circle(surf, (60, 170, 80), (cx + dx, cy + dy), 2)
            surf.fill((30, 110, 50), (cx, cy + 2, 1, 4))

    def draw(self, surf, camera):
        pass

    def draw_over(self, surf, camera):
        """Desenhado por cima dos lutadores (o bilhete fica sobre a cabeça)."""
        owner = self.owner
        cx = round(owner.x - camera.x)
        cy = round(owner.y - 92 - owner.lift - camera.y)
        box = pygame.Rect(0, 0, 46, 18)
        box.center = (cx, cy)
        color = {"green": (110, 230, 110), "meio": (230, 220, 110), "red": (230, 80, 70)}[self.outcome]
        done = self.age >= self.spin
        pygame.draw.rect(surf, (20, 14, 22), box.inflate(4, 4))
        surf.fill((246, 240, 222), box)
        if done and (self.age // 3) % 2 == 0:
            pygame.draw.rect(surf, color, box.inflate(4, 4), 2)
        stops = [self.spin * k // 3 for k in (1, 2, 3)]
        for i in range(3):
            sx = box.x + 8 + i * 15
            kind = self.final[i] if self.age >= stops[i] else (self.age // 3 + i) % 3
            self._symbol(surf, kind, sx, box.centery)
            if i < 2:
                surf.fill((200, 190, 170), (sx + 7, box.y + 2, 1, box.h - 4))


class ExoSuit(Entity):
    """Exoesqueleto do Borba Jr: placas de metal voam e se encaixam nele com faíscas e vapor;
    enquanto dura, solta vapor de vez em quando; no fim, as placas se soltam."""

    ASSEMBLE = 16
    METAL = ((150, 160, 178), (200, 208, 222), (96, 104, 122))

    def __init__(self, owner, frames):
        super().__init__(owner.x, owner.y)
        self.owner = owner
        self.frames = frames
        self.age = 0
        rng = random.Random(id(owner) + frames)
        self.plates = [(rng.uniform(0, math.tau), rng.uniform(70, 110), rng.choice(self.METAL)) for _ in range(7)]

    def update(self, match):
        owner = self.owner
        self.age += 1
        self.x, self.y = owner.x, owner.y
        if self.age == self.ASSEMBLE:
            match.burst(owner.x, owner.y - 24, (255, 220, 120), 14, speed=5, size=3)     # faíscas
            match.burst(owner.x, owner.y - 24, (120, 190, 255), 8, speed=3, size=3)
            match.camera.shake(4)
            match.assets.play("barrier", 0.45)
        if self.age % 24 == 0 and owner.exo_timer > 0:                                  # vapor
            for side in (-1, 1):
                match.particles.append(Particle(owner.x + side * 16, owner.y - 34, side * 0.6, -0.9,
                                                (220, 224, 230), 26, 5, -0.01))
        if self.age % 9 == 0 and owner.exo_timer > 0 and random.random() < 0.5:
            match.particles.append(Particle(owner.x + random.uniform(-14, 14), owner.y - random.uniform(10, 40),
                                            random.uniform(-1, 1), random.uniform(-1.5, -0.5),
                                            (255, 220, 120), 10, 2, 0.1))
        if owner.exo_timer <= 0 or self.age >= self.frames or not owner.alive_in_match:
            self.alive = False
            match.burst(owner.x, owner.y - 24, (200, 208, 222), 10, speed=4, gravity=0.2, size=4)
            for side in (-1, 1):
                match.particles.append(Particle(owner.x + side * 12, owner.y - 30, side * 1.2, -1.2,
                                                (220, 224, 230), 30, 6, -0.01))

    def draw(self, surf, camera):
        if self.age >= self.ASSEMBLE:
            return
        t = self.age / self.ASSEMBLE
        ox, oy = self.owner.x - camera.x, self.owner.y - 26 - camera.y
        for a, dist, color in self.plates:              # placas voando até o corpo
            d = dist * (1 - t) ** 2
            px, py = round(ox + math.cos(a) * d), round(oy + math.sin(a) * d * 0.8)
            surf.fill((20, 14, 22), (px - 5, py - 4, 10, 8))
            surf.fill(color, (px - 4, py - 3, 8, 6))
            surf.fill((236, 240, 248), (px - 4, py - 3, 8, 1))


class FrostNova(Entity):
    """Nevasca da Geada: onda de gelo que machuca e deixa lento quem estiver perto."""

    LIFE = 24

    def __init__(self, owner, x, y, radius=180, damage=10, slow_frames=int(2.5 * config.FPS)):
        super().__init__(x, y)
        self.owner = owner
        self.radius = radius
        self.damage = damage
        self.slow_frames = slow_frames
        self.age = 0
        self.applied = False

    def update(self, match):
        if not self.applied:
            self.applied = True
            for f in match.opponents_of(self.owner):
                if not f.alive_in_match or math.hypot(f.x - self.x, f.y - self.y) > self.radius + f.radius:
                    continue
                if self.damage and not f.take_damage(self.damage, self.x, self.y, attacker=self.owner,
                                                     match=match):
                    continue
                f.slow(self.slow_frames)
                match.popup(f.x, f.y - 62, "LENTO", (150, 212, 240))
            match.burst(self.x, self.y - 6, (200, 236, 250), 26, speed=6)
            match.camera.shake(4)
        self.age += 1
        if self.age >= self.LIFE:
            self.alive = False

    def draw(self, surf, camera):
        t = self.age / self.LIFE
        r = int(self.radius * (0.3 + 0.7 * t))
        cx, cy = round(self.x - camera.x), round(self.y - camera.y)
        ring = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
        alpha = int(170 * (1 - t))
        pygame.draw.circle(ring, (150, 212, 240, alpha // 3), (r + 4, r + 4), r)
        pygame.draw.circle(ring, (220, 244, 255, alpha), (r + 4, r + 4), r, 4)
        for k in range(10):                      # cristais na borda
            a = k * math.tau / 10 + t
            px, py = r + 4 + math.cos(a) * r, r + 4 + math.sin(a) * r * 0.9
            ring.fill((240, 250, 255, alpha), (round(px) - 2, round(py) - 2, 4, 4))
        surf.blit(ring, (cx - r - 4, cy - r - 4))


class Explosion(Entity):
    DURATION = 22

    def __init__(self, owner, x, y, damage, radius=config.EXPLOSION_RADIUS):
        super().__init__(x, y)
        self.owner = owner
        self.damage = damage
        self.radius = radius
        self.timer = self.DURATION
        self.applied = False

    def update(self, match):
        if not self.applied:
            self.applied = True
            for fighter in match.fighters:
                if hostile(self.owner, fighter) and fighter.alive_in_match and self.distance_to(fighter) < self.radius + fighter.radius:
                    fighter.take_damage(self.damage, self.x, self.y, attacker=self.owner, match=match)
        self.timer -= 1
        if self.timer <= 0:
            self.alive = False

    def draw(self, surf, camera):
        t = 1 - self.timer / self.DURATION
        sx, sy = int(self.x - camera.x), int(self.y - camera.y)
        r = int(10 + self.radius * min(1, t * 1.6))
        if t < 0.25:
            pygame.draw.circle(surf, (255, 244, 214), (sx, sy), r)
            return
        ring = max(2, int(10 * (1 - t)))
        pygame.draw.circle(surf, (232, 108, 52), (sx, sy), r, ring)
        inner = int(r * (1 - t))
        if inner > 2:
            pygame.draw.circle(surf, (255, 196, 92), (sx, sy), inner)


class GroundMark(Entity):
    """Círculo de aviso no chão: algo vai cair (ou pousar) aqui daqui a pouco."""

    def __init__(self, x, y, radius, frames, color=(220, 70, 90)):
        super().__init__(x, y)
        self.radius = radius
        self.frames = self.left = frames
        self.color = color

    @property
    def progress(self):
        return 1 - self.left / self.frames

    def update(self, match):
        self.left -= 1
        if self.left <= 0:
            self.alive = False

    def draw(self, surf, camera):
        t = self.progress
        r = max(4, round(self.radius * (0.35 + 0.65 * t)))
        cx, cy = round(self.x - camera.x), round(self.y + 14 - camera.y)
        layer = pygame.Surface((r * 2 + 6, r + 6), pygame.SRCALPHA)
        rect = pygame.Rect(3, 3, r * 2, r)
        pygame.draw.ellipse(layer, (*self.color, round(40 + 60 * t)), rect)
        pygame.draw.ellipse(layer, (*self.color, 220), rect, 2)
        full = pygame.Rect(0, 0, self.radius * 2, self.radius)
        full.center = (cx, cy)
        surf.blit(layer, (cx - r - 3, cy - r // 2 - 3))
        pygame.draw.ellipse(surf, _dim(self.color, 0.8), full, 1)


class ShadowBomb(GroundMark):
    """Bomba sombria (Aryel Corrompido): marca o chão, cai do céu e explode."""

    def __init__(self, owner, x, y, delay=60, damage=20, radius=54, coin=False):
        super().__init__(x, y, radius, delay, (240, 196, 60) if coin else (190, 80, 230))
        self.owner = owner
        self.damage = damage
        self.coin = coin                # moeda da aposta (Aryel) em vez de bomba sombria

    def update(self, match):
        super().update(match)
        if not self.alive:
            match.add_effect(Explosion(self.owner, self.x, self.y, self.damage, self.radius))
            match.burst(self.x, self.y, (255, 216, 90) if self.coin else (190, 120, 255), 10, speed=5)
            match.assets.play("explosion", 0.35)
            match.camera.shake(4)

    def draw(self, surf, camera):
        super().draw(surf, camera)
        t = self.progress
        if t > 0.55:
            fall = (1 - (t - 0.55) / 0.45) ** 2
            bx, by = round(self.x - camera.x), round(self.y + 6 - camera.y - fall * 240)
            if self.coin:                                  # moeda de ouro girando
                w = max(2, round(8 * abs(math.cos(self.left * 0.4))))
                pygame.draw.ellipse(surf, (90, 60, 10), (bx - w - 1, by - 9, w * 2 + 2, 18))
                pygame.draw.ellipse(surf, (240, 196, 60), (bx - w, by - 8, w * 2, 16))
                if w > 3:
                    surf.fill((255, 240, 160), (bx - 1, by - 5, 2, 8))
                return
            for k in range(1, 4):
                surf.fill((120, 60, 170), (bx - 1, by - k * 8, 3, 4))
            pygame.draw.circle(surf, (20, 10, 28), (bx, by), 8)
            pygame.draw.circle(surf, (110, 50, 160), (bx, by), 6)
            surf.fill((230, 200, 255), (bx - 3, by - 3, 2, 2))


class Barrier(Entity):
    """Muralha do Tanque: bloqueia os tiros do adversário por alguns segundos."""

    def __init__(self, owner, x, y, dx, dy, duration):
        super().__init__(x, y)
        self.owner = owner
        w, h = (16, 64) if abs(dx) > abs(dy) else (64, 16)
        self.rect = pygame.Rect(0, 0, w, h)
        self.rect.center = (round(x), round(y))
        self.timer = self.duration = duration

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
        step = 6
        if r.w > r.h:
            for x in range(r.x + 4, r.right - 2, step):
                surf.fill((70, 140, 170), (x, r.y + 4, 2, r.h - 8))
        else:
            for y in range(r.y + 4, r.bottom - 2, step):
                surf.fill((70, 140, 170), (r.x + 4, y, r.w - 8, 2))


_ICONS = {
    # 8x9 em pixels; cada letra é uma cor
    "vida": (["...cc...", "...cc...", "..gggg..", "...rr...", "..rrrr..",
              ".rrwrrr.", ".rrrrrr.", ".rrrrrr.", "..rrrr.."],
             {"c": (130, 86, 50), "g": (170, 176, 190), "r": (214, 64, 64), "w": (255, 220, 220)}),
    "furia": (["...o....", "...oo...", "..oyo...", "..oyyo..", ".ooyyoo.",
               ".oyyyyo.", ".oyywyo.", "..oyyo..", "...oo..."],
              {"o": (234, 104, 44), "y": (252, 200, 72), "w": (255, 250, 220)}),
    "energia": (["....bb..", "...bb...", "..bbb...", ".bbbbbb.", "...bbw..",
                 "...bb...", "..bb....", "..b.....", "........"],
                {"b": (110, 180, 246), "w": (230, 246, 255)}),
    "municao": (["..t...t.", ".ttt.ttt", ".ccc.ccc", ".cwc.cwc", ".ccc.ccc",
                 ".ccc.ccc", ".ccc.ccc", ".ddd.ddd", "........"],
                {"t": (200, 204, 216), "c": (226, 176, 74), "w": (255, 236, 170), "d": (166, 120, 40)}),
}


def _icon(kind, scale=4):
    rows, colors = _ICONS[kind]
    surf = pygame.Surface((len(rows[0]), len(rows)), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in colors:
                surf.set_at((x, y), colors[ch])
    mask = pygame.mask.from_surface(surf)
    line = mask.to_surface(setcolor=(20, 14, 24, 255), unsetcolor=(0, 0, 0, 0))
    out = pygame.Surface((surf.get_width() + 2, surf.get_height() + 2), pygame.SRCALPHA)
    for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2)):
        out.blit(line, (dx, dy))
    out.blit(surf, (1, 1))
    return pygame.transform.scale(out, (out.get_width() * scale, out.get_height() * scale))


class Pickup(Entity):
    """Item que aparece na arena: vida, fúria (mais dano), energia (habilidade pronta) ou
    munição (enche o pente na hora e ainda sobra um pente extra)."""

    KINDS = {
        "vida": ("+VIDA", (214, 64, 64)),
        "furia": ("FÚRIA", (234, 104, 44)),
        "energia": ("HABILIDADE PRONTA", (110, 180, 246)),
        "municao": ("+MUNIÇÃO", (226, 176, 74)),
    }
    _images = {}

    def __init__(self, kind, x, y):
        super().__init__(x, y)
        self.kind = kind
        self.radius = 12
        self.timer = config.PICKUP_LIFETIME
        self.age = 0

    def update(self, match):
        self.age += 1
        self.timer -= 1
        if self.timer <= 0:
            self.alive = False

    def apply(self, fighter, match):
        label, color = self.KINDS[self.kind]
        if self.kind == "vida":
            heal = min(config.HEAL_AMOUNT, fighter.max_hp - fighter.hp)
            fighter.hp += heal
            label = f"+{heal}"
        elif self.kind == "furia":
            fighter.fury_timer = config.FURY_FRAMES
        elif self.kind == "municao":
            fighter.refill_ammo(config.AMMO_PICKUP_EXTRA)
        else:
            fighter.ability_cd = 0
        match.popup(fighter.x, fighter.y - 74, label, color)
        match.burst(self.x, self.y - 10, color, 16, speed=4)
        match.assets.play("select", 0.5)
        self.alive = False

    def draw(self, surf, camera):
        if self.timer < 2 * config.FPS and (self.timer // 6) % 2:
            return
        if self.kind not in self._images:
            Pickup._images[self.kind] = _icon(self.kind)
        img = self._images[self.kind]
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        bob = round(math.sin(self.age * 0.08) * 3)
        color = self.KINDS[self.kind][1]
        pulse = 20 + round(math.sin(self.age * 0.12) * 4)
        beam = _beam(color)
        surf.blit(beam, beam.get_rect(midbottom=(sx, sy + 10)))
        pygame.draw.ellipse(surf, _dim(color, 0.45), (sx - pulse, sy + 6, pulse * 2, 10), 2)
        pygame.draw.ellipse(surf, (10, 8, 14), (sx - 13, sy + 8, 26, 7))
        surf.blit(img, img.get_rect(midbottom=(sx, sy + 8 + bob)))


class FloatingText:
    """Número de dano que sobe e some (desenhado por cima, na tela)."""

    def __init__(self, x, y, text, color):
        self.x, self.y = x, y
        self.text = text
        self.color = color
        self.life = 40

    def update(self):
        self.y -= 0.6
        self.life -= 1
        return self.life > 0


class Particle:
    def __init__(self, x, y, vx, vy, color, life, size=3, gravity=0.0):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.color = color
        self.life = self.max_life = life
        self.size = size
        self.gravity = gravity

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vx *= 0.95
        self.vy = self.vy * 0.95 + self.gravity
        self.life -= 1
        return self.life > 0

    def draw(self, surf, camera):
        s = max(1, round(self.size * self.life / self.max_life))
        surf.fill(self.color, (self.x - camera.x - s // 2, self.y - camera.y - s // 2, s, s))


_BEAMS = {}


def _beam(color):
    """Facho de luz vertical sobre o item, para ele ser visto de longe."""
    if color not in _BEAMS:
        w, h = 26, 90
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            a = int(70 * (y / h) ** 2)
            s.fill((*color[:3], a), (4, y, w - 8, 1))
            s.fill((*color[:3], a // 2), (0, y, 4, 1))
            s.fill((*color[:3], a // 2), (w - 4, y, 4, 1))
        _BEAMS[color] = s
    return _BEAMS[color]


def _dim(color, t):
    return tuple(int(c * t) for c in color[:3])
