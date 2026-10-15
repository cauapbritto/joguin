"""Câmera que segue os jogadores e afasta o zoom para manter todos na tela.

O zoom anda em degraus (100%, 75% e 60%) e, parado num degrau, a posição da câmera
encaixa na grade desse zoom: assim a redução da imagem cai sempre igual nos mesmos
pixels e a pixel art não "treme" quando a câmera desliza.
"""
import math
import random
from fractions import Fraction

import pygame

from . import config

ZOOM_STEPS = (Fraction(1), Fraction(3, 4), Fraction(3, 5))
ZOOM_IN_MARGIN = 0.06     # para aproximar de novo precisa sobrar essa folga (não fica indo e voltando)


class Camera:
    def __init__(self, world_size, min_zoom=0.6, margin=170):
        self.world_w, self.world_h = world_size
        sw, sh = config.SCREEN_W, config.SCREEN_H
        # nunca mostrar além das bordas do mapa
        self.min_zoom = min(1.0, max(min_zoom, sw / self.world_w, sh / self.world_h))
        lowest = Fraction(self.min_zoom).limit_denominator(20)
        self.levels = [z for z in ZOOM_STEPS if z >= lowest] or [Fraction(1)]
        if self.levels[-1] != lowest and lowest < 1:
            self.levels.append(lowest)
        self.level = self.levels[0]
        self.margin = margin
        self.zoom = 1.0
        self.x = self.y = 0.0
        self._render_x = self._render_y = 0.0
        self._screen_x = self._screen_y = 0.0
        self._shake = 0.0
        self._offset = (0, 0)
        max_view = (math.ceil(sw / self.min_zoom) + 2, math.ceil(sh / self.min_zoom) + 2)
        self._canvas = pygame.Surface(max_view)

    @property
    def view_size(self):
        return (min(self._canvas.get_width(), math.ceil(config.SCREEN_W / self.zoom - 1e-6)),
                min(self._canvas.get_height(), math.ceil(config.SCREEN_H / self.zoom - 1e-6)))

    @property
    def settled(self):
        """O zoom está parado exatamente num degrau."""
        return self.zoom == float(self.level)

    def _pick_level(self, fit):
        """fit: maior zoom em que todo mundo cabe (sem limite). Se o degrau atual não cabe mais,
        afasta na hora; para aproximar de novo, o degrau mais perto precisa caber com folga."""
        if fit < float(self.level) - 1e-9:
            return next((z for z in self.levels if z <= fit + 1e-9), self.levels[-1])
        for z in self.levels:                     # do mais perto para o mais longe
            if z <= self.level:
                break
            if fit >= float(z) * (1 + ZOOM_IN_MARGIN):
                return z
        return self.level

    def focus(self, points, instant=False):
        if not points:
            return
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        span_w = max(xs) - min(xs) + self.margin * 2
        span_h = max(ys) - min(ys) + self.margin * 2
        fit = min(config.SCREEN_W / span_w, config.SCREEN_H / span_h)
        self.level = self._pick_level(fit)
        goal = float(self.level)
        k_zoom, k_pos = (1.0, 1.0) if instant else (0.12, 0.1)
        self.zoom += (goal - self.zoom) * k_zoom
        if abs(goal - self.zoom) < 0.003:
            self.zoom = goal
        vw, vh = config.SCREEN_W / self.zoom, config.SCREEN_H / self.zoom
        cx = (max(xs) + min(xs)) / 2
        cy = (max(ys) + min(ys)) / 2
        tx = min(max(cx - vw / 2, 0), max(0, self.world_w - vw))
        ty = min(max(cy - vh / 2, 0), max(0, self.world_h - vh))
        self.x += (tx - self.x) * k_pos
        self.y += (ty - self.y) * k_pos
        # sacudida
        if self._shake > 0.3:
            s = self._shake
            self._offset = (random.uniform(-s, s), random.uniform(-s, s))
            self._shake *= 0.85
        else:
            self._shake = 0
            self._offset = (0, 0)

    def shake(self, amount):
        self._shake = max(self._shake, amount)

    # ── renderização ─────────────────────────
    def begin(self):
        """Devolve a superfície do mundo visível e prende a posição em pixels inteiros."""
        vw, vh = self.view_size
        self._render_x, self._render_y = self.x, self.y
        x, y = self.x + self._offset[0], self.y + self._offset[1]
        if self.settled and self.level.denominator > 1:
            # zoom 3/4: andar de 4 em 4 pixels do mundo = 3 pixels inteiros da tela
            q = self.level.denominator
            x, y = round(x / q) * q, round(y / q) * q
        self.x = round(min(max(x, 0), max(0, self.world_w - vw)))
        self.y = round(min(max(y, 0), max(0, self.world_h - vh)))
        return self._canvas.subsurface((0, 0, vw, vh))

    def end(self, view, screen):
        if view.get_size() == screen.get_size():
            screen.blit(view, (0, 0))
        else:
            pygame.transform.scale(view, screen.get_size(), screen)
        self._screen_x, self._screen_y = self.x, self.y
        self.x, self.y = self._render_x, self._render_y

    def to_screen(self, wx, wy):
        """Converte posição do mundo para a tela (usar depois de end())."""
        sx = (wx - self._screen_x) * (config.SCREEN_W / self.view_size[0])
        sy = (wy - self._screen_y) * (config.SCREEN_H / self.view_size[1])
        return sx, sy
