"""Desenho da Casa da turma (hub da campanha): móveis, cantos da turma, horta e portas, em pixel art
no mesmo tamanho dos personagens. Cada peça é desenhada uma vez numa folha transparente
(``bake``) e depois só colada na tela.

As funções desenham em coordenadas da folha: ``x, y`` é o ponto de referência da peça (o mesmo das
prévias do hub)."""
import math
import random

import pygame

from . import config, theme
from .data import CHARACTERS

WOOD, WOOD_D, WOOD_L = (122, 80, 48), (84, 54, 32), (156, 108, 66)
CAU = (84, 162, 222)         # cores da turma (data.py)
ARYEL = (234, 132, 64)
BORBA = (236, 118, 84)
METAL, METAL_D = (150, 150, 160), (90, 90, 100)
SHADOW = (0, 0, 0, 90)
SPRITES = {c.key: c.sprite for c in CHARACTERS}

_ctx = {}


def use(assets):
    """As fontes e os sprites do jogo (os textos e os retratos usam)."""
    from .ui import UI
    if _ctx.get("assets") is not assets:
        _ctx["assets"] = assets
        _ctx["ui"] = UI(assets)


def _text(s, text, size, color, pos):
    ui = _ctx.get("ui")
    if ui is not None:
        ui.text(s, text, size, color, pos)


def _sprite(key):
    assets = _ctx.get("assets")
    if assets is None:
        return None
    return assets.sprites.get(SPRITES.get(key, key))


def shade(color, amount):
    return tuple(max(0, min(255, c + amount)) for c in color[:3])


# ── folha pronta ─────────────────────────────
CANVAS = (720, 560)
ANCHOR = (360, 380)


class Baked:
    """Peça já desenhada: a imagem e onde fica o canto dela em relação ao ponto de referência."""

    def __init__(self, image, dx, dy):
        self.image, self.dx, self.dy = image, dx, dy

    @property
    def bottom(self):
        return self.dy + self.image.get_height()


def bake(fn, *args, **kw):
    """Desenha ``fn(folha, x, y, ...)`` uma vez e recorta só o que foi pintado."""
    canvas = pygame.Surface(CANVAS, pygame.SRCALPHA)
    ax, ay = ANCHOR
    fn(canvas, ax, ay, *args, **kw)
    rect = canvas.get_bounding_rect()
    if rect.w == 0 or rect.h == 0:
        rect = pygame.Rect(ax, ay, 1, 1)
    return Baked(canvas.subsurface(rect).copy(), rect.x - ax, rect.y - ay)


# ── pincéis ──────────────────────────────────
def box(s, c, x, y, w, h):
    s.fill(c, (round(x), round(y), round(w), round(h)))


def shadow(s, x, y, w):
    pygame.draw.ellipse(s, SHADOW, (x - w // 2, y - 6, w, 12))


def glow(s, center, size, color, alpha):
    g = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.ellipse(g, (*color, alpha), (0, 0, *size))
    s.blit(g, (center[0] - size[0] // 2, center[1] - size[1] // 2))


# ── sala ─────────────────────────────────────
def rug(s, x, y, w, h, c1=(120, 40, 40), c2=(200, 150, 70)):
    box(s, c2, x, y, w, h)
    box(s, c1, x + 4, y + 4, w - 8, h - 8)
    for i in range(x + 12, x + w - 12, 16):
        box(s, c2, i, y + 10, 8, 2)
        box(s, c2, i, y + h - 12, 8, 2)
    box(s, (150, 60, 50), x + 20, y + 20, w - 40, h - 40)
    pygame.draw.rect(s, c2, (x + 20, y + 20, w - 40, h - 40), 2)


def table(s, x, y, w=120, h=56):
    shadow(s, x + w // 2, y + h + 8, w + 10)
    box(s, WOOD_D, x + 6, y + h - 4, 8, 16)
    box(s, WOOD_D, x + w - 14, y + h - 4, 8, 16)
    box(s, WOOD, x, y, w, h)
    box(s, WOOD_L, x, y, w, 4)
    box(s, WOOD_D, x, y + h - 4, w, 4)
    for k in range(3):                                       # pratos e um vaso no meio
        box(s, (236, 232, 220), x + 24 + k * (w - 60) // 2, y + 18, 14, 10)
    box(s, (90, 140, 200), x + w // 2 - 5, y + 10, 10, 14)
    box(s, (230, 80, 90), x + w // 2 - 6, y + 4, 4, 4)
    box(s, (250, 210, 90), x + w // 2 + 2, y + 5, 4, 4)


def chair(s, x, y):
    shadow(s, x + 10, y + 26, 24)
    box(s, WOOD_D, x, y, 20, 26)
    box(s, WOOD, x + 2, y + 2, 16, 10)


def sofa(s, x, y, w=150, c=(70, 90, 140)):
    shadow(s, x + w // 2, y + 46, w)
    box(s, shade(c, -30), x, y, w, 44)
    box(s, c, x + 8, y + 4, w - 16, 22)
    box(s, shade(c, 20), x + 8, y + 4, w - 16, 3)
    box(s, shade(c, -10), x + 10, y + 26, w - 20, 14)
    box(s, shade(c, -40), x, y, 10, 44)
    box(s, shade(c, -40), x + w - 10, y, 10, 44)
    box(s, shade(c, 30), x + 20, y + 8, 22, 14)              # almofadas
    box(s, (230, 200, 120), x + w - 42, y + 8, 22, 14)


def shelf(s, x, y, w=80, seed=0):
    rng = random.Random(seed or x)
    shadow(s, x + w // 2, y + 70, w + 6)
    box(s, WOOD_D, x, y, w, 70)
    for k in range(3):
        sy = y + 6 + k * 22
        box(s, (40, 26, 16), x + 4, sy, w - 8, 18)
        bx = x + 6
        while bx < x + w - 10:
            bw = rng.randrange(4, 9)
            box(s, rng.choice(((170, 60, 50), (60, 110, 170), (210, 180, 90), (80, 140, 80), (150, 90, 160))),
                bx, sy + rng.randrange(0, 5), bw, 18 - rng.randrange(0, 5))
            bx += bw + 1
        box(s, WOOD, x + 2, sy + 18, w - 4, 3)


def plant(s, x, y):
    shadow(s, x, y + 4, 26)
    box(s, (160, 90, 60), x - 10, y - 16, 20, 18)
    box(s, (190, 110, 74), x - 10, y - 16, 20, 3)
    for dx, dy in ((-10, -30), (0, -38), (9, -30), (-5, -24), (5, -24)):
        pygame.draw.ellipse(s, (60, 130, 60), (x + dx - 7, y + dy - 7, 14, 16))
        pygame.draw.ellipse(s, (90, 160, 80), (x + dx - 4, y + dy - 6, 6, 6))


def lamp(s, x, y):
    g = pygame.Surface((140, 140), pygame.SRCALPHA)
    for r in range(70, 0, -6):
        pygame.draw.circle(g, (255, 210, 130, int(14 * (1 - r / 70)) + 2), (70, 70), r)
    s.blit(g, (x - 70, y - 70))
    shadow(s, x, y + 30, 22)
    box(s, (60, 50, 40), x - 2, y, 4, 30)
    box(s, (60, 50, 40), x - 8, y + 28, 16, 4)
    pygame.draw.polygon(s, (230, 200, 140), [(x - 12, y), (x + 12, y), (x + 8, y - 12), (x - 8, y - 12)])


def window_wall(s, x, y, w=120):
    box(s, (40, 26, 16), x - 4, y - 4, w + 8, 60)
    box(s, (120, 170, 210), x, y, w, 52)
    box(s, (170, 210, 236), x, y, w, 18)
    box(s, (70, 120, 70), x, y + 38, w, 14)              # o quintal lá fora
    box(s, (40, 26, 16), x + w // 2 - 2, y, 4, 52)
    box(s, (40, 26, 16), x, y + 24, w, 3)
    for cx in (x - 10, x + w - 6):                      # cortinas
        box(s, (150, 60, 60), cx, y - 6, 16, 66)
        box(s, (120, 44, 44), cx + 10, y - 6, 3, 66)
    light = pygame.Surface((w + 60, 160), pygame.SRCALPHA)
    pygame.draw.polygon(light, (255, 240, 200, 26), [(30, 0), (w + 30, 0), (w + 60, 160), (0, 160)])
    s.blit(light, (x - 30, y + 56))


def frame_portrait(s, x, y, key=None, covered=False):
    """Quadro (x, y = canto de cima): o rosto do herói, ou coberto com um pano."""
    box(s, (40, 24, 14), x - 2, y - 2, 52, 60)
    box(s, (210, 160, 70), x, y, 48, 56)
    box(s, (30, 26, 36), x + 4, y + 4, 40, 48)
    if covered:
        box(s, (150, 146, 136), x - 4, y - 4, 56, 64)
        for i in range(0, 56, 8):
            box(s, (124, 120, 112), x - 4 + i, y - 4, 3, 64)
        box(s, (110, 106, 98), x - 4, y + 56, 56, 4)
        _text(s, "?", theme.S, (70, 66, 60), (x + 24, y + 28))
        return
    sprite = _sprite(key) if key else None
    if sprite is not None:
        img = sprite.frame("frente", 0)
        head = img.subsurface((0, 0, img.get_width(), img.get_height() // 2)).copy()
        k = 44 / head.get_width()
        head = pygame.transform.scale(head, (44, round(head.get_height() * k)))
        clip = s.get_clip()
        s.set_clip((x + 4, y + 4, 40, 48))
        s.blit(head, head.get_rect(midtop=(x + 24, y + 4)))
        s.set_clip(clip)


def easel_portrait(s, x, y, key):
    shadow(s, x, y + 80, 46)
    box(s, WOOD_D, x - 20, y + 30, 4, 50)
    box(s, WOOD_D, x + 16, y + 30, 4, 50)
    box(s, WOOD_D, x - 2, y + 30, 4, 46)
    frame_portrait(s, x - 24, y - 26, key)


def mannequin(s, x, y, key):
    """Herói da vitrine em cima do pedestal (x, y = pé do pedestal)."""
    shadow(s, x, y + 2, 46)
    box(s, (60, 54, 70), x - 22, y - 8, 44, 10)
    box(s, (90, 82, 104), x - 22, y - 8, 44, 3)
    sprite = _sprite(key)
    if sprite is None:
        return
    img = sprite.frame("frente", 0)
    k = config.SPRITE_HEIGHT / img.get_height()
    img = pygame.transform.scale(img, (round(img.get_width() * k), config.SPRITE_HEIGHT))
    s.blit(img, img.get_rect(midbottom=(x, y - 6)))


def poster(s, x, y, w, h, bg, text, fg=(255, 255, 255)):
    box(s, (20, 14, 10), x - 2, y - 2, w + 4, h + 4)
    box(s, bg, x, y, w, h)
    _text(s, text, theme.XS, fg, (x + w // 2, y + h // 2))


# ── canto do Cauanzera ───────────────────────
def pc_desk(s, x, y):
    """Mesa do Cauanzera: monitor ligado, gabinete com luz, teclado, caneca e cadeira gamer."""
    shadow(s, x + 70, y + 62, 160)
    box(s, WOOD_D, x + 4, y + 30, 8, 30)
    box(s, WOOD_D, x + 128, y + 30, 8, 30)
    box(s, WOOD, x, y + 14, 140, 22)
    box(s, WOOD_L, x, y + 14, 140, 3)
    box(s, (30, 30, 36), x + 30, y - 34, 64, 42)                 # monitor
    box(s, (16, 28, 48), x + 33, y - 31, 58, 34)
    box(s, (60, 110, 170), x + 33, y - 31, 58, 3)
    for i in range(3):
        box(s, (200, 220, 250), x + 37 + i * 16, y - 24, 8, 8)
    box(s, (40, 40, 48), x + 33, y - 2, 58, 4)
    box(s, (40, 40, 46), x + 58, y + 8, 8, 8)
    glow(s, (x + 62, y - 15), (110, 70), (90, 170, 255), 34)
    box(s, (34, 34, 40), x + 104, y - 26, 26, 40)                # gabinete com luz colorida
    for i, c in enumerate(((240, 80, 160), (80, 200, 255), (120, 240, 140))):
        box(s, c, x + 108, y - 20 + i * 8, 18, 2)
    box(s, (60, 60, 70), x + 30, y + 18, 54, 8)                  # teclado, mouse, caneca, disquete
    for i in range(6):
        box(s, (110, 110, 120), x + 33 + i * 8, y + 20, 6, 2)
    box(s, (200, 200, 210), x + 90, y + 20, 6, 5)
    box(s, (240, 240, 240), x + 8, y + 12, 10, 10)
    box(s, (40, 70, 140), x + 18, y + 22, 10, 10)
    box(s, (30, 30, 40), x + 52, y + 50, 24, 30)                 # cadeira gamer
    box(s, CAU, x + 54, y + 52, 20, 22)
    box(s, (20, 20, 26), x + 56, y + 80, 16, 6)


def lectern_book(s, x, y):
    """O livro do Cauanzera aberto no suporte, com uma luz suave em volta."""
    g = pygame.Surface((90, 70), pygame.SRCALPHA)
    for r in range(35, 0, -5):
        pygame.draw.ellipse(g, (255, 230, 150, int(16 * (1 - r / 35)) + 4), (45 - r, 35 - r * 0.8, r * 2, r * 1.6))
    s.blit(g, (x - 45, y - 40))
    shadow(s, x, y + 40, 50)
    box(s, WOOD_D, x - 4, y + 4, 8, 36)
    box(s, WOOD_D, x - 14, y + 36, 28, 6)
    pygame.draw.polygon(s, WOOD, [(x - 24, y - 2), (x + 24, y - 2), (x + 20, y + 10), (x - 20, y + 10)])
    box(s, (240, 232, 210), x - 21, y - 12, 20, 16)
    box(s, (250, 244, 228), x + 1, y - 12, 20, 16)
    box(s, (150, 30, 40), x - 1, y - 13, 2, 18)
    for i in range(4):
        box(s, (130, 120, 110), x - 18, y - 9 + i * 3, 14, 1)
        box(s, (130, 120, 110), x + 4, y - 9 + i * 3, 14, 1)
    box(s, (200, 40, 50), x + 10, y + 2, 2, 10)                  # fitinha marcando a página


def uno_armor(s, x, y):
    """Armadura de enfeite feita de peças de um Uno branco: faróis retangulares, grade e a placa."""
    W, W2, D = (240, 240, 236), (208, 208, 204), (40, 40, 46)
    shadow(s, x, y + 2, 64)
    box(s, (90, 90, 96), x - 26, y - 6, 52, 8)
    box(s, (120, 120, 126), x - 3, y - 20, 6, 16)
    box(s, W2, x - 16, y - 40, 12, 22)
    box(s, W2, x + 4, y - 40, 12, 22)
    box(s, (40, 40, 44), x - 16, y - 24, 12, 3)
    box(s, (40, 40, 44), x + 4, y - 24, 12, 3)
    box(s, W, x - 24, y - 80, 48, 42)                            # peitoral: a frente quadradinha do Uno
    box(s, W2, x - 24, y - 42, 48, 4)
    for fx in (x - 21, x + 9):                                   # faróis retangulares
        box(s, (250, 244, 200), fx, y - 70, 12, 8)
        box(s, (180, 170, 130), fx, y - 63, 12, 1)
    box(s, D, x - 7, y - 70, 14, 8)                              # grade com frisos
    for i in range(3):
        box(s, (90, 90, 100), x - 6, y - 69 + i * 3, 12, 1)
    box(s, (30, 30, 34), x - 24, y - 54, 48, 6)                  # para-choque preto
    box(s, (250, 250, 250), x - 8, y - 52, 16, 4)                # placa
    box(s, (30, 30, 30), x - 6, y - 51, 12, 1)
    for sx in (x - 36, x + 24):                                  # ombreiras: para-lamas com a roda
        box(s, W, sx, y - 82, 12, 16)
        pygame.draw.circle(s, D, (sx + 6, y - 68), 6)
        pygame.draw.circle(s, (150, 150, 156), (sx + 6, y - 68), 2)
    box(s, W, x - 15, y - 104, 30, 24)                           # elmo: a cabine
    box(s, (90, 140, 180), x - 12, y - 100, 24, 10)
    box(s, (170, 210, 236), x - 10, y - 99, 6, 2)
    box(s, W2, x - 15, y - 82, 30, 3)
    box(s, (40, 40, 46), x - 17, y - 104, 34, 3)                 # bagageiro no teto


# ── canto do Aryel ───────────────────────────
def moto(s, x, y):
    """Moto do Aryel, de lado (x, y = chão entre as rodas)."""
    m = pygame.Surface((120, 80), pygame.SRCALPHA)
    D = (26, 24, 30)
    for wx in (22, 96):
        pygame.draw.circle(m, D, (wx, 62), 15)
        pygame.draw.circle(m, (120, 120, 130), (wx, 62), 6)
        pygame.draw.circle(m, (60, 60, 66), (wx, 62), 15, 3)
    pygame.draw.polygon(m, ARYEL, [(30, 50), (82, 50), (96, 36), (70, 30), (40, 32)])     # tanque e carenagem
    pygame.draw.polygon(m, shade(ARYEL, -40), [(30, 50), (82, 50), (78, 56), (34, 56)])
    box(m, (30, 26, 30), 34, 26, 30, 7)                                                   # banco
    box(m, METAL, 14, 54, 26, 4)                                                          # escapamento
    box(m, METAL_D, 82, 46, 4, 18)                                                        # garfo
    box(m, METAL, 84, 16, 4, 18)
    box(m, D, 80, 14, 16, 4)                                                              # guidão
    box(m, (250, 240, 190), 98, 30, 8, 6)                                                 # farol
    box(m, (240, 240, 240), 52, 38, 16, 3)
    shadow(s, x, y + 4, 110)
    s.blit(m, m.get_rect(midbottom=(x, y + 6)))


def roulette_table(s, x, y):
    shadow(s, x, y + 40, 70)
    box(s, WOOD_D, x - 4, y + 10, 8, 30)
    box(s, WOOD, x - 30, y, 60, 12)
    cx, cy = x, y - 8
    for k in range(12):
        a0 = k * math.tau / 12
        a1 = a0 + math.tau / 12
        c = (50, 170, 80) if k % 2 == 0 else (200, 50, 50)
        pygame.draw.polygon(s, c, [(cx, cy), (cx + math.cos(a0) * 22, cy + math.sin(a0) * 10),
                                   (cx + math.cos(a1) * 22, cy + math.sin(a1) * 10)])
    pygame.draw.ellipse(s, (210, 170, 70), (cx - 23, cy - 11, 46, 22), 2)
    box(s, (240, 240, 240), cx - 2, cy - 2, 4, 4)


def helmet_rack(s, x, y):
    shadow(s, x, y + 72, 30)
    box(s, WOOD_D, x - 2, y, 4, 70)
    box(s, WOOD_D, x - 14, y + 66, 28, 6)
    pygame.draw.ellipse(s, (30, 30, 36), (x - 14, y - 6, 28, 22))
    box(s, (120, 170, 210), x - 9, y + 2, 16, 6)
    box(s, ARYEL, x - 14, y + 12, 28, 3)


# ── canto do Albeguinio ──────────────────────
def office_desk(s, x, y):
    """Mesa do Albeguinio: notebook aberto, pilhas de papel, carimbo e o celular virado para baixo."""
    shadow(s, x + 70, y + 50, 160)
    box(s, METAL_D, x + 4, y + 26, 6, 26)
    box(s, METAL_D, x + 130, y + 26, 6, 26)
    box(s, (170, 160, 140), x, y + 10, 140, 20)
    box(s, (200, 190, 170), x, y + 10, 140, 3)
    box(s, (40, 40, 48), x + 50, y - 16, 40, 26)                 # notebook
    box(s, (20, 40, 30), x + 53, y - 13, 34, 20)
    for i in range(4):
        box(s, (90, 230, 120), x + 56, y - 10 + i * 4, 10 + (i * 7) % 20, 2)
    box(s, (70, 70, 80), x + 46, y + 10, 48, 5)
    for k in range(3):                                           # papéis
        for j in range(5 + k * 2):
            box(s, (240, 236, 224) if j % 2 else (226, 220, 206), x + 6 + k * 14, y + 4 - j * 2, 12, 2)
    box(s, (150, 30, 40), x + 104, y + 2, 10, 8)                 # carimbo
    box(s, (60, 40, 30), x + 107, y - 6, 4, 8)
    box(s, (20, 20, 24), x + 118, y + 8, 12, 6)                  # celular virado
    box(s, (120, 200, 255), x + 120, y + 5, 8, 1)


def file_cabinet(s, x, y):
    shadow(s, x + 20, y + 74, 46)
    box(s, METAL_D, x, y, 40, 72)
    for k in range(3):
        box(s, METAL, x + 3, y + 3 + k * 23, 34, 20)
        box(s, (60, 60, 70), x + 14, y + 10 + k * 23, 12, 3)
    box(s, (240, 236, 224), x + 6, y - 4, 26, 6)


def router(s, x, y):
    shadow(s, x + 17, y + 12, 38)
    box(s, (30, 30, 36), x, y, 34, 12)
    box(s, (50, 50, 58), x, y, 34, 3)
    box(s, (40, 40, 46), x + 4, y - 14, 3, 14)
    box(s, (40, 40, 46), x + 27, y - 14, 3, 14)
    for i in range(4):
        box(s, (90, 240, 120) if i != 2 else (30, 60, 40), x + 6 + i * 6, y + 6, 3, 3)


# ── canto do Borba Jr (João) ─────────────────
def bakery(s, x, y):
    """Balcão da PADARIA DO JOÃO: vitrine de vidro com pães, caixa registradora e a placa."""
    shadow(s, x + 110, y + 64, 240)
    box(s, WOOD_D, x, y + 20, 220, 44)
    box(s, WOOD, x + 4, y + 24, 212, 36)
    box(s, WOOD_L, x, y + 18, 220, 4)
    box(s, (230, 220, 190), x + 10, y + 8, 180, 22)
    for i in range(12):                                          # pães, sonhos e pão de queijo
        px, py = x + 16 + i * 14, y + 14 + (i % 2) * 6
        kind = i % 3
        if kind == 0:
            pygame.draw.ellipse(s, (200, 140, 70), (px, py, 14, 8))
            box(s, (230, 180, 110), px + 4, py + 2, 6, 1)
        elif kind == 1:
            pygame.draw.circle(s, (220, 170, 90), (px + 6, py + 4), 5)
            box(s, (250, 250, 250), px + 3, py, 6, 2)
        else:
            pygame.draw.circle(s, (236, 200, 110), (px + 6, py + 4), 4)
    glass = pygame.Surface((180, 30), pygame.SRCALPHA)
    glass.fill((200, 230, 240, 90))
    s.blit(glass, (x + 10, y))
    box(s, (240, 250, 255), x + 10, y, 180, 2)
    box(s, (60, 60, 70), x + 196, y - 4, 20, 22)                 # caixa registradora
    box(s, (120, 220, 140), x + 199, y - 1, 14, 5)
    box(s, (40, 24, 14), x + 30, y - 74, 160, 34)                # placa
    box(s, (250, 236, 200), x + 33, y - 71, 154, 28)
    _text(s, "PADARIA DO JOÃO", theme.XS, (150, 60, 30), (x + 110, y - 57))
    box(s, (40, 24, 14), x + 60, y - 40, 3, 10)
    box(s, (40, 24, 14), x + 160, y - 40, 3, 10)


def oven(s, x, y):
    shadow(s, x + 40, y + 70, 90)
    box(s, (140, 70, 50), x, y, 80, 70)
    for r in range(0, 70, 10):
        for c in range((r // 10) % 2 * 10, 80, 20):
            box(s, (120, 58, 40), x + c, y + r, 18, 8)
    pygame.draw.ellipse(s, (30, 14, 10), (x + 18, y + 26, 44, 30))
    pygame.draw.ellipse(s, (250, 150, 50), (x + 24, y + 36, 32, 18))
    pygame.draw.ellipse(s, (255, 220, 120), (x + 32, y + 42, 16, 10))
    box(s, (90, 90, 96), x + 30, y - 30, 20, 30)                 # chaminé


def exo_stand(s, x, y):
    """Exoesqueleto do Borba Jr no suporte (x, y = base)."""
    shadow(s, x, y + 2, 60)
    box(s, METAL_D, x - 24, y - 6, 48, 8)
    box(s, METAL, x - 3, y - 20, 6, 16)
    for lx in (x - 16, x + 6):
        box(s, (70, 70, 80), lx, y - 50, 10, 32)
        box(s, BORBA, lx, y - 42, 10, 6)
    box(s, (70, 70, 80), x - 20, y - 86, 40, 38)
    box(s, BORBA, x - 16, y - 82, 32, 14)
    pygame.draw.circle(s, (120, 220, 255), (x, y - 62), 5)
    for ax in (x - 32, x + 20):
        box(s, (70, 70, 80), ax, y - 84, 12, 30)
        box(s, BORBA, ax, y - 84, 12, 8)
    box(s, (90, 90, 100), x + 22, y - 56, 10, 10)                # canhão de pulso
    box(s, (60, 60, 70), x - 10, y - 104, 20, 18)
    box(s, (120, 220, 255), x - 7, y - 98, 14, 5)


def city_car(s, x, y):
    """O Honda City do João estacionado no quintal, de lado (x, y = chão no meio do carro)."""
    W, W2, D = (226, 228, 232), (190, 192, 198), (30, 30, 34)
    shadow(s, x, y + 2, 176)
    pygame.draw.ellipse(s, (0, 0, 0, 60), (x - 92, y - 8, 184, 18))
    box(s, W2, x - 84, y - 30, 168, 26)                          # carroceria (sedã: porta-malas atrás)
    box(s, W, x - 84, y - 34, 168, 20)
    box(s, shade(W, 14), x - 84, y - 34, 168, 3)
    pygame.draw.polygon(s, W, [(x - 46, y - 34), (x - 30, y - 58), (x + 30, y - 58), (x + 50, y - 34)])
    pygame.draw.polygon(s, (90, 130, 170), [(x - 40, y - 36), (x - 27, y - 54), (x - 2, y - 54), (x - 2, y - 36)])
    pygame.draw.polygon(s, (90, 130, 170), [(x + 2, y - 36), (x + 2, y - 54), (x + 27, y - 54), (x + 43, y - 36)])
    box(s, (170, 210, 236), x - 30, y - 52, 8, 2)
    box(s, W2, x - 1, y - 56, 3, 22)                             # coluna do meio
    box(s, (120, 122, 128), x - 84, y - 20, 168, 2)              # friso
    box(s, (190, 192, 198), x - 10, y - 26, 10, 2)               # maçanetas
    box(s, (190, 192, 198), x + 26, y - 26, 10, 2)
    box(s, (250, 240, 190), x + 78, y - 30, 8, 6)                # farol na frente (direita)
    box(s, (210, 50, 50), x - 86, y - 30, 6, 7)                  # lanterna atrás
    box(s, D, x + 76, y - 12, 10, 6)
    box(s, D, x - 86, y - 12, 10, 6)
    for wx in (x - 52, x + 52):                                  # rodas
        pygame.draw.circle(s, D, (wx, y - 4), 15)
        pygame.draw.circle(s, (170, 172, 180), (wx, y - 4), 7)
        pygame.draw.circle(s, (90, 90, 96), (wx, y - 4), 2)
    box(s, (250, 250, 250), x + 64, y - 18, 14, 6)               # placa
    box(s, (40, 40, 120), x + 64, y - 18, 14, 2)


# ── portas trancadas ─────────────────────────
def locked_door(s, x, y, label, w=80, opened=False, inside=None):
    """Porta de madeira com grade e cadeado (x, y = canto de cima). Aberta: a folha encostada de lado
    e o cômodo aparecendo lá dentro."""
    box(s, (30, 20, 12), x - 4, y - 4, w + 8, 72)
    if opened:
        box(s, (24, 18, 22), x, y, w, 64)
        box(s, (255, 220, 140, 40), x, y + 40, w, 24)
        if inside is not None:
            inside(s, x, y, w)
        box(s, WOOD_D, x + w - 10, y, 10, 64)                    # a folha aberta de lado
        box(s, WOOD_L, x + w - 10, y, 2, 64)
        _text(s, label, theme.XS, theme.MOSS, (x + w // 2, y + 80))
        return
    box(s, WOOD_D, x, y, w, 64)
    for i in range(x + 6, x + w - 4, 10):
        box(s, (60, 60, 70), i, y, 4, 64)
    box(s, (90, 90, 100), x, y + 20, w, 4)
    box(s, (90, 90, 100), x, y + 44, w, 4)
    box(s, (210, 170, 60), x + w // 2 - 7, y + 26, 14, 14)
    box(s, (150, 110, 30), x + w // 2 - 2, y + 32, 4, 5)
    pygame.draw.arc(s, (190, 190, 200), (x + w // 2 - 6, y + 16, 12, 16), 0, math.pi, 3)
    _text(s, label, theme.XS, theme.BRASS, (x + w // 2, y + 80))


def inside_sotao(s, x, y, w):
    """Sótão aberto: a escada subindo e o brilho dos troféus lá em cima."""
    for k in range(5):
        box(s, WOOD, x + 14 + k * 4, y + 54 - k * 11, w - 40 - k * 8, 4)
    for k, c in enumerate(((250, 210, 90), (200, 200, 210), (210, 140, 80))):
        box(s, c, x + 16 + k * 16, y + 6, 8, 10)
        box(s, c, x + 18 + k * 16, y + 16, 4, 4)


def inside_oficina(s, x, y, w):
    """Oficina aberta: a bancada com ferramentas e um alvo de treino."""
    box(s, (70, 70, 80), x + 6, y + 40, w - 22, 6)
    for k in range(4):
        box(s, (150, 150, 160), x + 10 + k * 12, y + 16, 3, 18)
    pygame.draw.circle(s, (220, 60, 50), (x + w - 28, y + 22), 10)
    pygame.draw.circle(s, (240, 240, 240), (x + w - 28, y + 22), 6)
    pygame.draw.circle(s, (220, 60, 50), (x + w - 28, y + 22), 2)


def inside_garagem(s, x, y, w):
    """Garagem aberta: a frente do Uno branco lá dentro."""
    W = (240, 240, 236)
    box(s, W, x + 14, y + 22, w - 38, 34)
    box(s, (90, 140, 180), x + 22, y + 10, w - 54, 14)
    box(s, W, x + 18, y + 8, w - 46, 4)
    for fx in (x + 18, x + w - 42):
        box(s, (250, 244, 200), fx, y + 34, 14, 8)
    box(s, (40, 40, 46), x + w // 2 - 14, y + 34, 18, 8)
    box(s, (30, 30, 34), x + 14, y + 46, w - 38, 6)
    box(s, (250, 250, 250), x + w // 2 - 14, y + 47, 18, 4)


def cellar_door(s, x, y, label, opened=False):
    """Alçapão do porão no chão do quintal (x, y = canto de cima)."""
    w, h = 84, 56
    box(s, (40, 40, 44), x - 4, y - 4, w + 8, h + 8)
    if opened:
        box(s, (12, 10, 16), x, y, w, h)
        for k in range(4):
            box(s, (70, 70, 76), x + 10, y + 8 + k * 12, w - 20, 4)
        pygame.draw.rect(s, (120, 60, 180), (x + 6, y + 6, w - 12, h - 12), 2)
        _text(s, label, theme.XS, theme.MOSS, (x + w // 2, y + h + 14))
        return
    for k in range(2):
        box(s, WOOD_D, x + k * (w // 2) + 1, y, w // 2 - 2, h)
        for j in range(4):
            box(s, WOOD, x + k * (w // 2) + 3, y + 4 + j * 13, w // 2 - 6, 9)
    box(s, (90, 90, 100), x, y + 14, w, 4)
    box(s, (90, 90, 100), x, y + h - 18, w, 4)
    box(s, (210, 170, 60), x + w // 2 - 7, y + h // 2 - 7, 14, 14)
    box(s, (150, 110, 30), x + w // 2 - 2, y + h // 2 - 1, 4, 5)
    _text(s, label, theme.XS, theme.BRASS, (x + w // 2, y + h + 14))


# ── quintal ──────────────────────────────────
def bed(s, x, y, w=100, rows=3, crops="sprout", seed=0):
    """Canteiro da horta (x, y = canto de cima)."""
    rng = random.Random(seed or x * 7 + y)
    box(s, WOOD_D, x - 4, y - 4, w + 8, rows * 8 + 8)
    box(s, (78, 50, 30), x, y, w, rows * 8)
    for row in range(rows):
        ry = y + 4 + row * 8
        box(s, (60, 38, 22), x, ry + 5, w, 2)
        for cx in range(x + 6, x + w - 6, 14):
            if crops == "sprout":
                box(s, (90, 170, 70), cx, ry, 2, 4)
                box(s, (120, 200, 90), cx - 2, ry - 1, 2, 2)
                box(s, (120, 200, 90), cx + 2, ry - 1, 2, 2)
            else:
                pygame.draw.circle(s, (60, 140, 60), (cx + 1, ry + 1), 4)
                if rng.random() < 0.4:
                    box(s, (220, 70, 50), cx, ry - 1, 3, 3)


def sign(s, x, y, text):
    shadow(s, x, y + 22, 16)
    box(s, WOOD_D, x - 2, y, 4, 22)
    box(s, WOOD, x - 30, y - 14, 60, 18)
    box(s, WOOD_L, x - 30, y - 14, 60, 2)
    _text(s, text, theme.XS, (40, 24, 12), (x, y - 5))


def watering_can(s, x, y):
    shadow(s, x + 12, y + 12, 26)
    box(s, (90, 140, 170), x, y, 18, 12)
    box(s, (90, 140, 170), x + 18, y + 2, 10, 3)
    pygame.draw.arc(s, (70, 110, 140), (x + 2, y - 8, 14, 14), 0, math.pi, 2)


def flower(s, x, y, color, big=False):
    """Florzinha que nasce no canteiro regado (grande: a flor do meio da horta)."""
    k = 2 if big else 1
    box(s, (70, 150, 60), x - k, y - 14 * k, 2 * k, 14 * k)
    box(s, (90, 170, 70), x - 6 * k, y - 8 * k, 5 * k, 3 * k)
    box(s, (90, 170, 70), x + k, y - 10 * k, 5 * k, 3 * k)
    for dx, dy in ((-4, 0), (4, 0), (0, -4), (0, 4)):
        pygame.draw.circle(s, color, (x + dx * k, y - 18 * k + dy * k), 3 * k)
    pygame.draw.circle(s, (250, 220, 90), (x, y - 18 * k), 2 * k)


def adventure_arch(s, x, y, w):
    """Pilares e a placa da saída para a aventura no muro de baixo (x, y = canto de cima do vão)."""
    for px in (x - 18, x + w + 2):
        box(s, (90, 86, 96), px, y - 30, 16, 70)
        box(s, (130, 124, 138), px, y - 30, 16, 4)
        box(s, (60, 56, 66), px + 12, y - 26, 4, 66)
        pygame.draw.circle(s, theme.BRASS, (px + 8, y - 38), 6)
        pygame.draw.circle(s, (255, 230, 160), (px + 8, y - 39), 3)
