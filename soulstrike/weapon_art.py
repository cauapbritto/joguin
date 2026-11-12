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
_hd = {}                      # nome → imagem em dobro de detalhe (já do tamanho da tela)

DIRECTION_VECTORS = {"direita": (1, 0), "esquerda": (-1, 0), "frente": (0, 1), "costas": (0, -1)}


def load():
    """Carrega os sprites das armas e prepara as quatro direções (só giros de 90°, sem borrar)."""
    if _base:
        return
    try:
        grips = json.loads((WEAPON_DIR / "grips.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    sources = []
    for name, info in grips.items():
        try:
            small = pygame.image.load(str(WEAPON_DIR / info["file"])).convert_alpha()
        except (pygame.error, FileNotFoundError):
            continue
        sources.append((name, small, info["grip"], info.get("detail", 1)))
    for name, small, grip, detail in sources:
        if detail > 1:              # já vem com o dobro de pixels: é a arma do tamanho da tela
            img = small
            _hd[name] = img
            small = pygame.transform.scale(img, (img.get_width() // detail, img.get_height() // detail))
            gx, gy = grip
        else:
            img = pygame.transform.scale(small, (small.get_width() * SCALE, small.get_height() * SCALE))
            gx, gy = grip[0] * SCALE + SCALE // 2, grip[1] * SCALE + SCALE // 2
        _icons[name] = small
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


_files = None                 # nome → arquivo PNG em assets/weapons (o celular pede pela rota /arma/)


def icon_file(name):
    """Arquivo da imagem da arma (sem carregar o pygame), ou None se ela não tem arte."""
    global _files
    if _files is None:
        try:
            grips = json.loads((WEAPON_DIR / "grips.json").read_text(encoding="utf-8"))
            _files = {n: info["file"] for n, info in grips.items()}
        except (OSError, ValueError, KeyError, TypeError):
            _files = {}
    return _files.get(name)


def icon(name):
    """Ícone da arma no tamanho da arte (pequeno, para listas)."""
    return _icons.get(name)


def icon2x(name):
    """Ícone no dobro do tamanho (cartões e vitrines): a arte em dobro de detalhe quando houver."""
    img = _hd.get(name)
    if img is not None:
        return img
    small = _icons.get(name)
    return None if small is None else pygame.transform.scale(small, (small.get_width() * 2, small.get_height() * 2))


_rotated = {}
ANGLE_STEP = 15               # projéteis giram em passos de 15° (fica pixelado igual ao resto)


def rotated(name, angle_deg, scale=SCALE):
    """Sprite da arma (ou projétil) girado para o ângulo dado, ampliado sem borrar. Guardado em cache."""
    small = _icons.get(name)
    if small is None:
        return None
    step = round(angle_deg / ANGLE_STEP) % (360 // ANGLE_STEP)
    key = (name, step, scale)
    img = _rotated.get(key)
    if img is None:
        hd = _hd.get(name)
        if hd is not None and scale % 2 == 0:                       # gira a arte em dobro de detalhe
            img = pygame.transform.rotate(hd, -step * ANGLE_STEP)
            k = scale // 2
        else:
            img = pygame.transform.rotate(small, -step * ANGLE_STEP)  # gira o 1x (vizinho mais próximo)
            k = scale
        if k != 1:
            img = pygame.transform.scale(img, (img.get_width() * k, img.get_height() * k))
        _rotated[key] = img
    return img


# ── visual que muda ao evoluir e encantar no ferreiro ─────────────────
# encanto: a parte de metal ganha as cores do elemento, do escuro ao claro (rampa de 3 cores)
ENCHANT_TINT = {"fogo": ((130, 28, 12), (238, 86, 22), (255, 214, 110)),
                "gelo": ((34, 72, 140), (104, 186, 248), (232, 248, 255)),
                "raio": ((128, 92, 12), (240, 196, 40), (255, 252, 196))}
LEVEL_RIM = {2: (150, 104, 36), 3: (232, 178, 60)}        # contorno de ouro no +2 e no +3
_styled = {}


def styled(name, level=0, enchant=None):
    """Nome do desenho da arma com o visual do ferreiro: +1 o metal brilha mais, +2 ganha contorno
    de ouro, +3 contorno de ouro claro e uma aura; o encanto pinta a lâmina/o cano (fogo, gelo,
    raio). A variante é feita uma vez, a partir da arte normal, e fica com nome próprio para todo
    o resto (girar, desenhar na mão, ícone) funcionar igual."""
    level = max(0, min(3, int(level or 0)))
    if (not level and not enchant) or name not in _base:
        return name
    key = f"{name}|{level}|{enchant or ''}"
    if key in _styled:
        return key
    img, grip = _base[name]
    out = _restyle(img, level, ENCHANT_TINT.get(enchant))
    detail = name in _hd
    if detail:
        _hd[key] = out
        small = pygame.transform.scale(out, (out.get_width() // 2, out.get_height() // 2))
    else:
        small = _restyle(_icons[name], level, ENCHANT_TINT.get(enchant))
    _icons[key] = small
    gx, gy = grip
    w, h = out.get_size()
    _base[key] = (out, grip)
    _variants[key] = {
        "direita": (out, (gx, gy)),
        "esquerda": (pygame.transform.flip(out, True, False), (w - 1 - gx, gy)),
        "frente": (pygame.transform.rotate(out, -90), (h - 1 - gy, gx)),
        "costas": (pygame.transform.rotate(out, 90), (gy, w - 1 - gx)),
    }
    _styled[key] = (name, level, enchant)
    return key


def _restyle(img, level, tint):
    out = img.copy()
    w, h = out.get_size()
    src = pygame.PixelArray(img)
    dst = pygame.PixelArray(out)

    def rgba(x, y):
        return img.unmap_rgb(src[x, y])

    def solid(x, y):
        return 0 <= x < w and 0 <= y < h and rgba(x, y).a > 0

    for y in range(h):
        for x in range(w):
            c = rgba(x, y)
            if c.a == 0:
                continue
            r, g, b = c.r, c.g, c.b
            lum = (r * 3 + g * 6 + b) / 10
            edge = not all(solid(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if edge and lum < 60:                              # o contorno escuro
                if level in LEVEL_RIM:
                    dst[x, y] = (*LEVEL_RIM[level], c.a)
                continue
            metal = max(r, g, b) - min(r, g, b) < 46 and lum > 70
            if tint is not None and metal:
                t = min(1.0, max(0.0, (lum - 70) / 170))
                lo, hi, k = (tint[0], tint[1], t * 2) if t < 0.5 else (tint[1], tint[2], t * 2 - 1)
                tr, tg, tb = (a + (b2 - a) * k for a, b2 in zip(lo, hi))
                r, g, b = (round(a * 0.15 + c * 0.85) for a, c in ((r, tr), (g, tg), (b, tb)))
            if level and metal:
                boost = 1.06 + 0.05 * level
                r, g, b = (min(255, round(v * boost)) for v in (r, g, b))
            dst[x, y] = (r, g, b, c.a)
    del src, dst
    if level >= 3:                                             # aura: um pixel de luz em volta
        glow = tint[1] if tint else (255, 220, 120)
        halo = pygame.Surface((w, h), pygame.SRCALPHA)
        for y in range(h):
            for x in range(w):
                if out.get_at((x, y)).a == 0 and any(
                        0 <= x + dx < w and 0 <= y + dy < h and out.get_at((x + dx, y + dy)).a > 0
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    halo.set_at((x, y), (*glow, 110))
        halo.blit(out, (0, 0))
        out = halo
    return out


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


def draw_slash(surf, pivot, facing, radius, progress, color, glow=False):
    """Rastro fino do golpe: segue a ponta da arma e some rápido. ``glow``: arma rara, o rastro
    fica mais largo, com uma faixa de luz da cor da arma por dentro."""
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
        if glow:
            for w, k in ((9, 0.25), (6, 0.5)):
                g0 = (c + math.cos(a0) * (radius - 3), c + math.sin(a0) * (radius - 3))
                g1 = (c + math.cos(a1) * (radius - 3), c + math.sin(a1) * (radius - 3))
                pygame.draw.line(layer, (*color[:3], int(alpha * k)), g0, g1, w)
        pygame.draw.line(layer, (255, 255, 255, alpha), p0, p1, 3)
        q0 = (c + math.cos(a0) * (radius - 4), c + math.sin(a0) * (radius - 4))
        q1 = (c + math.cos(a1) * (radius - 4), c + math.sin(a1) * (radius - 4))
        pygame.draw.line(layer, (*color[:3], alpha // 2), q0, q1, 2)
    surf.blit(layer, (round(pivot[0] - c), round(pivot[1] - c)))
