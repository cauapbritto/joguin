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


def finish(s, seed=0):
    """Acabamento no padrão dos personagens: contorno escuro de 1 pixel em volta da peça, luz na
    beirada de cima, sombra na de baixo e um grão fino para tirar o chapado. Brilhos e sombras
    no chão (translúcidos) ficam de fora."""
    size = s.get_size()
    solid = pygame.mask.from_surface(s, 200)
    if not solid.count():
        return
    grown = pygame.mask.Mask(size)
    for off in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        grown.draw(solid, off)
    ring = grown.copy()
    ring.erase(solid, (0, 0))
    top = solid.copy()                                   # pixel com vazio logo acima: luz
    top.erase(solid, (0, 1))
    bottom = solid.copy()                                # com vazio logo abaixo: sombra
    bottom.erase(solid, (0, -1))
    s.blit(top.to_surface(setcolor=(40, 36, 30, 0), unsetcolor=(0, 0, 0, 0)), (0, 0),
           special_flags=pygame.BLEND_RGB_ADD)
    s.blit(bottom.to_surface(setcolor=(170, 166, 176, 255), unsetcolor=(255, 255, 255, 255)), (0, 0),
           special_flags=pygame.BLEND_RGB_MULT)
    s.blit(ring.to_surface(setcolor=(18, 12, 16, 255), unsetcolor=(0, 0, 0, 0)), (0, 0))
    rng = random.Random(seed)
    rect = solid.get_bounding_rects()
    get, put = s.get_at, s.set_at
    for r in rect:
        for _ in range(r.w * r.h // 40):
            x, y = rng.randrange(r.x, r.right), rng.randrange(r.y, r.bottom)
            if not solid.get_at((x, y)):
                continue
            cr, cg, cb, a = get((x, y))
            k = 9 if rng.random() < 0.5 else -10
            put((x, y), (max(0, min(255, cr + k)), max(0, min(255, cg + k)), max(0, min(255, cb + k)), a))


def bake(fn, *args, **kw):
    """Desenha ``fn(folha, x, y, ...)`` uma vez, dá o acabamento e recorta só o que foi pintado."""
    canvas = pygame.Surface(CANVAS, pygame.SRCALPHA)
    ax, ay = ANCHOR
    fn(canvas, ax, ay, *args, **kw)
    finish(canvas, fn.__name__)
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
    """Mesa de jantar de madeira com toalha, pratos, copos e um vaso de flores (x, y = canto de cima)."""
    shadow(s, x + w // 2, y + h + 14, w + 16)
    for lx in (x + 4, x + w - 12):                               # pés grossos
        box(s, WOOD_D, lx, y + h - 2, 8, 18)
        box(s, shade(WOOD_D, -18), lx + 6, y + h - 2, 2, 18)
    box(s, shade(WOOD, -26), x, y + h - 8, w, 10)                # frente do tampo
    box(s, shade(WOOD, -40), x, y + h, w, 2)
    box(s, WOOD, x, y, w, h - 8)                                 # tampo, com as tábuas
    for k in range(1, 4):
        box(s, shade(WOOD, -14), x, y + k * (h - 8) // 4, w, 1)
    for k in range(0, w, 37):
        box(s, shade(WOOD, 10), x + k + 6, y + 4 + (k // 37 % 3) * 9, 14, 1)
    box(s, WOOD_L, x, y, w, 2)
    box(s, (226, 220, 204), x + 10, y + 14, w - 20, 22)          # toalha de renda no meio
    box(s, (244, 240, 228), x + 10, y + 14, w - 20, 2)
    for k in range(x + 12, x + w - 12, 6):
        box(s, (200, 190, 170), k, y + 35, 3, 2)
    for k in range(3):                                           # pratos com comida e copos
        px = x + 22 + k * (w - 60) // 2
        pygame.draw.ellipse(s, (250, 250, 248), (px, y + 6, 22, 12))
        pygame.draw.ellipse(s, (210, 210, 206), (px + 3, y + 8, 16, 8))
        box(s, (200, 120, 60), px + 7, y + 10, 8, 4)
        box(s, (190, 220, 240), px + 26, y + 6, 5, 8)
        box(s, (240, 250, 255), px + 26, y + 6, 5, 2)
    cx = x + w // 2
    box(s, (70, 120, 190), cx - 5, y + 16, 10, 14)               # vaso com flores
    box(s, (110, 160, 220), cx - 5, y + 16, 3, 14)
    for dx, dy, c in ((-6, 6, (230, 80, 90)), (0, 2, (250, 210, 90)), (6, 6, (240, 140, 180)), (-2, 9, (230, 80, 90))):
        box(s, (70, 140, 60), cx + dx // 2, y + dy + 4, 1, 12 - dy)
        box(s, c, cx + dx - 2, y + dy - 2, 5, 5)


def chair(s, x, y, back=True):
    """Cadeira de madeira vista de cima (x, y = canto de cima), com o encosto de ripas."""
    shadow(s, x + 11, y + 30, 26)
    box(s, WOOD_D, x + 1, y + 20, 3, 10)
    box(s, WOOD_D, x + 18, y + 20, 3, 10)
    box(s, WOOD, x, y + 10, 22, 12)                              # assento
    box(s, WOOD_L, x, y + 10, 22, 2)
    box(s, shade(WOOD, -24), x, y + 20, 22, 2)
    if back:
        box(s, WOOD_D, x, y - 4, 22, 4)                          # encosto
        for k in range(3):
            box(s, WOOD, x + 3 + k * 6, y, 4, 10)
        box(s, WOOD_L, x, y - 4, 22, 1)


def sofa(s, x, y, w=150, c=(70, 90, 140)):
    """Sofá de três lugares visto de frente e de cima (x, y = canto de cima)."""
    dark, darker, light = shade(c, -28), shade(c, -50), shade(c, 26)
    shadow(s, x + w // 2, y + 50, w + 8)
    for fx in (x + 8, x + w - 14):                               # pezinhos
        box(s, WOOD_D, fx, y + 44, 6, 5)
    box(s, dark, x + 8, y, w - 16, 20)                           # encosto
    box(s, light, x + 10, y, w - 20, 2)
    n = 3
    cw = (w - 28) // n
    for k in range(n):                                           # almofadas do encosto
        bx = x + 14 + k * cw
        box(s, c, bx, y + 3, cw - 2, 15)
        box(s, light, bx + 2, y + 4, cw - 6, 2)
        box(s, dark, bx + cw // 2 - 1, y + 9, 2, 2)              # botão do capitonê
    box(s, darker, x + 8, y + 20, w - 16, 3)
    for k in range(n):                                           # assentos
        bx = x + 14 + k * cw
        box(s, c, bx, y + 22, cw - 2, 14)
        box(s, light, bx + 1, y + 22, cw - 4, 2)
        box(s, dark, bx, y + 34, cw - 2, 2)
    box(s, dark, x + 12, y + 36, w - 24, 8)                      # frente
    box(s, darker, x + 12, y + 42, w - 24, 2)
    for ax in (x, x + w - 14):                                   # braços redondos
        box(s, dark, ax, y + 6, 14, 38)
        box(s, c, ax + 2, y + 4, 10, 8)
        box(s, light, ax + 3, y + 4, 8, 2)
        box(s, darker, ax, y + 40, 14, 4)
    box(s, (236, 206, 120), x + 20, y + 10, 18, 12)              # almofadas soltas
    box(s, (250, 230, 160), x + 21, y + 10, 16, 2)
    box(s, shade(c, 60), x + w - 40, y + 10, 18, 12)


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
    """Abajur de pé com cúpula de pano e a luz quente em volta (x, y = alto da haste)."""
    g = pygame.Surface((160, 160), pygame.SRCALPHA)
    for r in range(80, 0, -6):
        pygame.draw.circle(g, (255, 210, 130, int(16 * (1 - r / 80)) + 2), (80, 80), r)
    s.blit(g, (x - 80, y - 90))
    shadow(s, x, y + 32, 26)
    pygame.draw.ellipse(s, (54, 46, 40), (x - 10, y + 26, 20, 8))  # base
    pygame.draw.ellipse(s, (90, 78, 66), (x - 8, y + 26, 16, 4))
    box(s, (70, 60, 50), x - 1, y - 20, 3, 48)                    # haste
    box(s, (120, 104, 86), x - 1, y - 20, 1, 48)
    pygame.draw.polygon(s, (226, 196, 140), [(x - 15, y - 18), (x + 15, y - 18), (x + 10, y - 38), (x - 10, y - 38)])
    pygame.draw.polygon(s, (250, 226, 170), [(x - 12, y - 20), (x - 4, y - 20), (x - 2, y - 36), (x - 8, y - 36)])
    box(s, (190, 150, 100), x - 15, y - 20, 30, 2)               # barra da cúpula
    box(s, (255, 236, 180), x - 8, y - 17, 16, 2)                # a lâmpada aparecendo embaixo


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
    """Mesa do Cauanzera: monitor com o CAUANZERA OS ligado, gabinete com luz colorida, teclado,
    mouse no mousepad, caneca de café, caixinhas de som e a cadeira gamer."""
    shadow(s, x + 70, y + 62, 160)
    for lx in (x + 4, x + 128):                                  # pés
        box(s, WOOD_D, lx, y + 30, 8, 30)
        box(s, shade(WOOD_D, -18), lx + 6, y + 30, 2, 30)
    box(s, WOOD, x, y + 14, 140, 16)                             # tampo
    box(s, WOOD_L, x, y + 14, 140, 2)
    box(s, shade(WOOD, -26), x, y + 28, 140, 8)                  # frente da mesa
    box(s, shade(WOOD, -10), x + 100, y + 29, 34, 6)             # gaveta
    box(s, (200, 170, 90), x + 115, y + 31, 4, 2)
    light = pygame.Surface((90, 10), pygame.SRCALPHA)           # a luz da tela no tampo
    light.fill((120, 180, 255, 40))
    s.blit(light, (x + 18, y + 15))
    # monitor: moldura fina, a área de trabalho azul com ícones e a barra de tarefas
    box(s, (22, 22, 28), x + 28, y - 38, 68, 46)
    sx, sy, sw, sh = x + 31, y - 35, 62, 38
    for k in range(sh):                                          # fundo em degradê
        t = k / sh
        box(s, (round(24 + 30 * t), round(52 + 50 * t), round(110 + 70 * t)), sx, sy + k, sw, 1)
    for k, (c, label) in enumerate((((236, 190, 70), 0), ((40, 40, 46), 1), ((90, 170, 240), 2), ((150, 150, 160), 3))):
        ix, iy = sx + 4 + (k % 2) * 12, sy + 4 + (k // 2) * 12
        box(s, c, ix, iy, 7, 6)                                  # pasta, terminal, navegador, lixeira
        if label == 1:
            box(s, (90, 240, 120), ix + 1, iy + 2, 3, 1)
        box(s, (220, 230, 245), ix, iy + 8, 7, 1)
    box(s, (250, 250, 255), sx + 38, sy + 8, 18, 14)             # janela aberta
    box(s, CAU, sx + 38, sy + 8, 18, 3)
    for k in range(3):
        box(s, (150, 160, 180), sx + 40, sy + 13 + k * 3, 10 + (k * 3) % 5, 1)
    box(s, (16, 18, 26), sx, sy + sh - 5, sw, 5)                 # barra de tarefas
    box(s, CAU, sx + 1, sy + sh - 4, 5, 3)
    box(s, (200, 210, 230), sx + sw - 10, sy + sh - 4, 8, 3)
    box(s, (40, 40, 48), x + 58, y + 8, 8, 6)                    # pé do monitor
    box(s, (40, 40, 48), x + 52, y + 13, 20, 3)
    # gabinete com luz colorida e o ventilador
    box(s, (30, 30, 36), x + 104, y - 28, 28, 44)
    box(s, (50, 50, 60), x + 104, y - 28, 28, 2)
    pygame.draw.circle(s, (60, 60, 72), (x + 118, y - 12), 8)
    pygame.draw.circle(s, (240, 80, 160), (x + 118, y - 12), 8, 1)
    pygame.draw.circle(s, (80, 200, 255), (x + 118, y - 12), 4, 1)
    for i, c in enumerate(((240, 80, 160), (80, 200, 255), (120, 240, 140))):
        box(s, c, x + 108, y + 2 + i * 4, 20, 1)
    box(s, (120, 240, 140), x + 127, y - 25, 2, 2)               # luzinha de ligado
    # caixinhas de som
    for cx in (x + 18, x + 100):
        box(s, (20, 20, 26), cx, y + 2, 7, 13)
        pygame.draw.circle(s, (60, 60, 70), (cx + 3, y + 10), 2)
        box(s, (80, 200, 255), cx + 2, y + 4, 2, 1)
    # teclado, mousepad com o mouse, caneca com fumacinha
    box(s, (40, 40, 48), x + 34, y + 18, 54, 9)
    for r in range(2):
        for i in range(8):
            box(s, (110, 110, 124), x + 36 + i * 6 + r * 2, y + 20 + r * 3, 4, 2)
    box(s, (30, 60, 110), x + 90, y + 17, 16, 11)
    box(s, (220, 220, 230), x + 96, y + 19, 5, 7)
    box(s, (170, 170, 180), x + 98, y + 19, 1, 3)
    box(s, (240, 240, 240), x + 6, y + 14, 10, 11)
    box(s, (240, 240, 240), x + 16, y + 17, 3, 5)
    box(s, (90, 50, 30), x + 7, y + 15, 8, 2)
    for k in range(3):
        box(s, (220, 220, 230, 110), x + 8 + (k % 2) * 3, y + 6 - k * 4, 2, 3)
    gamer_chair(s, x + 64, y + 46)


def gamer_chair(s, x, y):
    """Cadeira gamer do Cauanzera vista de trás, virada para o monitor (x, y = alto do encosto)."""
    D, D2 = (28, 28, 36), (46, 46, 58)
    shadow(s, x, y + 44, 40)
    for k in range(5):                                           # base de estrela com rodinhas
        ang = k * math.tau / 5 + 0.3
        ex, ey = x + round(math.cos(ang) * 16), y + 40 + round(math.sin(ang) * 5)
        pygame.draw.line(s, D2, (x, y + 40), (ex, ey), 2)
        box(s, D, ex - 2, ey, 4, 3)
    box(s, (110, 110, 120), x - 1, y + 28, 3, 12)                # pistão
    box(s, D, x - 15, y + 22, 30, 8)                             # assento aparecendo dos lados
    box(s, D2, x - 15, y + 22, 30, 2)
    box(s, D, x - 12, y - 4, 24, 28)                             # encosto
    box(s, CAU, x - 12, y - 4, 5, 28)                            # faixas azuis do Cauanzera
    box(s, CAU, x + 7, y - 4, 5, 28)
    box(s, shade(CAU, 40), x - 12, y - 4, 5, 2)
    box(s, shade(CAU, 40), x + 7, y - 4, 5, 2)
    box(s, D2, x - 5, y + 2, 10, 16)
    box(s, D, x - 8, y - 12, 16, 9)                              # cabeceira
    box(s, CAU, x - 6, y - 10, 12, 3)
    for side in (-1, 1):                                         # braços
        box(s, D2, x + side * 16 - 2, y + 12, 4, 12)
        box(s, D, x + side * 16 - 3, y + 10, 6, 3)


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
    """Armadura de enfeite feita com peças de um Uno branco (x, y = pé do suporte): o elmo é a cabine
    com o para-brisa e o bagageiro, o peito é a frente quadradona (faróis retangulares, grade
    com as listras da Fiat, para-choque preto e a placa UNO), os ombros são as rodas de ferro e as
    pernas, as lanternas traseiras em pé, do jeitinho do Uno."""
    W, W2, W3 = (244, 244, 240), (214, 214, 210), (186, 186, 184)
    D, D2 = (34, 34, 38), (58, 58, 64)
    GLASS, GLASS_L = (96, 146, 186), (176, 214, 238)
    shadow(s, x, y + 2, 72)
    # suporte com a plaquinha
    box(s, (70, 64, 78), x - 30, y - 8, 60, 10)
    box(s, (98, 90, 108), x - 30, y - 8, 60, 2)
    box(s, (40, 70, 150), x - 12, y - 6, 24, 7)
    box(s, (230, 230, 240), x - 9, y - 4, 18, 1)
    box(s, (120, 120, 126), x - 3, y - 22, 6, 14)
    # pernas: as lanternas traseiras do Uno, em pé (vermelho em cima, âmbar e a ré branca)
    for lx in (x - 18, x + 6):
        box(s, W2, lx - 1, y - 52, 14, 32)
        box(s, (200, 40, 40), lx + 2, y - 50, 8, 12)
        box(s, (240, 90, 80), lx + 3, y - 49, 3, 10)
        box(s, (236, 150, 40), lx + 2, y - 38, 8, 6)
        box(s, (236, 236, 236), lx + 2, y - 32, 8, 5)
        box(s, D, lx - 1, y - 24, 14, 4)                           # o pé: um pedaço de para-choque
    # peito: a frente do Uno
    box(s, W, x - 30, y - 96, 60, 46)
    box(s, (255, 255, 255), x - 30, y - 96, 60, 3)                 # quina do capô
    box(s, W2, x - 30, y - 90, 60, 2)
    for side in (-1, 1):
        hx = x + side * 15 - 9
        box(s, (150, 150, 156), hx - 1, y - 85, 20, 12)            # aro do farol
        box(s, (250, 246, 214), hx, y - 84, 18, 10)
        box(s, (255, 255, 240), hx + 2, y - 83, 6, 3)
        box(s, (230, 150, 40), x + side * 27 - 2, y - 84, 4, 10)   # pisca âmbar na quina
    box(s, D, x - 5, y - 85, 10, 12)                               # grade preta no meio...
    for i in range(5):                                             # ...com as cinco listras da Fiat
        pygame.draw.line(s, (200, 200, 210), (x - 4 + i * 2, y - 75), (x - 1 + i * 2, y - 84), 1)
    box(s, W2, x - 30, y - 71, 60, 3)
    box(s, D, x - 32, y - 66, 64, 10)                              # para-choque preto, bem grosso
    box(s, D2, x - 32, y - 66, 64, 2)
    box(s, (250, 250, 250), x - 11, y - 65, 22, 9)                 # placa com UNO
    box(s, (40, 70, 150), x - 11, y - 65, 22, 2)
    letters = ((-6, ((0, 0), (0, 1), (0, 2), (0, 3), (1, 4), (2, 0), (2, 1), (2, 2), (2, 3))),          # U
               (-2, ((0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (1, 1), (1, 2), (2, 2), (2, 3),
                     (3, 0), (3, 1), (3, 2), (3, 3), (3, 4))),                                          # N
               (3, ((1, 0), (0, 1), (0, 2), (0, 3), (1, 4), (2, 1), (2, 2), (2, 3))))                   # O
    for dx, pixels in letters:
        for px, py in pixels:
            box(s, D, x + dx + px, y - 62 + py, 1, 1)
    box(s, W3, x - 30, y - 56, 60, 6)                              # saia de baixo
    # ombros: para-lamas com as rodas de ferro (pretas, aro cinza e os furos)
    for side in (-1, 1):
        cx = x + side * 36
        box(s, W, cx - 9, y - 98, 18, 14)
        box(s, W2, cx - 9, y - 86, 18, 2)
        pygame.draw.circle(s, D, (cx, y - 82), 9)
        pygame.draw.circle(s, (140, 140, 148), (cx, y - 82), 5)
        pygame.draw.circle(s, (200, 200, 208), (cx, y - 82), 5, 1)
        for a in range(4):
            ang = a * math.tau / 4 + 0.6
            box(s, D2, cx + round(math.cos(ang) * 3), y - 82 + round(math.sin(ang) * 3), 1, 1)
        # braço: o retrovisor preto vira a manopla
        box(s, D, cx - 4, y - 72, 8, 12)
        box(s, (90, 120, 150), cx - 3, y - 71, 6, 4)
    # elmo: a cabine vista de frente, para-brisa de viseira e o bagageiro no teto
    pygame.draw.polygon(s, W, [(x - 22, y - 96), (x + 22, y - 96), (x + 17, y - 126), (x - 17, y - 126)])
    pygame.draw.polygon(s, GLASS, [(x - 18, y - 99), (x + 18, y - 99), (x + 14, y - 121), (x - 14, y - 121)])
    pygame.draw.polygon(s, GLASS_L, [(x - 12, y - 117), (x - 5, y - 117), (x - 11, y - 103), (x - 16, y - 103)])
    pygame.draw.line(s, D, (x - 2, y - 100), (x - 13, y - 106), 1)  # limpador de para-brisa
    box(s, W2, x - 17, y - 128, 34, 3)
    box(s, D, x - 19, y - 132, 38, 2)                              # barras do bagageiro
    box(s, D, x - 17, y - 132, 2, 5)
    box(s, D, x + 15, y - 132, 2, 5)
    for side in (-1, 1):                                           # retrovisores nas "orelhas"
        box(s, D, x + side * 24 - 3, y - 104, 6, 5)


# ── canto do Aryel ───────────────────────────
def moto(s, x, y, ground=True):
    """Moto esportiva do Aryel, de lado (x, y = chão entre as rodas), na cor dele. ``ground``: com a
    sombra no chão (sem ela, para empinar)."""
    m = pygame.Surface((132, 84), pygame.SRCALPHA)
    D, D2 = (26, 24, 30), (54, 52, 60)
    dark, light = shade(ARYEL, -46), shade(ARYEL, 40)
    for wx in (24, 106):                                         # rodas: pneu, disco e raios
        pygame.draw.circle(m, D, (wx, 64), 16)
        pygame.draw.circle(m, D2, (wx, 64), 16, 2)
        pygame.draw.circle(m, (150, 150, 160), (wx, 64), 9)
        pygame.draw.circle(m, (60, 60, 66), (wx, 64), 9, 1)
        for a in range(5):
            ang = a * math.tau / 5
            pygame.draw.line(m, (90, 90, 100), (wx, 64), (wx + round(math.cos(ang) * 8), 64 + round(math.sin(ang) * 8)), 1)
        pygame.draw.circle(m, (200, 200, 210), (wx, 64), 3)
    pygame.draw.line(m, METAL_D, (24, 64), (52, 52), 4)          # balança traseira
    box(m, (70, 70, 80), 46, 46, 30, 14)                         # motor
    for k in range(4):
        box(m, (110, 110, 120), 48 + k * 7, 48, 4, 10)
    pygame.draw.line(m, METAL, (34, 60), (64, 60), 3)            # escapamento cromado
    box(m, METAL, 12, 54, 26, 6)
    box(m, (220, 220, 230), 12, 54, 26, 2)
    box(m, D, 10, 54, 3, 6)
    pygame.draw.line(m, METAL_D, (106, 64), (94, 22), 4)         # garfo dianteiro
    pygame.draw.line(m, METAL, (104, 64), (92, 22), 1)
    # carenagem: rabeta, tanque e bico
    pygame.draw.polygon(m, ARYEL, [(14, 30), (40, 34), (58, 30), (76, 24), (98, 22), (112, 38), (100, 48),
                                   (76, 50), (56, 46), (40, 44), (20, 40)])
    pygame.draw.polygon(m, light, [(58, 30), (76, 24), (90, 23), (74, 30)])
    pygame.draw.polygon(m, dark, [(20, 40), (40, 44), (56, 46), (76, 50), (100, 48), (98, 52), (60, 52), (24, 44)])
    box(m, (240, 240, 240), 64, 38, 22, 3)                       # faixa branca
    box(m, (240, 240, 240), 70, 42, 14, 2)
    box(m, D, 30, 26, 26, 6)                                     # banco
    box(m, D2, 30, 26, 26, 2)
    box(m, (220, 50, 40), 12, 30, 5, 4)                          # lanterna
    pygame.draw.polygon(m, (130, 180, 220), [(92, 12), (100, 12), (106, 22), (96, 22)])   # bolha
    box(m, D, 86, 18, 14, 3)                                     # guidão
    box(m, (250, 240, 190), 106, 28, 8, 7)                       # farol
    box(m, (255, 255, 230), 108, 29, 3, 3)
    if ground:
        shadow(s, x, y + 4, 120)
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
    """Mesa do Albeguinio: o notebook aberto no modo hacker (texto verde), pilhas de papel, o
    carimbo, a caneca, o celular virado para baixo, os post-its e a cadeira de escritório."""
    shadow(s, x + 70, y + 50, 160)
    for lx in (x + 4, x + 130):
        box(s, METAL_D, lx, y + 26, 6, 26)
        box(s, METAL, lx, y + 26, 2, 26)
    box(s, (178, 168, 146), x, y + 10, 140, 14)                  # tampo de fórmica
    box(s, (206, 196, 176), x, y + 10, 140, 2)
    box(s, (140, 132, 116), x, y + 22, 140, 6)                   # frente
    # notebook: tampa aberta com o terminal, a base com o teclado e os post-its
    box(s, (34, 34, 42), x + 46, y - 22, 48, 32)
    box(s, (8, 16, 10), x + 49, y - 19, 42, 26)
    for i, (w, c) in enumerate(((18, (90, 230, 120)), (30, (90, 230, 120)), (12, (200, 240, 120)),
                                (26, (90, 230, 120)), (20, (240, 90, 90)), (8, (90, 230, 120)))):
        box(s, c, x + 51, y - 17 + i * 4, w, 2)
    box(s, (90, 230, 120), x + 60, y + 3, 3, 2)                  # cursor piscando
    box(s, (250, 230, 90), x + 92, y - 22, 6, 6)                 # post-its na tampa
    box(s, (250, 140, 180), x + 92, y - 14, 6, 6)
    pygame.draw.polygon(s, (60, 60, 72), [(x + 44, y + 10), (x + 96, y + 10), (x + 100, y + 18), (x + 40, y + 18)])
    for i in range(9):
        box(s, (100, 100, 116), x + 46 + i * 5, y + 12, 3, 2)
    box(s, (110, 110, 126), x + 64, y + 15, 12, 2)               # touchpad
    glow(s, (x + 70, y - 6), (70, 46), (90, 255, 140), 26)
    # papéis, carimbo, caneca, celular
    for k in range(3):
        for j in range(5 + k * 2):
            box(s, (240, 236, 224) if j % 2 else (222, 216, 200), x + 4 + k * 13, y + 10 - j * 2, 12, 2)
    box(s, (150, 30, 40), x + 104, y + 6, 12, 7)                 # carimbo e a almofada
    box(s, (60, 40, 30), x + 108, y - 2, 4, 8)
    box(s, (90, 60, 40), x + 106, y - 4, 8, 3)
    box(s, (60, 60, 120), x + 118, y + 14, 10, 4)
    box(s, (230, 230, 220), x + 126, y + 2, 9, 10)               # caneca do café
    box(s, (230, 230, 220), x + 135, y + 4, 3, 5)
    box(s, (90, 50, 30), x + 127, y + 3, 7, 2)
    box(s, (20, 20, 24), x + 104, y + 15, 12, 6)                 # celular virado para baixo
    box(s, (120, 200, 255), x + 106, y + 14, 8, 1)
    # cadeira de escritório, de costas
    cx, cy = x + 70, y + 40
    box(s, (40, 40, 50), cx - 12, cy, 24, 22)
    box(s, (64, 64, 78), cx - 12, cy, 24, 2)
    box(s, (52, 52, 64), cx - 4, cy + 6, 8, 12)
    box(s, (110, 110, 120), cx - 1, cy + 22, 3, 6)
    for dx in (-10, 0, 10):
        box(s, (34, 34, 40), cx + dx - 2, cy + 27, 4, 3)


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
    box(s, (236, 226, 200), x + 4, y + 24, 212, 34)              # frente de azulejo
    for tx in range(x + 4, x + 216, 12):
        box(s, (206, 194, 168), tx, y + 24, 1, 34)
    for ty in range(y + 24, y + 58, 12):
        box(s, (206, 194, 168), x + 4, ty, 212, 1)
    for tx in range(x + 10, x + 210, 24):                        # faixa de azulejo azul
        box(s, (70, 120, 180), tx, y + 37, 8, 8)
    box(s, WOOD_D, x + 4, y + 56, 212, 4)                        # rodapé
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
    """O Honda City cinza-escuro do João estacionado no quintal, de lado (x, y = chão no meio do carro)."""
    W, W2, D = (84, 88, 96), (62, 65, 72), (24, 24, 28)
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

