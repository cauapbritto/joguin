"""Os pets animados: 6 estados para cada um dos 9 bichos (os 3 da Casa e os 6 da loja de CACOS).

Mesmo caminho dos pets de sempre (desenho base em pixels grandes -> Scale2x + volume -> 70% -> contorno
fino, via gerar_pets.hd). Cada estado vira uma folha com os quadros lado a lado, todos do mesmo
tamanho e com os pés alinhados embaixo: assets/pecas/pet_<pet>_<estado>.png.

Estados: parado (4), andando (4), especial (4 a 6, a graça de cada bicho), feliz (4), susto (2) e
dormindo (2). Os desenhos de sempre (mascote_<pet>_sentado/_andando) continuam: a loja usa eles.

Uso (na raiz do repositório):  python tools/gerar_pets_anim.py
"""
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

pygame.init()
import gerar_pets as G  # noqa: E402

OUT = ROOT / "assets" / "pecas"
OB, ell, eye, EYE, GL, hd = G.OB, G.ell, G.eye, G.EYE, G.GL, G.hd
Z = (0, 0, 0, 0)


# ═════════════════ CAPIVARA ═════════════════
CAP = dict(c=(150, 104, 66), cd=(116, 78, 48), cdd=(86, 56, 34), cl=(182, 134, 88), cll=(206, 164, 112),
           nose=(64, 42, 30), lar=(250, 150, 50), folha=(70, 170, 70))


def _laranja(b, x, y):
    k = CAP
    ell(b, (x, y, 6, 5), k["lar"])
    b.p(x + 1, y + 1, (255, 210, 120))
    b.r(x + 3, y, 2, 1, (120, 80, 40))
    b.r(x + 4, y - 1, 3, 1, k["folha"]); b.p(x + 6, y - 2, k["folha"])


def _passarinho(b, x, y, asa=0):
    b.r(x, y, 4, 3, (240, 200, 60)); b.r(x + 4, y + 1, 1, 1, (230, 120, 40))
    b.p(x + 3, y, EYE)
    b.r(x - 1, y + 1 - asa, 2, 1 + asa, (200, 160, 40))
    b.p(x + 1, y + 3, (120, 80, 40)); b.p(x + 2, y + 3, (120, 80, 40))


def capivara_lado(fr=0, olho="sono", bob=0, lar_dy=0, lar_dx=0, deitada=False, boca=False):
    """De lado, virada para a direita. fr: passo 0-3 (perna)."""
    k = CAP
    b = OB(34, 24, dy=14)
    y0 = 1 + bob + (4 if deitada else 0)
    ell(b, (2, 6 + y0, 22, 12), k["c"])
    ell(b, (4, 7 + y0, 16, 4), k["cl"])
    for x, y in ((6, 11), (10, 13), (15, 11), (19, 13), (8, 15)):
        b.p(x, y + y0, k["cd"])
    if not deitada:
        lift = [(0, 2, 0, 2), (1, 1, 1, 1), (2, 0, 2, 0), (1, 1, 1, 1)][fr % 4]
        for (lx, cor), up in zip(((4, k["cd"]), (9, k["c"]), (15, k["cd"]), (19, k["c"])), lift):
            b.r(lx, 15 + y0 - up, 3, 6, cor); b.r(lx, 20 + y0 - up, 4, 1, k["cdd"])
    else:
        b.r(4, 17 + y0, 5, 2, k["cd"]); b.r(17, 17 + y0, 5, 2, k["cd"])
    hy = y0 + (1 if deitada else 0)
    b.r(19, 3 + hy, 11, 10, k["c"]); b.r(20, 3 + hy, 9, 2, k["cl"]); b.r(19, 11 + hy, 11, 2, k["cd"])
    b.r(20, 1 + hy, 3, 3, k["cd"]); b.p(21, 2 + hy, (190, 120, 110))
    if olho == "sono":
        b.r(23, 6 + hy, 3, 1, k["cdd"]); b.r(23, 7 + hy, 3, 1, EYE)
    elif olho == "fechado":
        b.r(23, 7 + hy, 3, 1, k["cdd"])
    elif olho == "aberto":
        b.r(23, 5 + hy, 3, 3, (250, 250, 250)); b.r(24, 6 + hy, 2, 2, EYE); b.p(24, 6 + hy, GL)
    elif olho == "feliz":
        b.p(23, 7 + hy, k["cdd"]); b.p(24, 6 + hy, k["cdd"]); b.p(25, 7 + hy, k["cdd"])
    b.r(27, 7 + hy, 5, 6, k["cll"]); b.r(30, 8 + hy, 2, 1, k["nose"])
    b.r(28, 11 + hy, 3, 1, k["cdd"])
    if boca:
        b.r(28, 11 + hy, 3, 2, (120, 50, 50))
    b.r(0, 8 + y0, 3, 3, k["cd"])
    _laranja(b, 22 + lar_dx, -1 + hy + lar_dy)
    return b


def capivara():
    A = {}
    A["parado"] = [hd(capivara_lado(0, bob=b_, olho=o).s, keep=[EYE, GL])
                   for b_, o in ((0, "sono"), (0, "sono"), (1, "sono"), (1, "fechado"))]
    A["andando"] = [hd(capivara_lado(f, bob=(1 if f % 2 else 0), lar_dy=-(f % 2)).s, keep=[EYE, GL])
                    for f in range(4)]
    esp = []                                                  # passarinho pousa na laranja
    for i, (px, py, asa, olho) in enumerate(((30, -6, 1, "sono"), (26, -5, 0, "sono"), (23, -4, 1, "sono"),
                                             (24, -5, 0, "fechado"), (24, -5, 0, "feliz"))):
        b = capivara_lado(0, olho=olho)
        _passarinho(b, px, py + (0 if i > 2 else -2), asa)
        esp.append(hd(b.s, keep=[EYE, GL]))
    A["especial"] = esp
    A["feliz"] = [hd(capivara_lado(0, bob=d, lar_dy=l, olho="feliz", boca=True).s, keep=[EYE, GL])
                  for d, l in ((0, 0), (-3, -3), (-5, -6), (-3, -3))]
    A["susto"] = [hd(capivara_lado(0, olho="aberto", lar_dy=-5, lar_dx=-2, bob=-2).s, keep=[EYE, GL]),
                  hd(capivara_lado(0, olho="aberto", lar_dy=-1).s, keep=[EYE, GL])]
    A["dormindo"] = [hd(capivara_lado(0, olho="fechado", deitada=True, bob=d).s, keep=[EYE, GL]) for d in (0, 1)]
    return A


# ═════════════════ CARAMELO ═════════════════
CA = dict(c=(198, 140, 70), cd=(150, 96, 46), cl=(226, 178, 110), w=(240, 224, 196), col=(200, 50, 50))


def caramelo(pose="lado", fr=0, rabo=0, olho="aberto", lingua=False, bob=0, orelha=0, pata=False):
    k = CA
    b = OB(26, 21, dy=8)
    y = bob
    if pose == "sentado":                                     # de frente, rabo balançando
        b.r(6, 9 + y, 12, 10, k["c"]); b.r(9, 12 + y, 6, 7, k["w"])
        b.r(6, 1 + y, 12, 9, k["c"])
        b.r(4, 2 + y - orelha, 3, 7, k["cd"]); b.r(17, 2 + y - orelha, 3, 7, k["cd"])
        b.r(9, 6 + y, 6, 4, k["cl"]); b.r(11, 6 + y, 2, 2, (30, 26, 28))
        if olho == "aberto":
            b.r(8, 4 + y, 2, 2, (40, 30, 26)); b.r(14, 4 + y, 2, 2, (40, 30, 26))
            b.p(8, 4 + y, (250, 250, 250)); b.p(14, 4 + y, (250, 250, 250))
        elif olho == "feliz":
            b.r(8, 4 + y, 2, 1, (40, 30, 26)); b.r(14, 4 + y, 2, 1, (40, 30, 26))
        else:
            b.r(8, 5 + y, 2, 1, (40, 30, 26)); b.r(14, 5 + y, 2, 1, (40, 30, 26))
        b.r(9, 10 + y, 6, 1, k["col"]); b.p(12, 11 + y, (240, 200, 80))
        if lingua:
            b.r(11, 9 + y, 2, 3, (230, 100, 110))
        b.r(7, 18, 3, 1, k["cl"]); b.r(14, 18, 3, 1, k["cl"])
        if pata:
            b.r(15, 12 + y, 3, 3, k["c"]); b.r(17, 10 + y, 3, 3, k["c"])
            b.r(18, 9 + y, 3, 2, k["cl"]); b.p(19, 9 + y, (120, 80, 60)); b.p(20, 10 + y, (120, 80, 60))
        ang = [(18, 14, 20, 11), (18, 14, 21, 12), (18, 14, 22, 14), (18, 14, 21, 12)][rabo % 4]
        b.r(ang[0], ang[1], 4, 2, k["c"]); b.r(ang[2], ang[3], 2, 4, k["c"])
        return b
    if pose == "deitado":
        b.r(3, 13, 18, 6, k["c"]); b.r(6, 16, 10, 3, k["w"])
        b.r(15, 9 + y, 8, 6, k["c"]); b.r(14, 10 + y, 2, 6, k["cd"])
        b.r(20, 12 + y, 3, 3, k["cl"]); b.p(22, 12 + y, (30, 26, 28))
        b.r(17, 11 + y, 2, 1, (40, 30, 26))
        b.r(15, 14 + y, 2, 2, k["col"])
        b.r(0, 15, 4, 2, k["c"])
        return b
    # de lado, virado para a direita, 4 passos
    b.r(4, 7 + y, 14, 7, k["c"]); b.r(8, 12 + y, 6, 2, k["w"])
    legs = [(0, 2, 0, 2), (1, 1, 1, 1), (2, 0, 2, 0), (1, 1, 1, 1)][fr % 4]
    for (lx, cor), up in zip(((5, k["c"]), (9, k["cd"]), (13, k["c"]), (16, k["cd"])), legs):
        b.r(lx, 13 + y - up, 2, 6, cor)
    b.r(16, 2 + y, 7, 7, k["c"]); b.r(21, 5 + y, 3, 3, k["cl"]); b.p(23, 5 + y, (30, 26, 28))
    b.r(15, 3 + y - orelha, 2, 6, k["cd"])
    if olho == "aberto":
        b.r(19, 4 + y, 2, 2, (40, 30, 26)); b.p(19, 4 + y, (250, 250, 250))
    elif olho == "feliz":
        b.r(19, 4 + y, 2, 1, (40, 30, 26))
    elif olho == "susto":
        b.r(18, 3 + y, 3, 3, (250, 250, 250)); b.p(19, 4 + y, (40, 30, 26))
    b.r(16, 8 + y, 3, 1, k["col"])
    if lingua:
        b.r(21, 8 + y, 2, 3, (230, 100, 110))
    tail = [((1, 4), (0, 2)), ((1, 3), (0, 1)), ((1, 5), (0, 4)), ((1, 3), (0, 1))][rabo % 4]
    b.r(tail[0][0], tail[0][1] + y, 3, 2, k["c"]); b.r(tail[1][0], tail[1][1] + y, 2, 3, k["c"])
    return b


def cachorro():
    A = {}
    k = [EYE, GL, (250, 250, 250)]
    A["parado"] = [hd(caramelo("sentado", rabo=r, olho=o, lingua=True).s, keep=k)
                   for r, o in ((0, "aberto"), (1, "aberto"), (2, "aberto"), (1, "fechado"))]
    A["andando"] = [hd(caramelo("lado", fr=f, rabo=f, bob=(f % 2), lingua=True).s, keep=k) for f in range(4)]
    A["especial"] = [hd(caramelo("sentado", rabo=r, olho="feliz", pata=p, orelha=o).s, keep=k)   # dá a pata
                     for r, p, o in ((0, False, 0), (1, True, 1), (2, True, 1), (3, True, 1), (0, False, 0))]
    A["feliz"] = [hd(caramelo("lado", fr=0, rabo=r, olho="feliz", lingua=True, bob=d).s, keep=k)
                  for r, d in ((0, 0), (2, -3), (0, -5), (2, -3))]
    A["susto"] = [hd(caramelo("lado", olho="susto", orelha=2, bob=-2).s, keep=k),
                  hd(caramelo("lado", olho="susto", orelha=1).s, keep=k)]
    A["dormindo"] = [hd(caramelo("deitado", bob=d).s, keep=k) for d in (0, 1)]
    return A


# ═════════════════ CAQUINHO ═════════════════
CQ = dict(cr=(90, 170, 240), cd=(44, 92, 186), cdd=(30, 56, 130), cl=(170, 224, 255), cw=(240, 252, 255))


def caquinho_q(up=0, larg=1.0, olho="aberto", orbita=0, brilho=-1, apagado=False, racha=False, pernas=False):
    k = dict(CQ)
    if apagado:
        k = {n: tuple(int(v * 0.65) for v in c) for n, c in k.items()}
    b = OB(26, 30, dy=8)
    cx = 13
    top, mid, bot = 2 - up + 3, 12 - up + 3, 24 - up
    hw = 7 * larg
    pygame.draw.polygon(b.s, k["cr"], [(cx, top + 2), (cx + hw, mid + 2), (cx, bot + 2), (cx - hw, mid + 2)])
    pygame.draw.polygon(b.s, k["cl"], [(cx, top + 2), (cx, bot + 2), (cx - hw + 1, mid + 2)])
    pygame.draw.polygon(b.s, k["cd"], [(cx, top + 4), (cx + hw - 1, mid + 2), (cx, bot + 2)])
    if brilho >= 0:                                           # faixa de brilho varrendo
        yb = top + 4 + brilho * 4
        for d in range(3):
            if b.s.get_at((cx - 3 + d, yb + 2 - d)).a:
                b.p(cx - 3 + d, yb + 2 - d, k["cw"])
    b.r(cx, top + 2, 1, bot - top, k["cdd"])
    m = mid + 2
    if olho == "aberto":
        eye(b, cx - 3, m - 2, 2, 3); eye(b, cx + 2, m - 2, 2, 3)
    elif olho == "feliz":
        for ex in (cx - 3, cx + 2):
            b.p(ex, m, k["cdd"]); b.p(ex + 1, m - 1, k["cdd"]); b.p(ex + 2, m, k["cdd"])
    elif olho == "fechado":
        b.r(cx - 3, m, 2, 1, k["cdd"]); b.r(cx + 2, m, 2, 1, k["cdd"])
    elif olho == "susto":
        b.r(cx - 4, m - 3, 3, 4, (250, 250, 250)); b.r(cx + 2, m - 3, 3, 4, (250, 250, 250))
        b.p(cx - 3, m - 2, EYE); b.p(cx + 3, m - 2, EYE)
    if olho == "susto":
        b.r(cx - 1, m + 3, 3, 2, k["cdd"])
    else:
        b.r(cx - 1, m + 3, 3, 1, k["cdd"]); b.p(cx - 2, m + 2, k["cdd"]); b.p(cx + 2, m + 2, k["cdd"])
    b.p(cx - 5, m + 2, (250, 170, 200)); b.p(cx + 5, m + 2, (250, 170, 200))
    if racha:
        for x, y in ((cx + 2, top + 5), (cx + 3, top + 6), (cx + 2, top + 7), (cx + 3, top + 8)):
            b.p(x, y, k["cw"])
    for i in range(3):                                         # cacos em órbita
        a = orbita * math.pi / 4 + i * 2 * math.pi / 3
        ox, oy = cx + math.cos(a) * 11, mid + 2 + math.sin(a) * 4 - 3
        b.r(round(ox), round(oy), 2, 3, k["cl"]); b.p(round(ox), round(oy), k["cw"])
    if pernas:
        b.r(cx - 3, bot + 2, 2, 3, k["cd"]); b.r(cx + 2, bot + 2, 2, 3, k["cd"])
    return b


def caquinho():
    A = {}
    k = [EYE, GL, CQ["cw"]]
    A["parado"] = [hd(caquinho_q(up=u, orbita=i, brilho=(i if i < 4 else -1)).s, keep=k)
                   for i, u in enumerate((0, 1, 2, 1))]
    A["andando"] = [hd(caquinho_q(up=2 + (i % 2), orbita=i * 2).s, keep=k) for i in range(4)]
    A["especial"] = [hd(caquinho_q(up=2, larg=l, olho=o, orbita=i * 2, brilho=b_).s, keep=k)   # rodopio
                     for i, (l, o, b_) in enumerate(((1, "aberto", -1), (0.6, "aberto", -1), (0.2, "fechado", -1),
                                                    (0.6, "feliz", -1), (1, "feliz", 1), (1, "feliz", 3)))]
    A["feliz"] = [hd(caquinho_q(up=u, olho="feliz", orbita=i * 2, brilho=i).s, keep=k)
                  for i, u in enumerate((2, 5, 7, 5))]
    A["susto"] = [hd(caquinho_q(up=4, olho="susto", racha=True).s, keep=k),
                  hd(caquinho_q(up=3, olho="susto", larg=0.9, racha=True).s, keep=k)]
    A["dormindo"] = [hd(caquinho_q(up=u, olho="fechado", apagado=True, pernas=True).s, keep=k) for u in (0, 0)]
    return A




def poly(b, pts, c):
    """Polígono que respeita a origem descida do OB."""
    pygame.draw.polygon(b.s, c, [(x, y + getattr(b, 'dy', 0)) for x, y in pts])


# ═════════════════ GATO ═════════════════
GA = dict(o=(226, 140, 60), od=(184, 100, 40), odd=(140, 72, 30), w=(250, 244, 236), eye=(90, 170, 80),
          gl=(250, 250, 220), nose=(230, 120, 130))


def gato_frente(rabo=0, olho="aberto", pata=False, lingua=False, bob=0):
    """Sentado de frente (como o do sofá). rabo 0-3 balança, pata = lambendo a pata."""
    k = GA
    b = OB(22, 18, dy=6)
    y = bob
    b.r(5, 8 + y, 10, 9 - y, k["o"]); b.r(7, 12 + y, 6, 5 - y, k["w"])
    b.r(5, 2 + y, 10, 7, k["o"])
    poly(b, [(5, 3 + y), (6, 0 + y), (8, 2 + y)], k["o"])
    poly(b, [(12, 2 + y), (14, 0 + y), (15, 3 + y)], k["o"])
    b.p(6, 1 + y, (240, 160, 160)); b.p(13, 1 + y, (240, 160, 160))
    b.r(6, 4 + y, 2, 1, k["od"]); b.r(12, 4 + y, 2, 1, k["od"])      # listrinhas da testa
    b.p(9, 3 + y, k["od"]); b.p(10, 3 + y, k["od"])
    if olho == "aberto":
        b.r(7, 5 + y, 2, 2, k["eye"]); b.r(11, 5 + y, 2, 2, k["eye"])
        b.p(7, 5 + y, k["gl"]); b.p(11, 5 + y, k["gl"])
    elif olho == "feliz":
        b.p(7, 6 + y, k["odd"]); b.p(8, 5 + y, k["odd"]); b.p(11, 5 + y, k["odd"]); b.p(12, 6 + y, k["odd"])
    else:
        b.r(7, 6 + y, 2, 1, k["odd"]); b.r(11, 6 + y, 2, 1, k["odd"])
    b.p(10, 7 + y, k["nose"]); b.r(9, 8 + y, 3, 1, k["w"])
    if lingua:
        b.p(10, 9 + y, (240, 120, 140))
    b.r(6, 16, 3, 1, k["w"]); b.r(11, 16, 3, 1, k["w"])
    if pata:                                                  # pata levantada até a boca
        b.r(9, 9 + y, 3, 4, k["o"]); b.r(9, 9 + y, 3, 1, k["w"])
    tails = [((15, 12), (17, 9)), ((15, 12), (18, 10)), ((15, 13), (18, 12)), ((15, 12), (18, 10))]
    (ax, ay), (cx, cy) = tails[rabo % 4]
    b.r(ax, ay, 3, 2, k["o"]); b.r(cx, cy, 2, 4, k["o"]); b.p(cx, cy, k["od"])
    return b


def gato_lado(fr=0, olho="aberto", bob=0, rabo_up=0, arco=0, espreguica=False):
    """De lado, virado para a direita. arco = costas arrepiadas (susto)."""
    k = GA
    b = OB(22, 18, dy=8)
    y = bob
    if espreguica:                                            # frente baixa, bumbum para cima
        poly(b, [(3, 5 + y), (15, 10 + y), (15, 13 + y), (3, 11 + y)], k["o"])
        b.r(3, 10 + y, 2, 7 - y, k["o"]); b.r(6, 10 + y, 2, 7 - y, k["od"])
        b.r(13, 15, 6, 2, k["o"]); b.r(16, 14, 4, 2, k["od"])
        b.r(13, 7 + y + 2, 6, 6, k["o"])
        hx, hy = 13, 9 + y
    else:
        b.r(4, 7 + y - arco, 12, 6, k["o"])
        if arco:
            b.r(6, 5 + y, 8, 3, k["o"])
            for x in (6, 9, 12):
                b.p(x, 4 + y, k["od"])
        legs = [(0, 2, 0, 2), (1, 1, 1, 1), (2, 0, 2, 0), (1, 1, 1, 1)][fr % 4]
        for (lx, cor), up in zip(((4, k["o"]), (8, k["od"]), (12, k["o"]), (14, k["od"])), legs):
            b.r(lx, 12 + y - up, 2, 5, cor)
        for x in (6, 10):
            b.r(x, 7 + y - arco, 1, 5, k["od"])
        b.r(7, 11 + y, 5, 2, k["w"])
        hx, hy = 13, 2 + y - arco
    b.r(hx, hy, 6, 6, k["o"])
    poly(b, [(hx, hy + 1), (hx + 1, hy - 2), (hx + 3, hy)], k["o"])
    poly(b, [(hx + 4, hy), (hx + 5, hy - 2), (hx + 6, hy + 1)], k["o"])
    if olho == "aberto":
        b.r(hx + 3, hy + 2, 2, 2, k["eye"]); b.p(hx + 3, hy + 2, k["gl"])
    elif olho == "susto":
        b.r(hx + 2, hy + 1, 3, 3, (250, 250, 250)); b.p(hx + 3, hy + 2, (30, 30, 30))
    elif olho == "feliz":
        b.p(hx + 3, hy + 3, k["odd"]); b.p(hx + 4, hy + 2, k["odd"])
    else:
        b.r(hx + 3, hy + 3, 2, 1, k["odd"])
    b.p(hx + 6, hy + 4, k["nose"]); b.r(hx + 3, hy + 5, 3, 1, k["w"])
    if espreguica:
        b.r(1, 4 + y, 3, 2, k["o"]); b.r(0, 1 + y, 2, 4, k["o"])
    else:
        b.r(2, 7 + y - arco, 3, 2, k["o"])                    # rabo grudado nas costas
        b.r(1, 3 + y - arco - 2 * rabo_up, 2, 5 + 2 * rabo_up, k["o"]); b.p(1, 3 + y - arco - 2 * rabo_up, k["od"])
    return b


def gato_dormindo(bob=0):
    k = GA
    b = OB(22, 18, dy=4)
    ell(b, (2, 9 + bob, 18, 9 - bob), k["o"])                 # bolinha enrolada
    for x in (6, 10, 14):
        b.r(x, 10 + bob, 1, 3, k["od"])
    b.r(12, 9 + bob, 7, 5, k["o"])
    poly(b, [(12, 9 + bob), (13, 7 + bob), (14, 9 + bob)], k["o"])
    poly(b, [(17, 9 + bob), (18, 7 + bob), (19, 9 + bob)], k["o"])
    b.r(14, 11 + bob, 2, 1, k["odd"]); b.r(17, 11 + bob, 1, 1, k["odd"])
    b.r(3, 15, 12, 2, k["o"]); b.r(3, 15, 12, 1, k["od"])        # rabo abraçando
    return b


def gato():
    k = [EYE, GL, GA["eye"], GA["gl"], (250, 250, 250)]
    A = {}
    A["parado"] = [hd(gato_frente(rabo=r, olho=o, bob=b_).s, keep=k)
                   for r, o, b_ in ((0, "aberto", 0), (1, "aberto", 0), (2, "aberto", 1), (1, "fechado", 1))]
    A["andando"] = [hd(gato_lado(f, bob=f % 2).s, keep=k) for f in range(4)]
    A["especial"] = [hd(gato_frente(pata=True, olho="fechado", lingua=l).s, keep=k) for l in (False, True, True)] + \
                    [hd(gato_lado(0, espreguica=True, olho="fechado").s, keep=k),
                     hd(gato_lado(0, espreguica=True, olho="feliz").s, keep=k)]
    A["feliz"] = [hd(gato_lado(0, bob=d, olho="feliz", rabo_up=1).s, keep=k) for d in (0, -3, -5, -3)]
    A["susto"] = [hd(gato_lado(0, olho="susto", arco=2, rabo_up=2, bob=-2).s, keep=k),
                  hd(gato_lado(0, olho="susto", arco=2, rabo_up=2).s, keep=k)]
    A["dormindo"] = [hd(gato_dormindo(d).s, keep=k) for d in (0, 1)]
    return A


# ═════════════════ PAPAGAIO ═════════════════
PA = dict(g=(60, 170, 70), gd=(34, 120, 50), gl=(120, 210, 100), y=(250, 210, 60), r=(220, 60, 50),
          bl=(60, 120, 220), bico=(60, 60, 64), bicod=(40, 40, 44))


def papagaio_pousado(cab=0, olho="aberto", bob=0, eri=False, cab_dy=0):
    """Pousado de lado (sem o poleiro). cab = cabeça para os lados (dança), eri = penas eriçadas."""
    k = PA
    b = OB(20, 20, dy=6)
    y, hx, hy = bob, cab, bob + cab_dy
    b.r(6, 8 + y, 8, 10, k["g"]); b.r(5, 9 + y, 3, 8, k["gd"])
    if eri:
        for x, yy in ((4, 8), (3, 11), (14, 9), (15, 12), (8, 7)):
            b.r(x, yy + y, 2, 2, k["gl"])
    b.r(6, 15 + y, 3, 3, k["r"]); b.r(7, 17 + y, 4, 3, k["gd"])
    b.r(8, 17 + y, 2, 3, k["bl"])
    b.r(8, 2 + hy, 6, 6, k["g"] if not eri else k["gl"]); b.r(9 + hx, 3 + hy, 4, 2, k["y"])
    b.r(8 + hx, 1 + hy, 4, 2, k["bl"])
    b.r(12 + hx, 4 + hy, 3, 3, k["bico"]); b.p(14 + hx, 6 + hy, k["bicod"])
    if olho == "aberto":
        b.r(10 + hx, 4 + hy, 1, 1, (30, 30, 30)); b.p(10 + hx, 3 + hy, (250, 250, 250))
    elif olho == "susto":
        b.r(9 + hx, 3 + hy, 2, 2, (250, 250, 250)); b.p(10 + hx, 4 + hy, (30, 30, 30))
    elif olho == "feliz":
        b.p(9 + hx, 4 + hy, (30, 30, 30)); b.p(10 + hx, 3 + hy, (30, 30, 30))
    else:
        b.r(9 + hx, 4 + hy, 2, 1, (30, 30, 30))
    b.r(8, 18, 1, 2, (110, 110, 120)); b.r(11, 18, 1, 2, (110, 110, 120))
    return b


def papagaio_voando(asa=0, olho="aberto", bob=0):
    """Voando de lado. asa 0-3: em cima, meio, embaixo, meio."""
    k = PA
    b = OB(20, 20, dy=6)
    y = bob
    b.r(6, 10 + y, 8, 6, k["g"]); b.r(13, 10 + y, 3, 3, k["g"])
    b.r(15, 11 + y, 2, 2, k["bico"]); b.r(13, 10 + y, 2, 1, k["y"])
    if olho == "feliz":
        b.p(14, 11 + y, (30, 30, 30))
    else:
        b.p(14, 11 + y, (30, 30, 30)); b.p(14, 10 + y, (250, 250, 250))
    tip = [(2, 2), (1, 7), (3, 17), (1, 7)][asa % 4]
    poly(b, [(7, 10 + y), (tip[0], tip[1] + y), (12, 9 + y + (3 if asa % 4 == 2 else 0))], k["gd"])
    poly(b, [(8, 10 + y), (tip[0] + 3, tip[1] + 1 + y), (11, 9 + y + (3 if asa % 4 == 2 else 0))], k["gl"])
    b.r(tip[0] + 1, tip[1] + y, 3, 2, k["r"])
    b.r(1, 13 + y, 6, 2, k["bl"]); b.r(2, 15 + y, 4, 1, k["r"])
    return b


def papagaio():
    k = [(250, 250, 250), (30, 30, 30)]
    A = {}
    A["parado"] = [hd(papagaio_pousado(olho=o, bob=b_).s, keep=k)
                   for o, b_ in (("aberto", 0), ("aberto", 0), ("aberto", 1), ("fechado", 0))]
    A["andando"] = [hd(papagaio_voando(a, bob=(1 if a == 2 else 0)).s, keep=k) for a in range(4)]
    A["especial"] = [hd(papagaio_pousado(cab=c, bob=d, olho="feliz").s, keep=k)                 # dancinha
                     for c, d in ((0, 0), (-1, 1), (0, 0), (1, 1), (0, 0), (-1, 1))]
    A["feliz"] = [hd(papagaio_voando(a, bob=d, olho="feliz").s, keep=k) for a, d in ((0, 0), (2, -3), (0, -5), (2, -3))]
    A["susto"] = [hd(papagaio_pousado(olho="susto", eri=True, bob=-2).s, keep=k),
                  hd(papagaio_pousado(olho="susto", eri=True).s, keep=k)]
    A["dormindo"] = [hd(papagaio_pousado(olho="fechado", cab_dy=d + 2, cab=-1).s, keep=k) for d in (0, 1)]
    return A


# ═════════════════ MICO ═════════════════
MI = dict(o=(238, 150, 40), od=(204, 112, 26), odd=(160, 80, 20), ol=(255, 196, 80), oll=(255, 226, 140),
          face=(124, 74, 54), faced=(86, 50, 36), moeda=(250, 210, 70), moedad=(200, 150, 40))


def mico_frente(olho="aberto", bracos="baixo", moeda=False, juba=0, bob=0, rabo=0):
    k = MI
    b = OB(26, 26, dy=8)
    y = bob
    ell(b, (2 - juba, 0 + y - juba, 20 + 2 * juba, 17 + 2 * juba), k["o"])      # juba
    ell(b, (3, 1 + y, 16, 8), k["ol"])
    for x, yy in ((3, 7), (2, 10), (20, 7), (21, 10), (5, 3), (17, 3), (11, 0)):
        b.r(x - (juba if x < 11 else -juba), yy + y, 2, 2, k["od"])
    ell(b, (7, 4 + y, 10, 10), k["face"]); b.r(8, 12 + y, 8, 2, k["faced"])
    if olho == "aberto":
        eye(b, 9, 7 + y); eye(b, 13, 7 + y)
    elif olho == "susto":
        b.r(8, 6 + y, 3, 3, (250, 250, 250)); b.r(13, 6 + y, 3, 3, (250, 250, 250))
        b.p(9, 7 + y, EYE); b.p(14, 7 + y, EYE)
    elif olho == "feliz":
        for ex in (9, 13):
            b.p(ex, 8 + y, k["faced"]); b.p(ex + 1, 7 + y, k["faced"])
    else:
        b.r(9, 8 + y, 2, 1, k["faced"]); b.r(13, 8 + y, 2, 1, k["faced"])
    b.r(11, 10 + y, 2, 1, (60, 34, 26))
    b.r(10, 12 + y, 4, 1, (90, 50, 40) if olho != "susto" else (60, 30, 30))
    ell(b, (6, 14 + y, 12, 10 - y), k["o"]); ell(b, (8, 15 + y, 6, 5), k["ol"])
    if bracos == "cima":
        b.r(5, 9 + y, 2, 6, k["od"]); b.r(17, 9 + y, 2, 6, k["od"])
        b.r(5, 8 + y, 2, 1, k["face"]); b.r(17, 8 + y, 2, 1, k["face"])
    elif bracos == "boca":
        b.r(8, 13 + y, 2, 3, k["od"]); b.r(14, 13 + y, 2, 3, k["od"])
    else:
        b.r(7, 17 + y, 2, 4, k["od"]); b.r(15, 17 + y, 2, 4, k["od"])
        b.r(7, 21 + y, 2, 1, k["face"]); b.r(15, 21 + y, 2, 1, k["face"])
    if moeda:
        ell(b, (10, 11 + y, 5, 5), k["moeda"]); b.p(11, 12 + y, (255, 245, 180)); b.p(13, 14 + y, k["moedad"])
    b.r(7, 23, 4, 2, k["od"]); b.r(13, 23, 4, 2, k["od"])
    b.r(7, 24, 4, 1, k["face"]); b.r(13, 24, 4, 1, k["face"])
    tx = 19 + (1 if rabo else 0)
    b.r(17, 21, 3, 2, k["o"]); b.r(tx, 16, 2, 6, k["od"])
    b.r(tx + 1, 12, 2, 5, k["o"]); b.r(tx - 1, 11, 3, 2, k["ol"])
    return b


def mico_lado(fr=0, olho="aberto", bob=0):
    k = MI
    b = OB(28, 22, dy=6)
    y = bob
    ell(b, (4, 9 + y, 14, 7), k["o"]); ell(b, (6, 9 + y, 10, 3), k["ol"])
    legs = [(0, 2, 0, 2), (1, 1, 1, 1), (2, 0, 2, 0), (1, 1, 1, 1)][fr % 4]
    for (x, c2), up in zip(((5, k["od"]), (9, k["o"]), (12, k["od"]), (15, k["o"])), legs):
        b.r(x, 14 + y - up, 2, 6, c2); b.r(x, 19 + y - up, 3, 1, k["face"])
    ell(b, (14, 1 + y, 13, 13), k["o"]); ell(b, (15, 2 + y, 9, 5), k["ol"])
    for x, yy in ((14, 6), (15, 10), (24, 3), (19, 1)):
        b.r(x, yy + y, 2, 2, k["od"])
    ell(b, (19, 4 + y, 8, 8), k["face"])
    if olho == "feliz":
        b.p(22, 7 + y, k["faced"]); b.p(23, 6 + y, k["faced"])
    else:
        eye(b, 22, 6 + y)
    b.r(25, 9 + y, 2, 1, (60, 34, 26)); b.r(23, 11 + y, 3, 1, k["faced"])
    wag = [0, 1, 2, 1][fr % 4]
    b.r(1, 10 + y, 5, 2, k["o"])                              # rabo saindo do corpo
    b.r(0, 5 + y + wag, 2, 6 - wag, k["o"]); b.r(1, 4 + y + wag, 3, 2, k["ol"])
    return b


def mico_dormindo(bob=0):
    k = MI
    b = OB(26, 20, dy=4)
    ell(b, (2, 4 + bob, 20, 16 - bob), k["o"])
    ell(b, (4, 5 + bob, 14, 6), k["ol"])
    ell(b, (8, 8 + bob, 9, 8), k["face"])
    b.r(9, 12 + bob, 2, 1, k["faced"]); b.r(14, 12 + bob, 2, 1, k["faced"])
    b.r(2, 16, 20, 3, k["od"]); b.r(19, 15, 4, 2, k["o"])         # rabo enrolando
    return b


def mico():
    k = [EYE, GL, (250, 250, 250)]
    A = {}
    A["parado"] = [hd(mico_frente(olho=o, rabo=r, bob=b_).s, keep=k)
                   for o, r, b_ in (("aberto", 0, 0), ("aberto", 1, 0), ("aberto", 0, 1), ("fechado", 1, 0))]
    A["andando"] = [hd(mico_lado(f, bob=f % 2).s, keep=k) for f in range(4)]
    A["especial"] = [hd(mico_frente(olho="aberto", bracos="baixo", moeda=False).s, keep=k),
                     hd(mico_frente(olho="aberto", bracos="boca", moeda=True).s, keep=k),
                     hd(mico_frente(olho="fechado", bracos="boca", moeda=True, bob=1).s, keep=k),
                     hd(mico_frente(olho="fechado", bracos="boca", moeda=True).s, keep=k),
                     hd(mico_frente(olho="feliz", bracos="cima").s, keep=k)]
    A["feliz"] = [hd(mico_frente(olho="feliz", bracos="cima", bob=d, rabo=i % 2).s, keep=k)
                  for i, d in enumerate((0, -3, -5, -3))]
    A["susto"] = [hd(mico_frente(olho="susto", juba=2, bob=-2, bracos="cima").s, keep=k),
                  hd(mico_frente(olho="susto", juba=1).s, keep=k)]
    A["dormindo"] = [hd(mico_dormindo(d).s, keep=k) for d in (0, 1)]
    return A


# ═════════════════ TUIUIÚ ═════════════════
TU = dict(w=(240, 240, 236), wd=(198, 200, 208), wl=(255, 255, 252), bk=(30, 28, 34), bkl=(70, 66, 80),
          r=(214, 48, 48), rd=(160, 30, 34), bico=(70, 64, 70), bicod=(44, 40, 46), olho=(240, 200, 60))


def tuiuiu_lado(fr=0, asa=0, olho="aberto", bob=0, pesc=0, bico_aberto=False, cab_baixa=0):
    """De lado. asa 0 fechada, 1 meio, 2 aberta. pesc = pescoço esticado (susto)."""
    k = TU
    b = OB(28, 28, dy=10)
    y = bob
    ell(b, (3, 11 + y, 13, 10), k["w"]); ell(b, (4, 12 + y, 7, 4), k["wl"])
    if asa == 0:
        b.r(4, 13 + y, 8, 4, k["wd"]); b.r(4, 16 + y, 7, 1, (170, 170, 180))
    else:
        tip = (0, 4) if asa == 1 else (-1, -2)
        pygame.draw.polygon(b.s, k["wd"], [(5, 12 + y + b.dy), (tip[0] + 1, tip[1] + y + b.dy), (4, tip[1] + y - 1 + b.dy), (12, 11 + y + b.dy)])
        pygame.draw.polygon(b.s, k["wl"], [(6, 12 + y + b.dy), (tip[0] + 3, tip[1] + 1 + y + b.dy), (11, 11 + y + b.dy)])
        b.r(tip[0] + 1, tip[1] + y, 3, 1, k["bk"])
    nx, ny = 11, 4 + y - pesc + cab_baixa
    b.r(nx, ny, 5, 9 + pesc - cab_baixa, k["bk"]); b.r(nx + 1, ny + 1, 1, 6, k["bkl"])
    b.r(nx, 9 + y, 5, 3, k["r"]); b.r(nx, 11 + y, 5, 1, k["rd"])
    ell(b, (nx, ny - 4, 8, 6), k["bk"])
    hy = ny - 4
    if olho == "aberto":
        eye(b, nx + 4, hy + 2, 1, 1, k["olho"])
    elif olho == "susto":
        b.r(nx + 3, hy + 1, 2, 2, (250, 250, 250)); b.p(nx + 4, hy + 2, k["bk"])
    elif olho == "feliz":
        b.p(nx + 3, hy + 3, k["olho"]); b.p(nx + 4, hy + 2, k["olho"])
    else:
        b.r(nx + 3, hy + 3, 2, 1, k["bkl"])
    if bico_aberto:
        b.r(nx + 7, hy + 2, 8, 1, k["bico"]); b.r(nx + 7, hy + 5, 7, 1, k["bicod"])
        b.p(nx + 14, hy + 3, k["bico"])
    else:
        b.r(nx + 7, hy + 3, 8, 2, k["bico"]); b.r(nx + 7, hy + 4, 7, 1, k["bicod"])
    legs = [(0, 2), (1, 1), (2, 0), (1, 1)][fr % 4]
    b.r(6 - legs[0] // 2, 21 + y, 1, 6 - y - (legs[0] - 1 if legs[0] == 2 else 0), k["bk"])
    b.r(11 + legs[1] // 2, 21 + y, 1, 6 - y - (legs[1] - 1 if legs[1] == 2 else 0), k["bk"])
    b.r(5 - legs[0] // 2, 26, 3, 1, k["bk"]); b.r(10 + legs[1] // 2, 26, 3, 1, k["bk"])
    return b


def tuiuiu():
    k = [GL, TU["olho"], (250, 250, 250)]
    A = {}
    A["parado"] = [hd(tuiuiu_lado(1, olho=o, bob=b_).s, keep=k)
                   for o, b_ in (("aberto", 0), ("aberto", 0), ("aberto", 1), ("fechado", 0))]
    A["andando"] = [hd(tuiuiu_lado(f, bob=f % 2).s, keep=k) for f in range(4)]
    A["especial"] = [hd(tuiuiu_lado(1, asa=a, bico_aberto=bo, olho="feliz" if a == 2 else "aberto").s, keep=k)
                     for a, bo in ((0, False), (1, False), (2, False), (2, True), (2, False), (2, True))]
    A["feliz"] = [hd(tuiuiu_lado(1, asa=2, bob=d, olho="feliz", bico_aberto=d < -3).s, keep=k) for d in (0, -3, -5, -3)]
    A["susto"] = [hd(tuiuiu_lado(1, asa=1, olho="susto", pesc=3, bob=-2).s, keep=k),
                  hd(tuiuiu_lado(1, olho="susto", pesc=2).s, keep=k)]
    A["dormindo"] = [hd(tuiuiu_lado(1, olho="fechado", cab_baixa=4 + d, bob=1).s, keep=k) for d in (0, 1)]
    return A


# ═════════════════ JABUTI ═════════════════
JA = dict(s=(126, 98, 50), sd=(88, 66, 32), sdd=(60, 44, 22), sl=(174, 142, 78), k=(156, 136, 86),
          kd=(118, 100, 60), kl=(190, 172, 118), y=(236, 186, 60))


def jabuti_q(fr=0, cabeca=1.0, pernas=True, olho="aberto", bob=0):
    """cabeca 0..1: o quanto a cabeça está para fora do casco."""
    k = JA
    b = OB(30, 18, dy=6)
    y = bob
    if cabeca > 0:
        hx = 14 + round(7 * cabeca)
        b.r(hx, 6 + y, 7, 6, k["k"]); b.r(hx + 1, 6 + y, 5, 1, k["kl"]); b.r(hx, 11 + y, 7, 1, k["kd"])
        if olho == "aberto":
            eye(b, hx + 3, 7 + y)
        elif olho == "susto":
            b.r(hx + 2, 6 + y, 3, 3, (250, 250, 250)); b.p(hx + 3, 7 + y, EYE)
        elif olho == "feliz":
            b.p(hx + 3, 8 + y, k["kd"]); b.p(hx + 4, 7 + y, k["kd"])
        else:
            b.r(hx + 3, 8 + y, 2, 1, k["kd"])
        b.p(hx + 6, 9 + y, k["kd"]); b.r(hx + 4, 10 + y, 3, 1, k["kd"])
        b.p(hx + 1, 9 + y, k["y"]); b.p(hx + 2, 7 + y, k["y"])
    if pernas:
        st = [(0, 1, 0, 1), (1, 0, 1, 0)][fr % 2] if fr >= 0 else (0, 0, 0, 0)
        for (lx, ly, cc), s in zip(((4, 12, k["kd"]), (8, 13, k["k"]), (16, 13, k["k"]), (19, 12, k["kd"])), st):
            b.r(lx + s, ly + y - s, 4, 4, cc); b.r(lx + s, ly + 3 + y - s, 4, 1, k["kd"]); b.p(lx + 1 + s, ly + 3 + y - s, k["kl"])
    ell(b, (2, 1 + y, 22, 14), k["s"]); ell(b, (4, 2 + y, 16, 5), k["sl"])
    b.r(3, 12 + y, 20, 2, k["sdd"]); b.r(2, 11 + y, 22, 1, k["sd"])
    for cx, cy in ((8, 4), (13, 3), (18, 4), (6, 8), (12, 8), (17, 8)):
        b.r(cx - 1, cy + y, 4, 3, k["sd"]); b.r(cx, cy + 1 + y, 2, 1, k["y"]); b.p(cx - 1, cy + y, k["sdd"])
    if pernas:
        b.r(0, 9 + y, 3, 2, k["kd"])
    return b


def jabuti():
    k = [EYE, GL, (250, 250, 250)]
    A = {}
    A["parado"] = [hd(jabuti_q(-1, olho=o).s, keep=k) for o in ("aberto", "aberto", "aberto", "fechado")]
    A["andando"] = [hd(jabuti_q(f, bob=(f == 1)).s, keep=k) for f in range(4)]
    A["especial"] = [hd(jabuti_q(-1, cabeca=c, pernas=p, olho=o).s, keep=k)                   # entra e sai do casco
                     for c, p, o in ((1, True, "aberto"), (0.5, True, "fechado"), (0, False, "fechado"),
                                     (0, False, "fechado"), (0.4, False, "aberto"), (1, True, "feliz"))]
    A["feliz"] = [hd(jabuti_q(-1, olho="feliz", bob=d).s, keep=k) for d in (0, -2, -4, -2)]
    A["susto"] = [hd(jabuti_q(-1, cabeca=0.3, olho="susto", bob=-2).s, keep=k),
                  hd(jabuti_q(-1, cabeca=0, pernas=False).s, keep=k)]
    A["dormindo"] = [hd(jabuti_q(-1, cabeca=0.2, pernas=False, olho="fechado", bob=d).s, keep=k) for d in (0, 1)]
    return A


# ═════════════════ MINI-DRONE ═════════════════
DR = dict(m=(156, 166, 184), md=(100, 108, 128), mdd=(66, 72, 90), ml=(214, 222, 236), cy=(90, 236, 230),
          cyd=(40, 150, 150), lag=(240, 90, 60), red=(250, 70, 70), redl=(255, 190, 190), cw=(220, 255, 250))


def drone_q(up=0, helice=0, tela="feliz", pousado=False, jato=0, coracao=0):
    k = DR
    b = OB(28, 22, dy=10)
    ell(b, (7, 6 - up, 14, 11), k["m"]); ell(b, (8, 6 - up, 10, 4), k["ml"])
    b.r(7, 14 - up, 14, 2, k["md"])
    b.r(9, 8 - up, 10, 6, (20, 22, 30)); b.r(9, 8 - up, 10, 1, (50, 56, 70))
    t = 10 - up
    if tela == "feliz":
        b.r(11, t, 2, 2, k["cy"]); b.r(16, t, 2, 2, k["cy"]); b.p(11, t, k["cw"]); b.p(16, t, k["cw"])
        b.r(13, t + 2, 3, 1, k["cyd"])
    elif tela == "pisca":
        b.r(11, t + 1, 2, 1, k["cy"]); b.r(16, t + 1, 2, 1, k["cy"]); b.r(13, t + 2, 3, 1, k["cyd"])
    elif tela == "risada":
        for ex in (11, 16):
            b.p(ex, t + 1, k["cy"]); b.p(ex + 1, t, k["cy"])
        b.r(12, t + 2, 5, 1, k["cy"]); b.r(13, t + 3, 3, 1, k["cy"])
    elif tela == "coracao":
        for row, line in enumerate((".X.X.", "XXXXX", ".XXX.", "..X..")):
            for col, ch in enumerate(line):
                if ch == "X":
                    b.p(12 + col, t - 1 + row, k["red"])
    elif tela == "alerta":
        b.r(9, 8 - up, 10, 6, (60, 14, 18))
        b.r(14, t - 1, 1, 3, k["red"]); b.p(14, t + 3, k["red"])
    elif tela == "zz":                                         # tela apagada, olhinhos fechados
        b.r(11, t + 1, 2, 1, k["cyd"]); b.r(16, t + 1, 2, 1, k["cyd"])
    b.r(12, 15 - up, 4, 1, k["lag"]); b.p(12, 15 - up, (255, 170, 130))
    for x, dx in ((0, 1), (20, -1)):
        b.r(x + 4 if dx > 0 else x, 8 - up, 4, 2, k["md"])
        b.r(x + 2, 6 - up, 2, 3, k["mdd"])
        w = [8, 5, 2, 5][helice % 4]
        b.r(x + 4 - w // 2, 4 - up, w, 1, (70, 70, 84))
        if helice % 2 == 0:
            b.p(x + 4 - w // 2, 4 - up, (200, 200, 220))
        b.r(x + 2, 5 - up, 4, 1, k["mdd"])
    b.r(13, 1 - up, 2, 5, k["md"])
    b.r(12, 0 - up, 4, 2, k["red"] if tela != "zz" else k["mdd"]); b.p(12, 0 - up, k["redl"] if tela != "zz" else k["md"])
    if coracao:                                                 # holograma de coração subindo
        hy = -2 - up - coracao * 2
        for x, yy in ((10, 0), (11, -1), (12, 0), (13, 1), (14, 0), (15, -1), (16, 0), (11, 1), (12, 2), (13, 3),
                      (14, 2), (15, 1)):
            b.p(x + 1, hy + yy, (120, 255, 240))
    if pousado:
        b.r(9, 17, 2, 4, k["md"]); b.r(17, 17, 2, 4, k["md"])
        b.r(8, 20, 4, 1, k["mdd"]); b.r(16, 20, 4, 1, k["mdd"])
    else:
        for i, x in enumerate((10, 13, 16)):
            b.p(x, 16 - up, k["cy"] if (i + jato) % 3 else k["cw"])
            b.p(x, 17 - up + (i + jato) % 2, k["cyd"])
    return b


def drone():
    k = [DR["cy"], DR["cw"], DR["red"], DR["redl"], (120, 255, 240)]
    A = {}
    A["parado"] = [hd(drone_q(up=u, helice=i, tela="pisca" if i == 3 else "feliz", jato=i).s, keep=k)
                   for i, u in enumerate((2, 3, 4, 3))]
    A["andando"] = [hd(drone_q(up=3, helice=i, jato=i).s, keep=k) for i in range(4)]
    A["especial"] = [hd(drone_q(up=3, helice=i, tela=t, coracao=c, jato=i).s, keep=k)
                     for i, (t, c) in enumerate((("feliz", 0), ("pisca", 0), ("coracao", 0), ("coracao", 1),
                                                 ("coracao", 2), ("risada", 3)))]
    A["feliz"] = [hd(drone_q(up=u, helice=i, tela="risada", jato=i).s, keep=k) for i, u in enumerate((3, 6, 8, 6))]
    A["susto"] = [hd(drone_q(up=6, helice=0, tela="alerta").s, keep=k), hd(drone_q(up=4, helice=2, tela="alerta").s, keep=k)]
    A["dormindo"] = [hd(drone_q(up=0, helice=1, tela="zz", pousado=True).s, keep=k) for _ in (0, 1)]
    return A


# ═════════════════ tudo junto ═════════════════
ANIMS = ("parado", "andando", "especial", "feliz", "susto", "dormindo")
PETS = {"gato": gato, "cachorro": cachorro, "papagaio": papagaio, "capivara": capivara, "mico": mico,
        "tuiuiu": tuiuiu, "jabuti": jabuti, "drone": drone, "caquinho": caquinho}


def sheet(frames):
    """Os quadros lado a lado, cada um num quadrado do mesmo tamanho, com os pés alinhados embaixo."""
    w = max(f.get_width() for f in frames)
    h = max(f.get_height() for f in frames)
    s = pygame.Surface((w * len(frames), h), pygame.SRCALPHA)
    for i, f in enumerate(frames):
        s.blit(f, f.get_rect(midbottom=(i * w + w // 2, h)))
    return s


def main():
    for slug, fn in PETS.items():
        anims = fn()
        for name in ANIMS:
            pygame.image.save(sheet(anims[name]), str(OUT / f"pet_{slug}_{name}.png"))
        print("pet", slug, {n: len(anims[n]) for n in ANIMS})


if __name__ == "__main__":
    main()
