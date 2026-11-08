"""Gera as folhas das skins da loja de CACOS (assets/characters/skins/<skin>.png + .json).

Uso:  python tools/gerar_skins.py [skin ...]

Cada skin reaproveita o desenho do herói em gerar_sprites.py: as cores da roupa são trocadas no
próprio código do herói (sombra, brilho e contorno saem certos), os acessórios entram por cima e a
folha sai no dobro de detalhe, com as mesmas poses (inclusive as do esporte) e a mão no lugar certo.
O efeito em volta (bits, cristais, brasas, moedas...) é desenhado no jogo (soulstrike/skins.py).
"""
import inspect
import json
import math  # noqa: F401
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gerar_sprites as gs  # noqa: E402

OUT = gs.OUT / "skins"
shade = gs.shade


def recolor(name, swaps):
    """Cópia do desenho do herói com as cores trocadas direto no código."""
    src = inspect.getsource(getattr(gs, name))
    for old, new in swaps.items():
        assert old in src, (name, old)
        src = src.replace(old, new)
    src = src.replace(f"def {name}(", f"def _skin_{name}(", 1)
    ns = gs.__dict__
    exec(compile(src, f"<skin {name}>", "exec"), ns)
    return ns[f"_skin_{name}"]


def under(base_fn, under_fn):
    """Desenha ``under_fn`` atrás do herói (capa, aura)."""
    def draw(p):
        top = base_fn(p)
        back = gs.Canvas(top.w, top.h)
        under_fn(back, p)
        back.big.blit(top.big, (0, 0))
        top.big = back.big
        top.surf = gs._Area(top.big, top.w, top.h)
        return top
    return draw


# ───────────────────────── 1. ALBEGUINIO HACKER SUPREMO ─────────────────────────
HOOD, HOOD_D, CODE, CODE_L = (34, 38, 46), (20, 22, 28), (60, 230, 120), (190, 255, 210)
_alb = recolor("albeguinio", {
    "(226, 212, 182)": "(40, 44, 54)", "(184, 166, 132)": "(24, 26, 34)", "(246, 238, 216)": "(70, 76, 90)",
    "tee, pants, shoes = (36, 34, 42), (218, 204, 172), (62, 44, 34)":
        "tee, pants, shoes = (30, 110, 70), (60, 64, 82), (30, 30, 38)",
    "(226, 226, 226)": "(120, 255, 170)",
})


def albeguinio_hacker(p):
    c = _alb(p)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    if p.dir == "costas":
        c.rect(hx - 1, hy - 2, hw + 2, hh + 1, HOOD)
        c.rect(hx, hy - 2, hw - 2, 1, shade(HOOD, 30))
        c.rect(hx + 4, hy + 1, 2, hh - 2, HOOD_D)
        for i, (cx, cy) in enumerate(((1, 2), (3, 5), (7, 3), (2, 8), (6, 7))):   # código nas costas
            if (i + p.frame) % 3:
                c.px(hx + cx, hy + cy, CODE)
        for cx in range(x + 1, x + w - 1, 2):
            c.px(cx, y + 2 + (cx + p.frame) % 4, CODE)
    elif p.side:
        c.rect(hx - 1, hy - 2, hw - 1, 3, HOOD)
        c.rect(hx - 1, hy + 1, 4, hh - 2, HOOD)
        c.rect(hx, hy - 2, hw - 4, 1, shade(HOOD, 30))
        c.rect(hx + 6, hy + 4, 4, 2, (16, 18, 22))                       # visor
        c.rect(hx + 6, hy + 4, 4, 1, CODE)
        c.px(hx + 9, hy + 4, CODE_L)
        c.px(x + 1, y + 2 + p.frame % 3, CODE)
    else:
        c.rect(hx - 1, hy - 2, hw + 2, 3, HOOD)                          # capuz
        c.rect(hx - 1, hy + 1, 1, hh - 2, HOOD)
        c.rect(hx + hw, hy + 1, 1, hh - 2, HOOD)
        c.rect(hx, hy - 2, hw - 2, 1, shade(HOOD, 30))
        c.rect(hx - 1, hy + 1, 1, 3, HOOD_D)
        c.rect(hx + 1, hy + 4, hw - 2, 2, (16, 18, 22))                  # visor de tela
        c.rect(hx + 1, hy + 4, hw - 2, 1, CODE)
        c.px(hx + 2, hy + 4, CODE_L)
        c.px(hx + 6 + (p.frame % 2), hy + 5, CODE)
        for cx, cy in ((0, 1), (1, 4), (w - 1, 2), (w - 2, 5), (0, 6)):  # código correndo no moletom
            c.px(x + cx, y + (cy + p.frame) % (h - 1), CODE)
        c.rect(x + 3, y + 1, 2, 1, CODE_L)                               # cordão do capuz
        c.px(x + 3, y + 2, CODE)
        c.px(x + w - 4, y + 2, CODE)
    return c


# ───────────────────────── 2. CAUANZERA REI DO CRISTAL ─────────────────────────
CR, CR_D, CR_L, CR_W = (90, 170, 240), (44, 88, 180), (180, 230, 255), (240, 252, 255)
_cau = recolor("cauanzera", {
    "uni(p, (46, 46, 56))": "uni(p, (52, 86, 170))", "uni(p, (28, 28, 36), \"dark\")": "uni(p, (30, 48, 112), \"dark\")",
    "uni(p, (78, 78, 92), \"light\")": "uni(p, (110, 170, 240), \"light\")",
    "tee, pants, shoes = (156, 158, 166), (34, 34, 42), (240, 240, 236)":
        "tee, pants, shoes = (214, 236, 252), (26, 34, 70), (240, 248, 255)",
    "stripe = (40, 40, 48)": "stripe = (70, 150, 230)",
})


def _cape(c, p):
    x, y, w, h = p.torso
    cape = (40, 70, 160)
    if p.side:
        back = 1 if p.wave < 0 or p.dash else 0
        c.rect(x - 3 - back, y, 4, 14, cape)
        c.rect(x - 3 - back, y + 13, 3, 1, CR)
    elif p.dir == "frente":
        c.rect(x - 2, y + 1, w + 4, 13, shade(cape, -24))
        c.rect(x - 2, y + 13, w + 4, 1, CR)


def cauanzera_cristal(p):
    c = under(_cau, _cape)(p)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    if p.dir == "costas":
        cape = (40, 70, 160)
        c.rect(x - 1, y, w + 2, 14, cape)
        c.rect(x, y, 1, 14, shade(cape, 30))
        c.rect(x - 1, y + 13, w + 2, 1, CR)
        c.rect(x + w // 2 - 1, y + 4, 2, 3, CR)                             # cristal bordado
        c.px(x + w // 2 - 1, y + 4, CR_W)
    # ombreiras de cristal
    spots = (x + w // 2 - 2,) if p.side else (x - 3, x + w)
    for sx in spots:
        c.rect(sx, y - 1, 3, 2, CR)
        c.px(sx + 1, y - 3, CR_L)
        c.rect(sx + 1, y - 2, 1, 1, CR)
        c.px(sx, y - 1, CR_W)
        c.rect(sx, y + 1, 3, 1, CR_D)
    # coroa de cristal flutuando em cima dos cachos (sobe e desce)
    fy = hy - 6 - (1 if p.frame % 2 else 0)
    if p.dir != "costas" or True:
        cx = hx + hw // 2 + (1 if p.side else 0)
        for dx, hgt in ((-4, 2), (-2, 3), (0, 4), (2, 3), (4, 2)):
            c.rect(cx + dx - (0 if dx <= 0 else 1), fy + 4 - hgt, 1, hgt, CR)
            c.px(cx + dx - (0 if dx <= 0 else 1), fy + 4 - hgt, CR_W)
        c.rect(cx - 4, fy + 4, 9, 1, CR_D)
    return c


# ───────────────────────── 3. ARYEL ALMA DE FOGO ─────────────────────────
F1, F2, F3, F4 = (255, 236, 150), (255, 170, 50), (232, 90, 30), (150, 34, 22)
_ary = recolor("aryel", {
    "hair_c, hair_d, hair_l = (112, 68, 42), (78, 46, 30), (152, 98, 62)":
        "hair_c, hair_d, hair_l = (232, 90, 30), (160, 40, 22), (255, 180, 60)",
    "uni(p, (236, 150, 172))": "uni(p, (52, 40, 46))", "uni(p, (198, 108, 138), \"dark\")": "uni(p, (32, 24, 30), \"dark\")",
    "uni(p, (250, 190, 204), \"light\")": "uni(p, (84, 66, 70), \"light\")",
    "(78, 118, 184)": "(255, 150, 40)",
    "pants, shoes = (226, 212, 172), (118, 72, 42)": "pants, shoes = (46, 36, 40), (30, 24, 26)",
    "frame, lens, lens_l = (48, 40, 50), (176, 206, 228), (226, 240, 250)": "frame, lens, lens_l = (48, 40, 50), (255, 196, 110), (255, 240, 200)",
})


def aryel_fogo(p):
    c = _ary(p)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    ph = p.frame
    # labaredas saindo do cabelo
    tips = range(hx, hx + hw, 2) if not p.side else range(hx - 1, hx + hw - 3, 2)
    for i, tx in enumerate(tips):
        tall = 2 + (i + ph) % 3
        c.rect(tx, hy - 1 - tall, 1, tall, F3)
        c.px(tx, hy - 1 - tall, F2)
        if tall == 4:
            c.px(tx, hy - 6, F1)
    # veios de lava na camisa e na calça
    if p.dir != "costas":
        for cx, cy in ((1, 4), (2, 5), (2, 6), (w - 2, 3), (w - 3, 4)):
            if cx < w:
                c.px(x + cx, y + cy, F2 if (cx + ph) % 2 else F3)
        c.px(x + 1, y + 6, F1)
    else:
        for cy in range(1, h - 1):
            c.px(x + w // 2 - 1 + (cy % 2), y + cy, F3)
        c.px(x + w // 2, y + 2, F1)
    bx, by, bw, bh = p.belt
    c.rect(bx, by + 3, 1, 2, F3)
    c.rect(bx + bw - 1, by + 4, 1, 2, F3)
    return c


# ───────────────────────── 4. BORBA JR EXECUTIVO DE OURO ─────────────────────────
G, G_D, G_L = (222, 176, 66), (150, 108, 34), (255, 230, 140)
_bor = recolor("borba", {
    "uni(p, (40, 40, 48))": "uni(p, (222, 176, 66))", "uni(p, (24, 24, 30), \"dark\")": "uni(p, (150, 108, 34), \"dark\")",
    "uni(p, (74, 74, 88), \"light\")": "uni(p, (255, 230, 140), \"light\")",
    "trim, pants, shoes = (232, 232, 226), (32, 32, 40), (34, 34, 40)":
        "trim, pants, shoes = (30, 24, 28), (96, 70, 30), (26, 20, 22)",
})


def borba_ouro(p):
    c = _bor(p)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    if p.dir == "frente":
        c.rect(x + w // 2 - 1, y, 3, 1, (240, 238, 230))                   # gola branca de camisa
        c.rect(x + w // 2, y + 1, 1, 1, (40, 30, 34))                       # nó da gravata
        sway = (0, 0, 1, 0, 0, 0, -1, 0)[p.frame % 8] if p.kind == "andar" else 0
        c.rect(x + w // 2 + sway, y + 2, 1, h - 3, (150, 30, 40))           # gravata vinho balançando
        c.px(x + w // 2 + sway, y + h - 2, (110, 20, 30))
        c.px(x + 2, y + 2, G_L)                                             # lenço no bolso
        c.px(x + 2, y + 1, (240, 238, 230))
        for lx in (hx + 1, hx + hw - 4):                                    # óculos escuros
            c.rect(lx, hy + 5, 3, 2, (24, 22, 30))
            c.px(lx, hy + 5, (140, 140, 160))
    elif p.side:
        c.rect(hx + 6, hy + 5, 3, 2, (24, 22, 30))
        c.px(hx + 6, hy + 5, (140, 140, 160))
        c.rect(x + w - 2, y + 1, 1, h - 3, (150, 30, 40))
    # relógio de ouro no pulso
    if not p.side:
        wy = y + 1 + max(2, 5 + p.arm_a) - 1
        wx = x - 3 - (1 if p.dash else 0)
        c.rect(wx, wy, 3, 1, G_L)
    return c


# ───────────────────────── 5. FANTASMA LENÇOL DA VÓ ─────────────────────────
_fan = recolor("fantasma", {
    "uni(p, (128, 86, 188))": "uni(p, (238, 236, 228))", "uni(p, (82, 50, 128), \"dark\")": "uni(p, (184, 186, 200), \"dark\")",
    "uni(p, (176, 138, 232), \"light\")": "uni(p, (255, 255, 250), \"light\")",
    "void, glow = (20, 14, 32), (150, 244, 255)": "void, glow = (238, 236, 228), (20, 16, 24)",
})
FLOR = ((236, 110, 150), (110, 170, 230), (250, 200, 70))


def fantasma_lencol(p):
    c = _fan(p)
    fy = p.float + (1 if p.hurt else 0)
    x, y = 7 + p.head_dx, 6 + fy
    if p.dir == "frente":                                                   # buracos dos olhos no lençol
        for ex in (x + 3, x + 6):
            c.rect(ex, y + 4, 2, 3, (26, 22, 30))
            c.px(ex, y + 4, (60, 56, 70))
        c.rect(x + 4, y + 8, 2, 1, (200, 196, 200))                          # boquinha amassada
    elif p.side:
        c.rect(x + 7, y + 4, 2, 3, (26, 22, 30))
    # florzinhas estampadas
    spots = ((1, 11), (6, 10), (3, 15), (8, 16), (0, 19), (5, 20), (2, 2), (8, 4))
    for i, (fx, fy2) in enumerate(spots):
        if p.dir == "frente" and fy2 < 9 and 2 < fx < 8:
            continue
        col = FLOR[i % 3]
        c.px(x + fx, y + fy2, col)
        c.px(x + fx + 1, y + fy2, shade(col, -30))
        c.px(x + fx, y + fy2 + 1, shade(col, -30))
    # barrinha de crochê embaixo
    for i, tx in enumerate(range(x - 1, x + 11, 2)):
        c.px(tx, y + 22 + (i % 2), (236, 110, 150))
    return c


# ───────────────────────── 6. ATIRADOR CANGACEIRO ─────────────────────────
COURO, COURO_D, COURO_L = (164, 112, 58), (110, 70, 34), (210, 160, 96)
_ati = recolor("atirador", {
    "uni(p, (64, 152, 164))": "uni(p, (176, 140, 88))",
    "hat, band, scarf = (124, 82, 46), (44, 116, 128), (198, 70, 58)":
        "hat, band, scarf = (164, 112, 58), (226, 190, 80), (204, 40, 46)",
    "(66, 60, 78), (98, 62, 38)": "(120, 96, 66), (88, 54, 28)",
})


def atirador_cangaceiro(p):
    c = _ati(p)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    gold = (236, 196, 80)
    if p.dir != "costas":
        # aba virada para cima em meia-lua, com a estrela de ouro na frente
        c.rect(hx - 2, hy - 6, 3, 3, COURO)
        c.rect(hx + hw - 1, hy - 6, 3, 3, COURO)
        c.px(hx - 3, hy - 7, COURO_L)
        c.px(hx + hw + 2, hy - 7, COURO_D)
        if p.dir == "frente":
            sx, sy = hx + hw // 2 - 1, hy - 3
            c.rect(sx, sy - 1, 2, 3, gold)
            c.rect(sx - 1, sy, 4, 1, gold)
            c.px(sx, sy - 1, (255, 240, 170))
            for mx in range(hx + 1, hx + hw - 1, 2):                         # moedinhas na aba
                c.px(mx, hy + 1, gold)
        else:
            c.rect(hx + hw - 3, hy - 3, 2, 2, gold)
        # cartucheiras cruzadas no peito
        if p.dir == "frente":
            for i in range(h - 1):
                c.px(x + i * w // (h - 1), y + i, COURO_D)
                c.px(x + w - 1 - i * w // (h - 1), y + i, COURO_D)
                if i % 2:
                    c.px(x + i * w // (h - 1), y + i, gold)
        else:
            for i in range(h - 1):
                c.px(x + i * w // (h - 1), y + i, COURO_D)
    else:
        c.rect(hx - 2, hy - 6, hw + 4, 2, COURO)
        for i in range(h - 1):
            c.px(x + i * w // (h - 1), y + i, COURO_D)
            c.px(x + w - 1 - i * w // (h - 1), y + i, COURO_D)
    return c


# ───────────────────────── 7. TANQUE CAVALEIRO DE OBSIDIANA ─────────────────────────
_tan = recolor("tanque", {
    "steel, steel_d, steel_l = (150, 158, 172), (96, 102, 118), (196, 204, 216)":
        "steel, steel_d, steel_l = (66, 62, 86), (44, 40, 62), (118, 110, 150)",
    "visor = (120, 232, 244)": "visor = (255, 70, 60)",
    "(220, 252, 255)": "(255, 210, 190)",
    "plume = (196, 64, 56)": "plume = (150, 70, 220)",
    "belt=(80, 66, 52), buckle=(196, 160, 90)": "belt=(40, 34, 50), buckle=(236, 196, 80)",
})


def tanque_obsidiana(p):
    c = _tan(p)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    gold = (236, 196, 80)
    c.rect(hx, hy - 1, hw, 1, gold)                                         # friso de ouro no elmo
    if not p.side:
        for sx in (x - 3, x + w - 2):
            c.rect(sx, y + 2, 5, 1, gold)
        if p.dir == "frente":                                               # runa roxa no peito
            c.rect(x + w // 2 - 1, y + 2, 2, 3, (170, 90, 255))
            c.px(x + w // 2 - 1, y + 2, (230, 200, 255))
    else:
        c.rect(x + 1, y + 2, 6, 1, gold)
    # chifres
    if p.side:
        c.rect(hx + 1, hy - 3, 1, 2, (220, 214, 200))
        c.px(hx, hy - 4, (220, 214, 200))
    else:
        for sx, d in ((hx - 1, -1), (hx + hw, 1)):
            c.rect(sx, hy, 1, 2, (220, 214, 200))
            c.px(sx + d, hy - 1, (220, 214, 200))
            c.px(sx + d, hy - 2, (240, 236, 226))
    return c


# ───────────────────────── 8. TITÃ REI MOMO ─────────────────────────
_tit = recolor("tita", {
    "uni(p, (164, 38, 42))": "uni(p, (120, 40, 170))",
    "gold, gold_d, gold_l = (220, 172, 66), (150, 108, 34), (255, 226, 132)":
        "gold, gold_d, gold_l = (232, 184, 70), (160, 112, 36), (255, 236, 150)",
    "uni(p, gold), uni(p, gold_d, \"dark\")": "uni(p, (40, 170, 90)), uni(p, (24, 110, 60), \"dark\")",
})
PENAS = ((236, 60, 90), (250, 200, 50), (60, 200, 120), (60, 150, 240), (200, 80, 220))


def tita_momo(p):
    c = _tit(p)
    x, y, w, h = p.torso
    hx, hy, hw, hh = p.head
    # coroa ganha um leque de penas coloridas atrás
    ph = p.frame % 2
    for i, dx in enumerate((-3, -1, 1, 3, 5, 7, 9, 11, 13)):
        col = PENAS[i % 5]
        tall = 5 - abs(i - 4) // 2 + (1 if (i + ph) % 3 == 0 else 0)
        px_ = hx + dx - 1
        c.rect(px_, hy - 2 - tall, 1, tall, col)
        c.px(px_, hy - 2 - tall, shade(col, 40))
    c.rect(hx, hy, hw, 2, (232, 184, 70))
    c.rect(hx, hy + 1, hw, 1, (160, 112, 36))
    for gx in range(hx + 1, hx + hw, 3):
        c.px(gx, hy, PENAS[gx % 5])                                       # pedrinhas na coroa
    # lantejoulas na túnica e na capa
    if p.dir != "costas":
        for i, (sx, sy) in enumerate(((1, 1), (3, 3), (w - 2, 2), (w - 4, 4), (2, 5))):
            if sx < w:
                c.px(x + sx, y + sy, (255, 250, 220) if (i + p.frame) % 2 else PENAS[i % 5])
    else:
        for i in range(6):
            c.px(x + (i * 3) % w, y + 2 + i * 2 % 10, (255, 250, 220) if (i + p.frame) % 2 else (230, 140, 255))
    # colar de flores
    if p.dir == "frente":
        for i, fx in enumerate(range(x, x + w)):
            c.px(fx, y + (1 if 0 < fx - x < w - 1 else 0), PENAS[i % 5])
    return c


# skin -> (herói, desenho, cores que brilham além das do herói)
SKINS = {
    "albeguinio_hacker": ("albeguinio", albeguinio_hacker, [CODE, CODE_L]),
    "cauanzera_cristal": ("cauanzera", cauanzera_cristal, [CR_L, CR_W]),
    "aryel_fogo": ("aryel", aryel_fogo, [F1, F2, F3]),
    "borba_ouro": ("borba", borba_ouro, [G_L]),
    "fantasma_lencol": ("fantasma", fantasma_lencol, []),
    "atirador_cangaceiro": ("atirador", atirador_cangaceiro, []),
    "tanque_obsidiana": ("tanque", tanque_obsidiana, [(255, 70, 60), (170, 90, 255)]),
    "tita_momo": ("tita", tita_momo, []),
}


def build(skin):
    hero, draw, glow = SKINS[skin]
    wide, base_glow = gs.CHARACTERS[hero][1], gs.CHARACTERS[hero][2]
    name = "skin_" + skin
    gs.CHARACTERS[name] = (draw, wide, list(base_glow) + list(glow))
    gs.HD.add(name)
    gs.VARIANTS = gs.VARIANTS + (name,)          # as poses do esporte também
    try:
        return gs.build_sheet(name)
    finally:
        del gs.CHARACTERS[name]


def main():
    gs.pygame.init()
    OUT.mkdir(parents=True, exist_ok=True)
    for skin in sys.argv[1:] or list(SKINS):
        sheet, info = build(skin)
        gs.pygame.image.save(sheet, str(OUT / f"{skin}.png"))
        (OUT / f"{skin}.json").write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
        cw, ch = info["cell"]                       # retrato para a loja do celular: parado de frente, 3x
        idle = sum(n for kind, n in info["poses"][:[k for k, _ in info["poses"]].index("parado")])
        cell = sheet.subsurface((idle * cw, 0, cw, ch))
        gs.pygame.image.save(gs.pygame.transform.scale(cell, (cw * 3, ch * 3)), str(OUT / f"{skin}_retrato.png"))
        print("ok", skin)


if __name__ == "__main__":
    main()
