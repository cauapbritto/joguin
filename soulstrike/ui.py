"""Primitivas de interface: texto, painéis, barras, listas de menu e dicas de tecla."""
import pygame

from . import config, theme

_ANCHORS = ("center", "topleft", "topright", "midtop", "midleft", "midright",
            "midbottom", "bottomleft", "bottomright")


class UI:
    """Desenha elementos de interface usando a fonte pixel do jogo."""

    def __init__(self, assets):
        self.assets = assets

    # ── texto ────────────────────────────────
    def text(self, surf, text, size, color, pos, anchor="center", shadow=True):
        img = self.assets.text(text, size, color)
        rect = img.get_rect(**{anchor: pos})
        if shadow:
            offset = 1 if size <= theme.S else 2
            surf.blit(self.assets.text(text, size, theme.SHADOW), rect.move(offset, offset))
        surf.blit(img, rect)
        return rect

    def logo(self, surf, center, size=theme.XL):
        """'SOUL STRIKE' de fliperama: letras em degradê (ouro no alto, brasa embaixo) com brilho na
        beirada de cima, sombra na de baixo, contorno duplo e um calor atrás. Montado uma vez só."""
        art = _LOGOS.get(size)
        if art is None:
            art = _LOGOS[size] = _build_logo(self.assets.text("SOUL STRIKE", size, (255, 255, 255)), size)
        img, glow, (ox, oy) = art
        rect = pygame.Rect(0, 0, img.get_width() - ox * 2, img.get_height() - oy * 2)
        rect.center = center
        surf.blit(glow, glow.get_rect(center=rect.center), special_flags=pygame.BLEND_RGB_ADD)
        surf.blit(img, (rect.x - ox, rect.y - oy))
        return rect

    def wrap(self, text, size, width):
        lines = []
        for paragraph in text.split("\n"):
            words, line = paragraph.split(" "), ""
            for word in words:
                trial = f"{line} {word}".strip()
                if self.assets.text_width(trial, size) <= width or not line:
                    line = trial
                else:
                    lines.append(line)
                    line = word
            lines.append(line)
        return lines

    def paragraph(self, surf, text, size, color, topleft, width, spacing=None):
        x, y = topleft
        spacing = spacing or size + size // 2
        for line in self.wrap(text, size, width):
            self.text(surf, line, size, color, (x, y), anchor="topleft", shadow=False)
            y += spacing
        return y

    # ── formas ───────────────────────────────
    def panel(self, surf, rect, fill=theme.INK_2, border=theme.LINE, accent=None, shadow=True):
        rect = pygame.Rect(rect)
        if shadow:
            surf.fill(theme.SHADOW, rect.move(4, 4).inflate(-2, -2))
        surf.fill(fill, rect.inflate(-2, -2))
        # borda com cantos "chanfrados" de 1 px
        x, y, w, h = rect
        surf.fill(border, (x + 2, y, w - 4, 2))
        surf.fill(border, (x + 2, y + h - 2, w - 4, 2))
        surf.fill(border, (x, y + 2, 2, h - 4))
        surf.fill(border, (x + w - 2, y + 2, 2, h - 4))
        for cx, cy in ((x + 1, y + 1), (x + w - 2, y + 1), (x + 1, y + h - 2), (x + w - 2, y + h - 2)):
            surf.fill(border, (cx, cy, 1, 1))
        # volume: o painel escurece aos poucos para baixo, luz por dentro em cima e à esquerda,
        # sombra por dentro embaixo e à direita
        if h > 12:
            band = (h - 4) // 3
            for i, k in enumerate((0.04, 0.08, 0.12)):
                surf.fill(_mix(fill, (0, 0, 0), k), (x + 2, y + h - 2 - band + i * band // 3, w - 4, band - i * band // 3))
        surf.fill(_mix(fill, (255, 255, 255), 0.10), (x + 2, y + 2, w - 4, 1))
        surf.fill(_mix(fill, (255, 255, 255), 0.05), (x + 2, y + 3, 1, h - 5))
        surf.fill(_mix(fill, (0, 0, 0), 0.25), (x + 2, y + h - 3, w - 4, 1))
        surf.fill(_mix(fill, (0, 0, 0), 0.18), (x + w - 3, y + 3, 1, h - 6))
        if accent:
            surf.fill(accent, (x + 2, y + 2, w - 4, 3))
        return rect

    def bar(self, surf, rect, ratio, color, back=theme.INK, ticks=0, flip=False):
        rect = pygame.Rect(rect)
        surf.fill(theme.SHADOW, rect)
        inner = rect.inflate(-2, -2)
        surf.fill(back, inner)
        surf.fill(_mix(back, (0, 0, 0), 0.4), (inner.x, inner.y, inner.w, 1))     # fundo afundado
        ratio = max(0.0, min(1.0, ratio))
        fw = round(inner.w * ratio)
        if fw > 0:
            fill = pygame.Rect(inner.right - fw if flip else inner.x, inner.y, fw, inner.h)
            surf.fill(color, fill)
            surf.fill(_mix(color, (255, 255, 255), 0.35), (fill.x, fill.y, fill.w, max(1, inner.h // 4)))
            if inner.h >= 5:                          # barra cilíndrica: brilho fino em cima, sombra embaixo
                surf.fill(_mix(color, (255, 255, 255), 0.6), (fill.x + 1, fill.y, max(1, fill.w - 2), 1))
                surf.fill(_mix(color, (0, 0, 0), 0.16), (fill.x, fill.bottom - 2, fill.w, 1))
            surf.fill(_mix(color, (0, 0, 0), 0.3), (fill.x, fill.bottom - 1, fill.w, 1))
            if fw < inner.w and fw > 1:               # ponta da barra acesa
                tip = fill.x if flip else fill.right - 1
                surf.fill(_mix(color, (255, 255, 255), 0.45), (tip, fill.y, 1, fill.h - 1))
        if ticks:
            for i in range(1, ticks):
                tx = inner.x + inner.w * i // ticks
                surf.fill(theme.SHADOW, (tx, inner.y, 1, inner.h))
        return rect

    def arrow(self, surf, center, direction, size, color):
        cx, cy = center
        s = size
        pts = {
            "left": [(cx + s // 2, cy - s), (cx - s // 2, cy), (cx + s // 2, cy + s)],
            "right": [(cx - s // 2, cy - s), (cx + s // 2, cy), (cx - s // 2, cy + s)],
            "up": [(cx - s, cy + s // 2), (cx, cy - s // 2), (cx + s, cy + s // 2)],
            "down": [(cx - s, cy - s // 2), (cx, cy + s // 2), (cx + s, cy - s // 2)],
        }[direction]
        pygame.draw.polygon(surf, color, pts)

    def keycap(self, surf, label, pos, anchor="midleft", color=theme.BONE):
        w = self.assets.text_width(label, theme.XS) + 10
        rect = pygame.Rect(0, 0, max(w, 18), 16)
        setattr(rect, anchor, pos)
        surf.fill(theme.SHADOW, rect.move(0, 2))
        surf.fill(theme.LINE_HI, rect)
        surf.fill(theme.INK_3, rect.inflate(-2, -2))
        self.text(surf, label, theme.XS, color, rect.center, shadow=False)
        return rect

    def hints(self, surf, items, pos, anchor="center", gap=18):
        """Linha de dicas: [(tecla, ação), ...] desenhada como teclas + texto."""
        widths = []
        for key, action in items:
            kw = max(self.assets.text_width(key, theme.XS) + 10, 18)
            widths.append(kw + 6 + self.assets.text_width(action, theme.XS))
        total = sum(widths) + gap * (len(items) - 1)
        x, y = pos
        if anchor == "center":
            x -= total // 2
        elif anchor == "right":
            x -= total
        for (key, action), w in zip(items, widths):
            cap = self.keycap(surf, key, (x, y), anchor="midleft")
            self.text(surf, action, theme.XS, theme.MUTED, (cap.right + 6, y), anchor="midleft", shadow=False)
            x += w + gap


class MenuList:
    """Lista vertical de opções navegável por teclado e mouse.

    Os retângulos clicáveis são os mesmos usados no desenho, então clique e
    imagem nunca ficam desalinhados.
    """

    def __init__(self, options, topleft, width, row_h=34, size=theme.S):
        self.options = list(options)        # [(rótulo, valor)]
        self.index = 0
        self.size = size
        x, y = topleft
        self.rects = [pygame.Rect(x, y + i * row_h, width, row_h - 6) for i in range(len(self.options))]
        self.enabled = [True] * len(self.options)

    @property
    def value(self):
        return self.options[self.index][1]

    def move(self, step):
        n = len(self.options)
        for _ in range(n):
            self.index = (self.index + step) % n
            if self.enabled[self.index]:
                return

    def handle(self, event, sfx=None):
        """Devolve o valor escolhido (Enter/clique) ou None."""
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.move(-1)
                sfx and sfx("select", 0.25)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.move(1)
                sfx and sfx("select", 0.25)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                return self.value
        elif event.type == pygame.MOUSEMOTION:
            for i, r in enumerate(self.rects):
                if r.collidepoint(event.pos) and self.enabled[i] and i != self.index:
                    self.index = i
                    sfx and sfx("hover", 0.15)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, r in enumerate(self.rects):
                if r.collidepoint(event.pos) and self.enabled[i]:
                    self.index = i
                    return self.value
        return None

    def draw(self, surf, ui, ticks=0):
        for i, ((label, _), rect) in enumerate(zip(self.options, self.rects)):
            selected = i == self.index
            if not self.enabled[i]:
                color = theme.FAINT
            else:
                color = theme.BRASS if selected else theme.BONE
            if selected:
                surf.fill(theme.INK_3, rect)
                for k in range(8):                       # luz da faixa escolhida some para a direita
                    band = rect.w * (8 - k) // 8
                    surf.fill((7, 5, 2), (rect.x, rect.y, band, rect.h), special_flags=pygame.BLEND_RGB_ADD)
                surf.fill(_mix(theme.INK_3, theme.BRASS, 0.25), (rect.x + 3, rect.y, rect.w * 3 // 4, 1))
                surf.fill(_mix(theme.INK_3, (0, 0, 0), 0.4), (rect.x + 3, rect.bottom - 1, rect.w - 3, 1))
                surf.fill(theme.BRASS, (rect.x, rect.y, 3, rect.h))
                surf.fill(_mix(theme.BRASS, (255, 255, 255), 0.4), (rect.x, rect.y, 1, rect.h))
                nudge = 1 if (ticks // 20) % 2 else 0
                ui.arrow(surf, (rect.x + 16 + nudge, rect.centery), "right", 6, theme.BRASS)
            ui.text(surf, label, self.size, color, (rect.x + 32, rect.centery + 1), anchor="midleft")


def _mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


_LOGOS = {}
_LOGO_STOPS = ((0.0, (255, 240, 184)), (0.22, (244, 196, 92)), (0.5, theme.BRASS), (0.56, theme.EMBER),
               (0.8, (196, 78, 46)), (1.0, (138, 44, 36)))


def _shifted(mask, dx, dy):
    out = pygame.mask.Mask(mask.get_size())
    out.draw(mask, (dx, dy))
    return out


def _build_logo(white, size):
    """Monta o logo a partir do texto branco: devolve (imagem, brilho de fundo, folga da borda)."""
    w, h = white.get_size()
    o = max(2, size // 12)                         # grossura do contorno (o "pixel" da fonte)
    pad_x, pad_y = o * 2 + 2, o * 2 + 2
    glyph = pygame.mask.from_surface(white, 1)
    grad = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):                             # degradê de cima para baixo, em faixas duras
        t = y / max(1, h - 1)
        for (a, ca), (b, cb) in zip(_LOGO_STOPS, _LOGO_STOPS[1:]):
            if a <= t <= b:
                k = (t - a) / max(1e-6, b - a)
                k = round(k * 3) / 3               # 4 tons por trecho, como pixel art
                grad.fill((*_mix(ca, cb, k), 255), (0, y, w, 1))
                break
    grad.blit(glyph.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0)), (0, 0),
              special_flags=pygame.BLEND_RGBA_MULT)
    step = max(1, o // 2)
    top = glyph.copy()
    top.erase(_shifted(glyph, 0, step), (0, 0))    # beirada de cima de cada letra: brilho
    low = glyph.copy()
    low.erase(_shifted(glyph, 0, -step), (0, 0))   # beirada de baixo: sombra
    grad.blit(top.to_surface(setcolor=(255, 228, 160, 255), unsetcolor=(0, 0, 0, 0)), (0, 0))
    grad.blit(low.to_surface(setcolor=(110, 34, 30, 255), unsetcolor=(0, 0, 0, 0)), (0, 0))
    img = pygame.Surface((w + pad_x * 2, h + pad_y * 2), pygame.SRCALPHA)
    outer = glyph.to_surface(setcolor=(52, 18, 44, 255), unsetcolor=(0, 0, 0, 0))
    ink = glyph.to_surface(setcolor=(8, 4, 10, 255), unsetcolor=(0, 0, 0, 0))
    big = o + max(1, o // 2)
    for dx in range(-big, big + 1, max(1, big // 2)):
        for dy in range(-big, big * 2 + 1, max(1, big // 2)):
            img.blit(outer, (pad_x + dx, pad_y + dy))
    for dx in (-o, 0, o):
        for dy in (-o, 0, o, o * 2):
            img.blit(ink, (pad_x + dx, pad_y + dy))
    img.blit(grad, (pad_x, pad_y))
    gw, gh = w + 160, h + 90                       # calor de brasa atrás do logo (soma na tela)
    glow = pygame.Surface((gw, gh))
    for i in range(12, 0, -1):
        k = i / 12
        c = (round(34 * (1 - k) ** 1.5), round(14 * (1 - k) ** 1.5), round(8 * (1 - k) ** 1.5))
        pygame.draw.ellipse(glow, c, (gw * (1 - k) / 2, gh * (1 - k) / 2, gw * k, gh * k))
    return img, glow, (pad_x, pad_y)


def mix(a, b, t):
    return _mix(a, b, t)


_VEILS = {}


def darken(surface, alpha):
    """Escurece a tela inteira (o véu é guardado: a pausa chama isso todo quadro)."""
    key = (surface.get_size(), alpha)
    veil = _VEILS.get(key)
    if veil is None:
        veil = _VEILS[key] = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        veil.fill((0, 0, 0, alpha))
    surface.blit(veil, (0, 0))


class Backdrop:
    """Fundo dos menus: arte da arena escurecida com um leve movimento."""

    def __init__(self, assets, map_key="arena_classica"):
        bg = assets.backgrounds.get(map_key)
        w, h = config.SCREEN_W, config.SCREEN_H
        if bg is None:
            self.image = pygame.Surface((w + 120, h + 80))
            self.image.fill(theme.INK)
        else:
            scale = max((w + 120) / bg.get_width(), (h + 80) / bg.get_height())
            size = (round(bg.get_width() * scale), round(bg.get_height() * scale))
            self.image = pygame.transform.scale(bg, size)
        shade = pygame.Surface(self.image.get_size(), pygame.SRCALPHA)
        shade.fill((8, 6, 14, 150))
        self.image.blit(shade, (0, 0))
        self.vignette = _vignette(w, h)

    def draw(self, surf, ticks):
        import math
        ox = 60 + math.sin(ticks * 0.004) * 50
        oy = 40 + math.cos(ticks * 0.003) * 30
        surf.blit(self.image, (-ox, -oy))
        _embers(surf, ticks)
        surf.blit(self.vignette, (0, 0))


_EMBER_SEEDS = [((i * 0.6180339) % 1.0, (i * 0.4142135) % 1.0, 0.35 + (i * 0.7320508) % 1.0, i % 3)
                for i in range(70)]
_EMBER_COLORS = ((228, 170, 76), (222, 104, 56), (200, 170, 255))


def _embers(surf, ticks):
    """Brasas e almas subindo devagar pelo fundo dos menus (poucos pixels por quadro)."""
    import math
    w, h = surf.get_size()
    t = ticks * 0.02
    for fx, fy, speed, kind in _EMBER_SEEDS:
        y = h + 10 - ((fy * (h + 20) + t * speed * 14) % (h + 20))
        x = fx * w + math.sin(t * 0.6 + fy * 9) * 14
        life = y / h                                  # some ao chegar perto do topo
        flick = 0.6 + 0.4 * math.sin(t * 3 + fx * 20)
        k = max(0.0, min(1.0, life * flick))
        if k < 0.08:
            continue
        r, g, b = _EMBER_COLORS[kind]
        col = (round(r * k), round(g * k), round(b * k))
        n = 2 if speed > 0.9 else 1
        surf.fill(col, (round(x), round(y), n, n), special_flags=pygame.BLEND_RGB_ADD)
        if n == 2:                                    # rastro curtinho
            surf.fill((col[0] // 3, col[1] // 3, col[2] // 3), (round(x), round(y) + 2, 2, 3),
                      special_flags=pygame.BLEND_RGB_ADD)


def _vignette(w, h):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    steps = 24
    for i in range(steps):
        alpha = int(150 * (1 - i / steps) ** 2)
        pygame.draw.rect(surf, (0, 0, 0, alpha), (i * 6, i * 4, w - i * 12, h - i * 8), 6)
    return surf
