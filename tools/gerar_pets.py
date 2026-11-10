"""Os pets da loja de CACOS, no mesmo jeito do gato, do cachorro e do papagaio de tools/gerar_pecas.py
(Scale2x + volume), só que 30% menores. Gera assets/pecas/mascote_<pet>_sentado.png e _andando.png.

Uso (na raiz do repositório):  python tools/gerar_pets.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402
import gerar_pecas as P  # noqa: E402
import gerar_sprites as gs  # noqa: E402

OUT = ROOT / "assets" / "pecas"
B, sh = P.B, P.sh
SCALE = 0.7          # 30% menores que a primeira versão (pedido do Cauã em 2026-11-08)


def hd(base, keep=()):
    """O mesmo caminho do jogo (Scale2x + volume), reduzido para SCALE e só então o contorno fino."""
    from pixel_hd import fine_outline, scale2x, volume
    img = volume(scale2x(base), gs.shade, keep)
    w, h = img.get_size()
    small = pygame.Surface((round(w * SCALE), round(h * SCALE)), pygame.SRCALPHA)
    for y in range(small.get_height()):
        for x in range(small.get_width()):
            small.set_at((x, y), img.get_at((min(w - 1, int((x + 0.5) / SCALE)), min(h - 1, int((y + 0.5) / SCALE)))))
    return fine_outline(small)
EYE, GL = (30, 26, 30), (250, 250, 250)


class OB(B):
    """B com a origem descida (para desenhar acima do topo, como a laranja da capivara)."""

    def __init__(self, w, h, dy=4):
        super().__init__(w, h + dy)
        self.dy = dy

    def r(self, x, y, w, h, c):
        super().r(x, y + self.dy, w, h, c)

    def p(self, x, y, c):
        super().p(x, y + self.dy, c)


def ell(b, rect, c):
    x, y, w, h = rect
    pygame.draw.ellipse(b.s, c, (x, y + getattr(b, "dy", 0), w, h))


def eye(b, x, y, w=2, h=2, iris=EYE):
    b.r(x, y, w, h, iris)
    b.p(x, y, GL)


def capivara(pose="sentado"):
    c, cd, cdd, cl, cll = (150, 104, 66), (116, 78, 48), (86, 56, 34), (182, 134, 88), (206, 164, 112)
    nose, lar, folha = (64, 42, 30), (250, 150, 50), (70, 170, 70)
    if pose == "sentado":
        b = OB(30, 24)
        ell(b, (4, 9, 22, 15), c)                         # corpão redondo
        ell(b, (6, 10, 16, 6), cl)
        b.r(5, 18, 20, 4, cd)
        for x, y in ((8, 13), (12, 15), (18, 13), (21, 16), (10, 19), (16, 18)):   # pelo
            b.p(x, y, cd)
        b.r(6, 21, 6, 3, cd)                              # patinhas
        b.r(18, 21, 6, 3, cd)
        for x in (7, 9, 19, 21):
            b.p(x, 23, cdd)
        b.r(8, 3, 14, 11, c)                              # cabeção quadrado
        b.r(9, 2, 12, 1, c)
        b.r(9, 3, 11, 2, cl)
        b.r(8, 12, 14, 2, cd)
        b.r(9, 1, 3, 3, cd); b.p(10, 2, (190, 120, 110))  # orelhinhas
        b.r(18, 1, 3, 3, cd); b.p(19, 2, (190, 120, 110))
        b.r(10, 6, 3, 1, cdd); b.r(17, 6, 3, 1, cdd)      # pálpebras de sono
        b.r(10, 7, 3, 1, EYE); b.r(17, 7, 3, 1, EYE)
        b.p(11, 7, (90, 70, 60)); b.p(18, 7, (90, 70, 60))
        b.r(11, 9, 8, 5, cll)                             # focinhão
        b.r(11, 13, 8, 1, cl)
        b.r(12, 10, 2, 1, nose); b.r(16, 10, 2, 1, nose)
        b.r(14, 12, 2, 1, cdd)
        b.p(10, 11, (220, 150, 140)); b.p(20, 11, (220, 150, 140))   # bochecha
        ell(b, (12, -1, 6, 5), lar)                       # laranja na cabeça
        b.p(13, 0, (255, 210, 120))
        b.r(15, -1, 2, 1, (120, 80, 40))
        b.r(16, -2, 3, 1, folha); b.p(18, -3, folha)
    else:
        b = OB(32, 22)
        ell(b, (2, 6, 22, 12), c)
        ell(b, (4, 7, 16, 4), cl)
        for x, y in ((6, 11), (10, 13), (15, 11), (19, 13), (8, 15)):
            b.p(x, y, cd)
        b.r(4, 15, 3, 6, cd); b.r(4, 20, 4, 1, cdd)
        b.r(9, 15, 3, 6, c); b.r(9, 20, 4, 1, cdd)
        b.r(15, 15, 3, 6, cd); b.r(15, 20, 4, 1, cdd)
        b.r(19, 15, 3, 5, c); b.r(19, 19, 4, 1, cdd)
        b.r(19, 3, 11, 10, c)
        b.r(20, 3, 9, 2, cl)
        b.r(19, 11, 11, 2, cd)
        b.r(20, 1, 3, 3, cd); b.p(21, 2, (190, 120, 110))
        b.r(23, 6, 3, 1, cdd); b.r(23, 7, 3, 1, EYE)
        b.r(27, 7, 5, 6, cll)
        b.r(30, 8, 2, 1, nose)
        b.r(28, 11, 3, 1, cdd)
        ell(b, (22, -1, 6, 5), lar)
        b.p(23, 0, (255, 210, 120))
        b.r(25, -1, 2, 1, (120, 80, 40)); b.r(26, -2, 3, 1, folha)
        b.r(0, 8, 3, 3, cd)
    return hd(b.s, keep=[EYE, GL])


def mico(pose="sentado"):
    o, od, odd, ol, oll = (238, 150, 40), (204, 112, 26), (160, 80, 20), (255, 196, 80), (255, 226, 140)
    face, faced = (124, 74, 54), (86, 50, 36)
    if pose == "sentado":
        b = B(24, 26)
        ell(b, (2, 0, 20, 17), o)                         # juba
        ell(b, (3, 1, 16, 8), ol)
        for x, y in ((3, 7), (2, 10), (20, 7), (21, 10), (5, 3), (17, 3), (11, 0)):
            b.r(x, y, 2, 2, od)
        for x, y in ((6, 2), (14, 2), (10, 1)):
            b.p(x, y, oll)
        ell(b, (7, 4, 10, 10), face)                      # rostinho
        b.r(8, 12, 8, 2, faced)
        eye(b, 9, 7); eye(b, 13, 7)
        b.p(8, 6, faced); b.p(15, 6, faced)
        b.r(11, 10, 2, 1, (60, 34, 26))
        b.r(10, 12, 4, 1, (90, 50, 40))
        ell(b, (6, 14, 12, 10), o)                        # corpinho
        ell(b, (8, 15, 6, 5), ol)
        b.r(7, 17, 2, 4, od); b.r(15, 17, 2, 4, od)       # bracinhos
        b.r(7, 21, 2, 1, face); b.r(15, 21, 2, 1, face)
        b.r(7, 23, 4, 2, od); b.r(13, 23, 4, 2, od)
        b.r(7, 24, 4, 1, face); b.r(13, 24, 4, 1, face)
        b.r(17, 21, 3, 2, o)                              # rabo enrolando
        b.r(19, 16, 2, 6, o); b.r(19, 16, 2, 6, od)
        b.r(20, 12, 2, 5, o); b.r(18, 11, 3, 2, ol)
    else:
        b = B(28, 22)
        ell(b, (4, 9, 14, 7), o)
        ell(b, (6, 9, 10, 3), ol)
        for x, y, c2 in ((5, 14, od), (9, 14, o), (12, 14, od), (15, 14, o)):
            b.r(x, y, 2, 6, c2); b.r(x, y + 5, 3, 1, face)
        ell(b, (14, 1, 13, 13), o)
        ell(b, (15, 2, 9, 5), ol)
        for x, y in ((14, 6), (15, 10), (24, 3), (19, 1)):
            b.r(x, y, 2, 2, od)
        ell(b, (19, 4, 8, 8), face)
        eye(b, 22, 6)
        b.r(25, 9, 2, 1, (60, 34, 26))
        b.r(23, 11, 3, 1, faced)
        b.r(0, 6, 5, 2, o); b.r(0, 2, 2, 5, o); b.r(1, 1, 3, 2, ol)
    return hd(b.s, keep=[EYE, GL])


def tuiuiu(pose="sentado"):
    w, wd, wl, bk, bkl, r, rd = (240, 240, 236), (198, 200, 208), (255, 255, 252), (30, 28, 34), (70, 66, 80), (214, 48, 48), (160, 30, 34)
    bico, bicod = (70, 64, 70), (44, 40, 46)
    if pose == "sentado":
        b = B(22, 30)
        ell(b, (4, 13, 14, 12), w)                        # penugem fofa
        ell(b, (5, 14, 8, 5), wl)
        for x, y in ((6, 20), (9, 22), (13, 21), (15, 18)):
            b.p(x, y, wd)
        b.r(3, 15, 3, 7, wd)                              # asinha
        b.r(3, 16, 1, 5, (170, 170, 180))
        b.r(8, 5, 6, 9, bk)                               # pescoço preto
        b.r(9, 6, 1, 6, bkl)
        b.r(8, 10, 6, 3, r); b.r(8, 12, 6, 1, rd)          # papo vermelho
        b.p(9, 10, (240, 110, 100))
        ell(b, (7, 0, 8, 7), bk)                          # cabeça
        b.p(9, 1, bkl)
        eye(b, 11, 2, 1, 1, (240, 200, 60))
        b.r(14, 3, 7, 2, bico); b.r(14, 4, 6, 1, bicod)    # bico grande
        b.p(20, 4, bicod)
        b.r(8, 0, 2, 1, (120, 120, 130))                  # topetinho de filhote
        b.r(7, 25, 1, 5, bk); b.r(13, 25, 1, 5, bk)
        b.r(6, 29, 3, 1, bk); b.r(12, 29, 3, 1, bk)
    else:
        b = B(26, 28)
        ell(b, (3, 11, 13, 10), w)
        ell(b, (4, 12, 7, 4), wl)
        pygame.draw.polygon(b.s, wd, [(5, 12), (0, 4), (3, 3), (12, 11)])     # asa abrindo
        pygame.draw.polygon(b.s, wl, [(6, 12), (2, 5), (11, 11)])
        b.r(0, 3, 3, 1, bk)
        b.r(11, 4, 5, 9, bk)
        b.r(12, 5, 1, 6, bkl)
        b.r(11, 9, 5, 3, r); b.r(11, 11, 5, 1, rd)
        ell(b, (11, 0, 8, 6), bk)
        eye(b, 15, 2, 1, 1, (240, 200, 60))
        b.r(18, 3, 8, 2, bico); b.r(18, 4, 7, 1, bicod)
        b.r(6, 21, 1, 6, bk); b.r(11, 21, 1, 7, bk)
        b.r(5, 26, 3, 1, bk); b.r(10, 27, 3, 1, bk)
    return hd(b.s, keep=[GL, (240, 200, 60)])


def jabuti(pose="sentado"):
    s, sd, sdd, sl, k, kd, kl, y = (126, 98, 50), (88, 66, 32), (60, 44, 22), (174, 142, 78), (156, 136, 86), (118, 100, 60), (190, 172, 118), (236, 186, 60)
    b = B(28, 18)
    head_x = 21 if pose != "sentado" else 20
    b.r(head_x, 6, 7, 6, k)                           # cabeça
    b.r(head_x + 1, 6, 5, 1, kl)
    b.r(head_x, 11, 7, 1, kd)
    eye(b, head_x + 3, 7)
    b.p(head_x + 6, 9, kd)
    b.r(head_x + 4, 10, 3, 1, kd)
    for x, yy in ((head_x + 1, 9), (head_x + 2, 7)):
        b.p(x, yy, y)                                 # pintinhas amarelas na cabeça
    step = 1 if pose != "sentado" else 0
    for lx, ly, cc in ((4 - step, 12, kd), (8 + step, 13, k), (16 - step, 13, k), (19 + step, 12, kd)):
        b.r(lx, ly, 4, 4, cc)
        b.r(lx, ly + 3, 4, 1, kd)
        b.p(lx + 1, ly + 3, kl)
    ell(b, (2, 1, 22, 14), s)                         # casco alto
    ell(b, (4, 2, 16, 5), sl)
    b.r(3, 12, 20, 2, sdd)
    b.r(2, 11, 22, 1, sd)
    for cx, cy in ((8, 4), (13, 3), (18, 4), (6, 8), (12, 8), (17, 8)):   # placas hexagonais
        b.r(cx - 1, cy, 4, 3, sd)
        b.r(cx, cy + 1, 2, 1, y)
        b.p(cx - 1, cy, sdd)
    b.r(0, 9, 3, 2, kd)                               # rabinho
    return hd(b.s, keep=[EYE, GL])


def drone(pose="sentado"):
    m, md, mdd, ml, cy, cyd = (156, 166, 184), (100, 108, 128), (66, 72, 90), (214, 222, 236), (90, 236, 230), (40, 150, 150)
    lag = (240, 90, 60)
    up = 0 if pose == "sentado" else 2
    b = B(28, 22)
    ell(b, (7, 6 - up, 14, 11), m)                     # corpo arredondado
    ell(b, (8, 6 - up, 10, 4), ml)
    b.r(7, 14 - up, 14, 2, md)
    b.r(9, 8 - up, 10, 6, (20, 22, 30))               # telinha
    b.r(9, 8 - up, 10, 1, (50, 56, 70))
    b.r(11, 10 - up, 2, 2, cy); b.r(16, 10 - up, 2, 2, cy)   # olhinhos felizes
    b.p(11, 10 - up, (220, 255, 250)); b.p(16, 10 - up, (220, 255, 250))
    b.r(13, 12 - up, 3, 1, cyd)
    b.r(12, 15 - up, 4, 1, lag)                       # faixa laranja Lag Lobby
    b.p(12, 15 - up, (255, 170, 130))
    for x, dx in ((0, 1), (20, -1)):                   # braços e hélices
        b.r(x + 4 if dx > 0 else x, 8 - up, 4, 2, md)
        b.r(x + 2, 6 - up, 2, 3, mdd)
        b.r(x, 4 - up, 8, 1, (70, 70, 84))
        b.p(x + (0 if pose == "sentado" else 7), 4 - up, (200, 200, 220))
        b.r(x + 2, 5 - up, 4, 1, mdd)
    b.r(13, 1 - up, 2, 5, md)                          # antena
    b.r(12, 0 - up, 4, 2, (250, 70, 70)); b.p(12, 0 - up, (255, 190, 190))
    if pose == "sentado":
        b.r(9, 17, 2, 4, md); b.r(17, 17, 2, 4, md)     # perninhas pousado
        b.r(8, 20, 4, 1, mdd); b.r(16, 20, 4, 1, mdd)
    else:
        for i, x in enumerate((10, 13, 16)):            # jatinho
            b.p(x, 16, cy if i != 1 else (220, 255, 250))
            b.p(x, 17 + i % 2, cyd)
    return hd(b.s, keep=[cy, (220, 255, 250), (250, 70, 70), (255, 190, 190)])


def caquinho(pose="sentado"):
    cr, cd, cdd, cl, cw = (90, 170, 240), (44, 92, 186), (30, 56, 130), (170, 224, 255), (240, 252, 255)
    up = 0 if pose == "sentado" else 3
    b = B(22, 28)
    top, mid, bot = 1 - up + 3, 11 - up + 3, 23 - up
    pygame.draw.polygon(b.s, cr, [(11, top), (18, mid), (11, bot), (4, mid)])
    pygame.draw.polygon(b.s, cl, [(11, top), (11, bot), (5, mid)])           # face da luz
    pygame.draw.polygon(b.s, cd, [(11, top + 2), (17, mid), (11, bot)])      # face da sombra
    pygame.draw.polygon(b.s, cw, [(10, top + 2), (7, mid - 1), (8, mid - 3)])   # reflexo
    b.r(11, top, 1, bot - top, cdd)                   # aresta do meio
    eye(b, 8, mid, 2, 3); eye(b, 13, mid, 2, 3)        # olhões
    b.r(10, mid + 4, 3, 1, cdd)                       # sorrisinho
    b.p(9, mid + 3, cdd); b.p(13, mid + 3, cdd)
    b.p(6, mid + 3, (250, 170, 200)); b.p(16, mid + 3, (250, 170, 200))   # bochecha
    for x, y2 in ((2, top + 2), (19, top + 5), (1, mid + 6)):   # cacos menores em volta
        b.r(x, y2, 2, 3, cl); b.p(x, y2, cw)
    if pose == "sentado":
        b.r(8, bot, 2, 3, cd); b.r(13, bot, 2, 3, cd)    # perninhas
        b.r(7, bot + 3, 3, 1, cdd); b.r(13, bot + 3, 3, 1, cdd)
    return hd(b.s, keep=[EYE, cw, GL])


PETS = [
    ("capivara", capivara, "CAPIVARA", "Anda devagarinho, dorme quando você para e tem uma laranja na cabeça."),
    ("mico", mico, "MICO-LEÃO-DOURADO", "Pula de um ombro para o outro e rouba moedinha do chão."),
    ("tuiuiu", tuiuiu, "TUIUIÚ FILHOTE", "O primo do bem do Tuiuiú-Drone do cap. 4, só que de verdade."),
    ("jabuti", jabuti, "JABUTI", "O mais lento da turma; quando você corre, ele se esconde no casco."),
    ("drone", drone, "MINI-DRONE LAG LOBBY", "Robozinho da Lag Lobby que voa do seu lado, de tela feliz."),
    ("caquinho", caquinho, "CAQUINHO", "Um caco do cristal que ganhou vida: o mascote dos CACOS."),
]


def main():
    pygame.init()
    for slug, fn, _name, _desc in PETS:
        pygame.image.save(fn("sentado"), str(OUT / f"mascote_{slug}_sentado.png"))
        pygame.image.save(fn("andando"), str(OUT / f"mascote_{slug}_andando.png"))
    print("pets em", OUT)


if __name__ == "__main__":
    main()
