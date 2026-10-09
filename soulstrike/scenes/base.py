"""Classe base das telas do jogo."""
import pygame

from .. import config, theme
from ..net.remote import hub


class Scene:
    """Uma tela: recebe eventos, atualiza e desenha. Subclasses sobrescrevem o que precisam."""

    music = "menu"
    phase = "menu"          # o que o celular deve mostrar
    show_cursor = True

    def __init__(self, game):
        self.game = game
        self.ticks = 0

    @property
    def ui(self):
        return self.game.ui

    @property
    def assets(self):
        return self.game.assets

    def sfx(self, name, volume=0.5):
        self.assets.play(name, volume)

    def enter(self):
        pygame.mouse.set_visible(self.show_cursor)
        if self.music:
            self.assets.music(self.music)
        session = self.game.session
        hub.set_phase(self.phase, mode="soccer" if session and session.soccer else "battle",
                      active=self.active_slots())

    def active_slots(self):
        session = self.game.session
        if session is None:
            return (1, 2, 3, 4)
        return tuple(s.slot for s in session.slots if not s.cpu)

    def handle(self, event):
        pass

    def update(self):
        self.ticks += 1

    def draw(self, screen):
        pass

    # ── utilidades comuns ────────────────────
    @staticmethod
    def is_back(event):
        return event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE)

    def title(self, screen, text, y=48):
        self.ui.text(screen, text, theme.M, theme.BONE, (64, y), anchor="midleft")
        w = self.assets.text_width(text, theme.M)
        screen.fill(theme.BRASS, (64, y + 18, min(w, 120), 3))

    def footer(self, screen, items):
        self.ui.hints(screen, items, (config.SCREEN_W // 2, config.SCREEN_H - 22))
