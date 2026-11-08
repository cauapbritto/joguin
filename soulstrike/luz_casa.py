"""A luz da Casa pela hora do relógio do computador: o sol entrando pelas janelas de manhã, branco
ao meio-dia, alaranjado no fim da tarde e o luar azulado de noite (com o vidro escuro e estrelinhas).
De quebra, o forno da padaria solta uma fumacinha de vez em quando."""
import random
import time

import pygame

from .entities import Particle

# período: (horas, cor da luz no chão, força, inclinação, tinta no vidro ou None)
PERIODS = (
    ("manhã", range(6, 10), (255, 228, 160), 40, 60, None),
    ("dia", range(10, 16), (255, 248, 222), 30, 10, None),
    ("tarde", range(16, 19), (255, 160, 80), 46, -70, (255, 140, 60, 70)),
    ("noite", range(0, 24), (150, 170, 255), 18, -20, (16, 24, 60, 170)),
)
BEAM_LEN = 170


def period(hour=None):
    hour = time.localtime().tm_hour if hour is None else hour
    return next(p for p in PERIODS if hour in p[1])


class CasaLight:
    """Efeito da Casa: a luz das janelas (debaixo de todo mundo) e a fumaça do forno."""

    alive = True

    def __init__(self, windows, chimney=None, hour=None):
        self.windows = windows            # [(x, y, largura do vidro, altura)]
        self.chimney = chimney
        self.hour = hour                  # None: a hora do computador (muda sozinha com o tempo)
        self.age = 0
        self._beams = {}

    @property
    def name(self):
        return period(self.hour)[0]

    def update(self, match):
        self.age += 1
        if self.chimney is not None and self.age % 22 == 0:
            x, y = self.chimney
            match.particles.append(Particle(x + random.uniform(-4, 4), y, random.uniform(-0.2, 0.2),
                                            random.uniform(-0.9, -0.5), (226, 222, 216), random.randint(34, 50), 5,
                                            -0.004))

    def _beam(self, w, color, alpha, lean):
        key = (w, color, alpha, lean)
        if key not in self._beams:
            pad = abs(lean) + 40
            surf = pygame.Surface((w + 2 * pad, BEAM_LEN), pygame.SRCALPHA)
            for k in range(8):                                # mais forte perto da janela, some no chão
                a = round(alpha * (1 - k / 8))
                y0, y1 = k * BEAM_LEN // 8, (k + 1) * BEAM_LEN // 8
                f0, f1 = y0 / BEAM_LEN, y1 / BEAM_LEN
                pts = [(pad + lean * f0 - 20 * f0, y0), (pad + w + lean * f0 + 20 * f0, y0),
                       (pad + w + lean * f1 + 20 * f1, y1), (pad + lean * f1 - 20 * f1, y1)]
                pygame.draw.polygon(surf, (*color, a), pts)
            self._beams[key] = (surf, pad)
        return self._beams[key]

    def draw(self, surf, cam):
        name, _, color, alpha, lean, tint = period(self.hour)
        for x, y, w, h in self.windows:
            sx, sy = round(x - cam.x), round(y - cam.y)
            if tint is not None:
                glass = pygame.Surface((w, h), pygame.SRCALPHA)
                glass.fill(tint)
                surf.blit(glass, (sx, sy))
                if name == "noite":
                    for k, (dx, dy) in enumerate(((14, 8), (44, 14), (86, 6), (100, 18))):
                        if (self.age // 40 + k) % 3:
                            surf.fill((240, 240, 255), (sx + dx, sy + dy, 2, 2))
                    pygame.draw.circle(surf, (236, 236, 220), (sx + w - 26, sy + 12), 6)
            beam, pad = self._beam(w, color, alpha, lean)
            surf.blit(beam, (sx - pad, sy + h + 6))
