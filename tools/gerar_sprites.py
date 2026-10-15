"""Gera as folhas de sprite pixel art de todos os personagens e criaturas.

Uso:  python tools/gerar_sprites.py [nome ...]

Cada personagem vira assets/characters/<nome>.png: uma folha com uma linha por
direção (frente, costas, direita, esquerda) e as colunas na ordem de SHEET_POSES
(andar 8, parado 2, ataque 3, dano 1, esquiva 1). Junto vai <nome>.json com o
tamanho do quadro, onde fica a mão que segura a arma em cada quadro e as cores
dos olhos (que acendem de vermelho nas almas corrompidas).
Os heróis também ganham o uniforme dos dois times do futebol, em
assets/characters/uniformes/<nome>_azul.png e <nome>_vermelho.png (só a roupa muda
de cor; o resto do desenho e o .json são os mesmos da folha normal).
O jogo amplia 2x sem suavizar, então cada pixel daqui vira um bloco.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame  # noqa: E402

from soulstrike.assets import SHEET_DIRECTIONS, SHEET_POSES  # noqa: E402

OUT = ROOT / "assets" / "characters"
W, H = 24, 34
EYE = (28, 22, 34)            # pupila (cor exata: é por ela que a sombra acha os olhos)
WHITE = (240, 238, 230)       # brilho do olho

# ── ciclos de animação ─────────────────────────
# caminhada em 8 quadros: contato, desce, passa, sobe (e o mesmo com a outra perna)
WALK_BOB = (0, 1, 0, -1, 0, 1, 0, -1)          # corpo sobe e desce
WALK_STRIDE = (2, 1, 0, -1, -2, -1, 0, 1)      # quanto a perna da esquerda/de trás está à frente
WALK_LIFT = (0, 1, 2, 1, 0, 0, 0, 0)           # pé da perna que está passando sai do chão
WALK_WAVE = (0, 1, 1, 1, 0, -1, -1, -1)        # capa, cabelo e rabo balançam atrás
WALK_FLOAT = (-1, -2, -2, -2, -1, 0, 0, 0)     # quem flutua sobe e desce devagar
ATTACK = ((-1, -1, 0), (1, 3, 0), (1, 2, 1))   # (inclina, alcance da mão, desce): prepara, golpe, fim

# uniformes do futebol: a cor base de cada tom (sombras, brilhos e contorno saem dela, como no resto)
KITS = {
    "azul": {"main": (48, 100, 220), "dark": (28, 58, 150), "light": (112, 158, 244)},
    "vermelho": {"main": (212, 54, 50), "dark": (140, 28, 34), "light": (246, 116, 100)},
}
KIT_DETAIL = (240, 238, 230)   # estampa/raio que sumiria no uniforme vira branco


class Canvas:
    def __init__(self, w=W, h=H):
        self.w, self.h = w, h
        self.surf = pygame.Surface((w, h), pygame.SRCALPHA)
        self.hand = None                          # centro da mão da arma (pixels da arte)

    def rect(self, x, y, w, h, color):
        if w > 0 and h > 0:
            self.surf.fill(color, (x, y, w, h))

    def px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.surf.set_at((x, y), color)

    def erase(self, x, y, w=1, h=1):
        self.surf.fill((0, 0, 0, 0), (x, y, w, h))

    def line(self, x0, y0, x1, y1, color, size=2):
        """Linha de pixels com pincel quadrado (braços dobrados, caudas)."""
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for i in range(steps + 1):
            x = x0 + round((x1 - x0) * i / steps)
            y = y0 + round((y1 - y0) * i / steps)
            self.rect(x, y, size, size, color)

    def finish(self):
        """Contorno de 1 px em volta do desenho, na cor escura do que está do lado
        (contorno "seletivo": a camisa rosa ganha borda vinho, o aço ganha borda chumbo)."""
        src = self.surf
        out = src.copy()
        get = src.get_at
        for y in range(self.h):
            for x in range(self.w):
                if get((x, y))[3]:
                    continue
                best = None
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if 0 <= nx < self.w and 0 <= ny < self.h:
                        col = get((nx, ny))
                        if col[3] and (best is None or sum(col[:3]) < sum(best[:3])):
                            best = col
                if best is not None:
                    out.set_at((x, y), (int(best[0] * 0.28) + 10, int(best[1] * 0.28) + 7,
                                        int(best[2] * 0.28) + 14, 255))
        return out


def shade(color, amount):
    return tuple(max(0, min(255, c + amount)) for c in color[:3])


def sign(v):
    return (v > 0) - (v < 0)


def uni(p, color, tone="main"):
    """Cor da roupa: a do uniforme do time quando a pose tem um (futebol), senão a do personagem."""
    return p.kit[tone] if p.kit else color


class Pose:
    """Posição das partes do corpo numa direção, num tipo de pose e num quadro."""

    def __init__(self, direction, kind, frame, wide=False, kit=None):
        self.dir, self.kind, self.frame = direction, kind, frame
        self.kit = kit                                 # cores do uniforme do time (futebol) ou None
        self.side = direction == "direita"
        self.wide = wide
        bob = lean = reach = stride = 0
        lift_a = lift_b = 0
        wave = floaty = 0
        hurt = dash = False
        if kind == "andar":
            bob, stride = WALK_BOB[frame], WALK_STRIDE[frame]
            lift_b, lift_a = WALK_LIFT[frame], WALK_LIFT[(frame + 4) % 8]
            wave, floaty = WALK_WAVE[frame], WALK_FLOAT[frame]
        elif kind == "parado":
            bob, floaty = frame, (-1, 0)[frame]
        elif kind == "ataque":
            lean, reach, bob = ATTACK[frame]
            stride, wave = (-1, 1, 1)[frame], (-1, 1, 1)[frame]
        elif kind == "dano":
            lean, reach, bob, wave, floaty = -1, -1, 1, -1, 1
            hurt = True
        elif kind == "esquiva":
            lean, bob, stride, wave = 2, 1, 3, -1
            dash = True
        self.bob, self.lean, self.reach, self.stride = bob, lean, reach, stride
        self.lift_a, self.lift_b = lift_a, lift_b          # a: perna da esquerda da imagem / de trás
        self.wave, self.float, self.hurt, self.dash = wave, floaty, hurt, dash
        # de frente/costas cada braço desce um pouco quando vai à frente
        self.arm_a = 1 if lift_b else 0
        self.arm_b = 1 if lift_a else 0
        if hurt:
            self.arm_a = -1                              # leva a mão livre para perto do corpo
        self.near_swing = sign(stride) if kind == "andar" else 0
        self.far_swing = -stride if kind in ("andar", "esquiva") else 0
        if dash:
            self.far_swing = -2
        self.head_dx = lean if self.side else 0
        self.torso_dx = int(lean / 2) if self.side else 0
        b = bob
        self.head = (7 + self.head_dx, 5 + b, 10, 10)
        tw = (8 if wide else 6) if self.side else (12 if wide else 8)
        tx = 12 - tw // 2 + self.torso_dx
        self.torso = (tx, 15 + b, tw, 8)
        self.belt = (tx, 23 + b, tw, 2)
        self.hip_x = tx + (tw - 3) // 2

    @property
    def reach_dy(self):
        """De frente a mão do golpe desce (vem para a câmera); de costas, sobe."""
        r = max(-1, min(2, self.reach))
        return r if self.dir == "frente" else -r


# ── partes básicas ────────────────────────────

def legs(c, p, pants, boots, wide=False):
    top = 25 + p.bob
    if p.side:
        for off, lift, col, bcol in ((p.stride, p.lift_a, shade(pants, -30), shade(boots, -26)),
                                     (-p.stride, p.lift_b, pants, boots)):
            bottom = 30 - lift
            n = bottom - top
            for i in range(n):
                x = p.hip_x + round(off * (i + 1) / n)
                c.rect(x, top + i, 3, 1, col)
                c.px(x, top + i, shade(col, -20))
            fx = p.hip_x + off
            c.rect(fx, bottom, 4, 2, bcol)
            c.px(fx + 3, bottom, shade(bcol, 22))
            c.rect(fx, bottom + 2, 4, 1, shade(bcol, -34))
        return
    gap = 4 if wide else 2
    spread = 1 if p.dash else 0
    lx, rx = 12 - gap // 2 - 3 - spread, 12 + gap // 2 + spread
    for x, lift in ((lx, p.lift_a), (rx, p.lift_b)):
        bottom = 30 - lift
        c.rect(x, top, 3, bottom - top, pants)
        c.rect(x + 2, top, 1, bottom - top, shade(pants, -24))
        c.px(x, top, shade(pants, 20))
        c.rect(x, bottom, 3, 2, boots)
        c.px(x, bottom, shade(boots, 26))
        c.rect(x, bottom + 2, 3, 1, shade(boots, -38))


def torso(c, p, main, belt=None, buckle=None):
    x, y, w, h = p.torso
    c.rect(x, y, w, h, main)
    c.rect(x, y, 1, h, shade(main, 28))
    c.rect(x + w - 1, y, 1, h, shade(main, -34))
    c.rect(x, y + h - 1, w, 1, shade(main, -22))
    if not p.side:
        c.px(x + w // 2 - 1, y + h - 3, shade(main, -16))     # dobra do pano
    if belt:
        bx, by, bw, bh = p.belt
        c.rect(bx, by, bw, bh, belt)
        c.rect(bx, by + bh - 1, bw, 1, shade(belt, -30))
        if buckle and p.dir == "frente":
            c.rect(bx + bw // 2 - 1, by, 2, 2, buckle)
            c.px(bx + bw // 2 - 1, by, shade(buckle, 40))
        elif buckle and p.side:
            c.rect(bx + bw - 2, by, 2, 2, buckle)


def arms(c, p, sleeve, hand, thick=2, cuff=None):
    """De frente e de costas: um braço de cada lado do tronco (o da direita da imagem segura a arma).
    De lado: só o braço da frente (o de trás é far_arm, desenhado antes do tronco)."""
    if p.side:
        near_arm(c, p, sleeve, hand, thick, cuff)
        return
    x, y, w, h = p.torso
    out = 1 if p.dash else 0
    for ax, dy, light, weapon in ((x - thick - out, p.arm_a, 24, False),
                                  (x + w + out, p.arm_b + p.reach_dy, -30, True)):
        length = max(2, 5 + dy)
        c.rect(ax, y + 1, thick, length, sleeve)
        edge = ax if light > 0 else ax + thick - 1
        c.rect(edge, y + 1, 1, length, shade(sleeve, light))
        c.rect(ax, y, thick, 1, shade(sleeve, 18))                 # ombro
        hy = y + 1 + length
        if cuff:
            c.rect(ax, hy - 1, thick, 1, cuff)
        c.rect(ax, hy, thick, 2, hand)
        c.px(ax + (0 if light > 0 else thick - 1), hy + 1, shade(hand, -30))
        if weapon:
            c.hand = (ax + thick / 2, hy + 1)


def near_arm(c, p, sleeve, hand, thick=2, cuff=None):
    """Braço da frente na vista de lado: dobrado, com a mão à frente do corpo (onde fica a arma)."""
    x, y, w, h = p.torso
    sx = x + w // 2 - 1
    reach = p.reach + p.near_swing
    hx = x + w - 1 + reach
    hy = y + 5 - (1 if p.reach >= 3 else 0) + (1 if p.hurt else 0)
    ex = sx + (1 if reach >= 0 else 0)
    c.line(sx, y + 1, ex, y + 3, sleeve, thick)
    c.line(ex, y + 3, hx, hy, sleeve, 2)
    c.rect(sx, y + 1, 1, 2, shade(sleeve, 24))
    if cuff:
        c.rect(hx - 1, hy, 1, 2, cuff)
    c.rect(hx, hy, 2, 2, hand)
    c.px(hx, hy + 1, shade(hand, -30))
    c.hand = (hx + 1, hy + 1)


def far_arm(c, p, sleeve, hand, thick=2):
    """Braço de trás na vista lateral (desenhado antes do tronco, mais escuro)."""
    if not p.side:
        return
    x, y, w, h = p.torso
    sx = x + w // 2 - 1
    c.line(sx, y + 1, sx + p.far_swing, y + 5, shade(sleeve, -40), thick)
    c.rect(sx + p.far_swing, y + 6, 2, 2, shade(hand, -40))


def head(c, p, skin, nose=True):
    x, y, w, h = p.head
    c.rect(x, y, w, h, skin)
    c.rect(x, y + h - 1, w, 1, shade(skin, -28))
    c.rect(x + w - 1, y + 1, 1, h - 2, shade(skin, -16))
    c.rect(x + 1, y + 1, 1, h - 3, shade(skin, 14))
    for cx, cy in ((x, y), (x + w - 1, y), (x, y + h - 1), (x + w - 1, y + h - 1)):
        c.erase(cx, cy)
    if p.side and nose:
        c.px(x + w, y + 6, skin)
        c.px(x + w, y + 7, shade(skin, -24))


def eyes(c, p, pupil=EYE, glint=WHITE):
    """Olhos 2x2 com brilho. Levando dano, fecham (um risco)."""
    x, y, w, h = p.head
    ey = y + 5
    spots = []
    if p.dir == "frente":
        spots = [x + 2, x + w - 4]
    elif p.side:
        spots = [x + w - 4]
    for ex in spots:
        if p.hurt:
            c.rect(ex, ey + 1, 2, 1, pupil)
            c.px(ex + (1 if ex < x + w // 2 else 0), ey, pupil)
        else:
            c.rect(ex, ey, 2, 2, pupil)
            c.px(ex, ey, glint)


def mouth(c, p, skin):
    x, y, w, h = p.head
    dark = shade(skin, -90)
    if p.dir == "frente":
        if p.hurt:
            c.rect(x + 4, y + 7, 2, 2, dark)
        else:
            c.rect(x + 4, y + 8, 2, 1, shade(skin, -60))
    elif p.side:
        c.px(x + w - 2, y + 8, dark if p.hurt else shade(skin, -60))


def blush(c, p, color):
    x, y, w, h = p.head
    if p.dir == "frente":
        c.px(x + 1, y + 7, color)
        c.px(x + w - 2, y + 7, color)
    elif p.side:
        c.px(x + w - 4, y + 7, color)


def hair(c, p, color, style="short"):
    x, y, w, h = p.head
    hi, lo = shade(color, 30), shade(color, -30)
    if p.dir == "costas":
        c.rect(x, y, w, h - 2, color)
        c.rect(x + 1, y + 1, w - 3, 1, hi)
        c.rect(x, y + h - 3, w, 1, lo)
        c.px(x + 3, y + 3, lo)
        c.px(x + 6, y + 4, lo)
    else:
        c.rect(x, y, w, 3, color)
        c.rect(x + 1, y, w - 3, 1, hi)
        if p.dir == "frente":
            c.rect(x, y + 3, 1, 3, color)
            c.rect(x + w - 1, y + 3, 1, 3, color)
            if style == "fringe":
                c.rect(x + 1, y + 3, 3, 1, color)
                c.px(x + 5, y + 3, color)
            c.px(x + 3, y + 2, lo)
            c.px(x + 7, y + 2, lo)
        else:
            c.rect(x, y, 4, h - 3, color)
            c.rect(x + 4, y + 3, 1, 1, color)
            c.px(x + 1, y + 4, lo)
    if style == "spiky":
        for sx in range(x, x + w, 2):
            c.px(sx, y - 1, color)
        if p.side:
            c.px(x - 1, y + 1, color)
            c.px(x - 1 - (1 if p.wave < 0 or p.dash else 0), y + 2, color)


# ── heróis ────────────────────────────────────

def guerreiro(p):
    """Cavaleiro de elmo fechado com viseira em T, tabardo azul e escudo."""
    c = Canvas()
    steel, steel_d, steel_l = (134, 140, 156), (86, 92, 110), (184, 190, 204)
    shine = (226, 230, 238)
    slit = (24, 24, 34)
    blue, blue_d, blue_l = uni(p, (54, 92, 196)), uni(p, (34, 58, 134), "dark"), uni(p, (96, 134, 226), "light")
    gold, leather, glove = (226, 184, 80), (102, 64, 38), (118, 76, 46)
    mail = (126, 130, 146)
    plume, plume_d = (236, 236, 242), (176, 178, 196)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head

    def shield(sx, sy, side=False):
        # escudo em formato de pipa: aro de aço, campo azul e um losango dourado
        rows = (6, 6, 6, 6, 6, 4, 2) if not side else (3, 3, 3, 3, 3, 2, 1)
        for i, n in enumerate(rows):
            off = (6 - n) // 2 if not side else 0
            c.rect(sx + off, sy + i, n, 1, steel)
        if not side:
            c.rect(sx + 1, sy + 1, 4, 4, blue_d)
            c.rect(sx + 2, sy + 5, 2, 1, blue_d)
            c.rect(sx + 2, sy + 2, 2, 2, gold)
            c.px(sx + 2, sy + 2, shade(gold, 40))
            c.rect(sx, sy, 6, 1, steel_l)
        else:
            c.rect(sx, sy, 3, 1, steel_l)
            c.rect(sx + 1, sy + 1, 1, 4, steel_d)

    if p.side:
        shield(x - 2, y + 1, side=True)                  # escudo nas costas
    legs(c, p, (86, 90, 106), (82, 54, 34))
    far_arm(c, p, mail, glove)
    # aba do tabardo abaixo do cinto
    if p.side:
        c.rect(x + 1 + min(0, p.wave), y + h + 2, 3, 3, blue_d)
    elif p.dir == "frente":
        c.rect(x + 2, y + h + 2, w - 4, 3, blue)
        c.rect(x + 2, y + h + 4, w - 4, 1, blue_d)
    torso(c, p, blue, belt=leather, buckle=gold)
    if p.dir == "frente":
        c.rect(x + 3, y + 2, 2, 3, gold)                 # emblema
        c.px(x + 3, y + 2, shade(gold, 40))
        c.rect(x + 1, y, w - 2, 1, mail)                 # cota de malha no pescoço
    elif p.dir == "costas":
        c.rect(x - 1, y, w + 2, h + 3, blue)             # capa curta
        c.rect(x - 1, y, 1, h + 3, blue_l)
        c.rect(x + w, y, 1, h + 3, blue_d)
        c.rect(x - 1, y + h + 2, w + 2, 1, blue_d)
        c.px(x + 2 + p.wave, y + h + 2, blue)
        c.rect(x + 3, y + 2, 2, 6, blue_d)
    arms(c, p, mail, glove, cuff=leather)
    # ombreiras
    if p.side:
        c.rect(x + 1, y - 1, 4, 3, steel)
        c.rect(x + 1, y - 1, 4, 1, steel_l)
    else:
        for sx in (x - 3, x + w):
            c.rect(sx, y - 1, 3, 3, steel)
            c.rect(sx, y - 1, 3, 1, steel_l)
            c.px(sx + (2 if sx < x else 0), y + 1, steel_d)
    if p.dir == "frente":
        shield(x - 7 - (1 if p.dash else 0), y + 1 + p.arm_a)
    elif p.dir == "costas":
        shield(x - 7 - (1 if p.dash else 0), y + 1 + p.arm_a)
    # elmo: cúpula com brilho em cima, faixa escura na testa e viseira em T
    c.rect(hx, hy - 1, hw, hh + 1, steel)
    c.rect(hx + 1, hy - 1, hw - 3, 2, steel_l)
    c.rect(hx + 2, hy - 1, 2, 1, shine)
    c.rect(hx, hy, 1, hh - 2, steel_l)
    c.rect(hx + hw - 2, hy + 1, 2, hh - 1, steel_d)
    c.rect(hx, hy + hh - 1, hw, 1, steel_d)
    c.rect(hx, hy + 3, hw, 1, steel_d)
    c.erase(hx, hy - 1)
    c.erase(hx + hw - 1, hy - 1)
    if p.dir == "frente":
        c.rect(hx + 4, hy - 1, 2, 4, steel_l)            # crista do elmo
        c.px(hx + 4, hy - 1, shine)
        c.rect(hx + 1, hy + 4, hw - 2, 2, slit)          # viseira em T
        c.rect(hx + 4, hy + 6, 2, 2, slit)
        c.rect(hx + 1, hy + 4, hw - 2, 1, shade(slit, 10))
        if not p.hurt:
            c.px(hx + 2, hy + 5, EYE)
            c.px(hx + 7, hy + 5, EYE)
        c.rect(hx + 1, hy + 6, 2, 2, steel)              # bochechas
        c.rect(hx + hw - 3, hy + 6, 2, 2, steel_d)
        for rx in (hx + 1, hx + hw - 2):
            c.px(rx, hy + 8, shine)                      # rebites
    elif p.side:
        c.rect(hx + 5, hy + 4, 5, 2, slit)
        c.rect(hx + 8, hy + 6, 2, 1, slit)
        c.px(hx + 9, hy + 7, slit)
        if not p.hurt:
            c.px(hx + 8, hy + 5, EYE)
        c.rect(hx + 3, hy - 1, 2, 4, steel_l)
        c.px(hx + 3, hy - 1, shine)
        c.px(hx + 2, hy + 7, shine)
        c.rect(hx, hy + 4, 4, 1, steel_d)
    else:
        c.rect(hx + 4, hy - 1, 2, hh - 1, steel_d)
        c.rect(hx + 4, hy - 1, 1, 3, steel_l)
        c.rect(hx + 1, hy + hh - 3, hw - 2, 1, steel_d)
    # penacho
    if p.side:
        tail = -1 if p.wave < 0 or p.dash else 0
        c.rect(hx + 3, hy - 4, 2, 3, plume)
        c.rect(hx + 1 + tail, hy - 3, 2, 2, plume)
        c.px(hx + tail, hy - 1 + (1 if p.wave > 0 else 0), plume_d)
        c.px(hx + 4, hy - 4, (255, 255, 255))
    else:
        c.rect(hx + 4, hy - 4, 2, 3, plume)
        c.px(hx + 4, hy - 4, (255, 255, 255))
        c.px(hx + 5, hy - 2, plume_d)
        if p.dir == "costas":
            c.rect(hx + 4, hy - 2, 2, 3, plume)
            c.px(hx + 5, hy, plume_d)
    return c


def aryel(p):
    """Aryel: cabelo castanho bagunçado, óculos, camisa rosa com estampa azul, calça bege."""
    c = Canvas()
    skin = (238, 190, 150)
    hair_c, hair_d, hair_l = (112, 68, 42), (78, 46, 30), (152, 98, 62)
    shirt, shirt_d, shirt_l = uni(p, (236, 150, 172)), uni(p, (198, 108, 138), "dark"), uni(p, (250, 190, 204), "light")
    print_c = KIT_DETAIL if p.kit else (78, 118, 184)
    pants, shoes = (226, 212, 172), (118, 72, 42)
    frame, lens, lens_l = (48, 40, 50), (176, 206, 228), (226, 240, 250)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    legs(c, p, pants, shoes)
    far_arm(c, p, shirt, skin)
    torso(c, p, shirt)
    c.rect(x, y + h - 1, w, 1, shirt_d)
    if p.dir == "frente":
        c.rect(x + 1, y + 2, 2, 2, print_c)              # estampa
        c.rect(x + 4, y + 2, 2, 1, print_c)
        c.px(x + 5, y + 3, print_c)
        c.px(x + 1, y + 2, shade(print_c, 40))
        c.rect(x + 2, y, w - 4, 1, shirt_l)              # gola
        c.px(x + w // 2 - 1, y, shade(skin, -10))
        c.px(x + w // 2, y, shade(skin, -10))
    elif p.side:
        c.rect(x + w - 3, y + 2, 2, 2, print_c)
        c.rect(x + 1, y, w - 2, 1, shirt_l)
    else:
        c.rect(x + 1, y, w - 2, 1, shirt_l)
        c.px(x + 2, y + 4, shirt_d)
        c.px(x + w - 3, y + 3, shirt_d)
    # barra da camisa por cima da calça
    c.rect(x, y + h, w, 1, shirt_d)
    arms(c, p, shirt, skin)
    head(c, p, skin)
    # cabelo bagunçado com volume
    if p.dir == "costas":
        c.rect(hx - 1, hy - 1, hw + 2, hh - 1, hair_c)
        c.rect(hx, hy - 2, hw - 2, 1, hair_c)
        c.rect(hx + 1, hy - 1, hw - 4, 1, hair_l)
        c.rect(hx + 2, hy + 1, 3, 1, hair_l)
        c.px(hx + 6, hy + 2, hair_l)
        c.rect(hx, hy + hh - 3, hw, 1, hair_d)
        c.px(hx + 3, hy + 4, hair_d)
        c.px(hx + 7, hy + 5, hair_d)
        for tx in (hx, hx + 3, hx + 6, hx + 9):
            c.px(tx, hy + hh - 2, hair_d)                # pontas na nuca
    elif p.side:
        c.rect(hx - 1, hy - 1, hw - 1, 4, hair_c)
        c.rect(hx - 1, hy + 3, 5, 5, hair_c)
        c.rect(hx, hy - 2, hw - 3, 1, hair_c)
        c.rect(hx + 1, hy - 1, hw - 5, 1, hair_l)
        c.px(hx + hw - 2, hy, hair_c)                    # franja na testa
        c.px(hx + hw - 2, hy + 1, hair_c)
        c.px(hx + hw - 3, hy + 2, hair_c)
        c.px(hx - 2 - (1 if p.wave < 0 or p.dash else 0), hy + 1, hair_c)
        c.px(hx - 2, hy + 4, hair_d)
        c.rect(hx + 1, hy + 4, 2, 1, hair_d)
        c.px(hx + 4, hy + 5, shade(skin, -26))           # orelha
    else:
        c.rect(hx - 1, hy - 1, hw + 2, 4, hair_c)
        c.rect(hx, hy - 2, hw - 2, 1, hair_c)
        c.rect(hx + 1, hy - 1, hw - 4, 1, hair_l)
        c.px(hx + 2, hy - 2, hair_l)
        c.rect(hx - 1, hy + 3, 2, 4, hair_c)             # costeletas
        c.rect(hx + hw - 1, hy + 3, 2, 4, hair_c)
        c.rect(hx + 1, hy + 3, 3, 1, hair_c)             # franja jogada de lado
        c.px(hx + 4, hy + 3, hair_d)
        c.px(hx + 7, hy + 3, hair_c)
        c.px(hx + 3, hy + 2, hair_d)
        c.px(hx + 6, hy + 1, hair_d)
    # óculos
    if p.dir == "frente":
        c.rect(hx + 1, hy + 4, hw - 2, 1, frame)
        for lx in (hx + 1, hx + hw - 4):
            c.rect(lx, hy + 5, 3, 2, lens)
            c.px(lx, hy + 5, lens_l)
            if p.hurt:
                c.rect(lx, hy + 6, 3, 1, EYE)
            else:
                c.rect(lx + 1, hy + 5, 1, 2, EYE)
        c.rect(hx + 1, hy + 7, 3, 1, frame)
        c.rect(hx + hw - 4, hy + 7, 3, 1, frame)
        c.px(hx, hy + 5, frame)
        c.px(hx + hw - 1, hy + 5, frame)
        if p.hurt:
            mouth(c, p, skin)
        else:
            c.rect(hx + 4, hy + 8, 2, 1, shade(skin, -60))   # sorriso
        blush(c, p, (236, 150, 140))
    elif p.side:
        c.rect(hx + 5, hy + 4, 5, 1, frame)
        c.rect(hx + 6, hy + 5, 3, 2, lens)
        c.px(hx + 6, hy + 5, lens_l)
        c.px(hx + 7, hy + 6, EYE)
        c.rect(hx + 6, hy + 7, 3, 1, frame)
        c.rect(hx + 3, hy + 4, 2, 1, frame)              # haste até a orelha
        mouth(c, p, skin)
        blush(c, p, (236, 150, 140))
    return c


def atirador(p):
    c = Canvas()
    skin, hair_c = (234, 184, 142), (96, 60, 38)
    coat, pants, boots = uni(p, (64, 152, 164)), (66, 60, 78), (98, 62, 38)
    hat, band, scarf = (124, 82, 46), (44, 116, 128), (198, 70, 58)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    legs(c, p, pants, boots)
    far_arm(c, p, coat, skin)
    # cauda do casaco (balança atrás ao andar)
    if p.side:
        back = 1 if p.wave < 0 or p.dash else 0
        c.rect(x - 1 - back, y + h, 3, 4 - back, shade(coat, -30))
        c.px(x - 1 - back, y + h + 3 - back, shade(coat, -50))
    else:
        c.rect(x, y + h + 2, 2, 2, shade(coat, -10))
        c.rect(x + w - 2, y + h + 2, 2, 2, shade(coat, -40))
    torso(c, p, coat, belt=(84, 54, 32), buckle=(206, 170, 90))
    if p.dir == "frente":
        c.rect(x + w // 2, y + 1, 1, h - 2, shade(coat, -28))   # abertura do casaco
        c.rect(x + w - 1, y + h, 1, 3, (84, 54, 32))             # coldre
    elif p.side:
        c.rect(x + 1, y + h, 2, 3, (84, 54, 32))
    arms(c, p, coat, skin, cuff=shade(coat, -36))
    head(c, p, skin)
    hair(c, p, hair_c)
    eyes(c, p)
    mouth(c, p, skin)
    # lenço
    if p.dir != "costas":
        c.rect(x + 1, y, w - 2, 2, scarf)
        c.px(x + 2, y, shade(scarf, 40))
        if p.dir == "frente":
            c.rect(x + 3, y + 2, 2, 1, scarf)
    else:
        c.rect(x + 1, y, w - 2, 1, scarf)
        c.rect(x + 3 + p.wave, y + 1, 2, 2, shade(scarf, -20))  # ponta do lenço
    # chapéu de aba larga
    c.rect(hx - 3, hy + 1, hw + 6, 2, hat)
    c.rect(hx - 3, hy + 2, hw + 6, 1, shade(hat, -30))
    c.px(hx - 3, hy + 1, shade(hat, 26))
    c.rect(hx + 1, hy - 4, hw - 2, 5, hat)
    c.rect(hx + 2, hy - 4, hw - 5, 1, shade(hat, 30))
    c.rect(hx + 1, hy - 1, hw - 2, 1, band)
    c.px(hx + 4, hy - 3, shade(hat, -26))                        # amassado no topo
    c.px(hx + 5, hy - 3, shade(hat, -26))
    return c


def tanque(p):
    c = Canvas()
    steel, steel_d, steel_l = (150, 158, 172), (96, 102, 118), (196, 204, 216)
    plate, plate_d, plate_l = uni(p, steel), uni(p, steel_d, "dark"), uni(p, steel_l, "light")   # peitoral e mangas
    visor = (120, 232, 244)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    legs(c, p, steel_d, (64, 66, 78), wide=True)
    far_arm(c, p, plate, steel, thick=3)
    torso(c, p, plate, belt=(80, 66, 52), buckle=(196, 160, 90))
    if not p.side:
        c.rect(x + 2, y + 2, w - 4, 3, shade(plate, 20))         # placa do peito
        c.rect(x + 2, y + 4, w - 4, 1, plate_d)
        c.rect(x + w // 2 - 1, y + 2, 2, 2, plate_l if p.dir == "frente" else plate_d)
    else:
        c.rect(x + w - 3, y + 2, 2, 3, shade(plate, 20))
    arms(c, p, plate_d, steel, thick=3)
    # ombreiras
    if p.side:
        c.rect(x + 1, y - 1, 6, 4, steel)
        c.rect(x + 1, y - 1, 6, 1, steel_l)
        c.rect(x + 1, y + 2, 6, 1, steel_d)
    else:
        for sx in (x - 3, x + w - 2):
            c.rect(sx, y - 1, 5, 4, steel)
            c.rect(sx, y - 1, 5, 1, steel_l)
            c.rect(sx, y + 2, 5, 1, steel_d)
            c.px(sx + 2, y, (255, 255, 255))
    # elmo fechado
    c.rect(hx, hy - 1, hw, hh + 1, steel)
    c.rect(hx + 1, hy - 1, hw - 3, 1, steel_l)
    c.rect(hx, hy, 1, hh - 1, steel_l)
    c.rect(hx + hw - 1, hy, 1, hh, steel_d)
    c.rect(hx, hy + hh - 1, hw, 1, steel_d)
    if p.dir == "frente":
        c.rect(hx + 1, hy + 4, hw - 2, 2, (30, 34, 44))
        c.rect(hx + 2, hy + 4, hw - 4, 1, visor)
        c.px(hx + 2, hy + 4, (220, 252, 255))
        for gx in range(hx + 2, hx + hw - 2, 2):
            c.px(gx, hy + 7, steel_d)                            # grade da boca
    elif p.side:
        c.rect(hx + 5, hy + 4, 5, 2, (30, 34, 44))
        c.rect(hx + 6, hy + 4, 4, 1, visor)
        c.px(hx + 9, hy + 4, (220, 252, 255))
        c.px(hx + 3, hy + 5, steel_l)
    else:
        c.rect(hx + 4, hy, 2, hh - 2, steel_d)
    # penacho vermelho (balança)
    plume = (196, 64, 56)
    if p.side:
        back = -1 if p.wave < 0 or p.dash else 0
        c.rect(hx + 4, hy - 3, 2, 2, plume)
        c.rect(hx + 2 + back, hy - 2, 2, 1, shade(plume, -30))
    else:
        c.rect(hx + 4, hy - 3, 2, 2, plume)
        c.px(hx + 4, hy - 3, shade(plume, 40))
    return c


def ninja(p):
    c = Canvas()
    cloth, cloth_d = (46, 50, 60), (30, 32, 40)
    skin, sash, band = (232, 186, 146), (64, 168, 124), (204, 58, 58)
    top = uni(p, cloth)                                          # parte de cima da roupa
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    legs(c, p, cloth, cloth_d)
    far_arm(c, p, top, cloth)
    torso(c, p, top, belt=sash)
    if p.dir == "frente":
        c.rect(x + 2, y + 1, 1, 4, shade(top, 24))               # gola cruzada
        c.rect(x + 3, y + 3, 1, 2, shade(top, 24))
        c.rect(x + w - 3, y + 1, 1, 4, shade(top, -12))
    elif p.side:
        c.rect(x + w - 2, y + 1, 1, 4, shade(top, 24))
    if p.dir in ("frente", "costas"):
        bx, by, bw, bh = p.belt
        c.rect(bx + bw - 2, by + 1, 2, 3, sash)                 # ponta da faixa
    arms(c, p, top, cloth_d, cuff=(80, 86, 98))
    head(c, p, cloth, nose=False)
    # faixa de pele nos olhos
    if p.dir == "frente":
        c.rect(hx + 1, hy + 4, hw - 2, 3, skin)
    elif p.side:
        c.rect(hx + 4, hy + 4, hw - 4, 3, skin)
    eyes(c, p)
    # faixa vermelha com pontas (balançam)
    c.rect(hx, hy + 2, hw, 2, band)
    c.rect(hx, hy + 3, hw, 1, shade(band, -40))
    c.px(hx + 1, hy + 2, shade(band, 40))
    t = p.wave
    if p.side:
        back = 1 if p.dash else 0
        c.line(hx - 1, hy + 2, hx - 3 - back, hy + 2 + t, band, 1)
        c.line(hx - 1, hy + 3, hx - 5 - back, hy + 4 - t, shade(band, -20), 1)
    elif p.dir == "costas":
        c.rect(hx + 4, hy + 4, 2, 3, band)
        c.rect(hx + 3 + t, hy + 7, 2, 2, band)
    return c


def velocista(p):
    c = Canvas()
    skin, hair_c = (184, 124, 86), (34, 28, 30)
    jacket = uni(p, (238, 200, 66))
    shorts, shoes = (46, 44, 66), (236, 236, 228)
    bolt = KIT_DETAIL if p.kit else (214, 64, 48)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    legs(c, p, skin, shoes)
    c.rect(x, y + h, w, 3, shorts)                               # bermuda
    c.rect(x, y + h + 2, w, 1, shade(shorts, -20))
    if p.side:
        c.rect(x + w - 2, y + h, 1, 3, bolt)
    else:
        c.rect(x, y + h, 1, 3, bolt)
        c.rect(x + w - 1, y + h, 1, 3, bolt)
    far_arm(c, p, jacket, skin)
    torso(c, p, jacket)
    if p.dir == "frente":
        for px_, py_ in ((4, 1), (3, 2), (2, 3), (3, 3), (4, 3), (3, 4), (2, 5)):
            c.px(x + px_ - 1, y + py_, bolt)
        c.rect(x + w - 2, y, 1, h - 1, shade(jacket, -40))       # zíper
    elif p.side:
        c.rect(x, y + 3, w, 1, bolt)
    else:
        c.rect(x + 1, y + 2, w - 2, 1, bolt)
        c.rect(x + 3, y + 3, 2, 1, bolt)
    arms(c, p, jacket, skin, cuff=bolt)
    head(c, p, skin)
    hair(c, p, hair_c, style="spiky")
    eyes(c, p)
    mouth(c, p, skin)
    # óculos de corrida na testa
    goggle = (120, 220, 240)
    c.rect(hx, hy + 3, hw, 1, (60, 60, 70))
    if p.dir == "frente":
        c.rect(hx + 1, hy + 2, 3, 2, goggle)
        c.rect(hx + hw - 4, hy + 2, 3, 2, goggle)
        c.px(hx + 1, hy + 2, (230, 250, 255))
        c.px(hx + hw - 4, hy + 2, (230, 250, 255))
    elif p.side:
        c.rect(hx + hw - 4, hy + 2, 3, 2, goggle)
        c.px(hx + hw - 4, hy + 2, (230, 250, 255))
    return c


def fantasma(p):
    c = Canvas()
    cloak, cloak_d, cloak_l = uni(p, (128, 86, 188)), uni(p, (82, 50, 128), "dark"), uni(p, (176, 138, 232), "light")
    void, glow = (20, 14, 32), (150, 244, 255)
    hand = (210, 200, 230)
    fy = p.float + (1 if p.hurt else 0)
    x, y, w, h = 7 + p.head_dx, 6 + fy, 10, 22
    # manto com cauda ondulada
    c.rect(x + 1, y, w - 2, 1, cloak)
    c.rect(x, y + 1, w, h, cloak)
    c.rect(x - 1, y + 9, w + 2, h - 9, cloak)
    c.rect(x - 1, y + 9, 1, h - 9, cloak_l)
    c.rect(x + w, y + 9, 1, h - 9, cloak_d)
    c.rect(x + w - 2, y + 1, 2, h, cloak_d)
    c.rect(x + 1, y + 1, 1, 8, cloak_l)
    c.rect(x + 2, y + 12, 1, 6, cloak_d)                         # dobras do manto
    c.rect(x + 6, y + 13, 1, 5, cloak_d)
    phase = p.frame if p.kind == "andar" else (p.frame + 1) * 2
    base = y + h + 1
    for i, tx in enumerate(range(x - 1, x + w + 1, 3)):
        drop = ((i + phase // 2) % 2)
        c.rect(tx, base - 1, 2, 1 + drop, cloak if i % 2 else cloak_d)
    if p.side:
        tail = 1 if p.wave < 0 or p.dash else 0
        c.rect(x - 2 - tail, y + 14, 1 + tail, 6, cloak_d)        # o manto fica para trás
    # capuz e rosto
    if p.dir == "frente":
        c.rect(x + 2, y + 3, w - 4, 6, void)
        if p.hurt:
            c.rect(x + 3, y + 6, 1, 1, glow)
            c.rect(x + w - 4, y + 6, 1, 1, glow)
        else:
            c.rect(x + 3, y + 5, 1, 2, glow)
            c.rect(x + w - 4, y + 5, 1, 2, glow)
        c.rect(x + 1, y + 2, w - 2, 1, cloak_l)
    elif p.side:
        c.rect(x + 5, y + 3, w - 5, 6, void)
        c.rect(x + w - 2, y + 5 + (1 if p.hurt else 0), 1, 2 - (1 if p.hurt else 0), glow)
        c.rect(x + 4, y + 2, w - 4, 1, cloak_l)
    else:
        c.rect(x + 4, y + 1, 2, 9, cloak_d)
        c.px(x + 4, y, cloak_l)
    # mangas (a da direita da imagem / a da frente segura a arma)
    if p.side:
        r = p.reach + p.near_swing
        sx = x + 4 + r
        sy = y + 11 - (1 if p.reach >= 3 else 0)
        c.line(x + 4, y + 10, sx, sy, cloak_d, 3)
        c.rect(sx + 1, sy + 6 - 3, 2, 1, hand)
        c.rect(sx, sy + 2, 3, 2, cloak_d)
        c.rect(sx + 1, sy + 4, 2, 1, hand)
        c.hand = (sx + 2, sy + 4)
    elif p.dir in ("frente", "costas"):
        da = p.arm_a
        db = p.arm_b + p.reach_dy
        c.rect(x - 2, y + 11, 2, 6 + da, cloak_d)
        c.rect(x - 2, y + 17 + da, 2, 1, hand)
        c.rect(x + w, y + 11, 2, 6 + db, cloak_d)
        c.rect(x + w, y + 17 + db, 2, 1, hand)
        c.hand = (x + w + 1, y + 18 + db)
    return c


def tita(p):
    c = Canvas()
    gold, gold_d, gold_l = (220, 172, 66), (150, 108, 34), (255, 226, 132)
    cape, skin, beard = uni(p, (164, 38, 42)), (226, 170, 128), (118, 70, 40)
    tunic, tunic_d = uni(p, gold), uni(p, gold_d, "dark")      # túnica por baixo das ombreiras
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    # capa atrás do corpo (balança)
    if p.side:
        back = 1 if p.wave < 0 or p.dash else 0
        c.rect(x - 3 - back, y, 4, 13, cape)
        c.rect(x - 3 - back, y + 12, 3, 2, shade(cape, -30))
        c.px(x - 4 - back, y + 10 + p.wave, shade(cape, -30))
    elif p.dir == "frente":
        c.rect(x - 1, y + 1, w + 2, 12, shade(cape, -30))
    legs(c, p, gold_d, (86, 58, 30), wide=True)
    far_arm(c, p, tunic, skin, thick=3)
    torso(c, p, tunic, belt=(110, 74, 28), buckle=gold_l)
    if p.dir == "frente":
        c.rect(x + 3, y + 2, w - 6, 1, gold_l)
        c.rect(x + 5, y + 3, 2, 3, gold_d)
        c.px(x + 3, y + 5, gold_d)
        c.px(x + w - 4, y + 5, gold_d)
    arms(c, p, tunic_d, skin, thick=3, cuff=gold)
    if p.dir == "costas":
        c.rect(x - 1, y, w + 2, 13, cape)
        c.rect(x, y, 1, 13, shade(cape, 30))
        c.rect(x - 1, y + 12, w + 2, 1, shade(cape, -40))
        c.rect(x + 3, y + 2, 1, 9, shade(cape, -24))
        c.rect(x + w - 4, y + 2, 1, 9, shade(cape, -24))
        c.px(x + 2 + p.wave, y + 13, cape)
    # ombreiras grandes
    if p.side:
        c.rect(x + 1, y - 1, 7, 4, gold)
        c.rect(x + 2, y - 1, 4, 1, gold_l)
        c.rect(x + 1, y + 2, 7, 1, gold_d)
    else:
        for sx in (x - 4, x + w - 1):
            c.rect(sx, y - 1, 5, 4, gold)
            c.rect(sx + 1, y - 1, 3, 1, gold_l)
            c.rect(sx, y + 2, 5, 1, gold_d)
    head(c, p, skin)
    if p.dir == "costas":
        c.rect(hx, hy, hw, hh - 2, (96, 58, 34))
        c.rect(hx + 1, hy + 1, hw - 3, 1, (124, 80, 48))
    else:
        eyes(c, p)
        if p.dir == "frente":
            c.rect(hx + 1, hy + 7, hw - 2, 3, beard)             # barba
            c.rect(hx + 3, hy + 10, hw - 6, 1, beard)
            c.rect(hx + 3, hy + 8, hw - 6, 1, shade(skin, -40) if not p.hurt else (60, 30, 24))
            c.rect(hx + 2, hy + 4, 2, 1, beard)                  # sobrancelhas
            c.rect(hx + hw - 4, hy + 4, 2, 1, beard)
        else:
            c.rect(hx + 4, hy + 7, hw - 4, 3, beard)
            c.rect(hx + 6, hy + 10, hw - 7, 1, beard)
            c.rect(hx + hw - 4, hy + 4, 2, 1, beard)
            c.rect(hx + 1, hy + 2, 3, 6, (96, 58, 34))
    # coroa
    c.rect(hx, hy, hw, 2, gold)
    c.rect(hx, hy + 1, hw, 1, gold_d)
    for sx in range(hx, hx + hw, 3):
        c.rect(sx, hy - 2, 1, 2, gold)
        c.px(sx, hy - 3, gold_l)
    if p.dir == "frente":
        c.px(hx + hw // 2, hy, (210, 50, 60))
    elif p.side:
        c.px(hx + hw - 2, hy, (210, 50, 60))
    return c


def pirata(p):
    c = Canvas()
    skin, beard, hair_c = (226, 170, 128), (72, 42, 30), (60, 36, 28)
    coat, coat_d = uni(p, (176, 48, 56)), uni(p, (118, 30, 40), "dark")
    shirt, gold = (236, 230, 214), (226, 180, 72)
    pants, boots = (52, 44, 58), (38, 30, 36)
    hat = (40, 32, 44)
    patch = (20, 16, 22)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    legs(c, p, pants, boots)
    # abas do casaco abaixo do cinto (balançam)
    if p.side:
        back = 1 if p.wave < 0 or p.dash else 0
        c.rect(x - 1 - back, y + h, 4, 4, coat_d)
        c.px(x - 1 - back, y + h + 3, shade(coat_d, -30))
    elif p.dir == "frente":
        c.rect(x - 1, y + h, 3, 4, coat)
        c.rect(x + w - 2, y + h, 3, 4, coat_d)
        c.px(x - 1, y + h + 3 + max(0, p.wave), gold)
    else:
        c.rect(x - 1, y + h, w + 2, 4, coat_d)
        c.rect(x + w // 2, y + h, 1, 4, shade(coat_d, -24))
    far_arm(c, p, coat, skin)
    torso(c, p, coat, belt=(96, 60, 36), buckle=gold)
    if p.dir == "frente":
        c.rect(x + 3, y, 2, 4, shirt)                            # camisa no decote
        c.px(x + 2, y, shirt)
        c.px(x + 5, y, shirt)
        c.px(x + 1, y + 5, gold)                                 # botões
        c.px(x + w - 2, y + 5, gold)
        c.px(x + 1, y + 3, gold)
        c.px(x + w - 2, y + 3, gold)
    elif p.side:
        c.rect(x + w - 2, y, 2, 3, shirt)
    arms(c, p, coat, skin, cuff=gold)
    head(c, p, skin)
    if p.dir == "costas":
        c.rect(hx, hy + 1, hw, hh - 3, hair_c)
        c.rect(hx + 4, hy + hh - 2, 2, 3, hair_c)               # rabo de cavalo
        c.rect(hx + 4, hy + hh - 2, 2, 1, coat)
        c.px(hx + 4 + p.wave, hy + hh + 1, hair_c)
    else:
        eyes(c, p)
        if p.dir == "frente":
            c.rect(hx + 1, hy + 7, hw - 2, 3, beard)
            c.rect(hx + 3, hy + 7, hw - 6, 1, shade(skin, -45) if not p.hurt else (40, 20, 18))
            c.rect(hx + 1, hy + 4, 3, 3, patch)                  # tapa-olho
            c.rect(hx, hy + 3, hw, 1, patch)
            c.px(hx + 1, hy + 10, beard)
            c.px(hx + hw - 2, hy + 10, beard)
        else:
            c.rect(hx + 4, hy + 7, hw - 4, 3, beard)
            c.rect(hx, hy + 3, hw, 1, patch)
            c.rect(hx + 1, hy + 1, 3, 6, hair_c)
            c.px(hx + 2, hy + 7, gold)                           # brinco
    # chapéu tricórnio com debrum dourado
    c.rect(hx - 2, hy, hw + 4, 2, hat)
    c.rect(hx - 2, hy + 1, hw + 4, 1, gold)
    c.rect(hx, hy - 3, hw, 3, hat)
    c.rect(hx + 1, hy - 3, hw - 3, 1, shade(hat, 34))
    if p.dir == "frente":
        c.px(hx - 3, hy - 1, hat)
        c.px(hx + hw + 2, hy - 1, hat)
        c.rect(hx + hw // 2 - 1, hy - 2, 2, 2, shirt)           # caveirinha
        c.px(hx + hw // 2 - 1, hy - 1, patch)
    elif p.side:
        c.px(hx + hw + 2, hy - 1, hat)
        c.px(hx - 3, hy - 1, hat)
    return c


def geada(p):
    c = Canvas()
    skin, hair_c = (236, 198, 178), (178, 210, 238)
    robe, robe_d, robe_l = uni(p, (104, 164, 216)), uni(p, (62, 106, 160), "dark"), uni(p, (196, 230, 250), "light")
    fur, ice, ice_l = (244, 248, 252), (150, 212, 240), (230, 248, 255)
    iris = (40, 84, 150)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    # cabelo comprido atrás do corpo (balança)
    if p.side:
        back = 1 if p.wave < 0 or p.dash else 0
        c.rect(hx - 1 - back, hy + 2, 4, 11, hair_c)
        c.rect(hx - 1 - back, hy + 12, 3, 1, shade(hair_c, -30))
    elif p.dir == "costas":
        c.rect(hx, hy + hh - 3, hw, 7, hair_c)
        c.rect(hx + 1, hy + hh + 3, hw - 2, 1, shade(hair_c, -30))
        c.px(hx + 2 + p.wave, hy + hh + 4, hair_c)
        c.px(hx + hw - 3 - p.wave, hy + hh + 4, hair_c)
    legs(c, p, robe_d, (210, 230, 244))
    far_arm(c, p, robe, skin)
    torso(c, p, robe, belt=robe_l)
    if p.dir == "frente":
        c.rect(x + w // 2 - 1, y + 2, 2, 2, ice)                 # broche de gelo
        c.px(x + w // 2 - 1, y + 2, ice_l)
    # saia longa do manto (os pés aparecem embaixo)
    sk = y + h
    c.rect(x - 1, sk, w + 2, 5, robe)
    if p.side:
        c.rect(x + w, sk, 1, 5, robe_d)
        c.rect(x - 1 - (1 if p.wave < 0 or p.dash else 0), sk + 2, 1, 3, robe_d)
    else:
        c.rect(x - 1, sk + 4, w + 2, 1, robe_d)
        c.rect(x - 1, sk, 1, 5, robe_l)
        if p.dir == "frente":
            c.rect(x + w // 2 - 1, sk, 2, 5, robe_l)
            c.rect(x - 1, sk + 4, w + 2, 1, ice)                 # barra de gelo
    arms(c, p, robe, skin, cuff=fur)
    # gola de pele
    if p.side:
        c.rect(x, y - 1, w + 1, 2, fur)
    else:
        c.rect(x - 1, y - 1, w + 2, 2, fur)
        c.px(x, y, (214, 224, 236))
    head(c, p, skin)
    hair(c, p, hair_c, style="fringe" if p.dir == "frente" else "short")
    if p.dir == "frente":
        c.rect(hx - 1, hy + 2, 2, 9, hair_c)
        c.rect(hx + hw - 1, hy + 2, 2, 9, hair_c)
        c.px(hx - 1, hy + 10, shade(hair_c, -30))
        c.px(hx + hw, hy + 10, shade(hair_c, -30))
        c.px(hx - 1, hy + 4, shade(hair_c, 30))
    elif p.side:
        c.rect(hx - 1, hy + 2, 4, 10, hair_c)
        c.rect(hx - 1, hy + 11, 4, 1, shade(hair_c, -30))
    if p.dir != "costas":
        eyes(c, p, pupil=iris, glint=(200, 244, 255))
        mouth(c, p, skin)
        blush(c, p, (236, 168, 176))
    # tiara de pontas de gelo
    c.rect(hx + 1, hy, hw - 2, 1, ice)
    for sx, tall in ((hx + 2, 2), (hx + hw // 2 - 1, 3), (hx + hw - 3, 2)):
        if p.side and sx < hx + 3:
            continue
        c.rect(sx, hy - tall, 1, tall, ice)
        c.px(sx, hy - tall, ice_l)
    return c


# ── criaturas da campanha ─────────────────────

def diabrete(p):
    """Diabinho vermelho que voa baixo: chifres, asas de morcego e rabo de ponta."""
    c = Canvas(24, 28)
    red, red_d, red_l = (204, 64, 58), (140, 36, 40), (240, 112, 92)
    wing, wing_d = (112, 40, 64), (74, 24, 44)
    horn, eye, dark = (236, 220, 180), (255, 214, 80), (40, 16, 22)
    flap = WALK_STRIDE[p.frame] if p.kind == "andar" else {"parado": (1, -1), "ataque": (2, -2, -2),
                                                             "dano": (-2,), "esquiva": (-2,)}[p.kind][p.frame]
    fly = p.float + (1 if p.hurt else 0)
    lean = p.head_dx
    hx, hy = 8 + lean, 6 + fly
    bx, by = 9 + p.torso_dx, 13 + fly

    def wing_poly(cx, side, front):
        tip_y = by - 2 - flap * 2
        pts = [(cx, by + 1), (cx + side * 7, tip_y), (cx + side * 8, tip_y + 3), (cx + side * 4, by + 5)]
        pygame.draw.polygon(c.surf, wing if front else wing_d, pts)
        pygame.draw.line(c.surf, wing_d if front else (50, 16, 30), (cx, by + 1), (cx + side * 7, tip_y))
        c.px(cx + side * 3, by + 3, shade(wing if front else wing_d, -20))

    def tail(x0, side):
        sway = p.wave
        for dx, dy in ((0, 0), (side, 1), (side * 2, 1 + sway), (side * 3, sway), (side * 3, -1 + sway)):
            c.px(x0 + dx, by + 6 + dy, red_d)
        c.rect(x0 + side * 3 - (1 if side < 0 else 0), by + 3 + sway, 2, 2, red_d)

    if p.side:
        wing_poly(bx + 1, -1, False)
        tail(bx, -1)
    elif p.dir == "frente":
        wing_poly(bx, -1, True)
        wing_poly(bx + 6, 1, True)
        tail(bx + 5, 1)
    # pernas curtas penduradas
    kick = 1 if p.kind == "andar" and p.frame % 4 in (1, 2) else 0
    if p.side:
        c.rect(bx + 1 - kick, by + 6, 2, 3, red_d)
        c.rect(bx + 3 + kick, by + 6, 2, 2, red_d)
    else:
        c.rect(bx, by + 6, 2, 3 - kick, red_d)
        c.rect(bx + 4, by + 6, 2, 2 + kick, red_d)
    # corpo
    w = 5 if p.side else 6
    c.rect(bx, by, w, 6, red)
    c.rect(bx, by, 1, 6, red_l)
    c.rect(bx + w - 1, by, 1, 6, red_d)
    if p.dir == "frente":
        c.rect(bx + 2, by + 2, 2, 3, red_l)                      # barriga
        claw = 1 if p.kind == "ataque" and p.frame else 0
        c.rect(bx - 1 - claw, by + 1, 1, 3 + claw, red_d)        # braços
        c.rect(bx + 6 + claw, by + 1, 1, 3 + claw, red_d)
        if claw:
            c.px(bx - 2, by + 4, horn)
            c.px(bx + 7, by + 4, horn)
    elif p.side:
        r = max(0, p.reach)
        c.rect(bx + 3, by + 1, 2 + r, 2, red_d)                  # braço na frente
        if r:
            c.px(bx + 5 + r - 1, by + 3, horn)                   # garras
    # cabeça
    c.rect(hx, hy, 8, 7, red)
    c.rect(hx, hy + 6, 8, 1, red_d)
    for cx, cy in ((hx, hy), (hx + 7, hy), (hx, hy + 6), (hx + 7, hy + 6)):
        c.erase(cx, cy)
    c.rect(hx + 1, hy, 5, 1, red_l)
    # chifres
    if p.side:
        c.rect(hx + 4, hy - 2, 2, 2, horn)
        c.px(hx + 6, hy - 3, horn)
        c.px(hx + 1, hy - 1, horn)
        c.px(hx - 1, hy + 2, red)                                # orelha
    else:
        c.rect(hx, hy - 2, 2, 2, horn)
        c.px(hx - 1, hy - 3, horn)
        c.rect(hx + 6, hy - 2, 2, 2, horn)
        c.px(hx + 8, hy - 3, horn)
        c.px(hx - 1, hy + 2, red)
        c.px(hx + 8, hy + 2, red)
    if p.dir == "frente":
        for ex in (hx + 1, hx + 5):
            if p.hurt:
                c.rect(ex, hy + 3, 2, 1, dark)
            else:
                c.rect(ex, hy + 3, 2, 1, eye)
                c.px(ex + (1 if ex < hx + 4 else 0), hy + 3, dark)
        c.rect(hx + 2, hy + 5, 4, 1, dark)                       # boca com presas
        c.px(hx + 2, hy + 5, horn)
        c.px(hx + 5, hy + 5, horn)
    elif p.side:
        c.rect(hx + 5, hy + 3, 2, 1, dark if p.hurt else eye)
        c.px(hx + 6, hy + 3, dark)
        c.rect(hx + 5, hy + 5, 3, 1, dark)
        c.px(hx + 6, hy + 5, horn)
    else:
        wing_poly(bx, -1, True)                                  # de costas as asas ficam na frente
        wing_poly(bx + 6, 1, True)
        tail(bx + 2, 1)
    c.hand = (bx + 3, by + 3)
    return c


def esqueleto(p):
    """Esqueleto arqueiro de capuz, com aljava nas costas e olhos acesos."""
    c = Canvas()
    bone, bone_d = (226, 220, 200), (162, 154, 136)
    cloth, cloth_d = (70, 52, 84), (44, 32, 56)
    socket, glow = (30, 22, 34), (255, 86, 70)
    quiver, feather = (110, 72, 44), (214, 64, 58)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    if p.side:
        c.rect(x - 2, y - 1, 2, 8, quiver)                       # aljava nas costas
        c.px(x - 2, y - 2, feather)
        c.px(x - 1, y - 3, feather)
    legs(c, p, bone_d, (86, 70, 60))
    far_arm(c, p, bone, bone)
    # tronco: costelas por cima de um pano escuro
    c.rect(x, y, w, h, cloth_d)
    if p.dir != "costas":
        for k in range(3):
            c.rect(x + 1, y + 1 + k * 2, w - 2, 1, bone)
        if p.dir == "frente":
            c.rect(x + w // 2 - 1, y, 2, h, bone_d)               # esterno
    else:
        c.rect(x + w // 2 - 1, y, 2, h, bone)                     # coluna
        c.rect(x + 1, y - 2, 3, 9, quiver)                        # aljava
        c.px(x + 1, y - 3, feather)
        c.px(x + 3, y - 3, feather)
    c.rect(x, y + h - 1, w, 1, cloth)
    bx, by, bw, bh = p.belt
    c.rect(bx, by, bw, bh, cloth)
    c.rect(bx + 1, by + bh, bw - 2, 2, cloth_d)                   # tanga
    arms(c, p, bone, bone)
    # caveira
    head(c, p, bone, nose=False)
    c.rect(hx, hy + hh - 2, hw, 1, bone_d)
    lit = glow if not p.hurt else socket
    if p.dir == "frente":
        for ex in (hx + 1, hx + hw - 4):
            c.rect(ex, hy + 4, 3, 2, socket)
            c.px(ex + 1, hy + 4, lit)
        c.px(hx + hw // 2, hy + 6, socket)                       # nariz
        for tx in range(hx + 2, hx + hw - 2, 2):                 # dentes
            c.px(tx, hy + 8, socket)
    elif p.side:
        c.rect(hx + hw - 4, hy + 4, 3, 2, socket)
        c.px(hx + hw - 3, hy + 4, lit)
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
        c.px(hx - 2 - (1 if p.wave < 0 else 0), hy + 3, cloth)
    return c


def golem(p):
    """Golem de pedra: ombros de rocha com musgo, punhos enormes e runas acesas.
    No ataque ergue os punhos acima da cabeça e martela o chão."""
    c = Canvas(36, 40)
    stone, stone_d, stone_l = (132, 122, 108), (88, 80, 72), (170, 160, 142)
    moss, moss_d = (88, 128, 62), (60, 92, 44)
    glow, glow_d = (255, 160, 64), (200, 92, 40)
    b = p.bob
    hurt = p.hurt
    if p.kind == "ataque":
        fist = ("cima", "meio", "chao")[p.frame]
    elif p.dash:
        fist = "meio"
    else:
        fist = None
    lit = (255, 236, 180) if fist == "chao" else glow

    def block(x, y, w, h, base=stone):
        c.rect(x, y, w, h, base)
        c.rect(x, y, w, 1, shade(base, 34))
        c.rect(x, y, 1, h, shade(base, 18))
        c.rect(x + w - 1, y, 1, h, shade(base, -34))
        c.rect(x, y + h - 1, w, 1, shade(base, -40))

    if p.side:
        stride = p.stride + (1 if p.stride > 0 else -1 if p.stride < 0 else 0)
        block(14 - stride, 30 + b - p.lift_a, 7, 8 + (0 if p.lift_a else 0), stone_d)   # perna de trás
        block(15 + stride, 30 + b - p.lift_b, 7, 8)
        swing = p.far_swing
        block(11 + swing, 20 + b, 6, 9, stone_d)                  # braço de trás
        lean = p.head_dx
        block(11 + p.torso_dx, 15 + b, 14, 16)                    # tronco
        c.rect(19 + p.torso_dx, 21 + b, 4, 1, glow_d)
        c.rect(21 + p.torso_dx, 22 + b, 1, 3, lit)
        block(14 + lean, 8 + b, 10, 9)                            # cabeça
        c.rect(21 + lean, 12 + b, 2, 1 if hurt else 2, lit)
        c.rect(14 + lean, 8 + b, 10, 2, moss)
        block(12 + p.torso_dx, 13 + b, 9, 8, stone_l)             # ombro
        c.rect(12 + p.torso_dx, 13 + b, 9, 2, moss)
        c.rect(14 + p.torso_dx, 12 + b, 3, 1, moss_d)
        if fist == "cima":
            c.line(16, 15 + b, 15, 7 + b, stone, 5)               # braço erguido atrás da cabeça
            block(12, 1 + b, 9, 7, stone_l)
            c.rect(14, 4 + b, 5, 1, stone_d)
        elif fist in ("meio", "chao"):
            reach = 3 if fist == "meio" else 4
            block(15 + reach, 19 + b, 6, 9)
            block(16 + reach, 27 + b + (3 if fist == "chao" else 0), 8, 7, stone_l)
            c.rect(18 + reach, 29 + b + (3 if fist == "chao" else 0), 4, 1, stone_d)
        else:
            s = -p.near_swing * 2
            block(15 + s, 21 + b, 6, 10)                          # braço da frente
            block(14 + s, 30 + b, 8, 7, stone_l)                  # punho
            c.rect(16 + s, 32 + b, 4, 1, stone_d)
        c.hand = (18, 33 + b)
        return c

    for x, lifted in ((10, p.lift_a), (20, p.lift_b)):
        block(x - (1 if p.dash and x < 15 else 0) + (1 if p.dash and x > 15 else 0),
              30 + b - lifted, 7, 8, stone_d)
    block(9, 15 + b, 18, 16)                                      # tronco
    if p.dir == "frente":
        # runas acesas no peito
        c.rect(15, 19 + b, 6, 1, glow_d)
        c.rect(17, 19 + b, 2, 6, lit)
        c.rect(14, 23 + b, 8, 1, glow_d)
        c.px(17, 21 + b, (255, 236, 180))
    else:
        c.rect(12, 18 + b, 12, 3, moss_d)
        c.rect(14, 21 + b, 8, 2, moss)
        c.px(16, 24 + b, moss_d)
    if fist == "cima":
        # os dois punhos juntos acima da cabeça
        for x0, x1 in ((5, 11), (26, 20)):
            c.line(x0, 15 + b, x1, 6 + b, stone_d, 5)
            c.line(x0, 15 + b, x1, 6 + b, stone, 4)
        block(10, 1 + b, 16, 7, stone_l)
        c.rect(17, 2 + b, 1, 5, stone_d)
        c.rect(12, 5 + b, 12, 1, stone_d)
    elif fist in ("meio", "chao"):
        drop = 3 if fist == "chao" else 0
        for x in (3, 27):
            block(x, 21 + b, 6, 11 + drop)
            block(x - 1, 31 + b + drop - (2 if drop else 0), 8, 7 - (1 if drop else 0), stone_l)
    else:
        for x, dy in ((3, p.arm_a), (27, p.arm_b)):
            block(x, 21 + b + dy, 6, 11)
            block(x - 1, 31 + b + dy, 8, 7, stone_l)
            c.rect(x + 1, 33 + b + dy, 4, 1, stone_d)
    block(13, 8 + b + (1 if hurt else 0), 10, 9)                  # cabeça encaixada nos ombros
    hb = b + (1 if hurt else 0)
    if p.dir == "frente":
        c.rect(15, 12 + hb, 2, 1 if hurt else 2, lit)
        c.rect(19, 12 + hb, 2, 1 if hurt else 2, lit)
        c.rect(16, 15 + hb, 4, 1, stone_d)
    c.rect(13, 8 + hb, 10, 2, moss)
    for x in (2, 25):                                             # ombros de rocha com musgo
        block(x, 13 + b, 9, 9, stone_l)
        c.rect(x, 13 + b, 9, 2, moss)
        c.rect(x + 2, 12 + b, 4, 1, moss_d)
        c.px(x + 3, 15 + b, moss_d)
    c.hand = (30, 33 + b)
    return c


# ── catálogo ──────────────────────────────────
# nome → (desenho, largo, cores que acendem de vermelho na alma corrompida)
CHARACTERS = {
    "guerreiro": (guerreiro, False, [EYE]),
    "atirador": (atirador, False, [EYE, WHITE]),
    "tanque": (tanque, True, [(120, 232, 244), (220, 252, 255)]),
    "ninja": (ninja, False, [EYE, WHITE]),
    "velocista": (velocista, False, [EYE, WHITE]),
    "aryel": (aryel, False, [EYE, (176, 206, 228), (226, 240, 250)]),
    "fantasma": (fantasma, False, [(150, 244, 255)]),
    "tita": (tita, True, [EYE, WHITE]),
    "pirata": (pirata, False, [EYE, WHITE]),
    "geada": (geada, False, [(40, 84, 150), (200, 244, 255)]),
    "diabrete": (diabrete, False, []),
    "esqueleto": (esqueleto, False, []),
    "golem": (golem, False, []),
}
HEROES = ("guerreiro", "atirador", "tanque", "ninja", "velocista", "aryel", "fantasma", "tita", "pirata", "geada")
KIT_DIR = OUT / "uniformes"


def build_sheet(name, kit=None):
    """Folha do personagem (linhas = direções, colunas = quadros das poses) e os dados dela.
    Com ``kit`` (um item de KITS), a roupa sai na cor do uniforme do time."""
    draw, wide, glow = CHARACTERS[name]
    probe = draw(Pose("frente", "parado", 0, wide, kit))
    cw, ch = probe.w, probe.h
    columns = [(kind, i) for kind, n in SHEET_POSES for i in range(n)]
    sheet = pygame.Surface((cw * len(columns), ch * len(SHEET_DIRECTIONS)), pygame.SRCALPHA)
    hands = {}
    for row, direction in enumerate(SHEET_DIRECTIONS):
        if direction == "esquerda":
            continue
        hands[direction] = []
        for col, (kind, i) in enumerate(columns):
            canvas = draw(Pose(direction, kind, i, wide, kit))
            sheet.blit(canvas.finish(), (col * cw, row * ch))
            hx, hy = canvas.hand or (cw / 2, ch / 2)
            hands[direction].append([round(hx, 1), round(hy, 1)])
    # esquerda = direita espelhada
    right, left = SHEET_DIRECTIONS.index("direita"), SHEET_DIRECTIONS.index("esquerda")
    for col in range(len(columns)):
        cell = sheet.subsurface((col * cw, right * ch, cw, ch))
        sheet.blit(pygame.transform.flip(cell, True, False), (col * cw, left * ch))
    info = {"cell": [cw, ch], "poses": [list(p) for p in SHEET_POSES], "hand": hands,
            "eyes": [list(g) for g in glow]}
    return sheet, info


def main():
    pygame.init()
    OUT.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1:] or list(CHARACTERS)
    for name in only:
        sheet, info = build_sheet(name)
        pygame.image.save(sheet, str(OUT / f"{name}.png"))
        (OUT / f"{name}.json").write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
        if name in HEROES:
            KIT_DIR.mkdir(parents=True, exist_ok=True)
            for team, kit in KITS.items():
                kit_sheet, _ = build_sheet(name, kit)
                pygame.image.save(kit_sheet, str(KIT_DIR / f"{name}_{team}.png"))
        print("ok", name)


if __name__ == "__main__":
    main()
