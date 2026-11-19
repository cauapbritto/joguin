"""Recorta a folha de sprites da LUTA (fundo verde) em um PNG transparente por pose.

    python tools/recortar_luta.py            # lê assets/luta/folha_turma.png e grava assets/luta/<lutador>/<pose>.png

Cada pedaço da folha é achado pelos pixels que não são verde; os quadros abaixo dizem qual
pedaço (pela posição na folha) vira qual pose. O verde que sobra na borda é tirado (despill).
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import numpy as np
import pygame

ROOT = Path(__file__).resolve().parent.parent
SHEET = ROOT / "assets" / "luta" / "folha_turma.png"
OUT = ROOT / "assets" / "luta"

# (lutador, pose): ponto dentro do pedaço na folha (x, y)
PIECES = {
    ("aryel", "chute"): (100, 130),
    ("aryel", "forte"): (270, 120),
    ("aryel", "pulo"): (430, 100),
    ("aryel", "soco"): (590, 120),
    ("aryel", "especial"): (750, 120),
    ("aryel", "vitoria"): (925, 120),
    ("aryel", "guarda"): (95, 300),
    ("aryel", "defesa"): (290, 300),
    ("aryel", "corrida"): (525, 310),
    ("aryel", "caido"): (735, 335),
    ("aryel", "tonto"): (925, 310),
    ("cauanzera", "chute"): (100, 520),
    ("cauanzera", "forte"): (245, 490),
    ("cauanzera", "pulo"): (405, 490),
    ("cauanzera", "soco_baixo"): (575, 495),
    ("cauanzera", "especial"): (735, 500),
    ("cauanzera", "soco"): (915, 500),
    ("cauanzera", "defesa"): (90, 680),
    ("cauanzera", "guarda"): (240, 680),
    ("cauanzera", "caido"): (650, 705),
    ("cauanzera", "tonto"): (900, 705),
}


def is_green(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return (g > 120) & (g - r > 50) & (g - b > 50)


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    sheet = pygame.image.load(str(SHEET)).convert_alpha()
    rgb = pygame.surfarray.array3d(sheet).astype(np.int32)
    fg = ~is_green(rgb)
    mask = pygame.mask.from_surface(sheet)
    mask.clear()
    for x, y in zip(*np.nonzero(fg)):
        mask.set_at((int(x), int(y)), 1)
    for (who, pose), at in PIECES.items():
        # o pedaço é o maior componente perto do ponto (o ponto pode cair num buraco do desenho)
        best = None
        for dx in range(-12, 13, 3):
            for dy in range(-12, 13, 3):
                p = (at[0] + dx, at[1] + dy)
                if mask.get_at(p):
                    best = mask.connected_component(p)
                    break
            if best:
                break
        if best is None:
            sys.exit(f"não achei o pedaço de {who}/{pose} em {at}")
        rect = best.get_bounding_rects()[0]
        part = np.zeros((rect.w, rect.h, 4), np.uint8)
        sub = rgb[rect.x:rect.right, rect.y:rect.bottom].copy()
        keep = np.array([[best.get_at((rect.x + i, rect.y + j)) for j in range(rect.h)] for i in range(rect.w)], bool)
        # despill: o verde da borda vira a média do vermelho e do azul
        g = sub[..., 1]
        lim = np.maximum(sub[..., 0], sub[..., 2])
        sub[..., 1] = np.where(g > lim + 10, lim + 10, g)
        part[..., :3] = sub.clip(0, 255)
        part[..., 3] = np.where(keep, 255, 0)
        surf = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.surfarray.pixels3d(surf)[:] = part[..., :3]
        pygame.surfarray.pixels_alpha(surf)[:] = part[..., 3]
        (OUT / who).mkdir(parents=True, exist_ok=True)
        pygame.image.save(surf, str(OUT / who / f"{pose}.png"))
        print(who, pose, rect.size)


if __name__ == "__main__":
    main()
