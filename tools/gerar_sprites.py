"""Gera os sprites pixel-art dos personagens que não têm arte desenhada à mão.

Uso:  python tools/gerar_sprites.py

Cria assets/characters/<nome>[n]<direção>.png (24x34 px, 4 quadros de caminhada
por direção), e também as criaturas da campanha (diabrete, esqueleto e golem). O jogo amplia sem suavizar, então cada pixel daqui vira um bloco.
Guerreiro e Aryel já têm arte própria e não são tocados.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "assets" / "characters"
W, H = 24, 34
OUTLINE = (24, 17, 28, 255)
EYE = (28, 22, 34)


class Canvas:
    def __init__(self, w=W, h=H):
        self.w, self.h = w, h
        self.surf = pygame.Surface((w, h), pygame.SRCALPHA)

    def rect(self, x, y, w, h, color):
        if w > 0 and h > 0:
            self.surf.fill(color, (x, y, w, h))

    def px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.surf.set_at((x, y), color)

    def erase(self, x, y, w=1, h=1):
        self.surf.fill((0, 0, 0, 0), (x, y, w, h))

    def finish(self):
        """Contorno escuro de 1 px em volta de tudo (o que dá a cara de pixel art)."""
        mask = pygame.mask.from_surface(self.surf)
        line = mask.to_surface(setcolor=OUTLINE, unsetcolor=(0, 0, 0, 0))
        out = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            out.blit(line, (dx, dy))
        out.blit(self.surf, (0, 0))
        return out


def shade(color, amount):
    return tuple(max(0, min(255, c + amount)) for c in color[:3])


class Pose:
    """Posição das partes do corpo para uma direção e um quadro de caminhada."""

    def __init__(self, direction, frame, wide=False):
        self.dir = direction
        self.frame = frame
        self.bob = -1 if frame in (1, 3) else 0
        b = self.bob
        self.head = (7, 5 + b, 10, 10)
        tw = 12 if wide else 8
        if direction == "direita":
            tw = 8 if wide else 6
        tx = 12 - tw // 2
        self.torso = (tx, 15 + b, tw, 8)
        self.belt = (tx, 23 + b, tw, 2)
        self.lift_left = frame == 1
        self.lift_right = frame == 3


# ── partes básicas ────────────────────────────

def legs(c, p, pants, boots, wide=False):
    b = p.bob
    top = 25 + b
    if p.dir == "direita":
        stride = {0: 0, 1: 2, 2: 0, 3: -2}[p.frame]
        far_x, near_x = 10 - stride, 10 + stride
        for x, col, lifted in ((far_x, shade(pants, -28), stride < 0), (near_x, pants, stride > 0)):
            c.rect(x, top, 3, 30 - top, col)
            by = 29 if lifted else 30
            c.rect(x, by, 4, 3, shade(boots, -20) if col != pants else boots)
            c.rect(x, by + 2, 4, 1, shade(boots, -40))
        return
    gap = 2 if not wide else 4
    lx, rx = 12 - gap // 2 - 3, 12 + gap // 2
    for x, lifted in ((lx, p.lift_left), (rx, p.lift_right)):
        bottom = 28 if lifted else 30
        c.rect(x, top, 3, bottom - top, pants)
        c.rect(x + 2, top, 1, bottom - top, shade(pants, -24))
        c.rect(x, bottom, 3, 3, boots)
        c.rect(x, bottom + 2, 3, 1, shade(boots, -40))


def torso(c, p, main, belt=None):
    x, y, w, h = p.torso
    c.rect(x, y, w, h, main)
    c.rect(x, y, 1, h, shade(main, 30))
    c.rect(x + w - 1, y, 1, h, shade(main, -36))
    c.rect(x, y + h - 1, w, 1, shade(main, -24))
    if belt:
        bx, by, bw, bh = p.belt
        c.rect(bx, by, bw, bh, belt)
        c.rect(bx, by + bh - 1, bw, 1, shade(belt, -30))


def arms(c, p, sleeve, hand, thick=2):
    x, y, w, h = p.torso
    if p.dir == "direita":
        swing = {0: 0, 1: -2, 2: 0, 3: 2}[p.frame]
        ax = 11 + swing
        c.rect(ax, y + 1, 2, 6, sleeve)
        c.rect(ax + 1, y + 1, 1, 6, shade(sleeve, -30))
        c.rect(ax, y + 7, 2, 2, hand)
        return
    lift_l = 1 if p.lift_right else 0
    lift_r = 1 if p.lift_left else 0
    for ax, dy in ((x - thick, lift_l), (x + w, lift_r)):
        c.rect(ax, y + 1 + dy, thick, 5, sleeve)
        c.rect(ax, y + 6 + dy, thick, 2, hand)
    c.rect(x - thick, y + 1 + lift_l, 1, 5, shade(sleeve, 24))
    c.rect(x + w + thick - 1, y + 1 + lift_r, 1, 5, shade(sleeve, -30))


def far_arm(c, p, sleeve, hand):
    """Braço de trás na vista lateral (desenhado antes do tronco)."""
    if p.dir != "direita":
        return
    x, y, w, h = p.torso
    swing = {0: 0, 1: 2, 2: 0, 3: -2}[p.frame]
    ax = 11 + swing
    c.rect(ax, y + 1, 2, 6, shade(sleeve, -40))
    c.rect(ax, y + 7, 2, 2, shade(hand, -40))


def head(c, p, skin):
    x, y, w, h = p.head
    c.rect(x, y, w, h, skin)
    c.rect(x, y + h - 1, w, 1, shade(skin, -30))
    c.rect(x + w - 1, y, 1, h, shade(skin, -18))
    for cx, cy in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):
        c.erase(cx, cy)


def eyes(c, p, color=EYE, glow=None):
    x, y, w, h = p.head
    ey = y + 5
    if p.dir == "frente":
        for ex in (x + 2, x + w - 3):
            c.rect(ex, ey, 1, 2, color)
            if glow:
                c.px(ex, ey, glow)
    elif p.dir == "direita":
        c.rect(x + w - 3, ey, 1, 2, color)
        if glow:
            c.px(x + w - 3, ey, glow)


def hair(c, p, color, style="short"):
    x, y, w, h = p.head
    hi = shade(color, 28)
    if p.dir == "costas":
        c.rect(x, y, w, h - 2, color)
        c.rect(x + 1, y + 1, w - 3, 1, hi)
        return
    c.rect(x, y, w, 3, color)
    c.rect(x + 1, y, w - 3, 1, hi)
    if p.dir == "frente":
        c.rect(x, y + 3, 1, 3, color)
        c.rect(x + w - 1, y + 3, 1, 3, color)
        if style == "spiky":
            for sx in range(x, x + w, 2):
                c.px(sx, y - 1, color)
    else:
        c.rect(x, y, 4, h - 3, color)
        if style == "spiky":
            for sx in range(x, x + w - 2, 2):
                c.px(sx, y - 1, color)
            c.px(x - 1, y + 2, color)


# ── personagens ──────────────────────────────

def atirador(p):
    c = Canvas()
    skin, hair_c = (234, 184, 142), (96, 60, 38)
    coat, pants, boots = (64, 152, 164), (66, 60, 78), (98, 62, 38)
    hat, band, scarf = (124, 82, 46), (64, 152, 164), (198, 70, 58)
    legs(c, p, pants, boots)
    far_arm(c, p, coat, skin)
    torso(c, p, coat, belt=(84, 54, 32))
    # cauda do casaco
    x, y, w, h = p.torso
    tail_y = y + h + 2
    if p.dir == "direita":
        c.rect(x - 1, tail_y - 2, 3, 4, shade(coat, -30))
    else:
        c.rect(x, tail_y, 2, 2, shade(coat, -10))
        c.rect(x + w - 2, tail_y, 2, 2, shade(coat, -40))
    arms(c, p, coat, skin)
    head(c, p, skin)
    hair(c, p, hair_c)
    eyes(c, p)
    # lenço
    if p.dir != "costas":
        c.rect(x + 1, y, w - 2, 2, scarf)
        c.px(x + 2, y, shade(scarf, 40))
    else:
        c.rect(x + 1, y, w - 2, 1, scarf)
    # chapéu de aba larga
    hx, hy, hw, hh = p.head
    c.rect(hx - 3, hy + 1, hw + 6, 2, hat)
    c.rect(hx - 3, hy + 2, hw + 6, 1, shade(hat, -30))
    c.rect(hx + 1, hy - 4, hw - 2, 5, hat)
    c.rect(hx + 2, hy - 4, hw - 5, 1, shade(hat, 30))
    c.rect(hx + 1, hy - 1, hw - 2, 1, band)
    return c.finish()


def tanque(p):
    c = Canvas()
    steel, steel_d = (150, 158, 172), (96, 102, 118)
    visor = (120, 232, 244)
    legs(c, p, steel_d, (64, 66, 78), wide=True)
    far_arm(c, p, steel, steel)
    torso(c, p, steel, belt=(80, 66, 52))
    x, y, w, h = p.torso
    if p.dir != "direita":
        c.rect(x + 2, y + 2, w - 4, 3, shade(steel, 20))   # placa do peito
        c.rect(x + 2, y + 4, w - 4, 1, steel_d)
    arms(c, p, steel_d, steel, thick=3)
    # ombreiras
    if p.dir == "direita":
        c.rect(x + 1, y - 1, 6, 4, steel)
        c.rect(x + 1, y + 2, 6, 1, steel_d)
    else:
        for sx in (x - 3, x + w - 2):
            c.rect(sx, y - 1, 5, 4, steel)
            c.rect(sx, y + 2, 5, 1, steel_d)
            c.px(sx + 1, y, shade(steel, 50))
    # elmo fechado
    hx, hy, hw, hh = p.head
    c.rect(hx, hy - 1, hw, hh + 1, steel)
    c.rect(hx + 1, hy - 1, hw - 3, 1, shade(steel, 40))
    c.rect(hx + hw - 1, hy, 1, hh, steel_d)
    c.rect(hx, hy + hh - 1, hw, 1, steel_d)
    if p.dir == "frente":
        c.rect(hx + 1, hy + 4, hw - 2, 2, (30, 34, 44))
        c.rect(hx + 2, hy + 4, hw - 4, 1, visor)
    elif p.dir == "direita":
        c.rect(hx + 5, hy + 4, 5, 2, (30, 34, 44))
        c.rect(hx + 6, hy + 4, 4, 1, visor)
    else:
        c.rect(hx + 4, hy, 2, hh - 2, steel_d)
    c.rect(hx + 4, hy - 3, 2, 2, (196, 64, 56))   # penacho
    return c.finish()


def ninja(p):
    c = Canvas()
    cloth, cloth_d = (46, 50, 60), (30, 32, 40)
    skin, sash, band = (232, 186, 146), (64, 168, 124), (204, 58, 58)
    legs(c, p, cloth, cloth_d)
    far_arm(c, p, cloth, cloth)
    torso(c, p, cloth, belt=sash)
    x, y, w, h = p.torso
    if p.dir == "frente":
        c.px(x + w // 2 - 1, y + 1, shade(cloth, 30))
        c.rect(x + w // 2 - 1, y + 2, 2, 4, shade(cloth, 18))
    arms(c, p, cloth, cloth_d)
    hx, hy, hw, hh = p.head
    head(c, p, cloth)
    # faixa de pele nos olhos
    if p.dir == "frente":
        c.rect(hx + 1, hy + 4, hw - 2, 3, skin)
    elif p.dir == "direita":
        c.rect(hx + 4, hy + 4, hw - 4, 3, skin)
    eyes(c, p)
    # faixa vermelha com pontas
    c.rect(hx, hy + 2, hw, 2, band)
    c.rect(hx, hy + 3, hw, 1, shade(band, -40))
    tail = {0: 0, 1: 1, 2: 0, 3: -1}[p.frame]
    if p.dir == "direita":
        c.rect(hx - 3, hy + 2 + tail, 3, 1, band)
        c.rect(hx - 5, hy + 3 - tail, 3, 1, band)
    elif p.dir == "costas":
        c.rect(hx + 4, hy + 4, 2, 3, band)
        c.rect(hx + 3 + tail, hy + 7, 2, 2, band)
    return c.finish()


def velocista(p):
    c = Canvas()
    skin, hair_c = (184, 124, 86), (34, 28, 30)
    jacket = (238, 200, 66)
    shorts, shoes = (46, 44, 66), (236, 236, 228)
    legs(c, p, skin, shoes)
    x, y, w, h = p.torso
    # bermuda
    c.rect(x, y + h, w, 3, shorts)
    far_arm(c, p, jacket, skin)
    torso(c, p, jacket)
    # raio no peito
    if p.dir == "frente":
        for i, (px_, py_) in enumerate(((4, 1), (3, 2), (2, 3), (3, 3), (4, 3), (3, 4), (2, 5))):
            c.px(x + px_ - 1, y + py_, (214, 64, 48))
    elif p.dir == "direita":
        c.rect(x, y + 3, w, 1, (214, 64, 48))
    else:
        c.rect(x + 1, y + 2, w - 2, 1, (214, 64, 48))
    arms(c, p, jacket, skin)
    head(c, p, skin)
    hair(c, p, hair_c, style="spiky")
    eyes(c, p)
    # óculos de corrida na testa
    hx, hy, hw, hh = p.head
    if p.dir != "costas":
        c.rect(hx, hy + 3, hw, 1, (60, 60, 70))
        if p.dir == "frente":
            c.rect(hx + 1, hy + 2, 3, 2, (120, 220, 240))
            c.rect(hx + hw - 4, hy + 2, 3, 2, (120, 220, 240))
        else:
            c.rect(hx + hw - 4, hy + 2, 3, 2, (120, 220, 240))
    else:
        c.rect(hx, hy + 3, hw, 1, (60, 60, 70))
    return c.finish()


def fantasma(p):
    c = Canvas()
    cloak, cloak_d, cloak_l = (128, 86, 188), (82, 50, 128), (176, 138, 232)
    void, glow = (20, 14, 32), (150, 244, 255)
    float_y = {0: 0, 1: -1, 2: -2, 3: -1}[p.frame]
    x, y, w, h = 7, 6 + float_y, 10, 22
    # manto com cauda ondulada
    c.rect(x + 1, y, w - 2, 1, cloak)
    c.rect(x, y + 1, w, h, cloak)
    c.rect(x - 1, y + 9, w + 2, h - 9, cloak)
    c.rect(x - 1, y + 9, 1, h - 9, cloak_l)
    c.rect(x + w, y + 9, 1, h - 9, cloak_d)
    c.rect(x + w - 2, y + 1, 2, h, cloak_d)
    c.rect(x + 1, y + 1, 1, 8, cloak_l)
    wave = p.frame % 2
    base = y + h + 1
    for i, tx in enumerate(range(x - 1, x + w + 1, 3)):
        drop = (i + wave) % 2
        c.rect(tx, base - 1, 2, 1 + drop, cloak if i % 2 else cloak_d)
    # capuz e rosto
    if p.dir == "frente":
        c.rect(x + 2, y + 3, w - 4, 6, void)
        c.rect(x + 3, y + 5, 1, 2, glow)
        c.rect(x + w - 4, y + 5, 1, 2, glow)
    elif p.dir == "direita":
        c.rect(x + 5, y + 3, w - 5, 6, void)
        c.rect(x + w - 2, y + 5, 1, 2, glow)
    else:
        c.rect(x + 4, y + 1, 2, 9, cloak_d)
    # mangas
    if p.dir == "direita":
        sw = {0: 0, 1: -1, 2: 0, 3: 1}[p.frame]
        c.rect(x + 4 + sw, y + 11, 3, 6, cloak_d)
        c.rect(x + 4 + sw, y + 17, 3, 1, (210, 200, 230))
    elif p.dir == "frente":
        c.rect(x - 2, y + 11, 2, 6, cloak_d)
        c.rect(x + w, y + 11, 2, 6, cloak_d)
        c.rect(x - 2, y + 17, 2, 1, (210, 200, 230))
        c.rect(x + w, y + 17, 2, 1, (210, 200, 230))
    return c.finish()


def tita(p):
    c = Canvas()
    gold, gold_d, gold_l = (220, 172, 66), (150, 108, 34), (255, 226, 132)
    cape, skin, beard = (164, 38, 42), (226, 170, 128), (118, 70, 40)
    x, y, w, h = p.torso
    # capa atrás do corpo
    if p.dir == "costas":
        pass
    elif p.dir == "direita":
        c.rect(x - 3, y, 4, 13, cape)
        c.rect(x - 3, y + 12, 3, 2, shade(cape, -30))
    else:
        c.rect(x - 1, y + 1, w + 2, 12, shade(cape, -30))
    legs(c, p, gold_d, (86, 58, 30), wide=True)
    far_arm(c, p, gold, skin)
    torso(c, p, gold, belt=(110, 74, 28))
    if p.dir == "frente":
        c.rect(x + 3, y + 2, w - 6, 1, gold_l)
        c.rect(x + 5, y + 3, 2, 3, gold_d)
    arms(c, p, gold_d, skin, thick=3)
    if p.dir == "costas":
        c.rect(x - 1, y, w + 2, 12, cape)
        c.rect(x, y, 1, 12, shade(cape, 30))
        c.rect(x - 1, y + 11, w + 2, 1, shade(cape, -40))
    # ombreiras grandes
    if p.dir == "direita":
        c.rect(x + 1, y - 1, 7, 4, gold)
        c.rect(x + 2, y - 1, 4, 1, gold_l)
    else:
        for sx in (x - 4, x + w - 1):
            c.rect(sx, y - 1, 5, 4, gold)
            c.rect(sx + 1, y - 1, 3, 1, gold_l)
            c.rect(sx, y + 2, 5, 1, gold_d)
    hx, hy, hw, hh = p.head
    head(c, p, skin)
    if p.dir == "costas":
        c.rect(hx, hy, hw, hh - 2, (96, 58, 34))
    else:
        eyes(c, p)
        # barba
        if p.dir == "frente":
            c.rect(hx + 1, hy + 7, hw - 2, 3, beard)
            c.rect(hx + 3, hy + 8, hw - 6, 1, shade(skin, -40))
        else:
            c.rect(hx + 4, hy + 7, hw - 4, 3, beard)
    # coroa
    c.rect(hx, hy, hw, 2, gold)
    c.rect(hx, hy + 1, hw, 1, gold_d)
    for sx in range(hx, hx + hw, 3):
        c.rect(sx, hy - 2, 1, 2, gold)
        c.px(sx, hy - 3, gold_l)
    if p.dir == "frente":
        c.px(hx + hw // 2, hy, (210, 50, 60))
    return c.finish()


def pirata(p):
    c = Canvas()
    skin, beard, hair_c = (226, 170, 128), (72, 42, 30), (60, 36, 28)
    coat, coat_d = (176, 48, 56), (118, 30, 40)
    shirt, gold = (236, 230, 214), (226, 180, 72)
    pants, boots = (52, 44, 58), (38, 30, 36)
    hat = (40, 32, 44)
    patch = (20, 16, 22)
    legs(c, p, pants, boots)
    x, y, w, h = p.torso
    # abas do casaco abaixo do cinto
    if p.dir == "direita":
        c.rect(x - 1, y + h, 4, 4, coat_d)
    elif p.dir == "frente":
        c.rect(x - 1, y + h, 3, 4, coat)
        c.rect(x + w - 2, y + h, 3, 4, coat_d)
    else:
        c.rect(x - 1, y + h, w + 2, 4, coat_d)
    far_arm(c, p, coat, skin)
    torso(c, p, coat, belt=(96, 60, 36))
    if p.dir == "frente":
        c.rect(x + 3, y, 2, 4, shirt)            # camisa aparecendo no decote
        c.px(x + 2, y, shirt)
        c.px(x + 5, y, shirt)
        c.px(x + 1, y + 5, gold)                 # botões
        c.px(x + w - 2, y + 5, gold)
        bx, by, bw, bh = p.belt
        c.rect(x + w // 2 - 1, by, 2, 2, gold)   # fivela
    elif p.dir == "direita":
        c.rect(x + w - 2, y, 2, 3, shirt)
    arms(c, p, coat, skin)
    head(c, p, skin)
    hx, hy, hw, hh = p.head
    if p.dir == "costas":
        c.rect(hx, hy + 1, hw, hh - 3, hair_c)
        c.rect(hx + 4, hy + hh - 2, 2, 3, hair_c)   # rabo de cavalo
        c.rect(hx + 4, hy + hh - 2, 2, 1, (176, 48, 56))
    else:
        eyes(c, p)
        if p.dir == "frente":
            c.rect(hx + 1, hy + 7, hw - 2, 3, beard)
            c.rect(hx + 3, hy + 7, hw - 6, 1, shade(skin, -45))
            c.rect(hx + 1, hy + 4, 3, 3, patch)  # tapa-olho
            c.rect(hx, hy + 3, hw, 1, patch)
        else:
            c.rect(hx + 4, hy + 7, hw - 4, 3, beard)
            c.rect(hx + hw - 4, hy + 4, 3, 3, patch)
            c.rect(hx, hy + 3, hw, 1, patch)
    # chapéu tricórnio com debrum dourado
    c.rect(hx - 2, hy, hw + 4, 2, hat)
    c.rect(hx - 2, hy + 1, hw + 4, 1, gold)
    c.rect(hx, hy - 3, hw, 3, hat)
    c.rect(hx + 1, hy - 3, hw - 3, 1, shade(hat, 34))
    if p.dir == "frente":
        c.px(hx - 3, hy - 1, hat)
        c.px(hx + hw + 2, hy - 1, hat)
        c.rect(hx + hw // 2 - 1, hy - 2, 2, 2, shirt)   # caveirinha
    elif p.dir == "direita":
        c.px(hx + hw + 2, hy - 1, hat)
    return c.finish()


def geada(p):
    c = Canvas()
    skin, hair_c = (236, 198, 178), (178, 210, 238)
    robe, robe_d, robe_l = (104, 164, 216), (62, 106, 160), (196, 230, 250)
    fur, ice, ice_l = (244, 248, 252), (150, 212, 240), (230, 248, 255)
    legs(c, p, robe_d, (210, 230, 244))
    x, y, w, h = p.torso
    far_arm(c, p, robe, skin)
    torso(c, p, robe, belt=robe_l)
    # saia longa do manto (os pés aparecem embaixo)
    sk = y + h
    c.rect(x - 1, sk, w + 2, 5, robe)
    if p.dir == "direita":
        c.rect(x + w, sk, 1, 5, robe_d)
    else:
        c.rect(x - 1, sk + 4, w + 2, 1, robe_d)
        c.rect(x - 1, sk, 1, 5, robe_l)
        if p.dir == "frente":
            c.rect(x + w // 2 - 1, sk, 2, 5, robe_l)
    arms(c, p, robe, skin)
    # gola de pele
    if p.dir == "direita":
        c.rect(x, y - 1, w + 1, 2, fur)
    else:
        c.rect(x - 1, y - 1, w + 2, 2, fur)
    head(c, p, skin)
    hx, hy, hw, hh = p.head
    hair(c, p, hair_c)
    if p.dir == "frente":
        c.rect(hx - 1, hy + 2, 2, 9, hair_c)       # cabelo comprido
        c.rect(hx + hw - 1, hy + 2, 2, 9, hair_c)
        c.px(hx - 1, hy + 10, shade(hair_c, -30))
        c.px(hx + hw, hy + 10, shade(hair_c, -30))
    elif p.dir == "direita":
        c.rect(hx - 1, hy + 2, 4, 10, hair_c)
        c.rect(hx - 1, hy + 11, 4, 1, shade(hair_c, -30))
    else:
        c.rect(hx, hy + hh - 3, hw, 6, hair_c)
        c.rect(hx + 1, hy + hh + 2, hw - 2, 1, shade(hair_c, -30))
    if p.dir != "costas":
        eyes(c, p, color=(40, 84, 150), glow=(200, 244, 255))
        if p.dir == "frente":
            c.px(hx + hw // 2 - 1, hy + 8, (196, 112, 116))     # boca
            c.px(hx + 2, hy + 7, shade(skin, -18))               # bochechas
            c.px(hx + hw - 3, hy + 7, shade(skin, -18))
        else:
            c.px(hx + hw - 3, hy + 8, (196, 112, 116))
    # tiara de pontas de gelo
    c.rect(hx + 1, hy, hw - 2, 1, ice)
    for sx, tall in ((hx + 2, 2), (hx + hw // 2 - 1, 3), (hx + hw - 3, 2)):
        if p.dir == "direita" and sx < hx + 3:
            continue
        c.rect(sx, hy - tall, 1, tall, ice)
        c.px(sx, hy - tall, ice_l)
    return c.finish()


# ── criaturas da campanha ─────────────────────

def diabrete(p):
    """Diabinho vermelho que voa baixo: chifres, asas de morcego e rabo de ponta."""
    c = Canvas(24, 28)
    red, red_d, red_l = (204, 64, 58), (140, 36, 40), (240, 112, 92)
    wing, wing_d = (112, 40, 64), (74, 24, 44)
    horn, eye, dark = (236, 220, 180), (255, 214, 80), (40, 16, 22)
    fly = {0: 0, 1: -1, 2: -2, 3: -1}[p.frame]
    up = p.frame in (1, 2)
    hx, hy = 8, 6 + fly
    bx, by = 9, 13 + fly

    def wing_poly(cx, side, front):
        tip_y = by - 6 if up else by + 4
        pts = [(cx, by + 1), (cx + side * 7, tip_y), (cx + side * 8, tip_y + 3), (cx + side * 4, by + 5)]
        pygame.draw.polygon(c.surf, wing if front else wing_d, pts)
        pygame.draw.line(c.surf, wing_d if front else (50, 16, 30), (cx, by + 1), (cx + side * 7, tip_y))

    def tail(x0, side):
        for i, (dx, dy) in enumerate(((0, 0), (side, 1), (side * 2, 1), (side * 3, 0), (side * 3, -1))):
            c.px(x0 + dx, by + 6 + dy, red_d)
        c.rect(x0 + side * 3 - (1 if side < 0 else 0), by + 3, 2, 2, red_d)

    if p.dir == "direita":
        wing_poly(bx + 1, -1, False)
        tail(bx, -1)
    elif p.dir == "frente":
        wing_poly(bx, -1, True)
        wing_poly(bx + 6, 1, True)
        tail(bx + 5, 1)
    # pernas curtas penduradas
    if p.dir == "direita":
        c.rect(bx + 1, by + 6, 2, 3, red_d)
        c.rect(bx + 3, by + 6, 2, 2, red_d)
    else:
        c.rect(bx, by + 6, 2, 3, red_d)
        c.rect(bx + 4, by + 6, 2, 3, red_d)
    # corpo
    w = 5 if p.dir == "direita" else 6
    c.rect(bx, by, w, 6, red)
    c.rect(bx, by, 1, 6, red_l)
    c.rect(bx + w - 1, by, 1, 6, red_d)
    if p.dir == "frente":
        c.rect(bx + 2, by + 2, 2, 3, red_l)              # barriga
        c.rect(bx - 1, by + 1, 1, 3, red_d)              # braços
        c.rect(bx + 6, by + 1, 1, 3, red_d)
    elif p.dir == "direita":
        c.rect(bx + 3, by + 1, 2, 2, red_d)              # braço na frente
    # cabeça
    c.rect(hx, hy, 8, 7, red)
    c.rect(hx, hy + 6, 8, 1, red_d)
    for cx, cy in ((hx, hy), (hx + 7, hy), (hx, hy + 6), (hx + 7, hy + 6)):
        c.erase(cx, cy)
    c.rect(hx + 1, hy, 5, 1, red_l)
    # chifres
    if p.dir == "direita":
        c.rect(hx + 4, hy - 2, 2, 2, horn)
        c.px(hx + 6, hy - 3, horn)
        c.px(hx + 1, hy - 1, horn)
        c.px(hx - 1, hy + 2, red)                        # orelha
    else:
        c.rect(hx, hy - 2, 2, 2, horn)
        c.px(hx - 1, hy - 3, horn)
        c.rect(hx + 6, hy - 2, 2, 2, horn)
        c.px(hx + 8, hy - 3, horn)
        c.px(hx - 1, hy + 2, red)
        c.px(hx + 8, hy + 2, red)
    if p.dir == "frente":
        for ex in (hx + 1, hx + 5):
            c.rect(ex, hy + 3, 2, 1, eye)
            c.px(ex + (1 if ex < hx + 4 else 0), hy + 3, dark)
        c.rect(hx + 2, hy + 5, 4, 1, dark)               # boca com presas
        c.px(hx + 2, hy + 5, horn)
        c.px(hx + 5, hy + 5, horn)
    elif p.dir == "direita":
        c.rect(hx + 5, hy + 3, 2, 1, eye)
        c.px(hx + 6, hy + 3, dark)
        c.rect(hx + 5, hy + 5, 3, 1, dark)
        c.px(hx + 6, hy + 5, horn)
    else:
        wing_poly(bx, -1, True)                          # de costas as asas ficam na frente
        wing_poly(bx + 6, 1, True)
        tail(bx + 2, 1)
    return c.finish()


def esqueleto(p):
    """Esqueleto arqueiro de capuz, com aljava nas costas e olhos acesos."""
    c = Canvas()
    bone, bone_d = (226, 220, 200), (162, 154, 136)
    cloth, cloth_d = (70, 52, 84), (44, 32, 56)
    socket, glow = (30, 22, 34), (255, 86, 70)
    quiver, feather = (110, 72, 44), (214, 64, 58)
    legs(c, p, bone_d, (86, 70, 60))
    x, y, w, h = p.torso
    far_arm(c, p, bone, bone)
    # tronco: costelas por cima de um pano escuro
    c.rect(x, y, w, h, cloth_d)
    if p.dir != "costas":
        for k in range(3):
            c.rect(x + 1, y + 1 + k * 2, w - 2, 1, bone)
        if p.dir == "frente":
            c.rect(x + w // 2 - 1, y, 2, h, bone_d)       # esterno
    else:
        c.rect(x + w // 2 - 1, y, 2, h, bone)             # coluna
        c.rect(x + 1, y - 2, 3, 9, quiver)                 # aljava
        c.px(x + 1, y - 3, feather)
        c.px(x + 3, y - 3, feather)
    c.rect(x, y + h - 1, w, 1, cloth)
    bx, by, bw, bh = p.belt
    c.rect(bx, by, bw, bh, cloth)
    if p.dir == "direita":
        c.rect(x - 2, y - 1, 2, 8, quiver)
        c.px(x - 2, y - 2, feather)
    arms(c, p, bone, bone)
    # caveira
    hx, hy, hw, hh = p.head
    head(c, p, bone)
    c.rect(hx, hy + hh - 2, hw, 1, bone_d)
    if p.dir == "frente":
        for ex in (hx + 1, hx + hw - 4):
            c.rect(ex, hy + 4, 3, 2, socket)
            c.px(ex + 1, hy + 4, glow)
        c.px(hx + hw // 2, hy + 6, socket)                # nariz
        for tx in range(hx + 2, hx + hw - 2, 2):          # dentes
            c.px(tx, hy + 8, socket)
    elif p.dir == "direita":
        c.rect(hx + hw - 4, hy + 4, 3, 2, socket)
        c.px(hx + hw - 3, hy + 4, glow)
        c.px(hx + hw - 1, hy + 6, socket)
        for tx in range(hx + 5, hx + hw, 2):
            c.px(tx, hy + 8, socket)
    # capuz
    if p.dir == "costas":
        c.rect(hx - 1, hy - 1, hw + 2, hh - 1, cloth)
        c.rect(hx, hy - 1, hw - 2, 1, shade(cloth, 26))
        c.rect(hx + 2, hy + hh - 3, hw - 4, 2, cloth_d)
    elif p.dir == "frente":
        c.rect(hx - 1, hy - 1, hw + 2, 3, cloth)
        c.rect(hx, hy - 1, hw - 2, 1, shade(cloth, 26))
        c.rect(hx - 1, hy + 2, 1, 7, cloth)
        c.rect(hx + hw, hy + 2, 1, 7, cloth_d)
    else:
        c.rect(hx - 1, hy - 1, hw, 3, cloth)
        c.rect(hx - 1, hy + 2, 5, 7, cloth)
        c.rect(hx, hy - 1, hw - 3, 1, shade(cloth, 26))
    return c.finish()


def golem(p):
    """Golem de pedra: ombros de rocha com musgo, punhos enormes e runas acesas."""
    c = Canvas(36, 40)
    stone, stone_d, stone_l = (132, 122, 108), (88, 80, 72), (170, 160, 142)
    moss, moss_d = (88, 128, 62), (60, 92, 44)
    glow, glow_d = (255, 160, 64), (200, 92, 40)
    b = -1 if p.frame in (1, 3) else 0
    lift_l, lift_r = p.frame == 1, p.frame == 3

    def block(x, y, w, h, base=stone):
        c.rect(x, y, w, h, base)
        c.rect(x, y, w, 1, shade(base, 34))
        c.rect(x, y, 1, h, shade(base, 18))
        c.rect(x + w - 1, y, 1, h, shade(base, -34))
        c.rect(x, y + h - 1, w, 1, shade(base, -40))

    if p.dir == "direita":
        stride = {0: 0, 1: 3, 2: 0, 3: -3}[p.frame]
        block(14 - stride, 30 + b, 7, 8, stone_d)          # perna de trás
        block(15 + stride, 30 + b, 7, 8)
        swing = {0: 0, 1: -2, 2: 0, 3: 2}[p.frame]
        block(11 + swing, 20 + b, 6, 9, stone_d)           # braço de trás
        block(11, 15 + b, 14, 16)                          # tronco
        c.rect(19, 21 + b, 4, 1, glow_d)
        c.rect(21, 22 + b, 1, 3, glow)
        block(14, 8 + b, 10, 9)                            # cabeça
        c.rect(21, 12 + b, 2, 2, glow)
        c.rect(14, 8 + b, 10, 2, moss)
        block(12, 13 + b, 9, 8, stone_l)                   # ombro
        c.rect(12, 13 + b, 9, 2, moss)
        c.rect(14, 12 + b, 3, 1, moss_d)
        block(15 - swing, 21 + b, 6, 10)                   # braço da frente
        block(14 - swing, 30 + b, 8, 7, stone_l)           # punho
        c.rect(16 - swing, 32 + b, 4, 1, stone_d)
        return c.finish()

    for x, lifted in ((10, lift_l), (20, lift_r)):
        block(x, (28 if lifted else 30) + b, 7, 8, stone_d)
    block(9, 15 + b, 18, 16)                               # tronco
    if p.dir == "frente":
        # runas acesas no peito
        c.rect(15, 19 + b, 6, 1, glow_d)
        c.rect(17, 19 + b, 2, 6, glow)
        c.rect(14, 23 + b, 8, 1, glow_d)
        c.px(17, 21 + b, (255, 236, 180))
    else:
        c.rect(12, 18 + b, 12, 3, moss_d)
        c.rect(14, 21 + b, 8, 2, moss)
    arm_l = 1 if lift_r else 0
    arm_r = 1 if lift_l else 0
    for x, dy in ((3, arm_l), (27, arm_r)):
        block(x, 21 + b + dy, 6, 11)
        block(x - 1, 31 + b + dy, 8, 7, stone_l)
        c.rect(x + 1, 33 + b + dy, 4, 1, stone_d)
    block(13, 8 + b, 10, 9)                                # cabeça encaixada nos ombros
    if p.dir == "frente":
        c.rect(15, 12 + b, 2, 2, glow)
        c.rect(19, 12 + b, 2, 2, glow)
        c.rect(16, 15 + b, 4, 1, stone_d)
    c.rect(13, 8 + b, 10, 2, moss)
    for x in (2, 25):                                      # ombros de rocha com musgo
        block(x, 13 + b, 9, 9, stone_l)
        c.rect(x, 13 + b, 9, 2, moss)
        c.rect(x + 2, 12 + b, 4, 1, moss_d)
        c.px(x + 3, 15 + b, moss_d)
    return c.finish()


CREATURES = {
    "diabrete": diabrete,
    "esqueleto": esqueleto,
    "golem": golem,
}

CHARACTERS = {
    "atirador": (atirador, False),
    "tanque": (tanque, True),
    "ninja": (ninja, False),
    "velocista": (velocista, False),
    "fantasma": (fantasma, False),
    "tita": (tita, True),
    "pirata": (pirata, False),
    "geada": (geada, False),
}
DIRECTIONS = ("frente", "costas", "direita")


def build(name):
    if name in CREATURES:
        draw, wide = CREATURES[name], False
    else:
        draw, wide = CHARACTERS[name]
    frames = {}
    for d in DIRECTIONS:
        frames[d] = [draw(Pose(d, f, wide)) for f in range(4)]
    frames["esquerda"] = [pygame.transform.flip(s, True, False) for s in frames["direita"]]
    return frames


def main():
    pygame.init()
    OUT.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1:] or list(CHARACTERS) + list(CREATURES)
    for name in only:
        for direction, frames in build(name).items():
            for i, surf in enumerate(frames):
                suffix = "" if i == 0 else str(i)
                pygame.image.save(surf, str(OUT / f"{name}{suffix}{direction}.png"))
        print("ok", name)


if __name__ == "__main__":
    main()
