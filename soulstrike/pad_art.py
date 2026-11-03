"""Controle desenhado em pixel art (tela CONTROLE), no jeito de cada família: Xbox, PlayStation e
Nintendo. No Nintendo o A fica à direita e o B embaixo (e o X em cima, o Y à esquerda), como está
escrito no controle; o SDL já entrega o botão pelo nome escrito nele."""
import pygame

from . import theme

FACE_COLORS = {"a": (96, 190, 96), "b": (214, 74, 64), "x": (86, 136, 232), "y": (236, 190, 70)}
PS_COLORS = {"a": (110, 150, 235), "b": (225, 85, 85), "x": (220, 120, 200), "y": (80, 200, 170)}
# posição dos botões de cima, em pixels do desenho (96 x 60)
FACE_XBOX = {"y": (74, 15), "x": (67, 22), "b": (81, 22), "a": (74, 29)}
FACE_NINTENDO = {"x": (74, 15), "y": (67, 22), "a": (81, 22), "b": (74, 29)}
FACE_JOYCON = {"y": (68, 25), "x": (61, 32), "b": (75, 32), "a": (68, 39)}
BODY = {"xbox": (58, 52, 72), "playstation": (206, 204, 214), "nintendo": (50, 50, 58),
        "joycon": (230, 70, 60)}
EDGE = (22, 19, 30)


def _rounded(s, color, rect, r):
    pygame.draw.rect(s, color, rect, border_radius=r)


def face_positions(fam):
    return {"nintendo": FACE_NINTENDO, "joycon": FACE_JOYCON}.get(fam, FACE_XBOX)


def draw_symbol(surf, fam, button, center, size=5, color=None):
    """Símbolo do PlayStation (✕ ○ □ △) desenhado (a fonte não tem esses caracteres)."""
    cx, cy = center
    col = color or PS_COLORS[button]
    if button == "a":
        pygame.draw.line(surf, col, (cx - size, cy - size), (cx + size, cy + size), 2)
        pygame.draw.line(surf, col, (cx - size, cy + size), (cx + size, cy - size), 2)
    elif button == "b":
        pygame.draw.circle(surf, col, (cx, cy), size + 1, 2)
    elif button == "x":
        pygame.draw.rect(surf, col, (cx - size, cy - size, size * 2 + 1, size * 2 + 1), 2)
    else:
        pygame.draw.polygon(surf, col, [(cx, cy - size - 1), (cx - size - 1, cy + size), (cx + size + 1, cy + size)], 2)


def keycap(surf, ui, fam, button, pos, labels, anchor="midleft", color=theme.BONE):
    """Tecla com o nome do botão (no PlayStation, o símbolo desenhado)."""
    if fam == "playstation" and button in ("a", "b", "x", "y"):
        rect = ui.keycap(surf, "  ", pos, anchor=anchor, color=color)
        draw_symbol(surf, fam, button, rect.center, size=4)
        return rect
    return ui.keycap(surf, labels.get(button, button.upper()), pos, anchor=anchor, color=color)


def _joycon(layer, body):
    """Joy-Con deitado: analógico à esquerda, os 4 botões à direita, SL e SR no trilho de cima."""
    light = tuple(min(255, c + 30) for c in body)
    _rounded(layer, EDGE, (7, 17, 82, 32), 15)
    _rounded(layer, body, (8, 18, 80, 30), 14)
    layer.fill(light, (18, 19, 60, 1))
    layer.fill((40, 38, 50), (20, 14, 56, 4))                 # trilho
    for x0 in (28, 58):
        _rounded(layer, EDGE, (x0 - 1, 12, 12, 5), 2)
        _rounded(layer, (210, 208, 218), (x0, 13, 10, 3), 1)
    pygame.draw.circle(layer, EDGE, (24, 33), 7)
    pygame.draw.circle(layer, (40, 38, 50), (24, 33), 6)
    pygame.draw.circle(layer, (90, 88, 100), (24, 33), 4)
    pygame.draw.circle(layer, EDGE, (44, 25), 2)
    return {"ls": (24, 33), "lb": (33, 14), "rb": (63, 14), "start": (44, 25), "back": (44, 25)}


def draw_pad(surf, ui, fam, center, k=4, lit=None, pulse=0.0, pressed=()):
    """Desenha o controle e devolve onde fica cada botão na tela ({botão: (x, y)})."""
    layer = pygame.Surface((96, 60), pygame.SRCALPHA)
    if fam == "joycon":
        return _draw_joycon(surf, ui, layer, center, k, lit, pulse, pressed)
    body = BODY.get(fam, BODY["xbox"])
    light = tuple(min(255, c + 22) for c in body)
    dark = tuple(max(0, c - 18) for c in body)
    stick = (100, 94, 118) if fam != "playstation" else (60, 58, 70)
    for x0 in (10, 66):
        _rounded(layer, EDGE, (x0 - 1, 1, 22, 9), 3)
        _rounded(layer, light, (x0, 2, 20, 7), 3)
        _rounded(layer, EDGE, (x0 - 2, 7, 24, 7), 2)
        _rounded(layer, tuple(min(255, c + 30) for c in body), (x0 - 1, 8, 22, 5), 2)
    for cx0 in (20, 76):
        pygame.draw.ellipse(layer, EDGE, (cx0 - 15, 20, 30, 40))
        pygame.draw.ellipse(layer, body, (cx0 - 14, 21, 28, 38))
    _rounded(layer, EDGE, (6, 11, 84, 32), 12)
    _rounded(layer, body, (7, 12, 82, 30), 11)
    layer.fill(light, (16, 13, 64, 1))
    if fam == "playstation":
        _rounded(layer, (40, 38, 50), (36, 14, 24, 12), 3)        # touchpad
    # Xbox e PlayStation: analógico esquerdo em cima; no PlayStation os dois ficam embaixo
    sticks = ((30, 34), (60, 34)) if fam == "playstation" else ((22, 22), (60, 34))
    dpad = (22, 22) if fam == "playstation" else (36, 34)
    for (x, y) in sticks:
        pygame.draw.circle(layer, EDGE, (x, y), 7)
        pygame.draw.circle(layer, dark, (x, y), 6)
        pygame.draw.circle(layer, stick, (x, y), 4)
        pygame.draw.circle(layer, tuple(min(255, c + 20) for c in stick), (x - 1, y - 1), 2)
    dx, dy = dpad
    layer.fill(EDGE, (dx - 7, dy - 3, 15, 7))
    layer.fill(EDGE, (dx - 3, dy - 7, 7, 15))
    layer.fill(dark, (dx - 6, dy - 2, 13, 5))
    layer.fill(dark, (dx - 2, dy - 6, 5, 13))
    back, start = ((33, 16), (63, 16)) if fam == "playstation" else ((42, 23), (54, 23))
    for (x, y) in (back, start):
        _rounded(layer, EDGE, (x - 3, y - 2, 6, 4), 2)
    pygame.draw.circle(layer, EDGE, (48, 16 if fam != "playstation" else 30), 3)
    pygame.draw.circle(layer, theme.BRASS, (48, 16 if fam != "playstation" else 30), 2)
    face = face_positions(fam)
    for b, (x, y) in face.items():
        pygame.draw.circle(layer, EDGE, (x, y + 1), 5)
        if fam == "xbox":
            col = FACE_COLORS[b]
        elif fam == "playstation":
            col = (40, 38, 50)
        else:
            col = (200, 198, 208)
        if b in pressed:
            col = theme.BRASS
        pygame.draw.circle(layer, col, (x, y), 4)
    big = pygame.transform.scale(layer, (96 * k, 60 * k))
    rect = big.get_rect(center=center)
    surf.blit(big, rect)

    def at(px, py):
        return (rect.x + px * k + k // 2, rect.y + py * k + k // 2)

    anchors = {"lt": at(20, 4), "lb": at(20, 10), "rt": at(76, 4), "rb": at(76, 10),
               "ls": at(*sticks[0]), "rs": at(*sticks[1]), "dpad": at(dx, dy), "back": at(*back), "start": at(*start),
               **{b: at(*p) for b, p in face.items()}}
    for b in face:
        x, y = anchors[b]
        if fam == "playstation":
            draw_symbol(surf, fam, b, (x, y), size=5)
        else:
            ui.text(surf, b.upper(), theme.S if k >= 4 else theme.XS, (20, 18, 26), (x + 1, y + 1), shadow=False)
    for b in pressed:
        if b in ("lt", "rt", "lb", "rb", "back", "start"):
            pygame.draw.circle(surf, theme.BRASS, anchors[b], 2 * k)
    if lit:
        x, y = anchors[lit]
        rad = int(5 * k + pulse * 6)
        glow = pygame.Surface((rad * 4, rad * 4), pygame.SRCALPHA)
        for i in range(6, 0, -1):
            pygame.draw.circle(glow, (*theme.BRASS, 18 * i), (rad * 2, rad * 2), rad + i * 3)
        surf.blit(glow, glow.get_rect(center=(x, y)))
        pygame.draw.circle(surf, theme.BRASS, (x, y), rad, 3)
    return anchors


def _glow(surf, pos, k, pulse):
    x, y = pos
    rad = int(5 * k + pulse * 6)
    glow = pygame.Surface((rad * 4, rad * 4), pygame.SRCALPHA)
    for i in range(6, 0, -1):
        pygame.draw.circle(glow, (*theme.BRASS, 18 * i), (rad * 2, rad * 2), rad + i * 3)
    surf.blit(glow, glow.get_rect(center=(x, y)))
    pygame.draw.circle(surf, theme.BRASS, (x, y), rad, 3)


def _draw_joycon(surf, ui, layer, center, k, lit, pulse, pressed):
    spots = _joycon(layer, BODY["joycon"])
    for b, (x, y) in FACE_JOYCON.items():
        pygame.draw.circle(layer, EDGE, (x, y + 1), 5)
        pygame.draw.circle(layer, theme.BRASS if b in pressed else (40, 38, 50), (x, y), 4)
    big = pygame.transform.scale(layer, (96 * k, 60 * k))
    rect = big.get_rect(center=center)
    surf.blit(big, rect)

    def at(px, py):
        return (rect.x + px * k + k // 2, rect.y + py * k + k // 2)

    anchors = {b: at(*p) for b, p in spots.items()}
    anchors.update({b: at(*p) for b, p in FACE_JOYCON.items()})
    arrows = {"a": "down", "b": "right", "x": "left", "y": "up"}
    for b, d in arrows.items():
        ui.arrow(surf, anchors[b], d, 2 * k, (230, 228, 236))
    for b in pressed:
        if b in ("lb", "rb", "start", "back"):
            pygame.draw.circle(surf, theme.BRASS, anchors[b], 2 * k)
    if lit and lit in anchors:
        _glow(surf, anchors[lit], k, pulse)
    return anchors
