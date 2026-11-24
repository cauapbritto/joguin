"""Gera as peças das salas que eram trancadas na Casa (sótão, oficina e porão), desenhadas como os
heróis: arte base pequena + Scale2x + volume + contorno fino (o mesmo caminho de gerar_pecas.py).

Uso:  python tools/gerar_salas.py

Sai em assets/pecas/, no tamanho em que aparece na tela (o jogo não amplia):

  sotao_caixa_<n>.png          caixas de papelão (com fita, aba aberta e etiqueta)
  sotao_caixa_nao_mexer.png    a caixa da faixa vermelha (o segredo) e _aberta
  sotao_mesa_album.png         mesinha com toalha de crochê, abajur e o álbum vermelho
  sotao_cadeira_balanco.png, sotao_cabideiro.png, sotao_espelho.png, sotao_mala.png,
  sotao_ventilador.png, sotao_lampada.png, sotao_brinquedos.png, sotao_quadro.png
"""
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pygame  # noqa: E402

from gerar_pecas import OUT, B, hd, sh  # noqa: E402

CARD, CARD_D, CARD_L, TAPE = (184, 140, 90), (150, 110, 68), (210, 170, 116), (210, 196, 150)


# ── sótão ────────────────────────────────────
def caixa(w=22, h=16, label=None, red=False, aberta=False):
    """Caixa de papelão com aba, fita e etiqueta (``label`` = cor do rótulo). ``red``: a faixa
    vermelha da NÃO MEXER; ``aberta``: as abas abertas e o desenho dobrado aparecendo."""
    b = B(w + 2, h + 4)
    b.r(1, 4, w, h, CARD); b.r(1, 4, w, 2, CARD_L); b.r(1, h + 2, w, 2, CARD_D)
    if aberta:
        b.r(2, 4, w - 2, 3, (70, 50, 30))                                    # o fundo escuro da caixa
        b.poly([(1, 4), (-2, 0), (6, 0), (8, 4)], CARD_L)
        b.poly([(w, 4), (w + 2, 0), (w - 6, 0), (w - 8, 4)], CARD_L)
        b.r(6, 2, 10, 4, (246, 242, 230)); b.r(8, 3, 2, 1, (60, 120, 220)); b.r(12, 3, 2, 1, (220, 60, 60))
    else:
        b.poly([(1, 4), (4, 1), (w // 2, 1), (w // 2, 4)], CARD_L)          # aba levantada
        b.r(w // 2 - 1, 4, 3, h, TAPE); b.r(w // 2 - 1, 4, 1, h, sh(TAPE, -20))
    if label:
        b.r(3, 8, 8, 5, label); b.r(4, 9, 6, 1, sh(label, 50)); b.r(4, 11, 4, 1, sh(label, 50))
    if red:
        b.r(2, 8, w - 2, 5, (210, 50, 50))
    return hd(b.s)


def mesa_album():
    """Mesinha com toalha de crochê, o abajur de franja e o álbum vermelho aberto."""
    b = B(48, 40)
    wood, wd = (120, 76, 44), (86, 52, 30)
    b.r(4, 22, 40, 4, wood); b.r(4, 22, 40, 1, sh(wood, -30))
    for x in (6, 40):
        b.r(x, 26, 3, 13, wd); b.r(x - 1, 30, 5, 1, wood)
    b.r(3, 20, 42, 4, (236, 228, 206))
    for x in range(3, 45, 3):
        b.r(x, 24, 2, 2, (236, 228, 206))
    b.r(14, 17, 20, 3, (150, 30, 40)); b.r(15, 16, 8, 2, (246, 240, 224)); b.r(25, 16, 8, 2, (246, 240, 224))
    b.r(16, 16, 4, 1, (90, 120, 160)); b.r(26, 16, 5, 1, (180, 100, 70))
    b.r(38, 6, 2, 14, (160, 140, 100)); b.r(35, 19, 8, 2, (160, 140, 100))
    b.poly([(33, 7), (43, 7), (45, 0), (31, 0)], (230, 170, 90))
    for x in range(32, 45, 2):
        b.p(x, 8, (200, 120, 60))
    return hd(b.s, keep=[(230, 170, 90)])


def cadeira_balanco():
    b = B(26, 34)
    wood, wd = (140, 92, 54), (100, 64, 36)
    for x in (5, 17):
        b.r(x, 2, 2, 22, wood)
    for y in (4, 8, 12, 16):
        b.r(6, y, 12, 1, wd)
    b.r(4, 18, 18, 3, wood); b.r(3, 18, 2, 10, wd); b.r(21, 18, 2, 10, wd)
    b.r(6, 15, 14, 4, (170, 60, 60)); b.r(7, 15, 12, 1, (210, 100, 90))
    pygame.draw.arc(b.s, wd, (-2, 20, 30, 18), math.pi * 1.05, math.pi * 1.95, 2)
    return hd(b.s)


def cabideiro():
    b = B(20, 46)
    wood = (110, 70, 40)
    b.r(9, 4, 2, 38, wood); b.r(4, 42, 12, 2, wood); b.r(6, 44, 2, 2, wood); b.r(12, 44, 2, 2, wood)
    b.r(5, 6, 10, 1, wood)
    b.r(3, 6, 6, 16, (90, 70, 110)); b.r(3, 6, 6, 2, (120, 96, 140)); b.r(5, 12, 1, 6, (70, 54, 88))
    b.r(9, 1, 10, 3, (60, 40, 30)); b.r(11, 0, 6, 2, (60, 40, 30)); b.r(11, 2, 6, 1, (200, 60, 60))
    b.r(12, 7, 3, 14, (200, 170, 60)); b.r(12, 7, 3, 2, (230, 200, 90))
    return hd(b.s)


def espelho():
    """O espelho grande coberto com o lençol (só aparece a borda dourada e o pé)."""
    b = B(26, 44)
    gold = (210, 170, 70)
    b.r(4, 38, 18, 3, (90, 60, 36)); b.r(6, 41, 2, 3, (90, 60, 36)); b.r(18, 41, 2, 3, (90, 60, 36))
    b.r(5, 4, 16, 34, gold)
    b.poly([(3, 6), (13, 1), (23, 6), (24, 34), (19, 38), (12, 35), (6, 38), (2, 34)], (230, 228, 222))
    b.line((9, 8), (7, 32), (200, 198, 194)); b.line((16, 8), (18, 30), (200, 198, 194))
    return hd(b.s, keep=[gold])


def mala():
    b = B(26, 16)
    b.r(1, 4, 24, 11, (120, 70, 50)); b.r(1, 4, 24, 1, (160, 100, 70)); b.r(1, 9, 24, 1, (90, 50, 36))
    b.r(9, 1, 8, 3, (60, 40, 30)); b.r(10, 2, 6, 1, (30, 20, 14))
    for x in (3, 20):
        b.r(x, 7, 3, 4, (210, 170, 70))
    b.r(5, 5, 4, 3, (230, 220, 190)); b.r(17, 11, 5, 3, (90, 160, 210))
    return hd(b.s)


def ventilador():
    b = B(16, 30)
    b.r(7, 12, 2, 14, (150, 150, 160)); b.r(3, 26, 10, 3, (120, 120, 130))
    b.circ((8, 8), 7, (180, 184, 196)); b.circ((8, 8), 6, (60, 70, 90))
    for a in (0, 2.1, 4.2):
        b.line((8, 8), (8 + int(math.cos(a) * 5), 8 + int(math.sin(a) * 5)), (200, 210, 230), 2)
    b.circ((8, 8), 1, (230, 230, 240))
    return hd(b.s)


def lampada():
    b = B(8, 16)
    b.r(3, 0, 2, 8, (40, 40, 40)); b.r(2, 7, 4, 2, (120, 120, 120))
    b.circ((4, 12), 3, (255, 240, 190)); b.p(3, 11, (255, 255, 255))
    return hd(b.s, keep=[(255, 240, 190), (255, 255, 255)])


def brinquedos():
    """Prateleira de parede: bola de basquete, bola de vôlei, o Uno branco de brinquedo e um trofeuzinho."""
    b = B(70, 22)
    wood = (120, 80, 46)
    b.r(0, 16, 70, 3, wood); b.r(0, 16, 70, 1, sh(wood, -30)); b.r(6, 19, 2, 3, sh(wood, 20)); b.r(62, 19, 2, 3, sh(wood, 20))
    b.circ((9, 10), 6, (230, 120, 40)); b.line((3, 10), (15, 10), (90, 40, 20)); b.line((9, 4), (9, 16), (90, 40, 20))
    b.circ((24, 11), 5, (240, 240, 230)); b.line((20, 9), (28, 13), (60, 110, 200)); b.line((21, 14), (26, 7), (240, 200, 60))
    b.r(33, 10, 16, 5, (240, 240, 240)); b.r(36, 7, 9, 3, (240, 240, 240)); b.r(37, 8, 7, 2, (60, 80, 110))
    b.circ((36, 15), 2, (30, 30, 34)); b.circ((46, 15), 2, (30, 30, 34))
    b.r(56, 14, 8, 2, (90, 60, 40)); b.r(59, 10, 2, 4, (220, 180, 70)); b.r(55, 3, 10, 7, (220, 180, 70)); b.r(57, 4, 3, 4, (250, 220, 120))
    return hd(b.s, keep=[(220, 180, 70), (250, 220, 120)])


def quadro():
    """Quadro velho torto: a Casa pintada à mão, moldura dourada."""
    b = B(28, 22)
    b.r(0, 0, 28, 22, (190, 150, 70)); b.r(2, 2, 24, 18, (150, 200, 230))
    b.r(2, 14, 24, 6, (110, 160, 90)); b.r(8, 8, 12, 8, (240, 230, 210)); b.poly([(6, 9), (14, 3), (22, 9)], (180, 80, 60))
    b.r(12, 11, 3, 5, (120, 80, 50))
    return pygame.transform.rotate(hd(b.s, keep=[(190, 150, 70)]), 7)


SOTAO = {
    "sotao_caixa_1": lambda: caixa(26, 18, label=(230, 220, 190)),
    "sotao_caixa_2": lambda: caixa(20, 14),
    "sotao_caixa_3": lambda: caixa(22, 14, label=(150, 200, 230)),
    "sotao_caixa_4": lambda: caixa(28, 20, label=(200, 120, 80)),
    "sotao_caixa_nao_mexer": lambda: caixa(30, 22, red=True),
    "sotao_caixa_nao_mexer_aberta": lambda: caixa(30, 22, red=True, aberta=True),
    "sotao_mesa_album": mesa_album, "sotao_cadeira_balanco": cadeira_balanco, "sotao_cabideiro": cabideiro,
    "sotao_espelho": espelho, "sotao_mala": mala, "sotao_ventilador": ventilador, "sotao_lampada": lampada,
    "sotao_brinquedos": brinquedos, "sotao_quadro": quadro,
}

PIECES = {**SOTAO}


def main():
    pygame.init()
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in PIECES.items():
        pygame.image.save(fn(), str(OUT / f"{name}.png"))
    print(len(PIECES), "peças das salas em", OUT)


if __name__ == "__main__":
    main()
