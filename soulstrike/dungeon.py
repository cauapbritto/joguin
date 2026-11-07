"""Coisas do caminho da campanha: a fogueira e o baú (com as armas raras) da sala de recompensa,
a porta de saída da sala avulsa, o portal da fase e o botão INICIAR BATALHA."""
import math
import random

import pygame

from . import theme, weapon_art
from .data import rarity_color
from .entities import Entity, Particle, Wall



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
#  Fogueira (acampamento)
# ─────────────────────────────────────────────
class Campfire(Entity):
    """Fogueira do corredor: quem fica perto recupera vida devagar (até 70%)."""

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


def chest_image(open_, style=None):
    key = (open_, style)
    if key not in _CHEST:
        _CHEST[key] = _safe_surface(open_) if style == "lag" else _chest_surface(open_)
    return _CHEST[key]


def _safe_surface(open_):
    """Cofre da Lag Lobby (capítulo 2): aço escuro, roda do segredo e a porta que abre de lado."""
    s = pygame.Surface((24, 22), pygame.SRCALPHA)
    body, light, dark = (92, 100, 116), (150, 160, 178), (46, 50, 60)
    s.fill(dark, (1, 2, 22, 20))
    s.fill(body, (2, 3, 20, 18))
    s.fill(light, (2, 3, 20, 1))
    s.fill(dark, (2, 20, 20, 1))
    if open_:
        s.fill((20, 18, 26), (4, 5, 16, 14))                     # dentro (vazio, com o brilho saindo)
        s.fill((255, 220, 140), (6, 15, 12, 2))
        s.fill(body, (19, 3, 5, 18))                             # porta aberta para o lado
        s.fill(light, (19, 3, 1, 18))
    else:
        s.fill(light, (4, 5, 16, 1))
        pygame.draw.circle(s, (200, 206, 216), (12, 12), 4, 1)   # roda do segredo
        s.fill((230, 236, 244), (12, 9, 1, 3))
        s.fill((64, 200, 230), (17, 6, 2, 2))                    # luz ciano da Lag Lobby
        s.fill(dark, (5, 18, 3, 2))
        s.fill(dark, (16, 18, 3, 2))
    return pygame.transform.scale(s, (40, 36))


class Chest(Entity):
    """Baú escondido: perto dele, ATACAR abre. Treme, a tampa pula, sobe um feixe de luz e
    sai uma arma rara para cada jogador."""

    REACH = 64

    def __init__(self, x, y, style=None):
        super().__init__(x, y)
        self.style = style           # "lag": vira o cofre da Lag Lobby
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
            match.assets.play("bau", 0.6)
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
        img = chest_image(opened, self.style)
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


class GroundWeapon(Entity):
    """Arma no chão: a rara que alguém largou ou a comum que um inimigo derrubou. Perto dela,
    ATACAR pega — e quem pega solta no lugar a que tinha do mesmo tipo (troca). O nome e o brilho
    têm a cor da raridade (comum branca, rara azul, roubada dourada)."""

    REACH = 58
    TOSS = 22                    # quadros do arremesso até o chão

    def __init__(self, weapon, start, end):
        super().__init__(*end)
        self.weapon = weapon
        self.start = start
        self.end = end
        self.t = 0
        self.z = 0.0
        self.x, self.y = start
        self.color = rarity_color(weapon)

    @property
    def landed(self):
        return self.t >= self.TOSS

    @property
    def sort_y(self):
        return self.y - 30 if self.landed else 1e9      # no chão fica embaixo de quem pisa

    def can_pick(self, fighter):
        return self.landed and fighter.alive_in_match and fighter.distance_to(self) < self.REACH

    def update(self, match):
        self.t += 1
        if not self.landed:
            k = self.t / self.TOSS
            (x0, y0), (x1, y1) = self.start, self.end
            self.x, self.y = x0 + (x1 - x0) * k, y0 + (y1 - y0) * k
            self.z = 46 * 4 * k * (1 - k)
            if self.landed:
                self.z = 0.0
                match.dust(self.x, self.y + 6, 5)
                match.assets.play("click", 0.4)
        elif self.t % 24 == 0:
            match.particles.append(Particle(self.x + random.uniform(-14, 14), self.y - 4, 0, -0.5, self.color, 22, 2))

    def draw(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        pygame.draw.ellipse(surf, (0, 0, 0), (sx - 18, sy + 2, 36, 10))
        bob = 0 if not self.landed else round(math.sin(self.t * 0.08) * 2) - 6
        g = glow(20, self.color, 0.45 + 0.15 * math.sin(self.t * 0.1))
        surf.blit(g, g.get_rect(center=(sx, sy - 8 + bob)), special_flags=pygame.BLEND_ADD)
        angle = self.t * 24 if not self.landed else -25
        img = weapon_art.rotated(self.weapon.name, angle)
        if img is not None:
            surf.blit(img, img.get_rect(center=(sx, sy - round(self.z) + bob)))

    def draw_prompt(self, screen, camera, ui, frame, near):
        if not self.landed:
            return
        # embaixo da arma (em cima ficam os nomes dos jogadores)
        sx, sy = camera.to_screen(self.x, self.y + 14)
        ui.text(screen, self.weapon.name.upper(), theme.XS, self.color, (round(sx), round(sy)))
        if near:
            color = theme.BRASS if (frame // 15) % 2 else theme.BONE
            ui.text(screen, "ATACAR: PEGAR", theme.XS, color, (round(sx), round(sy) + 12))


# ─────────────────────────────────────────────
#  Saída da masmorra 1 (a fase acaba com o botão TELETRANSPORTE DE FASE)
# ─────────────────────────────────────────────
class ExitDoor(Entity):
    """Porta que aparece quando a masmorra 1 fica limpa: leva ao corredor (nunca de volta)."""

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


# ─────────────────────────────────────────────
#  Portal da fase (fim da masmorra 2)
# ─────────────────────────────────────────────
class PhasePortal(Entity):
    """Portal que aparece quando a masmorra 2 fica limpa. Todos dentro do círculo (contagem de
    2 s, a passagem coletiva) e o grupo vai para a próxima fase."""

    RADIUS = 78
    flat = True

    def __init__(self, x, y):
        super().__init__(x, y)
        self.age = 0

    def contains(self, fighter):
        return math.hypot(fighter.x - self.x, (fighter.y - self.y) * 1.4) < self.RADIUS

    def update(self, match):
        self.age += 1
        if self.age % 3 == 0:
            a = random.uniform(0, math.tau)
            r = self.RADIUS * random.uniform(0.6, 1.0)
            match.particles.append(Particle(self.x + math.cos(a) * r, self.y + math.sin(a) * r * 0.7,
                                            -math.cos(a) * 0.6, -0.9 - random.uniform(0, 0.6),
                                            random.choice(((240, 230, 255), (170, 120, 250))), 30, 3))

    def draw(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        grow = min(1.0, self.age / 24)
        w, h = round(self.RADIUS * 2 * grow), round(self.RADIUS * 1.4 * grow)
        if w < 6:
            return
        pulse = 0.6 + 0.4 * math.sin(self.age * 0.1)
        g = glow(round(self.RADIUS * grow) + 20, (150, 100, 250), pulse)
        surf.blit(g, g.get_rect(center=(sx, sy)), special_flags=pygame.BLEND_ADD)
        ring = pygame.Rect(0, 0, w, h)
        ring.center = (sx, sy)
        pygame.draw.ellipse(surf, (40, 20, 70), ring)
        for i, color in enumerate(((120, 70, 220), (170, 120, 250), (230, 210, 255))):
            k = 1 - i * 0.22
            r = ring.inflate(-ring.w * (1 - k), -ring.h * (1 - k))
            spin = (self.age * (0.05 + 0.02 * i)) % math.tau
            pygame.draw.arc(surf, color, r, spin, spin + math.pi * 1.2, 3)
            pygame.draw.arc(surf, color, r, spin + math.pi, spin + math.pi * 1.7, 2)


# ─────────────────────────────────────────────
#  Botão INICIAR BATALHA (entrada da masmorra)
# ─────────────────────────────────────────────
class StartButton(Entity):
    """Botão no chão, na entrada da masmorra: os inimigos só começam a sair quando alguém aperta
    (ATACAR perto). Dá tempo de o grupo se arrumar, trocar de arma e respirar."""

    REACH = 64

    def __init__(self, x, y):
        super().__init__(x, y)
        self.age = 0
        self.pressed = 0                 # quadros desde que foi apertado (0 = ainda não)
        self.wall = Wall(round(x) - 20, round(y) - 8, 40, 18, visible=False)

    @property
    def sort_y(self):
        return self.y

    def can_use(self, fighter):
        return not self.pressed and fighter.alive_in_match and fighter.distance_to(self) < self.REACH

    def press(self, match):
        self.pressed = 1
        match.camera.shake(4)
        match.burst(self.x, self.y - 20, (255, 120, 90), 22, speed=5)

    def update(self, match):
        self.age += 1
        if self.pressed:
            self.pressed += 1
            if self.pressed > 50:
                self.alive = False
                if self.wall in match.arena.walls:
                    match.arena.walls.remove(self.wall)

    def draw(self, surf, camera):
        sx, sy = round(self.x - camera.x), round(self.y - camera.y)
        sink = min(8, self.pressed // 2) if self.pressed else 0
        pygame.draw.ellipse(surf, (10, 8, 12), (sx - 24, sy + 2, 48, 12))
        surf.fill((40, 36, 48), (sx - 20, sy - 14, 40, 18))
        surf.fill((96, 90, 104), (sx - 18, sy - 14, 36, 14))
        surf.fill((140, 134, 150), (sx - 18, sy - 14, 36, 2))
        pulse = 0.5 + 0.5 * math.sin(self.age * 0.15)
        if not self.pressed:
            g = glow(30, (255, 90, 70), 0.4 + 0.4 * pulse)
            surf.blit(g, g.get_rect(center=(sx, sy - 22)), special_flags=pygame.BLEND_ADD)
        top = sy - 26 + sink
        pygame.draw.ellipse(surf, (90, 20, 20), (sx - 13, top + 4, 26, 12))
        pygame.draw.ellipse(surf, (220, 60, 50) if not self.pressed else (120, 40, 36), (sx - 13, top, 26, 12))
        pygame.draw.ellipse(surf, (255, 170, 150), (sx - 7, top + 2, 10, 4))

    def draw_prompt(self, screen, camera, ui, frame, near):
        if self.pressed:
            return
        sx, sy = camera.to_screen(self.x, self.y - 52)
        color = theme.BONE if near and (frame // 15) % 2 else theme.BRASS
        ui.text(screen, "INICIAR BATALHA", theme.XS, color, (round(sx), round(sy)))
