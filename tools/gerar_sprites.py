"""Gera os sprites pixel-art dos personagens que não têm arte desenhada à mão.

Uso:  python tools/gerar_sprites.py

Cria assets/characters/<nome>[n]<direção>.png (24x34 px, 4 quadros de caminhada
por direção). O jogo amplia sem suavizar, então cada pixel daqui vira um bloco.
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
    def __init__(self):
        self.surf = pygame.Surface((W, H), pygame.SRCALPHA)

    def rect(self, x, y, w, h, color):
        if w > 0 and h > 0:
            self.surf.fill(color, (x, y, w, h))

    def px(self, x, y, color):
        if 0 <= x < W and 0 <= y < H:
            self.surf.set_at((x, y), color)

    def erase(self, x, y, w=1, h=1):
        self.surf.fill((0, 0, 0, 0), (x, y, w, h))

    def finish(self):
        """Contorno escuro de 1 px em volta de tudo (o que dá a cara de pixel art)."""
        mask = pygame.mask.from_surface(self.surf)
        line = mask.to_surface(setcolor=OUTLINE, unsetcolor=(0, 0, 0, 0))
        out = pygame.Surface((W, H), pygame.SRCALPHA)
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


CHARACTERS = {
    "atirador": (atirador, False),
    "tanque": (tanque, True),
    "ninja": (ninja, False),
    "velocista": (velocista, False),
    "fantasma": (fantasma, False),
    "tita": (tita, True),
}
DIRECTIONS = ("frente", "costas", "direita")


def build(name):
    draw, wide = CHARACTERS[name]
    frames = {}
    for d in DIRECTIONS:
        frames[d] = [draw(Pose(d, f, wide)) for f in range(4)]
    frames["esquerda"] = [pygame.transform.flip(s, True, False) for s in frames["direita"]]
    return frames


def main():
    pygame.init()
    OUT.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1:] or list(CHARACTERS)
    for name in only:
        for direction, frames in build(name).items():
            for i, surf in enumerate(frames):
                suffix = "" if i == 0 else str(i)
                pygame.image.save(surf, str(OUT / f"{name}{suffix}{direction}.png"))
        print("ok", name)


if __name__ == "__main__":
    main()
