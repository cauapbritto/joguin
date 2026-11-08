"""A descida para a garagem da Casa (e a subida de volta ao quintal).

Descendo (uns 2 segundos): o portão de enrolar sobe, a tela escurece e os degraus da rampa passam
por baixo, com DESCENDO PARA A GARAGEM. Subindo, o contrário, mais curto. ESQUIVA, pausa ou ESC
pulam. ``then`` monta a cena seguinte."""
import pygame

from .. import config, theme
from ..net.remote import hub
from .base import Scene

DOWN_FRAMES = 110
UP_FRAMES = 60
SHUTTER = 40                 # quadros do portão subindo


class GarageTripScene(Scene):
    phase = "story"
    music = None

    def __init__(self, game, then, down=True):
        super().__init__(game)
        self.then = then
        self.down = down
        self.done = False
        self.length = DOWN_FRAMES if down else UP_FRAMES
        shot = game.screen.copy() if getattr(game, "screen", None) is not None else None
        self.shot = shot

    def enter(self):
        super().enter()
        hub.set_phase("story", mode="campaign", active=self.active_slots(),
                      banner="DESCENDO PARA A GARAGEM" if self.down else "SUBINDO PARA O QUINTAL")

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
        if self.ticks >= self.length:
            self._finish()

    # ── desenho ──────────────────────────────
    def draw(self, screen):
        W, H = config.SCREEN_W, config.SCREEN_H
        screen.fill((6, 6, 10))
        t = self.ticks
        if self.down:
            lift = min(1.0, t / SHUTTER)
            slide = max(0.0, (t - SHUTTER) / (DOWN_FRAMES - SHUTTER))
        else:
            lift, slide = 1.0, 1.0 - t / UP_FRAMES
        if self.shot is not None:
            screen.blit(self.shot, (0, -round(slide * H * 0.8)))
        if self.down and t < SHUTTER + 10:
            self._shutter(screen, lift)
        self._ramp(screen, slide)
        dark = pygame.Surface((W, H), pygame.SRCALPHA)
        fade = slide if self.down else 1 - slide
        dark.fill((4, 4, 10, round(200 * min(1.0, fade + (0.3 if t > self.length - 12 else 0)))))
        screen.blit(dark, (0, 0))
        title = "DESCENDO PARA A GARAGEM" if self.down else "SUBINDO PARA O QUINTAL"
        box = pygame.Rect(0, 0, 380, 64)
        box.center = (W // 2, H // 2 - 120)
        self.ui.panel(screen, box, fill=theme.INK_2, accent=theme.BRASS)
        self.ui.text(screen, title, theme.S, theme.BRASS, (box.centerx, box.centery - 8))
        self.ui.text(screen, "ESQUIVA: PULAR", theme.XS, theme.MUTED, (box.centerx, box.bottom - 12))

    def _shutter(self, screen, lift):
        """O portão de enrolar da garagem subindo no meio da tela."""
        W, H = config.SCREEN_W, config.SCREEN_H
        door = pygame.Rect(W // 2 - 180, H // 2 - 60, 360, 220)
        shown = round(door.h * (1 - lift))
        if shown <= 0:
            return
        part = pygame.Rect(door.x, door.y, door.w, shown)
        screen.fill((150, 150, 158), part)
        for y in range(part.y, part.bottom, 12):
            screen.fill((118, 118, 128), (part.x, y, part.w, 3))
        screen.fill((90, 90, 98), (part.x, part.bottom - 8, part.w, 8))
        pygame.draw.rect(screen, (60, 60, 68), door, 4)

    def _ramp(self, screen, slide):
        """Os degraus da rampa subindo pela tela enquanto a câmera desce."""
        W, H = config.SCREEN_W, config.SCREEN_H
        base = H - round(slide * H * 0.9)
        for i in range(14):
            y = base + i * 30
            if y > H or y < -30:
                continue
            w = 220 + i * 26
            c = 60 + min(60, i * 5)
            screen.fill((c, c, c + 8), (W // 2 - w // 2, y, w, 24))
            screen.fill((c + 34, c + 34, c + 40), (W // 2 - w // 2, y, w, 3))
            if i % 2 == 0:
                screen.fill((220, 190, 60), (W // 2 - w // 2, y + 20, 18, 4))
                screen.fill((220, 190, 60), (W // 2 + w // 2 - 18, y + 20, 18, 4))
