"""Tela de apresentação (VS), a partida em si e o resultado."""
import math

import pygame

from .. import config, theme
from ..arena import MAPS_BY_KEY
from ..data import CHARACTERS
from ..matches import create_match
from ..net.remote import hub
from ..ui import MenuList, darken, mix
from .base import Scene
from .menus import TitleScene, _MenuScene


def _scaled(img, factor):
    return pygame.transform.scale(img, (img.get_width() * factor, img.get_height() * factor))


class VersusScene(Scene):
    phase = "select"
    music = None
    show_cursor = False
    DURATION = 150

    def __init__(self, game):
        super().__init__(game)
        self.session = game.session
        self.match = create_match(game, self.session)
        self.assets.stop_music(800)

    def handle(self, event):
        skip = event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE)
        if skip and self.ticks > 30:
            self._start()

    def update(self):
        super().update()
        if self.ticks == 22:
            self.sfx("confirm", 0.6)
        if self.ticks >= self.DURATION:
            self._start()

    def _start(self):
        self.game.change(PlayScene(self.game, self.match))

    def draw(self, screen):
        W, H = config.SCREEN_W, config.SCREEN_H
        t = self.ticks
        soccer = self.session.soccer
        teams = soccer or self.session.team_mode
        sides = [[s for s in self.session.slots if self.session.team_of(s.slot) == team] for team in (0, 1)] \
            if teams else [[self.session.slots[0]], [self.session.slots[1]]]
        colors = [theme.TEAM_COLORS[0], theme.TEAM_COLORS[1]] if teams else [sides[0][0].color, sides[1][0].color]

        screen.fill(theme.INK)
        tilt = 60
        left = [(0, 0), (W // 2 + tilt, 0), (W // 2 - tilt, H), (0, H)]
        right = [(W // 2 + tilt, 0), (W, 0), (W, H), (W // 2 - tilt, H)]
        pygame.draw.polygon(screen, mix(colors[0], theme.INK, 0.72), left)
        pygame.draw.polygon(screen, mix(colors[1], theme.INK, 0.72), right)
        pygame.draw.line(screen, theme.BONE, (W // 2 + tilt, 0), (W // 2 - tilt, H), 4)

        ease = 1 - (1 - min(1.0, t / 24)) ** 3
        ground = H // 2 + 96
        for side, slots in enumerate(sides):
            direction = 1 if side == 0 else -1
            for k, setup in enumerate(slots):
                stats = CHARACTERS[setup.char]
                sprites = self.assets.kit_sprites(stats.key, side) if soccer else self.assets.sprites[stats.key]
                img = sprites.pose("direita" if side == 0 else "esquerda", "parado", 0)
                factor = 3 if len(slots) == 1 else 2
                img = _scaled(img, factor)
                spread = 0 if len(slots) == 1 else (k * 2 - 1) * 70
                base_x = W // 4 if side == 0 else W * 3 // 4
                x = base_x + spread - direction * int((1 - ease) * W // 2)
                gy = ground + (k * 20 if len(slots) > 1 else 0)
                pygame.draw.ellipse(screen, theme.SHADOW, (x - 40, gy - 8, 80, 16))
                screen.blit(img, img.get_rect(midbottom=(x, gy + 4)))
                if len(slots) == 1:
                    self.ui.text(screen, stats.name.upper(), theme.M, theme.BONE, (base_x, ground + 44))
                    self.ui.text(screen, setup.name, theme.XS, colors[side], (base_x, ground + 70))
                else:
                    self.ui.text(screen, setup.label, theme.XS, setup.color, (x, gy + 24))
            if teams and len(slots) > 1:
                self.ui.text(screen, f"TIME {theme.TEAM_NAMES[side]}", theme.S, theme.BONE,
                             (W // 4 if side == 0 else W * 3 // 4, 80))

        if t > 20:
            pop = 1 + max(0.0, 0.6 - (t - 20) * 0.06)
            size = theme.XL
            vs = self.assets.text("VS", size, theme.BRASS)
            ink = self.assets.text("VS", size, theme.SHADOW)
            if pop > 1:
                vs = pygame.transform.scale(vs, (int(vs.get_width() * pop), int(vs.get_height() * pop)))
                ink = pygame.transform.scale(ink, vs.get_size())
            r = vs.get_rect(center=(W // 2, H // 2 - 30))
            for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 4), (3, 4), (-3, 4)):
                screen.blit(ink, r.move(dx, dy))
            screen.blit(vs, r)

        if self.session.basket:
            place = MAPS_BY_KEY[self.session.map_key].name.upper() if self.session.map_key in MAPS_BY_KEY else "QUADRA"
        else:
            place = "ESTÁDIO" if soccer else MAPS_BY_KEY[self.session.map_key].name.upper()
        self.ui.text(screen, place, theme.XS, theme.MUTED, (W // 2, H - 24))


class PlayScene(Scene):
    phase = "playing"
    music = "battle"
    show_cursor = False

    def __init__(self, game, match):
        super().__init__(game)
        self.match = match
        self.music = getattr(match, "music", "battle")     # acampamento tem a sua música calma
        self.paused = False
        restart = "REINICIAR FASE" if game.session and game.session.campaign else "REINICIAR"
        self.main_menu = MenuList([("CONTINUAR", "resume"), (restart, "restart"), ("SAIR PARA O MENU", "quit")],
                                  topleft=(config.SCREEN_W // 2 - 156, 250), width=312)
        # sair no meio da campanha perde a corrida inteira: pergunta antes
        self.confirm_menu = MenuList([("NÃO, CONTINUAR", "back"), ("SIM, SAIR", "quit_now")],
                                     topleft=(config.SCREEN_W // 2 - 156, 266), width=312)
        self.pause_menu = self.main_menu

    @property
    def confirming(self):
        return self.pause_menu is self.confirm_menu

    def _set_paused(self, value):
        self.paused = value
        pygame.mouse.set_visible(value)       # mouse só aparece no menu de pausa (e no teletransporte)
        self._cursor = value
        self.pause_menu = self.main_menu
        self.pause_menu.index = 0
        hub.set_phase("paused" if value else "playing", active=self.active_slots())
        self.sfx("click", 0.5)
        self.assets.pause_music(value)

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
            self._set_paused(not self.paused)
            return
        if self.paused:
            choice = self.pause_menu.handle(event, self.sfx)
            if choice:
                self._choose(choice)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and hasattr(self.match, "click"):
            self.match.click(event.pos)          # botão TELETRANSPORTE DE FASE

    def _choose(self, choice):
        if choice == "resume":
            self._set_paused(False)
        elif choice == "restart":
            self.assets.pause_music(False)
            self.game.change(self.match.restart_scene() or VersusScene(self.game))
        elif choice == "quit" and self.game.session and self.game.session.campaign:
            self.pause_menu = self.confirm_menu
            self.pause_menu.index = 0
        elif choice == "back":
            self.pause_menu = self.main_menu
            self.pause_menu.index = len(self.main_menu.options) - 1
        elif choice in ("quit", "quit_now"):
            self.assets.pause_music(False)
            self.game.change(TitleScene(self.game))

    def update(self):
        super().update()
        if self.ticks == 1 and self.game.session.soccer:
            self.sfx("apito", 0.35)                       # apito do começo do jogo
        humans = [self.game.inputs[s] for s in self.active_slots()]
        if any(inp.pressed("pause") for inp in humans):
            self._set_paused(not self.paused)
        if self.paused:
            for inp in humans:
                if inp.pressed("up"):
                    self.pause_menu.move(-1)
                if inp.pressed("down"):
                    self.pause_menu.move(1)
                if inp.pressed("attack") or inp.pressed("confirm"):
                    self._choose(self.pause_menu.value)
                    return
            return
        cursor = self.paused or getattr(self.match, "wants_cursor", False)
        if cursor != getattr(self, "_cursor", False):
            self._cursor = cursor
            pygame.mouse.set_visible(cursor)
        self.match.update()
        if self.match.finished:
            self.game.change(self.match.next_scene() or ResultsScene(self.game, self.match.result))

    def draw(self, screen):
        self.match.draw(screen, self.ui)
        W, H = config.SCREEN_W, config.SCREEN_H
        if self.game.session.soccer and self.ticks < 70 and not self.paused:
            word = "VALENDO!"
            alpha_t = self.ticks / 70
            x = W // 2 + int((1 - min(1, self.ticks / 10)) * W)
            if alpha_t < 0.85 or self.ticks % 4 < 2:
                band = pygame.Rect(0, H // 2 - 34, W, 68)
                veil = pygame.Surface(band.size, pygame.SRCALPHA)
                veil.fill((0, 0, 0, 150))
                screen.blit(veil, band)
                self.ui.text(screen, word, theme.XL, theme.BRASS, (x, H // 2))
        if self.paused:
            darken(screen, 170)
            panel = pygame.Rect(0, 0, 360, 200)
            panel.midtop = (W // 2, 180)
            self.ui.panel(screen, panel)
            if self.confirming:
                self.ui.text(screen, "SAIR DA CAMPANHA?", theme.M, theme.BONE, (W // 2, panel.y + 30))
                self.ui.text(screen, "O PROGRESSO DESTA CORRIDA SE PERDE", theme.XS, theme.BLOOD, (W // 2, panel.y + 58))
            else:
                self.ui.text(screen, "PAUSADO", theme.M, theme.BONE, (W // 2, panel.y + 36))
            self.pause_menu.draw(screen, self.ui, self.ticks)


class ResultsScene(_MenuScene):
    phase = "results"

    def __init__(self, game, result):
        super().__init__(game)
        self.result = result
        self.menu = MenuList([("REVANCHE", "rematch"), ("TROCAR PERSONAGENS", "select"), ("MENU PRINCIPAL", "menu")],
                             topleft=(64, 330), width=320)

    def enter(self):
        super().enter()
        hub.set_phase("results", active=self.active_slots(), banner=self.result.title)

    def handle(self, event):
        choice = self.menu.handle(event, self.sfx)
        if choice:
            self._choose(choice)
        elif self.is_back(event):
            self._choose("menu")

    def update(self):
        super().update()
        for s in self.active_slots():
            inp = self.game.inputs[s]
            if inp.pressed("up"):
                self.menu.move(-1)
            if inp.pressed("down"):
                self.menu.move(1)
            if inp.pressed("confirm") or inp.pressed("attack"):
                self._choose(self.menu.value)
                return

    def _choose(self, choice):
        self.sfx("confirm")
        if choice == "rematch":
            self.game.change(VersusScene(self.game))
        elif choice == "select":
            from .select import CharSelectScene
            self.game.change(CharSelectScene(self.game))
        else:
            self.game.change(TitleScene(self.game))

    def draw(self, screen):
        W, H = config.SCREEN_W, config.SCREEN_H
        self.draw_background(screen)
        r = self.result
        self.ui.text(screen, "FIM DE JOGO", theme.XS, theme.MUTED, (64, 64), anchor="midleft")
        self.ui.text(screen, r.title, theme.L, r.color, (64, 100), anchor="midleft")
        screen.fill(r.color, (64, 124, 120, 3))
        if r.score:
            self.ui.text(screen, f"{r.score[0]}  x  {r.score[1]}", theme.M, theme.BONE, (64, 164), anchor="midleft")

        # vencedores
        stage_x = W - 250
        ground = 300
        n = len(r.winners)
        for i, f in enumerate(r.winners):
            img = (f.sprites.frame("frente", self.ticks // 5) if (self.ticks // 60) % 2
                   else f.sprites.pose("frente", "ataque", 1 if (self.ticks // 15) % 2 else 2))
            img = _scaled(img, 3 if n == 1 else 2)
            x = stage_x + (i - (n - 1) / 2) * 120
            bob = int(abs(math.sin(self.ticks * 0.08)) * 6)
            pygame.draw.ellipse(screen, theme.SHADOW, (x - 44, ground - 8, 88, 16))
            screen.blit(img, img.get_rect(midbottom=(x, ground + 4 - bob)))

        panel = pygame.Rect(stage_x - 200, 330, 400, 24 + 22 * len(r.lines))
        self.ui.panel(screen, panel)
        y = panel.y + 22
        for label, value in r.lines:
            self.ui.text(screen, label, theme.XS, theme.MUTED, (panel.x + 18, y), anchor="midleft", shadow=False)
            self.ui.text(screen, value, theme.XS, theme.BONE, (panel.right - 18, y), anchor="midright")
            y += 22
        self.menu.draw(screen, self.ui, self.ticks)
        self.footer(screen, [("↑↓", "ESCOLHER"), ("ENTER", "CONFIRMAR")])
