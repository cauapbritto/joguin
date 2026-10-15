"""Mapas: definição das arenas, chão pré-renderizado e colisão com paredes."""
import math
import random
from dataclasses import dataclass, field

import pygame

from . import lobbies, scenery
from .entities import Wall, WallStyle, push_circle_out

SOCCER_MAP = "campo_futebol"


class Pitch:
    """Medidas do campo de futebol. Muros, gols, linhas, largada e as zonas do jogo saem daqui."""
    W, H = 2240, 1260                      # 40% maior que o campo antigo (1600 x 900)
    EDGE = 20                              # muro de cima e de baixo; o gol fica atrás da linha
    LINE = 40                              # linha de fundo da esquerda (a da direita: W - LINE)
    GOAL = 160                             # boca do gol
    MID_Y = H / 2
    GOAL_TOP, GOAL_BOTTOM = H // 2 - GOAL // 2, H // 2 + GOAL // 2
    AREA_DEPTH, AREA_HALF = 250, 320       # grande área (fundo e metade da largura)
    SMALL_DEPTH, SMALL_HALF = 100, 150     # pequena área
    SPOT = 190                             # marca do pênalti, a partir da linha de fundo
    CIRCLE = 112                           # círculo central
    STRIPES = 20                           # faixas do gramado

    @classmethod
    def goal_x(cls, team):
        """Onde a bola entra no gol que o time defende (time 0 à esquerda)."""
        return cls.EDGE if team == 0 else cls.W - cls.EDGE

    @classmethod
    def walls(cls):
        W, H, E, L = cls.W, cls.H, cls.EDGE, cls.LINE
        top, bottom = cls.GOAL_TOP, cls.GOAL_BOTTOM
        return [(0, 0, W, E), (0, H - E, W, E),
                (E, E, L - E, top - E), (E, bottom, L - E, H - E - bottom),
                (W - L, E, L - E, top - E), (W - L, bottom, L - E, H - E - bottom)]

    @classmethod
    def spawns(cls):
        """Largada: time 0 à esquerda (vagas 0 e 2), time 1 à direita (1 e 3)."""
        x = round(cls.W * 0.19)
        up, down = round(cls.MID_Y - 130), round(cls.MID_Y + 130)
        return [(x, up), (cls.W - x, up), (x, down), (cls.W - x, down)]


@dataclass
class MapConfig:
    key: str
    name: str
    size: tuple
    walls: list                    # (x, y, w, h)
    spawns: list                   # pontos de partida
    floor: tuple = ((18, 16, 30), (22, 20, 35))
    wall_colors: tuple = ((50, 45, 65), (75, 65, 95), (30, 25, 40))
    bounds: list = field(default_factory=list)   # paredes invisíveis (a arte do fundo já mostra o muro)
    battle: bool = True
    theme: str = None              # cenário (chão, paredes, ambiente) de outro mapa; None = o próprio
    void: list = field(default_factory=list)     # áreas fora das salas (masmorra), pintadas de escuro
    markers: dict = field(default_factory=dict)  # acampamento: largada, fogueira, baú, entradas

    @property
    def scenery(self):
        return self.theme or self.key


MAPS = [
    MapConfig(
        "arena_classica", "Arena Clássica", (1600, 1200),
        walls=[(100, 100, 50, 250), (100, 850, 50, 250), (1450, 100, 50, 250), (1450, 850, 50, 250),
               (400, 300, 300, 50), (900, 300, 300, 50), (400, 850, 300, 50), (900, 850, 300, 50),
               (750, 570, 100, 60), (300, 570, 50, 60), (1250, 570, 50, 60)],
        spawns=[(420, 600), (1180, 600), (800, 200), (800, 1000)],
        bounds=[(0, 0, 1600, 24), (0, 1112, 1600, 88), (0, 0, 22, 1200), (1572, 0, 28, 1200)],
    ),
    MapConfig(
        "calabouco", "Calabouço", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (200, 100, 30, 200), (1370, 100, 30, 200), (200, 900, 30, 200), (1370, 900, 30, 200),
               (400, 250, 200, 30), (1000, 250, 200, 30), (400, 920, 200, 30), (1000, 920, 200, 30),
               (700, 400, 200, 30), (700, 770, 200, 30), (600, 500, 30, 200), (970, 500, 30, 200)],
        spawns=[(400, 600), (1200, 600), (800, 150), (800, 1050)],
        floor=((34, 26, 22), (40, 31, 26)), wall_colors=((64, 30, 24), (100, 52, 40), (30, 14, 10)),
    ),
    MapConfig(
        "coliseu", "Coliseu", (1800, 1200),
        walls=[(700, 100, 40, 150), (1060, 100, 40, 150), (700, 950, 40, 150), (1060, 950, 40, 150),
               (400, 500, 40, 200), (1360, 500, 40, 200), (870, 200, 60, 60), (870, 940, 60, 60),
               (300, 200, 150, 30), (1350, 200, 150, 30), (300, 970, 150, 30), (1350, 970, 150, 30)],
        spawns=[(260, 600), (1540, 600), (900, 600), (900, 400)],
        bounds=[(0, 0, 1800, 52), (0, 0, 70, 1200), (1730, 0, 70, 1200), (0, 1140, 1800, 60)],
        wall_colors=((70, 62, 52), (104, 94, 78), (30, 26, 22)),
    ),
    MapConfig(
        "floresta", "Floresta Encantada", (2000, 1400),
        walls=[(0, 0, 2000, 30), (0, 0, 30, 1400), (1970, 0, 30, 1400), (0, 1370, 2000, 30),
               (300, 200, 40, 200), (1660, 200, 40, 200), (300, 1000, 40, 200), (1660, 1000, 40, 200),
               (600, 400, 200, 40), (1200, 400, 200, 40), (600, 960, 200, 40), (1200, 960, 200, 40),
               (900, 650, 200, 100), (400, 680, 60, 40), (1540, 680, 60, 40),
               (750, 620, 30, 160), (1220, 620, 30, 160)],
        spawns=[(520, 700), (1480, 700), (1000, 250), (1000, 1150)],
        floor=((30, 50, 26), (35, 58, 30)), wall_colors=((40, 66, 32), (66, 98, 50), (16, 28, 14)),
    ),
    MapConfig(
        "templo_gelado", "Templo Gelado", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (400, 80, 30, 200), (1170, 80, 30, 200), (400, 920, 30, 200), (1170, 920, 30, 200),
               (200, 350, 150, 30), (1250, 350, 150, 30), (200, 820, 150, 30), (1250, 820, 150, 30),
               (700, 200, 200, 30), (700, 970, 200, 30), (580, 500, 30, 200), (990, 500, 30, 200),
               (750, 560, 100, 80)],
        spawns=[(400, 600), (1200, 600), (800, 360), (800, 840)],
        floor=((38, 48, 60), (46, 57, 70)), wall_colors=((52, 76, 100), (110, 150, 190), (20, 34, 50)),
    ),
    MapConfig(
        SOCCER_MAP, "Estádio", (Pitch.W, Pitch.H),
        walls=Pitch.walls(),
        spawns=Pitch.spawns(),
        floor=((44, 122, 58), (50, 134, 64)), wall_colors=((112, 102, 90), (150, 138, 122), (60, 52, 44)),
        battle=False,
    ),
]
# Variações das arenas (a 2ª masmorra de cada fase da campanha; também valem no duelo)
MAPS += [
    MapConfig(
        "floresta_ruinas", "Ruínas da Floresta", (2000, 1400),
        walls=[(0, 0, 2000, 30), (0, 0, 30, 1400), (1970, 0, 30, 1400), (0, 1370, 2000, 30),
               (800, 520, 140, 40), (1060, 520, 140, 40), (800, 840, 140, 40), (1060, 840, 140, 40),
               (760, 520, 40, 120), (760, 760, 40, 120), (1200, 520, 40, 120), (1200, 760, 40, 120),
               (300, 250, 240, 40), (1460, 250, 240, 40), (300, 1110, 240, 40), (1460, 1110, 240, 40),
               (520, 600, 40, 200), (1440, 600, 40, 200), (980, 150, 40, 180), (980, 1070, 40, 180)],
        spawns=[(300, 700), (1700, 700), (1000, 420), (1000, 990)],
        theme="floresta",
    ),
    MapConfig(
        "calabouco_celas", "Celas do Calabouço", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (300, 30, 30, 220), (600, 30, 30, 220), (970, 30, 30, 220), (1270, 30, 30, 220),
               (300, 950, 30, 220), (600, 950, 30, 220), (970, 950, 30, 220), (1270, 950, 30, 220),
               (500, 480, 60, 60), (1040, 480, 60, 60), (500, 660, 60, 60), (1040, 660, 60, 60),
               (200, 400, 200, 30), (1200, 400, 200, 30), (200, 770, 200, 30), (1200, 770, 200, 30)],
        spawns=[(400, 600), (1200, 600), (800, 180), (800, 1020)],
        theme="calabouco",
    ),
    MapConfig(
        "templo_patio", "Pátio do Templo", (1600, 1200),
        walls=[(0, 0, 1600, 30), (0, 0, 30, 1200), (1570, 0, 30, 1200), (0, 1170, 1600, 30),
               (250, 250, 150, 30), (1200, 250, 150, 30), (250, 920, 150, 30), (1200, 920, 150, 30),
               (560, 380, 30, 160), (1010, 380, 30, 160), (560, 660, 30, 160), (1010, 660, 30, 160),
               (760, 180, 80, 60), (760, 960, 80, 60), (380, 560, 80, 80), (1140, 560, 80, 80)],
        spawns=[(250, 600), (1350, 600), (800, 330), (800, 870)],
        theme="templo_gelado",
    ),
]


def _lobby(theme):
    """Acampamento da campanha (lobby) no tema da fase, desenhado como texto em lobbies.py."""
    name, rows = lobbies.LOBBIES[theme]
    size, walls, void, markers = lobbies.parse(rows)
    return MapConfig(f"acampamento_{theme}", name, size, walls=walls, spawns=markers["S"], battle=False,
                     theme=theme, void=void, markers=markers)


MAPS += [_lobby(theme) for theme in lobbies.LOBBIES]
MAPS_BY_KEY = {m.key: m for m in MAPS}
BATTLE_MAPS = [m for m in MAPS if m.battle]


class Arena:
    def __init__(self, cfg, assets):
        self.cfg = cfg
        self.width, self.height = cfg.size
        style = scenery.wall_style(cfg.scenery) or WallStyle(*cfg.wall_colors)
        textures = assets.wall_textures.get(cfg.key, {})
        self.walls = []
        for x, y, w, h in cfg.walls:
            wall = Wall(x, y, w, h)
            wall.style = style
            wall.image = _fit_texture(textures, w, h)
            self.walls.append(wall)
        for x, y, w, h in cfg.bounds:
            self.walls.append(Wall(x, y, w, h, visible=False))
        for wall in self.walls:
            wall.prepare()          # pronto antes da partida começar (nada de tranco no primeiro quadro)
        self.floor = self._render_floor(assets.backgrounds.get(cfg.key))
        self.ambience = scenery.create_ambience(cfg.scenery, cfg.size, self.walls)

    @property
    def size(self):
        return self.width, self.height

    # ── colisão ──────────────────────────────
    def resolve(self, body):
        """Empurra um corpo circular para fora das paredes e para dentro do mapa."""
        hit = None
        for _ in range(2):
            moved = False
            for wall in self.walls:
                res = push_circle_out(body.x, body.y, body.radius, wall.rect)
                if res:
                    body.x, body.y, nx, ny = res
                    hit = (nx, ny)
                    moved = True
            if not moved:
                break
        r = body.radius
        body.x = min(max(body.x, r), self.width - r)
        body.y = min(max(body.y, r), self.height - r)
        return hit

    def is_free(self, x, y, radius):
        if not (radius <= x <= self.width - radius and radius <= y <= self.height - radius):
            return False
        return not any(w.overlaps_circle(x, y, radius) for w in self.walls)

    def free_spot(self, x, y, radius):
        """Ponto livre mais próximo de (x, y), procurando em espiral."""
        if self.is_free(x, y, radius):
            return x, y
        for dist in range(10, 400, 10):
            for k in range(16):
                a = k * math.pi / 8
                px, py = x + math.cos(a) * dist, y + math.sin(a) * dist
                if self.is_free(px, py, radius):
                    return px, py
        return x, y

    def random_free_spot(self, radius, rng=random):
        for _ in range(80):
            x = rng.uniform(80, self.width - 80)
            y = rng.uniform(80, self.height - 80)
            if self.is_free(x, y, radius + 6):
                return x, y
        return self.width / 2, self.height / 2

    def blocks_segment(self, a, b):
        return any(w.rect.clipline(a, b) for w in self.walls)

    # ── desenho ──────────────────────────────
    def draw_floor(self, surf, camera, view_size):
        area = pygame.Rect(int(camera.x), int(camera.y), *view_size)
        surf.blit(self.floor, (0, 0), area)

    def draw_walls(self, surf, camera):
        view = pygame.Rect(int(camera.x), int(camera.y), *surf.get_size())
        for wall in self.walls:
            if wall.visible and view.colliderect(wall.area):     # fora da câmera não desenha
                wall.draw(surf, camera)

    def draw_ambience(self, surf, camera, frame, layer):
        self.ambience.draw(surf, camera, frame, layer)

    def thumbnail(self, size):
        """Miniatura do mapa para a tela de seleção."""
        full = self.floor.copy()

        class _Origin:
            x = y = 0
        self.draw_walls(full, _Origin)
        return pygame.transform.smoothscale(full, size)

    def _render_floor(self, background):
        surf = pygame.Surface((self.width, self.height))
        if background is not None:
            surf.blit(pygame.transform.scale(background, (self.width, self.height)), (0, 0))
            return surf
        if self.cfg.key == SOCCER_MAP:
            _soccer_pitch(surf, self.cfg.floor)
            return surf
        painted = scenery.paint_floor(self.cfg.key, (self.width, self.height), self.cfg.theme, self.cfg.void)
        if painted is not None:
            return painted
        rng = random.Random(self.cfg.key)
        a, b = self.cfg.floor
        grout = tuple(max(0, c - 10) for c in a)
        for gx in range(0, self.width, 32):
            for gy in range(0, self.height, 32):
                base = a if ((gx // 32) + (gy // 32)) % 2 else b
                j = rng.randint(-3, 3)
                color = tuple(max(0, min(255, c + j)) for c in base)
                surf.fill(color, (gx, gy, 32, 32))
                surf.fill(grout, (gx, gy, 32, 1))
                surf.fill(grout, (gx, gy, 1, 32))
                if rng.random() < 0.08:
                    surf.fill(grout, (gx + rng.randint(6, 22), gy + rng.randint(6, 22), 3, 2))
        return surf


def _fit_texture(textures, w, h):
    if (w, h) in textures:
        return textures[(w, h)]
    for (tw, th), img in textures.items():
        if tw == w and th > h:                     # mesma largura: junta topo + base
            out = pygame.Surface((w, h), pygame.SRCALPHA)
            top = h // 2
            out.blit(img, (0, 0), (0, 0, w, top))
            out.blit(img, (0, top), (0, th - (h - top), w, h - top))
            return out
        if th == h and tw > w:                     # mesma altura: junta esquerda + direita
            out = pygame.Surface((w, h), pygame.SRCALPHA)
            left = w // 2
            out.blit(img, (0, 0), (0, 0, left, h))
            out.blit(img, (left, 0), (tw - (w - left), 0, w - left, h))
            return out
    return None


def _soccer_pitch(surf, colors):
    P = Pitch
    w, h = surf.get_size()
    a, b = colors
    stripe = w / P.STRIPES
    for i in range(P.STRIPES):
        x0, x1 = round(i * stripe), round((i + 1) * stripe)
        surf.fill(a if i % 2 else b, (x0, 0, x1 - x0, h))
    line = (226, 232, 214)
    cx, cy = w // 2, h // 2
    left, right = P.LINE, w - P.LINE
    pygame.draw.line(surf, line, (cx, P.EDGE), (cx, h - P.EDGE), 3)
    pygame.draw.circle(surf, line, (cx, cy), P.CIRCLE, 3)
    surf.fill(line, (cx - 4, cy - 4, 8, 8))
    for depth, half in ((P.AREA_DEPTH, P.AREA_HALF), (P.SMALL_DEPTH, P.SMALL_HALF)):
        pygame.draw.rect(surf, line, (left, cy - half, depth, half * 2), 3)
        pygame.draw.rect(surf, line, (right - depth, cy - half, depth, half * 2), 3)
    for sx in (left + P.SPOT, right - P.SPOT):
        surf.fill(line, (sx - 3, cy - 3, 6, 6))
    cr = 40
    top, bottom = P.EDGE, h - P.EDGE
    corners = ((left, top, 1.5 * math.pi, 2 * math.pi), (right, top, math.pi, 1.5 * math.pi),
               (left, bottom, 0, 0.5 * math.pi), (right, bottom, 0.5 * math.pi, math.pi))
    for cx, cy, a0, a1 in corners:
        pygame.draw.arc(surf, line, (cx - cr, cy - cr, cr * 2, cr * 2), a0, a1, 3)
