"""A escada entre a Casa e um cômodo de cima ou de baixo (sótão, oficina, porão).

Uns 1,2 segundo: a tela da Casa desliza, os degraus da escada de madeira passam e o letreiro diz
para onde a turma vai (SUBINDO PARA O SÓTÃO, DESCENDO PARA A CASA...). ESQUIVA, pausa ou ESC
pulam. ``then`` monta a cena seguinte; ``up``: a escada sobe (os degraus descem pela tela).
``door=True`` (a oficina, no mesmo andar): no lugar da escada, as duas folhas de uma porta abrindo."""
import pygame

from .. import config, theme
from ..net.remote import hub
from .base import Scene

FRAMES = 72
WOOD, WOOD_D, WOOD_L = (122, 82, 50), (80, 52, 30), (160, 116, 74)


class StairsTripScene(Scene):
    phase = "story"
    music = None

    def __init__(self, game, then, title, up=True, accent=None, door=False):
        super().__init__(game)
        self.door = door
        self.then = then
        self.title = title
        self.up = up
        self.accent = accent or theme.BRASS
        self.done = False
        self.shot = game.screen.copy() if getattr(game, "screen", None) is not None else None

    def enter(self):
        super().enter()
        hub.set_phase("story", mode="campaign", active=self.active_slots(), banner=self.title)

    def _finish(self):
        if not self.done:
            self.done = True
            self.game.change(self.then())

    def handle(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_TAB):
            self._finish()

    def update(self):
        super().update()
        slots = self.active_slots()
        if self.ticks > 10 and any(self.game.inputs[s].pressed(a) for s in slots for a in ("dodge", "pause")):
            self._finish()
            return
        if self.ticks >= FRAMES:
            self._finish()

    def draw(self, screen):
        W, H = config.SCREEN_W, config.SCREEN_H
        screen.fill((8, 6, 6))
        t = min(1.0, self.ticks / FRAMES)
        sign = 1 if self.up else -1
        if self.shot is not None:
            screen.blit(self.shot, (0, round(sign * t * H * 0.8)))
        if self.door:
            self._door(screen, t)
        else:
            self._ladder(screen, t, sign)
        dark = pygame.Surface((W, H), pygame.SRCALPHA)
        dark.fill((6, 4, 4, round(150 * t + (60 if self.ticks > FRAMES - 12 else 0))))
        screen.blit(dark, (0, 0))
        box = pygame.Rect(0, 0, 380, 64)
        box.center = (W // 2, H // 2 - 120)
        self.ui.panel(screen, box, fill=theme.INK_2, accent=self.accent)
        self.ui.text(screen, self.title, theme.S, self.accent, (box.centerx, box.centery - 8))
        self.ui.text(screen, "ESQUIVA: PULAR", theme.XS, theme.MUTED, (box.centerx, box.bottom - 12))

    def _door(self, screen, t):
        """As duas folhas de madeira abrindo para os lados, com a luz do outro cômodo no meio."""
        W, H = config.SCREEN_W, config.SCREEN_H
        frame = pygame.Rect(W // 2 - 170, H // 2 - 70, 340, 300)
        screen.fill((40, 26, 16), frame.inflate(24, 24))
        screen.fill((255, 220, 150), frame)
        open_ = min(1.0, t * 1.6)
        leaf = round(frame.w / 2 * (1 - open_))
        for x in (frame.x, frame.right - leaf):
            if leaf <= 0:
                continue
            screen.fill(WOOD, (x, frame.y, leaf, frame.h))
            for k in range(3):
                pygame.draw.rect(screen, WOOD_D, (x + 6, frame.y + 10 + k * 96, max(1, leaf - 12), 84), 2)

    def _ladder(self, screen, t, sign):
        """A escada de mão: os dois trilhos e os degraus passando."""
        W, H = config.SCREEN_W, config.SCREEN_H
        cx = W // 2
        scroll = round(sign * t * 600)
        for side in (-1, 1):
            x = cx + side * 120 - 9
            screen.fill(WOOD_D, (x, 0, 18, H))
            screen.fill(WOOD_L, (x, 0, 4, H))
        for k in range(-2, H // 50 + 3):
            y = (k * 50 + scroll) % (H + 100) - 50
            screen.fill(WOOD, (cx - 120, y, 240, 14))
            screen.fill(WOOD_L, (cx - 120, y, 240, 3))
            screen.fill(WOOD_D, (cx - 120, y + 11, 240, 3))
