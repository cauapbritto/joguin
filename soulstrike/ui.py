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
        """'SOUL STRIKE' com contorno grosso e duas cores, no estilo de fliperama."""
        text = "SOUL STRIKE"
        top = self.assets.text(text, size, theme.BRASS)
        low = self.assets.text(text, size, theme.EMBER)
        ink = self.assets.text(text, size, theme.SHADOW)
        rect = top.get_rect(center=center)
        o = max(2, size // 12)
        for dx in (-o, 0, o):
            for dy in (-o, 0, o, o * 2):
                surf.blit(ink, rect.move(dx, dy))
        surf.blit(low, rect)
        surf.blit(top, rect, (0, 0, rect.w, rect.h * 11 // 20))
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
        # brilho interno no topo
        surf.fill(_mix(fill, (255, 255, 255), 0.06), (x + 2, y + 2, w - 4, 1))
        if accent:
            surf.fill(accent, (x + 2, y + 2, w - 4, 3))
        return rect

    def bar(self, surf, rect, ratio, color, back=theme.INK, ticks=0, flip=False):
        rect = pygame.Rect(rect)
        surf.fill(theme.SHADOW, rect)
        inner = rect.inflate(-2, -2)
        surf.fill(back, inner)
        ratio = max(0.0, min(1.0, ratio))
        fw = round(inner.w * ratio)
        if fw > 0:
            fill = pygame.Rect(inner.right - fw if flip else inner.x, inner.y, fw, inner.h)
            surf.fill(color, fill)
            surf.fill(_mix(color, (255, 255, 255), 0.35), (fill.x, fill.y, fill.w, max(1, inner.h // 4)))
            surf.fill(_mix(color, (0, 0, 0), 0.3), (fill.x, fill.bottom - 1, fill.w, 1))
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
                surf.fill(theme.BRASS, (rect.x, rect.y, 3, rect.h))
                nudge = 1 if (ticks // 20) % 2 else 0
                ui.arrow(surf, (rect.x + 16 + nudge, rect.centery), "right", 6, theme.BRASS)
            ui.text(surf, label, self.size, color, (rect.x + 32, rect.centery + 1), anchor="midleft")


def _mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


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
        surf.blit(self.vignette, (0, 0))


def _vignette(w, h):
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    steps = 24
    for i in range(steps):
        alpha = int(150 * (1 - i / steps) ** 2)
        pygame.draw.rect(surf, (0, 0, 0, alpha), (i * 6, i * 4, w - i * 12, h - i * 8), 6)
    return surf
