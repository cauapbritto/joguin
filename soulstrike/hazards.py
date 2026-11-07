"""Perigos de algumas masmorras dos capítulos 2 (Lag Lobby) e 3 (Clínica Clepalovers).
Cada um avisa antes de pegar:

- laser (Corredor de servidores): feixes atravessam o chão de lado a lado. Primeiro aparece a
  linha pontilhada e os emissores piscam; depois o feixe queima quem estiver em cima dele.
- vento (Heliponto): rajadas empurram todo mundo para um lado. As setas aparecem antes, e quem
  está atrás de uma parede (do lado de onde o vento vem) fica protegido.
"""
import math
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

    def __init__(self, axis, pos, length, delay=0, start=0):
        self.axis = axis
        self.pos = pos
        self.start = start            # o feixe vai de ``start`` a ``start + length`` (a parede da sala)
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
        along = f.x if self.axis == "h" else f.y
        return d < self.HALF + f.radius * 0.5 and self.start <= along <= self.start + self.length

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
        end = self.start + self.length
        if self.axis == "h":
            y = round(self.pos - cam.y)
            if not -20 < y < h + 20:
                return
            x0, x1 = max(0, round(self.start - cam.x)), min(w, round(end - cam.x))
            a, b = (x0, y), (x1, y)
            emitters = ((round(self.start - cam.x) + 6, y), (round(end - cam.x) - 6, y))
        else:
            x = round(self.pos - cam.x)
            if not -20 < x < w + 20:
                return
            y0, y1 = max(0, round(self.start - cam.y)), min(h, round(end - cam.y))
            a, b = (x, y0), (x, y1)
            emitters = ((x, round(self.start - cam.y) + 6), (x, round(end - cam.y) - 6))
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
                for x in range(a[0] - ((frame * 2) % (dash + gap)), b[0], dash + gap):
                    view.fill(color, (max(a[0], x), a[1] - 1, dash, 2))
            else:
                for y in range(a[1] - ((frame * 2) % (dash + gap)), b[1], dash + gap):
                    view.fill(color, (a[0] - 1, max(a[1], y), 2, dash))
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
        arena, room = self.arena, self.arena.room
        for _ in range(20):
            if axis == "h":
                pos = self.rng.uniform(room.y + 120, room.bottom - 120)
                xs = range(room.x + 40, room.right, 80)
                free = sum(arena.is_free(x, pos, 4) for x in xs)
                total = len(xs)
            else:
                pos = self.rng.uniform(room.x + 120, room.right - 120)
                ys = range(room.y + 40, room.bottom, 80)
                free = sum(arena.is_free(pos, y, 4) for y in ys)
                total = len(ys)
            if free >= total * 0.6:
                return pos
        return room.centery if axis == "h" else room.centerx

    def update(self, match):
        self.timer -= 1
        if self.timer <= 0:
            self.timer = self.rng.randint(*self.GAP)
            count = 2 if self.rng.random() < 0.35 else 1
            for k in range(count):
                axis = "v" if self.rng.random() < 0.55 else "h"
                room = self.arena.room
                length, start = (room.w, room.x) if axis == "h" else (room.h, room.y)
                self.beams.append(Beam(axis, self._free_line(axis), length, delay=k * 20, start=start))
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


# ─────────────────────────────────────────────
#  Clínica Clepalovers (capítulo 3)
# ─────────────────────────────────────────────
CLEPA = (255, 110, 190)
CLEPA_DARK = (120, 30, 80)
CAUTION = (250, 206, 50)


class WetFloor:
    """Sala de Espera: poças de piso molhado (com a plaquinha amarela). Quem anda em cima
    escorrega: o passo continua um pouco depois de soltar. E o painel de senhas chamando lá em
    cima (SENHA 042 · SALA 3), que é de onde os monstros "são chamados"."""

    COUNT = 5
    SLIDE = 0.8                  # quanto do passo anterior continua em cima da poça
    CALL = (260, 360)

    def __init__(self, arena, rng=random):
        self.arena = arena
        self.rng = rng
        self.puddles = []
        for _ in range(60):
            if len(self.puddles) >= self.COUNT:
                break
            x, y = arena.random_free_spot(60)
            if all(abs(x - px) > 220 or abs(y - py) > 160 for px, py, _ in self.puddles):
                self.puddles.append((x, y, rng.randint(70, 100)))
        self.last = {}
        self.ticket = rng.randint(30, 60)
        self.room = rng.randint(1, 6)
        self.call = 90
        self.flash = 0

    def on_puddle(self, f):
        return any(((f.x - x) / r) ** 2 + ((f.y - y) / (r * 0.45)) ** 2 < 1 for x, y, r in self.puddles)

    def update(self, match):
        seen = {}
        for f in match.fighters:
            if not f.alive_in_match or f.lift > 0:
                continue
            prev = self.last.get(f)
            seen[f] = (f.x, f.y)
            if prev is None or getattr(f, "knock_resist", 0.0) >= 1 or not self.on_puddle(f):
                continue
            dx, dy = f.x - prev[0], f.y - prev[1]
            if 0.3 < abs(dx) + abs(dy) < 12:
                f.x += dx * self.SLIDE
                f.y += dy * self.SLIDE
                self.arena.resolve(f)
                seen[f] = (f.x, f.y)
                if match.frame % 9 == 0:
                    match.burst(f.x, f.y + 14, (170, 210, 240), 2, speed=1.2)
        self.last = seen
        self.call -= 1
        self.flash = max(0, self.flash - 1)
        if self.call <= 0:
            self.call = self.rng.randint(*self.CALL)
            self.ticket += 1
            self.room = self.rng.randint(1, 6)
            self.flash = 60
            match.assets.play("senha", 0.35)

    def draw(self, view, cam, frame):
        for x, y, r in self.puddles:
            sx, sy = round(x - cam.x), round(y - cam.y)
            rect = pygame.Rect(0, 0, r * 2, round(r * 0.9))
            rect.center = (sx, sy)
            layer = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.ellipse(layer, (150, 200, 236, 90), layer.get_rect())
            pygame.draw.ellipse(layer, (220, 240, 255, 140), layer.get_rect(), 2)
            shine = (frame // 3 + x) % (r * 2)
            pygame.draw.line(layer, (255, 255, 255, 120), (shine - 8, rect.h // 3), (shine + 6, rect.h // 3 - 3), 2)
            view.blit(layer, rect)
            # plaquinha amarela de CUIDADO
            px, py = rect.right - 10, rect.top - 6
            pygame.draw.polygon(view, (60, 50, 20), [(px - 9, py + 14), (px + 9, py + 14), (px, py - 14)])
            pygame.draw.polygon(view, CAUTION, [(px - 7, py + 12), (px + 7, py + 12), (px, py - 11)])
            view.fill((60, 50, 20), (px - 1, py - 4, 2, 9))
            view.fill((60, 50, 20), (px - 1, py + 7, 2, 2))

    def draw_screen(self, screen, ui, frame):
        w = screen.get_width()
        box = pygame.Rect(0, 0, 300, 44)
        box.midtop = (w // 2, 60)
        lit = self.flash > 0 and (frame // 6) % 2 == 0
        pygame.draw.rect(screen, (24, 14, 22), box, border_radius=6)
        pygame.draw.rect(screen, CLEPA if lit else CLEPA_DARK, box, 2, border_radius=6)
        color = (255, 236, 120) if lit else (255, 170, 210)
        ui.text(screen, f"SENHA {self.ticket:03d} · SALA {self.room}", theme.S, color, box.center)


class LaserTiles:
    """Sala do Laser: o chão é uma grade de ladrilhos. Alguns acendem com o contorno rosa
    piscando (aviso) e depois queimam quem ficou em cima. Sempre sobra chão livre do lado."""

    CELL = 160
    WARN = 66
    BURN = 22
    GAP = (120, 170)
    DAMAGE = 11
    SHARE = 0.32

    def __init__(self, arena, rng=random):
        self.arena = arena
        self.rng = rng
        self.ox, self.oy = arena.room.topleft          # ladrilhos contados do canto da sala
        cols, rows = arena.room.w // self.CELL, arena.room.h // self.CELL
        self.cells = [(c, r) for c in range(cols) for r in range(rows)
                      if arena.is_free(self.ox + c * self.CELL + self.CELL / 2, self.oy + r * self.CELL + self.CELL / 2, 20)]
        self.lit = []                # ladrilhos da vez
        self.age = 0
        self.timer = 120
        self.hit = set()

    @property
    def burning(self):
        return bool(self.lit) and self.WARN <= self.age < self.WARN + self.BURN

    def cell_of(self, f):
        return int((f.x - self.ox) // self.CELL), int((f.y - self.oy) // self.CELL)

    def update(self, match):
        if self.lit:
            self.age += 1
            if self.age == self.WARN:
                match.assets.play("laser", 0.3)
            if self.burning:
                lit = set(self.lit)
                for f in match.fighters:
                    if f in self.hit or not f.alive_in_match or f.lift > 0 or self.cell_of(f) not in lit:
                        continue
                    self.hit.add(f)
                    if f.take_damage(round(self.DAMAGE * match.enemy_dmg), f.x, f.y, match=match):
                        match.burst(f.x, f.y - 10, CLEPA, 6, speed=3)
            if self.age >= self.WARN + self.BURN:
                self.lit = []
            return
        self.timer -= 1
        if self.timer <= 0 and self.cells:
            self.timer = self.rng.randint(*self.GAP)
            # tabuleiro: só uma das "cores" do xadrez, mais umas sorteadas (nunca a sala inteira)
            parity = self.rng.randint(0, 1)
            pool = [c for c in self.cells if (c[0] + c[1]) % 2 == parity]
            self.lit = self.rng.sample(pool, max(1, round(len(self.cells) * self.SHARE)) if len(pool) > 2 else len(pool))
            self.age = 0
            self.hit = set()

    def draw(self, view, cam, frame):
        if not self.lit:
            return
        for c, r in self.lit:
            rect = pygame.Rect(round(self.ox + c * self.CELL - cam.x) + 4, round(self.oy + r * self.CELL - cam.y) + 4,
                               self.CELL - 8, self.CELL - 8)
            if self.burning:
                t = (self.age - self.WARN) / self.BURN
                layer = pygame.Surface(rect.size, pygame.SRCALPHA)
                layer.fill((*CLEPA, round(170 * (1 - 0.5 * t))))
                view.blit(layer, rect)
                pygame.draw.rect(view, (255, 230, 244), rect, 3)
                for k in range(0, rect.w, 22):
                    view.fill((255, 240, 250), (rect.x + k, rect.y + (frame * 5 + k) % rect.h, 2, 6))
            else:
                t = self.age / self.WARN
                on = (frame // 4) % 2 == 0 or t > 0.75
                layer = pygame.Surface(rect.size, pygame.SRCALPHA)
                layer.fill((*CLEPA, round(20 + 50 * t)))
                view.blit(layer, rect)
                pygame.draw.rect(view, CLEPA if on else CLEPA_DARK, rect, 2)

    def draw_screen(self, screen, ui, frame):
        if self.lit and not self.burning and (frame // 8) % 2 == 0:
            ui.text(screen, "LASER! SAIAM DOS LADRILHOS ROSA", theme.XS, CLEPA, (screen.get_width() // 2, 96))


class Valve:
    """Registro do vapor (Spa): ATACAR perto fecha."""

    RADIUS = 70

    def __init__(self, x, y):
        self.x, self.y = x, y
        self.closed = False
        self.turn = 0

    def near(self, f):
        return abs(f.x - self.x) < self.RADIUS and abs(f.y - self.y) < self.RADIUS


class Steam:
    """Spa e Sauna: o vapor tapa a sala; só dá para ver em volta de cada herói. Três registros
    nas paredes: ATACAR perto de um fecha (o vapor afina); os três fechados, o vapor some."""

    SIGHT = 190
    SPOTS = ((150, 160), (1850, 160), (1000, 1260))

    def __init__(self, arena, rng=random):
        self.arena = arena
        self.valves = [Valve(*arena.free_spot(*arena.at(x, y), 24)) for x, y in self.SPOTS]
        self.density = 1.0
        self.match = None
        self._veil = None

    @property
    def open_valves(self):
        return [v for v in self.valves if not v.closed]

    def interact(self, f, match):
        for v in self.open_valves:
            if v.near(f):
                v.closed = True
                v.turn = 30
                match.burst(v.x, v.y - 20, (240, 240, 246), 16, speed=3)
                left = len(self.open_valves)
                text = "VAPOR DESLIGADO!" if left == 0 else f"REGISTRO FECHADO ({3 - left}/3)"
                match.popup(v.x, v.y - 60, text, (220, 240, 255))
                match.assets.play("vapor", 0.5)
                return True
        return False

    def update(self, match):
        self.match = match
        want = len(self.open_valves) / len(self.valves)
        self.density += (want - self.density) * 0.03
        for v in self.valves:
            v.turn = max(0, v.turn - 1)
            if not v.closed and match.frame % 7 == 0:
                match.burst(v.x, v.y - 26, (236, 236, 242), 1, speed=1.2)

    def draw(self, view, cam, frame):
        for v in self.valves:
            sx, sy = round(v.x - cam.x), round(v.y - cam.y)
            view.fill((70, 74, 86), (sx - 4, sy - 34, 8, 34))
            color = (90, 200, 120) if v.closed else (220, 60, 70)
            spin = v.turn * 0.4 + (0 if v.closed else frame * 0.02)
            for k in range(4):
                a = spin + k * math.pi / 2
                pygame.draw.line(view, color, (sx, sy - 34), (sx + round(math.cos(a) * 13), sy - 34 + round(math.sin(a) * 13)), 3)
            pygame.draw.circle(view, (40, 40, 48), (sx, sy - 34), 4)

    def draw_screen(self, screen, ui, frame):
        match = self.match
        if self.density < 0.03 or match is None:
            return
        w, h = screen.get_size()
        if self._veil is None or self._veil.get_size() != (w, h):
            self._veil = pygame.Surface((w, h), pygame.SRCALPHA)
        veil = self._veil
        veil.fill((232, 234, 240, round(215 * self.density)))
        cam = match.camera
        sight = round(self.SIGHT * cam.zoom) if hasattr(cam, "zoom") else self.SIGHT
        steps = 10                                    # a borda da visão vai clareando aos poucos
        for k in range(steps + 1):
            t = k / steps
            r = max(10, round(sight + 60 - 120 * t))
            alpha = round(215 * self.density * (1 - t) ** 1.6)
            for p in match.alive_players:
                sx, sy = cam.to_screen(p.x, p.y - 10)
                pygame.draw.circle(veil, (232, 234, 240, alpha), (round(sx), round(sy)), r)
        for rect in getattr(match, "hud_regions", lambda: [])():
            veil.fill((232, 234, 240, round(50 * self.density)), rect)   # placar e vidas sempre à vista
        screen.blit(veil, (0, 0))
        for v in self.open_valves:                    # os registros abertos aparecem através do vapor
            sx, sy = cam.to_screen(v.x, v.y - 60)
            if (frame // 10) % 2 == 0:
                ui.text(screen, "REGISTRO", theme.XS, (220, 60, 70), (round(sx), round(sy)))
        if self.open_valves and (frame // 30) % 4 == 0:
            ui.text(screen, "FECHEM OS REGISTROS DO VAPOR (ATACAR PERTO)", theme.XS, (90, 110, 140), (w // 2, 96))


HAZARDS = {"laser": LaserGrid, "vento": Wind, "piso_molhado": WetFloor, "laser_grade": LaserTiles,
           "vapor": Steam}


def _register():
    from .mansao import HAZARDS as MANSAO        # capítulo 4: Mansão do Carimbo
    HAZARDS.update(MANSAO)


_register()


def make_hazard(key, arena):
    cls = HAZARDS.get(key)
    return cls(arena) if cls else None
