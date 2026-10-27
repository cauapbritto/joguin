"""Gera os sprites pixel-art das armas.

Uso:  python tools/gerar_armas.py

Cada arma é desenhada apontando para a direita, em tamanho 1x (o jogo amplia 2x,
igual aos personagens). O ponto onde a mão segura vai em assets/weapons/grips.json.
"""
import json
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "assets" / "weapons"
OUTLINE = (24, 17, 28, 255)

WOOD, WOOD_D = (152, 106, 64), (100, 66, 40)
LEATHER, LEATHER_D = (126, 76, 52), (84, 48, 32)
STEEL, STEEL_M, STEEL_D = (222, 226, 236), (160, 166, 182), (98, 102, 120)
GOLD, GOLD_D = (234, 186, 74), (166, 120, 40)
RED, DARK = (206, 62, 56), (54, 54, 68)
GREEN, GREEN_D = (100, 126, 76), (64, 86, 48)
PURPLE, PURPLE_L, PURPLE_D = (152, 98, 216), (220, 192, 255), (92, 56, 140)
STRING = (232, 222, 192)
ICE, ICE_L, ICE_D = (150, 212, 240), (230, 248, 255), (84, 140, 196)


class Sprite:
    def __init__(self, w, h):
        self.surf = pygame.Surface((w, h), pygame.SRCALPHA)

    def rect(self, x, y, w, h, color):
        self.surf.fill(color, (x, y, w, h))

    def px(self, x, y, color):
        self.surf.set_at((x, y), color)

    def paint(self, rows, palette, x=0, y=0):
        """Desenho em texto: cada letra é uma cor da paleta ("." fica vazio)."""
        for j, row in enumerate(rows):
            for i, c in enumerate(row):
                if c in palette:
                    self.surf.set_at((x + i, y + j), palette[c])

    def finish(self):
        """Adiciona o contorno escuro de 1 px (fica com 1 px de margem em volta)."""
        w, h = self.surf.get_size()
        out = pygame.Surface((w + 2, h + 2), pygame.SRCALPHA)
        line = pygame.mask.from_surface(self.surf).to_surface(setcolor=OUTLINE, unsetcolor=(0, 0, 0, 0))
        for dx, dy in ((0, 1), (2, 1), (1, 0), (1, 2)):
            out.blit(line, (dx, dy))
        out.blit(self.surf, (1, 1))
        return out


def espada():
    s = Sprite(20, 6)
    s.rect(0, 2, 1, 2, GOLD)
    s.rect(1, 2, 4, 2, LEATHER)
    s.rect(1, 3, 4, 1, LEATHER_D)
    s.rect(5, 0, 2, 6, GOLD)
    s.px(5, 0, (255, 220, 130))
    s.rect(7, 2, 11, 2, STEEL_M)
    s.rect(7, 2, 11, 1, STEEL)
    s.px(18, 2, STEEL)
    return s.finish(), (2, 3)


def faca():
    s = Sprite(12, 4)
    s.rect(0, 1, 4, 2, DARK)
    s.rect(4, 0, 1, 4, STEEL_D)
    s.rect(5, 1, 6, 2, STEEL_M)
    s.rect(5, 1, 6, 1, STEEL)
    s.px(11, 1, STEEL)
    return s.finish(), (2, 2)


def katana():
    s = Sprite(23, 4)
    s.rect(0, 1, 6, 2, DARK)
    for x in (1, 3, 5):
        s.px(x, 1, RED)
    s.rect(6, 0, 1, 4, GOLD)
    s.rect(7, 1, 12, 2, STEEL_M)
    s.rect(7, 1, 12, 1, STEEL)
    s.rect(19, 0, 2, 2, STEEL_M)
    s.rect(19, 0, 2, 1, STEEL)
    s.px(21, 0, STEEL)
    return s.finish(), (3, 2)


def espadao():
    s = Sprite(27, 8)
    s.rect(0, 2, 1, 4, GOLD)
    s.rect(1, 3, 4, 2, LEATHER)
    s.rect(5, 0, 2, 8, GOLD)
    s.rect(5, 7, 2, 1, GOLD_D)
    s.rect(7, 2, 16, 4, STEEL_M)
    s.rect(7, 2, 16, 1, STEEL)
    s.rect(8, 4, 13, 1, STEEL_D)
    s.rect(23, 3, 2, 2, STEEL_M)
    s.px(23, 3, STEEL)
    s.px(25, 3, STEEL_M)
    return s.finish(), (3, 4)


def maca():
    s = Sprite(17, 9)
    s.rect(0, 3, 10, 2, WOOD)
    s.rect(0, 4, 10, 1, WOOD_D)
    s.rect(10, 1, 6, 7, STEEL_D)
    s.rect(11, 2, 4, 5, STEEL_M)
    s.rect(11, 2, 3, 1, STEEL)
    for x, y in ((12, 0), (13, 0), (12, 8), (13, 8), (16, 4), (16, 3)):
        s.px(x, y, STEEL)
    return s.finish(), (3, 4)


def martelo():
    s = Sprite(17, 11)
    s.rect(0, 4, 11, 2, WOOD)
    s.rect(0, 5, 11, 1, WOOD_D)
    s.rect(10, 3, 1, 5, DARK)
    s.rect(11, 0, 5, 11, STEEL_D)
    s.rect(12, 1, 3, 9, STEEL_M)
    s.rect(12, 1, 3, 1, STEEL)
    return s.finish(), (3, 5)


def foice():
    s = Sprite(21, 12)
    s.rect(0, 9, 18, 2, WOOD)
    s.rect(0, 10, 18, 1, WOOD_D)
    for y, x0, x1 in ((0, 11, 17), (1, 9, 19), (2, 13, 19), (3, 16, 19), (4, 17, 19),
                      (5, 18, 19), (6, 18, 19), (7, 18, 19), (8, 18, 19)):
        s.rect(x0, y, x1 - x0 + 1, 1, STEEL_M)
    for y, x in ((1, 9), (2, 13), (3, 16), (4, 17)):
        s.px(x, y, STEEL)
    s.rect(9, 0, 2, 1, STEEL)
    return s.finish(), (4, 10)


def lanca():
    s = Sprite(28, 6)
    s.rect(0, 2, 21, 2, WOOD)
    s.rect(0, 3, 21, 1, WOOD_D)
    s.rect(20, 1, 2, 4, LEATHER)
    for y, x1 in ((1, 24), (2, 26), (3, 26), (4, 24)):
        s.rect(22, y, x1 - 22 + 1, 1, STEEL_M)
    s.rect(22, 1, 3, 1, STEEL)
    s.rect(22, 2, 5, 1, STEEL)
    s.px(27, 2, STEEL)
    s.px(27, 3, STEEL_M)
    return s.finish(), (7, 3)


BOW_PULL = {0: 4, 1: 4, 2: 2, 3: 0}     # onde fica o meio da corda (x) em cada estágio


def _arco(stage):
    """Arco em 4 estágios: 0 vazio (sem flecha), 1 flecha encaixada, 2 meio puxado, 3 tenso.
    Todos no mesmo tamanho e com a pegada no mesmo ponto (a animação não "pula" na mão)."""
    s = Sprite(17, 21)
    ox = 2
    bend = {0: 0, 1: 0, 2: 1, 3: 1}[stage]       # puxado, as pontas do arco vêm um pouco para trás
    curve = [5, 6, 7, 7, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 7, 7, 6, 5, 4]
    for y, x in enumerate(curve):
        tip = y < 3 or y > 17
        x = ox + x - (bend if tip else 0)
        s.rect(x, y, 2, 1, WOOD)
        s.px(x + 1, y, WOOD_D)
    s.rect(ox + 8, 8, 2, 5, LEATHER)
    nock = BOW_PULL[stage]
    top, bottom = (ox + 2, 1), (ox + 2, 19)
    if nock == top[0]:
        s.rect(top[0], 1, 1, 19, STRING)
    else:
        pygame.draw.line(s.surf, STRING, top, (nock, 10))
        pygame.draw.line(s.surf, STRING, (nock, 10), bottom)
    if stage > 0:
        # flecha encaixada na corda
        s.rect(nock, 10, 11, 1, WOOD_D)
        head = nock + 11
        s.px(head, 9, STEEL)
        s.px(head + 1, 10, STEEL)
        s.px(head, 11, STEEL)
        s.px(head, 10, STEEL_M)
        s.rect(nock, 9, 2, 1, RED)
        s.rect(nock, 11, 2, 1, RED)
    return s.finish(), (ox + 9, 11)


def arco():
    return _arco(1)


def arco_vazio():
    return _arco(0)


def arco_puxado():
    return _arco(2)


def arco_tenso():
    return _arco(3)


def flecha():
    """Flecha em voo (só o projétil, não é arma de mão)."""
    s = Sprite(15, 3)
    s.rect(2, 1, 10, 1, WOOD_D)
    s.rect(3, 1, 8, 1, WOOD)
    s.px(12, 0, STEEL_M)
    s.px(12, 2, STEEL_M)
    s.rect(12, 1, 2, 1, STEEL)
    s.px(14, 1, STEEL)
    s.rect(0, 0, 3, 1, RED)
    s.rect(0, 2, 3, 1, RED)
    s.px(1, 1, (240, 110, 100))
    return s.finish(), (7, 1)


def rifle():
    s = Sprite(21, 7)
    s.rect(0, 3, 5, 3, WOOD)
    s.rect(0, 5, 5, 1, WOOD_D)
    s.rect(5, 2, 9, 3, DARK)
    s.rect(5, 2, 9, 1, STEEL_D)
    s.rect(8, 5, 1, 2, DARK)
    s.rect(14, 2, 7, 2, STEEL_D)
    s.rect(14, 2, 7, 1, STEEL_M)
    s.px(12, 1, STEEL_M)
    return s.finish(), (7, 4)


def corrente():
    s = Sprite(23, 7)
    s.rect(0, 2, 4, 3, DARK)
    s.rect(0, 2, 4, 1, STEEL_D)
    for k in range(5):
        x = 4 + k * 3
        s.rect(x, 3 if k % 2 else 2, 2, 2 if k % 2 else 3, STEEL_M)
        s.px(x, 2 if k % 2 == 0 else 3, STEEL)
    s.rect(18, 1, 5, 5, DARK)
    s.rect(19, 2, 3, 3, STEEL_D)
    s.px(19, 2, STEEL_M)
    for x, y in ((20, 0), (20, 6), (22, 3)):
        s.px(x, y, STEEL)
    return s.finish(), (2, 3)


def shuriken():
    s = Sprite(9, 9)
    s.rect(3, 3, 3, 3, STEEL_D)
    s.rect(4, 0, 1, 3, STEEL_M)
    s.rect(4, 6, 1, 3, STEEL_M)
    s.rect(0, 4, 3, 1, STEEL_M)
    s.rect(6, 4, 3, 1, STEEL_M)
    for x, y in ((4, 0), (0, 4), (3, 3)):
        s.px(x, y, STEEL)
    s.px(4, 4, DARK)
    return s.finish(), (1, 5)


def estrela():
    s = Sprite(9, 9)
    s.rect(4, 0, 1, 9, GOLD_D)
    s.rect(0, 4, 9, 1, GOLD_D)
    for d in range(1, 4):
        for x, y in ((4 - d, 4 - d), (4 + d, 4 + d), (4 - d, 4 + d), (4 + d, 4 - d)):
            if d < 3:
                s.px(x, y, GOLD)
    s.rect(3, 3, 3, 3, GOLD)
    s.px(3, 3, (255, 236, 160))
    return s.finish(), (1, 5)


def granada():
    s = Sprite(9, 10)
    s.rect(1, 3, 6, 7, GREEN)
    s.rect(1, 9, 6, 1, GREEN_D)
    s.rect(1, 6, 6, 1, GREEN_D)
    s.rect(4, 3, 1, 7, GREEN_D)
    s.px(2, 4, (150, 176, 112))
    s.rect(2, 1, 3, 2, STEEL_M)
    s.rect(5, 0, 2, 2, STEEL_D)
    s.px(7, 1, STEEL)
    s.px(8, 2, STEEL)
    s.px(7, 3, STEEL)
    return s.finish(), (1, 6)


def orbe():
    s = Sprite(9, 9)
    rows = [(3, 5), (1, 7), (1, 7), (0, 8), (0, 8), (0, 8), (1, 7), (1, 7), (3, 5)]
    for y, (x0, x1) in enumerate(rows):
        s.rect(x0, y, x1 - x0 + 1, 1, PURPLE)
    s.rect(1, 6, 7, 2, PURPLE_D)
    s.rect(3, 8, 3, 1, PURPLE_D)
    s.rect(2, 2, 2, 2, PURPLE_L)
    s.px(4, 1, PURPLE_L)
    return s.finish(), (0, 5)


def garras():
    s = Sprite(13, 9)
    s.rect(0, 2, 3, 5, LEATHER)
    s.rect(0, 6, 3, 1, LEATHER_D)
    for y, length in ((1, 8), (4, 10), (7, 8)):
        s.rect(3, y, length, 1, STEEL)
        s.rect(3, y + 1 if y < 7 else y - 1, length - 2, 1, STEEL_D)
    return s.finish(), (1, 5)


def pistola():
    """Pistola de pederneira do Pirata."""
    s = Sprite(15, 8)
    s.rect(0, 4, 3, 4, WOOD)                 # cabo curvo
    s.rect(0, 7, 3, 1, WOOD_D)
    s.rect(1, 3, 3, 2, WOOD)
    s.px(0, 4, GOLD)                         # ponteira do cabo
    s.rect(4, 2, 10, 2, STEEL_D)             # cano
    s.rect(4, 2, 10, 1, STEEL_M)
    s.rect(13, 1, 2, 4, STEEL_D)             # boca do cano
    s.px(14, 1, STEEL)
    s.rect(3, 1, 2, 3, GOLD)                 # cão e fecho de latão
    s.px(3, 0, GOLD_D)
    s.rect(4, 4, 3, 1, GOLD_D)               # guarda-mato
    s.px(5, 5, DARK)                         # gatilho
    return s.finish(), (1, 5)


def sabre():
    """Sabre curvo do Pirata, com guarda de concha."""
    s = Sprite(20, 9)
    s.rect(0, 5, 4, 2, LEATHER)
    s.rect(0, 6, 4, 1, LEATHER_D)
    s.px(0, 5, GOLD)
    s.rect(4, 3, 2, 5, GOLD)                 # concha
    s.rect(1, 8, 5, 1, GOLD_D)               # arco que protege os dedos
    s.px(1, 7, GOLD_D)
    for y, x0, x1 in ((5, 6, 11), (4, 8, 14), (3, 12, 16), (2, 15, 18), (1, 17, 19)):
        s.rect(x0, y, x1 - x0 + 1, 1, STEEL_M)
    for y, x0, x1 in ((4, 6, 10), (3, 11, 14), (2, 14, 16), (1, 17, 18), (0, 18, 19)):
        s.rect(x0, y, x1 - x0 + 1, 1, STEEL)  # fio com brilho
    return s.finish(), (2, 6)


def cristal():
    """Lasca de gelo que a Geada arremessa."""
    s = Sprite(12, 7)
    rows = [(4, 7), (2, 9), (1, 11), (2, 9), (4, 7)]
    for i, (x0, x1) in enumerate(rows):
        s.rect(x0, i + 1, x1 - x0 + 1, 1, ICE)
    s.rect(3, 2, 5, 1, ICE_L)                # face de cima brilhando
    s.rect(4, 4, 5, 1, ICE_D)
    s.rect(2, 5, 3, 1, ICE_D)
    s.px(11, 3, ICE_L)
    s.rect(0, 3, 2, 1, ICE_D)                # cabo de gelo
    return s.finish(), (0, 3)


def cajado():
    """Cajado de madeira clara com um cristal de gelo na ponta."""
    s = Sprite(27, 11)
    s.rect(0, 5, 20, 2, (196, 170, 132))
    s.rect(0, 6, 20, 1, (140, 116, 86))
    s.rect(16, 4, 2, 4, ICE_D)               # amarração
    s.px(16, 4, ICE)
    rows = [(22, 23), (21, 24), (20, 25), (19, 26), (20, 25), (21, 24), (22, 23)]
    for i, (x0, x1) in enumerate(rows):
        s.rect(x0, i + 2, x1 - x0 + 1, 1, ICE)
    s.rect(21, 3, 3, 2, ICE_L)
    s.rect(22, 6, 3, 2, ICE_D)
    s.px(23, 0, ICE_L)                       # faíscas de gelo
    s.px(26, 1, ICE)
    s.px(19, 9, ICE)
    return s.finish(), (7, 6)


# ── armas raras (baú da campanha) ─────────────
FIRE, FIRE_L = (234, 104, 44), (252, 200, 72)
BOLT, BOLT_L = (246, 214, 70), (255, 250, 210)


def besta():
    """Besta: coronha de madeira, arco de metal na frente e o virote armado."""
    s = Sprite(20, 13)
    s.rect(0, 5, 14, 3, WOOD)
    s.rect(0, 7, 14, 1, WOOD_D)
    s.rect(3, 8, 2, 3, WOOD_D)                   # cabo
    s.px(6, 8, DARK)                             # gatilho
    for y, x in ((0, 13), (1, 14), (2, 14), (3, 15), (4, 15), (5, 15), (6, 15), (7, 15), (8, 15), (9, 15),
                 (10, 14), (11, 14), (12, 13)):
        s.px(x, y, STEEL_D)
        if 2 <= y <= 10:
            s.px(x - 1, y, STEEL_M)
    pygame.draw.line(s.surf, STRING, (12, 0), (9, 6))
    pygame.draw.line(s.surf, STRING, (9, 6), (12, 12))
    s.rect(9, 4, 9, 1, WOOD_D)                   # virote
    s.px(18, 3, STEEL)
    s.px(19, 4, STEEL)
    s.px(18, 5, STEEL)
    s.px(18, 4, STEEL_M)
    return s.finish(), (4, 8)


def lanca_chamas():
    """Lança-chamas: tanque vermelho atrás, cano comprido e a chama piloto acesa."""
    s = Sprite(23, 9)
    s.rect(0, 3, 6, 6, RED)                      # tanque
    s.rect(0, 3, 6, 1, (232, 110, 100))
    s.rect(0, 8, 6, 1, (140, 40, 36))
    s.rect(2, 1, 2, 2, STEEL_D)                  # válvula
    s.rect(6, 4, 12, 3, DARK)                    # cano
    s.rect(6, 4, 12, 1, STEEL_D)
    s.rect(9, 7, 2, 2, DARK)                     # gatilho
    s.rect(18, 3, 3, 5, STEEL_M)                 # bico
    s.rect(18, 3, 3, 1, STEEL)
    s.px(21, 5, FIRE)                            # chama piloto
    s.px(22, 5, FIRE_L)
    s.px(21, 4, FIRE_L)
    return s.finish(), (8, 6)


def bumerangue():
    """Bumerangue de madeira com listras pintadas."""
    s = Sprite(13, 12)
    pygame.draw.line(s.surf, WOOD, (0, 1), (6, 9), 3)
    pygame.draw.line(s.surf, WOOD, (6, 9), (12, 1), 3)
    pygame.draw.line(s.surf, WOOD_D, (1, 3), (6, 10))
    pygame.draw.line(s.surf, WOOD_D, (6, 10), (11, 3))
    for x, y in ((2, 3), (10, 3)):
        s.px(x, y, RED)
        s.px(x + (1 if x < 6 else -1), y + 1, RED)
    s.px(6, 8, GOLD)
    return s.finish(), (1, 2)


def cajado_raio():
    """Cajado do Raio: haste escura com aro de ouro segurando uma pedra de raio que solta faíscas."""
    s = Sprite(27, 13)
    s.paint([
        "........................y..",
        "...................gg..yw..",
        "..................gG.yy.y..",
        "..................g.ywwy...",
        "..................gywwwwy.w",
        "PPPPPPPPPPPPPPPPGggywwwwyyy",
        "vvvvvvvvvvvvvvvvGGgyywwyy..",
        "..................g.yyyy...",
        "..................gG..y.y..",
        "...................gg..yw..",
        "........................y..",
        "...........................",
        "...........................",
    ], FORGE)
    return s.finish(), (7, 5)


def canhao():
    """Canhão de mão: cano grosso com cintas de latão e o pavio aceso."""
    s = Sprite(20, 10)
    s.rect(0, 5, 6, 4, WOOD)
    s.rect(0, 8, 6, 1, WOOD_D)
    s.rect(5, 2, 13, 6, STEEL_D)
    s.rect(5, 2, 13, 2, STEEL_M)
    s.rect(6, 6, 12, 1, DARK)
    s.rect(8, 1, 2, 8, GOLD)                     # cintas
    s.rect(14, 1, 2, 8, GOLD)
    s.rect(18, 0, 2, 10, DARK)                   # boca
    s.rect(18, 0, 2, 2, STEEL_M)
    s.px(5, 0, FIRE)                             # pavio
    s.px(4, 1, (120, 100, 80))
    return s.finish(), (2, 7)


def virote():
    """Virote da besta em voo."""
    s = Sprite(13, 3)
    s.rect(2, 1, 8, 1, WOOD_D)
    s.rect(10, 0, 1, 3, STEEL_M)
    s.rect(10, 1, 2, 1, STEEL)
    s.px(12, 1, STEEL)
    s.rect(0, 0, 2, 1, STEEL_M)
    s.rect(0, 2, 2, 1, STEEL_M)
    return s.finish(), (6, 1)


# ── armas raras de cada fase da campanha ─────
HIVE, HIVE_D, HONEY = (214, 160, 70), (150, 100, 40), (250, 210, 70)
THORN_W, THORN_W_D, LEAF = (110, 74, 44), (74, 48, 28), (90, 160, 70)
SOUL, SOUL_D = (120, 240, 170), (50, 130, 90)
BONE_C, BONE_D = (232, 228, 210), (170, 164, 146)
SPECTRAL, SPECTRAL_L = (150, 120, 230), (210, 196, 255)
SNOW, SNOW_D = (232, 242, 252), (170, 200, 228)


def colmeia():
    """Colmeia de abelhas, com listras e a entradinha escura."""
    s = Sprite(10, 11)
    for i, (x, w) in enumerate(((3, 4), (1, 8), (0, 10), (0, 10), (1, 8), (2, 6))):
        s.rect(x, 1 + i * 2, w, 2, HIVE if i % 2 == 0 else HIVE_D)
    s.rect(4, 0, 2, 1, HIVE_D)                   # galhinho
    s.rect(4, 7, 2, 2, (40, 28, 20))             # entrada
    s.px(2, 3, HONEY)
    s.px(8, 5, HONEY)
    return s.finish(), (4, 0)


def arco_espinhos():
    """Arco de galho retorcido com folhas e espinhos."""
    s = Sprite(10, 22)
    for y in range(22):
        bend = round(4 * (1 - ((y - 10.5) / 10.5) ** 2))
        s.px(1 + bend, y, THORN_W)
        s.px(2 + bend, y, THORN_W_D)
        if y % 5 == 2:
            s.px(3 + bend, y, (220, 214, 190))   # espinho
    s.rect(0, 0, 1, 22, (200, 200, 190))         # corda
    s.rect(5, 3, 2, 2, LEAF)
    s.rect(5, 16, 2, 2, LEAF)
    return s.finish(), (4, 11)


def espinho():
    """Espinho em voo (projétil)."""
    s = Sprite(10, 3)
    s.rect(0, 1, 7, 1, THORN_W)
    s.rect(7, 0, 2, 3, (220, 214, 190))
    s.px(9, 1, (240, 236, 220))
    s.px(1, 0, LEAF)
    return s.finish(), (4, 1)


def machado():
    """Machado do Lenhador: cabo de madeira com cinta de couro e lâmina larga em meia-lua."""
    s = Sprite(23, 15)
    s.paint([
        "................dds....",
        "...............dmmss...",
        "..............dmmmssw..",
        ".............dmmmmmssw.",
        "............ddmmmmmmsw.",
        ".............dmmmmmmsw.",
        "xxxxxhhxxxxxxdkdmmmmsw.",
        "XXXXXHHXXXXXXdkdmmmmsw.",
        ".............dmmmmmmsw.",
        "............ddmmmmmmsw.",
        ".............dmmmmmssw.",
        "..............dmmmssw..",
        "...............dmmss...",
        "................dds....",
        ".......................",
    ], FORGE)
    return s.finish(), (3, 6)


def lanterna():
    """Lanterna das Almas: lampião de ferro com uma chama verde de alma."""
    s = Sprite(11, 15)
    s.rect(4, 0, 3, 1, STEEL_D)                  # alça
    s.rect(3, 1, 1, 2, STEEL_D)
    s.rect(7, 1, 1, 2, STEEL_D)
    s.rect(1, 3, 9, 2, (60, 62, 74))
    s.rect(2, 5, 7, 7, SOUL_D)
    s.rect(3, 6, 5, 5, SOUL)
    s.rect(4, 7, 3, 3, (220, 255, 230))
    s.rect(2, 5, 1, 7, (60, 62, 74))             # grades
    s.rect(8, 5, 1, 7, (60, 62, 74))
    s.rect(1, 12, 9, 2, (60, 62, 74))
    return s.finish(), (5, 0)


def cranio():
    """Crânio Uivante na mão (os olhos brilham verde)."""
    s = Sprite(10, 10)
    s.rect(1, 0, 8, 7, BONE_C)
    s.rect(0, 2, 10, 4, BONE_C)
    s.rect(2, 7, 6, 2, BONE_C)
    s.rect(1, 6, 8, 1, BONE_D)
    s.rect(2, 3, 2, 2, (20, 14, 22))
    s.rect(6, 3, 2, 2, (20, 14, 22))
    s.px(2, 3, SOUL)
    s.px(6, 3, SOUL)
    s.px(4, 5, (40, 30, 30))
    for x in (3, 5, 7):
        s.px(x, 8, (40, 30, 30))
    return s.finish(), (5, 9)


def foice_espectral():
    """Foice Espectral: cabo escuro e uma lâmina roxa em meia-lua, translúcida e com fio brilhante."""
    s = Sprite(21, 14)
    s.paint([
        "..........lllllll....",
        ".......lllppppppplll.",
        ".....llppppPPPPPPppl.",
        "....lpppPPP.......Pl.",
        "...lppPP.........vPl.",
        "..lpPP...........vk..",
        "..lP.............vk..",
        "..l..............vk..",
        "..................k..",
        "..................k..",
        "kkkkkkkkkkkkkkkkkkk..",
        "KKKKKKKKKKKKKKKKKKK..",
        ".....................",
        ".....................",
    ], FORGE)
    return s.finish(), (3, 10)


def estalactites():
    """Estalactites: cetro de prata com coroa de ouro e três pontas de gelo penduradas."""
    s = Sprite(25, 15)
    s.paint([
        "...............g..g..g...",
        "..............gYggYggYg..",
        "..............GgIIIIIIIi.",
        "gsmmmmmmmmmmmmGIiiiiiiiij",
        "GddddddddddddddGjiiijiiij",
        "...............gJIiJIiJIj",
        "................JIiJIiJIj",
        ".................IiJ.iJIj",
        ".................IiJ.iJ.j",
        ".................Ij..iJ..",
        "..................j..iJ..",
        "..................j..I...",
        ".....................I...",
        "..........................",
        "..........................",
    ], FORGE)
    return s.finish(), (4, 3)


def espelho():
    """Espelho de Cristal: moldura de ouro trabalhada, cristal azul com reflexo e um rubi no cabo."""
    s = Sprite(18, 15)
    s.paint([
        "........gYYg......",
        "......gYggggYg....",
        ".....gGIIiiiiGg...",
        "....gGIIiiiiijGg..",
        "....gIIwiiiiijjg..",
        "...gGIwIiiiijjjGg.",
        "gGhhgIIiiiiiijjjg.",
        "GGHHgIiiiiiijjjJgr",
        "...gGiiiiiijjjJJGg",
        "....giiiiijjjJJJg.",
        "....gGijjjjjJJJGg.",
        ".....gGjjjJJJJGg..",
        "......gYggggYg....",
        "........gGGg......",
        "..................",
    ], FORGE)
    return s.finish(), (2, 6)


def bola_neve():
    """Bola de Neve: neve batida com sombra azulada, brilho de gelo e uns cristais em volta."""
    s = Sprite(12, 12)
    s.paint([
        "....IIII....",
        "..IIwwIIIc..",
        ".IwwIIIIIIc.",
        ".IwIIIIIIcc.",
        "IIIIIIIIIccj",
        "IIIIIIIIcccj",
        "IIIIIIIccccj",
        "cIIIIIcccccj",
        ".ccIccccccj.",
        ".cccccccjjj.",
        "..jjcccjjj..",
        "....jjjj....",
    ], {**FORGE, "c": (196, 220, 240)})
    return s.finish(), (2, 6)


def raio_supremo():
    """Cajado do Raio Supremo: haste dourada com cabeça em tridente e três pedras de raio acesas."""
    s = Sprite(30, 15)
    s.paint([
        "..........................w...",
        ".....................gg..yw...",
        "....................gYwy.yy...",
        "...................gG.yywy....",
        "...................g...yy...w.",
        "..................gG......wy..",
        "gYgggYgggYgggYggggGgGyywyyyyyw",
        "GGGGGGGGGGGGGGGGGGGgGyyyyyyyy.",
        "..................gG......wy..",
        "...................g...yy...w.",
        "...................gG.yywy....",
        "....................gYwy.yy...",
        ".....................gg..yw...",
        "..........................w...",
        "..............................",
    ], FORGE)
    return s.finish(), (7, 6)


# ── armas do Cauanzera, do Albeguinio e do Borba Jr ──
NAVY, NAVY_D = (52, 74, 140), (32, 46, 92)
PAGE = (240, 232, 210)
LAPTOP, LAPTOP_D, LAPTOP_L = (150, 154, 166), (96, 100, 112), (200, 204, 214)
SCREEN_G = (90, 230, 120)
PLASTIC, PLASTIC_D = (60, 62, 74), (36, 36, 46)
CABLE, CABLE_D = (64, 150, 220), (34, 92, 150)
EXO, EXO_L, EXO_D = (150, 160, 178), (206, 214, 228), (92, 100, 120)
PULSE, PULSE_L = (80, 170, 255), (210, 244, 255)


def capacete():
    """Capacete de moto do Aryel, segurado pela jugular (bate com o casco)."""
    s = Sprite(13, 12)
    shell, shell_d, shell_l = (204, 52, 48), (130, 30, 30), (244, 130, 120)
    s.rect(0, 5, 3, 1, (40, 40, 48))             # jugular na mão
    s.rect(2, 2, 10, 9, shell)
    s.rect(3, 1, 8, 1, shell)
    s.rect(4, 0, 6, 1, shell)
    s.rect(3, 1, 4, 1, shell_l)                  # brilho
    s.rect(2, 10, 10, 1, shell_d)
    s.rect(7, 4, 5, 4, (40, 46, 70))             # viseira
    s.rect(8, 4, 3, 1, (110, 130, 190))
    s.rect(4, 3, 1, 6, (240, 238, 230))          # faixa
    return s.finish(), (1, 5)


def disquete():
    """Disquete de 3,5": corpo azul, janelinha de metal e etiqueta (gira quando é jogado)."""
    s = Sprite(9, 9)
    s.rect(0, 0, 9, 9, NAVY)
    s.rect(0, 8, 9, 1, NAVY_D)
    s.rect(8, 0, 1, 9, NAVY_D)
    s.rect(2, 0, 5, 3, STEEL_M)                  # tampa de metal
    s.rect(5, 1, 1, 2, NAVY_D)
    s.px(2, 0, STEEL)
    s.rect(1, 5, 7, 3, PAGE)                     # etiqueta
    s.rect(2, 6, 4, 1, (120, 120, 140))
    s.px(0, 8, NAVY_D)
    return s.finish(), (1, 5)


def cabo_de_rede():
    """Cabo de rede azul enrolado na mão, com o conector RJ45 transparente na ponta (chicote)."""
    s = Sprite(30, 7)
    s.rect(0, 2, 4, 3, CABLE_D)                  # voltas na mão
    s.rect(1, 1, 2, 5, CABLE)
    for x in range(4, 26):                       # o cabo ondulando
        y = 3 + (1 if (x // 3) % 2 else -1 if (x // 3) % 4 == 2 else 0)
        s.rect(x, y, 1, 2, CABLE)
        s.px(x, y + 1, CABLE_D)
    s.rect(26, 2, 4, 3, (210, 226, 236))         # conector
    s.rect(26, 2, 4, 1, (244, 250, 255))
    s.rect(27, 4, 3, 1, GOLD)                    # pinos
    s.px(25, 3, CABLE_D)
    return s.finish(), (2, 3)


def pendrive():
    """Pendrive preto com a ponta USB de metal e uma luzinha verde."""
    s = Sprite(11, 5)
    s.rect(0, 0, 7, 5, PLASTIC)
    s.rect(0, 0, 7, 1, (92, 94, 110))
    s.rect(0, 4, 7, 1, PLASTIC_D)
    s.px(1, 2, SCREEN_G)                         # luzinha
    s.rect(7, 1, 4, 3, STEEL_M)                  # ponta USB
    s.rect(7, 1, 4, 1, STEEL)
    s.px(8, 2, STEEL_D)
    s.px(10, 2, STEEL_D)
    return s.finish(), (2, 2)


def notebook():
    """Notebook fechado, segurado pela beirada (bate com a tampa)."""
    s = Sprite(16, 12)
    s.rect(0, 0, 16, 12, LAPTOP)
    s.rect(0, 0, 16, 1, LAPTOP_L)
    s.rect(0, 11, 16, 1, LAPTOP_D)
    s.rect(15, 0, 1, 12, LAPTOP_D)
    s.rect(0, 9, 16, 1, LAPTOP_D)                # junção da tampa
    s.rect(6, 4, 4, 3, (220, 224, 232))          # logo
    s.px(7, 5, LAPTOP_D)
    return s.finish(), (1, 6)


def canhao_de_pulso():
    """Canhão de Pulso: canhão de metal preso no antebraço, com a boca azul acesa."""
    s = Sprite(18, 9)
    s.rect(0, 1, 6, 7, EXO_D)                    # braçadeira
    s.rect(1, 2, 4, 5, EXO)
    s.rect(5, 0, 9, 9, EXO)
    s.rect(5, 0, 9, 2, EXO_L)
    s.rect(5, 7, 9, 2, EXO_D)
    for x in (7, 10):                            # aletas
        s.rect(x, 2, 1, 5, EXO_D)
    s.rect(14, 1, 4, 7, (40, 46, 70))            # boca
    s.rect(15, 2, 3, 5, PULSE)
    s.rect(16, 3, 2, 3, PULSE_L)
    return s.finish(), (2, 4)


def punho_mecanico():
    """Punho Mecânico: luva robótica grande, com dedos de placas e a junta azul."""
    s = Sprite(13, 11)
    s.rect(0, 3, 4, 5, EXO_D)                    # punho
    s.rect(3, 1, 8, 9, EXO)
    s.rect(3, 1, 8, 1, EXO_L)
    s.rect(3, 9, 8, 1, EXO_D)
    for y in (2, 4, 6, 8):                       # dedos
        s.rect(10, y, 3, 1, EXO_L)
        s.rect(10, y + 1, 3, 1, EXO_D) if y < 8 else None
    s.rect(5, 4, 2, 2, PULSE)                    # junta acesa
    s.px(5, 4, PULSE_L)
    return s.finish(), (2, 5)


# ── armas forjadas (fusão do ferreiro) ───────
# paleta das forjadas: cada letra é uma cor (as maiúsculas são as versões escuras)
FORGE = {
    "k": (40, 34, 52), "K": (24, 20, 32),
    "h": LEATHER, "H": LEATHER_D, "x": WOOD, "X": WOOD_D,
    "g": GOLD, "G": GOLD_D, "Y": (255, 232, 150),
    "w": (255, 252, 236), "y": (255, 214, 80), "o": (255, 146, 44), "r": (222, 72, 36), "R": (140, 36, 24),
    "s": STEEL, "m": STEEL_M, "d": STEEL_D,
    "c": (196, 232, 255), "u": (92, 140, 226), "U": (48, 70, 142),
    "l": (226, 204, 255), "p": (160, 104, 230), "P": (94, 54, 150), "v": (34, 16, 54),
    "I": (236, 250, 255), "i": (150, 212, 240), "j": (84, 140, 196), "J": (46, 86, 140),
    "n": BONE_C, "N": BONE_D, "z": (130, 255, 190),
}


def lamina_solar():
    """Lâmina Solar: guarda em forma de sol e a lâmina em brasa, com labaredas no fio."""
    s = Sprite(27, 11)
    s.paint([
        "....g......................",
        ".g..Y..g.......o.....o.....",
        "..gYYYg.......oy....oyo....",
        "..YgwgY.......oy.o..oy..o..",
        "..YgwgY.wwwwwwwwwwwwwwwww..",
        "HhgYwwYgyyyyyyyyyyyyyyyyyyw",
        "HhgYwwYgooooooooooooooooyw.",
        "..YgwgY.rrrrrrrrrrrrrrrrr..",
        "..gYYYg........RRRRRRRR....",
        ".g..Y..g...................",
        "....g......................",
    ], FORGE)
    return s.finish(), (1, 5)


def martelo_trovao():
    """Martelo do Trovão Eterno: cabeça de aço azulado com cintas de ouro e a runa do raio acesa."""
    s = Sprite(26, 14)
    s.paint([
        ".............dsssssssssssd",
        "............dsccccccccccsd",
        "............sgcuuuuuuuucgs",
        "............sguuuuyuuuuugs",
        "............sguuuyyuuuuugs",
        "gKkhhkhhkhhkdguuyyyyyuuugd",
        "GKkHhkHhkHhkdguuuuyyuuuugd",
        "............sguuuuyuuuuugs",
        "............sguuuyuuuuuugs",
        "............sgUuuuuuuuuUgs",
        "............dsUUUUUUUUUUsd",
        ".............dddddddddddd.",
        "...........................",
        "...........................",
    ], FORGE)
    return s.finish(), (2, 5)


def arco_mil_almas():
    """Arco das Mil Almas: arco de osso roxo com chamas de alma nas pontas e a corda de luz."""
    s = Sprite(11, 25)
    s.paint([
        "...l.......",
        "..lpl......",
        "..cPP......",
        "..c.pP.....",
        "..c..pP....",
        "..c..npP...",
        "..c...nP...",
        "..c...np...",
        "..c....nP..",
        "..c....nP..",
        "..c...gg...",
        "..c...hh...",
        "..c...Gg...",
        "..c...hh...",
        "..c...gg...",
        "..c....nP..",
        "..c....nP..",
        "..c...np...",
        "..c...nP...",
        "..c..npP...",
        "..c..pP....",
        "..c.pP.....",
        "..cPP......",
        "..lpl......",
        "...l.......",
    ], FORGE)
    return s.finish(), (6, 12)


def canhao_vazio():
    """Canhão do Vazio: cano roxo com anéis de ouro e um buraco negro girando na boca."""
    s = Sprite(24, 12)
    s.paint([
        "...............gg.......",
        "..........PPPPPggPPPPP..",
        ".........PppppplgpppplP.",
        "....kk..PplllllgllllppPv",
        "hhhhkKkPppppppggpppppPvl",
        "HHhhkKkPpPPPPPggPPPPpPvp",
        "...kkk.PPPPPPPggPPPPPPvl",
        "...K.K..PPPPPPggPPPPPPv.",
        "...K.K...PPPPPGGPPPPP...",
        "..........kkkkkkkkkk....",
        "........................",
        "........................",
    ], FORGE)
    return s.finish(), (2, 4)


def coracao_inverno():
    """Coração do Inverno: cetro de prata com um coração de gelo facetado preso por garras."""
    s = Sprite(25, 13)
    s.paint([
        "...................I.I...",
        "................m.IiiI...",
        "...............m.IiIiiI..",
        "..............m.IIiiiijI.",
        "..............sIIiiiiijjI",
        "gdmmmmmmmmmmmsmIiiiiijjJ.",
        "GdddddddddddddmIiiiijjJ..",
        "..............sIiiijjJ...",
        "..............m.IijjJ....",
        "...............m.ijJ.....",
        "................m.J......",
        ".........................",
        ".........................",
    ], FORGE)
    return s.finish(), (2, 5)


def lanca_dragao():
    """Lança do Dragão: haste vermelha com escamas de ouro e a ponta em forma de cabeça de dragão."""
    s = Sprite(30, 9)
    s.paint([
        "........................ry....",
        "......................rroo....",
        "...................ggrooooRo..",
        "RrrRrrRrrRrrRrrRrrgGrrowooooy.",
        "RRrRRrRRrRRrRRrRRrgGRrooooooo y".replace(" ", ""),
        "...................ggRroooR...",
        "......................RRrr....",
        "........................Ry....",
        "..............................",
    ], FORGE)
    return s.finish(), (4, 3)


def cetro_tempestade():
    """Cetro da Tempestade: haste de ouro e uma nuvem de tempestade presa num aro, com raios."""
    s = Sprite(28, 15)
    s.paint([
        "...................y........",
        "..................y..mmmm...",
        "..................ymmssssm..",
        "................mmmsssssssm.",
        "...............msssddsssddsm",
        "...............gsddddddddddm",
        "gYggggggggggggGg.dddddddddm.",
        "GGGGGGGGGGGGGGGg..y..y..y...",
        "...............g..yy.y..yy..",
        "................g..y..y..y..",
        "...................y..yy..y.",
        ".......................y....",
        "............................",
        "............................",
        "............................",
    ], FORGE)
    return s.finish(), (3, 6)


def foice_ceifador():
    """Foice do Ceifador: cabo de osso com crânio e a lâmina larga de aço escuro com fio pálido."""
    s = Sprite(24, 15)
    s.paint([
        ".............mmmm.......",
        "..........mmmsssssm.....",
        "........mmdddddddssmm...",
        "......mdddkkkkkkkddssm..",
        ".....mddk.........dddsm.",
        "....mdk.............ddm.",
        "...md................dm.",
        "...m..................m.",
        "..................nnnmd.",
        "Gkkkkkkkkkkkkkkkkknzn...",
        "GKKKKKKKKKKKKKKKKKnnn...",
        "...................N....",
        "........................",
        "........................",
        "........................",
    ], FORGE)
    return s.finish(), (2, 9)


WEAPONS = {
    "Espada": espada, "Faca": faca, "Katana": katana, "Espadão": espadao,
    "Maça": maca, "Martelo": martelo, "Foice": foice, "Lança": lanca,
    "Arco": arco, "Rifle": rifle, "Corrente": corrente, "Shuriken": shuriken,
    "Estrela": estrela, "Granada": granada, "Orbe": orbe, "Garras": garras,
    "Pistola": pistola, "Sabre": sabre, "Cristal": cristal, "Cajado": cajado,
    # estágios da animação do arco e o projétil da flecha
    "Arco Vazio": arco_vazio, "Arco Puxado": arco_puxado, "Arco Tenso": arco_tenso, "Flecha": flecha,
    # armas raras do baú da campanha e o virote da besta
    "Besta": besta, "Lança-chamas": lanca_chamas, "Bumerangue": bumerangue, "Cajado do Raio": cajado_raio,
    "Canhão de Mão": canhao, "Virote": virote,
    # Cauanzera, Albeguinio e Borba Jr
    "Colmeia": colmeia, "Arco de Espinhos": arco_espinhos, "Espinho": espinho,
    "Machado do Lenhador": machado, "Lanterna das Almas": lanterna, "Crânio Uivante": cranio,
    "Foice Espectral": foice_espectral, "Estalactites": estalactites, "Espelho de Cristal": espelho,
    "Bola de Neve": bola_neve, "Cajado do Raio Supremo": raio_supremo,
    "Capacete": capacete, "Disquete": disquete, "Cabo de Rede": cabo_de_rede, "Pendrive": pendrive, "Notebook": notebook,
    "Canhão de Pulso": canhao_de_pulso, "Punho Mecânico": punho_mecanico,
    # forjadas do ferreiro
    "Lâmina Solar": lamina_solar, "Martelo do Trovão Eterno": martelo_trovao,
    "Arco das Mil Almas": arco_mil_almas, "Canhão do Vazio": canhao_vazio,
    "Coração do Inverno": coracao_inverno, "Lança do Dragão": lanca_dragao,
    "Cetro da Tempestade": cetro_tempestade, "Foice do Ceifador": foice_ceifador,
}


def file_name(name):
    import unicodedata
    plain = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode()
    return plain.lower().replace(" ", "_") + ".png"


def build_all():
    pygame.init()
    result = {}
    for name, draw in WEAPONS.items():
        surf, (gx, gy) = draw()
        result[name] = (surf, (gx + 1, gy + 1))      # +1 por causa da margem do contorno
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    grips = {}
    for name, (surf, grip) in build_all().items():
        fname = file_name(name)
        pygame.image.save(surf, str(OUT / fname))
        grips[name] = {"file": fname, "grip": list(grip)}
    (OUT / "grips.json").write_text(json.dumps(grips, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(grips)} armas em {OUT}")


if __name__ == "__main__":
    main()
