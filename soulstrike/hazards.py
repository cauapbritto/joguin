"""Perigos de algumas masmorras do capítulo 2 (Lag Lobby). Cada um avisa antes de pegar:

- laser (Corredor de servidores): feixes atravessam o chão de lado a lado. Primeiro aparece a
  linha pontilhada e os emissores piscam; depois o feixe queima quem estiver em cima dele.
- vento (Heliponto): rajadas empurram todo mundo para um lado. As setas aparecem antes, e quem
  está atrás de uma parede (do lado de onde o vento vem) fica protegido.
"""
import random

import pygame

from . import theme

LASER_RED = (255, 54, 70)
LASER_CORE = (255, 220, 226)


class Beam:
    """Um feixe de laser no chão: horizontal ("h", na altura ``pos``) ou vertical ("v")."""

    WARN = 54
    BURN = 24
    HALF = 9                      # metade da grossura de quem queima

    def __init__(self, axis, pos, length, delay=0):
        self.axis = axis
        self.pos = pos
        self.length = length
        self.age = -delay
        self.hit = set()

    @property
    def burning(self):
        return self.WARN <= self.age < self.WARN + self.BURN

    @property
    def done(self):
        return self.age >= self.WARN + self.BURN

    def touches(self, f):
        d = abs((f.y if self.axis == "h" else f.x) - self.pos)
        return d < self.HALF + f.radius * 0.5

    def update(self, match, damage):
        self.age += 1
        if self.age == self.WARN:
            match.assets.play("laser", 0.35)
        if not self.burning:
            return
        for f in match.fighters:
            if f in self.hit or not f.alive_in_match or f.lift > 0 or not self.touches(f):
                continue
            self.hit.add(f)
            if f.take_damage(damage, f.x, f.y, match=match):
                match.burst(f.x, f.y - 10, LASER_RED, 6, speed=3)

    def draw(self, view, cam, frame):
        if self.age < 0:
            return
        w, h = view.get_size()
        if self.axis == "h":
            y = round(self.pos - cam.y)
            if not -20 < y < h + 20:
                return
            a, b = (0, y), (w, y)
            emitters = ((round(-cam.x) + 6, y), (round(self.length - cam.x) - 6, y))
        else:
            x = round(self.pos - cam.x)
            if not -20 < x < w + 20:
                return
            a, b = (x, 0), (x, h)
            emitters = ((x, round(-cam.y) + 6), (x, round(self.length - cam.y) - 6))
        if self.burning:
            t = (self.age - self.WARN) / self.BURN
            width = round(self.HALF * 2 * (1 - 0.5 * t))
            pygame.draw.line(view, (120, 20, 34), a, b, width + 6)
            pygame.draw.line(view, LASER_RED, a, b, width)
            pygame.draw.line(view, LASER_CORE, a, b, max(1, width // 3))
        else:
            # aviso: linha pontilhada que vai ficando mais cheia
            t = self.age / self.WARN
            dash, gap = 10, max(2, round(14 * (1 - t)))
            on = (frame // 4) % 2 == 0 or t > 0.75
            color = LASER_RED if on else (130, 30, 40)
            if self.axis == "h":
                for x in range(-((frame * 2) % (dash + gap)), w, dash + gap):
                    view.fill(color, (x, a[1] - 1, dash, 2))
            else:
                for y in range(-((frame * 2) % (dash + gap)), h, dash + gap):
                    view.fill(color, (a[0] - 1, y, 2, dash))
        for ex, ey in emitters:
            lit = self.burning or (frame // 5) % 2 == 0
            view.fill((40, 44, 56), (ex - 6, ey - 6, 12, 12))
            view.fill(LASER_RED if lit else (90, 26, 34), (ex - 3, ey - 3, 6, 6))


class LaserGrid:
    """Corredor de servidores: de tempos em tempos, um ou dois feixes atravessam o corredor."""

    DAMAGE = 12
    GAP = (120, 170)

    def __init__(self, arena, rng=random):
        self.arena = arena
        self.rng = rng
        self.beams = []
        self.timer = 90

    def _free_line(self, axis):
        """Uma altura (ou coluna) onde o feixe passa por chão livre na maior parte do caminho."""
        arena = self.arena
        for _ in range(20):
            if axis == "h":
                pos = self.rng.uniform(120, arena.height - 120)
                free = sum(arena.is_free(x, pos, 4) for x in range(40, arena.width, 80))
                total = len(range(40, arena.width, 80))
            else:
                pos = self.rng.uniform(120, arena.width - 120)
                free = sum(arena.is_free(pos, y, 4) for y in range(40, arena.height, 80))
                total = len(range(40, arena.height, 80))
            if free >= total * 0.6:
                return pos
        return (arena.height if axis == "h" else arena.width) / 2

    def update(self, match):
        self.timer -= 1
        if self.timer <= 0:
            self.timer = self.rng.randint(*self.GAP)
            count = 2 if self.rng.random() < 0.35 else 1
            for k in range(count):
                axis = "v" if self.rng.random() < 0.55 else "h"
                length = self.arena.width if axis == "h" else self.arena.height
                self.beams.append(Beam(axis, self._free_line(axis), length, delay=k * 20))
        for beam in self.beams:
            beam.update(match, round(self.DAMAGE * match.enemy_dmg))
        self.beams = [b for b in self.beams if not b.done]

    def draw(self, view, cam, frame):
        for beam in self.beams:
            beam.draw(view, cam, frame)

    def draw_screen(self, screen, ui, frame):
        pass


class Wind:
    """Heliponto: rajadas de vento. Aviso (setas) → sopra empurrando → calmaria."""

    WARN = 70
    BLOW = 110
    GAP = (200, 280)
    PUSH = 1.8
    SHELTER = 110                 # parede até essa distância, do lado do vento, protege

    def __init__(self, arena, rng=random):
        self.arena = arena
        self.rng = rng
        self.state = "calm"
        self.timer = 160
        self.dir = (1.0, 0.0)
        self.streaks = [(rng.uniform(0, 1), rng.uniform(0, 1), rng.uniform(0.6, 1.4)) for _ in range(46)]

    @property
    def blowing(self):
        return self.state == "blow"

    def sheltered(self, f):
        dx, dy = self.dir
        return self.arena.blocks_segment((f.x, f.y), (f.x - dx * self.SHELTER, f.y - dy * self.SHELTER))

    def update(self, match):
        self.timer -= 1
        if self.state == "calm" and self.timer <= 0:
            self.state, self.timer = "warn", self.WARN
            self.dir = self.rng.choice(((1.0, 0.0), (-1.0, 0.0), (0.0, 1.0), (0.0, -1.0)))
            match.assets.play("vento", 0.5)
        elif self.state == "warn" and self.timer <= 0:
            self.state, self.timer = "blow", self.BLOW
        elif self.state == "blow":
            ease = min(1.0, (self.BLOW - self.timer) / 20, self.timer / 20)
            dx, dy = self.dir
            for f in match.fighters:
                if not f.alive_in_match or f.lift > 0 or self.sheltered(f):
                    continue
                k = self.PUSH * ease * (1 - getattr(f, "knock_resist", 0.0))
                if k <= 0.01:
                    continue
                f.x += dx * k
                f.y += dy * k
                self.arena.resolve(f)
            if self.timer <= 0:
                self.state, self.timer = "calm", self.rng.randint(*self.GAP)

    def draw(self, view, cam, frame):
        pass

    def draw_screen(self, screen, ui, frame):
        if self.state == "calm":
            return
        w, h = screen.get_size()
        dx, dy = self.dir
        if self.state == "blow":
            # riscos de vento atravessando a tela
            for fx, fy, sp in self.streaks:
                length = round(26 * sp)
                if dx:
                    x = (fx * w + dx * frame * 14 * sp) % (w + 60) - 30
                    y = fy * h
                    screen.fill((220, 232, 240), (round(x), round(y), length, 1))
                else:
                    x = fx * w
                    y = (fy * h + dy * frame * 14 * sp) % (h + 60) - 30
                    screen.fill((220, 232, 240), (round(x), round(y), 1, length))
        # setas na borda de onde o vento vem, apontando para onde ele empurra
        blink = self.state == "blow" or (frame // 8) % 2 == 0
        if blink:
            label = "VENTO! PROTEJAM-SE ATRÁS DAS PAREDES" if self.state == "warn" else "VENTO!"
            ui.text(screen, label, theme.XS, (200, 230, 255), (w // 2, 96))
            arrow = {(1.0, 0.0): "right", (-1.0, 0.0): "left", (0.0, 1.0): "down", (0.0, -1.0): "up"}[self.dir]
            for k in range(-2, 3):
                if dx:
                    pos = (40 if dx > 0 else w - 40, h // 2 + k * 70)
                else:
                    pos = (w // 2 + k * 110, 130 if dy > 0 else h - 60)
                ui.arrow(screen, pos, arrow, 9, (200, 230, 255))


HAZARDS = {"laser": LaserGrid, "vento": Wind}


def make_hazard(key, arena):
    cls = HAZARDS.get(key)
    return cls(arena) if cls else None
