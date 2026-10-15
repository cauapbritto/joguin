"""Coisas do caminho entre as masmorras da campanha: entradas com grade, fogueira do
acampamento, o baú escondido (com as armas raras) e a porta de volta ao acampamento."""
import math
import random

import pygame

from . import theme, weapon_art
from .entities import Entity, Particle, Wall

GATE_LIFT = 26               # quadros da grade subindo (ou descendo)


def _glow(radius, color, strength=1.0):
    surf = pygame.Surface((radius * 2, radius * 2))
    for r in range(radius, 0, -2):
        k = (1 - r / radius) ** 1.6 * strength
        pygame.draw.circle(surf, tuple(min(255, int(c * k)) for c in color), (radius, radius), r)
    return surf


_GLOWS = {}


def glow(radius, color, strength=1.0):
    key = (radius, color, strength)
    if key not in _GLOWS:
        _GLOWS[key] = _glow(radius, color, strength)
    return _GLOWS[key]


# ─────────────────────────────────────────────
#  Entrada de masmorra (acampamento)
# ─────────────────────────────────────────────
class Gate(Entity):
    """Entrada de uma masmorra na parede do acampamento.

    Estados: "open" (dá para entrar, brilha por dentro), "locked" (grade fechada) e
    "done" (grade fechada com um OK: essa masmorra já foi). A grade sobe e desce animada;
    fechada, ela vira parede (ninguém passa)."""

    flat = True                  # desenhada junto do chão, por cima das paredes

    def __init__(self, number, rect, state="locked"):
        r = pygame.Rect(rect)
        super().__init__(r.centerx, r.centery)
        self.number = number
        self.rect = r
        self.state = state
        self.bars = 0.0 if state == "open" else 1.0      # 1 = grade toda abaixada
        self.wall = Wall(r.x, r.y, r.w, r.h, visible=False)
        self.age = 0

    @property
    def closed(self):
        return self.state != "open"

    @property
    def entrance(self):
        """Ponto logo na frente da entrada (onde o grupo se junta para entrar)."""
        return self.rect.centerx, self.rect.bottom + 40

    def open(self):
        self.state = "open"

    def sync_wall(self, arena):
        """Grade fechada é parede; aberta não."""
        blocking = self.bars > 0.5
        present = self.wall in arena.walls
        if blocking and not present:
            arena.walls.append(self.wall)
        elif not blocking and present:
            arena.walls.remove(self.wall)

    def update(self, match):
        self.age += 1
        target = 0.0 if self.state == "open" else 1.0
        if self.bars != target:
            step = 1 / GATE_LIFT
            self.bars = max(target, self.bars - step) if target < self.bars else min(target, self.bars + step)
            if self.age % 6 == 0:
                match.dust(self.rect.centerx + random.uniform(-20, 20), self.rect.bottom - 18, 1)
        self.sync_wall(match.arena)
        if self.state == "open" and self.age % 5 == 0:
            # luz sendo puxada para dentro da masmorra
            x = self.rect.centerx + random.uniform(-self.rect.w / 2, self.rect.w / 2)
            match.particles.append(Particle(x, self.rect.bottom + 30, random.uniform(-0.2, 0.2),
                                            random.uniform(-1.4, -0.8), (180, 150, 250), 26, 3))

    def draw(self, surf, camera):
        r = self.rect.move(-round(camera.x), -round(camera.y))
        # vão escuro
        for i in range(r.h):
            k = i / max(1, r.h - 1)
            surf.fill((round(6 + 16 * k), round(4 + 12 * k), round(10 + 18 * k)), (r.x, r.y + i, r.w, 1))
        if self.state == "open":
            pulse = 0.65 + 0.35 * math.sin(self.age * 0.09)
            g = glow(48, (150, 110, 240), pulse)
            surf.blit(g, g.get_rect(center=(r.centerx, r.bottom - 6)), special_flags=pygame.BLEND_ADD)
        # moldura de pedra (pilares e verga)
        stone, edge, light = (96, 90, 104), (40, 36, 48), (140, 134, 150)
        for x in (r.x - 8, r.right):
            surf.fill(edge, (x - 1, r.y - 2, 10, r.h + 8))
            surf.fill(stone, (x, r.y, 8, r.h + 5))
            surf.fill(light, (x, r.y, 2, r.h + 5))
        surf.fill(edge, (r.x - 9, r.y - 3, r.w + 18, 7))
        surf.fill(stone, (r.x - 8, r.y - 2, r.w + 16, 5))
        # grade
        if self.bars > 0:
            drop = round(r.h * self.bars)
            clip = surf.get_clip()
            surf.set_clip(pygame.Rect(r.x, r.y, r.w, r.h + 4).clip(clip))
            top = r.y + r.h - drop
            for x in range(r.x + 3, r.right - 2, 8):
                surf.fill((24, 22, 30), (x - 1, top - 2, 5, drop + 2))
                surf.fill((122, 118, 132), (x, top - 2, 3, drop + 2))
                surf.fill((180, 176, 190), (x, top - 2, 1, drop + 2))
            for y in (top + drop // 3, top + 2 * drop // 3):
                surf.fill((24, 22, 30), (r.x, y - 1, r.w, 4))
                surf.fill((100, 96, 110), (r.x, y, r.w, 2))
            surf.set_clip(clip)

    def draw_label(self, screen, camera, ui, frame):
        sx, sy = camera.to_screen(self.rect.centerx, self.rect.bottom + 16)
        if self.state == "done":
            text, color = f"MASMORRA {self.number} · OK", theme.MOSS
        elif self.state == "locked":
            text, color = f"MASMORRA {self.number}", theme.MUTED
        else:
            text = f"MASMORRA {self.number}"
            color = theme.BRASS if (frame // 20) % 2 else theme.BONE
        ui.text(screen, text, theme.XS, color, (round(sx), round(sy)))


# ─────────────────────────────────────────────
#  Fogueira (acampamento)
# ─────────────────────────────────────────────
class Campfire(Entity):
    """Fogueira do acampamento: quem fica perto recupera vida devagar (até 70%)."""

    RADIUS = 110
    HEAL_TO = 0.7
    HEAL_EVERY = 6

    def __init__(self, x, y):
        super().__init__(x, y)
        self.wall = Wall(round(x) - 22, round(y) - 12, 44, 24, visible=False)
        self.age = 0
        rng = random.Random(f"fogueira:{x}:{y}")
        self.stones = [(math.cos(a) * 24 + rng.uniform(-2, 2), math.sin(a) * 12 + rng.uniform(-1, 1))
                       for a in [k * math.tau / 10 for k in range(10)]]

    @property
    def sort_y(self):
        return self.y - 4

    def update(self, match):
        self.age += 1
        if self.age % 3 == 0:
            match.particles.append(Particle(self.x + random.uniform(-6, 6), self.y - 14, random.uniform(-0.3, 0.3),
                                            random.uniform(-1.4, -0.7),
                                            random.choice(((252, 170, 60), (234, 104, 44), (255, 230, 150))),
                                            random.randint(16, 28), 3))
        if self.age % 9 == 0:
            match.particles.append(Particle(self.x + random.uniform(-4, 4), self.y - 26, random.uniform(-0.2, 0.2),
                                            -0.5, (80, 76, 84), 40, 5, -0.005))
        if self.age % self.HEAL_EVERY:
            return
        for f in match.alive_players:
            if f.distance_to(self) < self.RADIUS and f.hp < round(f.max_hp * self.HEAL_TO):
                f.hp += 1
                if self.age % (self.HEAL_EVERY * 4) == 0:
                    match.particles.append(Particle(f.x + random.uniform(-10, 10), f.y - 30, 0, -0.6,
                                                    theme.MOSS, 24, 3))

    def draw(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        flicker = math.sin(self.age * 0.23) + 0.5 * math.sin(self.age * 0.61)
        g = glow(120, (255, 140, 60), 0.42 + 0.06 * flicker)
        surf.blit(g, g.get_rect(center=(sx, sy - 6)), special_flags=pygame.BLEND_ADD)
        pygame.draw.ellipse(surf, (16, 12, 14), (sx - 30, sy - 12, 60, 26))
        for dx, dy in self.stones:
            x, y = round(sx + dx), round(sy + dy)
            surf.fill((40, 38, 46), (x - 4, y - 2, 8, 6))
            surf.fill((116, 112, 124), (x - 3, y - 2, 6, 4))
        for a, b in (((-16, 4), (14, -4)), ((-14, -4), (16, 4))):           # lenha cruzada
            pygame.draw.line(surf, (40, 24, 16), (sx + a[0], sy + a[1]), (sx + b[0], sy + b[1]), 7)
            pygame.draw.line(surf, (120, 76, 40), (sx + a[0], sy + a[1] - 1), (sx + b[0], sy + b[1] - 1), 3)
        tall = 20 + round(flicker * 4)
        for w, h, color in ((18, tall, (210, 70, 30)), (12, tall - 6, (250, 160, 50)), (6, tall - 12, (255, 236, 170))):
            pts = [(sx - w // 2, sy), (sx, sy - h), (sx + w // 2, sy)]
            pygame.draw.polygon(surf, color, pts)


# ─────────────────────────────────────────────
#  Baú escondido
# ─────────────────────────────────────────────
WOOD, WOOD_D, WOOD_L = (128, 78, 42), (78, 46, 26), (160, 104, 58)
GOLD, GOLD_D, GOLD_L = (226, 176, 74), (150, 106, 36), (255, 228, 140)
INK = (24, 16, 20)

OPEN_AT = 30                 # quadros tremendo antes da tampa abrir
LAUNCH_AT = 48               # quando as armas saltam do baú
DONE_AT = 150


def _chest_surface(open_):
    """Baú em pixel art 1x (o jogo amplia 2x): madeira, cintas e fechadura dourada."""
    s = pygame.Surface((18, 16), pygame.SRCALPHA)
    body = pygame.Rect(1, 7, 16, 8)
    s.fill(INK, body.inflate(2, 2))
    s.fill(WOOD, body)
    s.fill(WOOD_D, (1, 11, 16, 1))
    s.fill(WOOD_D, (1, 14, 16, 1))
    for x in (2, 14):
        s.fill(GOLD, (x, 7, 2, 8))
        s.fill(GOLD_L, (x, 7, 1, 8))
    if open_:
        s.fill(INK, (0, 2, 18, 6))                 # tampa jogada para trás
        s.fill(WOOD_D, (1, 3, 16, 4))
        s.fill(GOLD_D, (1, 6, 16, 1))
        s.fill((255, 236, 170), (3, 7, 12, 1))     # luz lá de dentro
    else:
        lid = pygame.Rect(1, 3, 16, 5)
        s.fill(INK, lid.inflate(2, 2))
        s.fill(WOOD_L, lid)
        s.fill(WOOD, (1, 5, 16, 3))
        for x in (2, 14):
            s.fill(GOLD, (x, 3, 2, 5))
        s.fill(GOLD, (1, 7, 16, 1))
        s.fill(GOLD, (8, 6, 2, 4))                 # fechadura
        s.fill(INK, (8, 8, 2, 1))
    return pygame.transform.scale(s, (36, 32))


_CHEST = {}


def chest_image(open_):
    if open_ not in _CHEST:
        _CHEST[open_] = _chest_surface(open_)
    return _CHEST[open_]


class Chest(Entity):
    """Baú escondido: perto dele, ATACAR abre. Treme, a tampa pula, sobe um feixe de luz e
    sai uma arma rara para cada jogador."""

    REACH = 64

    def __init__(self, x, y):
        super().__init__(x, y)
        self.state = "closed"        # closed → opening → open
        self.t = 0
        self.age = 0
        self.wall = Wall(round(x) - 18, round(y) - 6, 36, 18, visible=False)

    @property
    def sort_y(self):
        return self.y

    def can_open(self, fighter):
        return self.state == "closed" and fighter.distance_to(self) < self.REACH

    def open(self, match):
        self.state = "opening"
        self.t = 0
        match.assets.play("click", 0.5)

    def update(self, match):
        self.age += 1
        if self.state == "closed":
            if self.age % 50 == 0:                 # brilho de dica
                match.particles.append(Particle(self.x + random.uniform(-14, 14), self.y - 18, 0, -0.4,
                                                GOLD_L, 30, 3))
            return
        if self.state != "opening":
            return
        self.t += 1
        if self.t == OPEN_AT:
            match.burst(self.x, self.y - 20, GOLD_L, 26, speed=5)
            match.camera.shake(4)
            match.assets.play("ability", 0.6)
        if self.t == LAUNCH_AT:
            match.launch_relics(self)
        if OPEN_AT < self.t < 120 and self.t % 2 == 0:
            match.particles.append(Particle(self.x + random.uniform(-10, 10), self.y - 20,
                                            random.uniform(-1.2, 1.2), random.uniform(-3.2, -1.6),
                                            random.choice((GOLD, GOLD_L, (255, 255, 255))), random.randint(24, 40), 3,
                                            gravity=0.08))
        if self.t >= DONE_AT:
            self.state = "open"

    def draw(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        opened = self.state == "open" or (self.state == "opening" and self.t >= OPEN_AT)
        shake = 0
        if self.state == "opening" and self.t < OPEN_AT:
            shake = (2 if (self.t // 2) % 2 else -2) * (1 + self.t // 12)
        # luz que sai do baú aberto
        if self.state == "opening" and self.t >= OPEN_AT:
            k = min(1.0, (self.t - OPEN_AT) / 10) * (1 - max(0, self.t - 110) / 40)
            if k > 0:
                beam = _beam(round(255 * k))
                surf.blit(beam, beam.get_rect(midbottom=(sx, sy - 8)), special_flags=pygame.BLEND_ADD)
                g = glow(60, (255, 210, 120), 0.8 * k)
                surf.blit(g, g.get_rect(center=(sx, sy - 14)), special_flags=pygame.BLEND_ADD)
        elif self.state == "closed":
            g = glow(36, (255, 210, 120), 0.18 + 0.08 * math.sin(self.age * 0.08))
            surf.blit(g, g.get_rect(center=(sx, sy - 10)), special_flags=pygame.BLEND_ADD)
        pygame.draw.ellipse(surf, (10, 8, 12), (sx - 20, sy + 4, 40, 10))
        img = chest_image(opened)
        surf.blit(img, img.get_rect(midbottom=(sx + shake, sy + 10)))

    def draw_prompt(self, screen, camera, ui, frame, near):
        if self.state != "closed" or not near:
            return
        sx, sy = camera.to_screen(self.x, self.y - 40)
        color = theme.BRASS if (frame // 15) % 2 else theme.BONE
        ui.text(screen, "ATACAR: ABRIR", theme.XS, color, (round(sx), round(sy)))


_BEAMS = {}


def _beam(alpha):
    """Feixe de luz do baú (somado na tela). A intensidade vai em 8 degraus, cada um pronto."""
    level = max(0, min(8, round(alpha / 255 * 8)))
    if level not in _BEAMS:
        if "base" not in _BEAMS:
            w, h = 44, 220
            base = pygame.Surface((w, h))
            for y in range(h):
                k = (y / h) ** 1.4
                for x in range(w):
                    v = k * (1 - abs(x - w / 2) / (w / 2)) ** 1.5
                    base.set_at((x, y), (round(255 * v), round(220 * v), round(140 * v)))
            _BEAMS["base"] = base
        img = _BEAMS["base"].copy()
        v = round(255 * level / 8)
        img.fill((v, v, v), special_flags=pygame.BLEND_MULT)
        _BEAMS[level] = img
    return _BEAMS[level]


class RelicDrop(Entity):
    """Arma rara voando do baú até um jogador (em arco)."""

    FLIGHT = 40
    sort_y = 1e9                 # voa por cima de tudo

    def __init__(self, chest, fighter, weapon):
        super().__init__(chest.x, chest.y - 20)
        self.start = (chest.x, chest.y - 20)
        self.fighter = fighter
        self.weapon = weapon
        self.t = 0

    def update(self, match):
        self.t += 1
        k = min(1.0, self.t / self.FLIGHT)
        x0, y0 = self.start
        x1, y1 = self.fighter.x, self.fighter.y - 20
        self.x, self.y = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
        self.z = 90 * 4 * k * (1 - k)
        if self.t % 2 == 0:
            match.particles.append(Particle(self.x, self.y - self.z, 0, 0, GOLD_L, 14, 3))
        if k >= 1:
            self.alive = False
            match.give_relic(self.fighter, self.weapon)

    def draw(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y - getattr(self, "z", 0))
        g = glow(22, (255, 210, 120), 0.7)
        surf.blit(g, g.get_rect(center=(sx, sy)), special_flags=pygame.BLEND_ADD)
        img = weapon_art.rotated(self.weapon.name, self.t * 18)
        if img is not None:
            surf.blit(img, img.get_rect(center=(sx, sy)))


# ─────────────────────────────────────────────
#  Saída da masmorra 1 (a fase acaba com o botão TELETRANSPORTE DE FASE)
# ─────────────────────────────────────────────
class ExitDoor(Entity):
    """Porta que aparece quando a masmorra 1 fica limpa: leva de volta ao acampamento."""

    RADIUS = 70

    def __init__(self, x, y):
        super().__init__(x, y)
        self.age = 0

    @property
    def sort_y(self):
        return self.y - 30

    def update(self, match):
        self.age += 1
        if self.age % 4 == 0:
            match.particles.append(Particle(self.x + random.uniform(-22, 22), self.y, random.uniform(-0.2, 0.2),
                                            random.uniform(-1.2, -0.6), (255, 200, 120), 30, 3))

    def draw(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        grow = min(1.0, self.age / 20)
        h = round(76 * grow)
        if h < 4:
            return
        pygame.draw.ellipse(surf, (255, 190, 100), (sx - 46, sy - 10, 92, 26), 2)
        g = glow(70, (255, 170, 80), 0.5 + 0.15 * math.sin(self.age * 0.1))
        surf.blit(g, g.get_rect(center=(sx, sy - h // 2)), special_flags=pygame.BLEND_ADD)
        door = pygame.Rect(0, 0, 44, h)
        door.midbottom = (sx, sy + 4)
        surf.fill((24, 16, 14), door.inflate(16, 8).move(0, -4))
        surf.fill((110, 100, 112), door.inflate(12, 4).move(0, -2))
        for i in range(door.h):
            k = i / max(1, door.h - 1)
            surf.fill((round(255 - 60 * k), round(210 - 80 * k), round(130 - 70 * k)), (door.x, door.y + i, door.w, 1))
        pygame.draw.circle(surf, (110, 100, 112), (door.centerx, door.y), door.w // 2 + 6, 6, draw_top_left=True,
                           draw_top_right=True)
