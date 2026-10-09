"""Armas na mão dos lutadores: sprites pixel art (assets/weapons) e o rastro do golpe."""
import json
import math

import pygame

from . import config

WEAPON_DIR = config.ASSETS_DIR / "weapons"
SCALE = 2                     # mesma ampliação dos personagens

_icons = {}                   # nome → imagem 1x (para a interface)
_variants = {}                # nome → {direção: (imagem, (grip_x, grip_y))}
_base = {}                    # nome → (imagem apontando para a direita, grip)

DIRECTION_VECTORS = {"direita": (1, 0), "esquerda": (-1, 0), "frente": (0, 1), "costas": (0, -1)}


def load():
    """Carrega os sprites das armas e prepara as quatro direções (só giros de 90°, sem borrar)."""
    if _base:
        return
    try:
        grips = json.loads((WEAPON_DIR / "grips.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    for name, info in grips.items():
        try:
            small = pygame.image.load(str(WEAPON_DIR / info["file"])).convert_alpha()
        except (pygame.error, FileNotFoundError):
            continue
        _icons[name] = small
        img = pygame.transform.scale(small, (small.get_width() * SCALE, small.get_height() * SCALE))
        gx, gy = info["grip"][0] * SCALE + SCALE // 2, info["grip"][1] * SCALE + SCALE // 2
        w, h = img.get_size()
        _base[name] = (img, (gx, gy))
        _variants[name] = {
            "direita": (img, (gx, gy)),
            "esquerda": (pygame.transform.flip(img, True, False), (w - 1 - gx, gy)),
            # girar no sentido horário: (x, y) → (h-1-y, x)
            "frente": (pygame.transform.rotate(img, -90), (h - 1 - gy, gx)),
            # anti-horário: (x, y) → (y, w-1-x)
            "costas": (pygame.transform.rotate(img, 90), (gy, w - 1 - gx)),
        }


def icon(name):
    return _icons.get(name)


def hand_point(x, y, direction, bob):
    """Onde fica a mão que segura a arma, para cada direção do personagem."""
    if direction == "direita":
        return x + 12, y + bob
    if direction == "esquerda":
        return x - 12, y + bob
    if direction == "costas":
        return x + 9, y - 4 + bob
    return x + 10, y + 2 + bob


def draw_weapon(surf, name, hand, direction, facing, swing=None, recoil=0):
    """Desenha a arma e devolve a posição da ponta (para o clarão do tiro).

    swing: progresso (0..1) do golpe corpo a corpo — a arma gira num arco em volta da mão.
    """
    if name not in _base:
        return hand
    hx, hy = hand
    if swing is not None:
        img, (gx, gy) = _base[name]
        base = math.degrees(math.atan2(facing[1], facing[0]))
        angle = base - 75 + 150 * swing
        return _blit_rotated(surf, img, (gx, gy), hand, angle)
    img, (gx, gy) = _variants[name][direction]
    vx, vy = DIRECTION_VECTORS[direction]
    hx -= vx * recoil
    hy -= vy * recoil
    surf.blit(img, (round(hx - gx), round(hy - gy)))
    length = _base[name][0].get_width() - _base[name][1][0]
    return hx + vx * length, hy + vy * length


def _blit_rotated(surf, img, grip, pivot, angle_deg):
    """Gira a imagem (que aponta para a direita) em volta do ponto de pegada."""
    w, h = img.get_size()
    rotated = pygame.transform.rotate(img, -angle_deg)
    ox, oy = grip[0] - w / 2, grip[1] - h / 2
    a = math.radians(angle_deg)
    rx = ox * math.cos(a) - oy * math.sin(a)
    ry = ox * math.sin(a) + oy * math.cos(a)
    cx, cy = pivot[0] - rx, pivot[1] - ry
    surf.blit(rotated, rotated.get_rect(center=(round(cx), round(cy))))
    length = w - grip[0]
    return pivot[0] + math.cos(a) * length, pivot[1] + math.sin(a) * length


def weapon_length(name):
    if name not in _base:
        return 30
    img, (gx, _) = _base[name]
    return img.get_width() - gx


def draw_slash(surf, pivot, facing, radius, progress, color):
    """Rastro fino do golpe: segue a ponta da arma e some rápido."""
    if progress >= 1:
        return
    base = math.atan2(facing[1], facing[0])
    start = base - math.radians(75)
    current = start + math.radians(150) * progress
    tail = max(start, current - math.radians(80))
    steps = 9
    pts = []
    for i in range(steps + 1):
        a = tail + (current - tail) * i / steps
        pts.append((a, i / steps))
    size = int(radius * 2 + 12)
    layer = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size / 2
    fade = 1 - progress * 0.6
    for (a0, t0), (a1, t1) in zip(pts, pts[1:]):
        alpha = int(220 * t1 * fade)
        p0 = (c + math.cos(a0) * radius, c + math.sin(a0) * radius)
        p1 = (c + math.cos(a1) * radius, c + math.sin(a1) * radius)
        pygame.draw.line(layer, (255, 255, 255, alpha), p0, p1, 3)
        q0 = (c + math.cos(a0) * (radius - 4), c + math.sin(a0) * (radius - 4))
        q1 = (c + math.cos(a1) * (radius - 4), c + math.sin(a1) * (radius - 4))
        pygame.draw.line(layer, (*color[:3], alpha // 2), q0, q1, 2)
    surf.blit(layer, (round(pivot[0] - c), round(pivot[1] - c)))
