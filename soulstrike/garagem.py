"""A garagem da Casa, lá embaixo: o hall dos carros e o salão dos corrompidos.

Do quintal, ATACAR na porta da garagem leva o grupo inteiro para baixo (a cena da descida, em
``scenes/garagem.py``). Em cima ficam as três vagas (City, Uno e moto): andar até um carro e
apertar ATACAR escolhe com o que a turma sai; carro ainda trancado fica coberto com a lona. A
estante da parede abre a lista da garagem (os carros, os troféus e o melhor tempo). Descendo a
escada do meio, o salão dos corrompidos: os liberados em pedestais (falam no ATACAR, como os da
vitrine) e os que faltam com um "?". A rampa do canto de cima leva de volta ao quintal.
"""
import math

import pygame

from . import casa_art as art
from . import config, janelas, progress, theme
from .arena import MAPS_BY_KEY
from .campaign import CoopMatch, _spread
from .casa import (CORROMPIDOS, MINI_TOP, MINI_W, VEHICLES, Decor, GarageMenu, Speaker, _bake, _near_rect, vehicle_ready)
from .matches import Result

GARAGE_MAP = "garagem_casa"
T = 40
TOP = 3 * T                         # as linhas de folga do mapa em texto (lobbies.HEADROOM)
RAMP = pygame.Rect(T, TOP + T, 3 * T, 3 * T)          # a rampa de volta ao quintal
CAR_Y = TOP + 6 * T                 # chão do meio dos carros
BAYS = {"city": 330, "uno": 600, "moto": 860}         # meio de cada vaga (x)
BAY_W, BAY_H = 230, 170
SHELF = (1080, TOP + 4 * T)         # estante dos troféus (pé no chão, meio)
STAIRS = pygame.Rect(12 * T, TOP + 9 * T, 6 * T, T)   # o vão do muro do meio: a escada
HALL_Y = TOP + 14 * T               # pé dos pedestais do salão de baixo
PEDESTALS = (200, 460, 740, 1000)
REACH = 70


def bay_rect(key):
    x = BAYS[key]
    return pygame.Rect(x - BAY_W // 2, CAR_Y - BAY_H + 30, BAY_W, BAY_H)


def car_rect(key):
    """Onde o carro ocupa o chão (ninguém passa por dentro)."""
    half = {"city": 86, "uno": 72, "moto": 56}[key]
    return pygame.Rect(BAYS[key] - half, CAR_Y - 24, 2 * half, 26)


def _car_art(key):
    return {"city": art.city_car, "uno": art.uno_car, "moto": art.moto}[key]


def _tarp(baked):
    """O carro ainda trancado: coberto com a lona cinza (só o contorno aparece)."""
    img = baked.image.copy()
    veil = pygame.Surface(img.get_size(), pygame.SRCALPHA)
    veil.fill((96, 100, 108, 255))
    mask = pygame.mask.from_surface(img).to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    veil.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    img.blit(veil, (0, 0))
    for y in range(4, img.get_height() - 2, 9):       # as dobras da lona
        line = pygame.Surface((img.get_width(), 2), pygame.SRCALPHA)
        line.fill((70, 74, 80, 255))
        line.blit(mask.subsurface((0, y, img.get_width(), 2)), (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        img.blit(line, (0, y))
    return art.Baked(img, baked.dx, baked.dy)


def draw_ramp(s, rect):
    """A rampa de concreto subindo para o quintal (faixas amarelas e pretas na borda)."""
    s.fill((70, 72, 78), rect)
    for i in range(rect.h // 10):
        c = 84 + i * 4
        s.fill((c, c, c + 6), (rect.x, rect.y + i * 10, rect.w, 8))
    for i in range(0, rect.w, 20):
        s.fill((220, 190, 60) if (i // 20) % 2 else (30, 30, 34), (rect.x + i, rect.bottom - 6, 20, 6))


def draw_stairs(s, rect):
    """Os degraus no vão do muro do meio (descem para o salão)."""
    for i in range(4):
        c = 120 - i * 18
        s.fill((c, c, c + 8), (rect.x, rect.y + i * 10, rect.w, 9))
        s.fill((c + 30, c + 30, c + 36), (rect.x, rect.y + i * 10, rect.w, 2))


def draw_bay(s, x, y, w, h, label):
    """A vaga pintada no chão (faixa amarela dos lados e no fundo)."""
    fn = getattr(art, "parking_bay", None)
    if fn is not None:
        fn(s, x, y, w, h, label)
        return
    s.fill((220, 196, 80), (x, y, 4, h))
    s.fill((220, 196, 80), (x + w - 4, y, 4, h))
    s.fill((220, 196, 80), (x, y, w, 4))


class GarageMatch(janelas.Janelas, CoopMatch):
    """A garagem lá embaixo. ``story`` e ``walk`` só passam adiante para a Casa na volta."""

    lobby = True
    music = "camp"
    walk = False

    def __init__(self, game, run, story=False, walk=False):
        self.story = story
        self.walk = walk
        cfg = MAPS_BY_KEY[GARAGE_MAP]
        starts = _spread(cfg.markers["S"], len(run.session.slots))
        super().__init__(game, run, cfg.key, starts, (1.0, 0.0))
        art.use(self.assets)
        self.arena.floor = self.arena.floor.copy()
        self.speakers = []
        self.cars = {}
        self.going_up = False
        self.ramp = RAMP
        self._furnish()

    # ── montagem ─────────────────────────────
    def _put(self, fn, x, y, *args, flat=False, foot=(), **kw):
        from .entities import Wall
        d = Decor(x, y, _bake(fn, *args, **kw), flat=flat)
        self.props.append(d)
        for fx, fy, fw, fh in foot:
            self.arena.walls.append(Wall(x + fx, y + fy, fw, fh, visible=False))
        return d

    def _furnish(self):
        from .entities import Wall
        floor = self.arena.floor
        draw_ramp(floor, RAMP)
        draw_stairs(floor, STAIRS)
        for key, name, _ in VEHICLES:
            r = bay_rect(key)
            draw_bay(floor, r.x, r.y, r.w, r.h, name)
        sign = getattr(art, "neon_sign", None)
        if sign is not None:
            self._put(sign, 600, TOP + 30, flat=True)
        else:
            self._put(art.poster, 520, TOP + 6, 160, 26, (150, 40, 40), "GARAGEM DA TURMA", flat=True)
        board = getattr(art, "tool_board", None)
        if board is not None:
            self._put(board, 200, TOP + 36, flat=True)
        shelf = getattr(art, "trophy_shelf", None)
        if shelf is not None:
            self._put(shelf, *SHELF, len(progress.seals()), foot=((-46, -16, 92, 16),))
        else:
            self._put(art.shelf, SHELF[0] - 35, SHELF[1] - 70, 70, foot=((0, 50, 70, 20),))
        for fn_name, x, y in (("tool_cart", 1100, TOP + 7 * T), ("tire_stack", 60, TOP + 8 * T + 20),
                              ("oil_drum", 1130, TOP + 8 * T + 10)):
            fn = getattr(art, fn_name, None)
            if fn is not None:
                self._put(fn, x, y, foot=((-18, -12, 36, 14),))
        for key, _, _ in VEHICLES:
            baked = _bake(_car_art(key))
            if not vehicle_ready(key):
                baked = _tarp(baked)
            d = Decor(BAYS[key], CAR_Y, baked)
            self.props.append(d)
            self.cars[key] = d
            r = car_rect(key)
            self.arena.walls.append(Wall(r.x, r.y, r.w, r.h, visible=False))
        # o salão de baixo: os corrompidos liberados nos pedestais, os outros com "?"
        self.pedestals = []
        for (key, chapter, _, _), x in zip(CORROMPIDOS, PEDESTALS):
            freed = progress.chapter_cleared(chapter)
            if freed:
                self._put(art.mannequin, x, HALL_Y, key, foot=((-20, -10, 40, 14),))
                self.speakers.append(Speaker(key, x, HALL_Y))
            else:
                self._put(_empty_pedestal, x, HALL_Y, foot=((-20, -10, 40, 14),))
            self.pedestals.append((key, chapter, x, freed))

    # ── consultas ────────────────────────────
    hud_title = "GARAGEM DA TURMA"

    @property
    def objective_text(self):
        return "GARAGEM · ATACAR NUM CARRO PARA ESCOLHER · A RAMPA VOLTA AO QUINTAL"

    def objective(self):
        return None

    def car_near(self, f):
        """O carro ao alcance de ``f`` (ou None)."""
        for key, _, _ in VEHICLES:
            if _near_rect(f, car_rect(key), REACH):
                return key
        return None

    def ramp_near(self, f):
        return f.alive_in_match and self.ramp.inflate(30, 30).collidepoint(f.x, f.y)

    def shelf_near(self, f):
        x, y = SHELF
        return _near_rect(f, pygame.Rect(x - 50, y - 90, 100, 90))

    def speaker_near(self, f):
        if not f.alive_in_match or self.car_near(f) or self.shelf_near(f) or self.ramp_near(f):
            return None
        near = [s for s in self.speakers if s.near(f)]
        return min(near, key=lambda s: math.hypot(f.x - s.x, f.y - s.y)) if near else None

    def choose_vehicle(self, key):
        if self.run.vehicle == key:
            return
        self.run.vehicle = key
        name = next(n for k, n, _ in VEHICLES if k == key)
        self.popup(BAYS[key], CAR_Y - 110, f"VAMOS DE {name}", theme.BRASS)
        self.assets.play("confirm", 0.45)

    # ── ciclo ────────────────────────────────
    def update_stage(self):
        if self.frame == 1:
            self._set_banner("GARAGEM DA TURMA", "CITY, UNO, MOTO E OS CORROMPIDOS LÁ EMBAIXO", theme.BRASS)
        if self.banner and self.banner[3] > 130:
            self.banner = None
        waiting = {self.speaker_near(p) for p in self.alive_players if p not in self.menus}
        for s in self.speakers:
            s.update(self)
            s.waiting = s in waiting
        self.update_windows()
        if self.leaving:
            return

    def interact(self, f):
        if self.ramp_near(f):
            if self.leaving_in:
                return True
            self.going_up = True
            self.assets.play("select", 0.45)
            self.leave_soon(self.leave)
            return True
        key = self.car_near(f)
        if key is not None:
            if vehicle_ready(key):
                self.choose_vehicle(key)
            else:
                chapter = next(c for k, _, c in VEHICLES if k == key)
                self.popup(BAYS[key], CAR_Y - 110, f"ZERE O CAPÍTULO {chapter}", (170, 170, 180))
                self.assets.play("cancel", 0.3)
            return True
        if self.shelf_near(f):
            self.menus[f] = GarageMenu(self, f)
            self.assets.play("select", 0.45)
            return True
        speaker = self.speaker_near(f)
        if speaker is not None:
            speaker.say(self)
            return True
        return self.pick_ground(f)

    def _finish(self, won):
        self.won = won
        self.result = Result("GARAGEM DA TURMA", theme.MOSS, self.players)
        self.finished = True

    def next_scene(self):
        from .scenes.garagem import GarageTripScene
        from .scenes.campaign import hub_scene
        return GarageTripScene(self.game, lambda: hub_scene(self.game, self.run, story=self.story, walk=self.walk,
                                                            arrive="garagem"), down=False)

    def restart_scene(self):
        from .scenes.campaign import garage_scene
        return garage_scene(self.game, self.run, story=self.story, walk=self.walk)

    # ── desenho ──────────────────────────────
    def draw_screen_layer(self, screen, ui):
        cam = self.camera
        for s in self.speakers:
            s.draw(screen, cam, ui, self.assets, self.frame)
        free = [p for p in self.alive_players if p not in self.menus]
        blink = theme.BRASS if (self.frame // 15) % 2 else theme.BONE
        chosen = self.run.vehicle
        for key, name, chapter in VEHICLES:
            sx, sy = cam.to_screen(BAYS[key], CAR_Y + 26)
            label = name if vehicle_ready(key) else f"{name} · ZERE O CAPÍTULO {chapter}"
            color = theme.BRASS if key == chosen else theme.BONE if vehicle_ready(key) else theme.FAINT
            ui.text(screen, ("ESCOLHIDO: " if key == chosen else "") + label, theme.XS, color, (round(sx), round(sy)))
            if key != chosen and vehicle_ready(key) and any(self.car_near(p) == key for p in free):
                tx, ty = cam.to_screen(BAYS[key], CAR_Y - 100)
                ui.text(screen, f"ATACAR: IR DE {name.split()[0]}", theme.XS, blink, (round(tx), round(ty)))
        if any(self.ramp_near(p) for p in free):
            sx, sy = cam.to_screen(self.ramp.centerx, self.ramp.y - 10)
            ui.text(screen, "ATACAR: SUBIR PARA O QUINTAL", theme.XS, blink, (round(sx), round(sy)))
        else:
            sx, sy = cam.to_screen(self.ramp.centerx, self.ramp.bottom + 12)
            ui.text(screen, "RAMPA · QUINTAL", theme.XS, theme.MUTED, (round(sx), round(sy)))
        if any(self.shelf_near(p) for p in free):
            sx, sy = cam.to_screen(SHELF[0], SHELF[1] - 110)
            ui.text(screen, "ATACAR: VER OS TROFÉUS", theme.XS, blink, (round(sx), round(sy)))
        sx, sy = cam.to_screen(STAIRS.centerx, STAIRS.bottom + 20)
        ui.text(screen, "SALÃO DOS CORROMPIDOS", theme.XS, (190, 140, 240), (round(sx), round(sy)))
        for key, chapter, x, freed in self.pedestals:
            if not freed:
                px, py = cam.to_screen(x, HALL_Y - 40)
                ui.text(screen, "?", theme.M, (150, 100, 200), (round(px), round(py)))
                qx, qy = cam.to_screen(x, HALL_Y + 22)
                ui.text(screen, f"ZERE O CAPÍTULO {chapter}", theme.XS, theme.FAINT, (round(qx), round(qy)))
        self.draw_ground(screen, cam, ui)
        janelas.draw(self, screen, ui)


    # ── minimapa ─────────────────────────────
    def minimap_rect(self):
        w, h = self.arena.size
        k = MINI_W / w
        return pygame.Rect(config.SCREEN_W - 12 - MINI_W, MINI_TOP, MINI_W, round((HALL_Y + T - TOP) * k) + 4)

    def draw_hud(self, screen, ui):
        super().draw_hud(screen, ui)
        draw_minimap(screen, ui, self, self.minimap_rect())

    def hud_regions(self):
        return super().hud_regions() + [self.minimap_rect().inflate(4, 4)]


def draw_minimap(screen, ui, match, rect):
    """O mapinha da garagem: o hall dos carros em cima, o salão embaixo, a rampa, a escada,
    as vagas (cinza se trancada), os pedestais (roxo se o corrompido já está lá) e os jogadores."""
    w, _ = match.arena.size
    k = (rect.w - 4) / w
    bg = pygame.Surface(rect.size, pygame.SRCALPHA)
    bg.fill((8, 8, 14, 175))
    screen.blit(bg, rect.topleft)
    pygame.draw.rect(screen, (90, 90, 110), rect, 1)

    def at(x, y):
        return round(rect.x + 2 + x * k), round(rect.y + 2 + (y - TOP) * k)

    def box(r):
        x, y = at(r.x, r.y)
        return pygame.Rect(x, y, max(1, round(r.w * k)), max(1, round(r.h * k)))

    hall = box(pygame.Rect(T, TOP + T, w - 2 * T, 8 * T))
    salao = box(pygame.Rect(T, TOP + 10 * T, w - 2 * T, 5 * T))
    screen.fill((52, 54, 62), hall)
    screen.fill((44, 36, 58), salao)
    pygame.draw.rect(screen, (110, 112, 124), hall, 1)
    pygame.draw.rect(screen, (120, 90, 150), salao, 1)
    screen.fill((200, 170, 60), box(RAMP))
    screen.fill((130, 130, 140), box(STAIRS.inflate(0, 2 * T)))
    for key, _, _ in VEHICLES:
        color = (230, 190, 90) if key == match.run.vehicle else (170, 170, 180) if vehicle_ready(key) else (80, 80, 90)
        screen.fill(color, box(car_rect(key)))
    pygame.draw.circle(screen, (200, 150, 80), at(*SHELF), 2)
    for _, _, x, freed in match.pedestals:
        pygame.draw.circle(screen, (180, 110, 240) if freed else (80, 70, 96), at(x, HALL_Y), 3)
    ui.text(screen, "GARAGEM", theme.XS, (190, 190, 200), (hall.centerx, hall.y + 8), shadow=False)
    ui.text(screen, "SALÃO", theme.XS, (190, 150, 230), (salao.centerx, salao.bottom - 8), shadow=False)
    for p in match.players:
        if not p.alive_in_match:
            continue
        x, y = at(p.x, p.y)
        pygame.draw.circle(screen, (250, 250, 250), (x, y), 5)
        pygame.draw.circle(screen, p.color, (x, y), 4)


def _empty_pedestal(s, x, y):
    """Pedestal vazio do salão (o corrompido ainda não foi liberado): base e um pano roxo."""
    art.shadow(s, x, y + 2, 46)
    art.box(s, (60, 54, 70), x - 22, y - 8, 44, 10)
    art.box(s, (90, 82, 104), x - 22, y - 8, 44, 3)
    art.box(s, (70, 40, 100), x - 16, y - 40, 32, 32)
    art.box(s, (96, 60, 130), x - 16, y - 40, 32, 4)


__all__ = ("GarageMatch", "GARAGE_MAP", "car_rect", "bay_rect")
