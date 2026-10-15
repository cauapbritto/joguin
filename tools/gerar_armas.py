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
    """Cajado do Raio: haste escura e uma pedra amarela soltando faíscas."""
    s = Sprite(27, 11)
    s.rect(0, 5, 19, 2, (90, 70, 110))
    s.rect(0, 6, 19, 1, (60, 44, 76))
    s.rect(16, 3, 2, 6, GOLD_D)                  # garras que seguram a pedra
    s.px(18, 2, GOLD)
    s.px(18, 8, GOLD)
    rows = [(21, 22), (20, 23), (19, 24), (20, 23), (21, 22)]
    for i, (x0, x1) in enumerate(rows):
        s.rect(x0, i + 3, x1 - x0 + 1, 1, BOLT)
    s.rect(20, 4, 2, 1, BOLT_L)
    s.px(25, 1, BOLT_L)                          # faíscas
    s.px(26, 0, BOLT)
    s.px(25, 9, BOLT)
    s.px(26, 10, BOLT_L)
    return s.finish(), (7, 6)


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
