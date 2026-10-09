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


def arco():
    s = Sprite(15, 21)
    curve = [5, 6, 7, 7, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 7, 7, 6, 5, 4]
    for y, x in enumerate(curve):
        s.rect(x, y, 2, 1, WOOD)
        s.px(x + 1, y, WOOD_D)
    s.rect(2, 1, 1, 19, STRING)
    s.rect(8, 8, 2, 5, LEATHER)
    # flecha encaixada
    s.rect(2, 10, 11, 1, WOOD_D)
    s.px(13, 9, STEEL)
    s.px(14, 10, STEEL)
    s.px(13, 11, STEEL)
    s.px(13, 10, STEEL_M)
    s.rect(2, 9, 2, 1, RED)
    s.rect(2, 11, 2, 1, RED)
    return s.finish(), (9, 11)


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


WEAPONS = {
    "Espada": espada, "Faca": faca, "Katana": katana, "Espadão": espadao,
    "Maça": maca, "Martelo": martelo, "Foice": foice, "Lança": lanca,
    "Arco": arco, "Rifle": rifle, "Corrente": corrente, "Shuriken": shuriken,
    "Estrela": estrela, "Granada": granada, "Orbe": orbe, "Garras": garras,
}


def file_name(name):
    import unicodedata
    plain = unicodedata.normalize("NFD", name).encode("ascii", "ignore").decode()
    return plain.lower() + ".png"


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
