"""Câmera que segue os jogadores e afasta o zoom para manter todos na tela."""
import math
import random

import pygame

from . import config


class Camera:
    def __init__(self, world_size, min_zoom=0.6, margin=170):
        self.world_w, self.world_h = world_size
        sw, sh = config.SCREEN_W, config.SCREEN_H
        # nunca mostrar além das bordas do mapa
        self.min_zoom = min(1.0, max(min_zoom, sw / self.world_w, sh / self.world_h))
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
        return (min(self._canvas.get_width(), math.ceil(config.SCREEN_W / self.zoom)),
                min(self._canvas.get_height(), math.ceil(config.SCREEN_H / self.zoom)))

    def focus(self, points, instant=False):
        if not points:
            return
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        span_w = max(xs) - min(xs) + self.margin * 2
        span_h = max(ys) - min(ys) + self.margin * 2
        target_zoom = min(1.0, config.SCREEN_W / span_w, config.SCREEN_H / span_h)
        target_zoom = max(self.min_zoom, target_zoom)
        k_zoom, k_pos = (1.0, 1.0) if instant else (0.05, 0.1)
        self.zoom += (target_zoom - self.zoom) * k_zoom
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
        self.x = round(min(max(self.x + self._offset[0], 0), max(0, self.world_w - vw)))
        self.y = round(min(max(self.y + self._offset[1], 0), max(0, self.world_h - vh)))
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
