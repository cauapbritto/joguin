"""Gera a arte das quadras de basquete (fundo, cesta e aro da frente) em pixel art.

Uso:  pip install numpy pillow
      python tools/gerar_quadras.py

Tudo é desenhado em meia resolução (1000x600 e sprites de 100x120) e ampliado 2x sem suavizar,
para casar com o pixel dos personagens. As medidas são as de arena.Court (meia resolução aqui).
Sai em assets/tiles/quadra_*/ (fundo<quadra>.png, cesta.png, aro_frente.png e, na Arena Soul,
aro_fogo_1..4.png).
"""
import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "assets" / "tiles"

# ── medidas em meia resolução (mundo / 2) ─────────────────────────────
W, H = 1000, 600
L, R, T, B = 40, 960, 40, 560          # linhas externas
CX, CY = 500, 300
WALL = 10                               # muro invisível
HOOP_X = 92                             # aro no chão (esquerda)
KEY_X, KEY_T, KEY_B = 230, 220, 380     # garrafão
FT_R = 60
CIRCLE_R = 60
NOCHARGE_R = 41
THREE_R = 235
CORNER_T, CORNER_B = 75, 525
LW = 3                                  # largura da linha
SW, SH = 100, 120                       # sprite da cesta
ANCHOR = (84, 110)                      # chão sob o aro, dentro do sprite
RIM = (84, 62)                          # centro do aro, dentro do sprite
RIM_RX, RIM_RY = 10, 4


def mirror_x(x):
    return W - 1 - x


# ── utilidades de pixel ────────────────────────────────────────────────
def shade(c, k):
    """Clareia (k>0) ou escurece (k<0) uma cor; k em -1..1."""
    if k >= 0:
        return tuple(round(v + (255 - v) * k) for v in c)
    return tuple(round(v * (1 + k)) for v in c)


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0


def court_mask(fn):
    """Máscara booleana HxW a partir de um desenho em PIL (fn recebe o ImageDraw)."""
    m = Image.new("L", (W, H), 0)
    fn(ImageDraw.Draw(m))
    return np.array(m) > 0


def draw_lines(d, fill, width=LW, dashed_inside=True):
    """Todas as linhas da quadra (os dois lados)."""
    d.rectangle((L, T, R, B), outline=fill, width=width)
    d.rectangle((CX - 1, T, CX + 1, B), fill=fill)
    d.ellipse((CX - CIRCLE_R, CY - CIRCLE_R, CX + CIRCLE_R, CY + CIRCLE_R), outline=fill, width=width)
    for side in (0, 1):
        f = (lambda x: x) if side == 0 else mirror_x
        hx = f(HOOP_X)
        kx0, kx1 = sorted((f(L), f(KEY_X)))
        d.rectangle((kx0, KEY_T, kx1, KEY_B), outline=fill, width=width)
        kx = f(KEY_X)
        out0, out1 = (-90, 90) if side == 0 else (90, 270)
        d.arc((kx - FT_R, CY - FT_R, kx + FT_R, CY + FT_R), out0, out1, fill=fill, width=width)
        if dashed_inside:
            for a in range(0, 180, 24):
                a0 = out1 + a
                d.arc((kx - FT_R, CY - FT_R, kx + FT_R, CY + FT_R), a0, a0 + 12, fill=fill, width=width)
        d.arc((hx - NOCHARGE_R, CY - NOCHARGE_R, hx + NOCHARGE_R, CY + NOCHARGE_R), out0, out1, fill=fill, width=2)
        dy = CY - CORNER_T
        dx = math.sqrt(THREE_R ** 2 - dy ** 2)
        ang = math.degrees(math.atan2(dy, dx))
        a0, a1 = (-ang, ang) if side == 0 else (180 - ang, 180 + ang)
        d.arc((hx - THREE_R, CY - THREE_R, hx + THREE_R, CY + THREE_R), a0, a1, fill=fill, width=width)
        ex = round(hx + (dx if side == 0 else -dx))
        for cy in (CORNER_T, CORNER_B):
            xa, xb = sorted((f(L), ex))
            d.rectangle((xa, cy - 1, xb, cy + 1), fill=fill)
        # marquinhas do lance livre nas laterais do garrafão
        for i in range(3):
            mx = f(L + 70 + i * 30)
            d.rectangle((mx - 1, KEY_T - 5, mx + 1, KEY_T - 1), fill=fill)
            d.rectangle((mx - 1, KEY_B + 1, mx + 1, KEY_B + 5), fill=fill)


def paint_mask():
    def fn(d):
        d.ellipse((CX - CIRCLE_R, CY - CIRCLE_R, CX + CIRCLE_R, CY + CIRCLE_R), fill=255)
        d.rectangle((L, KEY_T, KEY_X, KEY_B), fill=255)
        d.rectangle((mirror_x(KEY_X), KEY_T, R, KEY_B), fill=255)
    return court_mask(fn)


def inside_court():
    return court_mask(lambda d: d.rectangle((L, T, R, B), fill=255))


def light_map(points, ambient, steps=4):
    """Luz em degraus (posterizada) a partir de pontos (x, y, raio, força)."""
    yy, xx = np.mgrid[0:H, 0:W]
    lm = np.full((H, W), ambient, float)
    for (x, y, r, k) in points:
        dist = np.hypot(xx - x, (yy - y) * 1.15) / r
        lm += k * np.clip(1 - dist, 0, 1) ** 1.4
    lm = np.clip(lm, -1, 1)
    # degraus com pontilhado nas bordas para não ficar com faixa lisa
    q = lm * steps + BAYER[yy % 4, xx % 4] - 0.5
    return np.round(q) / steps


def apply_light(arr, lm, tint=(255, 255, 255)):
    a = arr.astype(float)
    pos = np.clip(lm, 0, 1)[..., None]
    neg = np.clip(-lm, 0, 1)[..., None]
    a = a + (np.array(tint) - a) * pos * 0.55
    a = a * (1 - neg * 0.6)
    return np.clip(a, 0, 255).astype(np.uint8)


def finish(img, name, folder):
    folder.mkdir(parents=True, exist_ok=True)
    big = img.resize((img.width * 2, img.height * 2), Image.NEAREST)
    big.save(folder / name)
    return big


# ── texto em pixel (fonte 3x5) para pichos e placas ────────────────────
FONT = {
    "A": "010101111101101", "B": "110101110101110", "C": "011100100100011", "D": "110101101101110",
    "E": "111100110100111", "F": "111100110100100", "G": "011100101101011", "H": "101101111101101",
    "I": "111010010010111", "J": "001001001101010", "K": "101101110101101", "L": "100100100100111",
    "M": "101111111101101", "N": "110101101101101", "O": "010101101101010", "P": "110101110100100",
    "Q": "010101101110011", "R": "110101110101101", "S": "011100010001110", "T": "111010010010010",
    "U": "101101101101111", "V": "101101101101010", "W": "101101111111101", "X": "101101010101101",
    "Y": "101101010010010", "Z": "111001010100111", " ": "000000000000000", "0": "111101101101111",
    "1": "010110010010111", "2": "110001010100111", "3": "110001010001110", "4": "101101111001001",
    "5": "111100110001110", "!": "010010010000010",
}


def pixel_text(d, x, y, text, color, scale=1, outline=None):
    cx = x
    for ch in text.upper():
        g = FONT.get(ch, FONT[" "])
        for i, bit in enumerate(g):
            if bit == "1":
                px, py = cx + (i % 3) * scale, y + (i // 3) * scale
                if outline:
                    d.rectangle((px - 1, py - 1, px + scale, py + scale), fill=outline)
        cx += 4 * scale
    cx = x
    for ch in text.upper():
        g = FONT.get(ch, FONT[" "])
        for i, bit in enumerate(g):
            if bit == "1":
                px, py = cx + (i % 3) * scale, y + (i // 3) * scale
                d.rectangle((px, py, px + scale - 1, py + scale - 1), fill=color)
        cx += 4 * scale
    return cx - x


# ══════════════════════════════════════════════════════════════════════
# QUADRA DE RUA
# ══════════════════════════════════════════════════════════════════════
def quadra_rua():
    rnd = random.Random(11)
    nrng = np.random.default_rng(11)
    asphalt = [(46, 49, 57), (50, 53, 61), (54, 57, 65), (59, 62, 70)]
    # asfalto: ruído de grão em 4 tons
    n = nrng.random((H, W)) * 0.7 + nrng.random((H // 4 + 1, W // 4 + 1)).repeat(4, 0).repeat(4, 1)[:H, :W] * 0.5
    idx = np.clip((n / 1.2 * 4).astype(int), 0, 3)
    arr = np.array(asphalt, np.uint8)[idx]
    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img)
    # remendos de asfalto novo (retângulos mais escuros com borda)
    for _ in range(5):
        x, y = rnd.randint(L + 20, R - 120), rnd.randint(T + 20, B - 80)
        w, h = rnd.randint(24, 60), rnd.randint(14, 34)
        d.rectangle((x, y, x + w, y + h), fill=(45, 48, 55))
        for _ in range(w * h // 10):
            d.point((rnd.randint(x, x + w), rnd.randint(y, y + h)), fill=(49, 52, 60))
        d.rectangle((x, y, x + w, y + h), outline=(40, 42, 49))
    # pintura do garrafão e do círculo, desbotada e com grão
    pm = paint_mask()
    a = np.array(img)
    red = np.array([[160, 58, 48], [166, 62, 51], [154, 55, 46]], np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    low = nrng.random((H // 6 + 1, W // 6 + 1)).repeat(6, 0).repeat(6, 1)[:H, :W]
    ridx = np.where(low > 0.7, 1, np.where(low < 0.2, 2, 0))
    ridx = np.where(nrng.random((H, W)) > 0.93, 2, ridx)
    paint = red[ridx]
    blot = nrng.random((H // 3 + 1, W // 3 + 1)).repeat(3, 0).repeat(3, 1)[:H, :W]
    show = pm & (nrng.random((H, W)) < 0.992)
    a[show] = paint[show]
    img = Image.fromarray(a)
    d = ImageDraw.Draw(img)
    # rachaduras: linha escura com borda clara
    for _ in range(26):
        x, y = rnd.randint(L, R), rnd.randint(T, B)
        pts = [(x, y)]
        ang = rnd.uniform(0, math.tau)
        for _ in range(rnd.randint(5, 12)):
            ang += rnd.uniform(-0.9, 0.9)
            x += math.cos(ang) * rnd.uniform(3, 8)
            y += math.sin(ang) * rnd.uniform(2, 6)
            pts.append((round(x), round(y)))
        d.line([(px, py + 1) for px, py in pts], fill=(72, 75, 84))
        d.line(pts, fill=(26, 27, 32))
    # manchas de óleo
    for _ in range(6):
        x, y = rnd.randint(L + 40, R - 40), rnd.randint(T + 40, B - 40)
        for k in range(3):
            r = 10 - k * 3
            d.ellipse((x - r - k, y - r // 2, x + r, y + r // 2 + k), fill=(44 - k * 2, 46 - k * 2, 54 - k * 2))
    # linhas brancas gastas
    lines = Image.new("L", (W, H), 0)
    draw_lines(ImageDraw.Draw(lines), 255)
    lm = np.array(lines) > 0
    a = np.array(img)
    keep = lm & (nrng.random((H, W)) > 0.16)
    tone = np.where(nrng.random((H, W)) > 0.5, 226, 206)
    a[keep] = np.stack([tone, tone, tone - 8], -1)[keep]
    # faixa fora da quadra: calçada de concreto em placas
    outside = ~inside_court()
    yy, xx = np.mgrid[0:H, 0:W]
    conc = np.where(nrng.random((H, W)) > 0.5, 112, 104)
    joint = ((xx % 24) == 0) | ((yy % 24) == 0)
    cg = np.stack([conc, conc, conc + 4], -1).astype(np.uint8)
    cg[joint] = (82, 82, 88)
    band = outside & ~((xx >= L - 2) & (xx <= R + 2) & (yy >= T - 2) & (yy <= B + 2))
    a[band] = cg[band]
    # meio-fio entre calçada e quadra
    edge = outside & ~band
    a[edge] = (150, 150, 146)
    img = Image.fromarray(a)
    d = ImageDraw.Draw(img)
    # muro: concreto baixo com pichos e alambrado
    for (x0, y0, x1, y1) in ((0, 0, W - 1, WALL - 1), (0, H - WALL, W - 1, H - 1),
                             (0, 0, WALL - 1, H - 1), (W - WALL, 0, W - 1, H - 1)):
        d.rectangle((x0, y0, x1, y1), fill=(78, 78, 86))
    for x in range(0, W, 2):                                   # alambrado em losango
        for y in range(0, WALL):
            if (x + y) % 6 == 0 or (x - y) % 6 == 0:
                d.point((x, y), fill=(150, 156, 164))
                d.point((x, H - 1 - y), fill=(150, 156, 164))
    for y in range(0, H, 2):
        for x in range(0, WALL):
            if (x + y) % 6 == 0 or (x - y) % 6 == 0:
                d.point((x, y), fill=(150, 156, 164))
                d.point((W - 1 - x, y), fill=(150, 156, 164))
    for x in range(0, W, 60):                                  # postes do alambrado
        d.rectangle((x, 0, x + 2, WALL - 1), fill=(60, 62, 70))
        d.rectangle((x, H - WALL, x + 2, H - 1), fill=(60, 62, 70))
    d.line((0, WALL - 1, W, WALL - 1), fill=(48, 48, 54))
    d.line((0, H - WALL, W, H - WALL), fill=(48, 48, 54))
    # pichos na calçada perto do muro (no chão, sem volume)
    tags = [("SOUL", 120, 18, (70, 220, 150)), ("JAM", 690, 18, (250, 200, 60)),
            ("NBA RUA", 300, H - 34, (240, 90, 180)), ("ZERA", 820, H - 34, (90, 170, 255))]
    for text, x, y, c in tags:
        pixel_text(d, x, y, text, c, scale=2, outline=(20, 20, 26))
    # bueiro e tampa
    for (x, y) in ((24, 120), (W - 30, 470)):
        d.rectangle((x - 6, y - 4, x + 6, y + 4), fill=(40, 40, 44))
        for k in range(-5, 6, 2):
            d.line((x + k, y - 3, x + k, y + 3), fill=(24, 24, 28))
    # luz dos postes (posterizada, amarelada)
    lmap = light_map([(270, 150, 260, 0.38), (730, 450, 260, 0.38), (500, 300, 180, 0.12)], -0.22)
    a = apply_light(np.array(img), lmap, (255, 236, 190))
    return Image.fromarray(a)


# ══════════════════════════════════════════════════════════════════════
# GINÁSIO
# ══════════════════════════════════════════════════════════════════════
def quadra_ginasio():
    rnd = random.Random(21)
    nrng = np.random.default_rng(21)
    woods = [(196, 142, 84), (204, 150, 90), (188, 134, 78), (210, 158, 98), (182, 128, 74)]
    a = np.zeros((H, W, 3), np.uint8)
    PL = 6                                                    # altura da tábua
    for row in range(0, H, PL):
        x = -rnd.randint(0, 80)
        while x < W:
            ln = rnd.randint(60, 160)
            c = np.array(rnd.choice(woods))
            seg = slice(max(0, x), min(W, x + ln))
            a[row:row + PL, seg] = c
            # veio da madeira: uma ou duas linhas finas mais escuras
            gy = row + rnd.randint(1, PL - 2)
            a[gy, seg] = np.clip(c - 14, 0, 255)
            if rnd.random() < 0.5:
                gy2 = row + rnd.randint(1, PL - 2)
                gx0 = max(0, x + rnd.randint(0, ln // 2))
                a[gy2, gx0:min(W, gx0 + ln // 3)] = np.clip(c - 10, 0, 255)
            if 0 <= x < W:
                a[row:row + PL, x] = np.clip(c - 40, 0, 255)  # emenda
            x += ln
        a[min(H - 1, row + PL - 1), :] = np.clip(a[min(H - 1, row + PL - 1), :].astype(int) - 22, 0, 255)
    img = Image.fromarray(a)
    pm = paint_mask()
    blue = np.array([34, 86, 168])
    arr = np.array(img).astype(int)
    # tinta sobre a madeira: mantém a textura (multiplica a luminância)
    lum = arr.mean(-1, keepdims=True) / 196.0
    painted = np.clip(blue * lum, 0, 255)
    arr[pm] = painted[pm]
    # fora da quadra: madeira mais escura (verniz de fora)
    out = ~inside_court()
    arr[out] = (arr[out] * 0.72).astype(int)
    img = Image.fromarray(arr.astype(np.uint8))
    d = ImageDraw.Draw(img)
    draw_lines(d, (248, 248, 242))
    # logo no círculo central: escudo com "SS"
    d.ellipse((CX - 40, CY - 40, CX + 40, CY + 40), outline=(248, 248, 242), width=2)
    d.polygon([(CX, CY - 30), (CX + 26, CY - 16), (CX + 20, CY + 18), (CX, CY + 32), (CX - 20, CY + 18),
               (CX - 26, CY - 16)], fill=(236, 116, 40), outline=(248, 248, 242))
    pixel_text(d, CX - 13, CY - 8, "SS", (248, 248, 242), scale=4, outline=(120, 50, 16))
    # nome nas linhas de fundo, dentro do garrafão
    for side in (0, 1):
        pass
    # muro: placas de LED nas laterais e torcida em cima/embaixo
    ad_colors = [((220, 40, 50), "SOUL STRIKE"), ((30, 30, 36), "JAM 2X2"), ((40, 120, 220), "ENTERRADA!"),
                 ((240, 190, 30), "CESTA DE 3")]
    for y0 in (0, H - WALL):
        d.rectangle((0, y0, W - 1, y0 + WALL - 1), fill=(34, 30, 40))
        for x in range(1, W, 4):
            c = rnd.choice([(200, 60, 60), (60, 90, 200), (230, 210, 80), (230, 230, 230), (40, 160, 90),
                            (240, 140, 40)])
            skin = rnd.choice([(232, 190, 150), (196, 140, 100), (140, 92, 60), (98, 64, 44)])
            by = y0 + rnd.randint(2, 3)
            d.rectangle((x, by + 3, x + 2, y0 + WALL - 1), fill=c)          # camisa
            d.rectangle((x, by, x + 2, by + 2), fill=skin)                   # cabeça
            if rnd.random() < 0.25:                                          # braço levantado
                d.point((x + 3, by - 1), fill=skin)
    for x0 in (0, W - WALL):
        y = 0
        i = 0
        while y < H:
            c, txt = ad_colors[i % len(ad_colors)]
            h = 90
            d.rectangle((x0, y, x0 + WALL - 1, min(H, y + h) - 1), fill=c)
            d.rectangle((x0, y, x0 + WALL - 1, min(H, y + h) - 1), outline=(16, 16, 20))
            for k in range(y + 8, min(H, y + h) - 8, 6):                       # "letreiro" em blocos
                d.rectangle((x0 + 3, k, x0 + WALL - 4, k + 3), fill=shade(c, 0.6))
            y += h
            i += 1
    # brilho do verniz: luz forte em cima e reflexo perto das cestas
    lmap = light_map([(CX, CY, 520, 0.18), (170, CY, 160, 0.22), (W - 170, CY, 160, 0.22)], -0.05, steps=5)
    a = apply_light(np.array(img), lmap, (255, 246, 222))
    return Image.fromarray(a)


# ══════════════════════════════════════════════════════════════════════
# ARENA SOUL STRIKE
# ══════════════════════════════════════════════════════════════════════
def quadra_soul():
    rnd = random.Random(31)
    nrng = np.random.default_rng(31)
    stones = [(30, 24, 44), (34, 27, 50), (27, 22, 40), (38, 30, 55)]
    a = np.zeros((H, W, 3), np.uint8)
    TS = 20
    for ty in range(0, H, TS):
        off = (ty // TS % 2) * (TS // 2)
        for tx in range(-TS, W, TS):
            x0 = tx + off
            c = np.array(rnd.choice(stones))
            xs = slice(max(0, x0), min(W, x0 + TS))
            ys = slice(ty, min(H, ty + TS))
            a[ys, xs] = c
            # granulado
            sub = a[ys, xs]
            noise = nrng.random(sub.shape[:2]) > 0.86
            sub[noise] = np.clip(c + 7, 0, 255)
            a[ys, xs] = sub
            # junta (borda de baixo e direita escura, de cima e esquerda clara)
            a[ys, max(0, x0)] = np.clip(c + 10, 0, 255) if x0 >= 0 else a[ys, 0]
            if x0 + TS - 1 < W and x0 + TS - 1 >= 0:
                a[ys, x0 + TS - 1] = (14, 10, 22)
            a[min(H - 1, ty + TS - 1), xs] = (14, 10, 22)
            a[ty, xs] = np.clip(c + 10, 0, 255)
    img = Image.fromarray(a)
    pm = paint_mask()
    arr = np.array(img).astype(int)
    tint = np.array([74, 32, 118])
    arr[pm] = np.clip(arr[pm] * 0.5 + tint * 0.75, 0, 255)
    out = ~inside_court()
    arr[out] = (arr[out] * 0.7).astype(int)
    img = Image.fromarray(arr.astype(np.uint8))
    d = ImageDraw.Draw(img)
    # rachaduras com brilho roxo
    for _ in range(18):
        x, y = rnd.randint(L, R), rnd.randint(T, B)
        pts = [(x, y)]
        ang = rnd.uniform(0, math.tau)
        for _ in range(rnd.randint(4, 9)):
            ang += rnd.uniform(-1, 1)
            x += math.cos(ang) * rnd.uniform(3, 7)
            y += math.sin(ang) * rnd.uniform(3, 7)
            pts.append((round(x), round(y)))
        d.line(pts, fill=(96, 50, 170), width=2)
        d.line(pts, fill=(196, 150, 255))
    # linhas que brilham: halo largo escuro, halo médio, núcleo claro
    halo = Image.new("L", (W, H), 0)
    draw_lines(ImageDraw.Draw(halo), 255, width=7, dashed_inside=False)
    mid = Image.new("L", (W, H), 0)
    draw_lines(ImageDraw.Draw(mid), 255, width=5, dashed_inside=False)
    core = Image.new("L", (W, H), 0)
    draw_lines(ImageDraw.Draw(core), 255, width=LW)
    arr = np.array(img)
    hm, mm, cm = np.array(halo) > 0, np.array(mid) > 0, np.array(core) > 0
    arr[hm] = np.clip(arr[hm].astype(int) + np.array([30, 10, 60]), 0, 255)
    arr[mm] = np.clip(arr[mm].astype(int) + np.array([50, 26, 100]), 0, 255)
    arr[cm] = (176, 128, 255)
    img = Image.fromarray(arr)
    d = ImageDraw.Draw(img)
    # círculo rúnico central
    for r, c in ((46, (150, 100, 240)), (34, (120, 70, 210))):
        d.ellipse((CX - r, CY - r, CX + r, CY + r), outline=c, width=1)
    for k in range(8):
        ang = k * math.pi / 4
        x1, y1 = CX + math.cos(ang) * 34, CY + math.sin(ang) * 34
        x2, y2 = CX + math.cos(ang) * 46, CY + math.sin(ang) * 46
        d.line((x1, y1, x2, y2), fill=(150, 100, 240))
        gx, gy = round(CX + math.cos(ang + 0.39) * 40), round(CY + math.sin(ang + 0.39) * 40)
        d.rectangle((gx - 1, gy - 1, gx + 1, gy + 1), outline=(200, 160, 255))
    hexa = [(CX + math.cos(math.pi / 6 + k * math.pi / 3) * 26,
             CY + math.sin(math.pi / 6 + k * math.pi / 3) * 26) for k in range(7)]
    d.line(hexa, fill=(220, 180, 255), width=2)
    d.polygon([(CX, CY - 18), (CX + 12, CY), (CX, CY + 18), (CX - 12, CY)], outline=(200, 160, 255))
    d.ellipse((CX - 5, CY - 5, CX + 5, CY + 5), fill=(255, 140, 50), outline=(255, 220, 140))
    # runas nos garrafões (embaixo da cesta)
    for side in (0, 1):
        f = (lambda x: x) if side == 0 else mirror_x
        for i, gy in enumerate((KEY_T + 14, KEY_B - 14)):
            gx = f(L + 150)
            d.rectangle((gx - 3, gy - 3, gx + 3, gy + 3), outline=(160, 110, 245))
            d.point((gx, gy), fill=(230, 200, 255))
    # muro: pedra escura com tochas a cada 100 px
    for (x0, y0, x1, y1) in ((0, 0, W - 1, WALL - 1), (0, H - WALL, W - 1, H - 1),
                             (0, 0, WALL - 1, H - 1), (W - WALL, 0, W - 1, H - 1)):
        d.rectangle((x0, y0, x1, y1), fill=(18, 14, 28))
    for x in range(0, W, 12):
        d.line((x, 0, x, WALL - 1), fill=(26, 20, 40))
        d.line((x, H - WALL, x, H - 1), fill=(26, 20, 40))
    torches = [(x, 4) for x in range(50, W, 100)] + [(x, H - 5) for x in range(50, W, 100)]
    torches += [(4, y) for y in range(100, H - 50, 100)] + [(W - 5, y) for y in range(100, H - 50, 100)]
    for (x, y) in torches:
        d.rectangle((x - 2, y - 2, x + 2, y + 2), fill=(70, 60, 80))
        d.point((x, y), fill=(255, 230, 140))
        d.point((x - 1, y), fill=(255, 150, 50))
        d.point((x + 1, y), fill=(255, 150, 50))
    # braseiros nos cantos do muro
    for (x, y) in ((5, 5), (W - 6, 5), (5, H - 6), (W - 6, H - 6)):
        d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(60, 52, 70), outline=(30, 24, 40))
        d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(255, 120, 40))
        d.point((x, y), fill=(255, 240, 160))
    # luz: escuro nos cantos, roxo no meio, laranja das tochas
    pts = [(CX, CY, 420, 0.22), (170, CY, 140, 0.12), (W - 170, CY, 140, 0.12)]
    lmap = light_map(pts, -0.35, steps=5)
    arr = apply_light(np.array(img), lmap, (190, 140, 255))
    tl = light_map([(x, y, 40, 0.32) for (x, y) in torches], 0.0, steps=3)
    arr = apply_light(arr, tl, (255, 150, 70))
    return Image.fromarray(arr)


# ══════════════════════════════════════════════════════════════════════
# CESTAS (100x120, ampliadas para 200x240)
# ══════════════════════════════════════════════════════════════════════
THEME_HOOP = {
    "quadra_rua": dict(pole=(46, 92, 70), pole_hi=(72, 130, 100), pad=None, board=(170, 176, 184),
                       board_edge=(70, 74, 82), square=(232, 96, 40), rim=(220, 80, 36),
                       rim_dark=(140, 44, 20), net=(176, 180, 188), net_dark=(110, 114, 122), glass=False),
    "quadra_ginasio": dict(pole=(40, 46, 60), pole_hi=(80, 90, 110), pad=(30, 80, 170), board=(200, 230, 245),
                           board_edge=(245, 245, 250), square=(245, 245, 250), rim=(240, 104, 30),
                           rim_dark=(160, 60, 14), net=(250, 250, 250), net_dark=(200, 200, 206), glass=True),
    "quadra_soul": dict(pole=(40, 32, 54), pole_hi=(80, 64, 104), pad=None, board=(36, 28, 50),
                        board_edge=(120, 80, 200), square=(190, 140, 255), rim=(90, 80, 100),
                        rim_dark=(40, 34, 48), net=(130, 90, 210), net_dark=(80, 50, 140), glass=False),
}


def rim_points(front):
    """Pixels do aro (elipse de 2 px de espessura), metade da frente ou de trás."""
    pts = []
    cx, cy = RIM
    for k in range(240):
        t = k / 240 * math.tau
        x, y = cx + math.cos(t) * RIM_RX, cy + math.sin(t) * RIM_RY
        if (y >= cy) == front:
            pts.append((round(x), round(y)))
    return pts


def net_strands(front):
    """Fios da rede: de pontos no aro até o fundo da rede, cruzados em losango."""
    cx, cy = RIM
    depth = 18
    lines = []
    n = 10
    for k in range(n):
        t = k / n * math.tau
        x0, y0 = cx + math.cos(t) * RIM_RX, cy + math.sin(t) * RIM_RY
        if (y0 >= cy) != front:
            continue
        for s in (-1, 1):
            t2 = t + s * math.tau / n * 1.2
            x1 = cx + math.cos(t2) * RIM_RX * 0.55
            y1 = cy + depth + math.sin(t2) * RIM_RY * 0.55
            lines.append(((x0, y0 + 1), (x1, y1)))
    return lines


def hoop_layers(key):
    th = THEME_HOOP[key]
    back = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    front = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    d = ImageDraw.Draw(back)
    ax, ay = ANCHOR
    # sombras no chão (aro e poste)
    d.ellipse((ax - 10, ay - 3, ax + 10, ay + 3), fill=(0, 0, 0, 60))
    d.ellipse((ax - 6, ay - 2, ax + 6, ay + 2), fill=(0, 0, 0, 50))
    d.ellipse((6, ay - 3, 19, ay + 3), fill=(0, 0, 0, 70))
    # poste (x 9..15, y 35..110) com luz à esquerda
    d.rectangle((9, 35, 15, ay), fill=th["pole"] + (255,))
    d.rectangle((9, 35, 10, ay), fill=th["pole_hi"] + (255,))
    d.rectangle((15, 35, 15, ay), fill=shade(th["pole"], -0.4) + (255,))
    d.rectangle((7, ay - 2, 17, ay + 1), fill=shade(th["pole"], -0.3) + (255,))   # base
    if th["pad"]:
        d.rectangle((8, 70, 16, ay - 3), fill=th["pad"] + (255,))
        d.rectangle((8, 70, 9, ay - 3), fill=shade(th["pad"], 0.3) + (255,))
    # braço (y 38..42) com treliça
    d.rectangle((12, 38, 71, 42), fill=th["pole"] + (255,))
    d.line((12, 38, 71, 38), fill=th["pole_hi"] + (255,))
    for x in range(16, 70, 6):
        d.line((x, 39, x + 3, 41), fill=shade(th["pole"], -0.35) + (255,))
    # tabela (x 69..75, y 2..97)
    bx0, bx1, by0, by1 = 68, 72, 2, 97
    if th["glass"]:
        d.rectangle((bx0, by0, bx1, by1), fill=th["board"] + (150,))
        d.rectangle((bx0 + 2, by0 + 6, bx0 + 2, by1 - 30), fill=(255, 255, 255, 180))   # reflexo
    else:
        d.rectangle((bx0, by0, bx1, by1), fill=th["board"] + (255,))
        d.rectangle((bx0 + 1, by0 + 1, bx0 + 1, by1 - 1), fill=shade(th["board"], 0.25) + (255,))
    d.rectangle((bx0, by0, bx1, by1), outline=th["board_edge"] + (255,))
    d.rectangle((bx0 + 1, 44, bx1 - 1, 64), outline=th["square"] + (255,))           # quadrado atrás do aro
    if key == "quadra_soul":                                                           # runa na tabela
        for y in range(12, 36, 8):
            d.rectangle((bx0 + 2, y, bx1 - 2, y + 4), outline=(190, 140, 255, 255))
    # suporte do aro saindo da tabela
    d.rectangle((bx1, RIM[1] - 1, RIM[0] - RIM_RX + 1, RIM[1] + 1), fill=th["rim_dark"] + (255,))
    # rede de trás e aro de trás
    for (p0, p1) in net_strands(False):
        d.line((p0, p1), fill=th["net_dark"] + (255,))
    for (x, y) in rim_points(False):
        d.point((x, y), fill=th["rim_dark"] + (255,))
        d.point((x, y - 1), fill=th["rim"] + (255,))
    # camada da frente: rede da frente + aro da frente
    f = ImageDraw.Draw(front)
    for (p0, p1) in net_strands(True):
        f.line((p0, p1), fill=th["net"] + (255,))
    cx, cy = RIM
    f.line((cx - 7, cy + 12, cx + 7, cy + 12), fill=th["net"] + (255,))           # anel de baixo da rede
    f.line((cx - 9, cy + 7, cx + 9, cy + 7), fill=th["net"] + (200,))
    for (x, y) in rim_points(True):
        f.point((x, y + 1), fill=th["rim_dark"] + (255,))
        f.point((x, y), fill=th["rim"] + (255,))
    f.point((cx - RIM_RX + 2, cy + 2), fill=shade(th["rim"], 0.5) + (255,))         # brilho
    f.point((cx - RIM_RX + 3, cy + 3), fill=shade(th["rim"], 0.5) + (255,))
    if key == "quadra_soul":                                                         # brasas no aro
        rnd = random.Random(5)
        for (x, y) in rim_points(True)[::9]:
            f.point((x, y), fill=rnd.choice([(255, 140, 40), (255, 200, 90)]) + (255,))
    return back, front


def fire_frames():
    """Fogo animado em volta do aro (4 quadros), para quando alguém pega fogo."""
    frames = []
    cx, cy = RIM
    for fr in range(4):
        rnd = random.Random(100 + fr)
        im = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for k in range(26):
            t = k / 26 * math.tau
            x = cx + math.cos(t) * (RIM_RX + 1)
            y = cy + math.sin(t) * (RIM_RY + 1)
            hgt = rnd.randint(5, 13) + (3 if math.sin(t) > 0 else 0)
            for j in range(hgt):
                c = (255, 240, 170) if j < 2 else (255, 170, 50) if j < hgt * 0.55 else (220, 70, 30)
                wob = round(math.sin((j + fr * 2) * 0.9 + k) * 1)
                a = 255 if j < hgt - 2 else 170
                d.point((round(x) + wob, round(y) - j), fill=c + (a,))
        for _ in range(6):                                                           # faíscas
            d.point((cx + rnd.randint(-12, 12), cy - rnd.randint(14, 24)), fill=(255, 220, 120, 220))
        frames.append(im)
    return frames


# ══════════════════════════════════════════════════════════════════════
def main():
    builders = {"quadra_rua": quadra_rua, "quadra_ginasio": quadra_ginasio, "quadra_soul": quadra_soul}
    for key, fn in builders.items():
        folder = OUT / key
        bg = fn()
        finish(bg, f"fundo{key}.png", folder)
        back, front = hoop_layers(key)
        finish(back, "cesta.png", folder)
        finish(front, "aro_frente.png", folder)
        if key == "quadra_soul":
            for i, fr in enumerate(fire_frames(), 1):
                finish(fr, f"aro_fogo_{i}.png", folder)


if __name__ == "__main__":
    main()
