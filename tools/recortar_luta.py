"""Recorta as folhas de sprites da LUTA (fundo verde, uma por lutador) em um PNG transparente por quadro.

    python tools/recortar_luta.py      # lê assets/luta/<lutador>_folha.png e grava assets/luta/<lutador>/rLcC.png

Os desenhos são achados pelos pixels que não são verde. As linhas da folha saem da linha dos pés
(desenhos com o pé quase na mesma altura são da mesma linha) e as colunas, da esquerda para a
direita: o quadro da 3ª linha, 5ª coluna vira r2c4.png. Pedacinhos soltos (um punho, uma ponta de
cabelo) vão para o desenho mais perto. Nenhum lutador tem verde, então o verde que sobra (na borda) é tirado de tudo (despill).
"""
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import numpy as np
import pygame

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "assets" / "luta"
FIGHTERS = ("aryel", "cauanzera")
BIG = 400            # pixels: daqui para cima é um desenho; abaixo, pedacinho solto
ROW_GAP = 20         # pés até 20 px de diferença ficam na mesma linha


def foreground(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return ~((g > 110) & (g - r > 45) & (g - b > 45))


def _gap(a, b):
    return max(a.x - b.right, b.x - a.right, 0) + max(a.y - b.bottom, b.y - a.bottom, 0)


def cut(sheet_path, out_dir):
    sheet = pygame.image.load(str(sheet_path)).convert_alpha()
    rgb = pygame.surfarray.array3d(sheet).astype(np.int32)
    mask = pygame.mask.Mask(sheet.get_size())
    for x, y in zip(*np.nonzero(foreground(rgb))):
        mask.set_at((int(x), int(y)), 1)
    comps = [c for c in mask.connected_components() if c.count() >= 12]
    big = [c for c in comps if c.count() > BIG]
    rows = []
    for v in sorted(c.get_bounding_rects()[0].bottom for c in big):
        if rows and v - rows[-1][-1] <= ROW_GAP:
            rows[-1].append(v)
        else:
            rows.append([v])
    feet = [r[len(r) // 2] for r in rows if len(r) >= 5]
    by_row = {}
    for c in big:
        bottom = c.get_bounding_rects()[0].bottom
        by_row.setdefault(min(range(len(feet)), key=lambda i: abs(feet[i] - bottom)), []).append(c)
    figs = []
    for ri in sorted(by_row):
        for ci, c in enumerate(sorted(by_row[ri], key=lambda c: c.get_bounding_rects()[0].centerx)):
            figs.append([f"r{ri}c{ci}", c, c.get_bounding_rects()[0]])
    for c in comps:
        if c.count() > BIG:
            continue
        rect = c.get_bounding_rects()[0]
        best = min(figs, key=lambda f: _gap(f[2], rect))
        if _gap(best[2], rect) <= 6:
            merged = pygame.mask.Mask(sheet.get_size())
            merged.draw(best[1], (0, 0))
            merged.draw(c, (0, 0))
            best[1], best[2] = merged, best[2].union(rect)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, m, rect in figs:
        sub = rgb[rect.x:rect.right, rect.y:rect.bottom].copy()
        alpha = pygame.surfarray.array_alpha(m.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0)))
        sub[..., 1] = np.minimum(sub[..., 1], np.maximum(sub[..., 0], sub[..., 2]))   # despill: nada fica verde
        img = pygame.Surface(rect.size, pygame.SRCALPHA).convert_alpha()
        pygame.surfarray.blit_array(img, sub.clip(0, 255).astype(np.uint8))
        a = pygame.surfarray.pixels_alpha(img)
        a[:] = alpha[rect.x:rect.right, rect.y:rect.bottom]
        del a
        pygame.image.save(img, str(out_dir / f"{name}.png"))
    return len(figs), len(feet)


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    for key in FIGHTERS:
        n, rows = cut(DIR / f"{key}_folha.png", DIR / key)
        print(f"{key}: {n} quadros em {rows} linhas")


if __name__ == "__main__":
    main()
